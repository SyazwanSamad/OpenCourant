# Dependency removal: Stage 3 OpenReader-only Starter

Historical Stage 3 record. [Stage 5](STAGE5.md) records the current H3D removal
and its serial/MPI, native-output, and checkpoint checks.

Stage 3 code is implemented and validated on Windows x64 DP SMP, 2026-10-28.
Starter builds and links only OpenReader. The Windows cutover checks pass without
HM Reader in `extlib/` or on the normal library search paths. Linux x64/ARM64,
hosted CI, and the clean dependency-archive gate remain open; this is not a
cross-platform release sign-off. At this capture, Stages 4-7 had not started.

## Changes

- Starter's CMake graph adds the existing reader project and links its target
  directly. Reader objects depend on external-header preparation, and Starter
  links after the reader. Root builds share the extlib target with Engine.
  The standalone reader entry point is retained. Reader intermediate libraries now stay
  inside their own build tree; parent Starter C-source lists cannot leak into
  reader targets.
- All eight Starter compiler configurations drop HM Reader/APR linkage and the
  reader-selection branch. Root/component scripts, IDE, and CI use OpenReader
  automatically. `USE_OPEN_READER`, `-open_reader`, legacy include/part options,
  rigid-part bypass, and the structured-ALE build toggle are retired. Cached
  legacy variables cannot select the external library.
- The 40 adapters move from `starter/source/devtools/hm_reader/` to
  `starter/source/devtools/reader/`. Compiler lists and generated caller metadata
  throughout Starter/shared sources follow the move. Useful `HM_*` Fortran
  helpers and the in-tree CFG/message tree remain; their names do not imply an
  external library dependency. Legacy branches and the obsolete guard driver
  are removed.
- Build identity uses `open_reader_build_id` and `open_reader_version.cpp`.
  In-tree callers are updated. External tools using the former `hm_build_id`
  export must update to the new name; the buffer signature is unchanged.
- Tests/builders use OpenReader only. Fourteen original snapshots and 23
  additional ownership/connectivity snapshots preserve v82 provenance as data.
  Generated/explicit numerical controls use the same in-tree reader, retaining
  independent analytic assertions. Whole-deck comparisons use frozen Stage 1
  model counts, initialization, memberships, and raw histories.
- CI and package launch paths find OpenReader in `exec/`. Release jobs already
  transfer that directory and now omit external-reader copies. GCC runtimes move
  to `extlib/runtime/<arch>/`; matching package paths and notices are updated.
  Containers, QA helpers, IDE environment, and installation instructions follow
  those paths. H3D remains available for later-stage work.
- The existing dependency pin no longer requires HM Reader, and extraction skips
  its directory. A network-free test verifies retained headers/H3D files, absent
  reader binaries, and a successful second cache lookup. No new dependency or
  reader replacement framework was added.

## Issues found during integration

The combined build uses Starter's Intel C++ compiler, while the former standalone
Windows reader used MSVC. Five superscript character literals in the unit parser
were rejected by Intel C++; they now spell the existing single-byte operators
explicitly. The legacy unit format is preserved.

The first regression pass also exposed an access violation after a missing
configuration/message directory. Both native model creation/loading paths now
stop when message-file initialization fails and print the reader diagnostic
before entering CFG initialization. Missing configuration, both loader entry
points, and the complete Starter error path pass after the fix. Other initially
passing suites were rerun against the final DLL.

Structured-ALE generation remains unsupported. Native loading rejects its card
with file/line context, including in includes. The defensive Starter adapter
also rejects it; its unreachable external generator call is removed. Ordinary
ALE is separate and remains covered by the unchanged 2D ALE fixture.

## Verification

Clean source build: `cbuild_dependency_stage3/clean-starter`, Intel ifx/icx
2025.2.0, MSVC tools 14.44.35215, CMake 3.31.6-msvc6, Windows x64 DP SMP.
OpenReader: `or_20261028105100_d0a844f7`. The Engine binary and the 2,495-file
CFG/message tree retain their Stage 1/2 hashes. The old local reader payload was
quarantined under an ignored evidence directory, outside runtime search paths;
it was not loaded for the final build/tests.

| Current suite | Passing checks |
| --- | ---: |
| Dependency extraction and build invariants | 3 |
| Starter API audit: 84 APIs, four spellings; 11 local calls | 1 |
| Original frozen rigid-part snapshots | 14 |
| Include/part/model API groups | 2 |
| Loading, failures, default Starter, unsupported ALE | 27 |
| Contact groups and reload | 4 |
| Conversion lifecycle and frozen comparisons | 32 |
| Bounds-checked Starter integration | 30 |
| Numerical: 19 Engine and ten structural/error cases | 29 |
| Mode-2 generated/explicit Engine runs | 6 |
| **Total** | **148** |

Additional checks:

- Five whole-deck cases pass against frozen Stage 1 expectations. Accelerometer,
  TYPE7 friction, three-node shells, and 2D ALE each complete an Engine run with
  **zero absolute difference** in the recorded histories. Minimal LS-DYNA
  contact/include passes Starter. Two failed-input/include cases exit with code
  2 and no restart.
- H3D off/on cases both pass two-segment continuation to 0.1 s. H3D Reader opens
  the generated file. These remain same-build restart checks; old-format restart
  consumption after H3D removal is a later gate.
- `dumpbin` import inspection finds `open_reader_win64.dll` in Starter and no
  HM Reader import in either executable/library dependency list. Loaded-module
  inspection also finds OpenReader and no HM Reader.
- Root CMake configures Starter and Engine together, even with an obsolete
  `USE_OPEN_READER=0` and legacy include option supplied. Those variables are
  reported unused and the graph still links OpenReader. Root Windows batch
  dispatch was checked with isolated mock build tools; the clean native build
  above used component CMake. Linux shell syntax and workflow YAML parsing pass.
- Python syntax, diff whitespace, frozen evidence checksums, and removed-model
  reference scans pass. Existing tolerances and physical expectations were not
  loosened.

Lower test/run counts than Stage 2 reflect removal of duplicate live-v82 runs and
the obsolete guard/discrepancy execution. The underlying reference observations
remain in frozen data. They do not indicate lost OpenReader scenario coverage.

## Reproduction and evidence

Use the [current reader commands](../reader/README.md). With the initialized
Windows toolchain and a fresh output directory:

```powershell
python qa-tests/reader/rigid_parts/build_integration.py --starter-build cbuild_dependency_stage3/clean-starter --output cbuild_reader_integration
python qa-tests/dependency_removal/capture_baseline.py --binaries cbuild_reader_integration --starter-build cbuild_dependency_stage3/clean-starter --output cbuild_reader_verified
python qa-tests/dependency_removal/compare_decks.py --binaries cbuild_reader_integration --output cbuild_reader_decks
```

The collector retains its historical filename but now runs the current reader
only. It does not modify the Stage 1/2 frozen artifacts.
[Stage 3 evidence](stage3/windows_dp_smp/manifest.json) records reports, source and
binary hashes, dependency inspection, configuration/build/test logs, and generated
input hashes. Raw runs remain in ignored `cbuild_dependency_stage3/`.
The working tree is based on `d0a844f7270ae3c0666c1360700be42708a7694b`; that
commit alone predates this implementation.

## Remaining gates and limits

Linux x64/ARM64 runtime/link behavior, SP, MPI/R2R, hosted workflows, containers,
assembled release packages, full miniqa, all element formulations, and large-model
performance remain unverified. Windows import checks do not establish Linux
loader/rpath compatibility. Structured-ALE mesh generation is not supported.

The pinned upstream extlib ZIP still contains the retired reader's bytes. Current
loader/CI extraction excludes them and no current test uses them as an oracle,
but the archive is still downloaded as a whole. Stage 6 must publish and pin a
filtered artifact and validate stale-cache/package cleanup before claiming no
download or shipped-payload dependency. The final cross-platform Stage 3 cutover
gate remains pending those platform checks; HM Reader linkage and test loading
have been removed from the current source paths.
