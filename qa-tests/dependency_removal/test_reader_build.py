# Copyright (C) 2026 OpenCourant contributors
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Check reader cutover invariants and dependency extraction without network access."""

import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import shutil
import tempfile
from unittest.mock import patch
from zipfile import ZipFile, ZipInfo


ROOT = Path(__file__).resolve().parents[2]


def main():
    manifest = json.loads((ROOT / 'EXTLIB_VERSION.json').read_text())
    assert not any('hm_reader' in name or 'h3d' in name for name in manifest['required_files'])
    for arch in ['win64', 'linux64', 'linuxa64']:
        assert any('/' + arch + '/libboost_filesystem.' in name for name in manifest['required_files'])
    print('PASS required dependencies exclude retired SDKs and include OpenReader link inputs')

    spec = importlib.util.spec_from_file_location('load_extlib', ROOT / 'Compiling_tools/script/load_extlib.py')
    loader = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loader)
    with tempfile.TemporaryDirectory(prefix='reader-dependencies-') as temporary:
        work = Path(temporary)
        payload = work / 'payload.zip'
        def make_payload(path, extra=(), identity='fixture', required=True):
            with ZipFile(path, 'w') as archive:
                if required:
                    archive.writestr('extlib/headers/reader.h', 'retained header')
                archive.writestr('extlib/EXTLIB_VERSION.json', json.dumps({'package_tag': identity}))
                for name in extra:
                    archive.writestr(name, 'invalid payload')

        make_payload(payload)
        fake_root = work / 'checkout'
        fake_root.mkdir()
        (fake_root / 'EXTLIB_VERSION.json').write_text(json.dumps({
            'version': 'fixture', 'package_tag': 'fixture', 'url': 'https://invalid.example/fixture.zip',
            'sha256': hashlib.sha256(payload.read_bytes()).hexdigest(),
            'required_files': ['headers/reader.h']}))
        with patch.object(loader, '__file__', str(fake_root / 'Compiling_tools/script/load_extlib.py')), \
             patch.object(loader.urllib.request, 'urlretrieve',
                          side_effect=lambda url, target: shutil.copyfile(payload, target)) as fetch, \
             contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()) as errors:
            assert loader.main() == 0, errors.getvalue()
            assert (fake_root / 'extlib/headers/reader.h').read_text() == 'retained header'
            assert loader.main() == 0
            assert fetch.call_count == 1
            stale = fake_root / 'extlib/h3d'
            stale.mkdir()
            (stale / 'h3dwriter.dll').write_text('stale')
            assert loader.main() == 0 and not stale.exists()
            assert fetch.call_count == 1
            (fake_root / 'extlib/EXTLIB_VERSION.json').write_text('{"package_tag":"old"}')
            assert loader.main() == 0
            (fake_root / 'extlib/headers/reader.h').unlink()
            assert loader.main() == 0
            (fake_root / 'extlib.zip').write_bytes(b'old cached archive')
            assert loader.main() == 0 and fetch.call_count == 2
            assert loader.sha256_file(fake_root / 'extlib.zip') == loader.sha256_file(payload)
            pin = json.loads((fake_root / 'EXTLIB_VERSION.json').read_text())
            pin['sha256'] = pin['sha256'].upper()
            (fake_root / 'EXTLIB_VERSION.json').write_text(json.dumps(pin))
            assert loader.main() == 0 and fetch.call_count == 2

        invalid = [
            ('writer', ['extlib/h3d/lib/win64/h3dwriter.dll']),
            ('reader', ['extlib/HM_READER/win64/hm_reader_win64.lib']),
            ('header', ['extlib/includes/H3DPUBLIC_DEFS.H']),
            ('values-header', ['extlib/includes/h3d_values.h']),
            ('unversioned-reader', ['extlib/bin/hm_reader.dll']),
            ('license', ['extlib/license/hm_reader_license.txt']),
            ('converter', ['extlib/bin/h3dtoxml_Linux_I.exe']),
            ('traversal', ['extlib/../escape']),
            ('absolute', ['/extlib/escape']),
            ('windows', ['extlib/C:/escape']),
            ('backslash', ['extlib\\..\\escape']),
            ('identity', []), ('missing', []), ('checksum', []), ('corrupt', []), ('symlink', []),
        ]
        for case, extra in invalid:
            checkout = work / case
            (checkout / 'extlib').mkdir(parents=True)
            kept = checkout / 'extlib/kept.txt'
            kept.write_text('previous cache')
            bad = work / (case + '.zip')
            make_payload(bad, extra, identity='old' if case == 'identity' else 'fixture', required=case != 'missing')
            if case == 'corrupt':
                bad.write_bytes(b'not a zip')
            if case == 'symlink':
                with ZipFile(bad, 'a') as archive:
                    entry = ZipInfo('extlib/link')
                    entry.create_system = 3
                    entry.external_attr = 0o120777 << 16
                    archive.writestr(entry, '../../escape')
            pin = {'version': 'fixture', 'package_tag': 'fixture', 'url': 'https://invalid.example/fixture.zip',
                   'required_files': ['headers/reader.h'], 'sha256': '0'*64 if case == 'checksum' else loader.sha256_file(bad)}
            (checkout / 'EXTLIB_VERSION.json').write_text(json.dumps(pin))
            with patch.object(loader, '__file__', str(checkout / 'Compiling_tools/script/load_extlib.py')), \
                 patch.object(loader.urllib.request, 'urlretrieve', side_effect=lambda url, target: shutil.copyfile(bad, target)), \
                 contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                assert loader.main() == 1, case
                assert kept.read_text() == 'previous cache', case
                assert not (checkout / 'escape').exists(), case
                assert not (checkout / 'extlib.zip.tmp').exists(), case

        (fake_root / 'extlib/.package-sha256').unlink()
        kept = fake_root / 'extlib/kept.txt'
        kept.write_text('previous cache')
        rename = Path.rename
        def fail_install(path, target):
            if path.name == 'extlib' and path.parent.name.startswith('extlib-'):
                raise PermissionError('simulated promotion failure')
            return rename(path, target)
        with patch.object(loader, '__file__', str(fake_root / 'Compiling_tools/script/load_extlib.py')), \
             patch.object(Path, 'rename', fail_install), \
             contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            assert loader.main() == 1 and kept.read_text() == 'previous cache'
        def fail_install_and_restore(path, target):
            if path.parent.name.startswith('extlib-'):
                raise PermissionError('simulated install and rollback failure')
            return rename(path, target)
        with patch.object(loader, '__file__', str(fake_root / 'Compiling_tools/script/load_extlib.py')), \
             patch.object(Path, 'rename', fail_install_and_restore), \
             contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()) as errors:
            assert loader.main() == 1
            backups = list(fake_root.glob('extlib-*/previous/kept.txt'))
            assert len(backups) == 1 and backups[0].read_text() == 'previous cache'
            assert 'Previous cache preserved for recovery' in errors.getvalue()
    print('PASS pinned package/cache identity, stale SDK refresh, 16 invalid archives, rollback and recoverable failed rollback')

    assert not (ROOT / 'starter/source/devtools/hm_reader').exists()
    assert (ROOT / 'starter/source/devtools/reader/hm_evaluate_rbodies_from_rigid_parts.F90').is_file()
    for path in (ROOT / 'starter/CMake_Compilers').glob('cmake*.txt'):
        text = path.read_text()
        assert 'USE_OPEN_READER' not in text and 'hm_reader' not in text and '-lapr-1' not in text, path
    starter = (ROOT / 'starter/CMakeLists.txt').read_text()
    assert 'add_subdirectory(${source_directory}/../reader ' in starter
    assert 'target_link_libraries(${EXEC_NAME} ${OPEN_READER_TARGET}' in starter
    assert 'HM_READER_LEGACY' not in starter and 'HM_READER_NO_' not in starter
    reader = (ROOT / 'reader/CMakeLists.txt').read_text()
    assert 'add_dependencies(${reader_target}_${arch} extlib)' in reader
    assert 'OPEN_READER_TARGET ${link_library_name} PARENT_SCOPE' in reader
    print('PASS Starter always builds/links OpenReader with dependency ordering and neutral adapters')

    spec = importlib.util.spec_from_file_location('check_package', ROOT / 'Compiling_tools/script/check_package.py')
    package = importlib.util.module_from_spec(spec)
    with patch.dict('sys.modules', {'load_extlib': loader}):
        spec.loader.exec_module(package)
    for arch in ['win64', 'linux64', 'linuxa64']:
        reader = f'open_reader_{arch}.dll' if arch == 'win64' else f'libopen_reader_{arch}.so'
        suffix = '.exe' if arch == 'win64' else '_gf'
        names = {'OpenCourant/' + name for name in ['exec/' + reader, 'exec/starter_' + arch + suffix,
            'exec/engine_' + arch + suffix, 'LICENSE.md', 'COPYRIGHT.md', 'licenses/boost_license.txt', 'licenses/EXTLIB_VERSION.json',
            'hm_cfg_files/config/reader.cfg', 'hm_cfg_files/messages/messages.txt']}
        package.check_names(names, arch)
        for invalid_names in [names - {'OpenCourant/exec/' + reader},
                              names | {'OpenCourant/extlib/h3d/lib/h3dwriter.dll'},
                              names | {'OpenCourant/licenses/hm_reader_license.txt'},
                              names | {'OpenCourant/exec/H3DTOXML.exe'}]:
            try:
                package.check_names(invalid_names, arch)
            except ValueError:
                pass
            else:
                raise AssertionError((arch, invalid_names))
    print('PASS Windows/Linux/ARM package guards require OpenReader/configuration/notices and reject retired payloads')


if __name__ == '__main__':
    main()
