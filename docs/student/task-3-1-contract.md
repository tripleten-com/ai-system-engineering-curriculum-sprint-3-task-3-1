# Task 3.1 — Reproducible release contract

Pin the two supplied Coldline releases to immutable image tags, make the API health check a
real readiness gate, roll the stack forward to the candidate and back to the known-good build,
and bound the API and worker resources. You edit the Compose file, record what you observed,
and classify the supplied rollout evidence. You write no application code.

## What is assessed, and by whom

| Assessed | By |
|---|---|
| The pull request changes only `compose.yaml`, `submission.yaml`, and `docs/student/task-3-1-release-record.md` | Automated, in this repository |
| The first-party images are named from the manifest and default to the known-good tag | Automated, in this repository, against the rendered Compose file |
| The API health check probes readiness and tolerates the candidate warm-up | Automated, in this repository, against the rendered Compose file |
| Docker applied memory and CPU limits inside the published bounds, and your answers record them | Automated, in this repository, against the running containers |
| Rolling forward returns only when the candidate is ready, the candidate answers, and the exception workflow completes | Automated, in this repository, by performing the rollout |
| Rolling back restores the known-good build and the workflow completes | Automated, in this repository, by performing the rollback |
| Your two probe-status values, five claim classifications, and one fidelity limitation from the supplied evidence pack | Protected automated check |
| Your release record and your reasoning | Your instructor, at the Instructor Review and the Project Defense |

## The three steps

### Step 1 — Pin the release

`infra/release/manifest.yaml` names two releases. `poe release-build` builds both for the API
and the worker from this repository's source, so `coldline-api:3.1.0` and `coldline-api:3.1.1`
exist locally with different build identities. In `compose.yaml`, give `api`, `worker`, and
`initializer` an `image:` name from the manifest, parameterized with `${COLDLINE_RELEASE_TAG:-<known-good tag>}`.
The initializer runs the API image. Record both tags in `submission.yaml`.

### Step 2 — Roll forward and back through a real gate

Run `poe roll-forward`. The candidate warms up slowly: its readiness endpoint answers 503 for
the seconds the manifest states. With the supplied health check, `up --wait` returns as soon
as the process is alive, and the first request sees that 503. Change the health check so it
probes `/health/ready` and tolerates the warm-up, then run the two commands again. Record the
`build_version` the first probe reported after each.

### Step 3 — Bound the resources

Add `deploy.resources.limits` for `api` and `worker` inside the ranges the manifest publishes.
Size them from the post-readiness samples in `docs/fidelity/local-runtime.md`. Run
`poe release-status` and record the applied limits exactly as Docker reports them.

### The supplied evidence

`docs/student/evidence-pack.json` holds two captured rollouts, one behind the supplied health
check and one behind a readiness gate, plus a rollback record and the applied limits from the
reference run. Read `docs/student/evidence-guide.md`, then fill in the two probe-status values,
five claim classifications, and one fidelity limitation from the pack alone. Your own run is
the material for the release record and the defense.

## Commands

```shell
poe release-build       # build both manifest releases for api and worker
poe roll-forward        # move api and worker to the candidate, print the record
poe roll-back           # move api and worker to the known-good release
poe release-status      # running images, answering build, applied limits
poe release-checks      # the five release checks, against the running stack
poe verify              # the full public path
```

## What the checks verify

| Check | What it looks at |
|---|---|
| `test_first_party_images_are_pinned_to_the_known_good_tag` | The rendered Compose file: `api`, `worker`, and `initializer` name a manifest image with the known-good tag as the default |
| `test_api_health_gate_probes_readiness_and_tolerates_the_warm_up` | The API health check command and its `start_period`, `interval`, and `retries` |
| `test_resource_bounds_are_declared_within_the_published_ranges` | `docker inspect` of the running api and worker, compared with the manifest bounds and your answers |
| `test_roll_forward_serves_only_after_the_candidate_is_ready` | Performs the rollout; the first probe must be 200 from the candidate build, and one exception must complete |
| `test_roll_back_restores_the_known_good_build` | Performs the rollback; the first probe must be 200 from the known-good build, and one exception must complete |

## Student-editable paths

- `compose.yaml`
- `submission.yaml`
- `docs/student/task-3-1-release-record.md`

Keep the service roster, published host ports, profiles, third-party image digests, the
shared environment anchor, and the worker's environment exactly as supplied. The manifest,
the release tool under `tests/release/`, the Dockerfiles, and the application source are
protected.
