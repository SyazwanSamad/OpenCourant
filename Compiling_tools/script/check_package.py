"""Reject retired dependencies and incomplete reader delivery in solver packages."""

import argparse
from pathlib import Path
from zipfile import ZipFile

from load_extlib import forbidden_entry


def check_names(names, arch):
    forbidden = [name for name in names if forbidden_entry(name)]
    if forbidden:
        raise ValueError("Retired dependency in package: " + ", ".join(forbidden))
    reader = f"open_reader_{arch}.dll" if arch == "win64" else f"libopen_reader_{arch}.so"
    suffix = ".exe" if arch == "win64" else "_gf"
    required = ["exec/" + reader, "exec/starter_" + arch + suffix, "exec/engine_" + arch + suffix,
                "LICENSE.md", "COPYRIGHT.md", "licenses/boost_license.txt", "licenses/EXTLIB_VERSION.json"]
    missing = [name for name in required if "OpenCourant/" + name not in names]
    for folder in ["hm_cfg_files/config/", "hm_cfg_files/messages/"]:
        if not any(name.startswith("OpenCourant/" + folder) and not name.endswith("/") for name in names):
            missing.append(folder)
    if missing:
        raise ValueError("Incomplete package: " + ", ".join(missing))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package", type=Path)
    parser.add_argument("--arch", required=True, choices=["win64", "linux64", "linuxa64"])
    args = parser.parse_args()
    if args.package.is_dir():
        names = {"OpenCourant/" + path.relative_to(args.package).as_posix() + ("/" if path.is_dir() else "")
                 for path in args.package.rglob("*")}
    else:
        with ZipFile(args.package) as archive:
            if archive.testzip() is not None:
                raise ValueError("Corrupt package archive")
            names = set(archive.namelist())
    check_names(names, args.arch)
    print(f"PASS {args.arch} package: OpenReader, CFG/messages and notices present; retired dependencies absent")


if __name__ == "__main__":
    main()
