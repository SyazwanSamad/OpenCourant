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
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[2]


def main():
    manifest = json.loads((ROOT / 'EXTLIB_VERSION.json').read_text())
    assert not any('hm_reader' in name for name in manifest['required_files'])
    for arch in ['win64', 'linux64', 'linuxa64']:
        assert any('/' + arch + '/libboost_filesystem.' in name for name in manifest['required_files'])
    print('PASS required dependencies exclude HM Reader and include OpenReader link inputs')

    spec = importlib.util.spec_from_file_location('load_extlib', ROOT / 'Compiling_tools/script/load_extlib.py')
    loader = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loader)
    with tempfile.TemporaryDirectory(prefix='reader-dependencies-') as temporary:
        work = Path(temporary)
        payload = work / 'payload.zip'
        with ZipFile(payload, 'w') as archive:
            archive.writestr('extlib/headers/reader.h', 'retained header')
            archive.writestr('extlib/h3d/retained.lib', 'later removal stage')
            archive.writestr('extlib/hm_reader/win64/hm_reader_win64.dll', 'retired reader')
        fake_root = work / 'checkout'
        fake_root.mkdir()
        (fake_root / 'EXTLIB_VERSION.json').write_text(json.dumps({
            'version': 'fixture', 'url': 'https://invalid.example/fixture.zip',
            'sha256': hashlib.sha256(payload.read_bytes()).hexdigest(),
            'required_files': ['headers/reader.h']}))
        with patch.object(loader, '__file__', str(fake_root / 'Compiling_tools/script/load_extlib.py')), \
             patch.object(loader.urllib.request, 'urlretrieve',
                          side_effect=lambda url, target: shutil.copyfile(payload, target)) as fetch, \
             contextlib.redirect_stdout(io.StringIO()):
            assert loader.main() == 0
            assert (fake_root / 'extlib/headers/reader.h').read_text() == 'retained header'
            assert (fake_root / 'extlib/h3d/retained.lib').is_file()
            assert not (fake_root / 'extlib/hm_reader').exists()
            assert loader.main() == 0
            assert fetch.call_count == 1
    print('PASS pinned archive extraction skips HM Reader; retained dependency cache works')

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


if __name__ == '__main__':
    main()
