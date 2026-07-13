# noc_c_model — Torus Routing & Deadlock-Safety Fix Plan

## Background

Code review of `noc_c_model` (2026-07-13) found that the `torus` topology is built with real wraparound links (`Topology.cpp: TorusTopology::build_network`), but routing decisions for it are computed by `XYRouting`, which uses non-modular (non-wraparound) distance comparisons. As a result, wraparound edges are never selected by routing, and `torus` behaves identically to `mesh` in every simulation run. Separately, the `architecture.routing` YAML field is parsed into `routing_type` in `main.cpp` but never consulted when selecting the routing algorithm — it has no effect. These two issues must be fixed together, because fixing only the first (giving torus a real wraparound-aware router) introduces a new deadlock exposure that the current mesh-equivalent behavior does not have, so a dateline/VC-safety mechanism must ship in the same change. A related, already-known gap of the same category exists for `ring` (shortest-path routing with no dateline).

This document defines *what* must change and how success is verified. It intentionally does not prescribe implementation code — that is left to the implementer.

## Goals

1. `topology: torus` must produce genuinely different, wraparound-aware routing decisions from `topology: mesh`, for any src/dst pair where the wraparound path is shorter than the direct path.
2. The `architecture.routing` config field must actually determine which routing algorithm is used. An unsupported/misspelled value must cause a clear, immediate failure — not a silent fallback.
3. Any routing algorithm that can route a packet across a wraparound edge (torus in either dimension, ring) must not introduce a cyclic channel dependency that can deadlock the network. A dateline-based VC-class mechanism is required for this.
4. Whether a simulation run ended in deadlock or in a fully-completed state must be programmatically distinguishable (exit code and/or an unambiguous status line), so automated DSE sweeps do not silently treat a stalled run's partial numbers as valid results.

## Scope of work

### 1. Wraparound-aware routing for Torus
Add a routing algorithm dedicated to the torus topology, automatically selected whenever `architecture.topology: torus`. For each dimension (X then Y, consistent with the existing dimension-order convention used by mesh), it must compare the direct distance against the wraparound distance and choose whichever is shorter, mapping to the existing port numbering (1=N, 2=E, 3=S, 4=W) already used by `TorusTopology::build_network`. Mesh must continue to use the existing non-wraparound algorithm unchanged.

### 2. Config-driven algorithm selection
`architecture.routing`, once parsed from YAML, must actually be used to decide which algorithm class is instantiated for the given topology (today it is read and discarded). If the requested routing value is not supported for the given topology, the program must exit with a clear error message and non-zero status rather than silently defaulting.

### 3. Dateline mechanism (deadlock safety)
Whenever a flit's route crosses a wraparound edge (torus, either dimension; ring, its single wrap point), it must be forced onto a distinct virtual-channel class reserved for "already wrapped" traffic, and this transition must be one-directional (a flit that has wrapped must never be assignable back to the "not yet wrapped" VC class for the remainder of its journey). This requires the forwarding logic to be able to change a flit's VC under this specific rule (today VC is hardcoded to stay unchanged when forwarding — no other reason to change VC is in scope here). Any topology that requires this mechanism (torus, ring) must be validated at startup to have enough VCs to support it; if not, startup must fail with a clear error instead of running in a deadlock-prone configuration.

Verification requirement: a sustained high-injection-rate uniform-random-traffic run on torus and on ring, at multiple sizes, for a defined long duration, must complete with zero deadlock detections and 100% packet delivery within `max_cycles`.

### 4. Observable deadlock / incompletion status
When deadlock is detected, or when `max_cycles` is reached without 100% delivery, the program must signal this distinctly from a normal successful completion — via a dedicated non-zero exit code and/or an unambiguous, greppable status line. Before finalizing the output format, check what fields `dse_tools/runners/*.py` currently parse from this program's stdout, so the new status signal doesn't break existing sweep parsing and, ideally, gets consumed by it to filter out stalled runs.

## Acceptance criteria

- For a fixed torus config, at least one routing decision differs from the same config run as mesh, for a src/dst pair whose shortest path crosses a wraparound edge (verifiable via hop-count/latency output or an added debug trace of chosen output ports).
- Setting `architecture.routing` to an unsupported value causes immediate, clear failure instead of being silently ignored.
- Long stress runs (high injection rate, uniform random traffic) on torus and ring, across multiple sizes, complete with no deadlock detection and 100% delivery.
- A run that stalls (deadlock or incomplete delivery at `max_cycles`) is distinguishable from a normal completed run via exit code / stdout status, verified by a scripted check.
- No regression for existing `mesh` and non-wraparound-crossing `ring` traffic: same routing decisions, same latency/throughput numbers, same successful exit code, on representative existing configs (`NoC_config.yaml`, `check_booksim.yaml`).

## Non-goals (tracked separately, not part of this plan)

- `inject_flit` allocating VCs independently per flit call, which can fragment one packet's flits across different VCs.
- Unbounded-burst local injection bypassing the per-cycle, one-flit-per-link bandwidth model used elsewhere.
- Any other previously-identified issues in `huawei_c_model` or the Python DSE toolchain.

## Files likely in scope (for scoping/reference only)

- `noc_c_model/Routing.h`, `noc_c_model/Routing.cpp` — new torus algorithm.
- `noc_c_model/Router.h`, `noc_c_model/Router.cpp` — VC-class forwarding rule, startup VC-count validation.
- `noc_c_model/main.cpp` — algorithm selection wiring, routing-value validation, exit code / status signaling.
- `noc_c_model/Config.h`/`.cpp` — if VC-count validation belongs here.
- `dse_tools/runners/*.py` — check/update status parsing if the completion-status output format changes.
