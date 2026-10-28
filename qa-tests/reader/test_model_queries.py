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
"""Check Starter's include/part ABI and selection preservation against fixture expectations."""

import argparse
import ctypes as ct
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from rigid_parts.test_reader_contract import Reader, ROOT, INT, REF, PINT, PBOOL, TEXT


STEMS = ['cpp_get_number_of_include_files', 'cpp_get_include_file_by_index',
         'cpp_is_part_with_elements']


def configure(reader):
    for stem, signature in zip(STEMS, [[PINT, PINT], [PINT, PINT, TEXT, PINT], [PINT, PBOOL]]):
        for symbol in [stem, stem + '_', stem + '__', stem.upper()]:
            function = getattr(reader.library, symbol)
            function.argtypes, function.restype = signature, None


def count(reader, dyna=0):
    flag = (INT * 3)(123456789, dyna, 123456789)
    output = (INT * 3)(123456789, -99, 123456789)
    reader.library.cpp_get_number_of_include_files(
        ct.cast(ct.byref(flag, ct.sizeof(INT)), PINT),
        ct.cast(ct.byref(output, ct.sizeof(INT)), PINT))
    assert list(flag) == [123456789, dyna, 123456789], list(flag)
    assert output[0] == output[2] == 123456789, list(output)
    return output[1]


def name(reader, index, size=2048, dyna=0):
    output = ct.create_string_buffer(b'!' * (size + 2), size + 2)
    pointer = ct.cast(ct.byref(output, 1), TEXT)
    reader.library.cpp_get_include_file_by_index(REF(INT(dyna)), REF(INT(index)), pointer, REF(INT(size)))
    assert output.raw[0:1] == output.raw[-1:] == b'!', output.raw
    return output.raw[1:-1]


def filled(reader, part):
    output = (ct.c_ubyte * 3)(173, 0, 173)
    reader.library.cpp_is_part_with_elements(REF(INT(part)), ct.cast(ct.byref(output, 1), PBOOL))
    assert output[0] == output[2] == 173, list(output)
    assert output[1] in [0, 1], list(output)
    return bool(output[1])


def dyna_load(reader, fixture, output):
    filename, destination = os.fsencode(fixture), os.fsencode(output)
    function = reader.library.cpp_read_dyna_and_convert
    function.argtypes, function.restype = [TEXT, PINT, PINT, TEXT, PINT], None
    error = INT(-1)
    function(filename, REF(INT(len(filename))), REF(error), destination, REF(INT(len(destination))))
    return error.value


def probe(args):
    reader = Reader(args.reader)
    configure(reader)
    work = args.output.parent
    source = ROOT / 'qa-tests/reader/rigid_parts/data'
    fixture = work / 'case.rad'
    long_name = 'long_include_' + 'x' * 80 + '.inc'
    (work / 'nested').mkdir()
    shutil.copy(source / 'common.inc', work / 'nested/mesh.inc')
    (work / long_name).write_text('#include nested/mesh.inc\n')
    deck = (source / 'ordinary_zero.rad').read_text().replace('common.inc', long_name)
    deck = deck.replace('/END', '/PART/20\nempty\n         1         1\n/END')
    offset = 1000 if args.submodel else 0
    if args.submodel:
        deck = deck.replace('#include', '//SUBMODEL/2/0\noffset\n      1000\n#include', 1)
        deck = deck.replace('/END', '//ENDSUB\n/END')
    fixture.write_text(deck)
    reader.load(fixture)
    expected_count = 3 if args.submodel else 2
    assert count(reader) == expected_count, count(reader)
    paths = [name(reader, i).decode().rstrip(' \0') for i in range(1, expected_count + 1)]
    assert sorted(Path(p).name for p in paths[-2:]) == sorted([long_name, 'mesh.inc']), paths
    assert all(Path(p).is_absolute() for p in paths[-2:]), paths
    assert {Path(p).resolve() for p in paths[-2:]} == {(work / long_name).resolve(), (work / 'nested/mesh.inc').resolve()}
    if args.submodel:
        assert paths[0] == '', paths
    # Both ABI calls must preserve the current entity and its next iterator position.
    reader.select(b'PART')
    reader.library.cpp_option_next()
    assert reader.integer('id') == 10 + offset
    assert filled(reader, 10 + offset) and not filled(reader, 20 + offset)
    assert reader.integer('id') == 10 + offset
    assert count(reader) == expected_count
    assert name(reader, 1, 8) == name(reader, 1)[:8]
    assert name(reader, 1, 0) == b''
    assert reader.integer('id') == 10 + offset
    reader.library.cpp_option_next()
    assert reader.integer('id') == 20 + offset
    result = {'native_includes': [Path(p).name for p in paths], 'parts': [True, False]}
    if args.submodel:
        args.output.write_text(json.dumps(result, indent=2))
        return
    bulk = reader.library.cpp_get_include_files_list
    bulk.argtypes, bulk.restype = [ct.POINTER(ct.c_void_p)], None
    pointers = (ct.c_void_p * 4)(173, None, None, 173)
    bulk(ct.cast(ct.byref(pointers, ct.sizeof(ct.c_void_p)), ct.POINTER(ct.c_void_p)))
    assert pointers[0] == pointers[3] == 173
    assert [Path(ct.string_at(pointers[i]).decode()).name for i in [1, 2]] == [Path(p).name for p in paths]

    # Reload without includes; old names and part handles must not survive.
    fixture.write_text(deck.replace('#include ' + long_name, (source / 'common.inc').read_text()))
    reader.load(fixture)
    assert count(reader) == 0
    assert filled(reader, 10) and not filled(reader, 20)
    assert not filled(reader, 9999) and not filled(reader, 0)
    for index in [-1, 0, 1, 3]:
        assert name(reader, index, 8) == b' ' * 8

    child, nested = work / 'child.k', work / 'nested.k'
    nested.write_text('*NODE\n2,1,0,0\n')
    child.write_text('*NODE\n1,0,0,0\n*INCLUDE\nnested.k\n')
    keyword = work / 'case.k'
    keyword.write_text('*KEYWORD\n*INCLUDE\nchild.k\n*END\n')
    assert dyna_load(reader, keyword, work / 'converted.rad') == 0
    assert count(reader, 1) == 2, count(reader, 1)
    paths = [name(reader, i, dyna=1).decode().rstrip(' \0') for i in [1, 2]]
    assert sorted(Path(p).name for p in paths) == ['child.k', 'nested.k'], paths
    assert {Path(p).resolve() for p in paths} == {child.resolve(), nested.resolve()}, paths
    result['keyword_includes'] = [Path(p).name for p in paths]
    keyword.write_text('*KEYWORD\n*INCLUDE_TRANSFORM\nchild.k\n' +
                       f'{0:10d}' * 7 + '\n' + f'{0:10d}' + '\n' +
                       f'{1.0:10g}' * 3 + '\n' + f'{0:10d}' + '\n*END\n')
    assert dyna_load(reader, keyword, work / 'transform-converted.rad') == 0
    assert count(reader, 1) == 2, count(reader, 1)
    paths = [name(reader, i, dyna=1).decode().rstrip(' \0') for i in [1, 2]]
    assert {Path(p).resolve() for p in paths} == {child.resolve(), nested.resolve()}, paths
    keyword.write_text('*KEYWORD\n*END\n')
    assert dyna_load(reader, keyword, work / 'empty-converted.rad') == 0
    assert count(reader, 1) == 0, 'Stale keyword includes after reload'
    reader.load(fixture)
    assert count(reader, 1) == 0 and name(reader, 1, 8, 1) == b' ' * 8
    assert dyna_load(reader, work / 'absent.k', work / 'failed.rad') != 0
    assert count(reader) == count(reader, 1) == 0
    assert not filled(reader, 10)
    args.output.write_text(json.dumps(result, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reader', required=True, type=lambda p: Path(p).resolve())
    parser.add_argument('--output', type=Path, help=argparse.SUPPRESS)
    parser.add_argument('--submodel', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.output:
        probe(args)
        return
    results = []
    for library in [args.reader]:
        with tempfile.TemporaryDirectory(prefix='opencourant-queries-') as temporary:
            output = Path(temporary) / 'queries.json'
            command = [sys.executable, str(Path(__file__).resolve()), '--reader', str(library),
                       '--output', str(output)]
            result = subprocess.run(command, cwd=temporary, capture_output=True, text=True, timeout=60)
            assert result.returncode == 0, result.stdout + result.stderr
            results.append(json.loads(output.read_text()))
            scope = 'native/keyword includes, bounds, parts, reload'
            print(f'PASS {library.name}: exports, selection, {scope}', flush=True)
    for library in [args.reader]:
        with tempfile.TemporaryDirectory(prefix='opencourant-submodel-queries-') as temporary:
            command = [sys.executable, str(Path(__file__).resolve()), '--reader', str(library),
                       '--output', str(Path(temporary) / 'queries.json'), '--submodel']
            result = subprocess.run(command, cwd=temporary, capture_output=True, text=True, timeout=30)
            assert result.returncode == 0, result.stdout + result.stderr
            print(f'PASS {library.name}: submodel include/part queries', flush=True)


if __name__ == '__main__':
    main()
