# Copyright (C) 2026 OpenCourant contributors
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Continue pre-removal Windows DP checkpoints with two and four MPI ranks."""

import argparse
import hashlib
import json
import os
from pathlib import Path
from zipfile import ZipFile

import numpy as np

from compare_decks import records
from test_shared_results import ROOT, run


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--engine', required=True, type=lambda p: Path(p).resolve())
    parser.add_argument('--output', required=True, type=lambda p: Path(p).resolve())
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    fixture = Path(__file__).parent/'stage7/windows_x64/old_multidomain_checkpoints.zip'
    env = os.environ.copy()
    env.update(OMP_NUM_THREADS='1', KMP_STACKSIZE='400m', I_MPI_FABRICS='shm',
               RAD_CFG_PATH=str(ROOT/'hm_cfg_files'))
    report = {'status': 'running', 'engine_sha256': hashlib.sha256(args.engine.read_bytes()).hexdigest(),
              'fixture_sha256': hashlib.sha256(fixture.read_bytes()).hexdigest(), 'cases': []}
    try:
        with ZipFile(fixture) as archive:
            for ranks in [2, 4]:
                folder = args.output/f'np{ranks}'
                folder.mkdir()
                names = [f'CRA2V44_0001_{rank:04}.rst' for rank in range(1, ranks+1)]
                names += [f'CRA2V44_{segment:04}.rad' for segment in [2, 3]]
                names += [f'reference{segment}.npz' for segment in [2, 3]]
                for name in names:
                    (folder/name).write_bytes(archive.read(f'np{ranks}/{name}'))
                for segment in [2, 3]:
                    output = run(['mpiexec', '-localonly', '-n', ranks, args.engine,
                                  '-i', f'CRA2V44_{segment:04}.rad', '-nt', '1'], folder, env)
                    (folder/'mpiexec.log').rename(folder/f'segment-{segment}.log')
                    assert 'NORMAL TERMINATION' in output
                    widths, values = records(folder/f'CRA2V44T{segment:02}')
                    old = np.load(folder/f'reference{segment}.npz')
                    np.testing.assert_array_equal(widths, old['widths'])
                    np.testing.assert_allclose(values, old['values'], rtol=1e-5, atol=1e-6)
                    assert len(values) > 1 and np.isfinite(values).all()
                    assert len(list(folder.glob(f'CRA2V44_{segment:04}_*.rst'))) == ranks
                    assert not list(folder.glob('*.h3d'))
                    np.savez_compressed(folder/f'current{segment}.npz', widths=widths, values=values)
                    report['cases'].append({'ranks': ranks, 'segment': segment, 'threads': 1,
                        'samples': len(values), 'final_time': float(values[-1, 0]),
                        'max_history_difference': float(np.max(np.abs(values-old['values'])))})
                    print(f'PASS old MPI checkpoint: {ranks} ranks, segment {segment}', flush=True)
        report['status'] = 'passed'
    except Exception as error:
        report.update(status='failed', error=repr(error))
        raise
    finally:
        (args.output/'report.json').write_text(json.dumps(report, indent=2)+'\n')


if __name__ == '__main__':
    main()
