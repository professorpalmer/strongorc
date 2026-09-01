"""Private holdout overlay. Real banks stay outside git.

Set ``STRONGORC_HOLDOUT`` (or legacy ``DURABLE_ORCH_HOLDOUT``) to an
external overlay root. When unset, the public holdout slice is empty and
run/card refuse rather than scoring 0/0 as a pass.

Overlay layout (per opaque task id)::

    <overlay>/hld_<hex>/
      task.json          # id, track, slice, title, generator_id, family, rung
      prompt.md
      seed/
      oracle.py
      generators/<id>.py # stdlib-only: generate(run_dir, nonce) -> Path
      hidden/            # templates; never copied into the public repo
      agents/{pass,fail}.py

Generator contract: ``generate(run_dir: Path, nonce: str) -> Path``.
The returned path must be a directory inside ``run_dir``. Grade-time
cases are keyed to the harness nonce and materialize only in a temporary
grading workspace. Frozen ``TrialRecord.files`` and the public task tree
are never mutated. Check names use ``case_<hmac8>``.

Generators are trusted grader-side code loaded in-process. This is not a
sandbox and does not confine the generator process. Isolation is an
overlay snapshot/hash taken before and after ``generate``, plus a strict
jail on the returned path. If the overlay mutates, or the returned path
escapes the grading workspace, grade fails closed.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from strongorc.catalog import TaskSpec
from strongorc.env import getenv
from strongorc.module_loader import load_source_module

OPAQUE_ID = re.compile(r"^hld_[0-9a-f]+$")
HOLDOUT_ENV_KEYS = ("STRONGORC_HOLDOUT", "DURABLE_ORCH_HOLDOUT")
GENERATED_RELATIVE = ".holdout/generated"
GENERATOR_RECORD_RELATIVE = ".harness/generator.json"
CASE_HMAC_KEY = b"strongorc-holdout-case"
_SAFE_GENERATOR_ID = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class HoldoutUnavailable(RuntimeError):
    """Holdout slice cannot be scored without a usable overlay."""


class HoldoutError(RuntimeError):
    """Generator or overlay resolution failed closed."""


def overlay_root() -> Path | None:
    """Return the overlay directory, or None when unset / not a directory."""
    raw = getenv("HOLDOUT")
    if raw is None or not str(raw).strip():
        return None
    path = Path(raw).expanduser()
    try:
        path = path.resolve()
    except OSError:
        return None
    return path if path.is_dir() else None


def overlay_env_set() -> bool:
    raw = getenv("HOLDOUT")
    return raw is not None and bool(str(raw).strip())


def verify_overlay_commitment(root: Path | None = None) -> str:
    """Verify the private bank file manifest and return its SHA-256."""
    bank_root = Path(root) if root is not None else overlay_root()
    if bank_root is None:
        raise HoldoutError("holdout overlay is unavailable")
    commitment_path = bank_root / "BANK_COMMITMENT.json"
    if not commitment_path.is_file():
        raise HoldoutError("holdout overlay is missing BANK_COMMITMENT.json")
    try:
        commitment = json.loads(commitment_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HoldoutError("holdout bank commitment is not valid JSON") from exc
    expected = commitment.get("files") if isinstance(commitment, dict) else None
    if not isinstance(expected, dict) or not expected:
        raise HoldoutError("holdout bank commitment has no file digests")
    actual: dict[str, str] = {}
    for path in sorted(bank_root.rglob("*")):
        if path == commitment_path or not path.is_file():
            continue
        if path.is_symlink():
            raise HoldoutError("holdout bank commitment contains a symbolic link")
        relative = path.relative_to(bank_root).as_posix()
        actual[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    normalized = {str(name): str(digest) for name, digest in expected.items()}
    if normalized != actual:
        raise HoldoutError("holdout bank files do not match BANK_COMMITMENT.json")
    return hashlib.sha256(commitment_path.read_bytes()).hexdigest()


def generated_root(run_dir: Path) -> Path:
    return Path(run_dir).joinpath(*GENERATED_RELATIVE.split("/"))


def read_harness_nonce(run_dir: Path) -> str:
    path = Path(run_dir) / ".harness" / "nonce"
    if not path.is_file():
        raise HoldoutError("missing .harness/nonce")
    nonce = path.read_text(encoding="utf-8").strip()
    if not nonce:
        raise HoldoutError("empty .harness/nonce")
    return nonce


def opaque_case_name(case_id: str, nonce: str, *, key: bytes = CASE_HMAC_KEY) -> str:
    """Stable opaque check id: ``case_`` plus 8 hex HMAC chars."""
    digest = hmac.new(key, f"{case_id}\0{nonce}".encode("utf-8"), hashlib.sha256)
    return f"case_{digest.hexdigest()[:8]}"


def scrub_holdout_env(env: dict[str, str]) -> dict[str, str]:
    """Drop overlay location from an agent process environment."""
    for key in HOLDOUT_ENV_KEYS:
        env.pop(key, None)
    return env


@contextmanager
def holdout_env_hidden() -> Iterator[None]:
    """Hide overlay location from in-process scripted agents."""
    hidden: dict[str, str] = {}
    for key in HOLDOUT_ENV_KEYS:
        if key in os.environ:
            hidden[key] = os.environ.pop(key)
    try:
        yield
    finally:
        os.environ.update(hidden)


def _public_holdout_dir() -> Path:
    from strongorc.catalog import TASKS_ROOT

    return TASKS_ROOT / "holdout"


def _read_meta(task_dir: Path) -> dict:
    path = task_dir / "task.json"
    if not path.is_file():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _public_stubs() -> dict[str, dict]:
    root = _public_holdout_dir()
    stubs: dict[str, dict] = {}
    if not root.is_dir():
        return stubs
    for path in sorted(root.iterdir()):
        if not path.is_dir():
            continue
        meta = _read_meta(path)
        task_id = str(meta.get("id") or path.name)
        if OPAQUE_ID.fullmatch(task_id):
            stubs[task_id] = meta
    return stubs


def _load_overlay_task(task_dir: Path, stub: dict | None = None) -> TaskSpec:
    meta = _read_meta(task_dir)
    stub = stub or {}
    task_id = str(meta.get("id") or task_dir.name)
    if not OPAQUE_ID.fullmatch(task_id):
        raise HoldoutError(f"holdout task id must be hld_<hex>, got {task_id!r}")
    if task_dir.name != task_id:
        raise HoldoutError(f"holdout directory {task_dir.name} must match id {task_id}")
    track = meta.get("track") or stub.get("track")
    if track not in {"orchestrator", "worker"}:
        raise HoldoutError(f"{task_id} missing track")
    family = meta.get("family") or stub.get("family") or None
    rung = meta.get("rung") or stub.get("rung") or None
    generator_id = meta.get("generator_id") or None
    return TaskSpec(
        id=task_id,
        track=track,
        slice="holdout",
        title=str(meta.get("title") or task_id),
        timeout_seconds=int(meta.get("timeout_seconds", 30)),
        root=task_dir,
        bind=meta.get("bind"),
        interrupt=meta.get("interrupt"),
        facets=tuple(meta.get("facets") or ()),
        family=str(family) if family else None,
        rung=str(rung) if rung else None,
        generator_id=str(generator_id) if generator_id else None,
    )


def list_holdout_tasks() -> list[TaskSpec]:
    """Overlay tasks only. Public stubs are metadata; they do not score alone."""
    root = overlay_root()
    if root is None:
        return []
    stubs = _public_stubs()
    tasks: list[TaskSpec] = []
    for path in sorted(root.iterdir()):
        if not path.is_dir() or path.name.startswith("."):
            continue
        if not OPAQUE_ID.fullmatch(path.name):
            continue
        if not (path / "task.json").is_file():
            continue
        tasks.append(_load_overlay_task(path, stubs.get(path.name)))
    return tasks


def ensure_holdout_slice(slice_name: str) -> None:
    """Refuse vacuous holdout runs and cards."""
    if slice_name != "holdout":
        return
    if not overlay_env_set():
        raise HoldoutUnavailable(
            "holdout slice requires STRONGORC_HOLDOUT pointing at an overlay root; "
            "public holdout is empty and refusing vacuous score"
        )
    root = overlay_root()
    if root is None:
        raise HoldoutUnavailable(
            "STRONGORC_HOLDOUT is set but is not a directory; refusing vacuous score"
        )
    try:
        tasks = list_holdout_tasks()
    except HoldoutError as exc:
        raise HoldoutUnavailable(str(exc)) from exc
    if not tasks:
        raise HoldoutUnavailable(
            "holdout overlay has no opaque tasks; refusing vacuous score"
        )


def resolve_task(task: TaskSpec) -> TaskSpec:
    """Point oracle / hidden / generator / seed paths at the overlay."""
    if task.slice != "holdout":
        return task
    root = overlay_root()
    if root is None:
        raise HoldoutUnavailable(
            "holdout task requires STRONGORC_HOLDOUT; overlay is unset"
        )
    dest = root / task.id
    if not dest.is_dir() or not (dest / "task.json").is_file():
        raise HoldoutError(f"overlay missing task {task.id}")
    return _load_overlay_task(dest, _public_stubs().get(task.id))


def generator_path(task: TaskSpec) -> Path:
    direct = (
        task.root / "generators" / f"{task.generator_id}.py"
        if task.generator_id
        else None
    )
    if direct is None or not direct.is_file():
        task = resolve_task(task)
    if not task.generator_id:
        raise HoldoutError(f"{task.id} has no generator_id")
    if not _SAFE_GENERATOR_ID.fullmatch(task.generator_id):
        raise HoldoutError(f"invalid generator_id {task.generator_id!r}")
    path = task.root / "generators" / f"{task.generator_id}.py"
    if not path.is_file():
        raise HoldoutError(f"missing generator {path.name}")
    return path


def load_generator_module(task: TaskSpec):
    path = generator_path(task)
    module_name = f"holdout_gen_{task.id}_{task.generator_id}"
    try:
        return load_source_module(path, module_name)
    except Exception as exc:
        raise HoldoutError(f"cannot load generator {path}: {exc}") from exc


def load_generator(task: TaskSpec):
    path = generator_path(task)
    module = load_generator_module(task)
    generate = getattr(module, "generate", None)
    if not callable(generate):
        raise HoldoutError(f"{path} must define generate(run_dir, nonce)")
    return generate


def materialize_visible(task: TaskSpec, run_dir: Path, nonce: str) -> None:
    """Create candidate-visible live evidence before the agent starts."""
    module = load_generator_module(task)
    materialize = getattr(module, "materialize", None)
    if materialize is None:
        return
    if not callable(materialize):
        raise HoldoutError("generator materialize must be callable")
    before = _overlay_file_digests(task.root)
    try:
        materialize(Path(run_dir), nonce)
    except HoldoutError:
        raise
    except Exception as exc:
        raise HoldoutError(f"generator {task.generator_id} materialize failed: {exc}") from exc
    after = _overlay_file_digests(task.root)
    if before != after:
        raise HoldoutError("generator materialize mutated the overlay")


def materialize_after_interrupt(
    task: TaskSpec,
    run_dir: Path,
    nonce: str,
    step_index: int,
) -> None:
    """Apply private, nonce-bound live-state changes after a harness kill."""
    if not task.generator_id:
        return
    module = load_generator_module(task)
    materialize = getattr(module, "after_interrupt", None)
    if materialize is None:
        return
    if not callable(materialize):
        raise HoldoutError("generator after_interrupt must be callable")
    before = _overlay_file_digests(task.root)
    try:
        materialize(Path(run_dir), nonce, step_index)
    except HoldoutError:
        raise
    except Exception as exc:
        raise HoldoutError(
            f"generator {task.generator_id} after_interrupt failed: {exc}"
        ) from exc
    after = _overlay_file_digests(task.root)
    if before != after:
        raise HoldoutError("generator after_interrupt mutated the overlay")


def _record_generator_identity(task: TaskSpec, run_dir: Path, source: Path) -> None:
    harness = Path(run_dir) / ".harness"
    harness.mkdir(parents=True, exist_ok=True)
    payload = {
        "generator_id": task.generator_id,
        "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
    }
    dest = run_dir / GENERATOR_RECORD_RELATIVE
    dest.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _inside(child: Path, parent: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def _overlay_file_digests(root: Path) -> dict[str, str]:
    digests: dict[str, str] = {}
    for path in sorted(p for p in Path(root).rglob("*") if p.is_file()):
        relative = path.relative_to(root).as_posix()
        digests[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    return digests


def _jailed_returned_path(dest: Path, run_dir: Path) -> Path:
    """Require the generator return to resolve inside ``run_dir`` with no ``..``."""
    dest = Path(dest)
    run_dir = Path(run_dir)
    if any(part == ".." for part in dest.parts):
        raise HoldoutError("generator path escaped the grading workspace")
    if not dest.is_absolute():
        dest = run_dir / dest
    if dest.is_absolute() and not _inside(dest, run_dir):
        raise HoldoutError("generator wrote outside the grading workspace")
    try:
        resolved = dest.resolve()
    except OSError as exc:
        raise HoldoutError(f"generator path could not be resolved: {exc}") from exc
    if not resolved.is_dir():
        raise HoldoutError("generate(run_dir, nonce) must return a directory")
    if not _inside(resolved, run_dir):
        raise HoldoutError("generator wrote outside the grading workspace")
    return resolved


def generate_hidden(task: TaskSpec, run_dir: Path, nonce: str) -> Path:
    """Materialize nonce-keyed cases inside ``run_dir`` only.

    Does not write to ``task.root`` or to ``TrialRecord.files``.
    Generator modules are trusted grader-side code, not a sandbox.
    """
    task = resolve_task(task)
    run_dir = Path(run_dir)
    source = generator_path(task)
    generate = load_generator(task)
    before = _overlay_file_digests(task.root)
    try:
        dest = generate(run_dir, nonce)
    except HoldoutError:
        raise
    except Exception as exc:
        raise HoldoutError(f"generator {task.generator_id} failed: {exc}") from exc
    after = _overlay_file_digests(task.root)
    if before != after:
        raise HoldoutError("generator mutated the overlay")
    if dest is None:
        raise HoldoutError("generate(run_dir, nonce) returned None")
    dest = _jailed_returned_path(Path(dest), run_dir)
    if _inside(dest, task.root):
        raise HoldoutError("generator must not write into the overlay or public task tree")
    _record_generator_identity(task, run_dir, source)
    return dest


def isolate_grade_workspace(trial_files: dict[str, str], run_dir: Path, *, generator_id: str | None) -> Path:
    """Copy a live tree before generation so leftover run dirs stay frozen."""
    if not generator_id:
        return run_dir
    if trial_files:
        return run_dir
    dest = Path(tempfile.mkdtemp(prefix="strongorc-holdout-"))
    dest.rmdir()
    shutil.copytree(run_dir, dest)
    return dest
