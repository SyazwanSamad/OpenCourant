# Inline-table curve duplication and Starter error preservation

Status: implemented; Windows x64 DP SMP validation completed, 2026-10-29.
Branch `openreader`, source commit `d871244fb`.
The original model files remain unchanged. Solver interpolation and material
equations are unchanged. The changes and test results are recorded below.

## Implementation and validation

The shared reader now marks a successfully consumed subobject header using its
previous (actual header-start) location, after skipping comments. LAW88, LAW123,
LAW125 and LAW132 use local table-copy status variables and return safely when a
copy fails. Existing accumulated errors continue to control restart writing and
exit status; no new error counter or message-text filter was added.

Reload testing exposed another required repair: converted adhesive subobjects
appear in both the flat object index and their owning parent's child list.
Deleting both caused a double deletion when switching to a native model. Native
model replacement now deletes owning roots once and clears the index. Creating a
new conversion model also clears the old model instead of accumulating entities.
The regression covers conversion-to-native reload, conversion again, and an empty
keyword model replacing the previous entities.

`qa-tests/reader/test_shared_tables.py` adds nine bounded cases to Windows CI.
It generates a two-curve/two-material pair, checks exact samples and references,
and rejects both identical and different duplicate definitions. A native missing
LAW88 function fails safely. LAW123/125/132 controls intentionally include a later
property incompatibility and require both it and an earlier duplicate-ID error
to remain counted. These negative controls validate error preservation, not the
physical behavior of those composite materials.

The original deck now produces **15 unique functions**, unchanged material
references and exact listed curve samples, zero errors, exit 0 and a nonempty
restart. The genuine duplicate control exits 2 and produces no restart. The
existing focused reader/API, loading/query, contact, parameter, rigid-conversion
and bounds-checked Starter checks pass. No Engine simulation was needed because
the converted samples and references are unchanged.

[After-validation evidence](OpenReader_shared_table_validation.json) retains
source/input/binary hashes and results. Full local inputs, listings, logs and
restarts are under `cbuild_mat181_investigation/verified-model/`,
`verified-tables/` and `verified-parameters/`; `verified.log` records the combined
gate. The earlier investigation record and frozen Stage 1-7 evidence are retained.
SP, MPI, Linux, ARM64 and hosted CI execution remain unverified for this repair;
existing Stage 7 release blockers remain.

## Findings

The supplied `qa_mat181_commontable.k` contains two different MAT181 IDs
(`93500009`, `93600009`), one table (`95400015`) and five distinct curve
definitions (`95400016` through `95400020`). Both materials reference that table.
There are no duplicate curve or table definitions in this deck.

The current Windows DP Starter reproduces the reported failure: five duplicate-ID
errors (79), then normal termination, a summary of zero errors and a nonempty
restart. This combines two independent defects.

1. **Comment-sensitive inline subobject bookkeeping.** `*DEFINE_TABLE` reads its
   following curves through `SUBOBJECTS(CurveIds, /CURVE/DEFINE_CURVE)`. In
   `MECIDataReader::readNextCard`, the `CARD_HEADER` branch calls
   `updateSubKeywordRead` before reading the subobject header.
   `MECIReadModelBase::updateSubKeywordRead` compares the current file cursor
   against scanned header positions. Lookahead/unread can leave that cursor at
   the comments preceding the header. The consumed header is not marked loaded,
   so `ReadKeyword` reads it again as a standalone curve. The SDI curve selection
   exposes both representations and the ordinary curve converter converts both.
   Removing only `$` comments eliminates the duplicates; removing `_TITLE` does
   not. A table with explicit curve references also avoids this path.

2. **LAW88 overwrites the global error count.** MAT181 maps to `/MAT/LAW88`.
   `hm_read_mat88.F90` imports `message_mod::IERR` and passes it to
   `func_table_copy` as a local status argument at both loading/unloading calls.
   That helper declares its argument `intent(out)` and sets it to zero on entry.
   A successful material-table copy therefore erases earlier errors. The existing
   `IF(IERR==0)` restart gate and final exit status subsequently allow success.
   LAW123, LAW125 and LAW132 contain the same global-counter/status alias in
   `func_table_copy` calls; LAW50 uses a local variable and is different.

The extra MAT181-derived curves are legitimate: five per material, with different
IDs. The current converter also reuses its last derived curve in a sixth rate
row. Repeated references in those material rows are valid and must remain.
Sharing the source table is valid; duplicating tables or curves in the input is
not the repair.

## Reproduction evidence

The [investigation record](OpenReader_shared_table_investigation.json) contains
input/binary hashes, source identity, curve IDs and observed results. All runs
used isolated copies under `cbuild_mat181_investigation/`, Windows x64 DP SMP,
and one Starter process. No Engine simulation was run.

| Control | Converted functions | Duplicate curve IDs | Starter exit / restart |
| --- | ---: | ---: | --- |
| Original commented inline table, two MAT181 materials | 20 | 5 | 0 / written, incorrect |
| Same deck with one material | 15 | 5 | 0 / written, incorrect |
| Inline table and curves without any materials | 10 | 5 | Reader-only probe |
| Same physical inputs, `$` comments removed | 15 | 0 | 0 / written |
| Same physical inputs, explicit `*DEFINE_TABLE_2D` curve references | 15 | 0 | 0 / written |
| `_TITLE` removed, comments retained | 20 | 5 | 0 / written, incorrect |
| Explicit table with a deliberately duplicated curve definition | 16 | 1 | 0 / written, incorrect |
| Commented inline table with elastic materials instead of LAW88 | 10 | 5 | 2 / no restart |

All 15 unique function IDs and every listed X/Y sample match exactly between the
original, comment-free and explicit-reference MAT181 runs. Both materials retain
`NL=6` and the same derived-function references. These are input/conversion checks,
not proof of an Engine solution's physical correctness.

## Smallest complete implementation

1. **Correct consumed-header identity once in the shared reader.** Use the actual
   consumed header's file and start position when marking an inline curve loaded,
   after comment skipping and successful header parsing. Reuse the existing
   header-position/loaded-flag mechanism. Verify the exact cursor transition at
   the existing call before choosing whether the smallest fix belongs in
   `readNextCard`/`readHeaderCard` or `updateSubKeywordRead`.
   Preserve include/subdeck ownership and the standalone-curve path. Match source
   positions, not curve IDs: two genuinely separate definitions of the same ID
   must remain distinguishable and must still fail validation. Do not add an
   ID-based deduplication pass or change the generic converter to reuse duplicates.

2. **Separate table-copy status from accumulated errors.** Follow the existing
   local-status pattern used by other material readers. Change the affected
   loading/unloading calls in LAW88 and the matching LAW123/125/132 calls to use a
   local variable. Audit other table-copy calls in those routines for the same
   alias. Preserve the helper's output-status contract and its existing diagnostic
   paths. Handle failure before reading an uninitialized/failed material table;
   retain reported errors and return safely. Do not change `func_table_copy` to
   accumulate into an argument that other callers expect to be a fresh status.
   Keep Starter's existing global error count, restart gate and nonzero exit path.

3. **Add compact regression checks to the existing reader/loading workflow.**
   Reuse `Reader`, `dyna_load`, subprocess timeouts and fresh output folders.
   Use a small generated table with two curves and two material consumers, rather
   than checking in the supplied model or building a material/type/platform matrix.
   The required cases are below. Add a prior-error preservation check for each
   additional material reader changed in step 2. Document the behavior in the
   reader README; the current Windows CI loading step should execute the checks.

4. **Rebuild and close the gate on the supplied model.** Run the focused API,
   loading/query, contact, parameter, rigid-conversion and bounds-checked Starter
   checks. Re-run the original untouched deck in a fresh workspace output folder;
   require 15 unique functions, unchanged material references/samples, zero real
   errors, exit 0 and a new restart. Capture after-results and hashes beside the
   before-results. Do not alter frozen Stage 1-7 evidence or numerical tolerances.

## Change reach and user impact

| Surface | Required action |
| --- | --- |
| `reader/source/cfgio/MODEL_IO/meci_data_reader.cpp` | Audit the `CARD_HEADER` caller, comment lookahead/unread and subobject header consumption; fix only the bookkeeping needed |
| `reader/source/cfgio/MODEL_IO/meci_read_model_base.cpp` | Correct loaded-header matching; preserve `ReadKeyword`'s skip of previously consumed definitions |
| Corresponding reader headers/context | Change only if passing the existing source position explicitly is necessary; no exported C signature changes |
| `starter/source/materials/mat/mat088/hm_read_mat88.F90` | Preserve the global error count across both table-copy calls and handle local failure safely |
| LAW123/125/132 reader files | Repair the same proven status/counter alias; audit adjacent table-copy calls |
| `starter/source/materials/tools/func_table_copy.F90`, `mattab_usr2sys.F` | Verify status and diagnostics; keep the shared helper contract |
| `starter/source/starter/lectur.F`, `starter/source/output/analyse/analyse_arret.F` | Verify restart suppression, summary and exit propagation; change only if caller fixes do not restore existing behavior |
| `qa-tests/reader/test_model_loading.py`, compact fixtures/helpers, reader README and current Windows CI loading step | Cover the new checks without another test framework |
| Table/curve CFG and `convertcurves.cxx`/`convertmats.cxx` | Verify schema, rates, scale/offsets and references; current evidence does not justify changing them |

Valid shared tables must keep their data, reference ordering, scaling and material
ownership. There is no destructive input migration. Invalid models that previously
appeared successful will instead return nonzero and produce no usable new restart;
scripts relying only on restart existence should use the current run's exit status
and fresh outputs. Do not delete a user's old restart as part of this fix.

## Bounded acceptance cases

| Case | Assertions |
| --- | --- |
| Commented inline table, two curves, two MAT181 materials | Each source definition selected/converted once; unique IDs; correct table rates, scaled points and both material references; normal Starter restart |
| Equivalent explicit-reference table | Same converted values and references as inline; comment-free inline is a cheap reader comparison; include the inline table once through an include for file-position coverage |
| Genuine duplicate curve, differing data, followed by valid LAW88 processing | Named duplicate error survives; nonzero final error count and exit; no usable new restart; never silently pick one definition |
| Missing function in a material table | Existing named error survives; safe failure without an access violation or use of an incomplete table; no usable restart |

A small status-preservation harness or existing minimal fixtures should cover the
other material readers changed in step 2. Repeated loads must retain neither old
entities nor old diagnostics. Generated function IDs must not collide with the
shared `/FUNCT` and `/TABLE` pool. Keep identical-definition duplicates invalid as
well as differing-definition duplicates.

No Engine run is needed to prove these parser/error-count repairs if converted
physical inputs remain identical. If implementation changes curve values,
interpolation or material behavior, stop and add a numerical comparison before
claiming solver equivalence. SP, MPI, Linux, ARM64 and hosted CI execution remain
outside this initial gate. Existing Stage 7 release blockers remain unresolved.

## Temporary input workaround

The investigation's explicit-reference copy at
`cbuild_mat181_investigation/explicit_table/case.k` replaces the inline table with
`*DEFINE_TABLE_2D`, listing the same five rate/curve-ID pairs. Starter completes
without duplicate errors, and all listed curve samples match. Removing the `$`
comments also avoids this reproduction. Neither changes the original model on
disk, and neither repairs the error-counter defect for other invalid inputs.
These copies have Starter/conversion validation only; no Engine result is claimed.
