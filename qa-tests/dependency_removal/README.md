# Dependency removal: Stage 1 baseline

This is the frozen pre-change baseline. For current reader behavior, see
[Stage 5 results](STAGE5.md); the automatic rigid-part bypass and mode-2 rejection
described below apply to the Stage 1 build only.
The reproduction commands below describe the historical run; current collectors
use OpenReader and frozen data only, as documented in Stage 3.

Captured on 2026-10-28 at commit
`d0a844f7270ae3c0666c1360700be42708a7694b`.
The Windows x64, double-precision SMP baseline is complete. Solver source,
configuration, original decks, and existing expected results were not changed.
This establishes comparison evidence; it does not establish complete OpenReader
parity or authorize skipping the later removal gates.

## Build identity and controls

- Intel Fortran `ifx` and C/C++ `icx` 2025.2.0, build 20250605;
  MSVC tools 14.44.35215 and CMake 3.31.6-msvc6.
- Python 3.11.9, NumPy 1.26.4; the installed time-history reader's source hash is
  recorded in the numerical report.
- HM Reader: extlib v82, build `20260918_f907fe76`.
- OpenReader: `or_20261028082526_d0a844f7`.
- The configuration manifest contains 2,495 CFG/message files. Its aggregate
  hash, all 3,460 fixture/configuration file hashes, executable/DLL hashes, and
  CMake settings are retained in the evidence directory.

Reader, Starter, and serial Engine were refreshed from the existing Windows
build trees. `build_integration.py` then built isolated Starter/driver pairs
against OpenReader and v82, recompiling the five existing rigid-body integration
modules with bounds checking and conversion enabled. The same remaining Starter
objects and Engine were used for paired comparisons.

The ordinary `exec/starter_win64.exe` remains OpenReader-linked with its automatic
rigid-part bypass. Positive rigid-part results below use the isolated integration
executables; they do not show that production OpenReader conversion is enabled.
Structured ALE remains disabled by the existing build setting.

## Results

| Existing suite | Passing checks |
| --- | ---: |
| v82 reader reference contract | 14 |
| OpenReader contract, including two expected mode-2 rejections | 14 |
| Model/include/part API groups | 5 |
| Model loading, error propagation, default Starter smoke/guard | 18 |
| Contact-group behavior | 6 |
| Rigid conversion lifecycle/comparison checks | 12 |
| Bounds-checked Starter integration | 39 |
| Numerical/structural checks, including the documented reference discrepancy | 49 |
| **Total** | **157** |

The numerical suite includes 28 Engine runs, 20 structural/error cases, and one
documented v82 units discrepancy. It checks generated versus explicit rigid
bodies, translation, rotation, forces, offsets, sensors, missing main nodes,
added mass/inertia, and units. The maximum recorded position error was
`2.45005e-6 m`, below the existing `3e-5 m` limit. Existing velocity and energy
limits remain `3e-4 m/s` and `3e-5 J`; reader-to-reader numerical comparison uses
`rtol=1e-5`, `atol=1e-6`. No expected values or tolerances were loosened to accept
a solver difference.

Additional complete-deck comparisons:

| Model | Nodes | Engine runs | Warning totals, v82 / OpenReader | Result |
| --- | ---: | ---: | ---: | --- |
| Accelerometer | 207 | Both readers | 2 / 1 | Counts, rigid-body initialization, and all recorded histories match |
| TYPE7 friction | 12 | Both readers | 3 / 2 | Counts and all histories match, including declared interface/wall force groups |
| Three-node shells | 32 | Both readers | 1 / 0 | Counts and all recorded histories match |
| 2D ALE | 306 | Both readers | 1 / 0 | Counts and all recorded histories match |
| Minimal LS-DYNA contact/include | 8 | Starter only | 2 / 2 | Counts and restart generation match |

All eight native-deck Engine histories had **zero absolute difference** between
readers at the recorded samples. The histories are compared as validated packed
records because the installed reader has a known named-group offset issue for
the current global-variable layout. The raw files retain their original headers.
Secondary-node lists in the JSON summaries use counts and hashes of sorted IDs;
the comparison itself checked the complete lists.

The warning difference is v82 warning `100214` for an unsupported `/IOFLAG`
field. Existing physical/model warnings remain; this stage did not suppress or
fix them. Diagnostic-ID lists can include repeated IDs in the listing summary;
`warning_total` records the solver's final count.

Both readers also rejected a missing native input and a missing LS-DYNA include
with exit code 2 and no restart: four additional failure checks. The larger
configuration-failure/reload tests remain in the existing OpenReader suite.

Four explicit-body checkpoint cases cover both readers with H3D enabled and
disabled. Each runs to 0.05 s and continues from the resulting checkpoint to
0.1 s. Continuation position, velocity, energy, and reader/H3D comparisons pass.
Twelve restart files are frozen, including initial, intermediate, and final
checkpoints. The two H3D-enabled cases generate H3D files that H3D Reader opens,
reads through its string-table API, and closes successfully (29 strings each).
These files contain no `ZCHKSM_` tags, so populated checksum-tag comparison is
not established by this baseline.

The collector was corrected during capture to read continuation `T02`, use the
existing time-sampling margin, and request `/H3D/NODA/DIS`. The focused checkpoint
cases were rerun successfully. Initial collector failures and the rejected
`DISP` spelling remain in the ignored raw evidence; no solver change was needed.
Runtime observations are retained for provenance, not treated as benchmarks.

## H3D inventory and migration decisions

The tracked deck/configuration/launch inventory has **zero explicit `/H3D`
directives**, 273 text references, and one mixed-card review candidate. It scans
tracked native/keyword decks, schemas/messages, documentation, launch settings,
workflows, and modern/legacy QA scripts. Reference `.out` timing statistics are
not input requests and are excluded. Generated baseline inputs and their hashes
are retained separately.

| Request or integration | Finding and later migration |
| --- | --- |
| Generated `/H3D/DT` | Baseline fixture only. Use `/ANIM/DT` for native snapshots; validate the intended sample schedule. |
| Generated `/H3D/NODA/DIS` and `/H3D/NODA/VEL` | Baseline fixture only. Preserve displacement/velocity through native animation and time histories; verify any VTK conversion separately. |
| `qa-tests/miniqa/IMPOSED/IMPDISP_FGEO/data/mapSimple_0001.rad:17` | Plain `/STOP`, not `/STOP/LSENS`; preserve its existing controls. No active H3D sensor request was found. |
| `/MONVOL/FVMBAG1` / `FVMBAG2` `IH3D_FLAG` | Defined in the 2023 schemas, in columns 41-50 of the first data card after the title. No matching active tracked deck was found. Preserve other airbag fields; an equivalent native output has not been validated. |
| H3D sensor/report options | No active tracked deck request found. Recognition and explicit removal diagnostics still require dedicated later-stage cases. |
| `RAD_H3D_PATH` and H3D loader paths | Present in IDE settings, launch/environment helpers, workflows, and containers. Remove when the integrations are removed. |
| Legacy QA H3D extraction | `or_qa_script`, `or_QA.constants`, and `or_radioss.pl` contain H3D file/extraction handling, including `h3dtoxml_Linux_I.exe`. Remove/replace this path without altering native comparison and restart cleanup. No active tracked H3D extraction request was found. |

The complete inventory records source paths, line numbers, and card context in
[`h3d_inventory.json`](baseline/windows_dp_smp/h3d_inventory.json). It identifies
existing requests, not every possible H3D capability a user might request. The
archived H3D fixture inputs remain intentionally unchanged as pre-removal evidence.

## Capability gaps carried into later stages

1. `IRIGID=2` connected-region conversion is still rejected by OpenReader:
   `flag_two_single` and `disconnected_two` reproduce the gap. v82 generates one
   and two bodies respectively. Production OpenReader also keeps its broad
   rigid-part bypass, including for the tested mode-1 implementation.
2. v82 loses the generated rigid body's explicit unit ID in the existing units
   case. Preserve OpenReader's physically validated behavior; do not copy that
   reference defect. The numerical report retains the discrepancy and oracle.
3. Structured-ALE mesh generation has no new dynamic validation here. The
   default rejection and missing in-tree generator remain a support decision
   and implementation gate.
4. LS-DYNA include-transform query checks use known fixture paths as their
   oracle; they are not a claim of full v82 conversion parity. The paired contact
   fixture covers additional successful conversion/initialization.
5. Linux x64/ARM64, single precision, MPI Engine execution, R2R, Python-controlled
   physics, implicit paths, and the full miniqa suite were not rerun.
6. H3D sensor/report/airbag flags, populated H3D checksum tags, and every H3D
   result quantity are not covered by the small positive H3D fixture. Later
   cleanup must preserve shared calculations and add the relevant focused tests.

## Evidence

The versioned [`baseline/windows_dp_smp/`](baseline/windows_dp_smp/manifest.json)
contains the manifest and SHA-256 values, suite/model/numerical reports, 26 reader
snapshots (14 v82 and 12 successful OpenReader cases), compressed input manifests,
12 checkpoints, two H3D output files, 36 raw native/numerical history files, logs,
and PE dependency listings. Archive CRCs, checkpoint counts, and artifact hashes
were checked after capture. No executable, DLL, import library, or SDK header is
included in those versioned archives.

Full raw outputs and the ignored local reference binary archive remain under
`cbuild_dependency_baseline_20261028/`. Preserve that directory while later stages
need the original executables or full listings.
It is comparison evidence, not a directory to include in future solver packages.

## Reproduce

Use the pinned source/configuration and extlib v82. In an initialized Windows
x64 Visual Studio/Intel compiler/MKL command prompt with CMake/Ninja, Python,
NumPy, and the existing `vortex_radioss` reader available:

```bat
cmake --build reader/cbuild_win64 --parallel 4
cmake --build starter/cbuild_starter_win64_ninja --parallel 4
cmake --build engine/cbuild_engine_win64_ninja --parallel 4
python qa-tests/reader/rigid_parts/build_integration.py --starter-build starter/cbuild_starter_win64_ninja --output cbuild_baseline_repeat/binaries
python qa-tests/dependency_removal/capture_baseline.py --binaries cbuild_baseline_repeat/binaries --output cbuild_baseline_repeat/capture
python qa-tests/dependency_removal/compare_decks.py --binaries cbuild_baseline_repeat/binaries --output cbuild_baseline_repeat/decks
```

The commands reuse the preconfigured build trees described above. Configure them
using the project's documented Windows build procedure on a fresh checkout.
Output directories must be new, protecting previous evidence. The comparison
uses repository fixtures and requires no private model inputs.

Compare physical values and supported input behavior, not byte identity of
timestamped binaries, H3D files, or restarts. The capture scripts intentionally
use the old libraries during Stage 1; remove their runtime-reference paths when
Stage 3 converts these tests to standalone recorded/analytic oracles.
