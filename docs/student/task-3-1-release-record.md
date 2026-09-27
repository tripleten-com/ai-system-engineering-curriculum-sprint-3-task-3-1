# Task 3.1 release record

This record supports the Project Defense. It is not graded by the automated checks; they
read `submission.yaml`, `compose.yaml`, and the running stack. Replace every italic
placeholder line below with your own evidence; `poe verify` fails while any placeholder
remains. State the command, the time window, and what you saw. Keep the supplied evidence
pack separate from your own runs.

## Step 1 - The pinned release

Which images are named, which tag is the default, and how you confirmed that `poe start`
no longer produces an unnamed build.

My own run, 2026-09-27, Windows 11 with Docker Desktop, Compose project
`ais-20260927-090745-b53248a5` (the API host port and project name come from my local
environment).

`poe release-build` built the four references the manifest names:
`coldline-api:3.1.0`, `coldline-api:3.1.1`, `coldline-worker:3.1.0`, `coldline-worker:3.1.1`.

In `compose.yaml` I gave the three first-party services an `image:` name taken from
`infra/release/manifest.yaml`, parameterized with the release variable:

- `api` — `coldline-api:${COLDLINE_RELEASE_TAG:-3.1.0}`
- `initializer` — `coldline-api:${COLDLINE_RELEASE_TAG:-3.1.0}` (it runs the API image)
- `worker` — `coldline-worker:${COLDLINE_RELEASE_TAG:-3.1.0}`

The default is the known-good tag `3.1.0`, so an unset variable always selects the build the
stack starts on. The `build:` blocks stay, so `poe start` still builds from source — it now
tags the result instead of leaving it anonymous.

`docker compose config` rendered, with `COLDLINE_RELEASE_TAG` unset:

```text
api: coldline-api:3.1.0
initializer: coldline-api:3.1.0
worker: coldline-worker:3.1.0
```

and with `COLDLINE_RELEASE_TAG=3.1.1` all three moved together:

```text
api: coldline-api:3.1.1
initializer: coldline-api:3.1.1
worker: coldline-worker:3.1.1
```

How I confirmed `poe start` no longer produces an unnamed build: before the change,
`poe release-status` at 09:11:03 UTC reported the running images as
`ais-20260927-090745-b53248a5-api` and `ais-20260927-090745-b53248a5-worker` — the
project-derived names Compose invents when no `image:` is given. After the change I ran
`poe start` again (48.4 s, it recreated `api` and `worker`) and `poe release-status` at
09:12:19 UTC reported:

```json
"running_images": {"api": "coldline-api:3.1.0", "worker": "coldline-worker:3.1.0"},
"probe": {"build_version": "3.1.0", "ready_status": 200}
```

The manifest tags recorded in `submission.yaml` are `known_good_tag: 3.1.0` and
`candidate_tag: 3.1.1`.

## Step 2 - Roll forward and back

The `poe roll-forward` record: how long Compose waited, what the first probe saw, which
build answered. Then the same for `poe roll-back`. Say what you changed in the health check
and why the first probe changed with it.

All four records below are my own runs on 2026-09-27, in the order I ran them.

**Before the repair — the supplied liveness gate.**

`poe roll-forward`, recorded at 09:13:12 UTC:

```json
{"release": "candidate", "requested_tag": "3.1.1", "compose_wait_seconds": 12.5,
 "first_probe": {"ready_status": 503, "build_version": "3.1.1"},
 "running_images": {"api": "coldline-api:3.1.1", "worker": "coldline-worker:3.1.1"}}
```

Compose waited 12.5 s and returned. The candidate was already answering `/version` as
`3.1.1`, so the swap had happened, but the first readiness request got **503**: the
candidate was alive and not yet able to serve. The supplied check probed `/health/live`,
which the process answers as soon as it starts, so `up --wait` opened the gate roughly
8 s before the 20 s warm-up the manifest declares had finished.

`poe roll-back`, recorded at 09:13:32 UTC, returned the stack to the known-good build:

```json
{"release": "known_good", "requested_tag": "3.1.0", "compose_wait_seconds": 11.3,
 "first_probe": {"ready_status": 200, "build_version": "3.1.0"},
 "running_images": {"api": "coldline-api:3.1.0", "worker": "coldline-worker:3.1.0"}}
```

**What I changed.** In the `api` health check I replaced `/health/live` with
`/health/ready` and added `start_period: 30s`; `interval: 3s`, `timeout: 3s`, and
`retries: 20` stayed as supplied. Two separate changes, for two reasons:

- The endpoint decides *what* the gate asks. `/health/live` answers "the process runs";
  `/health/ready` answers "this build can serve a request", which is the condition a
  rollout actually needs before it counts as finished.
- `start_period` decides how long the gate *tolerates* a build that is not ready yet.
  `releases.candidate.ready_delay_seconds` in the manifest is 20, so I chose 30 s: enough
  to cover the declared warm-up with margin on a slower host, while inside the start
  period Docker does not count the early 503s against `retries`. Raising `retries`
  instead would not have helped, because the liveness probe never fails in the first
  place — the gate would still open early.

**After the repair — the readiness gate.**

`poe roll-forward`, recorded at 09:14:21 UTC:

```json
{"release": "candidate", "requested_tag": "3.1.1", "compose_wait_seconds": 32.8,
 "first_probe": {"ready_status": 200, "build_version": "3.1.1"},
 "running_images": {"api": "coldline-api:3.1.1", "worker": "coldline-worker:3.1.1"}}
```

`poe roll-back`, recorded at 09:14:41 UTC:

```json
{"release": "known_good", "requested_tag": "3.1.0", "compose_wait_seconds": 12.1,
 "first_probe": {"ready_status": 200, "build_version": "3.1.0"},
 "running_images": {"api": "coldline-api:3.1.0", "worker": "coldline-worker:3.1.0"}}
```

**Why the first probe changed.** The candidate image is identical in both rollouts — the
warm-up did not get shorter or longer. What changed is when Compose decided the rollout
was done. The wait grew from 12.5 s to 32.8 s, about the 20 s the candidate spends
refusing requests, and the first probe after the gate is now a 200 from `3.1.1` instead
of a 503. The rollback stayed at about 12 s both times, because the known-good build has
`ready_delay_seconds: 0` and is ready as soon as it starts — the readiness gate costs
nothing when there is nothing to wait for.

Recorded in `submission.yaml`: `observed_candidate_version: 3.1.1` and
`observed_rollback_version: 3.1.0`.

## Step 3 - Resource bounds

The limits you chose, the sample you sized them from, and the `poe release-status` output
that shows Docker applied them.

**The sample I sized from.** The per-container post-readiness memory sample in
`docs/fidelity/local-runtime.md`, measured run of 2026-09-07: **API 81.7 MiB** and
**worker 49.7 MiB**, on a host with 15.54 GiB available to the Docker VM. That record
says plainly what it is — one post-readiness sample from one host, not an average, a
percentile, or a peak — so I treated it as a floor to stay well above, not as a target.

**The limits I chose**, both inside the `resource_bounds` the manifest publishes:

| Service | Sample | Manifest bounds | My memory limit | My CPU limit |
|---|---:|---|---:|---:|
| `api` | 81.7 MiB | 256–1024 MiB, 0.25–2.0 CPUs | 512 MiB | 1.0 |
| `worker` | 49.7 MiB | 128–512 MiB, 0.25–2.0 CPUs | 256 MiB | 0.5 |

Reasoning. 512 MiB is about six times the API sample and 256 MiB about five times the
worker sample. That is deliberate slack: a single idle-state sample says nothing about
what a burst of retrieval requests or a batch of queued exceptions costs, and a container
that crosses its memory limit is killed rather than slowed, so the cost of sizing too
tightly is much worse than the cost of sizing generously. Both stay in the middle of the
published ranges, so the limit is still a real bound rather than a no-op at the top of
the range. For CPU, the API gets a whole core because it serves requests concurrently;
the worker processes one message at a time, so half a core is enough and leaves the rest
of the core for the API on a shared host.

**What Docker applied.** After adding the `deploy.resources.limits` blocks I ran
`poe start`, which recreated both containers, then `poe release-status` at 09:16:28 UTC:

```json
"limits": [
  {"service": "api",    "container": "…-api-1",    "image": "coldline-api:3.1.0",
   "memory_bytes": 536870912, "nano_cpus": 1000000000},
  {"service": "worker", "container": "…-worker-1", "image": "coldline-worker:3.1.0",
   "memory_bytes": 268435456, "nano_cpus": 500000000}
],
"probe": {"build_version": "3.1.0", "ready_status": 200}
```

Converted: 536870912 / 1048576 = **512 MiB** and 1000000000 / 10^9 = **1.0 CPU** for the
API; 268435456 / 1048576 = **256 MiB** and 500000000 / 10^9 = **0.5 CPU** for the worker.
Those four converted values — what Docker reported, not what I typed — are what I entered
in `submission.yaml`. They agree with the Compose values here because Compose reads the
`m` suffix as MiB, which is worth checking rather than assuming.

## What this local rollout does not prove

One sentence per limitation you would raise before calling this a production rollout.

- Compose stopped the one `api` container before starting the replacement, so the health
  gate proves no request was served by a build that was not ready, but nothing here shows
  that no request went unanswered during the swap — a managed platform would bring a
  second replica in first.
- The tag names a build that exists only in this host's local Docker image store; it is
  not a registry digest another machine could pull, so "same tag" does not yet mean "same
  bytes" anywhere but here.
- Every number above is a single observation on one Windows host with Docker Desktop, not
  an average or a percentile, so a 32.8 s rollout says how long this run took, not how
  long the next one will.
- No user traffic ran during any of my four rollouts, so these records say nothing about
  how the swap behaves under load, or about what latency a dispatcher would have seen.
- The resource limits are values Docker confirmed it applied, sized from an idle
  post-readiness memory sample; I have no measurement under load, so I cannot claim the
  limits are sufficient — only that they are bounds and that the stack stayed healthy
  inside them.
- One host's Docker scheduling stands in for a cluster scheduler here; there is no second
  node, no placement decision, and no drain-and-reschedule behavior to observe.

Note on sources: everything in this record comes from my own runs of 2026-09-27, listed
above with their command and UTC timestamp. The supplied evidence pack in
`docs/student/evidence-pack.json` is a separate reference run from 2026-09-17; I used it
only for the answers in `submission.yaml` that name it as their source, and none of its
numbers appear here as mine.
