# Remove HM Reader and H3D dependencies

Status: Stage 1 baseline captured and Stages 2-5 implemented and validated on
Windows x64, double-precision SMP, on 2026-10-28. Stage 5 also validates shared
element queries and native contact/sensor outputs with two Intel MPI ranks. See the
[Stage 1 baseline](../qa-tests/dependency_removal/README.md) and
[Stage 2 results](../qa-tests/dependency_removal/STAGE2.md), and
[Stage 3 results](../qa-tests/dependency_removal/STAGE3.md), and
[Stage 4 results](../qa-tests/dependency_removal/STAGE4.md), and
[Stage 5 results and limits](../qa-tests/dependency_removal/STAGE5.md).
Stages 6-7 remain. Cross-platform validation remains a cutover gate.

## Target behavior

Build, package, and run Starter and Engine without HM Reader, H3D Writer, H3D
Reader, their headers, or their runtime loaders. Use the existing in-tree
OpenReader as the sole model reader. Preserve model interpretation, solver
physics, Python element queries, supported restart behavior, native animation,
time histories, and other independent outputs.

Removing H3D also removes H3D file output and H3D checksum inspection. Those
workflows cannot remain compatible without another H3D implementation. This plan
uses existing native animation and time-history output, with the existing VTK/CSV
conversion tools where appropriate. It does not introduce a replacement format,
an automatic output translator, or an H3D compatibility stub.

An input that requests a removed H3D feature must fail during input validation
with the input location and an actionable diagnostic. Do not run successfully
while silently dropping requested results. Migrate affected repository examples
and regression decks explicitly; document fields without an equivalent output.

Other proprietary compiler/math/MPI libraries are outside this change.

## Findings that determine the order

- OpenReader exists under `reader/`; Stage 3 makes its existing target a required
  Starter dependency in root/component CMake, scripts, CI, and IDE builds. Reader
  selection and legacy compatibility branches are retired.
- Stage 2 implements `IRIGID=2` connected-region conversion alongside mode 1 and
  removes Starter's automatic OpenReader rigid-part bypass after Windows
  numerical validation. Focused fixtures do not establish general reader parity
  on every platform or for every input formulation.
- `/ALE/STRUCTURED_MESH` remains unsupported and fails during native loading,
  including in includes. Stage 3 removes the unreachable external generator call
  and its build toggle while retaining a defensive Starter diagnostic. Enabled
  generation has no validated baseline here and is not claimed by this plan.
- `funct_python_update_elements.F90` calls `h3d_shell_scalar_1`,
  `h3d_solid_scalar_1`, and `h3d_quad_scalar_1`. These contain ordinary element
  result calculations as well as output-specific branches. Deleting the H3D
  directory immediately would break Python queries.
- `redkey1_h3d.F` also parses `/ANIM`, `/STATE`, and `/DYNAIN` keyword families
  through `freform.F`. Its filename does not make its whole implementation
  disposable.
- `H3D_DATA` participates in allocation, contact/force collection, sensors,
  communication, output scheduling, and restart records. It occurs throughout
  Engine, including `resol.F`, `resol_alloc.F90`, and `rdresa.F`.
- Release jobs place GCC runtime libraries inside `extlib/hm_reader/`. Removing
  that directory without relocating those runtimes would break Linux packages.
- `extlib/` and `extlib.zip` are ignored by Git. The pinned download and release
  packaging must change; deleting local files alone cannot remove the dependency.

Prior evidence and its limits are recorded in
[the OpenReader plan](OpenReader_implementation_plan.md),
[reader regression documentation](../qa-tests/reader/README.md). Re-run the relevant checks on
the removal branch; their recorded results are not validation of this change.

## Scope: every affected surface

| Surface | Locations to audit and update |
| --- | --- |
| Model reader and exports | `reader/CMakeLists.txt`, `reader/CMake_arch/`, `reader/source/solver_interface/`, and the existing CFG/SDI/LS-DYNA implementations under `reader/source/` |
| Starter callers and adapters | `starter/source/devtools/hm_reader/`, `starter/source/starter/starter0.F`, `contrl.F`, reader wrappers throughout `starter/source/`, `starter/share/modules1/`, rigid bodies, includes/submodels, and error propagation |
| Reader configuration | `hm_cfg_files/config/`, `hm_cfg_files/messages/`, `RAD_CFG_PATH`, and message generation in `starter/CMakeLists.txt` |
| H3D SDK integration | `common_source/output/h3d/`, including `h3d_dl.c`, `h3dreader_dl.c`, C++ bridges, and SDK includes |
| Engine output and shared calculations | `engine/source/output/h3d/`, `engine/share/modules/h3d_mod.F`, `h3d_inc_mod.F`, input parsing, Engine initialization/time loop, animation, force/contact paths, element routines, implicit paths, sensors, reports, and MPI communication |
| Python integration | `engine/source/tools/curve/funct_python_update_elements.F90`, `python_register.F90`, `common_source/modules/python_element_mod.F90`, and their callers/serialization |
| Checksums | `starter/source/output/checksum/checksum_list.cpp`, `starter/share/includes/checksum_list.h`, and related checksum modules/callers |
| Restart and data layouts | `starter/source/restart/ddsplit/`, `engine/source/output/restart/`, shared output/element modules, common blocks, and serialized buffer lengths/offsets |
| Builds | Root, Starter, Engine, and reader CMake files; every architecture/compiler configuration; `legacy_fortran.cmake`; root/component build scripts; `CMakeSettings.json`; developer launch settings |
| Dependency delivery | `EXTLIB_VERSION.json`, `Compiling_tools/script/load_extlib.py`, the extlib release artifact, local ignored copies, licenses, and source/binary release manifests |
| QA and fixtures | `qa-tests/reader/`, `qa-tests/miniqa/`, `qa-tests/qa_tools/`, legacy `qa-tests/scripts/` H3D/XML extraction, CTest lists, regression reference results, and test-only integration builders |
| Distribution and documentation | All relevant `.github/workflows/`, `containers/solver/Dockerfile`, `Apptainer/`, generated environment scripts, release notes, `HOWTO.md`, `INSTALL.md`, and examples |

Audit actual declarations and callers before changing a signature. Generated
caller comments and stale compiler lists also need updating, but are not proof
of executable dependencies. A broad `h3d` search also matches unrelated names
such as `ISPH3D`; retain the SPH/animation behavior those names describe.

## Implementation sequence

### 1. Freeze a behavioral baseline

1. Record the commit, toolchain, precision, reader/build IDs, configuration tree,
   input hashes, and numerical tolerances used for comparisons.
2. Run the current bundled-reader build and the existing OpenReader build on the
   same representative native and LS-DYNA decks. Include includes/transforms,
   submodels, units, contacts, rigid bodies, materials, and failed-input cases.
3. Record model counts, connectivity, entity IDs/mappings, masses/inertias,
   warnings/errors, restart behavior, and Engine displacement/velocity/force/
   energy histories. Keep performance observations separate from correctness.
4. Capture approved reader reference snapshots and representative old restart
   fixtures before removing the binaries. Use the existing analytic/explicit-body
   controls as independent numerical checks.
5. Identify every H3D request in regression decks, embedded Engine inputs, airbag
   flags, sensor/report options, and example launch settings. Record which native
   output preserves each test's original purpose.

Gate: reproducible references and a concrete capability-gap list exist. A
successful link or a nonempty restart file is insufficient evidence of parity.

### 2. Complete OpenReader coverage before removing HM Reader

Implemented and validated for Windows x64 DP SMP; see the linked Stage 2 report.
Linux x64/ARM64, single precision, and MPI execution remain unverified. These
checks must pass before the cross-platform Stage 3 cutover is accepted.

1. Compare Starter's actual C/C++ entry-point calls with OpenReader's exports on
   each platform. Fix missing symbols, calling conventions, string lengths,
   selection/iterator behavior, and failure propagation in the existing reader.
2. Implement and validate `IRIGID=2` connected-region conversion. Extend the
   existing rigid-part fixtures for connected/disconnected parts, shared nodes,
   empty parts, explicit bodies, IDs, includes/submodels, and units. Verify
   evaluation counts agree with creation and preserve bounds/error checks.
3. Re-run mode-1 and mode-2 complete Starter/Engine cases against explicit-body
   and reference controls. Remove the automatic rigid-part bypass only after
   those checks pass.
4. Resolve structured-ALE support explicitly. The default already rejects it;
   do not present that as a new regression or as completed support. If preserving
   the validated enabled configuration is required, implement its existing
   `cpp_sale_mesh_create` contract in OpenReader and verify generated coordinates,
   connectivity, ownership, units, and an Engine run before cutover. Keep an
   explicit failure for unsupported input while that work is incomplete.
5. Exercise native and LS-DYNA regression models beyond startup smoke checks.
   Fix demonstrated parser/conversion differences at their shared
   source, including contact groups and include/model reload behavior.

Gate: supported model workflows pass with OpenReader, including previously
supported rigid-part modes. Any unresolved supported capability blocks the
no-regression cutover; it cannot be replaced with a successful no-op.

### 3. Make OpenReader the only reader

Implemented and validated on Windows x64 DP SMP without HM Reader on the library
search paths. All 148 current checks pass; native histories match the frozen
baseline. Linux x64/ARM64 and hosted CI execution remain unverified. The current
pinned archive still contains excluded vendor-reader bytes; Stage 6 must replace
that artifact before claiming download/package dependency absence.

1. Use the existing reader target/build procedure for all Starter entry points,
   including direct/root CMake, shell/batch scripts, CI, and IDE configurations.
   Ensure extlib headers are ready before reader compilation and the reader is
   built before Starter links. Reuse its current target/library names.
2. Link only OpenReader in every Starter compiler configuration. Remove the
   HM Reader link branches and legacy API/bypass options once their callers use
   validated implementations. Retire the reader-selection switch; no production
   build may select or fall back to the old library.
3. Move the retained `starter/source/devtools/hm_reader/` adapters to a neutral
   reader directory and update build paths and caller metadata. Preserve useful
   reader-independent `HM_*` helper APIs where a rename would only create churn:
   after retargeting, these are in-tree helpers, not calls to an external HM
   Reader. Remove vendor-specific identity/version code and obsolete adapters.
4. Keep the in-tree CFG/SDI schemas and message data required by OpenReader.
   `hm_cfg_files` and historical helper names alone are not evidence of a
   proprietary binary dependency. Do not delete input definitions by substring.
5. Convert reader tests and integration builders from runtime `--reference`
   comparisons/two-reader executables to checked-in expected results and analytic
   controls. Retain fixture provenance as data/documentation. Final CI must not
   load or download the removed reader, even as a test oracle.

Gate: a clean Starter build and reader regression run succeed with no HM Reader
installed or discoverable. Loader paths and shipped OpenReader dependencies work
on Windows, Linux x64, and Linux ARM64.

### 4. Preserve shared behavior currently housed in H3D code

Implemented on Windows x64 DP SMP, with two-rank Intel MPI query comparisons.
The shared arithmetic, native parser, contact helpers, coordinate transform, and
nodal reduction have neutral owners. Serial/MPI queries and histories match
pre-refactor results exactly; native output and old-checkpoint continuation pass.
H3D functionality and its active state remain until Stage 5.

1. Move the existing shell/solid/quad scalar calculations used by Python into
   the existing element-result/tools area. Retain the arithmetic, validation,
   error handling, and ordering. Remove H3D writes, SDK types, part-selection
   arguments, and writer-only buffers from the retained paths. Update every
   caller rather than leaving dummy H3D arguments or loaders.
2. Rename the internal Python keyword field from `h3d` to a neutral result name.
   Preserve public Python quantity names and the existing serialized width/order
   unless a deliberate format migration is separately tested. Verify shell,
   triangle, solid, and quad queries, including multi-domain synchronization and
   queries used to drive loads or sensors.
3. Retain and rename the shared keyword parser in `redkey1_h3d.F`. Test `/ANIM`,
   `/STATE`, and `/DYNAIN` parsing and their existing validation. Retain H3D
   dispatch until Stage 5 removes that functionality. Audit remaining helpers
   under H3D directories for other callers.
4. Classify `H3D_DATA` members and related flags by actual consumers. Delete
   unreferenced state now and retire active writer-only state with the writer
   in Stage 5; keep calculations/buffers needed by animation, OUTP, time
   histories, Python, reactions, failure/sensor logic, or coupling in their
   existing generic modules. Do not move the whole H3D database under a new name.
5. For every changed collection/allocation predicate, preserve all remaining
   demand terms, indexing, initialization, and MPI reductions. Check force and
   friction-energy paths and the matching restart initialization in particular.

Gate: Python element queries, ordinary output parsing, contact/reaction histories,
and sensor/load behavior match the baseline without using H3D library functions.

### 5. Remove H3D functionality and its remaining callers

Implemented and validated on Windows x64 DP SMP and focused two-rank Intel MPI
cases. SDK integration and output functionality are removed; unsupported requests
fail explicitly. Native output/checksums, query-driven loads and old serial
checkpoint continuations pass. Ignored SDK payloads and delivery plumbing remain
Stage 6 work; this is not a clean-package or cross-platform release sign-off.

1. Add the early unsupported-feature diagnostics before removing the old
   parsers. Cover `/H3D` variants, H3D-specific report/sensor/output flags, and
   both separate and embedded Engine inputs. Preserve unrelated fields on mixed
   cards and all non-H3D output modes. Inspect syntax through existing parsers;
   do not reject arbitrary comments or filenames by substring.
   Remove H3D-only schema definitions while keeping the minimal recognition
   needed for those diagnostics; preserve the remaining fields of shared schemas.
2. Delete H3D-specific output initialization, scheduling, geometry/result
   export, gather operations, loader calls, and finalization in Starter/Engine.
   Remove the residual `engine/source/output/h3d/` tree after shared routines
   have moved, and remove `common_source/output/h3d/` and SDK includes entirely.
3. Remove H3D-only modules, types, constants, flags, scratch arrays, and routine
   parameters. Update all callers across elements, contacts, loads, sensors,
   MPI, implicit paths, allocation/deallocation, and shutdown/error handling.
   Do not leave disabled writer bodies or success-returning stubs.
4. Remove H3D file discovery, import, string-table checksum parsing, printing,
   and header fields from the checksum subsystem. Keep native animation,
   time-history, and other independent checksum checks working.
   Remove H3D viewer embeds, JavaScript links, and generated `.h3d` references
   from reports while retaining the ordinary report contents.
5. Preserve the restart record contract in Starter and Engine together. Keep
   numbered reserved slots/required record widths instead of shifting later
   fields when removing output state. Handle packed fields such as the combined
   output flags in `TABVINT(294)` explicitly. For old records, consume their
   actual lengths before discarding retired output-only data; do not restore
   writer state. Audit `wrcommp.F`, `rdcomm.F`, `wrcomm.F`, `rdresa.F`, `rdresb.F`,
   `wrrest*.F`, and shared serialized types together.
6. Test continuation from pre-change checkpoints with H3D both disabled and
   enabled, and verify the physical continuation against the old solver. Report
   that retired output is not resumed. If the old layout cannot be consumed
   safely, that is a compatibility blocker requiring an explicit migration
   decision, not permission to misread or silently truncate a checkpoint.

Gate: no H3D SDK/runtime code remains, removed features fail clearly, and native
outputs, restart continuation, shared calculations, and MPI execution pass.

### 6. Remove the binaries from the complete delivery chain

1. Produce a pinned extlib artifact without `hm_reader/`, `h3d/`, their SDK
   headers/import libraries, or their library-specific license payloads. Update
   `EXTLIB_VERSION.json` required files, URL, checksum, and obsolete reader
   component metadata. Keep required open-source dependencies and attribution.
   Publishing that artifact is a separate release action in the extlib repository.
2. Inspect `load_extlib.py` against the new package. A cache hit based only on
   required files must not accept an old package that still contains the retired
   libraries. Validate package identity/forbidden entries, handle stale caches,
   and ensure refresh cannot silently reinstall the old payload. Use its existing
   checksum/error path, not a second downloader.
3. Remove H3D include flags and deleted-source entries from every compiler
   configuration and `legacy_fortran.cmake`. Remove HM Reader/APR linkage where
   no surviving consumer requires it; verify dependency ownership before pruning
   additional open-source files.
4. Ship OpenReader and the CFG/message tree in each binary package. Relocate
   GCC runtime libraries currently stored below `extlib/hm_reader/` to a neutral
   runtime directory; update loader paths and their license notices together.
5. Remove `RAD_H3D_PATH`, retired library loader paths, copy steps, matrix
   variables, and old reader selection from QA helpers, all affected workflows,
   Docker/Apptainer definitions, IDE settings, launchers, and generated release
   instructions. Preserve MPI/compiler runtime paths still required by the build.
6. Update fixtures, current build/run documentation, and release notes for
   OpenReader and native output. Move old implementation comparisons to clearly
   historical documentation if retained. Do not erase attribution from source
   code kept or moved in earlier stages.

Gate: a clean source download/build and freshly assembled Windows/Linux packages
and containers contain none of the three libraries and run without an external
installation. Validate the extlib artifact and final archives, not just the Git
working tree.

### 7. Release only after the complete regression gate

| Check | Required evidence |
| --- | --- |
| Reader behavior | Existing loading/query/contact suites; mode-1/mode-2 rigid-part integration and numerical checks; native/LS-DYNA includes, units, submodels, and malformed-input failures |
| Physics | Full applicable miniqa suite using existing tolerances; focused contacts/friction, rigid bodies, shells/solids/SPH, ALE, sensors, reactions, and Python-controlled behavior |
| Outputs | Native animation, time histories, checksums, and supported state/DYNAIN output still contain expected quantities; migrated decks retain their original assertions |
| Restart | Starter-to-Engine, same-build continuation, old-checkpoint continuation, and multi-domain/R2R cases; unchanged serialized record alignment |
| Platforms | Windows x64 and Linux x64/ARM64 release configurations, supported single/double precision, SMP/OpenMP, and MPI with multiple ranks; bounds checking on affected integration paths |
| Dependency absence | Link/import inspection plus runtime loaded-module inspection; no retired `LoadLibrary`/`dlopen` names, SDK includes, exported H3D bridges, or residual vendor link paths |
| Packaging | Clean-cache and stale-cache builds; extracted release archives/container contents; execution from a clean environment with no Altair/Siemens installation or removed libraries |
| Removed-feature behavior | Negative tests for H3D requests, embedded inputs, and mixed-card flags; clear nonzero failure before time integration and no misleading success |

Reuse the existing Python/CTest runners and fixture directories. Add small
targeted cases for new branches and preserved shared behavior; do not replace
physical assertions with output-file existence checks or regenerate all reference
values to hide a change. Investigate numerical differences outside the established
tolerances before release.

Finish with a repository scan for `hm_reader`, `HM_READER_*`, `h3dpublic`,
`Hyper3D`, `h3dwriter`, `h3dreader`, `RAD_H3D_PATH`, and remaining H3D routines/
types. Inspect both tracked text and ignored dependency payloads. Remaining
mentions must be limited to removed-feature diagnostics/tests, historical
provenance, or independently justified names; no executable vendor dependency
may be allowlisted. Compilation and runtime inspection complement the text scan.

## Delivery and completion

Use the seven stages as ordered, independently reviewable commits or PRs. Keep
each intermediate build valid; replace callers before deleting their shared
implementation. Do not declare the removal complete while a reader parity gate,
restart gate, platform gate, or clean-package check is outstanding.

The delivered release must have one model reader, no HM Reader/H3D build or runtime
fallback, no proprietary-reference test dependency, preserved solver checks, and
documented H3D workflow migration. Rollback is a version-control/release rollback,
not a permanent switch that retains the removed libraries.

Stage 1 records refreshed Windows builds, focused simulations, reference snapshots,
checkpoints, and PE dependency listings. Package publication and later-stage
validation remain outstanding. Principal risks are incomplete OpenReader parity
and accidental changes to shared calculations/restart layouts; H3D file workflows
necessarily change when their implementation is removed.
