import importlib.util
import json
from pathlib import Path

import pytest

from strongorc.catalog import TaskSpec
from strongorc.worker_broker import WorkerBroker

EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "openrouter_agent.py"


def _load():
    spec = importlib.util.spec_from_file_location("openrouter_agent", EXAMPLE)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_chat_allows_parallel_tool_calls() -> None:
    text = EXAMPLE.read_text(encoding="utf-8")
    assert '"parallel_tool_calls": True' in text
    assert "429" in text
    assert "402" in text
    assert '"usage": {"include": True}' in text or '"usage": {"include": true}' in text


@pytest.mark.parametrize(
    ("status", "reason"),
    [
        (401, "provider_authentication"),
        (402, "provider_payment_required"),
        (429, "provider_rate_limit"),
    ],
)
def test_terminal_failure_reason_classifies_provider_http_errors(
    status: int, reason: str
) -> None:
    module = _load()
    error = RuntimeError(f"openrouter HTTP {status}: provider detail")
    assert module.terminal_failure_reason(error) == reason


def test_run_loop_does_not_treat_midtask_empty_stop_as_terminal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = _load()
    monkeypatch.setenv("STRONGORC_TRACK", "worker")
    responses = iter(
        [
            {
                "usage": {"prompt_tokens": 10, "completion_tokens": 1, "cost": 0.01},
                "choices": [
                    {
                        "message": {
                            "tool_calls": [
                                {
                                    "id": "read-1",
                                    "function": {
                                        "name": "read_file",
                                        "arguments": '{"path":"missing.txt"}',
                                    },
                                }
                            ]
                        }
                    }
                ],
            },
            {
                "usage": {"prompt_tokens": 10, "completion_tokens": 1, "cost": 0.01},
                "choices": [{"message": {"content": ""}}],
            },
            {
                "usage": {"prompt_tokens": 10, "completion_tokens": 1, "cost": 0.01},
                "choices": [
                    {
                        "message": {
                            "tool_calls": [
                                {
                                    "id": "receipt-1",
                                    "function": {
                                        "name": "write_receipt",
                                        "arguments": (
                                            '{"status":"completed","workers_ran":0,'
                                            '"usd":0,"tokens_in":0,"tokens_out":0}'
                                        ),
                                    },
                                }
                            ]
                        }
                    }
                ],
            },
            {
                "usage": {"prompt_tokens": 10, "completion_tokens": 1, "cost": 0.01},
                "choices": [{"message": {"content": "done"}}],
            },
        ]
    )
    monkeypatch.setattr(module, "chat", lambda *args, **kwargs: next(responses))
    workspace = module.Workspace(tmp_path, "anthropic/claude-fable-5")
    module.run_loop(workspace, "secret", "anthropic/claude-fable-5")
    assert workspace.receipt_written is True


def test_run_loop_stops_on_provider_content_filter(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = _load()
    monkeypatch.setenv("STRONGORC_TRACK", "worker")
    calls = 0

    def refused_chat(*args, **kwargs):
        nonlocal calls
        calls += 1
        return {
            "provider": "Anthropic",
            "usage": {"prompt_tokens": 10, "completion_tokens": 0, "cost": 0.01},
            "choices": [
                {
                    "finish_reason": "content_filter",
                    "native_finish_reason": "refusal",
                    "message": {"content": ""},
                }
            ],
        }

    monkeypatch.setattr(module, "chat", refused_chat)
    workspace = module.Workspace(tmp_path, "anthropic/claude-fable-5")
    module.run_loop(workspace, "secret", "anthropic/claude-fable-5")

    assert calls == 2
    events = (tmp_path / "protocol.jsonl").read_text(encoding="utf-8")
    assert "provider_refusal" in events


def test_write_receipt_uses_workspace_totals_not_model_args(tmp_path: Path) -> None:
    module = _load()
    workspace = module.Workspace(tmp_path, "anthropic/claude-fable-5")
    workspace.tokens_in = 100_000
    workspace.tokens_out = 2_000
    workspace.usd = 3.10
    workspace.cost_source = "openrouter_usage"
    result = workspace.dispatch(
        "write_receipt",
        {
            "status": "completed",
            "usd": 0.40,
            "tokens_in": 12,
            "tokens_out": 3,
            "workers_ran": 2,
        },
    )
    assert "status=completed" in result
    receipt = json.loads((tmp_path / "receipts" / "job.json").read_text(encoding="utf-8"))
    assert receipt["usd"] == pytest.approx(3.10)
    assert receipt["tokens_in"] == 100_000
    assert receipt["tokens_out"] == 2_000
    assert receipt["workers_ran"] == 2
    assert receipt["cost_source"] == "openrouter_usage"
    assert receipt["model_id"] == "anthropic/claude-fable-5"


def test_workspace_dispatches_and_consumes_harness_worker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = _load()
    task_root = tmp_path / "task"
    task_root.mkdir()
    (task_root / "workers.py").write_text(
        """
def dispatch(worker_id, assignment, run_dir, nonce):
    return {"worker_id": worker_id, "answer": assignment["question"] + "-done"}
""".lstrip(),
        encoding="utf-8",
    )
    task = TaskSpec(
        id="worker-tool",
        track="orchestrator",
        slice="reason",
        title="worker tool",
        timeout_seconds=30,
        root=task_root,
    )
    run_dir = tmp_path / "run"
    (run_dir / ".harness").mkdir(parents=True)
    (run_dir / ".harness" / "nonce").write_text("nonce\n", encoding="utf-8")
    workspace = module.Workspace(run_dir, "model")

    with WorkerBroker(task, run_dir) as broker:
        for key, value in broker.environment.items():
            monkeypatch.setenv(key, value)
        dispatched = json.loads(
            workspace.dispatch(
                "dispatch_worker",
                {"worker_id": "analyst", "assignment": {"question": "case"}},
            )
        )
        report = json.loads(
            workspace.dispatch(
                "consume_worker_report",
                {"dispatch_id": dispatched["dispatch_id"]},
            )
        )
        sealed = broker.snapshot()

    assert report["answer"] == "case-done"
    assert len(sealed["dispatches"]) == 1
    assert len(sealed["consumptions"]) == 1
    events = [
        json.loads(line)
        for line in (run_dir / "protocol.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert [event["type"] for event in events] == [
        "worker_started",
        "worker_finished",
        "artifact_consumed",
    ]


def test_workspace_resumes_usage_from_disk(tmp_path: Path) -> None:
    module = _load()
    first = module.Workspace(tmp_path, "m")
    first.usd = 1.25
    first.tokens_in = 8_000
    first.tokens_out = 200
    first.cost_source = "openrouter_usage"
    module.write_usage(tmp_path, first.tokens_in, first.tokens_out, first.usd, first.cost_source)
    resumed = module.Workspace(tmp_path, "m")
    assert resumed.usd == pytest.approx(1.25)
    assert resumed.tokens_in == 8_000
    assert resumed.tokens_out == 200
    assert resumed.cost_source == "openrouter_usage"
    assert resumed.billed_usd() == pytest.approx(1.25)


def test_finalize_refreshes_receipt_after_later_turns(tmp_path: Path) -> None:
    module = _load()
    workspace = module.Workspace(tmp_path, "m")
    module.add_usage(workspace, {"prompt_tokens": 100, "completion_tokens": 10, "cost": 0.40})
    workspace.dispatch(
        "write_receipt",
        {
            "status": "completed",
            "usd": 0.01,
            "tokens_in": 1,
            "tokens_out": 1,
            "workers_ran": 1,
        },
    )
    module.add_usage(workspace, {"prompt_tokens": 50, "completion_tokens": 20, "cost": 0.07})
    module.finalize_if_needed(workspace, "failed")
    receipt = json.loads((tmp_path / "receipts" / "job.json").read_text(encoding="utf-8"))
    assert receipt["status"] == "completed"
    assert receipt["usd"] == pytest.approx(0.47)
    assert receipt["tokens_in"] == 150
    assert receipt["tokens_out"] == 30
    assert receipt["workers_ran"] == 1


def test_add_usage_appends_generation_ledger(tmp_path: Path) -> None:
    module = _load()
    workspace = module.Workspace(tmp_path, "m")
    module.add_usage(
        workspace,
        {"prompt_tokens": 100, "completion_tokens": 20, "cost": 0.04},
    )
    module.add_usage(
        workspace,
        {"prompt_tokens": 200, "completion_tokens": 10, "cost": 0.06},
    )
    assert workspace.usd == pytest.approx(0.10)
    ledger = (tmp_path / ".harness" / "openrouter_generations.jsonl").read_text(encoding="utf-8")
    lines = [json.loads(line) for line in ledger.splitlines() if line.strip()]
    assert len(lines) == 2
    assert lines[0]["cost"] == pytest.approx(0.04)
    assert lines[1]["cost"] == pytest.approx(0.06)
    assert workspace.billed_usd() == pytest.approx(0.10)


def test_workspace_enforces_explicit_usd_budget(tmp_path: Path, monkeypatch) -> None:
    module = _load()
    monkeypatch.setenv("STRONGORC_MAX_USD", "0.05")
    workspace = module.Workspace(tmp_path, "m")
    assert workspace.budget_exhausted() is False
    measured = module.add_usage(
        workspace,
        {"prompt_tokens": 100, "completion_tokens": 20, "cost": 0.06},
    )
    assert measured is True
    assert workspace.budget_exhausted() is True


def test_budgeted_usage_fails_closed_without_provider_cost(tmp_path: Path, monkeypatch) -> None:
    module = _load()
    monkeypatch.setenv("STRONGORC_MAX_USD", "1.0")
    workspace = module.Workspace(tmp_path, "m")
    measured = module.add_usage(
        workspace,
        {"prompt_tokens": 100, "completion_tokens": 20},
    )
    assert measured is False


def test_budget_accepts_live_list_estimate_when_provider_cost_is_delayed(
    tmp_path: Path, monkeypatch
) -> None:
    module = _load()
    monkeypatch.setenv("STRONGORC_MAX_USD", "1.0")
    workspace = module.Workspace(tmp_path, "m")
    measured = module.add_usage(
        workspace,
        {
            "prompt_tokens": 100,
            "completion_tokens": 20,
            "estimated_cost": 0.06,
        },
    )
    assert measured is True
    assert workspace.billed_usd() == pytest.approx(0.06)
    assert workspace.cost_source == "openrouter_list"


def test_response_usage_recovers_cost_from_generation_id(monkeypatch) -> None:
    module = _load()
    recovered = {
        "prompt_tokens": 120,
        "completion_tokens": 30,
        "cost": 0.42,
    }
    calls: list[tuple[str, str]] = []

    def fetch(api_key: str, generation_id: str) -> dict:
        calls.append((api_key, generation_id))
        return recovered

    monkeypatch.setattr(module, "fetch_generation_usage", fetch)
    usage = module.response_usage(
        "secret",
        "anthropic/claude-fable-5",
        {
            "id": "gen-123",
            "usage": {"prompt_tokens": 120, "completion_tokens": 30},
        },
    )
    assert usage == recovered
    assert calls == [("secret", "gen-123")]


def test_fetch_generation_usage_reads_authoritative_total_cost(monkeypatch) -> None:
    module = _load()

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

        def read(self) -> bytes:
            return json.dumps(
                {
                    "data": {
                        "tokens_prompt": 120,
                        "tokens_completion": 30,
                        "total_cost": 0.42,
                    }
                }
            ).encode("utf-8")

    def open_response(request, timeout):
        return Response()

    monkeypatch.setattr(module.urllib.request, "urlopen", open_response)
    assert module.fetch_generation_usage("secret", "gen-123") == {
        "prompt_tokens": 120,
        "completion_tokens": 30,
        "cost": 0.42,
    }


def test_response_usage_does_not_refetch_inline_cost(monkeypatch) -> None:
    module = _load()

    def unexpected_fetch(api_key: str, generation_id: str) -> dict:
        raise AssertionError("inline provider cost should be authoritative")

    monkeypatch.setattr(module, "fetch_generation_usage", unexpected_fetch)
    usage = module.response_usage(
        "secret",
        "anthropic/claude-fable-5",
        {
            "id": "gen-123",
            "usage": {
                "prompt_tokens": 120,
                "completion_tokens": 30,
                "cost": 0.42,
            },
        },
    )
    assert usage is not None
    assert module.provider_cost(usage) == pytest.approx(0.42)


def test_response_usage_estimates_from_live_model_rates(monkeypatch) -> None:
    module = _load()
    monkeypatch.setattr(module, "fetch_generation_usage", lambda api_key, generation_id: None)
    monkeypatch.setattr(
        module,
        "fetch_model_rates",
        lambda api_key, model: (10 / 1_000_000, 50 / 1_000_000),
    )
    usage = module.response_usage(
        "secret",
        "anthropic/claude-fable-5",
        {
            "id": "gen-123",
            "usage": {"prompt_tokens": 2_000, "completion_tokens": 100},
        },
    )
    assert usage is not None
    assert usage["estimated_cost"] == pytest.approx(0.025)


def test_response_usage_estimates_missing_token_metadata_from_payload(monkeypatch) -> None:
    module = _load()
    monkeypatch.setattr(module, "fetch_generation_usage", lambda api_key, generation_id: None)
    monkeypatch.setattr(
        module,
        "fetch_model_rates",
        lambda api_key, model: (10 / 1_000_000, 50 / 1_000_000),
    )
    messages = [{"role": "user", "content": "x" * 300}]
    usage = module.response_usage(
        "secret",
        "anthropic/claude-fable-5",
        {"id": "gen-123"},
        messages,
    )
    assert usage is not None
    assert usage["prompt_tokens"] >= 100
    assert usage["completion_tokens"] == 1
    assert 0 < usage["estimated_cost"] < 0.01
    assert usage["cost_source"] == "openrouter_list_estimate"


def test_agent_refuses_unbudgeted_paid_run_before_loading_key(monkeypatch) -> None:
    module = _load()
    monkeypatch.delenv("STRONGORC_MAX_USD", raising=False)
    monkeypatch.delenv("DURABLE_ORCH_MAX_USD", raising=False)

    def fail_if_key_is_loaded() -> str:
        raise AssertionError("key should not be loaded")

    monkeypatch.setattr(module, "load_openrouter_key", fail_if_key_is_loaded)
    with pytest.raises(SystemExit, match="STRONGORC_MAX_USD"):
        module.main([])


def test_confined_rejects_parent_escape(tmp_path: Path) -> None:
    module = _load()
    with pytest.raises(ValueError, match="escapes"):
        module.confined(tmp_path, "../secret")
    inside = module.confined(tmp_path, "pkg/mod.py")
    assert inside == (tmp_path / "pkg" / "mod.py").resolve()


def test_run_command_is_off_until_allow_shell(tmp_path: Path) -> None:
    module = _load()
    names = {item["function"]["name"] for item in module.TOOLS}
    assert "run_command" not in names
    assert "run_command" in {item["function"]["name"] for item in module.tools_for(True)}
    locked = module.Workspace(tmp_path, "m")
    assert locked.dispatch("run_command", {"command": "echo hi"}) == "unknown tool run_command"
    opened = module.Workspace(tmp_path, "m", allow_shell=True)
    result = opened.dispatch("run_command", {"command": "echo hi"})
    assert result.startswith("exit 0")
    assert "hi" in result
    refused = opened.dispatch(
        "run_command",
        {"command": f"cat {module.checkout_root()}/README.md"},
    )
    assert "may not reference the bench checkout" in refused


def test_system_prompt_mentions_run_command_only_when_allowed() -> None:
    module = _load()
    plain = module.system_prompt("orchestrator", "m", False)
    shelled = module.system_prompt("orchestrator", "m", False, allow_shell=True)
    assert "run_command" not in plain
    assert "run_command" in shelled


def test_system_prompt_does_not_demand_wait_without_interrupt() -> None:
    module = _load()
    quiet = module.system_prompt("orchestrator", "m", False, expect_interrupt=False)
    armed = module.system_prompt("orchestrator", "m", False, expect_interrupt=True)
    assert "Do not call wait" in quiet
    assert "call wait" in armed
    assert "Do not call wait" not in armed


def test_wait_is_a_no_op_when_interrupt_is_not_expected(tmp_path, monkeypatch) -> None:
    module = _load()
    monkeypatch.delenv("STRONGORC_EXPECT_INTERRUPT", raising=False)
    monkeypatch.delenv("DURABLE_ORCH_EXPECT_INTERRUPT", raising=False)
    workspace = module.Workspace(tmp_path, "m")
    assert workspace.dispatch("wait", {"seconds": 3600}) == (
        "no harness interrupt on this spawn; finish the job"
    )
    monkeypatch.setenv("STRONGORC_EXPECT_INTERRUPT", "1")
    # Must not sleep an hour in CI; patch sleep.
    monkeypatch.setattr(module.time, "sleep", lambda _seconds: None)
    assert (
        workspace.dispatch("wait", {"seconds": 1})
        == "wait finished without interruption"
    )
