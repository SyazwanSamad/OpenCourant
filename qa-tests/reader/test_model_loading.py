# Copyright>        OpenCourant
# Copyright>        Copyright (C) 2026 OpenCourant contributors
# Copyright>
# Copyright>        This program is free software: you can redistribute it and/or modify
# Copyright>        it under the terms of the GNU Affero General Public License as published by
# Copyright>        the Free Software Foundation, either version 3 of the License, or
# Copyright>        (at your option) any later version.
# Copyright>
# Copyright>        This program is distributed in the hope that it will be useful,
# Copyright>        but WITHOUT ANY WARRANTY; without even the implied warranty of
# Copyright>        MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# Copyright>        GNU Affero General Public License for more details.
# Copyright>
# Copyright>        You should have received a copy of the GNU Affero General Public License
# Copyright>        along with this program.  If not, see <https://www.gnu.org/licenses/>.
# Copyright>
# Copyright>
# Copyright>        This file is part of OpenCourant, a fork of OpenRadioss.
# Copyright>        See COPYRIGHT.md at the root of the repository for the full
# Copyright>        copyright and attribution statement.
"""Exercise OpenReader profile loading and errors at the native API and Starter boundaries."""

import argparse
import ctypes as ct
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / 'qa-tests/reader/rigid_parts/data'
INT = ct.c_int
REF = ct.byref
PINT = ct.POINTER(INT)


def probe(args):
    os.environ['RAD_CFG_PATH'] = str(args.configuration)
    if os.name == 'nt':
        dll_directory = os.add_dll_directory(str(args.reader.parent))
    reader = ct.CDLL(str(args.reader))
    initialize = reader.hm_reader_variables
    initialize.argtypes, initialize.restype = [PINT, PINT], None
    initial, version = INT(), INT(args.version)
    initialize(REF(initial), REF(version))
    filename = os.fsencode(args.case)
    result, includes = INT(-1), INT(-1)
    load = getattr(reader, args.entry)
    load.argtypes = [ct.c_char_p, PINT, PINT]
    load.restype = None
    parameters = [filename, REF(INT(len(filename))), REF(result)]
    if args.entry == 'cpp_build_model_inc':
        path = os.fsencode(str(args.case.parent) + os.sep)
        load.argtypes += [PINT, ct.c_char_p, PINT]
        parameters += [REF(includes), path, REF(INT(len(path)))]
    elif args.entry == 'cpp_read_dyna_and_convert':
        converted = os.fsencode(args.output.with_suffix('.rad'))
        load.argtypes += [ct.c_char_p, PINT]
        parameters += [converted, REF(INT(len(converted)))]
    load(*parameters)
    output = {'initial': initial.value, 'result': result.value, 'includes': includes.value}
    if result.value == 0:
        count = reader.cpp_option_count
        count.argtypes, count.restype = [ct.c_char_p, PINT, PINT], None
        parts = INT()
        count(b'PART', REF(INT(4)), REF(parts))
        output['parts'] = parts.value
        if parts.value:
            reader.cpp_option_next.restype = None
            reader.cpp_option_next()
            get = reader.cpp_get_intv
            get.argtypes = [ct.c_char_p, PINT, PINT, PINT, ct.POINTER(ct.c_bool), PINT]
            get.restype = None
            flag, submodel, kind, available = INT(), INT(), INT(), ct.c_bool()
            get(b'IRIGID', REF(INT(6)), REF(flag), REF(submodel), REF(available), REF(kind))
            output['irigid'] = flag.value if available.value else None
            for name, signature in {
                'cpp_model_open_file': [ct.c_char_p, PINT],
                'cpp_global_entity_sdi_write': [PINT],
                'cpp_model_close_file': [],
            }.items():
                function = getattr(reader, name)
                function.argtypes, function.restype = signature, None
            written = args.output.with_suffix('.rad')
            path = os.fsencode(written)
            reader.cpp_model_open_file(path, REF(INT(len(path))))
            count(b'PART', REF(INT(4)), REF(parts))
            for _ in range(parts.value):
                reader.cpp_global_entity_sdi_write(REF(INT(0)))
            reader.cpp_model_close_file()
            lines = [line for line in written.read_text().splitlines() if line and not line.startswith('#')]
            header = next(index for index, line in enumerate(lines) if line.startswith('/PART/10'))
            output['written_irigid'] = int(lines[header + 2][50:60])
    args.output.write_text(json.dumps(output), encoding='utf-8')


def configuration(target, version):
    shutil.copytree(ROOT / 'hm_cfg_files/messages', target / 'messages')
    shutil.copytree(ROOT / 'hm_cfg_files/config/CFG/UNITS', target / 'config/CFG/UNITS')
    folder = target / f'config/CFG/radioss{version}'
    folder.mkdir()
    (folder / 'data_hierarchy.cfg').write_text('''HIERARCHY {
  KEYWORD = NODES;
  TITLE = "NODE";
  TYPE = NODE;
  HIERARCHY {
    KEYWORD = NODE;
    TITLE = "NODE";
    FILE = "NODE/missing.cfg";
    USER_NAMES = (NODE);
  }
}
''', encoding='utf-8')


def run(args):
    with tempfile.TemporaryDirectory(prefix='opencourant-loading-') as temporary:
        work = Path(temporary)
        broken, unsupported = work / 'broken-cfg', work / 'unsupported-cfg'
        configuration(broken, 2612)
        configuration(unsupported, 9999)
        environment = os.environ.copy()
        environment['TEMP'] = environment['TMP'] = str(work)
        cases = [
            ('ordinary', DATA / 'ordinary_zero.rad', ROOT / 'hm_cfg_files', 2612, 0, None),
            ('rigid-field', DATA / 'single.rad', ROOT / 'hm_cfg_files', 2612, 1, None),
            ('unsupported-profile', DATA / 'ordinary_zero.rad', unsupported, 9999, None,
             'Unsupported configuration profile: radioss9999'),
            ('broken-configuration', DATA / 'ordinary_zero.rad', broken, 2612, None, 'NODE/missing.cfg'),
            ('missing-configuration', DATA / 'ordinary_zero.rad', work / 'absent-cfg', 2612, None, 'OpenReader:'),
            ('missing-input', work / 'absent.rad', ROOT / 'hm_cfg_files', 2612, None, 'OpenReader:'),
        ]
        for name, fixture, cfg, version, irigid, diagnostic in cases:
            for entry in ['cpp_build_model', 'cpp_build_model_inc']:
                output = work / 'result.json'
                command = [sys.executable, str(Path(__file__).resolve()), '--reader', str(args.reader),
                           '--case', str(fixture), '--configuration', str(cfg), '--version', str(version),
                           '--entry', entry, '--output', str(output)]
                result = subprocess.run(command, env=environment, capture_output=True, text=True,
                                        timeout=30, cwd=work)
                if result.returncode:
                    raise AssertionError(f'{name}/{entry}: native exception or process failure\n'
                                         f'{result.stdout}{result.stderr}')
                actual = json.loads(output.read_text(encoding='utf-8'))
                if diagnostic:
                    assert actual['result'] != 0, (name, actual)
                    assert diagnostic in result.stdout + result.stderr, (name, result.stdout, result.stderr)
                    if entry.endswith('_inc'):
                        assert actual['includes'] == 0, (name, actual)
                else:
                    assert actual['initial'] == actual['result'] == 0, (name, actual)
                    assert actual['parts'] == 1 and actual['irigid'] == irigid, (name, actual)
                    assert actual['written_irigid'] == irigid, (name, actual)
                print(f'PASS {name}/{entry}', flush=True)
        keyword = work / 'empty.k'
        keyword.write_text('*KEYWORD\n*END\n', encoding='utf-8')
        for fixture, version, expected, diagnostic in [
            (keyword, 2612, 0, None),
            (keyword, 9999, 1, 'Unsupported configuration profile: radioss9999'),
            (work / 'absent.k', 2612, 1, 'Cannot open LS-DYNA input file'),
        ]:
            output = work / 'dyna.json'
            command = [sys.executable, str(Path(__file__).resolve()), '--reader', str(args.reader),
                       '--case', str(fixture), '--configuration', str(ROOT / 'hm_cfg_files'),
                       '--version', str(version), '--entry', 'cpp_read_dyna_and_convert', '--output', str(output)]
            result = subprocess.run(command, env=environment, capture_output=True, text=True, timeout=30, cwd=work)
            assert result.returncode == 0, result.stdout + result.stderr
            actual = json.loads(output.read_text(encoding='utf-8'))
            assert actual['result'] == expected, (version, actual, result.stdout, result.stderr)
            if expected:
                assert diagnostic in result.stderr, result.stderr
            print(f'PASS LS-DYNA {fixture.name}/profile-{version}', flush=True)
        if args.starter:
            environment.update(RAD_CFG_PATH=str(ROOT / 'hm_cfg_files'), OMP_NUM_THREADS='1',
                               KMP_STACKSIZE='400m', RAD_H3D_PATH=str(ROOT / 'extlib/h3d/lib/win64'))
            smoke = work / 'accelerometer'
            shutil.copytree(ROOT / 'qa-tests/miniqa/ACCELEROMETRES/data', smoke)
            result = subprocess.run([str(args.starter), '-i', 'ACCELERO_0000.rad', '-np', '1'],
                                    env=environment, capture_output=True, text=True, timeout=60, cwd=smoke)
            assert result.returncode == 0, result.stdout + result.stderr
            listing = (smoke / 'ACCELERO_0000.out').read_text(errors='replace')
            assert '0 ERROR(S)' in listing, listing[-2000:]
            assert any(path.stat().st_size > 0 for path in smoke.glob('*.rst')), 'No restart generated'
            print('PASS Starter accelerometer smoke', flush=True)
            for name, fixture, cfg, diagnostic in [
                ('configuration-error', DATA / 'ordinary_zero.rad', broken, 'Input reader failed to load'),
                ('rigid-guard', DATA / 'single.rad', ROOT / 'hm_cfg_files', 'requests IRIGID=1'),
            ]:
                folder = work / name
                folder.mkdir()
                shutil.copy(DATA / 'common.inc', folder)
                shutil.copy(fixture, folder / 'case_0000.rad')
                environment['RAD_CFG_PATH'] = str(cfg)
                result = subprocess.run([str(args.starter), '-i', 'case_0000.rad', '-np', '1'],
                                        env=environment, capture_output=True, text=True, timeout=30, cwd=folder)
                assert result.returncode == 2, (name, result.stdout, result.stderr)
                assert diagnostic in result.stdout + result.stderr, (name, result.stdout, result.stderr)
                assert 'forrtl: severe' not in result.stdout + result.stderr, (name, result.stdout, result.stderr)
                print(f'PASS Starter {name}', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reader', required=True, type=lambda path: Path(path).resolve())
    parser.add_argument('--starter', type=lambda path: Path(path).resolve())
    parser.add_argument('--case', type=Path, help=argparse.SUPPRESS)
    parser.add_argument('--configuration', type=Path, help=argparse.SUPPRESS)
    parser.add_argument('--version', type=int, default=2612, help=argparse.SUPPRESS)
    parser.add_argument('--entry', default='cpp_build_model_inc', help=argparse.SUPPRESS)
    parser.add_argument('--output', type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.case:
        probe(args)
    else:
        run(args)


if __name__ == '__main__':
    main()
