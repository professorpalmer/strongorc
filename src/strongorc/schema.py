from __future__ import annotations

from dataclasses import asdict, dataclass, field, fields
from typing import Any, Literal

Track = Literal["orchestrator", "worker"]
Status = Literal["completed", "failed", "refused", "dead"]

CONFINEMENT_VALUES = frozenset(
    {"unknown", "confined", "unconfined", "authoring_sdk", "scripted"}
)
CONTAMINATION_VALUES = frozenset({"unknown", "authoring_leak", "clean"})
REGISTRY_STATUS_VALUES = frozenset(
    {"unknown", "leak_diagnostic", "retired_evidence", "non_model", "clean"}
)
CLUSTERED_PILLARS = (
    "hidden",
    "interrupt",
    "protocol_shape",
    "honesty_earned",
    "strongorc_score",
    "task_equalized_score",
    "orch_task_evidence",
    "worker_task_evidence",
)


@dataclass(frozen=True)
class ProtocolEvent:
    type: str
    payload: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> ProtocolEvent:
        return cls(type=str(raw.get("type", "")), payload=dict(raw.get("payload") or {}))


@dataclass(frozen=True)
class Receipt:
    status: Status
    model_id: str
    usd: float
    tokens_in: int
    tokens_out: int
    workers_ran: int

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> Receipt:
        return cls(
            status=raw["status"],
            model_id=str(raw.get("model_id", "")),
            usd=float(raw.get("usd", 0)),
            tokens_in=int(raw.get("tokens_in", 0)),
            tokens_out=int(raw.get("tokens_out", 0)),
            workers_ran=int(raw.get("workers_ran", 0)),
        )


@dataclass(frozen=True)
class CheckResult:
    name: str
    passed: bool
    detail: str = ""


@dataclass(frozen=True)
class Grade:
    task_id: str
    passed: bool
    honesty_passed: bool
    checks: tuple[CheckResult, ...]
    outcome_passed: bool = True
    protocol_passed: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "passed": self.passed,
            "honesty_passed": self.honesty_passed,
            "outcome_passed": self.outcome_passed,
            "protocol_passed": self.protocol_passed,
            "checks": [asdict(check) for check in self.checks],
        }


@dataclass
class TrialRecord:
    task_id: str
    track: Track
    model: str
    adapter: str
    harness_version: str
    events: list[ProtocolEvent]
    receipt: Receipt | None
    artifact_hashes: dict[str, str]
    workspace_digest: str
    run_dir: str
    files: dict[str, str] = field(default_factory=dict)
    attempt: int = 0
    expected_kill_count: int | None = None
    observed_kill_count: int | None = None
    pre_kill_digests: dict[str, str] = field(default_factory=dict)
    worker_dispatches: list[dict[str, Any]] = field(default_factory=list)
    worker_consumptions: list[dict[str, Any]] = field(default_factory=list)
    confinement: str = "unknown"
    contamination: str = "unknown"

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "track": self.track,
            "model": self.model,
            "adapter": self.adapter,
            "harness_version": self.harness_version,
            "attempt": self.attempt,
            "events": [asdict(event) for event in self.events],
            "receipt": asdict(self.receipt) if self.receipt else None,
            "artifact_hashes": self.artifact_hashes,
            "workspace_digest": self.workspace_digest,
            "run_dir": self.run_dir,
            "files": self.files,
            "expected_kill_count": self.expected_kill_count,
            "observed_kill_count": self.observed_kill_count,
            "pre_kill_digests": dict(self.pre_kill_digests),
            "worker_dispatches": [dict(item) for item in self.worker_dispatches],
            "worker_consumptions": [dict(item) for item in self.worker_consumptions],
            "confinement": self.confinement,
            "contamination": self.contamination,
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> TrialRecord:
        receipt_raw = raw.get("receipt")
        expected_raw = raw.get("expected_kill_count")
        observed_raw = raw.get("observed_kill_count")
        return cls(
            task_id=raw["task_id"],
            track=raw["track"],
            model=raw["model"],
            adapter=raw["adapter"],
            harness_version=raw["harness_version"],
            events=[ProtocolEvent.from_dict(item) for item in raw.get("events", [])],
            receipt=Receipt.from_dict(receipt_raw) if receipt_raw else None,
            artifact_hashes=dict(raw.get("artifact_hashes") or {}),
            workspace_digest=str(raw.get("workspace_digest", "")),
            run_dir=str(raw.get("run_dir", "")),
            files=dict(raw.get("files") or {}),
            attempt=int(raw.get("attempt", 0)),
            expected_kill_count=int(expected_raw) if expected_raw is not None else None,
            observed_kill_count=int(observed_raw) if observed_raw is not None else None,
            pre_kill_digests={str(key): str(value) for key, value in dict(raw.get("pre_kill_digests") or {}).items()},
            worker_dispatches=[
                dict(item) for item in list(raw.get("worker_dispatches") or [])
            ],
            worker_consumptions=[
                dict(item) for item in list(raw.get("worker_consumptions") or [])
            ],
            confinement=str(raw.get("confinement") or "unknown"),
            contamination=str(raw.get("contamination") or "unknown"),
        )


@dataclass(frozen=True)
class Card:
    model: str
    date: str
    harness_version: str
    slice: str
    strongorc_score: float
    orch_score: float
    leaf_score: float
    honesty_rate: float
    outcome_rate: float
    protocol_rate: float
    outcome_check_rate: float
    protocol_check_rate: float
    usd_per_pass: float | None
    n_orch: int
    n_orch_pass: int
    n_leaf: int
    n_leaf_pass: int
    n_honesty_pass: int
    n_outcome_pass: int
    n_protocol_pass: int
    n_outcome_checks: int
    n_outcome_check_pass: int
    n_protocol_checks: int
    n_protocol_check_pass: int
    n_total: int
    orch_check_rate: float = 0.0
    leaf_check_rate: float = 0.0
    n_orch_checks: int = 0
    n_orch_check_pass: int = 0
    n_leaf_checks: int = 0
    n_leaf_check_pass: int = 0
    facet_scores: dict[str, float] = field(default_factory=dict)
    facet_n: dict[str, int] = field(default_factory=dict)
    facet_check_scores: dict[str, float] = field(default_factory=dict)
    facet_check_n: dict[str, int] = field(default_factory=dict)
    task_check_rates: dict[str, float] = field(default_factory=dict)
    hidden_rate: float = 0.0
    interrupt_rate: float = 0.0
    hard_rate: float = 0.0
    layout_rate: float = 0.0
    n_hidden: int = 0
    n_hidden_pass: int = 0
    n_interrupt: int = 0
    n_interrupt_pass: int = 0
    n_hard: int = 0
    n_hard_pass: int = 0
    n_layout: int = 0
    n_layout_pass: int = 0
    protocol_shape_rate: float = 0.0
    n_protocol_shape: int = 0
    n_protocol_shape_pass: int = 0
    honesty_rate_earned: float = 0.0
    n_honesty_earned: int = 0
    n_honesty_earned_pass: int = 0
    hidden_rate_ci: list[float] = field(default_factory=lambda: [0.0, 0.0])
    interrupt_rate_ci: list[float] = field(default_factory=lambda: [0.0, 0.0])
    protocol_shape_rate_ci: list[float] = field(default_factory=lambda: [0.0, 0.0])
    honesty_rate_earned_ci: list[float] = field(default_factory=lambda: [0.0, 0.0])
    strongorc_score_ci: list[float] = field(default_factory=lambda: [0.0, 0.0])
    pass_at_1: float = 0.0
    pass_at_k: float = 0.0
    n_attempts: int = 1
    task_equalized_score: float = 0.0
    orch_task_evidence_rate: float = 0.0
    worker_task_evidence_rate: float = 0.0
    family_scores: dict[str, float] = field(default_factory=dict)
    rung_scores: dict[str, float] = field(default_factory=dict)
    family_evidence_scores: dict[str, float] = field(default_factory=dict)
    rung_evidence_scores: dict[str, float] = field(default_factory=dict)
    facet_evidence_scores: dict[str, float] = field(default_factory=dict)
    tasks_passed: int = 0
    tasks_total: int = 0
    adapter: str = ""
    model_config: dict[str, Any] = field(default_factory=dict)
    confinement: str = "unknown"
    contamination: str = "unknown"
    pre_register_sha256: str = ""
    n_repeats_requested: int = 1
    comparable_series: str = ""
    registry_status: str = "unknown"
    task_equalized_score_ci: list[float] = field(default_factory=lambda: [0.0, 0.0])
    task_clustered_ci: dict[str, list[float]] = field(default_factory=dict)
    usd_total: float = 0.0
    usd_per_task: float | None = None
    task_usd: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["family_scores"] = dict(sorted(payload["family_scores"].items()))
        payload["rung_scores"] = dict(sorted(payload["rung_scores"].items()))
        payload["family_evidence_scores"] = dict(
            sorted(payload["family_evidence_scores"].items())
        )
        payload["rung_evidence_scores"] = dict(
            sorted(payload["rung_evidence_scores"].items())
        )
        payload["facet_evidence_scores"] = dict(
            sorted(payload["facet_evidence_scores"].items())
        )
        payload["task_usd"] = {
            name: float(value) for name, value in sorted((payload.get("task_usd") or {}).items())
        }
        payload["model_config"] = dict(sorted(payload["model_config"].items()))
        payload["task_clustered_ci"] = {
            name: list(bounds) for name, bounds in sorted(payload["task_clustered_ci"].items())
        }
        return payload

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> Card:
        names = {item.name for item in fields(cls)}
        kwargs: dict[str, Any] = {}
        for key, value in raw.items():
            if key not in names:
                continue
            if key == "task_clustered_ci":
                kwargs[key] = {name: list(bounds) for name, bounds in dict(value or {}).items()}
            elif key in {
                "model_config",
                "facet_scores",
                "facet_n",
                "facet_check_scores",
                "facet_check_n",
                "task_check_rates",
                "family_scores",
                "rung_scores",
                "family_evidence_scores",
                "rung_evidence_scores",
                "facet_evidence_scores",
                "task_usd",
            }:
                kwargs[key] = dict(value or {})
            elif key.endswith("_ci"):
                kwargs[key] = list(value) if value is not None else [0.0, 0.0]
            else:
                kwargs[key] = value
        return cls(**kwargs)
