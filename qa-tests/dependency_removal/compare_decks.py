# Copyright (C) 2026 OpenCourant contributors
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Compare current OpenReader model and Engine results with the frozen pre-removal baseline."""

import argparse
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
from zipfile import ZipFile

import numpy as np
from vortex_radioss.animtod3plot.RadiossTHReader import RadiossTHReader

from capture_baseline import ROOT, READER, sha256, write_json

sys.path.insert(0, str(READER / 'rigid_parts'))
from test_numerical import initializations, compare_initialization


def records(path):
    # shortcut: inspect packed records to avoid the installed reader's group-offset bug; upgrade when that reader is fixed.
    with contextlib.redirect_stdout(io.StringIO()):
        reader = RadiossTHReader(str(path))
    packed, columns, widths = reader.all_data, [], []
    assert packed.dtype.str == '>f4', packed.dtype
    markers = packed.view('>i4')
    cursor = 0
    while cursor < packed.shape[1]:
        size = int(markers[0, cursor])
        assert size > 0 and size % 4 == 0
        width = size // 4
        assert cursor + width + 1 < packed.shape[1]
        assert np.all(markers[:, cursor] == size)
        assert np.all(markers[:, cursor + width + 1] == size)
        columns.append(packed[:, cursor + 1:cursor + width + 1].astype(float))
        widths.append(width)
        cursor += width + 2
    assert cursor == packed.shape[1] and widths[0] == 1
    values = np.concatenate(columns, axis=1)
    assert np.isfinite(values).all() and len(values) > 1
    return widths, values


def capture_failures(binaries, output, environment):
    output.mkdir()
    results = []
    for case in ['missing-native', 'missing-keyword-include']:
        for role in ['openreader']:
            folder = output / (case + '-' + role)
            folder.mkdir()
            filename = 'absent_0000.rad' if case == 'missing-native' else 'case_0000.rad'
            if case == 'missing-keyword-include':
                text = (READER / 'contact_groups/case_0000.rad').read_text()
                (folder / filename).write_text(text.replace('contact.key', 'absent.key'))
            command = [str(binaries / f'starter-{role}.exe'), '-i', filename, '-np', '1']
            result = subprocess.run(command, env=environment, cwd=folder, capture_output=True,
                                    text=True, errors='replace', timeout=60)
            text = result.stdout + result.stderr
            (folder / 'console.log').write_text(text, encoding='utf-8')
            assert result.returncode != 0 and 'ERROR' in text.upper(), (case, role, text)
            assert not list(folder.glob('*.rst')), (case, role)
            results.append({'case': case, 'reader': role, 'command': command,
                            'exit_code': result.returncode, 'restart_files': 0,
                            'log_sha256': sha256(folder / 'console.log')})
            print(f'PASS rejected {case}/{role}: exit={result.returncode}', flush=True)
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binaries', required=True, type=lambda p: Path(p).resolve())
    parser.add_argument('--output', required=True, type=lambda p: Path(p).resolve())
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    models = [('accelerometer', ROOT / 'qa-tests/miniqa/ACCELEROMETRES/data/ACCELERO_0000.rad', True),
              ('friction', ROOT / 'qa-tests/miniqa/INTERF/INT_7/friction/data/FRICT41_0000.rad', True),
              ('shell3', ROOT / 'qa-tests/miniqa/COQUES3N/ct3a/data/CT3AV4_0000.rad', True),
              ('ale2d', ROOT / 'qa-tests/miniqa/ALE2D/bar2_v41/data/BAR2V41B_0000.rad', True),
              ('lsdyna-contact', ROOT / 'qa-tests/reader/contact_groups/case_0000.rad', False)]
    environment = os.environ.copy()
    environment.update(RAD_CFG_PATH=str(ROOT / 'hm_cfg_files'), OMP_NUM_THREADS='1',
                       KMP_STACKSIZE='400m')
    environment['PATH'] = os.pathsep.join([str(ROOT / 'exec'), environment.get('PATH', '')])
    baseline = ROOT / 'qa-tests/dependency_removal/baseline/windows_dp_smp'
    frozen = {row['name']: row for row in json.loads((baseline / 'models_report.json').read_text())['models']}
    report = {'oracle': 'frozen Stage 1 v82 model counts, initialization and raw histories', 'status': 'running', 'comparison_tolerance': {'rtol': 1e-5, 'atol': 1e-6}, 'models': []}
    try:
        for name, source, dynamics in models:
            row = {'name': name, 'source': str(source), 'engine_run': dynamics, 'variants': []}
            report['models'].append(row)
            original = {p.name: sha256(p) for p in source.parent.iterdir() if p.is_file()
                        and p.suffix.lower() in {'.rad', '.key', '.k', '.inc'}}
            row['source_hashes'] = original
            for role in ['openreader']:
                folder = args.output / (name + '-' + role)
                shutil.copytree(source.parent, folder)
                commands = [[args.binaries / f'starter-{role}.exe', '-i', source.name, '-np', '1']]
                if dynamics:
                    commands.append([ROOT / 'exec/engine_win64.exe', '-i',
                                     source.name.replace('_0000.rad', '_0001.rad'), '-nt', '1'])
                runs = []
                for index, command in enumerate(commands):
                    started = time.perf_counter()
                    result = subprocess.run([str(p) for p in command], env=environment, cwd=folder,
                                            capture_output=True, text=True, errors='replace', timeout=300)
                    log = result.stdout + result.stderr
                    (folder / ('starter.log' if index == 0 else 'engine.log')).write_text(log, encoding='utf-8')
                    runs.append({'command': [str(p) for p in command], 'exit_code': result.returncode,
                                 'elapsed_seconds': time.perf_counter() - started})
                    assert result.returncode == 0, (name, role, log[-2000:])
                    assert 'NORMAL TERMINATION' in log if index else re.search(r'\b0 ERROR\(S\)', log)
                listing = (folder / source.name.replace('.rad', '.out')).read_text(errors='replace')
                counts = dict((key, int(value)) for key, value in re.findall(
                    r'^\s*([A-Z][A-Z_0-9]+):[^\n]*?\s(-?\d+)\s*$', listing, re.M))
                assert counts.get('NUMNOD', 0) > 0 and counts.get('NPART', 0) > 0, counts
                bodies = initializations(listing) if 'RIGID BODY INITIALIZATION' in listing else {}
                variant = {'reader': role, 'runs': runs, 'model_counts': counts, 'rigid_bodies': bodies,
                           'warnings': re.findall(r'WARNING ID\s*:?\s*(\d+)', listing),
                           'errors': re.findall(r'ERROR ID\s*:?\s*(\d+)', listing),
                           'warning_total': int(re.findall(r'(\d+) WARNING\(S\)', listing)[-1]),
                           'error_total': int(re.findall(r'(\d+) ERROR\(S\)', listing)[-1]),
                           'listing_sha256': sha256(folder / source.name.replace('.rad', '.out')),
                           'restart_files': [{'name': p.name, 'bytes': p.stat().st_size, 'sha256': sha256(p)}
                                             for p in sorted(folder.glob('*.rst'))]}
                assert variant['restart_files'] and not variant['errors']
                values, widths = None, None
                if dynamics:
                    history = folder / (source.name.split('_0000')[0] + 'T01')
                    widths, values = records(history)
                    np.savez_compressed(folder / 'history_values.npz', values=values, record_widths=widths)
                    variant['history'] = {'samples': len(values), 'record_widths': widths,
                                          'final_time': float(values[-1, 0]), 'sha256': sha256(history)}
                row['variants'].append(variant)
                prior = next(item for item in frozen[name]['variants'] if item['reader'] == 'v82')
                assert original == frozen[name]['source_hashes'], (name, 'input changed since baseline')
                assert counts == prior['model_counts'], (name, counts, prior['model_counts'])
                assert {str(key) for key in bodies} == prior['rigid_bodies'].keys()
                for key, body in bodies.items():
                    old = prior['rigid_bodies'][str(key)]
                    for quantity in ['mass', 'center', 'diagonal', 'off_diagonal']:
                        np.testing.assert_allclose(body[quantity], old[quantity], rtol=1e-5, atol=1e-6)
                    assert len(body['nodes']) == old['nodes']['count']
                    assert hashlib.sha256(json.dumps(sorted(body['nodes'])).encode()).hexdigest() == old['nodes']['sorted_ids_sha256']
                if dynamics:
                    reference_file = folder / ('baseline-' + history.name)
                    with ZipFile(baseline / 'histories.zip') as archive:
                        reference_file.write_bytes(archive.read(name + '/v82/' + history.name))
                    old_widths, old_values = records(reference_file)
                    assert widths == old_widths
                    np.testing.assert_allclose(values, old_values, rtol=1e-5, atol=1e-6)
                    row['max_history_absolute_difference'] = float(np.max(np.abs(values - old_values)))
                variant['rigid_bodies'] = {key: {**body, 'nodes': {'count': len(body['nodes']),
                    'sorted_ids_sha256': hashlib.sha256(json.dumps(sorted(body['nodes'])).encode()).hexdigest()}}
                    for key, body in bodies.items()}
                print(f'PASS {name}/{role}: nodes={counts["NUMNOD"]}, engine={dynamics}', flush=True)
                write_json(args.output / 'report.json', report)
            assert original == {filename: sha256(source.parent / filename) for filename in original}
            row['status'] = 'passed'
        report['failed_input_checks'] = capture_failures(args.binaries, args.output / 'failures', environment)
        report['status'] = 'passed'
    except Exception as error:
        report['status'], report['error'] = 'failed', repr(error)
        raise
    finally:
        write_json(args.output / 'report.json', report)


if __name__ == '__main__':
    main()
