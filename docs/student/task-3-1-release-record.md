# Task 3.1 release record

This record supports the Project Defense. It is not graded by the automated checks; they
read `submission.yaml`, `compose.yaml`, and the running stack. Replace every italic
placeholder line below with your own evidence; `poe verify` fails while any placeholder
remains. State the command, the time window, and what you saw. Keep the supplied evidence
pack separate from your own runs.

## Step 1 - The pinned release

Which images are named, which tag is the default, and how you confirmed that `poe start`
no longer produces an unnamed build.

All timestamps below are 2026-09-30 UTC on one Windows host with Docker Desktop. My Compose
project name is supplied by the environment, so my container names read
`ais-20260929-231114-1814d392-*` instead of `coldline-task-3-1-*`; the service names are the
supplied ones.

**Images named.** From `infra/release/manifest.yaml` (`images.api: coldline-api`,
`images.worker: coldline-worker`) I gave three first-party services an `image:` name in
`compose.yaml`:

- `api` — `coldline-api:${COLDLINE_RELEASE_TAG:-3.1.0}`
- `initializer` — `coldline-api:${COLDLINE_RELEASE_TAG:-3.1.0}` (it runs the API image)
- `worker` — `coldline-worker:${COLDLINE_RELEASE_TAG:-3.1.0}`

**Default tag.** `3.1.0`, the manifest's `known_good` release. The candidate is `3.1.1`.
One variable, `COLDLINE_RELEASE_TAG`, selects the release; nothing is hard-coded per rollout.
The `build:` blocks stayed, so `poe start` still builds from source.

**Render check** (`docker compose --profile observability --profile localstack config`,
run three times in one throw-away shell):

```text
=== COLDLINE_RELEASE_TAG unset ===      api/initializer: coldline-api:3.1.0   worker: coldline-worker:3.1.0
=== COLDLINE_RELEASE_TAG=3.1.1 ===      api/initializer: coldline-api:3.1.1   worker: coldline-worker:3.1.1
=== COLDLINE_RELEASE_TAG unset again === api/initializer: coldline-api:3.1.0  worker: coldline-worker:3.1.0
```

The variable was removed from the shell again in the same run, so no later command inherited
the candidate tag.

**Before / after.** `./.tools/bin/uv run --frozen poe release-build` printed the four
references it built: `coldline-api:3.1.0`, `coldline-api:3.1.1`, `coldline-worker:3.1.0`,
`coldline-worker:3.1.1`.

`poe start` before the change reported anonymous, project-named builds:

```text
Image ais-20260929-231114-1814d392-api Built
Image ais-20260929-231114-1814d392-initializer Built
Image ais-20260929-231114-1814d392-worker Built
```

and `docker compose ps -a` showed `api` and `initializer` on
`ais-20260929-231114-1814d392-api` / `-initializer`, `worker` on
`ais-20260929-231114-1814d392-worker` — names that identify the Compose project, not a build.

`poe start` after the change reported named builds instead:

```text
Image coldline-api:3.1.0 Built     (twice: once for api, once for initializer)
Image coldline-worker:3.1.0 Built
```

Two distinct image references for three services, because `api` and `initializer` share the
API image. `docker compose ps -a` then showed `api` and `initializer` on `coldline-api:3.1.0`
and `worker` on `coldline-worker:3.1.0`, all healthy or exited-0 as before.

That pair of `ps -a` outputs is what shows the build is no longer unnamed: the same command
that used to report a project-scoped, effectively `latest` image now reports a manifest tag
that names one build the team can return to.

## Step 2 - Roll forward and back

The `poe roll-forward` record: how long Compose waited, what the first probe saw, which
build answered. Then the same for `poe roll-back`. Say what you changed in the health check
and why the first probe changed with it.

All three records are my own runs of `./.tools/bin/uv run --frozen poe roll-forward` and
`poe roll-back` on 2026-09-29/30, one host, no user traffic. `recorded_at` in each record is
the time the tool printed it.

**A. `poe roll-forward` behind the supplied liveness check — 2026-09-29T23:16:32Z**

```json
{
  "compose_wait_seconds": 12.1,
  "first_probe": { "build_version": "3.1.1", "ready_status": 503 },
  "recorded_at": "2026-09-29T23:16:32+00:00",
  "release": "candidate",
  "requested_tag": "3.1.1",
  "running_images": { "api": "coldline-api:3.1.1", "worker": "coldline-worker:3.1.1" }
}
```

Compose waited 12.1 s and then declared the rollout done. The candidate was running and
answering, but the first request to `/health/ready` got **503** from build `3.1.1`: the
rollout finished in the middle of the 20 s warm-up. A dispatcher's next request would have
landed on a build that says it cannot serve. I then ran `poe roll-back` (11.3 s, first probe
200 from `3.1.0`) to return to the known-good build before changing anything.

**B. `poe roll-forward` after the repair — 2026-09-29T23:17:41Z**

```json
{
  "compose_wait_seconds": 32.2,
  "first_probe": { "build_version": "3.1.1", "ready_status": 200 },
  "recorded_at": "2026-09-29T23:17:41+00:00",
  "release": "candidate",
  "requested_tag": "3.1.1",
  "running_images": { "api": "coldline-api:3.1.1", "worker": "coldline-worker:3.1.1" }
}
```

**C. `poe roll-back` after the repair — 2026-09-29T23:17:59Z**

```json
{
  "compose_wait_seconds": 11.1,
  "first_probe": { "build_version": "3.1.0", "ready_status": 200 },
  "recorded_at": "2026-09-29T23:17:59+00:00",
  "release": "known_good",
  "requested_tag": "3.1.0",
  "running_images": { "api": "coldline-api:3.1.0", "worker": "coldline-worker:3.1.0" }
}
```

**What I changed in the health check.** Two things on `api`, and nothing else:

1. The probe URL moved from `http://localhost:8000/health/live` to
   `http://localhost:8000/health/ready`.
2. I added `start_period: 30s`. `interval: 3s` and `retries: 20` stayed as supplied.

**Why the first probe changed from 503 to 200.** The two checks ask different questions.
`/health/live` answers as soon as the process is up, so `up --wait` returned at 12.1 s, while
the candidate's readiness endpoint was still returning 503 for its remaining warm-up seconds.
`/health/ready` answers 503 until the build can actually serve, so Compose kept waiting and
returned only at 32.2 s — the warm-up plus container start, which matches the manifest's
`ready_delay_seconds: 20` for the candidate. The first probe after that wait is the first
moment the gate allowed, and by then the answer is 200 from `3.1.1`.

`start_period: 30s` makes the tolerance a stated decision rather than a side effect. Inside
the start period a failing probe does not count against `retries`, so the warm-up 503s cannot
mark the container unhealthy; only after 30 s do 20 consecutive failures (3 s apart) fail the
container. Sizing it at 30 s leaves margin over the manifest's 20 s warm-up. The rollback is
fast (11.1 s) because the known-good build has `ready_delay_seconds: 0` — the same gate simply
has nothing to wait for.

The candidate image did not change between run A and run B. Only the gate did.

## Step 3 - Resource bounds

The limits you chose, the sample you sized them from, and the `poe release-status` output
that shows Docker applied them.

**The sample I sized from.** `docs/fidelity/local-runtime.md`, the per-container
post-readiness memory table of the Sprint 2 measured run (2026-09-07): **API 81.7 MiB**,
**worker 49.7 MiB**. That record states it is one post-readiness sample from one host, not an
average, a percentile, or a peak, so I treated it as a floor to leave room above, not as a
prediction of peak use.

**What I declared in `compose.yaml`.** The manifest bounds are api 256-1024 MiB / 0.25-2.0
CPUs and worker 128-512 MiB / 0.25-2.0 CPUs.

| Service | Memory declared | Headroom over the sample | CPUs declared |
|---|---|---|---|
| `api` | `512M` | ~6.3x above 81.7 MiB | `"1.0"` |
| `worker` | `256M` | ~5.2x above 49.7 MiB | `"0.5"` |

**The CPU limits are my own choice, not a measurement.** The supplied evidence contains no
CPU sample for either service. I gave `api` a whole CPU because it is the request-serving
process a dispatcher waits on, and `worker` half a CPU because it drains one queued message
at a time behind a 250 ms simulated model latency, so it is waiting far more than computing.
If a CPU measurement ever contradicts these, the measurement wins.

**What Docker applied** — `./.tools/bin/uv run --frozen poe release-status`,
2026-09-29T23:19:39Z, after `poe start` recreated both containers:

```json
{
  "limits": [
    {
      "container": "ais-20260929-231114-1814d392-api-1",
      "image": "coldline-api:3.1.0",
      "memory_bytes": 536870912,
      "nano_cpus": 1000000000,
      "service": "api"
    },
    {
      "container": "ais-20260929-231114-1814d392-worker-1",
      "image": "coldline-worker:3.1.0",
      "memory_bytes": 268435456,
      "nano_cpus": 500000000,
      "service": "worker"
    }
  ],
  "probe": { "build_version": "3.1.0", "ready_status": 200 },
  "recorded_at": "2026-09-29T23:19:39+00:00",
  "running_images": { "api": "coldline-api:3.1.0", "worker": "coldline-worker:3.1.0" }
}
```

Converted from what Docker reports, not from what I typed:
`536870912 / 1048576 = 512` MiB and `1000000000 / 1e9 = 1.0` CPU for `api`;
`268435456 / 1048576 = 256` MiB and `500000000 / 1e9 = 0.5` CPU for `worker`.
Those four numbers are the ones in `submission.yaml`. Both sit inside the manifest bounds,
and the probe confirms the limited API still served 200 from build `3.1.0`.

## What this local rollout does not prove

One sentence per limitation you would raise before calling this a production rollout.

These sentences are about **my own** runs (commands 12-17 of this session), not about the
supplied evidence pack; the pack's records answer the evidence questions in `submission.yaml`
and nothing here is taken from them.

- My rollout recreated the single `api` container, so Compose stopped the old build before it
  started the new one, and I have no evidence about a second replica carrying traffic in
  between, because there was none.
- I sent no requests during the recreate window, so my records show that no request was served
  by a build that was not ready, but say nothing about what a dispatcher mid-request would have
  experienced.
- `coldline-api:3.1.0` and `coldline-api:3.1.1` name builds that exist only in my local Docker
  image store; a tag is not a registry digest, so another host pulling the same tag is not
  guaranteed the same bytes.
- Both rollouts ran on one Windows host under Docker Desktop with the whole stack on the same
  machine, so one host's Docker scheduling stands in for a cluster scheduler, and the timings
  say nothing about a cross-node rollout.
- My `compose_wait_seconds` values (12.1 s, 32.2 s, 11.3 s, 11.1 s) are single observations
  from that one host, not averages or peaks, so they are not a rollout-duration budget.
- The memory and CPU limits I recorded are what Docker applied, observed on an idle stack; I
  took no memory sample under load, so I cannot claim the limits are sufficient for peak
  dispatch traffic, only that they are declared and bounded.
- The candidate's 20 s warm-up is a deliberate build-time setting from the manifest, not a
  real slow startup, so my gate was tested against a known delay rather than an unpredictable
  one.

## Supplied evidence pack — my reading

Read from `docs/student/evidence-pack.json` alone, following
`docs/student/evidence-guide.md`. None of this comes from my own runs above.

- `weak_gate_first_probe_status` = **503**, `R01_weak_gate_roll_forward.first_probe.ready_status`.
- `ready_gate_first_probe_status` = **200**, `R02_ready_gate_roll_forward.first_probe.ready_status`.

| Claim | Classification | Why |
|---|---|---|
| C01 first request after the weakly gated rollout saw a readiness failure from the candidate | `observation` | R01 shows it directly: `ready_status` 503 with `build_version` 3.1.1. |
| C02 users kept receiving responses while the container was recreated | `not-established` | The pack has no request log during the recreate window; its `provenance.limits` says so outright, so nothing could settle it either way. |
| C03 the rollback restored the known-good build version | `observation` | R03 shows it directly: `build_version` 3.1.0 and `running_images` on `coldline-api:3.1.0`. |
| C04 the readiness gate held the rollout open until the candidate finished warming up | `inference` | No record times the warm-up against the gate. It follows from R02's 33.0 s wait and 200 first probe together with R06's repaired check (`/health/ready`, `start_period` 30s) against R01's 13.2 s liveness-gated wait — records plus configuration, not a direct observation. |
| C05 the memory limit kept the api container below 512 MiB under load | `not-established` | R05 records only the limits Docker applied; the pack states no memory sample under load was taken, and there was no load. |

- `fidelity_limitation` = **`local_tag_not_registry_digest`**. The pack states it verbatim in
  `provenance.limits`: "Image tags name local builds on this host, not registry digests."
  `no_load_during_rollout` is also supported by the pack; I picked one.
