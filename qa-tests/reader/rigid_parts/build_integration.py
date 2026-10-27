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
"""Build isolated, bounds-checked Windows integration binaries from an existing Starter build."""

import argparse
import json
from pathlib import Path
import re
import subprocess


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--starter-build', required=True, type=lambda p: Path(p).resolve())
    parser.add_argument('--output', required=True, type=lambda p: Path(p).resolve())
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    modules = args.output / 'modules'
    modules.mkdir(exist_ok=True)
    commands = json.loads((args.starter_build / 'compile_commands.json').read_text())
    replacements = {}
    compiler = None
    for name in ['hm_create_rbodies_from_rigid_parts.F90', 'hm_evaluate_rbodies_from_rigid_parts.F90',
                 'rbody_part_modif.F90', 'hm_read_rbody.F', 'hm_rbodies_add_main_node.F90']:
        entry = next(entry for entry in commands if Path(entry['file']).name == name)
        command = entry['command']
        compiler = command.split()[0]
        previous_modules = re.search(r'/module:(\S+)', command).group(1)
        target = args.output / (name + '.obj')
        command = re.sub(r'/module:\S+', lambda _: f'/module:"{modules.as_posix()}" -I"{modules.as_posix()}" '
                         f'-I"{previous_modules}"', command)
        command = re.sub(r'/Fo\S+', f'/Fo"{target.as_posix()}"', command)
        command = re.sub(r'/Fd\S+', '', command)
        command = command.replace('-DHM_READER_NO_RBODIES_FROM_RIGID_PARTS', '')
        command += ' /Od /check:bounds /traceback'
        subprocess.run(command, cwd=entry['directory'], check=True)
        replacements[entry['output']] = target
    ninja = (args.starter_build / 'build.ninja').read_text()
    block = re.search(r'^build starter_win64.exe: Fortran_EXECUTABLE_LINKER[^\n]+\n(?:  [^\n]*\n)+', ninja, re.M).group()
    objects = block.splitlines()[0].split(': ', 1)[1].split()[1:]
    objects = objects[:next((i for i, item in enumerate(objects) if item.startswith('|')), len(objects))]
    flags = re.search(r'^  LINK_FLAGS = (.*)$', block, re.M).group(1)
    libraries = re.search(r'^  LINK_LIBRARIES = (.*)$', block, re.M).group(1)
    response = args.output / 'starter-objects.rsp'
    response.write_text('\n'.join('"' + str(replacements.get(obj, args.starter_build / obj)) + '"'
                                   for obj in objects) + '\n' + libraries + '\n')
    readers = [('openreader', ROOT / 'exec/open_reader_win64.lib'),
               ('v82', ROOT / 'extlib/hm_reader/win64/hm_reader_win64.lib')]
    for name, library in readers:
        link_flags = re.sub(r'\S*open_reader_win64\.lib', '"' + library.as_posix() + '"', flags)
        executable = args.output / f'starter-{name}.exe'
        subprocess.run(f'{compiler} /nologo @"{response}" {link_flags} /link /out:"{executable}"',
                       cwd=args.starter_build, check=True)
        driver = args.output / f'driver-{name}.exe'
        subprocess.run(f'{compiler} /nologo /Od /check:bounds /traceback /module:"{modules}" -I"{modules}" '
                       f'"{HERE / "integration_driver.F90"}" '
                       f'"{args.output / "hm_create_rbodies_from_rigid_parts.F90.obj"}" '
                       f'"{args.output / "hm_evaluate_rbodies_from_rigid_parts.F90.obj"}" '
                       f'"{library}" /exe:"{driver}"', cwd=args.output, check=True)
    print('PASS isolated integration builds', flush=True)


if __name__ == '__main__':
    main()
