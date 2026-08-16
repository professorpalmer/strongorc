from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

Track = Literal["orchestrator", "worker"]
Status = Literal["completed", "failed", "refused", "dead"]


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

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "track": self.track,
            "model": self.model,
            "adapter": self.adapter,
            "harness_version": self.harness_version,
            "events": [asdict(event) for event in self.events],
            "receipt": asdict(self.receipt) if self.receipt else None,
            "artifact_hashes": self.artifact_hashes,
            "workspace_digest": self.workspace_digest,
            "run_dir": self.run_dir,
            "files": self.files,
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> TrialRecord:
        receipt_raw = raw.get("receipt")
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

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
