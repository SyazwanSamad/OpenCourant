"""Repack the authenticated upstream v82 archive without retired binary dependencies."""

import argparse
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED

from load_extlib import forbidden_entry, sha256_file


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    expected = "2d0365018e67dd4813e6a2cf2ebf19d00d4771aa1aeb9b9706b7ea45fbb56982"
    if sha256_file(args.source) != expected:
        parser.error("source must be the authenticated upstream v82 extlib.zip")
    if args.output.exists():
        parser.error("output already exists")
    identity = {"version": "82-openreader-1", "package_tag": "v82-openreader-1",
                "upstream_version": "82", "upstream_sha256": expected}
    retained = []
    with ZipFile(args.source) as old, ZipFile(args.output, "w", ZIP_DEFLATED, compresslevel=9) as new:
        for entry in sorted(old.infolist(), key=lambda item: item.filename):
            if entry.is_dir() or forbidden_entry(entry.filename) or entry.filename == "extlib/license/apr_license.txt":
                continue
            data = old.read(entry)
            if entry.filename == "extlib/EXTLIB_VERSION.json":
                data = (json.dumps(identity, indent=2) + "\n").encode()
            info = ZipInfo(entry.filename, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = entry.external_attr
            new.writestr(info, data, compresslevel=9)
            retained.append({"path": entry.filename, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()})
    report = {**identity, "archive_sha256": sha256_file(args.output), "files": retained}
    args.output.with_suffix(".manifest.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"{args.output}: {report['archive_sha256']} ({len(retained)} files)")


if __name__ == "__main__":
    main()
