# Task 3.1 release record

This record supports the Project Defense. It is not graded by the automated checks; they
read `submission.yaml`, `compose.yaml`, and the running stack. Replace every italic
placeholder line below with your own evidence; `poe verify` fails while any placeholder
remains. State the command, the time window, and what you saw. Keep the supplied evidence
pack separate from your own runs.

All records below are my own runs on this host (Windows with Docker Desktop, Compose project
`ais-20260926-154043-d96da4cd`) on 2026-09-26, between 15:45 and 15:49 UTC. The supplied
evidence pack is not used anywhere in this file.

## Step 1 - The pinned release

Which images are named, which tag is the default, and how you confirmed that `poe start`
no longer produces an unnamed build.

`./.tools/bin/uv run --frozen poe release-build` built the four references the manifest names:
`coldline-api:3.1.0`, `coldline-api:3.1.1`, `coldline-worker:3.1.0`, `coldline-worker:3.1.1`.

In `compose.yaml` the three first-party services now name a manifest image through one variable:

- `api`: `image: coldline-api:${COLDLINE_RELEASE_TAG:-3.1.0}`
- `initializer`: `image: coldline-api:${COLDLINE_RELEASE_TAG:-3.1.0}` (it runs the API image)
- `worker`: `image: coldline-worker:${COLDLINE_RELEASE_TAG:-3.1.0}`

`3.1.0` is the default because `infra/release/manifest.yaml` names it as the `known_good`
release; `3.1.1` is the `candidate`. The `build:` blocks are unchanged, so `poe start` still
builds from source — but it now tags the result with the manifest name instead of `latest`.

I rendered `docker compose config --format json` twice at 15:44 UTC. With `COLDLINE_RELEASE_TAG`
unset it rendered `coldline-api:3.1.0` for `api` and `initializer` and `coldline-worker:3.1.0`
for `worker`; with `COLDLINE_RELEASE_TAG=3.1.1` all three switched to the `3.1.1` tags. After a
further `poe start`, `poe release-status` at 15:45:07 UTC reported
`running_images: {api: coldline-api:3.1.0, worker: coldline-worker:3.1.0}` — the containers run
named builds, not an anonymous `latest`.

## Step 2 - Roll forward and back

The `poe roll-forward` record: how long Compose waited, what the first probe saw, which
build answered. Then the same for `poe roll-back`. Say what you changed in the health check
and why the first probe changed with it.

**Before the repair — the supplied `/health/live` gate.**

`poe roll-forward` at 15:45:44 UTC:

```json
{
  "release": "candidate", "requested_tag": "3.1.1",
  "compose_wait_seconds": 13.0,
  "first_probe": { "ready_status": 503, "build_version": "3.1.1" },
  "running_images": { "api": "coldline-api:3.1.1", "worker": "coldline-worker:3.1.1" }
}
```

`poe roll-back` at 15:46:04 UTC: waited 11.9 s, first probe `200` from `3.1.0`.

Compose returned after 13.0 s because the liveness probe passes as soon as the process
accepts a connection. The candidate was alive but still inside its 20 s readiness warm-up, so
the first request after the rollout "finished" got a `503` from build `3.1.1`. The rollback was
not affected because the known-good build has `ready_delay_seconds: 0`.

**What I changed.** In the `api` health check I replaced the probed path `/health/live` with
`/health/ready` and added `start_period: 30s`; `interval: 3s`, `timeout: 3s` and `retries: 20`
stayed as supplied. The path change makes the gate ask the question the rollout actually
depends on — can this build serve? — instead of whether its process exists. The `start_period`
is set above the manifest's `releases.candidate.ready_delay_seconds: 20`, with 10 s of headroom,
so the probes that fail during the warm-up do not consume `retries` and mark the container
unhealthy; Docker keeps it in `starting` until readiness first answers `200`.

**After the repair — the `/health/ready` gate.**

`poe roll-forward` at 15:46:53 UTC:

```json
{
  "release": "candidate", "requested_tag": "3.1.1",
  "compose_wait_seconds": 32.5,
  "first_probe": { "ready_status": 200, "build_version": "3.1.1" },
  "running_images": { "api": "coldline-api:3.1.1", "worker": "coldline-worker:3.1.1" }
}
```

`poe roll-back` at 15:47:14 UTC:

```json
{
  "release": "known_good", "requested_tag": "3.1.0",
  "compose_wait_seconds": 12.5,
  "first_probe": { "ready_status": 200, "build_version": "3.1.0" },
  "running_images": { "api": "coldline-api:3.1.0", "worker": "coldline-worker:3.1.0" }
}
```

The candidate image did not change between the two rollouts and its warm-up is the same 20 s;
what changed is that the wait now contains it. 13.0 s became 32.5 s — roughly the same container
start plus the warm-up the gate previously skipped — and the first probe went from `503` to
`200`. That extra 19.5 s is the failure moved from the user to the rollout, which is the point
of the gate. The rollback stayed near its earlier time (11.9 s, then 12.5 s) because `3.1.0`
is ready as soon as it starts, so a readiness gate costs nothing there.

## Step 3 - Resource bounds

The limits you chose, the sample you sized them from, and the `poe release-status` output
that shows Docker applied them.

**Sizing basis.** The per-container post-readiness samples in `docs/fidelity/local-runtime.md`
(Sprint 2 measured run, 2026-09-07): API 81.7 MiB, worker 49.7 MiB. Those are single
post-readiness samples from one host, not peaks or averages, so I took headroom of roughly six
times the API sample and five times the worker sample rather than sizing tightly to them.
The admissible ranges come from `resource_bounds` in `infra/release/manifest.yaml`:
api 256–1024 MiB and 0.25–2.0 CPUs, worker 128–512 MiB and 0.25–2.0 CPUs.

**What I declared in `compose.yaml`:**

| Service | `memory` | `cpus` | Sample | Manifest bounds |
|---|---|---|---:|---|
| `api` | `512m` | `"1.0"` | 81.7 MiB | 256–1024 MiB, 0.25–2.0 |
| `worker` | `256m` | `"0.5"` | 49.7 MiB | 128–512 MiB, 0.25–2.0 |

The API gets the larger share of both because it serves the request path; the worker runs one
consumer with a 250 ms simulated model latency and does not need a full CPU.

**What Docker applied.** `poe start` recreated both containers, then `poe release-status` at
15:48:41 UTC reported:

```json
"limits": [
  { "service": "api",    "image": "coldline-api:3.1.0",
    "memory_bytes": 536870912, "nano_cpus": 1000000000 },
  { "service": "worker", "image": "coldline-worker:3.1.0",
    "memory_bytes": 268435456, "nano_cpus": 500000000 }
]
```

Converted: api 536870912 / 1048576 = **512 MiB** and 1000000000 / 1e9 = **1.0 CPU**; worker
268435456 / 1048576 = **256 MiB** and 500000000 / 1e9 = **0.5 CPU**. These reported values, not
the strings I typed, are what `submission.yaml` records. Both sit inside the manifest bounds.

## What this local rollout does not prove

One sentence per limitation you would raise before calling this a production rollout.

- Compose stopped the one `api` container before starting the new one, so the gate proves that
  no request was served by a build that was not ready, but not that no request went unanswered
  during the swap — a managed platform would bring a second replica in first.
- `coldline-api:3.1.0` is a tag on a local build on this machine, not a registry digest another
  host could pull, so nothing here shows that a second host would run the same bytes.
- I sent no traffic during either rollout, so these records say nothing about what a dispatcher
  would have experienced mid-rollout.
- The limits are values Docker reports as applied, measured against a single post-readiness
  memory sample taken on a different host and Sprint; no load test showed what they prevent, or
  that 512 MiB is enough under a burst.
- Every timing here (13.0 s, 32.5 s, 12.5 s) is one observation on one Windows host with warm
  build caches, not an average, a percentile, or a cold-pull figure.
- One host's Docker stands in for a scheduler: there is no node placement, no rolling update
  strategy, and no automatic rollback on a failed health gate — I ran `poe roll-back` by hand.
