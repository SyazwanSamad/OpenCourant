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
"""Compare rigid-part Starter initialization and Engine motion with v82 and explicit bodies."""

import argparse
import contextlib
import hashlib
import io
import inspect
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

import numpy as np
from vortex_radioss.animtod3plot.RadiossTHReader import RadiossTHReader


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
XYZ = np.array([(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0),
                (0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1)], dtype=float)
END = 0.1
CASES = ['translation', 'missing_node', 'rotation', 'force', 'offset', 'sensor', 'load_sensor', 'added', 'units', 'explicit_rota']


def ints(*values):
    return ''.join(f'{value:10d}' for value in values)


def reals(*values):
    return ''.join(f'{value:20.12g}' for value in values)


def make_deck(folder, case, explicit):
    unit = 7 if case == 'units' else 0
    added_mass = 0.5 if case in ['added', 'units'] else 0
    inertias = np.array([0.2, 0.3, 0.4, 0.01, 0.02, 0.03])
    if case not in ['added', 'units']:
        inertias *= 0
    if unit:
        inertias *= 1e6
    sensor = 6 if case == 'sensor' else 0
    load_sensor = 6 if case == 'load_sensor' else 0
    skew = 5 if case in ['added', 'units'] else 0
    main = 0 if case == 'missing_node' and not explicit else 9
    lines = ['#RADIOSS STARTER', '# OpenCourant numerical regression; AGPL-3.0-or-later.',
             '/BEGIN', 'rigid', ints(2612, 0), f'{"kg":>20}{"m":>20}{"s":>20}',
             f'{"kg":>20}{"m":>20}{"s":>20}', '/MAT/LAW1/1', 'unit density elastic',
             reals(1), reals(10000, 0.3), '/PROP/SOLID/1', 'one integration point brick',
             ints(1, 0, 0, 0, 0, 0, 0, 0) + reals(0), reals(0, 0, 0), reals(0) + ints(1), '/NODE']
    for i, xyz in enumerate([*XYZ, (0.5, 0.5, 0.5)], 1):
        lines.append(ints(i) + reals(*xyz))
    lines += ['/BRICK/10', ints(1, *range(1, 9)), '/GRNOD/NODE/1', 'all nodes', ints(*range(1, 10)),
              '/GRNOD/NODE/2', 'main node', ints(9), '/SKEW/FIX/5', 'ninety degree local axes',
              reals(0.5, 0.5, 0.5), reals(-1, 0, 0), reals(0, 0, 1)]
    if unit:
        lines += ['/UNIT/7', 'kg mm s', f'{"kg":>20}{"mm":>20}{"s":>20}']
    lines += [f'/PART/10/{unit}', 'rigid cube', ints(1, 1, 0) + reals(0) + ints(0 if explicit else 1)]
    if explicit:
        lines += ['/GRNOD/NODE/3', 'body secondary nodes', ints(*range(1, 9)), f'/RBODY/1/{unit}',
                  'explicit rigid cube', ints(main, sensor, skew, 2) + reals(added_mass) + ints(3, 0, 1, 0),
                  reals(*inertias[:3]), reals(*inertias[3:]), ints(0, 2)]
    else:
        lines += [ints(main, skew) + reals(added_mass) + ' '*10 + ints(sensor),
                  reals(*inertias[:3]), reals(*inertias[3:])]
    if case in ['translation', 'missing_node', 'sensor']:
        lines += ['/INIVEL/TRA/1', 'uniform translation', reals(2, 0, 0) + ints(1, 0), reals(0) + ints(0)]
    if case == 'rotation':
        lines += ['/INIVEL/NODE/1', 'unit angular velocity']
        for i, xyz in enumerate([*XYZ, (0.5, 0.5, 0.5)], 1):
            velocity = np.cross([0, 0, 1], np.array(xyz) - 0.5)
            lines += [ints(i, 0) + reals(*velocity), ' '*20 + reals(0, 0, 1)]
    if sensor or load_sensor:
        lines += ['/SENSOR/TIME/6', 'activate at half time', reals(0.05), reals(1)]
    if case in ['force', 'offset', 'load_sensor']:
        lines += ['/FUNCT/1', 'unit force', reals(0, 1), reals(1, 1), '/CLOAD/1', 'unit main-node force',
                  ints(1) + f'{"X":>10}' + ints(0, load_sensor, 2) + ' '*10 + reals(1, 1)]
    lines += ['/TH/NODE/1', 'nodes', ''.join(f'{key:<10}' for key in ['X', 'Y', 'Z', 'VX', 'VY', 'VZ'])]
    lines += [ints(i, 0) + f'n{i}' for i in range(1, 9)]
    lines += ['/TH/RBODY/2', 'body', ''.join(f'{key:<10}' for key in
              ['X', 'Y', 'Z', 'VX', 'VY', 'VZ', 'MASS', 'IXX', 'IYY', 'IZZ']), ints(1),
              '/TH/RBODY/3', 'rotation', ''.join(f'{key:<10}' for key in ['RX', 'RY', 'RZ', 'VRX', 'VRY', 'VRZ']),
              ints(1), '/END']
    if case == 'offset':
        lines = lines[:7] + ['//SUBMODEL/2/0', 'offset cube', ints(1000, 0, 0, 0, 0, 0, 0)] + \
                lines[7:-1] + ['//ENDSUB', '/END']
    (folder / 'rigid_0000.rad').write_text('\n'.join(lines) + '\n', encoding='ascii')
    (folder / 'rigid_0001.rad').write_text('\n'.join(['#RADIOSS ENGINE', '/VERS/2026', '/RUN/rigid/1',
        reals(END), '/PRINT/-100', '/DT', '0.01 0.0', '/DTIX', '0.0001 0.0001', '/TFILE/4', reals(END/100),
        '/ANIM/DT', reals(0, END), '/ANIM/VECT/VEL']) + '\n', encoding='ascii')


def parse_initialization(block):
    def values(label, count):
        match = re.search(re.escape(label) + r'\s+([^\n]+)', block)
        assert match, (label, block)
        result = [float(x.replace('D', 'E')) for x in
                  re.findall(r'[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[ED][+-]?\d+)?', match.group(1))[:count]]
        assert len(result) == count
        return result
    nodes = re.search(r'SECONDARY NODES\s+([\d\s]+)', block)
    return {'mass': values('NEW MASS', 1)[0], 'center': values('NEW X,Y,Z', 3),
            'diagonal': values('NEW INERTIA xx yy zz', 3), 'off_diagonal': values('NEW INERTIA xy yz zx', 3),
            'nodes': [int(x) for x in nodes.group(1).split()]}


def initializations(listing):
    section = listing.split('RIGID BODY INITIALIZATION', 1)[1].split('PART MASS & INERTIA', 1)[0]
    result = {}
    for block in re.split(r'(?=\n\s*RIGID BODY ID\s+\d+)', section):
        match = re.search(r'RIGID BODY ID\s+(\d+)', block)
        if match:
            result[int(match.group(1))] = parse_initialization(block)
    return result


def initialization(listing):
    values = initializations(listing)
    assert len(values) == 1, values
    return next(iter(values.values()))


def compare_initialization(actual, expected):
    np.testing.assert_array_equal(sorted(actual['nodes']), sorted(expected['nodes']))
    for key in ['mass', 'center', 'diagonal', 'off_diagonal']:
        np.testing.assert_allclose(actual[key], expected[key], rtol=1e-6, atol=1e-8)


def history_records(path, widths):
    with contextlib.redirect_stdout(io.StringIO()):
        reader = RadiossTHReader(str(path))
    time = reader.array['time'].ravel().astype(float)
    # The installed reader offsets groups incorrectly for the current 23-global layout.
    packed = reader.all_data
    cursor = 3
    def record(width):
        nonlocal cursor
        assert np.all(packed[:, cursor:cursor+1].view('>i4') == 4*width)
        assert np.all(packed[:, cursor+width+1:cursor+width+2].view('>i4') == 4*width)
        values = packed[:, cursor+1:cursor+width+1].astype(float)
        cursor += width+2
        return values
    global_width = int(packed[0:1, cursor:cursor+1].view('>i4')[0, 0])//4
    globals_array = record(global_width)
    keys = ['internal_energy', 'kinetic_energy', 'x_momentum', 'y_momentum', 'z_momentum', 'mass',
            'time_step', 'rotational_energy', 'external_work', 'spring_energy', 'contact_energy', 'hourglass_energy']
    global_values = {key: globals_array[:, i] for i, key in enumerate(keys)}
    # shortcut: group widths are fixed by these test decks, use a general converter for other layouts.
    groups = [record(width) for width in widths]
    assert cursor == packed.shape[1], packed.shape
    return time, global_values, groups


def history(folder):
    time, global_values, groups = history_records(folder / 'rigidT01', [48, 10, 6])
    nodes = groups[0].reshape(-1, 8, 6)[:, :, [3, 4, 5, 0, 1, 2]]
    body, rotation = groups[1:]
    assert len(time) >= 20 and time[-1] >= END-1.1*END/100, time
    assert all(np.isfinite(array).all() for array in [time, nodes, body, rotation, *global_values.values()])
    return {'time': time, 'nodes': nodes, 'body': body, 'rotation': rotation, 'global': global_values}


def verify(case, initial, data):
    expected_mass = 1.5 if case in ['added', 'units'] else 1
    np.testing.assert_allclose(initial['mass'], expected_mass, rtol=2e-6)
    np.testing.assert_allclose(initial['center'], [0.5]*3, atol=2e-7)
    offset = 1000 if case == 'offset' else 0
    np.testing.assert_array_equal(sorted(initial['nodes']), list(range(1+offset, 9+offset)))
    expected_diagonal = [0.8, 0.7, 0.9] if case in ['added', 'units'] else [0.5]*3
    np.testing.assert_allclose(initial['diagonal'], expected_diagonal, atol=2e-6)
    expected_off_diagonal = [-0.01, 0.03, -0.02] if case in ['added', 'units'] else [0]*3
    np.testing.assert_allclose(initial['off_diagonal'], expected_off_diagonal, atol=2e-7)
    time, nodes, body = data['time'], data['nodes'], data['body']
    positions = nodes[:, :, :3]
    maximum_distance_error = 0
    for i in range(8):
        for j in range(i):
            error = np.abs(np.linalg.norm(positions[:, i]-positions[:, j], axis=1) - np.linalg.norm(XYZ[i]-XYZ[j]))
            maximum_distance_error = max(maximum_distance_error, float(error.max()))
    assert maximum_distance_error < 3e-5, maximum_distance_error
    np.testing.assert_allclose(data['global']['mass'], expected_mass, atol=2e-6)
    if case in ['translation', 'missing_node', 'sensor']:
        expected = np.broadcast_to(XYZ, positions.shape).copy()
        expected[:, :, 0] += 2*time[:, None]
        np.testing.assert_allclose(positions, expected, atol=3e-5)
        np.testing.assert_allclose(data['global']['kinetic_energy'], 2, atol=3e-5)
        expected_energy = np.full_like(time, 2)
    elif case == 'rotation':
        expected = np.broadcast_to(XYZ, positions.shape).copy()-0.5
        x, y = expected[:, :, 0].copy(), expected[:, :, 1].copy()
        expected[:, :, 0] = x*np.cos(time[:, None])-y*np.sin(time[:, None])
        expected[:, :, 1] = x*np.sin(time[:, None])+y*np.cos(time[:, None])
        expected += 0.5
        np.testing.assert_allclose(positions, expected, atol=3e-5)
        np.testing.assert_allclose(data['global']['rotational_energy'], 0.25, atol=3e-5)
        expected_energy = np.full_like(time, 0.25)
    elif case in ['force', 'offset', 'load_sensor']:
        elapsed = np.maximum(0, time-(0.05 if case == 'load_sensor' else 0))
        expected = np.broadcast_to(XYZ, positions.shape).copy()
        expected[:, :, 0] += 0.5*elapsed[:, None]**2
        np.testing.assert_allclose(positions, expected, atol=3e-5)
        np.testing.assert_allclose(body[:, 3], elapsed, atol=3e-4)
        np.testing.assert_allclose(data['global']['kinetic_energy'], 0.5*elapsed**2, atol=3e-5)
        expected_energy = 0.5*elapsed**2
        np.testing.assert_allclose(data['global']['external_work'], data['global']['kinetic_energy'], atol=3e-5)
        if case == 'load_sensor':
            assert np.max(np.abs(positions[time < 0.049]-XYZ)) < 1e-7
    else:
        expected = np.broadcast_to(XYZ, positions.shape)
        np.testing.assert_allclose(positions, expected, atol=1e-7)
        expected_energy = np.zeros_like(time)
    total_kinetic_energy = data['global']['kinetic_energy']+data['global']['rotational_energy']
    np.testing.assert_allclose(total_kinetic_energy, expected_energy, atol=3e-5)
    np.testing.assert_allclose(data['global']['internal_energy'], 0, atol=1e-7)
    return {'mass': initial['mass'], 'center': initial['center'], 'inertia': initial['diagonal'],
            'samples': len(time), 'final_time': float(time[-1]), 'max_distance_error': maximum_distance_error,
            'max_position_error': float(np.max(np.abs(positions-expected))),
            'max_energy_error': float(np.max(np.abs(total_kinetic_energy-expected_energy)))}


def solve(program, filename, folder, environment):
    starter = filename.endswith('0000.rad')
    options = ['-np', '1'] if starter else ['-nt', '1']
    result = subprocess.run([str(program), '-i', filename, *options], cwd=folder, env=environment,
                            capture_output=True, text=True, timeout=60)
    (folder / (filename+'.log')).write_text(result.stdout+result.stderr, encoding='utf-8')
    assert result.returncode == 0, (folder, program, result.returncode, result.stdout[-2500:], result.stderr)
    if starter:
        assert re.search(r'\b0 ERROR\(S\)', result.stdout), (folder, result.stdout[-1000:])
        assert any(p.stat().st_size for p in folder.glob('*.rst'))
    else:
        assert 'NORMAL TERMINATION' in result.stdout, (folder, program, result.stdout[-1000:])


def existing_rotation(args, environment, report):
    previous = None
    for role in ['openreader', 'v82']:
        folder = Path(tempfile.mkdtemp(prefix='explicit-rota-'+role+'-', dir=args.output))
        source = ROOT / 'qa-tests/miniqa/KIN_CONSTRAINTS/RBODY/ROTA/data'
        shutil.copytree(source, folder, dirs_exist_ok=True)
        # Keep the existing model and imposed rotation; shorten only its output/run schedule.
        (folder / 'BLOCK_0001.rad').write_text('\n'.join(['#RADIOSS ENGINE', '/VERS/2026', '/RUN/BLOCK/1',
            reals(END), '/PRINT/-100', '/DT', '0.5 0', '/DTIX', '0.0001 0.0001',
            '/TFILE/4', reals(END/100), '/ANIM/DT', reals(0, END)])+'\n', encoding='ascii')
        solve(args.binaries / f'starter-{role}.exe', 'BLOCK_0000.rad', folder, environment)
        solve(args.engine, 'BLOCK_0001.rad', folder, environment)
        time, globals_data, groups = history_records(folder / 'BLOCKT01', [6, 12, 9])
        nodes = groups[1].reshape(-1, 2, 6)
        expected = np.column_stack([np.cos(2*time)-1, np.sin(2*time), np.zeros_like(time)])
        np.testing.assert_allclose(nodes[:, 0, :3], 0, atol=1e-7)
        np.testing.assert_allclose(nodes[:, 1, :3], expected, atol=3e-5)
        distances = np.linalg.norm(nodes[:, 1, :3]+[1, 0, 0]-nodes[:, 0, :3], axis=1)
        np.testing.assert_allclose(distances, 1, atol=3e-5)
        np.testing.assert_allclose(globals_data['rotational_energy'][time > 0], 2, atol=3e-5)
        if previous is not None:
            np.testing.assert_allclose(time, previous[0], atol=1e-8)
            np.testing.assert_allclose(nodes, previous[1], atol=1e-6)
        previous = time, nodes
        report['cases'].append({'case': 'explicit_rota', 'variant': role, 'folder': str(folder),
            'checks': {'samples': len(time), 'final_time': float(time[-1]),
                       'max_distance_error': float(np.max(np.abs(distances-1)))}})
        print(f'PASS numerical existing RBODY/ROTA/{role}', flush=True)


def structural_checks(args, environment, report):
    expected_counts = {'ordinary_zero': 0, 'single': 1, 'disconnected_one': 1, 'mixed': 2, 'existing': 3,
                       'shared': 2, 'interleaved': 2, 'lagmul': 1, 'explicit_fields': 1, 'empty': None}
    for case, count in expected_counts.items():
        previous = None
        for role in ['openreader', 'v82']:
            folder = Path(tempfile.mkdtemp(prefix='structural-'+case+'-'+role+'-', dir=args.output))
            shutil.copytree(HERE / 'data', folder, dirs_exist_ok=True)
            shutil.copy(folder / (case+'.rad'), folder / 'case_0000.rad')
            if count is None:
                result = subprocess.run([str(args.binaries / f'starter-{role}.exe'), '-i', 'case_0000.rad', '-np', '1'],
                                        cwd=folder, env=environment, capture_output=True, text=True, timeout=60)
                (folder / 'case_0000.rad.log').write_text(result.stdout+result.stderr)
                assert result.returncode == 2 and 'ERROR' in result.stdout
                assert 'forrtl: severe' not in result.stdout+result.stderr
                assert not list(folder.glob('*.rst')), folder
                bodies = {}
            else:
                solve(args.binaries / f'starter-{role}.exe', 'case_0000.rad', folder, environment)
                listing = (folder / 'case_0000.out').read_text(errors='replace')
                bodies = initializations(listing) if count else {}
                assert len(bodies) == count, (case, bodies)
                if previous is not None:
                    assert bodies.keys() == previous.keys(), (case, bodies, previous)
                    for identity in bodies:
                        compare_initialization(bodies[identity], previous[identity])
                previous = bodies
            report.setdefault('structural', []).append({'case': case, 'reader': role, 'folder': str(folder),
                                                        'expected_rejection': count is None, 'bodies': bodies})
            print(f'PASS structural {case}/{role}', flush=True)
    folder = Path(tempfile.mkdtemp(prefix='known-v82-units-', dir=args.output))
    make_deck(folder, 'units', False)
    solve(args.binaries / 'starter-v82.exe', 'rigid_0000.rad', folder, environment)
    observed = initialization((folder / 'rigid_0000.out').read_text(errors='replace'))
    np.testing.assert_allclose(observed['diagonal'], [300000.5, 200000.5, 400000.5], rtol=2e-6)
    report['known_reference_differences'] = {'explicit_unit': {'folder': str(folder),
        'v82_generated_diagonal': observed['diagonal'], 'physical_diagonal': [0.8, 0.7, 0.9],
        'oracle': 'v82 explicit /RBODY with unit ID 7; OpenReader generated body preserves that unit'}}
    print('PASS documented v82 generated-unit discrepancy', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binaries', required=True, type=lambda p: Path(p).resolve())
    parser.add_argument('--engine', required=True, type=lambda p: Path(p).resolve())
    parser.add_argument('--output', required=True, type=lambda p: Path(p).resolve())
    parser.add_argument('--case', choices=CASES)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    environment = os.environ.copy()
    environment.update(RAD_CFG_PATH=str(ROOT / 'hm_cfg_files'), OMP_NUM_THREADS='1', KMP_STACKSIZE='400m',
                       RAD_H3D_PATH=str(ROOT / 'extlib/h3d/lib/win64'))
    environment['PATH'] = os.pathsep.join([str(ROOT / 'exec'), str(ROOT / 'extlib/hm_reader/win64'),
                                         environment.get('PATH', '')])
    report = {'engine_sha256': hashlib.sha256(args.engine.read_bytes()).hexdigest(),
              'numpy_version': np.__version__,
              'time_history_reader_sha256': hashlib.sha256(Path(inspect.getfile(RadiossTHReader)).read_bytes()).hexdigest(),
              'status': 'running', 'cases': []}
    try:
        for case in [args.case] if args.case else CASES:
            if case == 'explicit_rota':
                existing_rotation(args, environment, report)
                continue
            previous = None
            variants = [('openreader', False)] + ([] if case == 'units' else [('v82', False)]) + [('v82', True)]
            for role, explicit in variants:
                label = role + ('-explicit' if explicit else '-generated')
                folder = Path(tempfile.mkdtemp(prefix=case+'-'+label+'-', dir=args.output))
                make_deck(folder, case, explicit)
                solve(args.binaries / f'starter-{role}.exe', 'rigid_0000.rad', folder, environment)
                solve(args.engine, 'rigid_0001.rad', folder, environment)
                initial = initialization((folder / 'rigid_0000.out').read_text(errors='replace'))
                data = history(folder)
                checks = verify(case, initial, data)
                if case == 'sensor':
                    log = (folder / 'rigid_0001.rad.log').read_text()
                    assert 'WILL BE SET OFF WITHIN 2 CYCLES' in log and 'SET OFF' in log
                if previous:
                    old_initial, old_data = previous
                    compare_initialization(initial, old_initial)
                    for key in ['time', 'nodes', 'body', 'rotation']:
                        np.testing.assert_allclose(data[key], old_data[key], rtol=1e-5, atol=1e-6)
                    for key in data['global']:
                        np.testing.assert_allclose(data['global'][key], old_data['global'][key], rtol=1e-5, atol=1e-6)
                previous = initial, data
                report['cases'].append({'case': case, 'variant': label, 'folder': str(folder), 'checks': checks})
                print(f'PASS numerical {case}/{label}', flush=True)
        if args.case is None:
            structural_checks(args, environment, report)
        report['status'] = 'passed'
    except Exception as error:
        report['status'] = 'failed'
        report['error'] = str(error)
        raise
    finally:
        (args.output / 'report.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')


if __name__ == '__main__':
    main()
