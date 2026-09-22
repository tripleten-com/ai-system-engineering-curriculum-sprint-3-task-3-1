# Coldline Task 3.1 — Reproducible release

This checkpoint is the verified Sprint 2 platform with one addition: a release manifest that
names two supplied builds of the API and worker images, and the tooling to build them, roll the
stack between them, and report what is running. The Compose file still builds its first-party
images anonymously, its API health check asks only whether the process is alive, and no service
has a resource limit. Those three things are this Task's work.

[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/tripleten-com/ai-system-engineering-curriculum-sprint-3-task-3-1/tree/main)

## Start the system

Prerequisites are Python 3.12 and Docker with Compose v2. The supplied bootstrap supports macOS
arm64/x86-64, Windows x86-64, and Linux x86-64/aarch64, and installs pinned uv 0.11.8 under
`.tools/bin`. If your computer cannot run the stack locally, use the Codespaces button above.

On macOS and most Linux distributions the interpreter is `python3`; substitute it wherever these
commands say `python`.

```shell
python infra/scripts/bootstrap.py
./.tools/bin/uv sync --frozen
./.tools/bin/uv run --frozen poe preflight
./.tools/bin/uv run --frozen poe start
./.tools/bin/uv run --frozen poe ready
./.tools/bin/uv run --frozen poe ingest
./.tools/bin/uv run --frozen poe release-build
```

PowerShell and POSIX wrappers are available under `infra/scripts/`. After uv is on `PATH`, the
shorter `uv run --frozen poe <task>` form works.

| Service | Local URL | Purpose |
|---|---|---|
| API | `http://localhost:8000` | Submit exception workflows and retrieval queries; `/version` names the build that answers |
| Grafana | `http://localhost:3000` | Use the focused diagnostics dashboard |
| Prometheus | `http://localhost:9090` | Query bounded metrics |
| Jaeger | `http://localhost:16686` | Inspect local traces |
| LocalStack S3 | `http://localhost:4566` | Inspect the emulated object-storage endpoint |

Each of these ports can be overridden by setting the matching `COLDLINE_API_HOST_PORT`,
`COLDLINE_GRAFANA_HOST_PORT`, `COLDLINE_PROMETHEUS_HOST_PORT`, `COLDLINE_JAEGER_HOST_PORT`, or
`COLDLINE_LOCALSTACK_HOST_PORT` environment variable in your shell environment or a local `.env`
file (copy `.env.example`) if a default collides with something already running on your machine.
Keep the override in place for every `poe` command.

PostgreSQL, Redis, worker metrics, and OTLP remain inside the Compose network. Codespaces uses the
same `compose.yaml` and keeps every forwarded port private.

## Command path

For this Task, run the supplied commands in this order:

```text
poe start
poe ready
poe ingest
poe release-build
poe roll-forward
poe roll-back
poe release-status
poe verify
```

| Command | Use |
|---|---|
| `poe release-build` | Build both manifest releases (`3.1.0` and `3.1.1`) for the API and worker images from this source |
| `poe roll-forward` | Move `api` and `worker` to the candidate release with `--no-build --wait`, then print the transition record |
| `poe roll-back` | Move `api` and `worker` back to the known-good release the same way |
| `poe release-status` | Print the running images, the build that answers `/version`, and the limits Docker applied |
| `poe release-checks` | Run the five release checks against the running stack; they perform one rollout and one rollback |
| `poe ingest` | Run the supplied baseline corpus ingestion inside the API container |
| `poe student-tests` | Run your own tests under `tests/student/` |
| `poe unit` | Run fast isolated behavior tests |
| `poe contract` | Check interfaces, boundaries, submissions, and repository structure |
| `poe smoke` | Check the initialized running platform |
| `poe e2e` | Run the external API-to-worker workflow |
| `poe verify` | Run the public student verification path |
| `poe scenario` | Run the supplied exception-workflow walkthrough |
| `poe restart` | Restart the existing API and worker containers **without rebuilding** |
| `poe stop` | Remove containers and the network, keeping named volumes |
| `poe reset` | Remove containers, the network, and local named volumes |

`poe start` still rebuilds the first-party images from source with `--build`; it is the way to
bring the whole platform up. The two roll commands never build. They change one variable,
`COLDLINE_RELEASE_TAG`, and ask Compose to recreate `api` and `worker` from the image that tag
names, waiting on the health check before they return. If the Compose file gives those services no
`image:` name, both commands stop and say so.

For Task 3.1, `poe verify` rebuilds and starts the stack, ingests the supplied corpus, builds both
releases, runs the release checks, then the smoke tests, the end-to-end exception workflow, the
answer-sheet checks, and your own tests under `tests/student/`.

## The release manifest

`infra/release/manifest.yaml` is supplied and protected. It names the two images, the two
releases, and the resource bounds this Task accepts:

| Release | Tag | What is different |
|---|---|---|
| `known_good` | `3.1.0` | The build the stack starts on |
| `candidate` | `3.1.1` | Same source, and `/health/ready` answers 503 for 20 seconds after the process starts |

The candidate's slow warm-up is deliberate. It is the situation a health gate exists for: a
process that is alive, answering liveness, and not yet able to serve. `/version` reports the
build that answers, so a rollout and a rollback are observable from outside the container.

## Folder map

```text
repository root/
├── docs/                Student guidance, public contracts, and fidelity notes
│   ├── contracts/       Machine-readable public contracts
│   ├── fidelity/        Local-runtime boundary notes
│   ├── architecture/    Supplied vector engine technical profiles, in prose
│   ├── retrieval/       Supplied retrieval pipeline reference
│   └── student/         This Task's contract, evidence pack and guide, and your release record
├── config/              Retrieval configuration, settled and supplied from Sprint 2
├── infra/               Local setup and runtime configuration
│   ├── containers/      The API and worker Dockerfiles, with the build identity arguments
│   ├── release/         The supplied release manifest
│   ├── corpus/          Supplied synthetic corpus, query set, and designated investigation
│   ├── judge/           Supplied cached judge evidence and its provenance record
│   ├── profiles/        Supplied engine and emulator profiles, and their provenance record
│   └── postgres/        Database initialization and the migration baseline stamp
├── loadtest/            Supplied traffic profile and provider-latency harness
├── migrations/          Alembic environment, revision template, and revisions
├── src/
│   ├── api/             HTTP application code, the retrieval and document paths, composition
│   ├── worker/          Background application code
│   ├── domain/          Shared domain code, contracts, service and repository contracts
│   ├── ports/           Application interfaces
│   └── adapters/        Technology-specific implementations
└── tests/
    ├── unit/            Isolated behavior checks
    ├── release/         The supplied build, rollout, rollback, and status tool
    ├── benchmark/       Supplied evaluation harness, metrics, and adoption policy
    ├── contract/        Interface, release, retrieval, and repository checks
    ├── diagnostics/     Supplied stage inspector
    ├── doubles/         Supplied deterministic test doubles
    ├── student/         Your own tests
    ├── smoke/           Running-platform checks
    └── e2e/             Supplied workflow tools and checks
```

## Overview

Use the Task 3.1 lesson to decide what to do. This README covers local setup and repository
orientation.

1. `README.md` — local setup, commands, and permitted changes.
2. [`docs/student/task-3-1-contract.md`](docs/student/task-3-1-contract.md) — the three steps,
   what each check verifies, and the permitted paths.
3. `infra/release/manifest.yaml` — the two releases and the resource bounds.
4. `compose.yaml` — the file you change: image names, the API health check, resource limits.
5. [`docs/student/evidence-guide.md`](docs/student/evidence-guide.md) and
   `docs/student/evidence-pack.json` — the supplied rollout evidence for two probe-status
   values, five claim classifications, and one fidelity limitation.
6. `docs/student/task-3-1-release-record.md` — where your own rollout evidence goes.

The application source lives in five flat packages:

| Package | Responsibility |
|---|---|
| `api` | HTTP delivery, API use cases, the retrieval workflow, versioned routes, configuration, and composition |
| `worker` | Background processing, retries, configuration, and composition |
| `domain` | Provider-neutral contracts, state rules, identity, redaction, embedding, chunking, fusion, access constraints, service and repository contracts |
| `ports` | Exactly five visible application interfaces |
| `adapters` | PostgreSQL, pgvector retrieval, Redis Streams, S3-compatible object storage, deterministic model, logs, traces |

`src/api/bootstrap.py` and `src/worker/bootstrap.py` compose each process from its settings and
adapters. Process settings live in `src/api/config.py` and `src/worker/config.py`; the build
identity and the candidate warm-up are settings there, supplied by the image at build time.

## The five ports

Find the available interfaces in `src/ports/`. A port describes an application capability; an
adapter provides it using a concrete technology.

| Port | General responsibility |
|---|---|
| `ModelProvider` | Call an AI model service |
| `Retriever` | Look up relevant context or documents |
| `ObjectStore` | Store large binary objects or files |
| `JobQueue` | Publish and consume background work |
| `SecretProvider` | Read API keys and credentials |

Redis Streams still carries `JobQueue` in this Task. Task 3.3 introduces the supplied LocalStack
SQS and dead-letter binding.

## Test levels

| Level | Requires Compose | Main question |
|---|---:|---|
| Unit | No | Does one responsibility behave correctly, including failures? |
| Contract | Some | Do interfaces, schemas, paths, and dependency rules stay compatible? |
| Smoke | Yes | Did the complete local platform initialize and become observable? |
| E2E | Yes | Can an external client complete the supplied workflow? |

Contract checks marked `runtime` need the running stack. `poe contract` skips them; `poe verify`
and `poe runtime-contract` run them. The release checks are `runtime` and `assessed`.

## Submission checks

Run `poe verify` locally before opening your student pull request. Public GitHub CI repeats
the student checks. The course platform (CMS) runs the required protected grading separately
and associates its results with your submission commit. A green template-export check, or a
skipped student check on an `export/` branch, is not a passing grade. You do not configure
GitHub grading secrets. Follow the Task lesson's instructor-review and progression policy.

## Task boundary

Task 3.1 asks you to pin the two supplied releases to immutable image tags, make the API health
check a readiness gate that tolerates the candidate warm-up, roll forward and back through it,
bound the API and worker resources, and classify the supplied rollout evidence.

These paths are student-editable:

- `compose.yaml`
- `submission.yaml`
- `docs/student/task-3-1-release-record.md`

Keep the service roster, published host ports, profiles, third-party image digests, the shared
environment anchor, and the worker's environment as supplied; the public checks compare them.
Everything else in this repository is supplied, including the manifest, the release tool, the
Dockerfiles, and the application source.

### Student walkthrough

See **Task 1: Reproducible release** in your course platform for the full walkthrough. In outline:
build both releases, name the three first-party images from the manifest, roll forward and watch
the first probe fail behind the supplied health check, repair the gate, roll forward and back
again, add resource limits inside the published bounds, record what you observed, fill in the
two probe-status values, five claim classifications, and one fidelity limitation from the pack,
run `poe verify`, and open your pull request.

## Operational limits

This local system does not authenticate users, terminate TLS, or manage production secrets.
The Compose PostgreSQL password and the LocalStack access keys are local-only non-secret
credentials. Never place real credentials, personal data, or production records in this
repository.

A rollout here recreates one container on one host. Compose stops the running `api` container
before it starts the new one, so the health gate proves that no request is served by a build that
is not ready; it does not prove that no request went unanswered while the container was
recreated. Managed platforms roll a second replica in before the first one leaves. The tag names
a local build, not a registry digest another host could pull. Neither difference is a defect of
this Task, and both belong in your release record.

Named volumes preserve local PostgreSQL, Redis, Prometheus, Grafana, and Jaeger state across
`poe stop`. LocalStack object contents are deliberately not persisted; the initializer re-uploads
the supplied corpus artifacts on every start. The `poe reset` command deletes the named volumes.
This topology makes no backup, replication, high-availability, disaster-recovery, capacity,
latency-SLO, or availability claim.

See [JobQueue fidelity](docs/fidelity/JobQueue.md),
[ModelProvider fidelity](docs/fidelity/ModelProvider.md),
[ObjectStore fidelity](docs/fidelity/ObjectStore.md), and
[Retriever fidelity](docs/fidelity/Retriever.md) for the active adapter boundaries. The
[local runtime evidence](docs/fidelity/local-runtime.md) records the current measurement and its
qualification limits.
