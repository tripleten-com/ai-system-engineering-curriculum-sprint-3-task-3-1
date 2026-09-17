# Task 3.1 evidence guide

Use [the supplied rollout evidence pack](evidence-pack.json) for the six graded evidence
answers. Perform your own rollout and rollback for the release record and the Project
Defense; passing the evidence answers does not replace the runtime checks of your Compose file.

## What the pack contains

The pack was captured from the reference run of this Task on one host. It holds:

| Record | What it is |
|---|---|
| `R01_weak_gate_roll_forward` | The `poe roll-forward` record with the supplied health check still probing `/health/live` |
| `R02_ready_gate_roll_forward` | The same command after the health check probed `/health/ready` with a `start_period` covering the warm-up |
| `R03_roll_back` | The `poe roll-back` record that followed R02 |
| `R04_running_images_after_candidate` | `docker compose ps` for api and worker while the candidate was running |
| `R05_applied_limits` | The `limits` block of `poe release-status` after limits were declared |
| `R06_health_checks` | The two API health check definitions, weak and repaired, as Compose rendered them |

Each rollout record has the same shape as the one your own `poe roll-forward` prints:
`requested_tag`, `compose_wait_seconds`, `first_probe` with `ready_status` and `build_version`,
and `running_images`.

## How to answer

- `weak_gate_first_probe_status` and `ready_gate_first_probe_status` are the `first_probe.ready_status`
  values of R01 and R02. Copy the integers.
- `claim_classifications` covers the five claims in the pack's `claims` block. A claim is an
  **observation** when one record shows it directly. It is an **inference** when it follows from
  a record together with the configuration in R06, but no record shows it. It is
  **not-established** when nothing in the pack could settle it either way.
- `fidelity_limitation` names one way this local evidence differs from a managed rollout. Take
  it from what the pack itself states about its capture: `provenance.limits` and
  `provenance.capture_environment`. More than one option is stated there, and the check accepts
  any option the pack states. An option that is true of Docker in general but that the pack
  never records is not supported by its records.

## What the pack does not say

The pack has no request log during the recreate window, no memory sample under load, and no
second host. A claim about what users experienced during the rollout, or about what a limit
prevented, cannot be settled from it. Say so in the answer sheet rather than filling the gap
with a reasonable guess.

## Boundary

The pack is read-only and versioned with this Task release. Your own runs will differ in
`compose_wait_seconds`, timestamps, and container names; that is expected, and the difference
belongs in your release record, not in the graded fields.
