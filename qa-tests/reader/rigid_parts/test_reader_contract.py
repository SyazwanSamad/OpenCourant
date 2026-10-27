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
"""Check the Irigid reference contract; run each native reader in a fresh process."""

import argparse
import ctypes as ct
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
INT = ct.c_int
REF = ct.byref
PINT = ct.POINTER(INT)
PBOOL = ct.POINTER(ct.c_bool)
TEXT = ct.c_char_p


class Reader:
    def __init__(self, library):
        os.environ['RAD_CFG_PATH'] = str(ROOT / 'hm_cfg_files')
        if os.name == 'nt':
            self.dll_directory = os.add_dll_directory(str(library.parent))
        self.library = ct.CDLL(str(library))
        signatures = {
            'hm_reader_variables': [PINT, PINT],
            'cpp_build_model_inc': [TEXT, PINT, PINT, PINT, TEXT, PINT],
            'cpp_option_count': [TEXT, PINT, PINT],
            'cpp_option_start': [TEXT, PINT],
            'cpp_option_next': [],
            'cpp_get_intv': [TEXT, PINT, PINT, PINT, PBOOL, PINT],
            'cpp_get_intv_index': [TEXT, PINT, PINT, PINT, PINT, PBOOL, PINT],
            'cpp_get_intv_2index': [TEXT, PINT, PINT, PINT, PINT, PBOOL, PINT, PINT],
            'cpp_get_floatv_only': [TEXT, PINT, ct.POINTER(ct.c_double), PBOOL, PINT, PINT, PINT],
            'cpp_get_string_index': [TEXT, PINT, TEXT, PINT, PINT, PBOOL],
            'cpp_evaluate_rbodies_number_from_rigid_parts': [PINT],
            'cpp_create_rbodies_from_rigid_parts': [PINT, PINT],
            'cpp_add_rbody_main_node': [PINT],
            'CPP_GET_MESSAGE_NUMBER_RADIOSS': [PINT],
            'CPP_GET_MESSAGE_RADIOSS': [PINT, PINT, PINT, TEXT, TEXT, PINT, TEXT, TEXT],
        }
        for name, signature in signatures.items():
            function = getattr(self.library, name)
            function.argtypes = signature
            function.restype = None

    def count(self, kind):
        value = INT()
        self.library.cpp_option_count(kind, REF(INT(len(kind))), REF(value))
        return value.value

    def select(self, kind):
        self.library.cpp_option_start(kind, REF(INT(len(kind))))

    def integer(self, key, index=None, index2=None):
        key = key.encode()
        value, submodel, value_type = INT(), INT(), INT()
        available = ct.c_bool()
        args = [key, REF(INT(len(key))), REF(value)]
        name = 'cpp_get_intv'
        if index is not None:
            name += '_index' if index2 is None else '_2index'
            args.append(REF(INT(index)))
        args.extend([REF(submodel), REF(available), REF(value_type)])
        if index2 is not None:
            args.append(REF(INT(index2)))
        getattr(self.library, name)(*args)
        return value.value if available.value else None

    def real(self, key):
        key = key.encode()
        value, available = ct.c_double(), ct.c_bool()
        dimensions = [INT() for _ in range(3)]
        self.library.cpp_get_floatv_only(key, REF(INT(len(key))), REF(value), REF(available),
                                        *(REF(dimension) for dimension in dimensions))
        return value.value if available.value else None

    def string_at(self, key, index):
        key = key.encode()
        value, available = ct.create_string_buffer(2048), ct.c_bool()
        self.library.cpp_get_string_index(key, REF(INT(len(key))), value, REF(INT(index)),
                                           REF(INT(len(value))), REF(available))
        return value.value.decode('utf-8').rstrip()

    def entities(self, kind, integers, reals=()):
        count = self.count(kind)
        self.select(kind)
        entities = []
        for _ in range(count):
            self.library.cpp_option_next()
            row = {key: self.integer(key) for key in integers}
            row.update({key: self.real(key) for key in reals})
            entities.append(row)
        return entities

    def check_messages(self):
        count = INT()
        self.library.CPP_GET_MESSAGE_NUMBER_RADIOSS(REF(count))
        for index in range(1, count.value + 1):
            message_id, severity, line = INT(), INT(), INT()
            buffers = [ct.create_string_buffer(32768) for _ in range(4)]
            self.library.CPP_GET_MESSAGE_RADIOSS(REF(INT(index)), REF(message_id), REF(severity),
                                               buffers[0], buffers[1], REF(line), buffers[2], buffers[3])
            if message_id.value and severity.value:
                raise RuntimeError(f'Reader message {message_id.value}: {buffers[0].value!r}, '
                                   f'line {line.value}, {buffers[2].value!r}')

    def load(self, fixture):
        error, version, includes = INT(), INT(2612), INT()
        self.library.hm_reader_variables(REF(error), REF(version))
        if error.value:
            raise RuntimeError('Reader configuration initialization failed')
        filename = os.fsencode(fixture)
        path = os.fsencode(str(fixture.parent) + os.sep)
        self.library.cpp_build_model_inc(filename, REF(INT(len(filename))), REF(error),
                                         REF(includes), path, REF(INT(len(path))))
        if error.value:
            raise RuntimeError(f'Model loading failed: {error.value}')
        self.check_messages()

    def snapshot(self, fixture, metadata=False):
        self.load(fixture)
        parts = self.entities(b'PART', ['id', 'IRIGID'])
        before = self.entities(b'/RBODY', ['id'])
        counts = (INT * len(parts))()
        self.library.cpp_evaluate_rbodies_number_from_rigid_parts(counts)
        total = sum(counts)
        if any(count < 0 for count in counts) or total > 100:
            raise RuntimeError(f'Invalid conversion counts: {list(counts)}')
        mapping, ids = (INT * total)(), (INT * total)()
        self.library.cpp_create_rbodies_from_rigid_parts(mapping, ids)
        self.check_messages()
        bodies = self.entities(b'/RBODY', ['id', 'node_ID', 'grnd_ID', 'sens_ID', 'Skew_ID', 'ICoG', 'Ispher'],
                               ['Mass', 'Jxx', 'Jyy', 'Jzz', 'Jxy', 'Jyz', 'Jxz'])
        sets = []
        count = self.count(b'/SET')
        self.select(b'/SET')
        for _ in range(count):
            self.library.cpp_option_next()
            sets.append({'id': self.integer('id'), 'clauses': self.integer('clausesmax'),
                         'key': self.string_at('KEY_type', 1),
                         'items': self.integer('idsmax', 1), 'part': self.integer('ids', 1, 1)})
        added_nodes = []
        self.select(b'/RBODY')
        for _ in bodies:
            self.library.cpp_option_next()
            if self.integer('node_ID') == 0:
                added = INT()
                self.library.cpp_add_rbody_main_node(REF(added))
                added_nodes.append(added.value)
        main_nodes = self.entities(b'/RBODY', ['id', 'node_ID'])
        result = {'parts': parts, 'existing_body_ids': [row['id'] for row in before],
                'counts': list(counts), 'mapping': list(mapping), 'ids': list(ids),
                'bodies': bodies, 'sets': sets, 'added_main_nodes': added_nodes, 'main_nodes': main_nodes}
        if metadata:
            result['ownership'] = {}
            for kind in [b'PART', b'/RBODY', b'/SET']:
                rows = []
                self.select(kind)
                for _ in range(self.count(kind)):
                    self.library.cpp_option_next()
                    rows.append({**{key: self.integer(key) for key in ['id', 'include', 'submodel', 'unitid']},
                                 'name': self.string_at('name', 1)})
                result['ownership'][kind.decode()] = rows
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reader', type=Path, required=True)
    parser.add_argument('--openreader', action='store_true', help='Require explicit rejection of unimplemented IRIGID=2')
    parser.add_argument('--guard', type=Path, help='Optional compiled guard_driver executable')
    parser.add_argument('--case', type=Path, help=argparse.SUPPRESS)
    parser.add_argument('--output', type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    args.reader = args.reader.resolve()
    if args.case:
        snapshot = Reader(args.reader).snapshot(args.case.resolve())
        args.output.write_text(json.dumps(snapshot, indent=2) + '\n', encoding='utf-8')
        return
    expected = json.loads((HERE / 'expected.json').read_text(encoding='utf-8'))
    with tempfile.TemporaryDirectory(prefix='opencourant-irigid-') as temporary:
        output = Path(temporary) / 'snapshot.json'
        environment = os.environ.copy()
        environment['RAD_CFG_PATH'] = str(ROOT / 'hm_cfg_files')
        environment['PATH'] = str(args.reader.parent) + os.pathsep + environment.get('PATH', '')
        for name, case in expected['cases'].items():
            fixture = HERE / 'data' / (name + '.rad')
            command = [sys.executable, str(Path(__file__).resolve()), '--reader', str(args.reader),
                       '--case', str(fixture), '--output', str(output)]
            result = subprocess.run(command, capture_output=True, text=True, timeout=30, cwd=temporary)
            rejection = case.get('openreader_error') if args.openreader else None
            if rejection:
                assert result.returncode == 1 and rejection in result.stderr, (name, result.stdout, result.stderr)
            elif result.returncode:
                raise RuntimeError(f'{name}: reader failed ({result.returncode})\n{result.stdout}{result.stderr}')
            else:
                actual = json.loads(output.read_text(encoding='utf-8'))
                if actual != case['snapshot']:
                    raise AssertionError(f'{name}: reference mismatch\n{json.dumps(actual, indent=2)}')
            if args.guard:
                result = subprocess.run([str(args.guard.resolve()), str(fixture)], env=environment,
                                        capture_output=True, text=True, timeout=30, cwd=temporary)
                required = case['guard_error']
                if result.returncode != (2 if required else 0):
                    raise AssertionError(f'{name}: unexpected guard exit {result.returncode}\n'
                                         f'{result.stdout}{result.stderr}')
                if required and required not in result.stdout:
                    raise AssertionError(f'{name}: missing part diagnostic\n{result.stdout}')
                if not required and 'guard accepted ordinary parts' not in result.stdout:
                    raise AssertionError(f'{name}: ordinary-part path was not reached')
            label = 'unsupported mode rejected' if rejection else 'reference'
            print(f'PASS {name} ({label}' + (' + guard)' if args.guard else ')'))


if __name__ == '__main__':
    main()
