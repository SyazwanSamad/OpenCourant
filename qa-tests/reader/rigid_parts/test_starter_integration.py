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
"""Stage 4 native-helper, Fortran bounds, and full Starter integration checks."""

import argparse
import ctypes as ct
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

from test_reader_contract import Reader, HERE, ROOT, INT, REF, PINT, TEXT


def helper_check(library, name):
    reader = Reader(library)
    if name == 'no-selected-body':
        reader.library.cpp_add_rbody_main_node(REF(INT()))
        raise AssertionError('Missing model was accepted')
    invalid_position = name in ['negative-position', 'past-end-position']
    reader.load(HERE / 'data' / (('existing' if invalid_position else name) + '.rad'))
    npart_ids = {row['id'] for row in reader.entities(b'PART', ['id'])}
    shells = reader.count(b'/SHELL')
    connectivity = (INT * (6*shells+2))(*([123456789] * (6*shells+2)))
    integers = [(INT * (shells+2))(*([123456789] * (shells+2))) for _ in range(3)]
    reals = [(ct.c_double * (shells+2))(*([123456789] * (shells+2))) for _ in range(2)]
    ip = lambda value: ct.cast(ct.byref(value, ct.sizeof(INT)), PINT)
    dp = lambda value: ct.cast(ct.byref(value, ct.sizeof(ct.c_double)), ct.POINTER(ct.c_double))
    reader.library.cpp_shell_read.argtypes = [PINT, PINT, PINT, ct.POINTER(ct.c_double),
                                            ct.POINTER(ct.c_double), PINT, PINT]
    reader.library.cpp_shell_read(ip(connectivity), REF(INT(6)), ip(integers[0]),
                                  dp(reals[0]), dp(reals[1]), ip(integers[1]), ip(integers[2]))
    for array in [connectivity, *integers, *reals]:
        assert array[0] == array[-1] == 123456789, list(array)
    for i in range(shells):
        assert integers[0][i+1] in npart_ids
        nodes = list(connectivity)[6*i+2:6*i+6]
        assert len(set(nodes)) == 4 and all(node > 0 for node in nodes), nodes
    counts = (INT * reader.count(b'PART'))()
    reader.library.cpp_evaluate_rbodies_number_from_rigid_parts(counts)
    mapping, ids = (INT * sum(counts))(), (INT * sum(counts))()
    reader.library.cpp_create_rbodies_from_rigid_parts(mapping, ids)
    before = reader.count(b'/NODE')
    bodies = reader.count(b'/RBODY')
    reader.select(b'/RBODY')
    added = {}
    for _ in range(bodies):
        reader.library.cpp_option_next()
        original = reader.integer('node_ID')
        owner = {'include': reader.integer('include'), 'unitid': 0}
        node = INT(-1)
        reader.library.cpp_add_rbody_main_node(REF(node))
        if original:
            assert node.value == 0 and reader.integer('node_ID') == original
        else:
            assert node.value > 0 and reader.integer('node_ID') == node.value
            added[node.value] = owner
        node.value = -1
        reader.library.cpp_add_rbody_main_node(REF(node))
        assert node.value == 0, 'Repeated main-node creation'
    assert reader.count(b'/NODE') == before + len(added)
    for row in reader.entities(b'/NODE', ['id', 'include', 'unitid'], ['X', 'Y', 'Z']):
        if row['id'] in added:
            assert {key: row[key] for key in ['include', 'unitid']} == added[row['id']], row
            assert all(row[key] == 0 for key in ['X', 'Y', 'Z']), row
    reader.library.cpp_option_start_list.argtypes = [TEXT, PINT]
    reader.library.cpp_option_read.argtypes = [PINT, PINT, PINT, TEXT, PINT, TEXT, PINT, PINT, PINT]
    for kind in [b'/SET', b'/RBODY', b'/RBODY']:
        reader.library.cpp_option_start_list(kind, REF(INT(len(kind))))
        positions = range(1, reader.count(kind) + 1)
        if invalid_position:
            positions = [-1 if name == 'negative-position' else 9999]
        for position in positions:
            values = [INT() for _ in range(6)]
            key, title = ct.create_string_buffer(500), ct.create_string_buffer(500)
            reader.library.cpp_option_read(REF(values[0]), REF(values[1]), REF(values[2]), key,
                                           REF(values[3]), title, REF(values[4]), REF(values[5]), REF(INT(position)))
            assert values[0].value > 0
            if kind == b'/RBODY':
                assert reader.integer('node_ID') > 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reader', required=True, type=lambda p: Path(p).resolve())
    parser.add_argument('--binaries', required=True, type=lambda p: Path(p).resolve())
    parser.add_argument('--worker', help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker:
        helper_check(args.reader, args.worker)
        return
    environment = os.environ.copy()
    environment.update(RAD_CFG_PATH=str(ROOT / 'hm_cfg_files'), OMP_NUM_THREADS='1', KMP_STACKSIZE='400m',
                       RAD_H3D_PATH=str(ROOT / 'extlib/h3d/lib/win64'))
    environment['PATH'] = os.pathsep.join([str(args.reader.parent), str(ROOT / 'extlib/hm_reader/win64'),
                                         environment.get('PATH', '')])
    with tempfile.TemporaryDirectory(prefix='opencourant-stage4-') as temporary:
        work = Path(temporary)

        def run(command, cwd=work, expected=0):
            result = subprocess.run([str(arg) for arg in command], env=environment, cwd=cwd,
                                    capture_output=True, text=True, timeout=60)
            assert result.returncode == expected, (command, result.returncode, result.stdout[-6000:], result.stderr)
            assert 'forrtl: severe' not in result.stderr + result.stdout, (command, result.stderr)
            return result

        for name in ['existing', 'explicit_fields', 'interleaved', 'lagmul', 'lagmul_missing_node',
                     'submodel_missing_node']:
            run([sys.executable, Path(__file__).resolve(), '--reader', args.reader,
                 '--binaries', args.binaries, '--worker', name])
            print(f'PASS connectivity, main nodes, and indexed selection: {name}', flush=True)
        for mode, diagnostic in [('no-selected-body', 'requires a selected rigid body'),
                                 ('negative-position', 'out of bounds'), ('past-end-position', 'out of bounds')]:
            result = run([sys.executable, Path(__file__).resolve(), '--reader', args.reader,
                          '--binaries', args.binaries, '--worker', mode], expected=1)
            assert diagnostic in result.stderr
            print(f'PASS helper rejection: {mode}', flush=True)
        for library in ['openreader', 'v82']:
            driver = args.binaries / f'driver-{library}.exe'
            for name in ['no_parts', 'mixed', 'interleaved', 'lagmul', 'submodel_missing_node']:
                run([driver, HERE / 'data' / (name + '.rad')])
                print(f'PASS bounds-checked Fortran: {library}/{name}', flush=True)
            for mode in ['missing-id', 'duplicate-id']:
                result = run([driver, mode], expected=2)
                assert 'IDs do not match' in result.stdout
                print(f'PASS ordering rejection: {library}/{mode}', flush=True)
            for name in ['single', 'mixed', 'existing', 'shared', 'interleaved', 'lagmul', 'explicit_fields', 'explicit-rota']:
                folder = work / (library + '-' + name)
                if name == 'explicit-rota':
                    shutil.copytree(ROOT / 'qa-tests/miniqa/KIN_CONSTRAINTS/RBODY/ROTA/data', folder)
                    filename = 'BLOCK_0000.rad'
                else:
                    shutil.copytree(HERE / 'data', folder)
                    shutil.copy(folder / (name + '.rad'), folder / 'case_0000.rad')
                    filename = 'case_0000.rad'
                run([args.binaries / f'starter-{library}.exe', '-i', filename, '-np', '1'], cwd=folder)
                listing = (folder / filename.replace('.rad', '.out')).read_text(errors='replace')
                assert re.search(r'\b0 ERROR\(S\)', listing), listing[-6000:]
                assert any(p.stat().st_size for p in folder.glob('*.rst')), (library, name, 'missing restart')
                print(f'PASS full Starter: {library}/{name}', flush=True)


if __name__ == '__main__':
    main()
