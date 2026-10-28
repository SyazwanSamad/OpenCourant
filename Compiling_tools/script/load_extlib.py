"""Download and validate external libraries required to build OpenCourant."""

import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
import urllib.request
import zipfile


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def missing_required_files(extlib, manifest):
    return [
        name
        for name in manifest["required_files"]
        if not (extlib / name).is_file()
    ]


def forbidden_entry(name):
    parts = name.replace("\\", "/").lower().split("/")
    return any(part in ("hm_reader", "h3d", "h3d_values.h") or
               part.startswith(("libhm_reader", "hm_reader_", "hm_reader.", "libh3dreader", "h3dreader",
                                "libh3dwriter", "h3dwriter", "h3dpublic", "h3dtoxml", "h3d_license"))
               for part in parts)


def cache_ready(extlib, manifest):
    try:
        identity = json.loads((extlib / "EXTLIB_VERSION.json").read_text(encoding="utf-8"))
        stamp = (extlib / ".package-sha256").read_text().strip()
        return (stamp.lower() == manifest["sha256"].lower() and identity["package_tag"] == manifest["package_tag"]
                and not missing_required_files(extlib, manifest)
                and not any(forbidden_entry(p.relative_to(extlib).as_posix()) for p in extlib.rglob("*")))
    except (OSError, ValueError, KeyError):
        return False


def validate_archive(archive, manifest):
    for entry in archive.infolist():
        parts = entry.filename.split("/")
        if (parts[0] != "extlib" or ".." in parts or "\\" in entry.filename
                or ":" in entry.filename or (entry.external_attr >> 16) & 0o170000 == 0o120000):
            raise ValueError(f"Unsafe archive entry: {entry.filename}")
        if forbidden_entry(entry.filename):
            raise ValueError(f"Retired dependency in archive: {entry.filename}")
    names = set(archive.namelist())
    missing = [name for name in manifest["required_files"] if "extlib/" + name not in names]
    if missing:
        raise ValueError("Incomplete archive: " + ", ".join(missing))
    identity = json.loads(archive.read("extlib/EXTLIB_VERSION.json"))
    if identity["package_tag"] != manifest["package_tag"]:
        raise ValueError("Archive package identity does not match the pin")


def main():
    source_root = Path(__file__).resolve().parents[2]
    manifest_path = source_root / "EXTLIB_VERSION.json"
    extlib = source_root / "extlib"
    if extlib.resolve().parent != source_root:
        print("External library cache resolves outside the checkout.", file=sys.stderr)
        return 1

    with manifest_path.open(encoding="utf-8") as stream:
        manifest = json.load(stream)

    archive = source_root / "extlib.zip"
    expected_sha256 = manifest["sha256"].lower()
    archive_ready = archive.is_file() and sha256_file(archive) == expected_sha256
    if cache_ready(extlib, manifest) and (not archive.exists() or archive_ready):
        print(f"Using external libraries version {manifest['version']}.")
        return 0

    url = manifest["url"]
    print(f"Need external libraries version {manifest['version']}.")
    try:
        if not archive_ready:
            print(f"Downloading: {url}")
            download = archive.with_suffix(".zip.tmp")
            try:
                urllib.request.urlretrieve(url, download)
                actual_sha256 = sha256_file(download)
                if actual_sha256 != expected_sha256:
                    raise ValueError(f"SHA-256 verification failed: expected {expected_sha256}, actual {actual_sha256}")
                download.replace(archive)
            finally:
                if download.exists():
                    download.unlink()
        print("SHA-256 verified.")
        with zipfile.ZipFile(archive, "r") as zip_ref:
            validate_archive(zip_ref, manifest)
            staging = Path(tempfile.mkdtemp(prefix="extlib-", dir=source_root))
            old = staging / "previous"
            installed = False
            try:
                zip_ref.extractall(staging)
                incoming = staging / "extlib"
                missing = missing_required_files(incoming, manifest)
                if missing:
                    raise ValueError("Incomplete extracted package: " + ", ".join(missing))
                (incoming / ".package-sha256").write_text(expected_sha256 + "\n")
                if extlib.exists():
                    extlib.rename(old)
                try:
                    incoming.rename(extlib)
                    installed = True
                except BaseException:
                    if old.exists():
                        old.rename(extlib)
                    raise
            finally:
                if old.exists() and not installed:
                    print(f"Previous cache preserved for recovery: {old}", file=sys.stderr)
                else:
                    shutil.rmtree(staging)
    except Exception as exc:
        print(f"External library refresh failed: {exc}", file=sys.stderr)
        return 1

    print(f"External libraries version {manifest['version']} ready.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
