# OpenReader /PARAMETER repair plan

Status: implemented and validated in the current Windows x64 DP SMP environment,
2026-10-28. Based on source commit `184be37ac10066237cc624dda44a41f5eb78f1a6`.
[Results and reproduction](../qa-tests/reader/parameters/README.md) retain the
before/after evidence, input/binary hashes and remaining limits. Solver physics
and the public C API signatures are unchanged.

The two successful decks and four invalid variants pass Reader/Starter checks;
exactly two Engine runs pass the existing analytic assertions and paired-history
comparison. The existing focused reader and bounds-checked Starter checks pass.
TEXT expansion occurs before typed card parsing, allowing a text value to span
numeric fields; the generic per-cell replacement hook remains unchanged.
Failure recovery also required clearing old messages and guarding empty-model
selection. LS-DYNA resolved-value conversion and raw Python bodies are covered.

## Outcome and scope

Make the five RADIOSS parameter types usable through OpenReader and normal
Starter execution: `INTEGER`, `REAL`, `INT_EXPR`, `REAL_EXPR` and `TEXT`.
Resolve values and titles correctly, print their actual values without crashing,
and reject unresolved input before a usable restart is written. Preserve working
local/global resolution and valid zero/negative values.

Use the current Windows x64 DP SMP environment. Reuse the in-tree ExprTk evaluator,
the existing Reader test helper and the small rigid-cube solver fixture. This work
adds no proprietary executable or dependency. The contract for field widths,
local scope, text length and `$` stitching is the
[RADIOSS /PARAMETER reference](https://help.altair.com/hwsolvers/rad/topics/solvers/rad/parameter_starter_r.htm).
Complete Templex-language compatibility is outside this repair.

## Places the change must reach

| Surface | Required work |
| --- | --- |
| `reader/source/cfgio/MODEL_IO/solverCDR.cxx` | Correct integer-expression storage; preserve lookup, descriptor selection and include/submodel scope. Audit expression evaluation/error propagation. |
| `reader/source/solver_interface/source/misc/cpp_print_parameters.cpp` | Repair every global/local definition and replaced-reference listing block. Read the active schema values and check retrieval success before accessing them. |
| `hm_cfg_files/config/CFG/radioss2017/PARAMETER/parameter_text.cfg` | Restore the missing header/title consumption; verify fixed-length and full-line text reading. Keep the existing CFG attribution. |
| `reader/source/cfgio/MODEL_IO/meci_data_reader.cpp` | Repair text substitution and reject unresolved references using the existing message/error paths. Audit scalar, array, ID and string callers. |
| `reader/source/cfgio/MODEL_IO/meci_model_factory_parameter_evaluator.cpp`, `mv_model_factory.cpp`, corresponding declarations | Change only where needed to distinguish a missing/failed parameter from a valid zero and propagate expression failures. Preserve legitimate numeric conversions. |
| `starter/source/starter/starter0.F` and the model-loading entry points | Verify the caller receives readable diagnostics and nonzero status. Change callers only if reader-side fixes cannot propagate failure through the existing interfaces. |
| `qa-tests/reader/parameters/`, `qa-tests/reader/test_parameters.py` | Add the compact fixture pair, generated invalid variants and assertions described below. Reuse existing helpers rather than adding a new test framework. |
| `qa-tests/reader/README.md`, `.github/workflows/openreader_ci.yml` | Document the supported checks and add reader/Starter checks to the existing Windows job. Keep Engine comparisons as the existing local numerical workflow. |

Review shared-reader effects on LS-DYNA parameters. Retain exported function names
and signatures, model formats and solver physics. Do not change existing numerical
reference values or widen tolerances. Frozen Stage 1-7 evidence remains historical.

## Implementation order

1. **Capture the failures in the compact tests.** Keep a literal control model
   that succeeds today. Assert each parameterized field directly through the
   reader API before running Starter, so a later printing failure cannot hide an
   earlier substitution error. Retain the existing isolated probes for diagnosis.

2. **Fix numeric storage and printing.** In `SetExpressionValue`, use the integer
   attribute key for integer results. Make parameter listing read the active
   name/type/value fields, including evaluated expressions and text length.
   Correct all four listing paths, with checked value access and initialized
   values. Do not suppress parameter printing to avoid the crash.

3. **Repair TEXT parsing and replacement.** Fix the CFG header/title mismatch
   first, then exercise the existing substitution hook, which currently returns
   `false` unconditionally. Implement the required replacement in the shared
   reader path with bounded field handling. Cover exact text references, fixed
   lengths, length zero, a whole numeric card supplied by TEXT, and `$` stitching
   in a title. Parameter definitions must not be substituted as ordinary uses.

4. **Fail unresolved input explicitly.** Validate existence/type at the actual
   reference/evaluation boundary and use the existing file/line diagnostics.
   Ensure missing direct references, missing expression arguments, invalid
   expressions and cycles cannot become successful zero substitutions. Do not
   use zero as the failure sentinel, or reject valid negative/zero values.
   Preserve supported numeric coercion and text-to-card substitution. Verify
   failure clears parameter state before the next model load.

5. **Build and run the bounded gate.** Incrementally rebuild OpenReader and
   Starter. Reuse the current Engine because no Engine source/serialization change
   is planned. Run the new cases, existing API/loading/query/contact/rigid-conversion checks and
   the shared-reader compatibility checks. Record before/after values, status,
   listing output, input/binary hashes and physical comparisons.

## Minimum validation set

Use **two successful decks and four generated single-error variants**. Each
parameter type is exercised in the same successful parameterized model; scope is
checked once with REAL. There is no type-by-scope/platform test matrix.

| Case | Contents and assertions | Execution |
| --- | --- | --- |
| A: literal control | Existing small rigid-cube model, with literal values matching B, including its include/submodel layout and expected titles. | Reader, Starter, Engine |
| B: parameterized equivalent | All five types. `INTEGER -> INT_EXPR` supplies a valid function/ID reference; `REAL -> REAL_EXPR` supplies a real model/load field. Assert `2-1=1` and `6000*2+345=12345`. Use one integer reference in a keyword/header ID as well as data-card references. TEXT covers a title, `$` suffix, a fixed-length field and a full-card value. Include one local REAL override, global uses outside/before/after that submodel, a negated reference and a legitimate zero expression. | Reader, Starter, Engine |
| N1: missing direct reference | Remove one referenced definition; require a named file/line error, failed load and no usable restart. | Reader, Starter |
| N2: missing expression argument | Replace one argument with an undefined name; require an evaluation error, not a zero result. | Reader, Starter |
| N3: malformed expression | Introduce one syntax error into an expression; require a bounded, readable failure. | Reader, Starter |
| N4: cyclic expressions | Create one dependency cycle; require failure without recursion overflow or a hang. | Reader, Starter |

The four negative variants are generated from B, each with only its intended
error. Run them separately because one error must not hide another. After each
failed reader load, reload the existing good deck and check that definitions and
entities did not leak. Use fresh subprocesses for crash-prone listing checks and
fresh output directories for Starter/Engine runs.

This requires **two Engine simulations**, one per successful deck. Compare
initialization mass/inertia, load/function references, histories, displacement,
velocity and energy using the existing physical assertions and tolerances.
The two decks must have equal physical inputs after substitution; expected
parameter values/titles are independently specified, not derived by evaluating
the same expressions in the test. Require finite results and normal termination.

The ordinary existing reader/query tests cover native and keyword loading. If a
shared substitution/evaluation path changes, add one focused LS-DYNA parameter
reader control for the affected path. It requires no additional Engine run.

## Acceptance and limits

- B has the expected IDs, numeric values, text and scope; its listings contain
  actual names/values for both global and local parameters. There is no error 760,
  access violation, empty-name listing or unresolved reference silently changed to zero.
- Legitimate zero, negative values and negated references remain valid. All four
  invalid variants fail before producing a usable restart, with bounded runtime.
- A and B pass the same physical assertions without tolerance/reference changes.
  Existing focused reader tests and the affected shared-format control pass.
- Add the tested syntax and remaining expression limitations to the reader README.
  Do not declare complete Templex compatibility or resolve unrelated Stage 7
  regression failures as part of this repair.

SP, MPI, Linux and ARM64 parameter validation remain deferred. Hosted CI has been
updated but has not been dispatched. Existing Stage 7 release blockers remain.
