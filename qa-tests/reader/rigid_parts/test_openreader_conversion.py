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
"""Stage 3 comparisons and lifecycle checks for the in-tree OpenReader."""

import argparse
import ctypes as ct
import json
from pathlib import Path
import subprocess
import shutil
import sys
import tempfile

from test_reader_contract import Reader, HERE, INT, REF, PINT, PBOOL, TEXT


CANARY = 123456789


class GuardedArray:
    def __init__(self, size):
        self.storage = (INT * (size + 2))(*([CANARY] * (size + 2)))
        self.pointer = ct.cast(ct.byref(self.storage, ct.sizeof(INT)), PINT)

    def values(self):
        assert self.storage[0] == self.storage[-1] == CANARY, list(self.storage)
        return list(self.storage)[1:-1]


def lifecycle(reader, mode):
    reader.library.cpp_set_intv.argtypes = [TEXT, PINT, PINT, PBOOL]
    reader.library.cpp_set_intv.restype = None
    reader.library.cpp_delete_entity.argtypes = []
    reader.library.cpp_delete_entity.restype = None
    if mode == 'missing-reference':
        with tempfile.TemporaryDirectory() as temporary:
            fixture = Path(temporary) / 'missing_reference.rad'
            text = (HERE / 'data/mixed.rad').read_text(encoding='utf-8')
            fixture.write_text(text.replace('         0         0                   0                   0',
                                             '      9999         0                   0                   0'), encoding='utf-8')
            shutil.copy(HERE / 'data/common.inc', temporary)
            reader.load(fixture)
    else:
        reader.load(HERE / 'data/mixed.rad')
    counts = GuardedArray(3)
    if mode != 'without-evaluation':
        reader.select(b'PART')
        reader.library.cpp_option_next()
        assert reader.integer('id') == 10
        reader.library.cpp_evaluate_rbodies_number_from_rigid_parts(counts.pointer)
        assert counts.values() == [1, 0, 1]
        assert reader.integer('id') == 10, 'Evaluation moved the current entity'
    if mode == 'reload-without-evaluation':
        reader.load(HERE / 'data/ordinary_zero.rad')
    if mode == 'changed-after-create':
        mapping, ids = GuardedArray(2), GuardedArray(2)
        reader.library.cpp_create_rbodies_from_rigid_parts(mapping.pointer, ids.pointer)
    if mode in ['changed-parts', 'changed-after-create']:
        reader.library.cpp_set_intv(b'IRIGID', REF(INT(6)), REF(INT(0)), REF(ct.c_bool()))
        assert reader.integer('IRIGID') == 0
    if mode == 'deleted-part':
        reader.library.cpp_delete_entity()
    mapping, ids = GuardedArray(2), GuardedArray(2)
    reader.library.cpp_create_rbodies_from_rigid_parts(mapping.pointer, ids.pointer)
    assert mode == 'repeat-reload', 'Invalid creation unexpectedly returned'
    assert mapping.values() == [10, 30] and ids.values() == [1, 2]
    assert reader.integer('id') == 10, 'Creation moved the current entity'
    for _ in range(2):
        reader.library.cpp_evaluate_rbodies_number_from_rigid_parts(counts.pointer)
        reader.library.cpp_create_rbodies_from_rigid_parts(mapping.pointer, ids.pointer)
        assert counts.values() == [1, 0, 1]
        assert mapping.values() == [10, 30] and ids.values() == [1, 2]
        assert reader.count(b'/RBODY') == reader.count(b'/SET') == 2
    for name, expected in [('ordinary_zero', [0]), ('explicit_fields', [1]), ('no_parts', [])]:
        reader.load(HERE / 'data' / (name + '.rad'))
        counts = GuardedArray(len(expected))
        reader.library.cpp_evaluate_rbodies_number_from_rigid_parts(counts.pointer)
        assert counts.values() == expected
        mapping, ids = GuardedArray(sum(expected)), GuardedArray(sum(expected))
        reader.library.cpp_create_rbodies_from_rigid_parts(mapping.pointer, ids.pointer)
        assert reader.count(b'/RBODY') == sum(expected), 'Stale bodies after reload'
        assert len(mapping.values()) == len(ids.values()) == sum(expected)
    for stem in ['cpp_evaluate_rbodies_number_from_rigid_parts', 'cpp_create_rbodies_from_rigid_parts']:
        for symbol in [stem, stem + '_', stem + '__', stem.upper()]:
            getattr(reader.library, symbol)


def mode2_lifecycle(reader, mode):
    with tempfile.TemporaryDirectory() as temporary:
        fixture = Path(temporary) / 'connected.rad'
        text = (HERE / 'data/flag_two_single.rad').read_text().replace(
            '         1         1         2         3         4\n',
            '         1         1         2         3         4\n         2         4         5         6         7\n')
        fixture.write_text(text)
        shutil.copy(HERE / 'data/common.inc', temporary)
        reader.load(fixture)
    counts, mapping, ids = GuardedArray(1), GuardedArray(1), GuardedArray(1)
    reader.select(b'PART')
    reader.library.cpp_option_next()
    reader.library.cpp_evaluate_rbodies_number_from_rigid_parts(counts.pointer)
    assert counts.values() == [1] and reader.integer('id') == 10
    if mode == 'mode2-flag':
        reader.library.cpp_set_intv.argtypes = [TEXT, PINT, PINT, PBOOL]
        reader.library.cpp_set_intv(b'IRIGID', REF(INT(6)), REF(INT(1)), REF(ct.c_bool()))
    for _ in range(2):
        reader.library.cpp_create_rbodies_from_rigid_parts(mapping.pointer, ids.pointer)
        assert mode == 'mode2-repeat', 'Changed mode-2 plan was accepted'
        assert mapping.values() == [10] and ids.values() == [1]
        reader.library.cpp_evaluate_rbodies_number_from_rigid_parts(counts.pointer)
        assert counts.values() == [1] and reader.count(b'/RBODY') == 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reader', required=True, type=lambda path: Path(path).resolve())
    parser.add_argument('--worker', help=argparse.SUPPRESS)
    parser.add_argument('--output', type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker:
        reader = Reader(args.reader)
        if args.worker.endswith('.rad'):
            snapshot = reader.snapshot(HERE / 'data' / args.worker, metadata=True)
            args.output.write_text(json.dumps(snapshot, indent=2), encoding='utf-8')
        elif args.worker.startswith('mode2-'):
            mode2_lifecycle(reader, args.worker)
        else:
            lifecycle(reader, args.worker)
        return
    with tempfile.TemporaryDirectory(prefix='opencourant-conversion-') as temporary:
        work = Path(temporary)

        def run(library, worker, diagnostic=None):
            output = work / 'snapshot.json'
            command = [sys.executable, str(Path(__file__).resolve()), '--reader', str(library),
                       '--worker', worker, '--output', str(output)]
            result = subprocess.run(command, capture_output=True, text=True, timeout=30, cwd=work)
            if diagnostic:
                assert result.returncode == 1 and diagnostic in result.stderr, (worker, result.stdout, result.stderr)
            else:
                assert result.returncode == 0, (worker, result.stdout, result.stderr)
                if worker.endswith('.rad'):
                    return json.loads(output.read_text(encoding='utf-8'))

        for mode, diagnostic in [
            ('repeat-reload', None),
            ('without-evaluation', 'creation requires evaluation'),
            ('reload-without-evaluation', 'creation requires evaluation'),
            ('changed-parts', 'parts changed after'),
            ('changed-after-create', 'parts changed after'),
            ('deleted-part', 'parts changed after'),
            ('missing-reference', 'references a missing'),
            ('mode2-repeat', None),
            ('mode2-flag', 'parts changed after'),
        ]:
            run(args.reader, mode, diagnostic)
            print(f'PASS {mode}', flush=True)
        golden = json.loads((HERE / 'expected_conversion.json').read_text())
        for name in ['solid', 'include_fields', 'submodel_units', 'different_offsets', 'two_submodels']:
            actual = run(args.reader, name + '.rad')
            expected = golden['mode1'][name]
            # v82 loses explicit units on generated objects; preserve the part's unit context.
            part_units = {row['id']: row['unitid'] for row in actual['ownership']['PART']}
            for kind in ['/RBODY', '/SET']:
                for row, source in zip(actual['ownership'][kind], actual['mapping']):
                    assert row['unitid'] == part_units[source], (name, kind, row, part_units)
                for row in expected['ownership'][kind]:
                    assert row['unitid'] == 0, (name, row)
                for row in actual['ownership'][kind]:
                    row['unitid'] = 0
            assert actual == expected, (name, actual, expected)
            print(f'PASS {name} (frozen v82 snapshot, explicit units retained)', flush=True)
        variants = work / 'mode2'
        shutil.copytree(HERE / 'data', variants)
        for fixture in variants.iterdir():
            if fixture.suffix not in ['.rad', '.inc']:
                continue
            lines = fixture.read_text().splitlines()
            for index in reversed(range(len(lines))):
                if lines[index].startswith('/PART/') and lines[index+2][50:60].strip() == '1':
                    lines[index+2] = lines[index+2][:50] + f'{2:10d}'
                    del lines[index+3:index+6]
            fixture.write_text('\n'.join(lines) + '\n')
        base = (variants / 'flag_two_single.rad').read_text()
        for name, nodes in [('vertex', (4, 5, 6, 7)), ('edge', (3, 4, 5, 6))]:
            (variants / (name + '.rad')).write_text(base.replace('/PART/10',
                ''.join(f'{n:10d}' for n in (2, *nodes)) + '\n/PART/10'))
        (variants / 'reverse.rad').write_text(base.replace(
            '         1         1         2         3         4\n',
            '         1         5         6         7         8\n         2         1         2         3         4\n'))
        for kind, nodes in [('SH3N', [1, 2, 3]), ('TRUSS', [1, 2]), ('BEAM', [1, 2, 3]),
                            ('TETRA4', [1, 2, 3, 4])]:
            (variants / (kind.lower() + '.rad')).write_text(base.replace(
                '/SHELL/10\n         1         1         2         3         4\n',
                f'/{kind}/10\n' + ''.join(f'{n:10d}' for n in [1, *nodes]) + '\n'))
        for name in ['flag_two_single', 'disconnected_two', 'vertex', 'edge', 'reverse', 'empty',
                     'solid', 'shared', 'existing', 'mixed', 'include_fields', 'different_offsets',
                     'submodel_units', 'two_submodels', 'sh3n', 'truss', 'beam', 'tetra4']:
            actual = run(args.reader, str(variants / (name + '.rad')))
            expected = golden['mode2'][name]
            part_units = {row['id']: row['unitid'] for row in actual['ownership']['PART']}
            for kind in ['/RBODY', '/SET']:
                for row, source in zip(actual['ownership'][kind][-len(actual['mapping']):], actual['mapping']):
                    assert row['unitid'] == part_units[source], (name, kind, row)
                    row['unitid'] = 0
            assert actual == expected, (name, actual, expected)
            print(f'PASS mode2 {name} (full node sets and ownership)', flush=True)


if __name__ == '__main__':
    main()
