# Copyright (C) 2026 OpenCourant contributors
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Check shared scalar queries driving loads against captured pre-refactor results."""

import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'qa-tests/reader/rigid_parts'))
from test_numerical import make_deck, ints, reals, history_records
from compare_decks import records


SOURCES = {
    'shell': ('PYTHON/FUNCT_PYTHON/data', 'test_torsion_orthstrain_shell'),
    'tria': ('COQUES3N/ct3a/data', 'CT3AV4'),
    'quad': ('ALE2D/bar2_v41/data', 'BAR2V41B'),
}


def trace_lines():
    return ["    import os", "    values = (TIME, DENS(1), MASS(1), SIGEQ(1), MASS(2), SIGEQ(2), EPSP(1))",
            "    rank = os.getenv('PMI_RANK', '0')", "    with open('queries.' + rank + '.txt', 'a') as trace:",
            "        trace.write(str(values) + chr(10))"]


def solid(folder):
    make_deck(folder, 'force', False)
    p = folder / 'rigid_0000.rad'
    lines = p.read_text().splitlines()
    part = lines.index('/PART/10/0')
    lines[part+2] = lines[part+2][:50] + ints(0)
    del lines[part+3:part+6]
    lines.remove(ints(9) + reals(0.5, 0.5, 0.5))
    lines[lines.index('/GRNOD/NODE/1')+2] = ints(*range(1, 9), *range(10, 14))
    lines[lines.index('/GRNOD/NODE/2')+2] = ints(1)
    brick = lines.index('/BRICK/10')
    lines[brick:brick] = [ints(i) + reals(*xyz) for i, xyz in
                        zip(range(10, 14), [(2, 0, 0), (2, 1, 0), (2, 0, 1), (2, 1, 1)])]
    brick = lines.index('/BRICK/10')
    lines.insert(brick+2, ints(2, 2, 10, 11, 3, 6, 12, 13, 7))
    start, end = lines.index('/TH/RBODY/2'), lines.index('/END')
    del lines[start:end]
    start = lines.index('/FUNCT/1')
    lines[start:start+4] = ['/FUNCT_PYTHON/1', 'def shared_force(x):', *trace_lines(),
                          '    return 1.0 + 0.001*SIGEQ(1)']
    p.write_text('\n'.join(lines)+'\n')
    return 'rigid'


def prepare(case, folder):
    if case == 'solid':
        return solid(folder)
    source, name = SOURCES[case]
    shutil.copytree(ROOT / 'qa-tests/miniqa' / source, folder, dirs_exist_ok=True)
    p = folder / (name + '_0000.rad')
    lines = p.read_text().splitlines()
    if case == 'shell':
        start = lines.index('def myfun(x):')
        lines[start+1:start+1] = trace_lines()
        lines = [line + '*(1.0 + 0.001*SIGEQ(1))' if line.strip() ==
                 'return d*d*d*(10-15*d+6*d*d)' else line for line in lines]
    else:
        begin = lines.index('/BEGIN')
        lines[begin+2] = ints(2612) + lines[begin+2][10:]
        index = next(i for i, line in enumerate(lines) if line.startswith('/END'))
        lines[index:index] = ['/FUNCT_PYTHON/9001', 'def shared_force(x):', *trace_lines(),
                             '    return 1.0 + 0.001*SIGEQ(1)', '/GRNOD/NODE/9001', 'query-driven load',
                             ints(1), '/CLOAD/9001', 'query-driven force',
                             ints(9001) + f'{"Y":>10}' + ints(0, 0, 9001) + ' '*10 + reals(1, 1e-9)]
    p.write_text('\n'.join(lines)+'\n')
    return name


def run(command, folder, environment):
    result = subprocess.run([str(x) for x in command], cwd=folder, env=environment,
                            capture_output=True, text=True, errors='replace', timeout=180)
    (folder / (Path(command[0]).stem + '.log')).write_text(result.stdout+result.stderr, encoding='utf-8')
    assert result.returncode == 0, (command, result.returncode, result.stdout[-2000:], result.stderr[-2000:])
    return result.stdout + result.stderr


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--engine', required=True, type=lambda p: Path(p).resolve())
    parser.add_argument('--starter', type=lambda p: Path(p).resolve(), default=ROOT / 'exec/starter_win64.exe')
    parser.add_argument('--output', required=True, type=lambda p: Path(p).resolve())
    parser.add_argument('--baseline', type=lambda p: Path(p).resolve())
    parser.add_argument('--ranks', type=int, choices=[1, 2], default=1)
    parser.add_argument('--mpiexec', default='mpiexec')
    parser.add_argument('--case', choices=['shell', 'tria', 'quad', 'solid'])
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    env = os.environ.copy()
    env.update(RAD_CFG_PATH=str(ROOT/'hm_cfg_files'), OMP_NUM_THREADS='1', KMP_STACKSIZE='400m', I_MPI_FABRICS='shm')
    env['PATH'] = str(ROOT/'exec') + os.pathsep + env.get('PATH', '')
    report = {'status': 'running', 'engine_sha256': hashlib.sha256(args.engine.read_bytes()).hexdigest(),
              'ranks': args.ranks, 'cases': []}
    try:
        for case in [args.case] if args.case else ['shell', 'tria', 'quad', 'solid']:
            folder = args.output / case
            folder.mkdir()
            name = prepare(case, folder)
            inputs = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(folder.iterdir())
                      if p.suffix in ['.rad', '.inc']}
            output = run([args.starter, '-i', name+'_0000.rad', '-np', str(args.ranks), '-python'], folder, env)
            assert '0 ERROR(S)' in output
            command = [args.engine, '-i', name+'_0001.rad', '-nt', '1']
            if args.ranks > 1:
                command = [args.mpiexec, '-localonly', '-n', str(args.ranks), *command]
            output = run(command, folder, env)
            assert 'NORMAL TERMINATION' in output
            data = np.array(sorted(ast.literal_eval(line) for p in folder.glob('queries.*.txt')
                                   for line in p.read_text().splitlines()))
            assert data.ndim == 2 and data.shape[1] == 7 and len(data) > 20, (case, data.shape)
            active = data[data[:, 0] > 0]
            assert len(active) > 20 and np.isfinite(active).all() and np.abs(active).max() < 1e100
            assert (active[:, [1, 2, 4]] > 0).all(), (case, active.min(axis=0))
            if case == 'solid':
                np.testing.assert_allclose(active[:, [2, 4]], 1, rtol=2e-6, atol=2e-6)
                _, global_data, _ = history_records(folder / (name+'T01'), [48])
                np.testing.assert_allclose(global_data['mass'], 2, rtol=2e-6)
            widths, values = records(folder / (name+'T01'))
            np.savez_compressed(folder/'values.npz', queries=data, histories=values, widths=widths)
            row = {'case': case, 'samples': len(data), 'history_samples': len(values), 'inputs': inputs,
                   'query_min': active.min(axis=0).tolist(), 'query_max': active.max(axis=0).tolist()}
            if args.baseline:
                old = np.load(args.baseline / case / 'values.npz')
                np.testing.assert_array_equal(widths, old['widths'])
                np.testing.assert_allclose(data, old['queries'], rtol=1e-5, atol=1e-8)
                np.testing.assert_allclose(values, old['histories'], rtol=1e-5, atol=1e-6)
                row['max_query_difference'] = float(np.max(np.abs(data-old['queries'])))
                row['max_history_difference'] = float(np.max(np.abs(values-old['histories'])))
            report['cases'].append(row)
            print(f'PASS shared results {case}: ranks={args.ranks}, query rows={len(data)}', flush=True)
        report['status'] = 'passed'
    except Exception as error:
        report['status'], report['error'] = 'failed', repr(error)
        raise
    finally:
        (args.output/'report.json').write_text(json.dumps(report, indent=2)+'\n')


if __name__ == '__main__':
    main()
