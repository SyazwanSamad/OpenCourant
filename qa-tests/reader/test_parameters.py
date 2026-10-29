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
"""Check a literal/parameterized pair and four single-error variants on Windows."""

import argparse
import ctypes as ct
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

from rigid_parts.test_reader_contract import Reader, ROOT, INT, REF


CASES = ['literal', 'parameterized', 'missing', 'argument', 'syntax', 'cycle']
FIXTURES = Path(__file__).resolve().parent/'parameters'


def check_values(reader):
    materials = reader.entities(b'MATERIAL', ['id'], ['E'])
    assert {m['id']: m['E'] for m in materials} == {1: 12345, 2: 24000, 3: 6000, 4: 6000}, materials
    reader.select(b'MATERIAL')
    for _ in materials:
        reader.library.cpp_option_next()
        if reader.integer('id') == 1:
            assert reader.string_at('name', 0) == 'test specimen', reader.string_at('name', 0)
    parts = reader.entities(b'PART', ['id', 'IRIGID'])
    assert parts == [{'id': 10, 'IRIGID': 0}], parts
    functions = reader.entities(b'/FUNCT', ['id'])
    assert functions == [{'id': 1}], functions


def probe(args):
    reader = Reader(args.reader)
    if args.probe == 'compatibility':
        from test_model_queries import dyna_load
        error, version = INT(), INT(2612)
        reader.library.hm_reader_variables(REF(error), REF(version))
        assert error.value == 0
        converted = args.output/'converted.rad'
        assert dyna_load(reader, FIXTURES/'compatibility.key', converted) == 0
        count = INT()
        reader.library.cpp_node_count.argtypes = [ct.POINTER(INT)]
        reader.library.cpp_node_count(REF(count))
        assert count.value == 1, count.value
        ids, submodels, units = (INT*1)(), (INT*1)(), (INT*1)()
        coordinates, weights = (ct.c_double*3)(), (ct.c_double*1)()
        reader.library.cpp_node_read.argtypes = [ct.POINTER(INT), ct.POINTER(ct.c_double),
            ct.POINTER(ct.c_double), ct.POINTER(INT), ct.POINTER(INT)]
        reader.library.cpp_node_read(ids, coordinates, weights, submodels, units)
        assert list(ids) == [2] and list(coordinates) == [3.5, 0, 0], (list(ids), list(coordinates))
        material = args.output/'material.inc'
        material.write_text(material.read_text().replace('test specimen', 'test & specimen'))
        model = args.output/'rigid_0000.rad'
        model.write_text(model.read_text().replace('/END',
            '/FUNCT_PYTHON/9\ndef mask(x):\n    return int(x)&1\n/END'))
        reader.load(model)
        reader.select(b'MATERIAL')
        for _ in range(reader.count(b'MATERIAL')):
            reader.library.cpp_option_next()
            if reader.integer('id') == 1:
                assert reader.string_at('name', 0) == 'test & specimen'
        reader.select(b'/FUNCT_PYTHON')
        reader.library.cpp_option_next()
        assert reader.string_at('arraydatalines', 2).strip() == 'return int(x)&1'
    elif args.probe in ['literal', 'parameterized']:
        reader.load(args.output/'rigid_0000.rad')
        check_values(reader)
    else:
        try:
            reader.load(args.output/'rigid_0000.rad')
        except RuntimeError:
            assert reader.count(b'MATERIAL') == 0
        else:
            raise AssertionError('Invalid parameter input was accepted: '+args.probe)
        # A failed model must not poison the next load in the same library instance.
        reader.load(FIXTURES/'parameterized/rigid_0000.rad')
        check_values(reader)
    print('PASS reader parameters: '+args.probe, flush=True)


def prepare(case, folder):
    shutil.copytree(FIXTURES/('literal' if case == 'literal' else 'parameterized'), folder)
    path = folder/'rigid_0000.rad'
    text = path.read_text()
    if case == 'missing':
        path = folder/'material.inc'
        text = path.read_text().replace('&YOUNG', '&MISSING')
    elif case == 'argument':
        text = text.replace('BASE*2+345', 'MISSING*2+345')
    elif case == 'syntax':
        text = text.replace('BASE*2+345', 'BASE*(')
    elif case == 'cycle':
        text = text.replace('COUNT-1', 'YOUNG+1').replace('BASE*2+345', 'FUNCID+1')
    path.write_text(text)


def run(command, folder, env, label):
    result = subprocess.run(list(map(str, command)), cwd=folder, env=env,
                            capture_output=True, text=True, errors='replace', timeout=90)
    output = result.stdout+result.stderr
    (folder/(label+'.log')).write_text(output, encoding='utf-8')
    return result.returncode, output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reader', type=lambda p: Path(p).resolve(), default=ROOT/'exec/open_reader_win64.dll')
    parser.add_argument('--starter', type=lambda p: Path(p).resolve())
    parser.add_argument('--engine', type=lambda p: Path(p).resolve())
    parser.add_argument('--output', required=True, type=lambda p: Path(p).resolve())
    parser.add_argument('--probe', choices=CASES+['compatibility'], help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.probe:
        probe(args)
        return
    assert not args.engine or args.starter, '--engine requires --starter'
    args.output.mkdir(parents=True, exist_ok=False)
    env = os.environ.copy()
    env.update(RAD_CFG_PATH=str(ROOT/'hm_cfg_files'), OMP_NUM_THREADS='1', KMP_STACKSIZE='400m')
    report = {'status': 'running', 'cases': [], 'engine_runs': 0,
              'sha256': {str(path.relative_to(ROOT) if path.is_relative_to(ROOT) else path):
                         hashlib.sha256(path.read_bytes()).hexdigest()
                         for path in [args.reader, args.starter, args.engine, FIXTURES/'compatibility.key',
                                      *FIXTURES.glob('*/*.rad'), *FIXTURES.glob('*/*.inc')]
                         if path and path.is_file()}}
    try:
        for case in CASES:
            folder = args.output/case
            prepare(case, folder)
            code, output = run([sys.executable, __file__, '--reader', args.reader, '--output', folder,
                                '--probe', case], folder, env, 'reader')
            assert code == 0, (case, 'reader', output[-3500:])
            if case not in ['literal', 'parameterized']:
                assert re.search(r'\.(?:rad|inc):[1-9]\d*:', output), (case, output)
            row = {'case': case, 'reader': 'passed'}
            if args.starter:
                code, output = run([args.starter, '-i', 'rigid_0000.rad', '-np', '1'], folder, env, 'starter')
                if case in ['literal', 'parameterized']:
                    assert code == 0 and '0 ERROR(S)' in output, (case, code, output[-3500:])
                    assert any(p.stat().st_size for p in folder.glob('*.rst'))
                    if case == 'parameterized':
                        listing = (folder/'rigid_0000.out').read_text(errors='replace')
                        assert 'GLOBAL PARAMETERS' in listing and 'LOCAL PARAMETERS' in listing
                        for name, value in [('BASE', '6000'), ('BASE', '24000'), ('COUNT', '2'),
                                            ('FUNCID', '1'), ('YOUNG', '12345'), ('NEG', '-1'),
                                            ('ZEROV', '0'), ('LABEL', 'test'), ('AXIS', 'X')]:
                            pattern = r'REFERENCE[^\n]*=\s*'+name+r'\s*\n[^\n]*VALUE[^\n]*=\s*'+value+r'\s*(?:\n|$)'
                            assert re.search(pattern, listing), (name, value, listing[-3000:])
                else:
                    assert code != 0 and 'forrtl: severe' not in output.lower(), (case, code, output)
                    assert not any(p.stat().st_size for p in folder.glob('*.rst')), case
                    assert 'parameter' in output.lower() and any(suffix in output.lower() for suffix in ['.rad', '.inc']), output
                    assert re.search(r'\.(?:rad|inc):[1-9]\d*:', output), output
                row['starter_exit_code'] = code
            report['cases'].append(row)
            print('PASS parameter case: '+case, flush=True)

        folder = args.output/'compatibility'
        prepare('literal', folder)
        code, output = run([sys.executable, __file__, '--reader', args.reader, '--output', folder,
                            '--probe', 'compatibility'], folder, env, 'reader')
        assert code == 0, ('shared reader compatibility', output[-3500:])
        report['shared_reader_controls'] = 'passed'
        print('PASS LS-DYNA parameters and raw Python body', flush=True)

        if args.engine:
            import numpy as np
            from rigid_parts.test_numerical import history, initialization, verify, compare_initialization
            previous = None
            for case in ['literal', 'parameterized']:
                folder = args.output/case
                report['engine_runs'] += 1
                code, output = run([args.engine, '-i', 'rigid_0001.rad', '-nt', '1'], folder, env, 'engine')
                assert code == 0 and 'NORMAL TERMINATION' in output, (case, code, output[-2000:])
                initial = initialization((folder/'rigid_0000.out').read_text(errors='replace'))
                data = history(folder)
                assert np.isfinite(data['time']).all()
                checks = verify('force', initial, data)
                for key, values in data['global'].items():
                    assert np.isfinite(values).all(), key
                if previous:
                    compare_initialization(initial, previous[0])
                    np.testing.assert_allclose(data['time'], previous[1]['time'], rtol=1e-5, atol=1e-6)
                    for key in ['nodes', 'body', 'rotation']:
                        np.testing.assert_allclose(data[key], previous[1][key], rtol=1e-5, atol=1e-6)
                    for key in data['global']:
                        np.testing.assert_allclose(data['global'][key], previous[1]['global'][key], rtol=1e-5, atol=1e-6)
                previous = initial, data
                report['cases'][CASES.index(case)]['physics'] = checks
                print('PASS parameter physics: '+case, flush=True)
        report['status'] = 'passed'
    except Exception as error:
        report.update(status='failed', error=repr(error))
        raise
    finally:
        (args.output/'report.json').write_text(json.dumps(report, indent=2)+'\n')


if __name__ == '__main__':
    main()
