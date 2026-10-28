# Copyright (C) 2026 OpenCourant contributors
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Check the patched release GUI's environment without starting a graphical session."""

import argparse
import ast
import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--gui', required=True, type=Path)
    args = parser.parse_args()
    source = (args.gui / 'runopenradioss.py').read_text()
    tree = ast.parse(source)
    method = next(node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name == 'environment')
    job_source = (args.gui / 'job_window.py').read_text()
    job_tree = ast.parse(job_source)
    assert not any(isinstance(node, ast.FunctionDef) and node.name == 'h3d_job' for node in ast.walk(job_tree))
    assert 'h3d_button' not in job_source and "f.write('/H3D')" not in job_source
    assert "f.write('/ANIM')" in job_source
    assert 'RAD_H3D_PATH' not in source and '"hm_reader"' not in source and '"h3d"' not in source
    for arch, platform, cpu in [('win64', 'Windows', 'AMD64'), ('linux64', 'Linux', 'x86_64'), ('linuxa64', 'Linux', 'aarch64')]:
        scope = {'os': os, 'current_platform': platform, 'cpu': cpu}
        exec(compile(ast.Module(body=[method], type_ignores=[]), 'packaged GUI environment', 'exec'), scope)
        for ranks in [1, 2]:
            state = SimpleNamespace(np=str(ranks), nt='2', arch=arch, mpi_path='mpi-runtime', openradioss_path='solver-root')
            with patch.dict(os.environ, {'PATH': 'host-bin', 'LD_LIBRARY_PATH': 'host-libs'}, clear=True):
                env = scope['environment'](state)
            assert env['RAD_CFG_PATH'] == os.path.join('solver-root', 'hm_cfg_files')
            assert env['OMP_NUM_THREADS'] == '2'
            assert 'RAD_H3D_PATH' not in env
            variable = 'PATH' if arch == 'win64' else 'LD_LIBRARY_PATH'
            assert os.path.join('solver-root', 'exec') in env[variable]
            if arch == 'win64':
                assert os.path.join('solver-root', 'extlib', 'intelOneAPI_runtime', 'win64') in env['PATH']
            else:
                assert os.path.join('solver-root', 'extlib', 'runtime', arch) in env['LD_LIBRARY_PATH']
                assert 'host-libs' in env['LD_LIBRARY_PATH']
            if ranks == 2:
                assert 'mpi-runtime' in env['PATH']
                assert env['I_MPI_ROOT' if arch == 'win64' else 'OPAL_PREFIX'] == 'mpi-runtime'
    print('PASS packaged GUI: six serial/MPI platform environments retain OpenReader and native runtimes; H3D control removed')


if __name__ == '__main__':
    main()
