# Dependency removal: Stage 6 delivery changes

Stage 6 delivery code and local Windows validation are implemented on 2026-10-28.
Subsequent Windows SP/DP matrix results and current release blockers are recorded
in [Stage 7](STAGE7.md); this report retains the Stage 6 validation scope.
The clean artifact is published as
[v82-openreader-1](https://github.com/SyazwanSamad/extlib/releases/tag/v82-openreader-1)
in the user-approved fork. The original upstream repository was read-only to the
connected account. The pin uses the new release; archive and sidecar digests,
published metadata and an unauthenticated clean download are verified.
The fresh local build used the same archive digest and package identity.

Linux/ARM package and container execution remain release gates. This report does
not establish the complete Stage 6 gate or the Stage 7 release sign-off.

## Dependency artifact

The reproducible `extlib.zip` is 26,112,105 bytes, with SHA-256:

```
72831a1b3e95910e20e24cceb6fb6c4295cfab1fade01144f2cee53c603442a3
```

Two independent repacks produced that digest. All 3,327 retained files are listed
in the artifact manifest. Boost, exprtk, LAPACK, metis, MD5 and zlib payloads are
byte-identical to authenticated upstream v82; only the embedded package identity
changes. The archive excludes the retired reader and H3D directories, SDK headers,
import/shared libraries, and their two library-specific notices. APR and its
notice are removed because its only payload was private to the retired reader.
All eleven other open-source notices are preserved, including notices for code
used by the in-tree reader. Attribution in retained source is unchanged.

`EXTLIB_VERSION.json` pins this artifact and includes the surviving platform link
inputs and notices. The old upstream archive is not a build or CI fallback.
The local ignored archive was replaced, the extracted dependency tree refreshed,
and the old reader quarantine deleted. Eight retired SDK/APR/notice entries were
also removed from the ignored old reference-binary ZIP; its seven open-source
executable entries remain byte-identical. The historical Stage 1 manifest retains
the original ZIP digest as provenance; the Stage 6 cleanup report records both
archive digests and all retained/removed entries. Historical numerical/reference evidence
is retained as data; current tests load no retired reader or SDK.

## Loader and distribution behavior

`load_extlib.py` now checks the installed package tag, its verified archive stamp,
required files, and forbidden entries. A stale cached archive also invalidates a
cache hit. Clean archives are reused after checksum verification; invalid caches
refresh through the existing downloader. Archive validation rejects retired
payloads, traversal/absolute/Windows paths, symbolic links, missing requirements
and wrong package identities before replacing the extracted tree. Extraction is
staged, and a failed promotion restores the previous tree. A checksum, download
or extraction error fails the build while preserving the previous extracted cache.
If restoration itself fails, the previous cache is kept at the reported recovery
path rather than being deleted with the temporary extraction directory.

Release and QA jobs use this loader instead of selectively unzipping the old
archive. Windows, Linux x64 and ARM64 packaging ship OpenReader beside Starter,
the CFG/messages tree, existing compiler/MPI runtimes, retained notices,
`LICENSE.md`, `COPYRIGHT.md` and the pin under `licenses/EXTLIB_VERSION.json`.
The package checker rejects retired payloads and missing reader/configuration/
notice files before upload or release. GCC runtimes keep the neutral
`extlib/runtime/<arch>` location and the corresponding notices established earlier.

H3D environment variables and loader paths, release copy steps, IDE settings,
Docker/Apptainer environment settings, and QA setup are removed. Native QA
assertions remain. Legacy H3D duplication/extraction requests now fail explicitly;
their converter and XML parsing paths are removed. The inactive upstream-only
extlib-update workflow is deleted; its three-field manifest replacement could
discard the checksum and package requirements.

The packaged GUI comes from Tools commit
`1b6bb9200ee7dca899e61c18bd982c3fb1c72fd1`, with a checked-in patch applied at all
three package assembly sites. The patch removes the H3D button/control-file
request and retired loader paths, and uses `exec` plus native runtime directories.
Existing MPI environment setup, native animation and converters remain. Pinning
the Tools revision makes patch application reproducible; failure stops packaging.
The Docker recipe also rejects retired dependency paths in its input archive and
requires the architecture's OpenReader library after extraction.

## Local verification

| Check | Result |
| --- | --- |
| Artifact | Digest and all required files verified; two repacks identical; retained component bytes unchanged |
| Cache/loader tests | Clean install/hit, case-insensitive digest identity, stale extracted SDK and cached archive refresh, 16 invalid archives, rollback and preservation after failed rollback pass |
| Full archive cache exercise | Local file-URI clean/hit/stale/error checks pass; the published unauthenticated pin also downloads, validates, extracts and hits its cache |
| Fresh build | Starter/OpenReader built from a new Windows Release build tree with no SDK payload; SMP and Intel MPI Engine rebuilds pass |
| Existing suites | All 149 checks pass, including bounds-checked integration, mode-1/mode-2 numerical checks and same-build continuation; the extra check group covers package guards |
| Repository decks | Five model comparisons, four exact Engine histories, and both rejected-input cases pass against frozen Stage 1 |
| Extracted Windows package | Four physical accelerometer/friction runs pass with one thread and one/two MPI ranks; every history maximum difference is zero |
| Native animation/converters | Two-rank decompressed animation bytes match Stage 5 exactly; native VTK/CSV converters run successfully |
| Removed output | Packaged Engine rejects the retired request with exit 2 before integration |
| Runtime modules | Starter, serial Engine, MPI ranks and converters sampled; no retired library loaded; observed OpenReader/Intel runtime modules resolve inside the extracted package |
| Delivery checks | Windows/Linux/ARM layout guards, nine workflow parses, three release-assembly Bash syntax checks, GUI patch applicability and six GUI environment branches pass |
| Source/binary inspection | Shared-result source checks, four PE import/export audits and all three build-graph audits pass; current launcher SDK paths absent |

OpenReader build ID is `or_20261028195701_2fef8dac`. Toolchain is Intel ifx/icx
2025.2, MKL 2025.2, VS 2022 and Intel MPI 2021.16. The isolated package runtime
path contains its `exec`, its bundled Intel runtime directory, and Windows system
directories; it contains no compiler-installation or SDK directory. Sampling
tracks launcher descendants even after a short-lived parent exits.
An immediate cache-refresh test encountered a transient Windows rename denial;
the loader returned nonzero and restored the previous cache. A retry and the
final full-archive test passed. Build/package helper syntax also remains compatible
with Python 3.6; native execution in the Linux CI image is still unverified.

The local Windows package contains DP SMP/MPI binaries, the patched GUI and
converters; hosted CI supplies the additional release variants. Its archive hash,
complete file inventory, inputs, physical comparison arrays, module paths and
logs are recorded in [the evidence manifest](stage6/windows_dp_smp/manifest.json).
Historical Stage 1-5 evidence files are unchanged.

## Reproduction and publication handoff

Use a fresh output path and the authenticated upstream v82 source archive:

```powershell
python Compiling_tools/script/repack_extlib.py path/to/upstream-extlib.zip path/to/clean-extlib.zip
python qa-tests/dependency_removal/test_reader_build.py
python Compiling_tools/script/load_extlib.py
python Compiling_tools/script/check_package.py path/to/OpenCourant_win64.zip --arch win64
python Compiling_tools/script/check_package.py path/to/OpenCourant --arch win64
```

Use the [reader commands](../reader/README.md) for the 149-check suite. Release
assembly applies `Compiling_tools/patches/openreader_gui.patch` to the pinned
Tools checkout, then runs:

```powershell
python qa-tests/dependency_removal/test_packaged_gui.py --gui TOOLS/openradioss_gui
```

The published assets are `extlib.zip`, `extlib.manifest.json` and `SHA256SUMS`.
Their local copies and release notes are in `cbuild_dependency_stage6/`.
The fork's metadata commit is `07d6faee9a79c7126c5b3c65f3e895fd09044753`;
its current metadata/notices describe the clean package. Original open-source
attribution remains, and obsolete SDK/APR notices are excluded from its current tree.
The OpenCourant solver worktree has not been committed or pushed in this stage;
no solver binaries or containers have been released or deployed.

Native Linux/ARM package and container execution is unavailable on this host
(Docker is absent and WSL is not installed). Hosted CI, SP, multiple OpenMP
threads, broader MPI/R2R, old multi-domain checkpoints, implicit/modal, coupled/
user-library workflows, full miniqa and performance remain Stage 7 gates.
