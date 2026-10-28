# Copyright (C) 2026 OpenCourant contributors
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Compare connected-region rigid parts with explicit bodies and analytic motion."""

import argparse
import hashlib
import json
import os
from pathlib import Path

import numpy as np

from test_reader_contract import ROOT
from test_numerical import (XYZ, ints, reals, make_deck, solve, initializations,
                            history_records, compare_initialization)


def deck(folder, case, explicit):
    make_deck(folder, case if case != 'disconnected' else 'translation', explicit)
    path = folder / 'rigid_0000.rad'
    lines = path.read_text().splitlines()
    if not explicit:
        part = next(i for i, line in enumerate(lines) if line.startswith('/PART/'))
        lines[part + 2] = lines[part + 2][:50] + ints(2)
        del lines[part + 3:part + 6]
    if case == 'rotation':
        start, end = lines.index('/INIVEL/NODE/1'), lines.index('/TH/NODE/1')
        lines[start:end] = ['/GRNOD/NODE/6', 'include generated main nodes',
                            ints(*range(1, 10 if explicit else 11)),
                            '/INIVEL/ROT/1', 'unit angular velocity', reals(0, 0, 1) + ints(6, 0)]
    if case == 'disconnected':
        node = lines.index('/NODE')
        lines[node + 1:node + 1] = [ints(i) + reals(*(xyz + [3, 0, 0]))
                                   for i, xyz in zip(range(11, 20), [*XYZ, np.array([0.5]*3)])]
        brick = lines.index('/BRICK/10')
        lines.insert(brick + 2, ints(2, *range(11, 19)))
        history = lines.index('/TH/RBODY/2')
        lines[history:history] = [ints(i, 0) + f'n{i}' for i in range(11, 19)]
        for keyword in ['/TH/RBODY/2', '/TH/RBODY/3']:
            lines[lines.index(keyword) + 3] = ints(1, 2)
        extra = ['/GRNOD/NODE/5', 'second cube', ints(*range(11, 20)),
                 '/INIVEL/TRA/2', 'independent translation', reals(-1, 0, 0) + ints(5, 0), reals(0) + ints(0)]
        if explicit:
            extra += ['/GRNOD/NODE/4', 'second body nodes', ints(*range(11, 19)), '/RBODY/2',
                      'second explicit cube', ints(19, 0, 0, 2) + reals(0) + ints(4, 0, 1, 0),
                      reals(0, 0, 0), reals(0, 0, 0), ints(0, 2)]
        lines[-1:-1] = extra
    path.write_text('\n'.join(lines) + '\n', encoding='ascii')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binaries', required=True, type=lambda p: Path(p).resolve())
    parser.add_argument('--engine', required=True, type=lambda p: Path(p).resolve())
    parser.add_argument('--output', required=True, type=lambda p: Path(p).resolve())
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    environment = os.environ.copy()
    environment.update(RAD_CFG_PATH=str(ROOT / 'hm_cfg_files'), OMP_NUM_THREADS='1', KMP_STACKSIZE='400m')
    environment['PATH'] = os.pathsep.join([str(ROOT / 'exec'), environment.get('PATH', '')])
    report = {'status': 'running', 'engine_sha256': hashlib.sha256(args.engine.read_bytes()).hexdigest(), 'cases': []}
    try:
        for case in ['translation', 'rotation', 'disconnected']:
            previous = None
            for role, explicit in [('openreader', False), ('openreader', True)]:
                label = role + ('-explicit' if explicit else '-mode2')
                folder = args.output / (case + '-' + label)
                folder.mkdir()
                deck(folder, case, explicit)
                solve(args.binaries / f'starter-{role}.exe', 'rigid_0000.rad', folder, environment)
                solve(args.engine, 'rigid_0001.rad', folder, environment)
                bodies = initializations((folder / 'rigid_0000.out').read_text(errors='replace'))
                count = 2 if case == 'disconnected' else 1
                assert len(bodies) == count, bodies
                for index, body in enumerate(bodies.values()):
                    np.testing.assert_allclose(body['mass'], 1, atol=2e-6)
                    np.testing.assert_allclose(body['center'], [0.5 + 3*index, 0.5, 0.5], atol=2e-7)
                    np.testing.assert_allclose(body['diagonal'], [0.5]*3, atol=2e-6)
                    np.testing.assert_array_equal(sorted(body['nodes']), list(range(1 + 10*index, 9 + 10*index)))
                times, globals_data, groups = history_records(folder / 'rigidT01', [48*count, 10*count, 6*count])
                assert len(times) >= 20 and times[-1] >= 0.0989
                nodes = groups[0].reshape(-1, 8*count, 6)
                positions = nodes[:, :, 3:6]
                expected = np.broadcast_to(np.vstack([XYZ + [3*i, 0, 0] for i in range(count)]), positions.shape).copy()
                if case == 'rotation':
                    x, y = XYZ[:, 0] - 0.5, XYZ[:, 1] - 0.5
                    expected[:, :, 0] = 0.5 + x*np.cos(times[:, None]) - y*np.sin(times[:, None])
                    expected[:, :, 1] = 0.5 + x*np.sin(times[:, None]) + y*np.cos(times[:, None])
                    energy = globals_data['rotational_energy']
                    expected_energy = 0.25
                else:
                    expected[:, :8, 0] += 2*times[:, None]
                    if count == 2:
                        expected[:, 8:, 0] -= times[:, None]
                    energy = globals_data['kinetic_energy']
                    expected_energy = 2.5 if count == 2 else 2
                np.testing.assert_allclose(positions, expected, atol=3e-5)
                np.testing.assert_allclose(energy, expected_energy, atol=3e-5)
                np.testing.assert_allclose(globals_data['mass'], count, atol=2e-6)
                if previous:
                    old_bodies, old_times, old_groups = previous
                    assert bodies.keys() == old_bodies.keys()
                    for key in bodies:
                        compare_initialization(bodies[key], old_bodies[key])
                    np.testing.assert_allclose(times, old_times, atol=1e-8)
                    for actual, old in zip(groups, old_groups):
                        np.testing.assert_allclose(actual, old, rtol=1e-5, atol=1e-6)
                previous = bodies, times, groups
                report['cases'].append({'case': case, 'variant': label, 'bodies': bodies, 'samples': len(times),
                    'input_sha256': hashlib.sha256((folder / 'rigid_0000.rad').read_bytes()).hexdigest(),
                    'max_position_error': float(np.max(np.abs(positions - expected))),
                    'max_energy_error': float(np.max(np.abs(energy - expected_energy)))})
                print(f'PASS mode2 numerical {case}/{label}', flush=True)
        report['status'] = 'passed'
    except Exception as error:
        report['status'], report['error'] = 'failed', repr(error)
        raise
    finally:
        (args.output / 'report.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
