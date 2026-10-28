# Copyright (C) 2026 OpenCourant contributors
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Check that MiniQA reports integer mismatches without losing its tolerance rules."""

import contextlib
import io
import json
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'qa_tools'))
from verify_results import compare, verify_integer_tolerance, last_checksum
import execute_solver
from unittest.mock import patch
import tempfile


def main():
    root = Path(__file__).resolve().parents[2]
    legacy = (root/'qa-tests/scripts/or_QA.files_1miniqa').read_text()
    for test, folder in [('1.90', 'hexa8'), ('1.91', 'tetra4')]:
        section = legacy.split('#'+test+'\n', 1)[1].split('\ngo -engine', 1)[0]
        rules = json.loads((root/'qa-tests/miniqa/INTERF/INT_25'/folder/'data/test_files.json').read_text())
        for field, kind, value in re.findall(r'^local\s+(\S+)\s+(\S+)\s+(\S+)', section, re.M):
            assert rules['TOL_'+field] == ['Abs_tolerance' if kind == 'Int_Tolerance' else 'Diff_tolerance', value]
    assert verify_integer_tolerance('CYCLE', 100, 101, [])[0] == 0
    assert verify_integer_tolerance('CYCLE', 100, 101, {})[0] == 0
    assert verify_integer_tolerance('CYCLE', 100, 101, {'TOL_CYCLE': ['Abs_tolerance', 2]})[0] == 1
    assert verify_integer_tolerance('CYCLE', 100, 102, {'TOL_CYCLE': ['Abs_tolerance', 2]})[0] == 0
    with contextlib.redirect_stdout(io.StringIO()) as output:
        assert compare(['CYCLE'], {'CYCLE': '100'}, {'CYCLE': '101'}, [], {}, 'dp') == 1
    assert 'CYCLE' in output.getvalue() and 'Ref: 100' in output.getvalue()
    with contextlib.redirect_stdout(io.StringIO()):
        assert compare(['CYCLE'], {'CYCLE': '100'}, {'CYCLE': '102'},
                       {'TOL_CYCLE': ['Abs_tolerance', 2]}, {}, 'dp') == 1
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory)/'engine.out'
        path.write_text('NORMAL TERMINATION\n')
        try:
            last_checksum(path)
        except ValueError:
            pass
        else:
            raise AssertionError('A missing checksum must fail the parallel arithmetic gate')
        path.write_text('CHECKSUM: 123\nCHECKSUM: 0\n')
        assert last_checksum(path) == '0'
    with patch.object(execute_solver, 'arch', 'win64'):
        command = execute_solver.get_engine_command('engine.exe', 'impi', 'model_0001.rad', 2)
        assert command.startswith('mpiexec -localonly -np 2 engine.exe -i model_0001.rad')
        assert '-delegate' not in command
    print('PASS MiniQA diagnostics, missing checksums, local MPI and legacy TYPE25 tolerance rules')


if __name__ == '__main__':
    main()
