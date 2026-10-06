from __future__ import annotations

import argparse
import json
import signal
import sys
import time

from app.orchestrator.execution_policy import evaluate_llm_execution
from app.orchestrator.worker_tick import run_worker_tick

_STOP_SIGNALLED = False


def _handle_signal(signum, _frame):  # pragma: no cover - signal behavior
    global _STOP_SIGNALLED
    _STOP_SIGNALLED = True
    print(json.dumps({'event': 'signal_received', 'signal': signum}), flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(description='Worker daemon loop for orchestrator')
    parser.add_argument('--profile', default='runtime/agent_orchestrator/project_profile.json')
    parser.add_argument('--interval-seconds', type=int, default=30)
    args = parser.parse_args()

    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    while not _STOP_SIGNALLED:
        started_at = time.time()
        policy = evaluate_llm_execution(source='worker-daemon', profile_path=args.profile)
        if not policy.allowed:
            if policy.code == 'GLOBAL_LLM_HARD_OFF':
                result = {'status': 'WORKER_SKIP_HARD_OFF', 'reason': policy.message, 'policy_code': policy.code}
            elif policy.code == 'GLOBAL_SCHEDULER_DISABLED':
                result = {'status': 'WORKER_SKIP_DISABLED', 'reason': policy.message, 'policy_code': policy.code}
            else:
                result = {'status': 'WORKER_SKIP_SAFE_RUN', 'reason': policy.message, 'policy_code': policy.code}
        else:
            result = run_worker_tick(profile_path=args.profile, run_type='worker-daemon')
        print(json.dumps(result, ensure_ascii=False), flush=True)

        elapsed = max(0, int(time.time() - started_at))
        wait_seconds = max(1, args.interval_seconds - elapsed)
        for _ in range(wait_seconds):
            if _STOP_SIGNALLED:
                break
            time.sleep(1)

    print(json.dumps({'event': 'worker_daemon_exit'}), flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
