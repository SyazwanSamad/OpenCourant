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
"""Keep header options and geometry on every record under a shared keyword."""

import argparse
import ctypes as ct
import os
from pathlib import Path
import subprocess
import sys
import tempfile

from rigid_parts.test_reader_contract import Reader, ROOT, INT, REF, PINT
from test_model_queries import dyna_load


def deck(shared):
    text = ('*KEYWORD\n*NODE\n1,0,0,0\n2,1,0,0\n3,1,1,0\n4,0,1,0\n'
            '*ELEMENT_SHELL\n1,1,1,2,3,4\n*PART\nplate\n1,1,1\n'
            '*SECTION_SHELL\n1,16,0.8333,5\n1,1,1,1\n*MAT_ELASTIC\n1,1,100,0.3\n')
    planes = [
        (11, [0, .25, -.5, -.5, 1.25, -.5, -.5, 0], [.25, .5, -.5, 2, 1, 0, 0]),
        (23, [0, -.5, .75, -.5, -.5, 1.75, -.5, 0], [-.5, .75, .5, 1, 2, 0, 0]),
    ]
    for index, (identifier, normal, edge) in enumerate(planes):
        text += '$ plane record\n'
        if index == 0 or not shared:
            text += '*DATABASE_CROSS_SECTION_PLANE_ID\n'
        text += f'{identifier:10d}plane {identifier}\n'
        text += ''.join(f'{value:10g}' for value in normal) + '\n'
        text += ''.join(f'{value:10g}' for value in edge) + '\n'
    return text + '*DEFINE_CURVE\n        71\n                   0                   0\n                   1                   2\n*END\n'


def probe(args):
    reader = Reader(args.reader)
    if args.case.suffix == '.k':
        error, version = INT(), INT(2612)
        reader.library.hm_reader_variables(REF(error), REF(version))
        assert error.value == 0
        assert dyna_load(reader, args.case, args.case.with_suffix('.rad')) == 0
        reader.check_messages()
    else:
        reader.load(args.case)
    keys = ['XM', 'YM', 'ZM', 'XM1', 'YM1', 'ZM1', 'XM2', 'YM2', 'ZM2']
    expected = [
        dict(zip(['id'] + keys, [11, .25, -.5, -.5, .25, 1.5, -.5, .25, -.5, .5])),
        dict(zip(['id'] + keys, [23, -.5, .75, -.5, -.5, .75, .5, 1.5, .75, -.5])),
    ]
    assert reader.count(b'/SECT') == 2
    assert reader.entities(b'/SECT/PARAL', ['id'], keys) == expected
    assert reader.count(b'/FRAME/MOV') == 0
    assert reader.count(b'/NODE') == 10
    ids, submodels, units = (INT * 10)(), (INT * 10)(), (INT * 10)()
    coordinates, weights = (ct.c_double * 30)(), (ct.c_double * 10)()
    reader.library.cpp_node_read.argtypes = [PINT, ct.POINTER(ct.c_double), ct.POINTER(ct.c_double), PINT, PINT]
    reader.library.cpp_node_read.restype = None
    reader.library.cpp_node_read(ids, coordinates, weights, submodels, units)
    positions = {ids[i]: list(coordinates[3 * i:3 * i + 3]) for i in range(10)}
    assert len(positions) == 10
    sections = reader.entities(b'/SECT/PARAL', ['id', 'node_ID1', 'node_ID2', 'node_ID3'])
    expected_nodes = [
        [[.25, -.5, -.5], [.25, .5, -.5], [.25, -.5, .5]],
        [[-.5, .75, -.5], [-.5, .75, .5], [.5, .75, -.5]],
    ]
    for section, coordinates in zip(sections, expected_nodes):
        actual = [positions[section[key]] for key in ['node_ID1', 'node_ID2', 'node_ID3']]
        assert actual == coordinates, (section, actual, coordinates)
    assert reader.entities(b'/FUNCT', ['id', 'numberofpoints']) == [{'id': 71, 'numberofpoints': 2}]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reader', required=True, type=lambda p: Path(p).resolve())
    parser.add_argument('--starter', type=lambda p: Path(p).resolve())
    parser.add_argument('--case', type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.case:
        probe(args)
        return
    env = os.environ.copy()
    env.update(RAD_CFG_PATH=str(ROOT / 'hm_cfg_files'), OMP_NUM_THREADS='1', KMP_STACKSIZE='400m')
    with tempfile.TemporaryDirectory(prefix='opencourant-shared-headers-') as temporary:
        for shared in [False, True]:
            for native in [False, True]:
                name = ('shared' if shared else 'separate') + ('-include' if native else '-keyword')
                work = Path(temporary) / name
                work.mkdir()
                (work / 'case.k').write_text(deck(shared))
                filename = 'case.k'
                if native:
                    filename = 'case_0000.rad'
                    (work / filename).write_text('/BEGIN\ncase\n      2026         0\n'
                        '                  Mg                  mm                   s\n'
                        '/INCLUDE_LS-DYNA\ncase.k\n/END\n')
                command = [sys.executable, str(Path(__file__).resolve()), '--reader', str(args.reader),
                           '--case', str(work / filename)]
                result = subprocess.run(command, cwd=work, env=env, capture_output=True, text=True, timeout=30)
                assert result.returncode == 0, (name, result.stdout, result.stderr)
                print(f'PASS Reader {name}: section geometry, nodes, and following keyword', flush=True)
                if args.starter:
                    result = subprocess.run([str(args.starter), '-i', filename, '-np', '1'],
                        cwd=work, env=env, capture_output=True, text=True, timeout=60)
                    listing = (work / 'case_0000.out').read_text(errors='replace')
                    assert result.returncode == 0 and '0 ERROR(S)' in listing, (name,
                        result.stdout, result.stderr, listing[-3000:])
                    assert 'forrtl: severe' not in (result.stdout + result.stderr).lower()
                    assert any(path.stat().st_size for path in work.glob('*.rst')), name
                    print(f'PASS Starter {name}: restart', flush=True)


if __name__ == '__main__':
    main()
