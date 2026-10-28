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
"""Keep generic contact sets as surfaces and lines; preserve typed groups and reloads."""

import argparse
import ctypes as ct
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from rigid_parts.test_reader_contract import Reader, ROOT, INT, REF, PINT, PBOOL, TEXT


HERE = Path(__file__).resolve().parent
KINDS = [b'/SURF', b'/LINE', b'/GRNOD', b'/GRPART']


def usage(reader, identifier):
    function = reader.library.cpp_group_is_used
    function.argtypes, function.restype = [TEXT, PINT, PINT, PBOOL], None
    result = []
    for kind in KINDS:
        used = ct.c_bool()
        function(kind, REF(INT(len(kind))), REF(INT(identifier)), REF(used))
        result.append(used.value)
    return result


def probe(args):
    reader = Reader(args.reader)
    fixture = Path.cwd() / 'case_0000.rad'
    if args.worker == 'native':
        reader.load(HERE / 'rigid_parts/data/existing.rad')
        assert usage(reader, 50) == [False, False, True, False]
        return
    reader.load(fixture)
    reader.select(b'/INTER/TYPE25')
    reader.library.cpp_option_next()
    group = reader.integer('surf_ID1')
    assert group and reader.integer('id') == 1
    assert usage(reader, group) == [True, True, False, False]
    assert usage(reader, 10) == [False] * 4
    assert reader.integer('id') == 1, 'Group-use lookup moved the current entity'
    if args.worker == 'reload':
        reader.load(HERE / 'rigid_parts/data/existing.rad')
        assert usage(reader, group) == [False] * 4, 'Stale contact use survived reload'
        assert usage(reader, 50) == [False, False, True, False]
        reader.load(fixture)
        assert usage(reader, group) == [True, True, False, False]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reader', required=True, type=lambda p: Path(p).resolve())
    parser.add_argument('--starter', type=lambda p: Path(p).resolve())
    parser.add_argument('--worker', choices=['contact', 'native', 'reload'], help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker:
        probe(args)
        return
    for library in [args.reader]:
        cases = ['contact', 'native', 'reload']
        for case in cases:
            with tempfile.TemporaryDirectory(prefix='opencourant-contact-groups-') as temporary:
                work = Path(temporary)
                for path in (HERE / 'contact_groups').iterdir():
                    shutil.copy2(path, work / path.name)
                command = [sys.executable, str(Path(__file__).resolve()), '--reader', str(library),
                           '--worker', case]
                result = subprocess.run(command, cwd=work, capture_output=True, text=True, timeout=30)
                assert result.returncode == 0, result.stdout + result.stderr
                print(f'PASS {library.name}: {case} group use', flush=True)
    if args.starter:
        with tempfile.TemporaryDirectory(prefix='opencourant-contact-starter-') as temporary:
            work = Path(temporary)
            for path in (HERE / 'contact_groups').iterdir():
                shutil.copy2(path, work / path.name)
            env = os.environ.copy()
            env.update(RAD_CFG_PATH=str(ROOT / 'hm_cfg_files'), OMP_NUM_THREADS='1', KMP_STACKSIZE='400m')
            env['PATH'] = str(args.reader.parent) + os.pathsep + env['PATH']
            result = subprocess.run([str(args.starter), '-i', 'case_0000.rad', '-np', '1'],
                                    cwd=work, env=env, capture_output=True, text=True, timeout=60)
            listing = (work / 'case_0000.out').read_text(errors='replace')
            assert result.returncode == 0 and '0 ERROR(S)' in listing, result.stdout + result.stderr + listing[-3000:]
            assert any(p.stat().st_size > 0 for p in work.glob('*.rst')), 'No restart generated'
            print('PASS Starter TYPE25 ALL-minus-part-set contact restart', flush=True)


if __name__ == '__main__':
    main()
