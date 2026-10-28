# Copyright (C) 2026 OpenCourant contributors
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Run the current Windows OpenReader regression suites; preserve frozen pre-removal evidence."""

import argparse
import ctypes as ct
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone


ROOT = Path(__file__).resolve().parents[2]
READER = ROOT / 'qa-tests/reader'
sys.path.insert(0, str(READER / 'rigid_parts'))


def sha256(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')


def scan_requests(path, text):
    """Retain mixed-card context for review; do not guess historical field layouts."""
    lines = text.splitlines()
    records = []
    for index, line in enumerate(lines):
        stripped = line.strip()
        direct = re.match(r'^/H3D(?:/|\s|$)', stripped, re.I)
        mixed = re.match(r'^/(?:MONVOL/FVMBAG[^/]*|STOP|REPORT)(?:/|\s|$)', stripped, re.I)
        mention = re.search(r'(?i)(?<![a-z0-9_])(?:(?:lib)?h3d\w*|IH3D\w*|RAD_H3D_PATH|Hyper3D\w*)', line)
        if direct or mixed or mention:
            records.append({'path': path, 'line': index + 1,
                            'kind': 'h3d_directive' if direct else 'mixed_card_review' if mixed else 'text_reference',
                            'text': line, 'following_lines': lines[index + 1:index + 5] if direct or mixed else []})
    return records


def self_check():
    records = scan_requests('fixture.rad', '# /H3D/DT\n/H3D/DT\n0 .1\n/STOP/LSENS\n1\n0 0 0 0 0 1 0\n')
    assert [r['kind'] for r in records] == ['text_reference', 'h3d_directive', 'mixed_card_review']
    assert records[1]['line'] == 2 and records[2]['following_lines'][1] == '0 0 0 0 0 1 0'
    assert not scan_requests('fixture.F', 'ISPH3D = 1\n')
    assert len(scan_requests('launch.sh', 'libh3dwriter.so\n$h3dtoxmlexec\n')) == 2


def capture_restarts(binaries, output, run):
    from test_numerical import make_deck, reals, history_records, initialization, compare_initialization, XYZ
    import numpy as np
    output.mkdir()
    results, previous = [], None
    for role in ['openreader']:
        for enabled in [False]:
            folder = output / f'restart-{role}-h3d-{int(enabled)}'
            folder.mkdir()
            make_deck(folder, 'force', True)
            engine_input = folder / 'rigid_0001.rad'
            schedule = engine_input.read_text().replace(reals(0.1) + '\n/PRINT', reals(0.05) + '\n/PRINT')
            engine_input.write_text(schedule, encoding='ascii')
            (folder / 'rigid_0002.rad').write_text(schedule.replace('/RUN/rigid/1', '/RUN/rigid/2').replace(reals(0.05) + '\n/PRINT', reals(0.1) + '\n/PRINT'), encoding='ascii')
            run(folder.name + '-starter', [binaries / f'starter-{role}.exe', '-i', 'rigid_0000.rad', '-np', '1'], cwd=folder)
            first = run(folder.name + '-engine1', [ROOT / 'exec/engine_win64.exe', '-i', engine_input.name, '-nt', '1'], cwd=folder)
            assert 'NORMAL TERMINATION' in first, folder
            checkpoint = folder / 'rigid_0001_0001.rst'
            assert checkpoint.stat().st_size > 0
            second = run(folder.name + '-engine2', [ROOT / 'exec/engine_win64.exe', '-i', 'rigid_0002.rad', '-nt', '1'], cwd=folder)
            assert 'NORMAL TERMINATION' in second, folder
            assert (folder / 'rigid_0002_0001.rst').stat().st_size > 0
            h3d = list(folder.glob('*.h3d'))
            assert bool(h3d) == enabled, (folder, h3d)
            # Each Engine segment writes its own Tnn; T01 alone ends at the first checkpoint.
            times, globals_data, groups = history_records(folder / 'rigidT02', [48, 10, 6])
            assert len(times) >= 20 and times[0] >= 0.049 and times[-1] >= 0.1 - 1.1 * 0.001
            nodes, body = groups[0].reshape(-1, 8, 6), groups[1]
            expected = np.broadcast_to(XYZ, nodes[:, :, 3:6].shape).copy()
            expected[:, :, 0] += 0.5 * times[:, None]**2
            np.testing.assert_allclose(nodes[:, :, 3:6], expected, atol=3e-5)
            np.testing.assert_allclose(body[:, 3], times, atol=3e-4)
            np.testing.assert_allclose(globals_data['kinetic_energy'], 0.5 * times**2, atol=3e-5)
            np.savez_compressed(folder / 'continuation_values.npz', time=times, nodes=nodes, body=body,
                                **globals_data)
            if previous is not None:
                for actual, prior in zip((times, nodes, body), previous):
                    np.testing.assert_allclose(actual, prior, rtol=1e-5, atol=1e-6)
            previous = times, nodes, body
            listing = (folder / 'rigid_0000.out').read_text(errors='replace')
            results.append({'reader': role, 'h3d_enabled': enabled, 'initialization': initialization(listing),
                            'checkpoint_sha256': sha256(checkpoint), 'checkpoint_bytes': checkpoint.stat().st_size,
                            'history_samples': len(times), 'final_time': float(times[-1]),
                            'max_velocity_error': float(np.max(np.abs(body[:, 3] - times))),
                            'max_position_error': float(np.max(np.abs(nodes[:, :, 3:6] - expected))),
                            'max_energy_error': float(np.max(np.abs(globals_data['kinetic_energy'] - 0.5 * times**2))),
                            'h3d_files': [{'name': p.name, 'bytes': p.stat().st_size, 'sha256': sha256(p)} for p in h3d]})
            write_json(output / 'report.json', results)
            print(f'PASS continued checkpoint {role}/h3d={enabled}', flush=True)
    for item in results[1:]:
        compare_initialization(item['initialization'], results[0]['initialization'])
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binaries', required=True, type=lambda p: Path(p).resolve())
    parser.add_argument('--output', required=True, type=lambda p: Path(p).resolve())
    parser.add_argument('--starter-build', type=lambda p: Path(p).resolve(),
                        default=ROOT / 'starter/cbuild_starter_win64_ninja')
    args = parser.parse_args()
    self_check()
    args.output.mkdir(parents=True, exist_ok=False)
    logs = args.output / 'logs'
    logs.mkdir()
    report = {'captured_utc': datetime.now(timezone.utc).isoformat(), 'platform': platform.platform(),
              'python': sys.version, 'scope': 'Windows x64, double precision, SMP; integration conversion enabled',
              'status': 'running', 'runs': []}
    environment = os.environ.copy()
    environment.update(RAD_CFG_PATH=str(ROOT / 'hm_cfg_files'), OMP_NUM_THREADS='1',
                       KMP_STACKSIZE='400m')
    environment['PATH'] = os.pathsep.join([str(ROOT / 'exec'), environment.get('PATH', '')])

    def run(name, command, cwd=ROOT, expected=0, timeout=600):
        command = [str(value) for value in command]
        started = time.perf_counter()
        try:
            result = subprocess.run(command, cwd=cwd, env=environment, capture_output=True,
                                    text=True, errors='replace', timeout=timeout)
            output = result.stdout + result.stderr
            code = result.returncode
        except subprocess.TimeoutExpired as error:
            output = str(error)
            code = None
        (logs / (name + '.log')).write_text(output, encoding='utf-8')
        row = {'name': name, 'command': command, 'cwd': str(cwd), 'exit_code': code,
               'expected_exit_code': expected, 'elapsed_seconds': time.perf_counter() - started,
               'pass_lines': sum(line.startswith('PASS ') for line in output.splitlines()),
               'status': 'passed' if code == expected else 'failed', 'log': 'logs/' + name + '.log'}
        report['runs'].append(row)
        write_json(args.output / 'report.json', report)
        print(f"{row['status'].upper()} {name}: exit={code}, checks={row['pass_lines']}", flush=True)
        return output

    try:
        report['commit'] = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
        report['working_tree_dirty'] = bool(subprocess.check_output(['git', 'status', '--short'], cwd=ROOT, text=True).strip())
        tracked = subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT).decode().split('\0')
        manifest, inventory = [], []
        for name in sorted(filter(None, tracked)):
            path = ROOT / name
            if name.startswith(('hm_cfg_files/', 'qa-tests/reader/', 'qa-tests/miniqa/')) and path.is_file():
                manifest.append({'path': name, 'bytes': path.stat().st_size, 'sha256': sha256(path)})
            if path.suffix.lower() in {'.rad', '.key', '.k', '.cfg', '.yml', '.yaml', '.json', '.sh', '.bash', '.bat', '.def', '.py', '.pl', '.md', '.txt', '.constants'} or (name.startswith('qa-tests/') and not path.suffix):
                if not path.is_file():
                    continue
                inventory.extend(scan_requests(name, path.read_text(encoding='utf-8', errors='replace')))
        write_json(args.output / 'input_manifest.json', manifest)
        write_json(args.output / 'h3d_inventory.json', inventory)
        report['input_manifest_sha256'] = sha256(args.output / 'input_manifest.json')
        report['configuration_files'] = sum(row['path'].startswith('hm_cfg_files/') for row in manifest)
        report['configuration_tree_sha256'] = hashlib.sha256(json.dumps(
            [r for r in manifest if r['path'].startswith('hm_cfg_files/')], sort_keys=True).encode()).hexdigest()
        report['tracked_h3d_directives'] = [r for r in inventory if r['kind'] == 'h3d_directive']
        report['mixed_cards_to_review'] = [r for r in inventory if r['kind'] == 'mixed_card_review']
        binary_paths = [ROOT / 'exec/open_reader_win64.dll', ROOT / 'exec/starter_win64.exe',
                        ROOT / 'exec/engine_win64.exe',
                        *sorted(args.binaries.glob('*.exe'))]
        report['binaries'] = [{'path': str(p.relative_to(ROOT)), 'bytes': p.stat().st_size, 'sha256': sha256(p)}
                              for p in binary_paths]
        report['reader_build_ids'] = {}
        for path in [binary_paths[0]]:
            with os.add_dll_directory(str(path.parent)):
                library = ct.CDLL(str(path))
                function = library.open_reader_build_id
                function.argtypes, function.restype = [ct.c_char_p, ct.POINTER(ct.c_int), ct.POINTER(ct.c_int)], None
                buffer, length, copied = ct.create_string_buffer(256), ct.c_int(256), ct.c_int()
                function(buffer, ct.byref(length), ct.byref(copied))
                assert 0 <= copied.value < 256
                report['reader_build_ids'][path.name] = buffer.value.decode()
        for name, build in [('starter', args.starter_build),
                            ('engine', 'engine/cbuild_engine_win64_ninja')]:
            cache = ROOT / build / 'CMakeCache.txt'
            report.setdefault('build_settings', {})[name] = [line for line in cache.read_text().splitlines()
                if re.match(r'(?:CMAKE_(?:BUILD_TYPE|Fortran_COMPILER|C_COMPILER|CXX_COMPILER|EXE_LINKER_FLAGS)|precision|MPI|debug|USE_OPEN_READER|HM_READER_\w+):', line)]
        for tool in ['ifx', 'icx', 'cmake']:
            run(tool + '-version', [tool, '--version'])
        opened = binary_paths[0]
        commands = [
            ('reader-build', [ROOT / 'qa-tests/dependency_removal/test_reader_build.py']),
            ('starter-api', [READER / 'test_starter_api.py', '--reader', opened]),
            ('reader-open-contract', [READER / 'rigid_parts/test_reader_contract.py', '--reader', opened]),
            ('reader-api', [READER / 'test_model_queries.py', '--reader', opened]),
            ('reader-loading', [READER / 'test_model_loading.py', '--reader', opened, '--starter', ROOT / 'exec/starter_win64.exe']),
            ('reader-contact', [READER / 'test_contact_groups.py', '--reader', opened, '--starter', ROOT / 'exec/starter_win64.exe']),
            ('reader-conversion', [READER / 'rigid_parts/test_openreader_conversion.py', '--reader', opened]),
            ('starter-integration', [READER / 'rigid_parts/test_starter_integration.py', '--reader', opened, '--binaries', args.binaries]),
            ('numerical', [READER / 'rigid_parts/test_numerical.py', '--binaries', args.binaries, '--engine', ROOT / 'exec/engine_win64.exe', '--output', args.output / 'numerical']),
        ]
        for name, command in commands:
            run(name, [sys.executable, *command])
        run('mode2-numerical', [sys.executable, READER / 'rigid_parts/test_mode2_numerical.py',
            '--binaries', args.binaries, '--engine', ROOT / 'exec/engine_win64.exe', '--output', args.output / 'mode2-numerical'])
        snapshots = args.output / 'reader_snapshots'
        snapshots.mkdir()
        expected = json.loads((READER / 'rigid_parts/expected.json').read_text())
        for role, library in [('openreader', opened)]:
            for case, contract in expected['cases'].items():
                target = snapshots / f'{role}-{case}.json'
                run('snapshot-' + role + '-' + case,
                    [sys.executable, READER / 'rigid_parts/test_reader_contract.py', '--reader', library,
                     '--case', READER / 'rigid_parts/data' / (case + '.rad'), '--output', target],
                    cwd=snapshots)
        report['restart_checks'] = capture_restarts(args.binaries, args.output / 'restarts', run)
        report['status'] = 'passed' if all(r['status'] == 'passed' for r in report['runs']) else 'failed'
    except Exception as error:
        report['status'], report['error'] = 'failed', repr(error)
        raise
    finally:
        generated = [{'path': str(p.relative_to(args.output)), 'bytes': p.stat().st_size, 'sha256': sha256(p)}
                     for p in sorted(args.output.rglob('*')) if p.is_file() and p.suffix.lower() in {'.rad', '.key', '.k'}]
        write_json(args.output / 'generated_input_manifest.json', generated)
        report['generated_input_manifest_sha256'] = sha256(args.output / 'generated_input_manifest.json')
        write_json(args.output / 'report.json', report)
    assert report['status'] == 'passed', 'Inspect failed runs in report.json'


if __name__ == '__main__':
    main()
