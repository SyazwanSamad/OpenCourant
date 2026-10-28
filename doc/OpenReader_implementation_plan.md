# OpenReader implementation plan

Current status: dependency-removal Stage 3 makes OpenReader the sole Starter
reader after Windows x64 DP SMP validation. Both rigid modes remain supported;
the reader selector, compatibility branches, and live vendor-reader test oracle
are retired. Dependency-removal Stage 5 removes H3D functionality while retaining
shared results, native outputs, and old serial checkpoint continuation. Focused
element/contact cases also pass with two Intel MPI ranks. See
[the current report](../qa-tests/dependency_removal/STAGE5.md) and
[current test commands](../qa-tests/reader/README.md). Structured-ALE generation
remains unsupported and fails explicitly during native loading, with a defensive
Starter check as well. [Stage 7](../qa-tests/dependency_removal/STAGE7.md) records
Windows SP/DP, OpenMP/MPI and old multi-domain checkpoint checks, together with
the unresolved physics/reference and parallel-checksum failures. Linux/ARM
verification is deferred at the user's request; hosted CI and R2R execution
remain unverified. The solver is not approved for release.

Dependency delivery, the published clean artifact and package evidence are tracked in
[Stage 6](../qa-tests/dependency_removal/STAGE6.md).

The numbered stages below are the historical OpenReader rollout record, before
dependency-removal Stages 2-3. Their former mode-2 rejection, automatic bypass, and
check counts are superseded by the current report. They are separate from the
[dependency-removal stages](Remove_HMReader_H3D_plan.md).

## Objective

Make the in-tree OpenReader work with the current OpenCourant Starter, including
correct conversion of `/PART` with `IRIGID` into `/RBODY` entities. Success requires
validated model behavior as well as successful compilation and linking.

Reuse the existing SDI model, entity creation helpers, reader export conventions,
and Starter conversion sequence. Do not add a dependency or a parallel conversion
framework.

## Findings during the original rollout

- OpenReader builds on Windows x64 with Intel oneAPI 2025.2 and MSVC 19.44.
- Starter's original OpenReader build fails at linking because four reader APIs
  are missing: rigid-body evaluation, rigid-body creation, part-element checking,
  and indexed include-file lookup.
- The original CMake workaround enabled the legacy include and part APIs and
  disabled rigid-part conversion. Stage 6 retires the automatic include/part
  fallbacks after testing their replacements; the rigid-part bypass remains.
- The disabled conversion path now rejects detected nonzero `IRIGID` values and
  returns zero generated counts for ordinary parts.
- OpenReader now registers profile `2612`, including format fallback and entity
  output. The accelerometer Starter smoke test completes and generates a restart.
- Model-loading entry points report failure for missing input, unsupported
  profiles, and broken configuration. Starter checks the status before querying
  the model; the LS-DYNA conversion entry point also propagates failure.
- Stage 6 corrects `cpp_get_number_of_include_files` to the two-argument ABI used
  by Starter and v82, replacing OpenReader's mismatched one-argument export.
- The main-node helper now uses `node_ID`, the solver name shared by ordinary
  and LAGMUL bodies. It retains specified nodes and creates missing ones once.

## Scope and implementation locations

| Area | Main locations | Required work |
| --- | --- | --- |
| Profile registration | `reader/source/cfgkernel/KERNEL/mv_file_format.h`, `mv_file_format.cpp`, `cfg_kernel.cpp`, `mv_utils.cpp`, `mv_descriptor.cpp`, `reader/source/solver_interface/source/cfg_reading/PrintOption.cpp` | Register 2612 and audit version-dependent mappings, inheritance, and output. |
| Model initialization and errors | `reader/source/cfgkernel/HCDI/hcdi_multicfgkernelmgr.cpp`, `reader/source/io/model_readers/radioss/radiossblk/radiossblk.cxx`, `reader/source/solver_interface/source/model/cpp_build_model.cpp` | Propagate failed initialization and model loading. |
| Conversion implementation | `reader/source/solver_interface/source/cfg_reading/GlobalModelSdi.cpp`, `reader/source/solver_interface/source/includes/GlobalModelSDI.h` | Implement counting and creation using existing SDI operations. |
| Reader exports | `reader/source/solver_interface/source/cfg_reading/` | Add wrappers for the missing APIs following existing symbol conventions. |
| Starter integration | `starter/source/devtools/hm_reader/`, `starter/source/starter/starter0.F`, `starter/source/constraints/general/rbody/hm_read_rbody.F` | Preserve array, ordering, mapping, and main-node contracts. |
| Configuration schemas | `hm_cfg_files/config/CFG/radioss2612/PART/part.cfg`, inherited `/RBODY` and group schemas | Verify field names, defaults, references, and units; change only demonstrated defects. |
| Build and documentation | `starter/CMakeLists.txt`, `HOWTO.md` | Retire compatibility bypasses only when replacements pass validation. |
| Regression coverage | `qa-tests/miniqa/`, relevant CI workflows | Add focused fixtures and OpenReader build/runtime checks. |

Preserve the bundled reader's existing ABI and default behavior. The completed
conversion must work with explicit rigid bodies, includes, submodels, alternate
units, and existing IDs. No changes to Engine's rigid-body formulation are planned.

## Stage 1: establish the conversion contract

1. Build small decks exercising the 2612 `/PART` schema and run them through the
   bundled v82 reader as the reference implementation.
2. Record the supported `IRIGID` values and their behavior. The schema has optional
   rigid-body fields for `IRIGID == 1`; do not infer other values' semantics.
3. Determine whether disconnected regions generate one body per part or multiple
   bodies, and establish behavior for empty parts and shared nodes.
4. Record generated groups, main nodes, rigid-body IDs, entity order, and mappings
   when the input already contains `/RBODY` definitions.
5. Verify defaults and handling of specified node, skew, sensor, added mass, and
   all six inertia components.
6. While the bypass remains active, detect unsupported rigid-part input and return
   a clear error identifying the part instead of reporting zero generated bodies.

Acceptance: fixtures and expected results define conversion behavior, including
edge cases. Any behavior not established by the reference remains explicitly
unsupported rather than guessed.

Stage 1 results and reproducible checks are recorded in
[`qa-tests/reader/rigid_parts/README.md`](../qa-tests/reader/rigid_parts/README.md).
The 14 reference fixtures cover ordinary, rigid, disconnected, empty, shared-node,
existing-body, explicit-field, and nonstandard-flag cases. The compatibility guard
rejects detected nonzero `IRIGID` values instead of silently omitting conversion.
Reference observations are not a claim of Engine-level numerical validation.

Stage 4 corrected the fixture element headers to `/SHELL/<part ID>` and
`/BRICK/<part ID>`. Earlier fixtures put the part ID in the connectivity row,
leaving elements unassociated with their intended parts. Rechecking all 14 v82
cases changed the two `IRIGID=2` snapshots: one connected shell produces one body,
and two disconnected shells produce two bodies, with explicit NODE sets. The
earlier conclusion that v82 ignores mode 2 was incorrect. OpenReader now rejects
that mode instead of silently returning zero. Implementing and integrating its
connected-region behavior is required before removing the bypass.

## Stage 2: restore configuration loading

1. Add the 2612 format entry, string/version mappings, and inheritance chain.
   Audit enum ranges, version lists, and format selection for related assumptions.
2. Load the current configuration tree completely and resolve demonstrated parser
   or reference failures. Downgrading the requested profile to 2026 is insufficient:
   that hierarchy references `MAT/matl105.cfg`, now located under 2612.
3. Report failed CFG initialization and null model results through the existing
   reader error path. Remove success returns after swallowed model-load failures.
   Prevent C++ exceptions from escaping into Fortran.

Acceptance: the accelerometer Starter smoke test completes through OpenReader;
missing configuration and unsupported-profile tests produce readable errors.

Stage 2 is verified by [`qa-tests/reader/test_model_loading.py`](../qa-tests/reader/test_model_loading.py).
It checks both Radioss loading entry points, `IRIGID` input/output preservation,
missing/broken/unsupported configuration, missing input, LS-DYNA initialization
and failure propagation, the accelerometer restart, and the Stage 1 rejection
guard in the complete Starter. Commands and limits are in
[`qa-tests/reader/README.md`](../qa-tests/reader/README.md).

## Stage 3: implement rigid-part counting and creation

Implement these reader entry points with the symbol variants used by the project:

- `cpp_evaluate_rbodies_number_from_rigid_parts`
- `cpp_create_rbodies_from_rigid_parts`

Use one deterministic conversion plan for both operations so the evaluation
results agree exactly with the arrays allocated by Starter. Keep that state tied
to the loaded model; reset it on reload and reject or safely handle repeat calls.
Validate output bounds internally without breaking the existing external ABI.

For each body required by the Stage 1 contract:

1. Use the Stage 1 part-based set contract: one `PART` clause per converted part,
   including empty and disconnected parts. Preserve existing selection/iterator state.
2. Create the secondary-node group and `/RBODY` using existing entity helpers.
3. Transfer part fields to their verified rigid-body attributes, including
   `Node_ID`, `Skew_ID`, `Sens_ID`, `Mass`, and `JXX/JYY/JZZ/JXY/JYZ/JXZ`.
   Preserve defaults and unit context; avoid converting quantities twice.
4. Preserve include/submodel ownership, offsets, titles, and references.
5. Allocate collision-free group, node, and rigid-body IDs using existing model
   allocation rules and accounting for submodel ID spaces.
6. Fill `NEW_RBODY_TO_PART` and `NEW_RBODY_ID` in the order Starter consumes.
7. Validate inputs before committing changes and handle creation failures without
   leaving a partially converted model that can proceed to simulation.

Acceptance: generated counts, entities, attributes, and mappings agree with the
v82 reference for every established fixture, without duplicate creation or writes
past Starter's allocated arrays.

Stage 3 now exports all four symbol variants for both APIs. Counting and creation
share model-scoped state; repeated calls reuse the result. Creation rejects changed
part membership or rigid flags since evaluation, and creation without current
evaluation fails. Reload before changing an already-created conversion plan.
Source references are validated before mutation; failed creation removes generated
entities and terminates with a diagnostic because the existing void ABI cannot
return an error to Starter. Array lengths remain the caller's responsibility under
that ABI; the implementation writes exactly the evaluated counts and rejects a
changed plan before writing output arrays.

The implementation initializes SDI allocation from the loaded entities, implements
the existing submodel-offset hook through CFG drawables, and resets entities,
selections, and conversion state on model reload. Twelve corrected snapshots match
v82 exactly; the two mode-2 cases check explicit rejection in OpenReader. Five
additional comparisons cover solids, include ownership, alternate
units, different entity offsets, and two submodel ID spaces. An explicit unit ID
is retained on generated entities: v82 drops it, so this is a deliberate difference
physically verified in Stage 5 against a unit-tagged explicit body. Titles, IDs, references, raw values, and
ownership otherwise match those additional comparisons.

[`test_openreader_conversion.py`](../qa-tests/reader/rigid_parts/test_openreader_conversion.py)
also checks array canaries, selection preservation, repeat conversion, reload,
missing references, changed/deleted parts, invalid call order, and exported symbols.
The normal Starter build still enables the rigid-part bypass. Stage 4 covers the
main-node helper and mapping integration; numerical validation remains Stage 5.

## Stage 4: verify Starter integration

Preserve this sequence in `starter0.F`:

```text
evaluate counts -> allocate output arrays -> create bodies
-> add missing main nodes -> normal model reading
```

- `hm_read_rbody.F` treats generated bodies as the final ordinary rigid bodies and
  indexes `NRBODY_TO_PART` accordingly. Preserve that order or update the producer
  and consumer together. Include explicit `/RBODY/LAGMUL` cases in the audit.
- Check how `RBODY_PART_MODIF` handles shared nodes, parent bodies, and part
  associations before changing group membership or body ordering.
- Resolve the `RBID`/`independentnode` lookup consistently with CFG solver-label
  aliases. Retain a specified main node and generate a missing one exactly once.
- Use explicit interoperable Fortran types/interfaces where needed while keeping
  the bundled reader's calling convention and exported signatures compatible.
- Preserve sensor activation, center-of-gravity, mass, and inertia behavior through
  the existing Starter rigid-body initialization.

Acceptance: mapping and node-generation checks pass under bounds checking, and
explicit rigid-body models retain their existing behavior.

Stage 4 is verified for mode 1 by
[`test_starter_integration.py`](../qa-tests/reader/rigid_parts/test_starter_integration.py).
The create/evaluate interfaces use `bind(C)` and `integer(c_int)`. Starter receives
the generated body IDs through `LECTUR` and builds an explicit-first read order
followed by generated bodies in conversion order. This preserves the hierarchy
routine's prefix assumption, keeps LAGMUL out of ordinary-body indices, and uses
the matching generated ID to select each part mapping. Original reader positions
remain available for domain tags. The sequential reader API is used because v82
appends indexed selection lists instead of replacing them.

The node helper retains specified main nodes, returns zero when nothing was added,
and initializes a missing ordinary or LAGMUL node once in the body's include.
New coordinates are zero with the existing node unit convention; Starter performs
the later center-of-gravity calculation. Native failures are contained at the ABI.
OpenReader indexed selections now replace stale handles, reset descriptor caches,
and reject invalid positions. The hierarchy routine no longer indexes parent zero.

There are 39 focused checks: six helper/connectivity cases, three invalid native
calls, ten bounds-checked Fortran conversions, four ordering rejections, and sixteen
complete Starter runs across OpenReader and v82. Eight full cases per reader cover
single, mixed, existing/shared bodies, interleaved includes, LAGMUL, explicit fields,
and the existing RBODY/ROTA model. Each completes with zero errors and a restart.
The conversion modules, main-node module, body reader, and hierarchy module are
compiled with bounds checking in isolated test executables. The default executable
retains the bypass. Stage 5 records the supported Engine checks. Mode 2, runtime
R2R domain filtering, and Linux/ARM builds remain unimplemented or unverified.

## Stage 5: regression and numerical validation

Use small, focused fixtures covering:

| Case | Main checks |
| --- | --- |
| Ordinary part, `IRIGID=0` | No generated body or unintended model change. |
| One rigid shell or solid part | Correct count, node group, attributes, and part mapping. |
| Multiple and disconnected rigid parts | Reference body count, deterministic ordering, and mapping. |
| Shared nodes and existing rigid bodies | Reference ownership, hierarchy, and conflict diagnostics. |
| Empty part or invalid reference | Defined result or clear error without partial conversion. |
| Specified and missing main nodes | Node retained or generated once with correct references. |
| Added mass, inertia, skew, and sensor | Correct values, defaults, orientation, and activation behavior. |
| Includes, submodels, alternate units, and ID collisions | Correct ownership, offsets, scaling, and unique IDs. |
| Reload and repeat conversion | No stale state or duplicate entities. |

Compare both readers using normalized entity data and physical quantities rather
than requiring byte-identical generated restart files. Check total mass, center
of gravity, inertia, and dependent-node membership before running Engine.

Run short Engine cases for rigid translation, rotation, applied loading, and sensor
activation. Check preservation of rigid distances, motion, and energy within
documented tolerances. Extend existing explicit rigid-body QA, including
`KIN_CONSTRAINTS/RBODY/ROTA`, instead of duplicating it.

Acceptance: structural comparisons and numerical cases pass against v82 and
hand-checkable reference models. A successful link alone is not acceptance.

Stage 5 passes for mode 1 using
[`test_numerical.py`](../qa-tests/reader/rigid_parts/test_numerical.py) and an Engine
built from this checkout. It runs 28 Engine comparisons: nine small cube cases
through OpenReader-generated, v82-generated, and explicit v82 bodies (the units
case uses the correctly unit-tagged explicit control), plus both readers on the
existing RBODY/ROTA model with its run/output schedule shortened to 0.1 seconds.
The cube cases cover translation, generated main nodes, rotation, force, submodel
offsets, sensor-triggered release, delayed loading, added mass/inertia, and units.

The unit cube has eight lumped nodal masses: expected mass 1 kg, center
`[0.5,0.5,0.5]` m, and diagonal inertia `[0.5,0.5,0.5]` kg m². Free translation
uses velocity 2 m/s and energy 2 J. Rotation uses 1 rad/s and energy 0.25 J.
A 1 N force gives acceleration 1 m/s². Sensor tests separately check release of
the rigid body after activation (including the existing two-cycle delay) and
loading starting at 0.05 seconds. Release under uniform velocity preserves energy
and distances while the solid elements become active again.

Twenty additional Starter checks compare normalized masses, centers, tensors,
and secondary-node lists for ordinary, single, disconnected, mixed, existing,
shared, interleaved, LAGMUL, and explicit-field models. Empty parts now terminate
with a readable error and no restart; Stage 5 fixed the body's zero-length
secondary-node storage access before it could reach a bounds exception.

On the recorded run, maximum rigid-distance error is `6.68e-8` m, maximum analytic
position error is `2.45e-6` m, and maximum analytic energy error is `2.46e-6` J.
Acceptance tolerances are `3e-5` m for distances/positions, `3e-4` m/s for driven
velocity, `3e-5` J for energy, and relative `1e-6` with absolute `1e-8` for normalized
Starter comparisons. Histories use single-precision output and 100 samples over
the 0.1-second run. JSON results retain input folders, solver logs, initialized
properties, errors, and Engine/history-reader hashes.

The alternate-unit case establishes a v82 defect rather than copying it: its
generated body drops unit ID 7 and produces diagonal inertia
`[300000.5,200000.5,400000.5]`, while OpenReader and a correctly tagged explicit
v82 body produce the physical `[0.8,0.7,0.9]`. A separate check records this known
discrepancy. No Engine formulation was changed. Mode 2, MPI/R2R execution,
Linux/ARM, contact-rich production models, and other element formulations remain
outside this validation. Keep the default bypass until remaining rollout work passes.

## Stage 6: complete API alignment and rollout

1. Implement the missing part-element check and indexed include lookup; fix the
   include-count ABI mismatch while retaining compatibility with the bundled reader.
2. Remove the automatic rigid-part bypass only after Stages 3-5 pass. Retire the
   include and part fallbacks individually after their replacement APIs pass tests.
3. Add an OpenReader-enabled build, export check, basic smoke test, and focused
   rigid-part regression tests to CI. Validate Windows first, then Linux x64 and
   supported ARM builds before claiming cross-platform support.
4. Update `HOWTO.md` with validated capabilities and remaining restrictions.

Stage 6 implements the missing `cpp_is_part_with_elements` and
`cpp_get_include_file_by_index` exports with the project's four symbol spellings.
Part lookup uses a local SDI handle and element selection; it does not disturb
Starter's active entity or iterator. Include count now accepts `(is_dyna, count)`
and assigns its output, matching v82. All in-tree callers use this ABI; external
callers of the former one-argument OpenReader export must update their declaration.

Indexed lookup uses the current native or original keyword model, returns resolved
paths in space-padded buffers, and preserves v82's synthetic submodel entry/order
with an empty filename. Tests exposed missing absolute-path metadata for nested
includes, absent transformed-keyword include paths, and stale keyword objects on
reload; these are corrected at their shared storage/loading points. The old
bulk-list export remains available, with its
undersized string allocation corrected and checked using a long include filename.
Exceptions terminate with a native diagnostic rather than crossing the C/Fortran
boundary. Invalid part IDs return false; invalid include indices return blanks.

[`test_model_queries.py`](../qa-tests/reader/test_model_queries.py) checks ABI
canaries, exports, empty/filled parts, nested includes, truncation, zero capacity,
submodel offsets, selection preservation, reload, and model-load failure. Native
queries match bundled v82. The minimal keyword fixture is validated against known
source paths because v82 does not return success for that conversion fixture.
The Starter build now uses these replacement include/part APIs by default;
explicit legacy options remain available for older external readers.

[`openreader_ci.yml`](../.github/workflows/openreader_ci.yml) adds a Windows x64
pull-request/manual job that builds OpenReader and Starter and runs export/API,
loading/smoke, rigid-part contract/lifecycle, and bounds-checked Starter integration
checks. Hosted CI execution, Linux x64, and ARM validation remain pending. The
Stage 5 numerical runner is retained as a separate local check.

Final local Windows validation passes five API check groups, all 14 v82 reference
snapshots, 14 OpenReader contract checks, 12 lifecycle/comparison checks, 18 loading
and Starter smoke/guard checks, 39 bounds-checked Starter integration checks, and
all 49 numerical/structural checks (28 Engine runs). The complete Starter build
has no automatic legacy include/part compile definitions. Local builds use oneAPI
2025.2; the hosted workflow follows the existing Windows CI oneAPI 2025.0 setup
and still needs its first hosted execution.

Rollout is deliberately incomplete: the corrected Stage 4 contract establishes
that `IRIGID=2` needs connected-region conversion. Mode-1 numerical success does
not implement that mode. The automatic rigid-part bypass and structured-ALE
restriction remain until their respective missing behavior is validated.

The TYPE25 contact regression checks converted sets used as both lines and
surfaces. Group-use classification retains all allowed subtypes and clears its
cached references on model read/creation. Six focused contact/reload checks are
included in Windows CI.

Keep structured ALE and unrelated reader features outside this repair unless they
block the focused regression cases. Preserve the existing restriction until those
features receive separate validation.

## Suggested delivery order

1. Reference fixtures, unsupported-input guard, and conversion contract.
2. Profile 2612 registration and model-load error handling.
3. Counting/creation APIs, main-node handling, and mapping integration.
4. Numerical regressions and removal of the rigid-part bypass.
5. Remaining include/part API alignment, CI coverage, and documentation.

## References

- Repository source and configuration paths listed above.
- [Official /PART reference](https://help.altair.com/hwsolvers/rad/topics/solvers/rad/part_starter_r.htm): the currently published page omits the Irigid extension; use the checked-in 2612 schema and v82 behavior to establish that contract.
- [Official /RBODY reference](https://help.altair.com/hwsolvers/rad/topics/solvers/rad/rbody_starter_r.htm): rigid-body fields, defaults, and mass/inertia/sensor behavior.
