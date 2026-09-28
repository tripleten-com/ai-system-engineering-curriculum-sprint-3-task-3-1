# Task 3.1 release record

This record supports the Project Defense. It is not graded by the automated checks; they
read `submission.yaml`, `compose.yaml`, and the running stack. Replace every italic
placeholder line below with your own evidence; `poe verify` fails while any placeholder
remains. State the command, the time window, and what you saw. Keep the supplied evidence
pack separate from your own runs.

## Step 1 - The pinned release

Which images are named, which tag is the default, and how you confirmed that `poe start`
no longer produces an unnamed build.

Host: Windows 11 with Docker Desktop, Compose project `ais-20260928-083535-cf44bdfc`.
Run window: 2026-09-28, between `poe start` and `poe release-build`.

`infra/release/manifest.yaml` names `coldline-api` and `coldline-worker`, with `3.1.0` as the
`known_good` release and `3.1.1` as the `candidate`. In `compose.yaml` I gave all three
first-party services an `image:` line that reads the release from one variable:

- `api` → `coldline-api:${COLDLINE_RELEASE_TAG:-3.1.0}`
- `initializer` → `coldline-api:${COLDLINE_RELEASE_TAG:-3.1.0}` (it runs the API image)
- `worker` → `coldline-worker:${COLDLINE_RELEASE_TAG:-3.1.0}`

The `build:` blocks stay, so `poe start` still builds from source — but it now tags the result
with the manifest name instead of `latest`, and the default in the substitution is the
known-good tag, so an unset variable can only start `3.1.0`.

`poe release-build` reported the four references it built:

```json
{"built": ["coldline-api:3.1.0", "coldline-api:3.1.1",
           "coldline-worker:3.1.0", "coldline-worker:3.1.1"]}
```

Confirmation, with `COLDLINE_RELEASE_TAG` unset, from `docker compose --profile observability
--profile localstack config`:

```text
api          image: coldline-api:3.1.0
initializer  image: coldline-api:3.1.0
worker       image: coldline-worker:3.1.0
```

With `COLDLINE_RELEASE_TAG=3.1.1` the same render moves all three at once:

```text
api => coldline-api:3.1.1
initializer => coldline-api:3.1.1
worker => coldline-worker:3.1.1
```

So a rollout is one environment change, not an edit to `compose.yaml`, and the tag that is
running is readable from `docker compose ps` rather than guessed from `latest`.

## Step 2 - Roll forward and back

The `poe roll-forward` record: how long Compose waited, what the first probe saw, which
build answered. Then the same for `poe roll-back`. Say what you changed in the health check
and why the first probe changed with it.

My own runs, 2026-09-28, Compose project `ais-20260928-083535-cf44bdfc`, no user traffic.

**Before the repair — the supplied liveness gate.** `poe roll-forward` at 08:39:43 UTC:

```json
{"release": "candidate", "requested_tag": "3.1.1", "compose_wait_seconds": 12.4,
 "first_probe": {"ready_status": 503, "build_version": "3.1.1"},
 "running_images": {"api": "coldline-api:3.1.1", "worker": "coldline-worker:3.1.1"}}
```

Compose waited 12.4 s and returned, but the first request got **503** from `3.1.1`. The
container was up and the candidate answered `/version`, so the new build was already the one
serving — it just could not serve yet. `poe roll-back` at 08:40:02 UTC returned in 10.9 s with
a 200 from `3.1.0`; the known-good build has `ready_delay_seconds: 0`, so the weak gate
happens to look fine in that direction, which is exactly why the rollout was the one that
exposed the problem.

**What I changed.** In `compose.yaml` the `api` health check now probes `/health/ready`
instead of `/health/live`, and I added `start_period: 30s`. `interval: 3s`, `timeout: 3s`
and `retries: 20` are unchanged.

- The endpoint is the substantive change: `--wait` returns when the health check passes, so
  the check has to ask the question the rollout depends on. `/health/live` only says the
  process exists, which is true from the first second of a 20 s warm-up.
- `start_period` is the tolerance: `infra/release/manifest.yaml` gives the candidate
  `ready_delay_seconds: 20`, so probes have to be allowed to fail for at least that long
  without counting against `retries`. I chose 30 s — the manifest's 20 s plus headroom for
  process start on a busy host — rather than something just over 20 s.

**After the repair.** `poe roll-forward` at 08:40:55 UTC:

```json
{"release": "candidate", "requested_tag": "3.1.1", "compose_wait_seconds": 32.1,
 "first_probe": {"ready_status": 200, "build_version": "3.1.1"},
 "running_images": {"api": "coldline-api:3.1.1", "worker": "coldline-worker:3.1.1"}}
```

`poe roll-back` at 08:41:14 UTC:

```json
{"release": "known_good", "requested_tag": "3.1.0", "compose_wait_seconds": 11.0,
 "first_probe": {"ready_status": 200, "build_version": "3.1.0"},
 "running_images": {"api": "coldline-api:3.1.0", "worker": "coldline-worker:3.1.0"}}
```

**Why the first probe changed.** The candidate image is identical in both rollouts; the only
difference is when Compose decides the rollout is finished. The wait went from 12.4 s to
32.1 s — about the 20 s warm-up the manifest declares — and that extra time is the gate
holding the rollout open until `/health/ready` answered 200. The rollback time barely moved
(10.9 s → 11.0 s) because `3.1.0` has no warm-up to wait through, which confirms the added
time is the candidate's readiness delay and not overhead from the new check.

## Step 3 - Resource bounds

The limits you chose, the sample you sized them from, and the `poe release-status` output
that shows Docker applied them.

**The sample I sized from.** `docs/fidelity/local-runtime.md`, the per-container
post-readiness memory sample of the Sprint 2 measured run (2026-09-07, Windows with Docker
Desktop): **API 81.7 MiB**, **worker 49.7 MiB**. That record states its own boundary — single
observations from one host, post-readiness, not averages, percentiles, or peaks — so I treated
each figure as a floor to stay well above, not as a size to match.

**What I declared** in `compose.yaml`, against `resource_bounds` in the manifest
(api `memory_mib: [256, 1024]`, `cpus: [0.25, 2.0]`; worker `memory_mib: [128, 512]`,
`cpus: [0.25, 2.0]`):

| Service | Sample | Memory limit | CPU limit | Inside bounds |
|---|---:|---:|---:|---|
| `api` | 81.7 MiB | 512 MiB | 1.0 | yes, mid-range of [256, 1024] |
| `worker` | 49.7 MiB | 256 MiB | 0.5 | yes, mid-range of [128, 512] |

Each memory limit is roughly six times the observed sample. That is deliberate: the sample is
one idle-ish reading, so a limit close to it would turn an ordinary request burst into an OOM
kill rather than into backpressure. The API gets the larger CPU share because it serves
requests and runs the retrieval path; the worker polls and processes in the background, so
half a CPU bounds it without starving it.

**What Docker applied.** `poe release-status`, 2026-09-28 08:43:04 UTC:

```json
{"limits": [
   {"service": "api", "container": "ais-20260928-083535-cf44bdfc-api-1",
    "image": "coldline-api:3.1.0", "memory_bytes": 536870912, "nano_cpus": 1000000000},
   {"service": "worker", "container": "ais-20260928-083535-cf44bdfc-worker-1",
    "image": "coldline-worker:3.1.0", "memory_bytes": 268435456, "nano_cpus": 500000000}],
 "probe": {"ready_status": 200, "build_version": "3.1.0"},
 "running_images": {"api": "coldline-api:3.1.0", "worker": "coldline-worker:3.1.0"}}
```

Converted from what Docker reports, not from what I typed:
536870912 / 1048576 = **512 MiB** and 1000000000 / 1e9 = **1.0 CPU** for `api`;
268435456 / 1048576 = **256 MiB** and 500000000 / 1e9 = **0.5 CPU** for `worker`.
Those four values are what went into `submission.yaml`. They happen to agree with the
Compose declaration, which is the check that Compose's `M` suffix is binary (1 M = 1048576)
and not decimal.

## What this local rollout does not prove

One sentence per limitation you would raise before calling this a production rollout.

These are limitations of **my own** runs above; the supplied evidence pack is read separately
in `submission.yaml` and is not the source of anything in this record.

- Compose stopped the single `api` container before starting the replacement, so the gate
  proves no request was served by a build that was not ready, but nothing here shows that no
  request went unanswered during the swap.
- I sent no traffic during either rollout, so the 200 first probes describe one request after
  the wait, not the experience of a dispatcher mid-session.
- `coldline-api:3.1.0` is a tag on a local build on this one host; it is not a registry digest
  another machine could pull, so "the same tag" is only reproducible here.
- The limits are declared values that Docker applied, and I took no memory sample under load,
  so I can say the bound exists but not what it prevented.
- `compose_wait_seconds` (12.4, 32.1, 11.0) are single observations from one Windows host with
  Docker Desktop, not averages or percentiles, and a slower or busier host would move them.
- Only one rollout and one rollback ran, so this is evidence that the procedure works once,
  not evidence about its failure rate.
- The rollout used one host's Docker scheduling; a cluster scheduler placing replicas across
  nodes is a different problem that this topology does not exercise.
