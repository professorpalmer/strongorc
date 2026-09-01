import json
import time
from pathlib import Path

from strongorc.agentlib import copy_reference, finish, write_checkpoint
from strongorc.env import getenv
from strongorc.protocol import emit

run_dir = Path(RUN_DIR)
model = MODEL
copied: list[str] = []
nonce = json.loads((run_dir / 'job' / 'leases.json').read_text(encoding='utf-8')).get('nonce')
if not nonce:
    nonce = (run_dir / '.harness' / 'nonce').read_text(encoding='utf-8').strip()
if getenv("RESUME") != "1":
    emit(run_dir, "worker_started", worker="alpha")
    copied = copy_reference(run_dir, Path(__file__), ['kiln'])
    for name in copied:
        init = run_dir / name / '__init__.py'
        if init.is_file() and nonce:
            text = init.read_text(encoding='utf-8')
            if nonce not in text:
                init.write_text(text + f'\nNONCE = {nonce!r}\n', encoding='utf-8')
    emit(run_dir, "worker_finished", worker="alpha")
    write_checkpoint(run_dir, "checkpoint.json", {"last_completed": "alpha"})
    time.sleep(3600)
else:
    emit(run_dir, "resumed_from_checkpoint")
    if []:
        emit(run_dir, "worker_started", worker="beta")
        copied = copy_reference(run_dir, Path(__file__), [])
        emit(run_dir, "worker_finished", worker="beta")
    for name in copied:
        init = run_dir / name / '__init__.py'
        if init.is_file() and nonce:
            text = init.read_text(encoding='utf-8')
            if nonce not in text:
                init.write_text(text + f'\nNONCE = {nonce!r}\n', encoding='utf-8')
    finish(run_dir, model, status="completed", workers_ran=1, usd=0.36, extra={'nonce': nonce})
