from __future__ import annotations

import hashlib
import json
import re
import secrets
import threading
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable

from strongorc.catalog import TaskSpec
from strongorc.module_loader import load_source_module

_WORKER_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")
_BROKER_URL_KEYS = ("STRONGORC_WORKER_BROKER_URL", "DURABLE_ORCH_WORKER_BROKER_URL")
_BROKER_TOKEN_KEYS = (
    "STRONGORC_WORKER_BROKER_TOKEN",
    "DURABLE_ORCH_WORKER_BROKER_TOKEN",
)


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _first(environment: dict[str, str], keys: tuple[str, ...]) -> str:
    for key in keys:
        value = environment.get(key)
        if value:
            return value
    return ""


def _load_dispatch(task: TaskSpec) -> Callable[..., dict[str, Any]]:
    path = task.root / "workers.py"
    if not path.is_file():
        raise FileNotFoundError(f"missing worker pool: {path}")
    try:
        module = load_source_module(path, f"strongorc_workers_{task.id}")
    except Exception as exc:
        raise RuntimeError(f"cannot load worker pool: {path}: {exc}") from exc
    dispatch = getattr(module, "dispatch", None)
    if not callable(dispatch):
        raise TypeError(f"{path} must define dispatch(worker_id, assignment, run_dir, nonce)")
    return dispatch


class _BrokerState:
    def __init__(self, task: TaskSpec, run_dir: Path) -> None:
        self.run_dir = Path(run_dir)
        self.nonce = (self.run_dir / ".harness" / "nonce").read_text(
            encoding="utf-8"
        ).strip()
        self.dispatch_worker = _load_dispatch(task)
        self.dispatches: list[dict[str, Any]] = []
        self.consumptions: list[dict[str, Any]] = []
        self.lock = threading.Lock()

    def dispatch(self, payload: dict[str, Any]) -> dict[str, Any]:
        worker_id = str(payload.get("worker_id") or "")
        assignment = payload.get("assignment")
        if not _WORKER_ID.fullmatch(worker_id):
            return {"ok": False, "error": "invalid worker_id"}
        if not isinstance(assignment, dict):
            return {"ok": False, "error": "assignment must be an object"}
        with self.lock:
            dispatch_id = f"dispatch_{len(self.dispatches) + 1:03d}"
            try:
                report = self.dispatch_worker(
                    worker_id,
                    dict(assignment),
                    self.run_dir,
                    self.nonce,
                )
            except Exception as exc:
                return {
                    "ok": False,
                    "error": f"worker failed: {type(exc).__name__}",
                }
            if not isinstance(report, dict):
                return {"ok": False, "error": "worker report must be an object"}
            report_path = Path("workers") / f"{dispatch_id}.json"
            report_text = json.dumps(report, indent=2, sort_keys=True) + "\n"
            absolute_report_path = self.run_dir / report_path
            absolute_report_path.parent.mkdir(parents=True, exist_ok=True)
            absolute_report_path.write_text(report_text, encoding="utf-8")
            receipt = {
                "dispatch_id": dispatch_id,
                "worker_id": worker_id,
                "assignment_sha256": _sha256_text(_canonical_json(assignment)),
                "report_path": report_path.as_posix(),
                "report_sha256": _sha256_text(report_text),
            }
            self.dispatches.append(receipt)
        return {
            "ok": True,
            "dispatch_id": dispatch_id,
            "report_path": report_path.as_posix(),
        }

    def consume(self, payload: dict[str, Any]) -> dict[str, Any]:
        dispatch_id = str(payload.get("dispatch_id") or "")
        with self.lock:
            receipt = next(
                (
                    item
                    for item in self.dispatches
                    if item["dispatch_id"] == dispatch_id
                ),
                None,
            )
            if receipt is None:
                return {"ok": False, "error": "unknown dispatch_id"}
            report_path = self.run_dir / receipt["report_path"]
            report_text = report_path.read_text(encoding="utf-8")
            report_sha256 = _sha256_text(report_text)
            if report_sha256 != receipt["report_sha256"]:
                return {"ok": False, "error": "worker report integrity failure"}
            self.consumptions.append(
                {
                    "dispatch_id": dispatch_id,
                    "report_sha256": report_sha256,
                }
            )
            report = json.loads(report_text)
        return {"ok": True, "report": report}

    def snapshot(self) -> dict[str, list[dict[str, Any]]]:
        with self.lock:
            return {
                "dispatches": [dict(item) for item in self.dispatches],
                "consumptions": [dict(item) for item in self.consumptions],
            }


class _BrokerHandler(BaseHTTPRequestHandler):
    server: "_BrokerServer"

    def do_POST(self) -> None:
        authorization = self.headers.get("Authorization", "")
        if authorization != f"Bearer {self.server.token}":
            self._respond({"ok": False, "error": "unauthorized"}, status=401)
            return
        try:
            size = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(size) or b"{}")
        except (TypeError, ValueError, json.JSONDecodeError):
            self._respond({"ok": False, "error": "invalid JSON"}, status=400)
            return
        if not isinstance(payload, dict):
            self._respond({"ok": False, "error": "request must be an object"}, status=400)
            return
        if self.path == "/dispatch":
            response = self.server.state.dispatch(payload)
        elif self.path == "/consume":
            response = self.server.state.consume(payload)
        else:
            response = {"ok": False, "error": "unknown endpoint"}
        self._respond(response)

    def _respond(self, payload: dict[str, Any], status: int = 200) -> None:
        body = json.dumps(payload, sort_keys=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: Any) -> None:
        return


class _BrokerServer(ThreadingHTTPServer):
    def __init__(
        self,
        state: _BrokerState,
        token: str,
    ) -> None:
        super().__init__(("127.0.0.1", 0), _BrokerHandler)
        self.state = state
        self.token = token


class WorkerBroker:
    def __init__(self, task: TaskSpec, run_dir: Path) -> None:
        self.state = _BrokerState(task, run_dir)
        self.token = secrets.token_urlsafe(32)
        self.server = _BrokerServer(self.state, self.token)
        self.thread: threading.Thread | None = None

    @property
    def environment(self) -> dict[str, str]:
        host, port = self.server.server_address
        return {
            "STRONGORC_WORKER_BROKER_URL": f"http://{host}:{port}",
            "STRONGORC_WORKER_BROKER_TOKEN": self.token,
        }

    def __enter__(self) -> WorkerBroker:
        self.thread = threading.Thread(
            target=self.server.serve_forever,
            name="strongorc-worker-broker",
            daemon=True,
        )
        self.thread.start()
        return self

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        self.server.shutdown()
        self.server.server_close()
        if self.thread is not None:
            self.thread.join(timeout=5)

    def snapshot(self) -> dict[str, list[dict[str, Any]]]:
        return self.state.snapshot()


class WorkerClient:
    def __init__(self, base_url: str, token: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token

    @classmethod
    def from_environment(cls, environment: dict[str, str]) -> WorkerClient:
        base_url = _first(environment, _BROKER_URL_KEYS)
        token = _first(environment, _BROKER_TOKEN_KEYS)
        if not base_url or not token:
            raise ValueError("worker broker unavailable")
        return cls(base_url, token)

    def request(self, operation: str, payload: dict[str, Any]) -> dict[str, Any]:
        request = urllib.request.Request(
            f"{self.base_url}/{operation}",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            result = json.loads(response.read())
        if not isinstance(result, dict):
            raise RuntimeError("worker broker returned a non-object response")
        return result

    def dispatch(self, worker_id: str, assignment: dict[str, Any]) -> dict[str, Any]:
        response = self.request(
            "dispatch",
            {"worker_id": worker_id, "assignment": assignment},
        )
        if not response.get("ok"):
            raise RuntimeError(str(response.get("error") or "worker dispatch failed"))
        return response

    def consume(self, dispatch_id: str) -> dict[str, Any]:
        response = self.request("consume", {"dispatch_id": dispatch_id})
        if not response.get("ok"):
            raise RuntimeError(str(response.get("error") or "worker consume failed"))
        report = response.get("report")
        if not isinstance(report, dict):
            raise RuntimeError("worker report must be an object")
        return report
