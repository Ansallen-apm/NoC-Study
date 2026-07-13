# huawei_c_model — Correctness & Test-Coverage Fix Plan

## Background

Code review of `huawei_c_model` (2026-07-13) found that commit `8fc4963` ("implement Phase 2.8 Chaos Stress Test") added a chaos/invariant test and, in the same change, fixed a real flit-duplication bug in `RBRG_L1`/`RBRG_L2` (switching their ejection logic from reading `curr_slots` to reading `next_slots`, to respect `CrossStation` passthrough ordering). The very next commit, `28c7732` (titled as a docs-only change), deleted the new test file entirely and reverted the bug fix back to the buggy `curr_slots` version. `todo.md`'s Phase 2.8 checkboxes are still unchecked, consistent with the test's absence, even though the surrounding narrative implied it was completed. This is currently the most severe open issue in the module: a known, previously-fixed bug is active again, and the regression test that would have caught the revert does not exist.

Beyond that, review found: an eject-queue capacity invariant that can be silently violated under tiny-buffer/high-load conditions; config parsing that never validates required YAML fields, letting missing keys become indeterminate values used directly in array sizing and modulo arithmetic; and two of the model's core anti-starvation/anti-livelock test files (`test_e_tag.cpp`, `test_i_tag.cpp`) that contain no real assertions, only `EXPECT_TRUE(true)` placeholders, despite being presented in `huawei_readme.md` as functional verification of those mechanisms.

This document defines *what* must change and how success is verified. It intentionally does not prescribe implementation code — that is left to the implementer.

## Goals

1. The `RBRG_L1`/`RBRG_L2` ejection logic must correctly read the same-cycle-authoritative slot state (i.e., the state a component actually writes for consumption within the same simulated cycle), not a stale pre-update snapshot, so that flits are never duplicated or dropped at ring/bridge boundaries.
2. A permanent, always-run regression test must exist that stresses the network under tiny buffers and high injection rate and asserts real runtime invariants: flit conservation (every injected flit is eventually accounted for exactly once — in flight, queued, or ejected/absorbed — with no duplication or loss), slot mutual exclusion (no slot ever holds more than one flit at a time), and liveness (no flit remains permanently stuck; the network makes forward progress under sustained load).
3. `EjectQueue` (or equivalent) must never hold more entries — reserved plus actual — than its configured capacity, under any sequence of reservation and push operations.
4. Missing or malformed required fields in the YAML config must be caught and reported as a clear startup error, not silently left as indeterminate/default-zero values that later get used in buffer sizing or modulo arithmetic.
5. `test_e_tag.cpp` and `test_i_tag.cpp` must contain real, meaningful assertions that verify I-tag injection-reservation (anti-starvation) and E-tag ejection-reservation (anti-livelock/deflection) behavior under scenarios where these mechanisms are actually exercised — not placeholder assertions that always pass. Test coverage claims in `huawei_readme.md` must match what the tests actually verify.

## Scope of work

### 1. Restore and harden the RBRG_L1 / RBRG_L2 ejection fix
Re-apply the same-cycle-authoritative-state fix that commit `8fc4963` made and commit `28c7732` reverted, in both `rbrg_l1.cpp` and `rbrg_l2.cpp`. Confirm the fix is consistent with how `CrossStation` and the bridges are ordered within a simulated cycle in `simulator.cpp`, so the bridge always consumes the correct, final state of the slot for that cycle.

### 2. Restore and expand the chaos/invariant regression test
Recreate a test equivalent to the deleted `test_chaos_stress.cpp` (dense multi-ring topology, tiny buffers, low deadlock threshold, high-rate uniform-random traffic, long run length) and make its runtime invariant checks (flit conservation, slot mutual exclusion, liveness) real, always-executed assertions that fail the test on violation — not just log output. This test must be part of the standard test suite that runs on every change (wired into `CMakeLists.txt` alongside the other `test_*.cpp` files), so a future revert of the fix in item 1 would be caught automatically.

### 3. Fix eject-queue capacity accounting
Ensure that whatever function currently determines whether a new reservation can be granted accounts for the queue's *actual current occupancy*, not only the count of outstanding reservations, so that the true worst-case size (occupied + reserved) can never exceed the configured capacity at any point.

### 4. Add YAML config validation
For every required field currently read via an `if (node[...])` pattern with no `else` branch (across ring, node, bridge, and multi-ring config structures in `config.cpp`), add explicit validation that fails config parsing with a clear, specific error message (naming the missing field and its containing section) if the field is absent or of the wrong type. Parsing must not return success while leaving any required field at an indeterminate value. Decide and document, for each field, whether it is required (must error if missing) or genuinely optional (has a documented, sane default) — and apply that decision consistently.

### 5. Replace stub tests with real E-tag / I-tag verification
Design and implement scenarios in `test_e_tag.cpp` that actually create ejection contention (multiple flits destined for the same station in the same cycle) and verify the E-tag reservation prevents livelock/starvation of the reserving flit as intended. Do the same in `test_i_tag.cpp` for injection contention and I-tag anti-starvation. Update `huawei_readme.md`'s test-coverage description if the actual verified scope differs from what's currently claimed.

## Acceptance criteria

- The chaos/invariant test (restored per item 2) passes on the current codebase and would fail if the ejection logic were reverted to the buggy `curr_slots`-based version (verify by temporarily reintroducing the old code locally and confirming the test catches it, then restoring the fix).
- A fuzz/stress run with `capacity = 1` on an eject queue under sustained contention never observes the queue's occupied+reserved count exceed 1, checked programmatically (not just by inspection).
- Starting the simulator with a config file missing a required field (for each of ring/node/bridge/multi-ring sections) produces a non-zero exit and a specific, human-readable error naming the missing field, instead of proceeding to run.
- `test_e_tag.cpp` and `test_i_tag.cpp` contain assertions that fail when the corresponding tag mechanism is disabled or broken (verify by temporarily disabling each mechanism and confirming the relevant test fails), and pass on the current correct implementation.
- No regression in existing passing tests (`test_full_ring.cpp`, `test_single_ring.cpp`, `test_rbrg_l1.cpp`, `test_rbrg_l1_backpressure.cpp`, `test_rbrg_l2.cpp`, `test_rbrg_l2_credit.cpp`, `test_swap_deadlock.cpp`, `test_simulator.cpp`, `test_config.cpp`, `test_validation.cpp`) after all changes above.

## Non-goals (tracked separately, not part of this plan)

- Latency statistics currently reflecting hop count rather than true elapsed simulation cycles (`create_cycle`/`inject_cycle` in `flit.hpp` are never populated).
- RBRG bridges defaulting to "try CW first" when injecting onto a remote ring instead of choosing a direction based on the flit's actual destination.
- `assert()`-based structural parameter checks in `rbrg_l1.cpp`/`rbrg_l2.cpp` being compiled out in Release/NDEBUG builds.
- `HotspotGenerator` always tagging synthetic traffic `Direction::CW` regardless of topology/destination.
- Bridge queue/credit depth being hardcoded in `simulator.cpp` instead of YAML-configurable.
- Any issues previously identified in `noc_c_model` or the Python DSE toolchain.

## Files likely in scope (for scoping/reference only)

- `huawei_c_model/src/rbrg_l1.cpp`, `huawei_c_model/src/rbrg_l2.cpp` — ejection logic fix.
- `huawei_c_model/tests/test_chaos_stress.cpp` (to be recreated), `huawei_c_model/tests/test_e_tag.cpp`, `huawei_c_model/tests/test_i_tag.cpp`.
- `huawei_c_model/CMakeLists.txt` — ensure the chaos test is registered and always run.
- `huawei_c_model/include/node_interface.hpp` — `EjectQueue` capacity accounting.
- `huawei_c_model/include/config.hpp`, `huawei_c_model/src/config.cpp` — required-field validation.
- `huawei_c_model/huawei_readme.md` — test-coverage description accuracy.
- `todo.md` — Phase 2.8 status should reflect actual restored/completed state once done.
