# Reader regression tests

Starter always builds and links the in-tree OpenReader. No test or integration
builder loads HM Reader. Reference provenance is retained as checked-in data in
`expected.json`, `expected_conversion.json`, and the frozen dependency-removal
reports. The `--reference`, `--guard`, and reader-selection options are retired.

Build Starter in an initialized Intel/MSVC environment; CMake builds OpenReader
first and prepares its external headers before compilation. The following
commands run from the repository root. Reader-only checks use Python's standard
library. Numerical checks also use the existing NumPy and `vortex_radioss`
installation.

## Loading, contacts, and APIs

```powershell
python qa-tests/dependency_removal/test_reader_build.py
python qa-tests/reader/test_starter_api.py --reader exec/open_reader_win64.dll
python qa-tests/reader/test_model_queries.py --reader exec/open_reader_win64.dll
python qa-tests/reader/test_model_loading.py --reader exec/open_reader_win64.dll --starter exec/starter_win64.exe
python qa-tests/reader/test_contact_groups.py --reader exec/open_reader_win64.dll --starter exec/starter_win64.exe
```

The build check verifies dependency extraction and source/build invariants without
network access. The API audit discovers actual Starter calls, resolves local
C/C++ implementations separately, and checks all four reader export spellings.
Build identity is now `open_reader_build_id`; retained `hm_reader_variables`
and `HM_*` adapters are in-tree APIs, with no vendor binary behind them.

Two model-query groups cover native/keyword include paths, submodel offsets,
empty/filled parts, canaries, fixed-width padding/truncation, zero capacity,
selection/iterator preservation, reload, and failure without stale entities.
The expected paths and memberships come directly from the generated fixtures.

Twenty-seven loading checks cover both native entry points, profile 2612,
IRIGID preservation, bad/missing configuration and input, keyword initialization,
structured-ALE rejection in root/includes, comments, the accelerometer restart,
and default Starter conversion of mode 1 and connected/disconnected mode 2.
Four contact checks cover typed groups, converted sets used as surfaces and
lines, selection preservation, reload, and a complete TYPE25 Starter restart.

The include-count ABI remains
`cpp_get_number_of_include_files(int *is_dyna, int *count)`. Indexed lookup is
one-based, fixed-width, space-padded, and truncated to capacity; invalid indices
return blanks. Reload/failure clears saved keyword paths.

## Rigid-part conversion

```powershell
python qa-tests/reader/rigid_parts/test_reader_contract.py --reader exec/open_reader_win64.dll
python qa-tests/reader/rigid_parts/test_openreader_conversion.py --reader exec/open_reader_win64.dll
```

Fourteen original conversion snapshots and 32 lifecycle/ownership checks use
frozen reference data. The latter include nine lifecycle/error cases, five
mode-1 comparisons, and 18 mode-2 comparisons. Complete NODE lists, component
order, titles, IDs, mappings, includes/submodels, offsets, and units are checked.
See [the contract](rigid_parts/README.md).

Evaluate before creating bodies. Repeat calls reuse mappings/IDs. Invalid call
order, changed/deleted parts, changed rigid flags, and missing references fail
with a diagnostic. Creation validates before mutation and rolls back generated
entities on failure. The ABI has no capacity argument: callers must allocate
the evaluated sizes; tests place canaries around correctly sized arrays.

The external reference dropped explicit unit IDs. OpenReader preserves them on
generated bodies/sets; the test explicitly checks that intentional difference
before comparing the other frozen fields. Raw field values are not rescaled.

## Starter integration (Stage 4)

With Starter's CMake compile database enabled:

```powershell
python qa-tests/reader/rigid_parts/build_integration.py --starter-build starter/cbuild_starter_win64_ninja --output cbuild_reader_integration
python qa-tests/reader/rigid_parts/test_starter_integration.py --reader exec/open_reader_win64.dll --binaries cbuild_reader_integration
```

The existing Windows builder reuses Starter objects, recompiles five affected
modules with bounds checking, and links only `starter-openreader.exe` and
`driver-openreader.exe`. Thirty checks cover connectivity/ownership, Fortran
canaries, mapping/order, invalid calls, shared-node hierarchy, ordinary/LAGMUL
main nodes, explicit fields, RBODY/ROTA, and both mode-2 region cases.
The loading suite separately checks the normal Starter executable.

## Numerical validation (Stage 5)

Build the serial DP Engine with the existing toolchain. Direct CMake uses
`arch=win64`, `precision=dp`, `MPI=smp`, `EXEC_NAME=engine_win64`, and `debug=0`.

```powershell
python qa-tests/reader/rigid_parts/test_numerical.py --binaries cbuild_reader_integration --engine exec/engine_win64.exe --output cbuild_reader_numerical
python qa-tests/reader/rigid_parts/test_mode2_numerical.py --binaries cbuild_reader_integration --engine exec/engine_win64.exe --output cbuild_reader_mode2
```

The first suite runs 19 Engine cases and ten structural/error cases. Generated
and explicit bodies both use OpenReader and retain independent analytic
mass/inertia, motion, force, sensor, and energy assertions. Units are compared
with explicit unit-tagged bodies. The known external-reader unit-loss observation
is preserved in Stage 1/2 evidence and no longer requires that binary at runtime.

Six mode-2 Engine runs compare generated/explicit translation, rotation, and
independently moving disconnected cubes. Membership, mass, center, inertia,
analytic motion/energy, and paired histories are checked. The disconnected cubes
retain velocities `+2` and `-1 m/s`, mass `2 kg`, and kinetic energy `2.5 J`.

Runs last 0.1 s with maximum step `1e-4 s`. Existing limits remain `3e-5 m`
for position/distance, `3e-4 m/s` for driven velocity, `3e-5 J` for energy,
and `rtol=1e-5`, `atol=1e-6` for paired histories. The existing packed-record
helper validates record lengths to avoid the installed history reader's
group-offset issue. Fresh output directories retain inputs, logs, histories,
restarts, and reports.

## CI and remaining gates

[Windows CI](../../.github/workflows/openreader_ci.yml) runs the standard-library
checks, including dependency extraction and bounds-checked integration.
Numerical suites remain local checks. [Stage 5 evidence](../dependency_removal/STAGE5.md)
records current H3D removal results, including four shared-result families and
native contact/sensor output with two Intel MPI ranks; earlier reports remain historical.
H3D requests now fail explicitly. Native outputs and old serial checkpoint
continuations remain covered; retired output is not resumed.

Structured-ALE generation remains unsupported and fails explicitly during native
loading. The missing generator and its build toggle have been removed.
Linux x64/ARM64, SP, multiple OpenMP threads, broader MPI/R2R, hosted CI, full miniqa, every element formulation,
and large-model performance still require validation before release.
