# Copyright (C) 2026 OpenCourant contributors
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Exercise native STATE/DYNAIN/ANIM parsing, output and invalid-keyword diagnostics."""

import argparse
import gzip
import json
import os
from pathlib import Path
import re
import subprocess

import numpy as np

from test_shared_results import ROOT, prepare, run
from compare_decks import records


def contents(path):
    data = gzip.decompress(path.read_bytes()) if path.suffix == '.gz' else path.read_bytes()
    text = data.decode(errors='replace')
    return '\n'.join(line.rstrip() for line in text.splitlines() if not line.startswith(('#', '$')))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--engine', required=True, type=lambda p: Path(p).resolve())
    parser.add_argument('--output', required=True, type=lambda p: Path(p).resolve())
    parser.add_argument('--baseline', type=lambda p: Path(p).resolve())
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    env = os.environ.copy()
    env.update(RAD_CFG_PATH=str(ROOT/'hm_cfg_files'), OMP_NUM_THREADS='1', KMP_STACKSIZE='400m')
    env['PATH'] = str(ROOT/'exec') + os.pathsep + env.get('PATH', '')
    report = {'status': 'running', 'cases': []}
    try:
        for case in ['solid', 'shell']:
            folder = args.output / case
            folder.mkdir()
            name = prepare(case, folder)
            engine_input = folder / (name+'_0001.rad')
            if case == 'solid':
                family = 'STATE'
                cards = '/STATE/DT/ALL\n0 0.05\n/STATE/BRICK/STRESS/FULL\n/STATE/BRICK/STRAIN/FULL\n'
                pattern = '*.sta*'
            else:
                family = 'DYNAIN'
                cards = '/DYNAIN/DT/ALL\n0 0.001\n/DYNAIN/SHELL/STRESS/FULL\n/DYNAIN/SHELL/STRAIN/FULL\n'
                pattern = '*.dynain*'
            schedule = engine_input.read_text()
            if '/ANIM/DT' not in schedule:
                cards += '/ANIM/DT\n0 0.0005\n'
            engine_input.write_text(schedule + '\n' + cards)
            run([ROOT/'exec/starter_win64.exe', '-i', name+'_0000.rad', '-np', '1', '-python'], folder, env)
            output = run([args.engine, '-i', name+'_0001.rad', '-nt', '1'], folder, env)
            assert 'NORMAL TERMINATION' in output
            outputs = sorted(folder.glob(pattern))
            assert outputs and all(p.stat().st_size > 0 for p in outputs), (family, list(folder.iterdir()))
            assert any(folder.glob(name+'A*')), (case, 'native animation missing')
            widths, values = records(folder/(name+'T01'))
            np.savez_compressed(folder/'histories.npz', widths=widths, values=values)
            if args.baseline:
                old = np.load(args.baseline/case/'histories.npz')
                np.testing.assert_array_equal(widths, old['widths'])
                np.testing.assert_allclose(values, old['values'], rtol=1e-5, atol=1e-6)
                for path in outputs:
                    assert contents(path) == contents(args.baseline/case/path.name), (family, path.name)
            engine_input.write_text(engine_input.read_text().replace('/STRESS/FULL', '/INVALID/FULL'))
            invalid = subprocess.run([str(args.engine), '-i', name+'_0001.rad', '-nt', '1'],
                                     cwd=folder, env=env, capture_output=True, text=True, timeout=60)
            diagnostic = invalid.stdout + invalid.stderr
            (folder/'invalid-output.log').write_text(diagnostic, encoding='utf-8')
            assert 'NORMAL TERMINATION' not in diagnostic and 'forrtl: severe' not in diagnostic
            assert any(word in diagnostic.upper() for word in ['ERROR', 'INCORRECT', 'UNKNOWN']), diagnostic[-2000:]
            row = {'case': case, 'family': family, 'files': [p.name for p in outputs],
                   'invalid_exit_code': invalid.returncode}
            if args.baseline:
                prior = json.loads((args.baseline/'report.json').read_text())
                expected = next(r for r in prior['cases'] if r['case'] == case)
                assert row['invalid_exit_code'] == expected['invalid_exit_code']
            report['cases'].append(row)
            print(f'PASS native {family} and ANIM output, histories: {case}', flush=True)
        report['status'] = 'passed'
    except Exception as error:
        report['status'], report['error'] = 'failed', repr(error)
        raise
    finally:
        (args.output/'report.json').write_text(json.dumps(report, indent=2)+'\n')


if __name__ == '__main__':
    main()
