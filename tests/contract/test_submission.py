"""Coldline.

===================

File:              tests/contract/test_submission.py
Component:         Contract tests — Test Submission
Purpose:           Tests for the public answer and path checks for this Task's submission.
Interacts With:    Published interfaces and repository boundaries
Sprint/Task:       Sprint 3 — Project 3
Concepts:          Compatibility, ownership, export safety
Tools:             Python 3.12, pytest
"""

from pathlib import Path
from typing import Any

import pytest
import yaml

from tests.contract.submission_validation import (
    SubmissionError,
    _load_one_document,
    main,
    validate_changed_paths,
    validate_submission,
)

ROOT = Path(__file__).parents[2]
SCHEMA = ROOT / "docs/contracts/submission.schema.json"


def valid_answers(**overrides: Any) -> dict[str, object]:
    """Return a complete answer sheet in the published shape."""
    answers: dict[str, Any] = {
        "known_good_tag": "3.1.0",
        "candidate_tag": "3.1.1",
        "observed_candidate_version": "3.1.1",
        "observed_rollback_version": "3.1.0",
        "api_memory_limit_mib": 512,
        "api_cpu_limit": 1.0,
        "worker_memory_limit_mib": 256,
        "worker_cpu_limit": 0.5,
        "weak_gate_first_probe_status": 503,
        "ready_gate_first_probe_status": 200,
        "claim_classifications": {
            "C01": "observation",
            "C02": "not-established",
            "C03": "observation",
            "C04": "inference",
            "C05": "not-established",
        },
        "fidelity_limitation": "single_replica_recreate",
    }
    answers.update(overrides)
    return {"answers": answers}


def _task_root(tmp_path: Path, submission_text: str) -> Path:
    """Stage a minimal Task root the public verifier can validate."""
    (tmp_path / "docs/contracts").mkdir(parents=True)
    (tmp_path / "submission.yaml").write_text(submission_text, encoding="utf-8")
    (tmp_path / "submission-sample.yaml").write_text(
        (ROOT / "submission-sample.yaml").read_text(encoding="utf-8"), encoding="utf-8"
    )
    (tmp_path / "docs/contracts/submission.schema.json").write_text(
        SCHEMA.read_text(encoding="utf-8"), encoding="utf-8"
    )
    return tmp_path


def test_a_complete_sheet_is_well_formed(tmp_path: Path) -> None:
    """The public schema accepts a complete sheet without judging its correctness."""
    root = _task_root(tmp_path, yaml.safe_dump(valid_answers()))

    validate_submission(root / "submission.yaml", SCHEMA)


def test_blank_template_fails_with_field_address(tmp_path: Path) -> None:
    """An untouched answer sheet must identify the first incomplete field."""
    root = _task_root(
        tmp_path, (ROOT / "tests/fixtures/submission-template.yaml").read_text(encoding="utf-8")
    )

    with pytest.raises(SubmissionError, match="answers.known_good_tag"):
        validate_submission(root / "submission.yaml", SCHEMA)


@pytest.mark.parametrize(
    "overrides,message",
    [
        ({"known_good_tag": "latest"}, "known_good_tag"),
        ({"api_memory_limit_mib": 0}, "api_memory_limit_mib"),
        ({"api_cpu_limit": 0}, "api_cpu_limit"),
        ({"weak_gate_first_probe_status": 404}, "weak_gate_first_probe_status"),
        ({"claim_classifications": {"C01": "observation"}}, "claim_classifications"),
        ({"fidelity_limitation": "it was slow"}, "fidelity_limitation"),
    ],
    ids=["mutable-tag", "zero-memory", "zero-cpu", "unlisted-status", "missing-claims", "prose"],
)
def test_values_outside_the_published_contract_are_rejected(
    tmp_path: Path, overrides: dict[str, Any], message: str
) -> None:
    """The public schema must name the field it rejected, and reject the right ones."""
    root = _task_root(tmp_path, yaml.safe_dump(valid_answers(**overrides)))

    with pytest.raises(SubmissionError, match=message):
        validate_submission(root / "submission.yaml", SCHEMA)


def test_a_blank_claim_classification_is_rejected(tmp_path: Path) -> None:
    """A nested placeholder cannot hide behind the top-level placeholder check."""
    claims = dict(valid_answers()["answers"]["claim_classifications"])  # type: ignore[index]
    claims["C03"] = ""
    root = _task_root(tmp_path, yaml.safe_dump(valid_answers(claim_classifications=claims)))

    with pytest.raises(SubmissionError, match="C03"):
        validate_submission(root / "submission.yaml", SCHEMA)


@pytest.mark.parametrize(
    "field",
    ["rollout_passed", "instructor_approved", "defense_recording_url", "notes"],
)
def test_no_self_attestation_or_recording_field_is_accepted(tmp_path: Path, field: str) -> None:
    """Reject a self-approval, a pass boolean, or a recording URL."""
    answers = valid_answers()
    mapping = answers["answers"]
    assert isinstance(mapping, dict)
    mapping[field] = True
    root = _task_root(tmp_path, yaml.safe_dump(answers))

    with pytest.raises(SubmissionError, match="Additional properties"):
        validate_submission(root / "submission.yaml", SCHEMA)


def test_exact_sample_copy_is_rejected(tmp_path: Path) -> None:
    """The published sample must not be accepted as a student submission."""
    root = _task_root(tmp_path, (ROOT / "submission-sample.yaml").read_text(encoding="utf-8"))

    with pytest.raises(SubmissionError, match="fictional sample"):
        validate_submission(
            root / "submission.yaml",
            SCHEMA,
            sample_path=root / "submission-sample.yaml",
        )


def test_only_the_three_permitted_paths_may_change() -> None:
    """The Compose file, the answer sheet, and the release record; nothing else."""
    validate_changed_paths(
        ["compose.yaml", "submission.yaml", "docs/student/task-3-1-release-record.md"]
    )

    for protected in (
        "infra/release/manifest.yaml",
        "tests/release/rollout.py",
        "tests/contract/test_release.py",
        "infra/containers/api.Dockerfile",
        "src/api/routes.py",
        "pyproject.toml",
        "README.md",
    ):
        with pytest.raises(SubmissionError, match="protected path changed"):
            validate_changed_paths([protected])


def test_public_entrypoint_reports_an_incomplete_answer_sheet(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Catch a verifier entrypoint that skips the real submission contract."""
    root = _task_root(
        tmp_path, (ROOT / "tests/fixtures/submission-template.yaml").read_text(encoding="utf-8")
    )
    (root / "docs/student").mkdir(parents=True)
    (root / "docs/student/task-3-1-release-record.md").write_text(
        (ROOT / "docs/student/task-3-1-release-record.md").read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    assert main(root, changed_paths=[]) == 1
    assert "answers.known_good_tag is incomplete" in capsys.readouterr().err


def test_public_entrypoint_rejects_an_untouched_release_record(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A complete answer sheet with the template record still in place is incomplete."""
    root = _task_root(tmp_path, yaml.safe_dump(valid_answers()))
    (root / "docs/student").mkdir(parents=True)
    (root / "docs/student/task-3-1-release-record.md").write_text(
        (ROOT / "docs/student/task-3-1-release-record.md").read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    assert main(root, changed_paths=[]) == 1
    assert "template markers" in capsys.readouterr().err


@pytest.mark.parametrize(
    "unsafe_text",
    [
        "answers: {value: first, value: second}\n",
        "answers: &answer {value: fictional}\n",
        "answers: *missing\n",
        "answers: {<<: {value: fictional}}\n",
        "answers: {value: 2026-09-04}\n",
        "answers: {value: !custom fictional}\n",
        "answers: {1: fictional}\n",
    ],
    ids=["duplicate-key", "anchor", "alias", "merge-key", "date", "custom-tag", "non-string-key"],
)
def test_non_json_yaml_constructs_are_rejected(tmp_path: Path, unsafe_text: str) -> None:
    """Reject restricted syntax before schema validation can mask a parser defect."""
    submission = tmp_path / "submission.yaml"
    submission.write_text(unsafe_text, encoding="utf-8")

    with pytest.raises(SubmissionError, match="restricted YAML"):
        _load_one_document(submission)


def test_multiple_yaml_documents_are_rejected(tmp_path: Path) -> None:
    """A second document cannot supply or replace the answer mapping."""
    submission = tmp_path / "submission.yaml"
    submission.write_text("answers: {}\n---\nanswers: {}\n", encoding="utf-8")

    with pytest.raises(SubmissionError, match="exactly one YAML mapping"):
        _load_one_document(submission)
