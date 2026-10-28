# Copyright (C) 2026 OpenCourant contributors
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Continue frozen pre-removal checkpoints; no external model reader is loaded."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import struct
from zipfile import ZipFile

import numpy as np

from compare_decks import records
from test_shared_results import ROOT, run


def packed_pressure_flag(path):
    data = path.read_bytes()
    assert data.startswith(path.name.encode())
    # The existing restart header follows the filename and 100-integer title record.
    offset = len(path.name.encode()) + 100*4
    header_length = struct.unpack_from('>i', data, offset)[0]
    assert 0 < header_length <= 100
    return struct.unpack_from('>i', data, offset + 4 + header_length*4 + 293*4)[0]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--engine', required=True, type=lambda p: Path(p).resolve())
    parser.add_argument('--output', required=True, type=lambda p: Path(p).resolve())
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    env = os.environ.copy()
    env.update(RAD_CFG_PATH=str(ROOT/'hm_cfg_files'), OMP_NUM_THREADS='1', KMP_STACKSIZE='400m')
    report = {'engine_sha256': hashlib.sha256(args.engine.read_bytes()).hexdigest(), 'status': 'running', 'cases': []}
    try:
        fixtures = [
            ('baseline/windows_dp_smp/checkpoints.zip', [(role, enabled, f'restart-{role}-h3d-{enabled}')
                for role in ['v82', 'openreader'] for enabled in [0, 1]]),
            ('stage5/windows_dp_smp/retired_payload_checkpoints.zip', [('stage4', 1, 'retired-payloads'),
                ('stage4-pressure', 1, 'packed-pressure')])]
        for archive_path, cases in fixtures:
            with ZipFile(ROOT/'qa-tests/dependency_removal'/archive_path) as archive:
                for role, enabled, name in cases:
                    folder = args.output/name
                    folder.mkdir()
                    for filename in ['rigid_0001_0001.rst', 'rigid_0002.rad']:
                        (folder/filename).write_bytes(archive.read(name+'/'+filename))
                    if name == 'packed-pressure':
                        assert packed_pressure_flag(folder/'rigid_0001_0001.rst') == 11
                    schedule = folder/'rigid_0002.rad'
                    text = schedule.read_text()
                    schedule.write_text(text.split('/H3D/')[0])
                    assert not list(folder.glob('*.h3d'))
                    reference = folder/'oldT02'
                    reference.write_bytes(archive.read(name+'/rigidT02'))
                    old_widths, old_values = records(reference)
                    output = run([args.engine, '-i', 'rigid_0002.rad', '-nt', '1'], folder, env)
                    assert 'NORMAL TERMINATION' in output
                    widths, values = records(folder/'rigidT02')
                    np.testing.assert_array_equal(widths, old_widths)
                    np.testing.assert_allclose(values, old_values, rtol=1e-5, atol=1e-6)
                    assert (folder/'rigid_0002_0001.rst').stat().st_size > 0
                    if name == 'packed-pressure':
                        assert packed_pressure_flag(folder/'rigid_0002_0001.rst') == 10
                    assert not list(folder.glob('*.h3d'))
                    if enabled:
                        assert 'retired H3D output is not resumed' in output
                    report['cases'].append({'origin': role, 'h3d_enabled': bool(enabled),
                        'retired_output_resumed': False, 'samples': len(values), 'final_time': float(values[-1, 0]),
                        'max_history_difference': float(np.max(np.abs(values-old_values)))})
                    print(f'PASS pre-removal checkpoint continuation: {name}', flush=True)
                    if name in ['retired-payloads', 'packed-pressure']:
                        # Re-read a new checkpoint written after consuming the retired records.
                        (folder/'rigid_0003.rad').write_text(archive.read(name+'/rigid_0003.rad').decode().split('/H3D/')[0])
                        reference.write_bytes(archive.read(name+'/rigidT03'))
                        expected_widths, expected_values = records(reference)
                        output = run([args.engine, '-i', 'rigid_0003.rad', '-nt', '1'], folder, env)
                        assert 'NORMAL TERMINATION' in output
                        widths, values = records(folder/'rigidT03')
                        np.testing.assert_array_equal(widths, expected_widths)
                        np.testing.assert_allclose(values, expected_values, rtol=1e-5, atol=1e-6)
                        assert not list(folder.glob('*.h3d'))
                        report['cases'].append({'origin': role, 'segment': 3,
                            'retired_output_resumed': False, 'samples': len(values),
                            'max_history_difference': float(np.max(np.abs(values-expected_values)))})
                        if name == 'packed-pressure':
                            assert packed_pressure_flag(folder/'rigid_0003_0001.rst') == 10
                        print(f'PASS re-read current checkpoint after {name}', flush=True)

        report['status'] = 'passed'
    except Exception as error:
        report['status'], report['error'] = 'failed', repr(error)
        raise
    finally:
        (args.output/'report.json').write_text(json.dumps(report, indent=2)+'\n')


if __name__ == '__main__':
    main()
