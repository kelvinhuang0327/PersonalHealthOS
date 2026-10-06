"""Problem Signal Layer — detects real product and process issues from orchestrator data.

Signals are derived from the SQLite orchestrator task history and represent
concrete, observable problems that the next sprint task should address.
Each issue carries a suggested_category so the planner can generate a
problem-specific task instead of a generic static template.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

# How long a completed task signature stays "on cooldown" before it can be re-queued
SIGNATURE_COOLDOWN_DAYS = 7


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_iso(ts: str | None) -> datetime | None:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(str(ts).replace('Z', '+00:00'))
    except (ValueError, AttributeError):
        return None


def get_recently_completed_signatures(
    recent_tasks: list[dict[str, Any]],
    cooldown_days: int = SIGNATURE_COOLDOWN_DAYS,
) -> dict[str, datetime]:
    """Return a mapping of {signature: finished_at} for tasks completed within cooldown_days.

    Used by the duplicate gate and the planner to avoid re-queuing identical work.
    """
    cutoff = _utc_now() - timedelta(days=cooldown_days)
    result: dict[str, datetime] = {}
    for task in recent_tasks:
        if task.get('status') != 'COMPLETED':
            continue
        sig = str(task.get('duplicate_signature') or '').strip()
        if not sig:
            continue
        finished = _parse_iso(task.get('finished_at'))
        if finished and finished > cutoff:
            result[sig] = finished
    return result


def detect_product_issues(
    recent_tasks: list[dict[str, Any]],
    all_pool_signatures: dict[str, str],  # {signature: category}
    product_signals: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Scan orchestrator task history and return detected product/process issues.

    Each issue dict contains:
      issue_type      — machine-readable type
      severity        — 'high' | 'medium' | 'low'
      title           — short human-readable problem statement
      description     — longer explanation with numbers
      suggested_category — category from the pool to address this issue (may be None)
      signal_data     — raw numbers/lists for audit / debugging

    Args:
        recent_tasks: Task list from db.list_tasks(limit=50).
        all_pool_signatures: {duplicate_signature: category} for every pool template.
        product_signals: Optional dict from build_product_signals() with real user
            engagement metrics (completion_rate, snooze_count, etc.).
    """
    issues: list[dict[str, Any]] = []
    now = _utc_now()
    cutoff_7d = now - timedelta(days=7)
    cutoff_30d = now - timedelta(days=30)

    # ── 0. Real product signal issues (highest priority — surface first) ──────
    if product_signals:
        issues.extend(_detect_product_signal_issues(product_signals))

    # ── 1. Quality gate failure rate ─────────────────────────────────────────
    # If REPLAN_REQUIRED tasks exist, the quality gate is miscalibrated or workers
    # are not filling in delivery evidence.
    replan_tasks = [t for t in recent_tasks if t.get('status') == 'REPLAN_REQUIRED']
    if replan_tasks:
        gate_reasons = [str(t.get('gate_reason') or '') for t in replan_tasks]
        sample_reason = gate_reasons[0][:120] if gate_reasons else ''
        issues.append({
            'issue_type': 'quality_gate_failures',
            'severity': 'high',
            'title': f'{len(replan_tasks)} tasks rejected by quality gate (REPLAN_REQUIRED)',
            'description': (
                f'{len(replan_tasks)} tasks are stuck in REPLAN_REQUIRED. '
                f'Sample rejection reason: {sample_reason}. '
                'Worker delivery is not meeting the substantive evidence bar.'
            ),
            'suggested_category': None,
            'signal_data': {
                'replan_count': len(replan_tasks),
                'task_ids': [t['id'] for t in replan_tasks],
                'sample_reason': sample_reason,
            },
        })

    # ── 2. Category neglect — product areas not touched recently ─────────────
    completed_sigs_30d: set[str] = set()
    completed_sigs_7d: set[str] = set()
    for task in recent_tasks:
        if task.get('status') != 'COMPLETED':
            continue
        sig = str(task.get('duplicate_signature') or '').strip()
        if not sig:
            continue
        finished = _parse_iso(task.get('finished_at'))
        if finished:
            if finished > cutoff_30d:
                completed_sigs_30d.add(sig)
            if finished > cutoff_7d:
                completed_sigs_7d.add(sig)

    untouched_30d = [
        cat for sig, cat in all_pool_signatures.items()
        if sig not in completed_sigs_30d
    ]
    if untouched_30d:
        issues.append({
            'issue_type': 'category_neglected',
            'severity': 'medium',
            'title': f'{len(untouched_30d)} product areas not addressed in 30 days',
            'description': (
                f'Categories with no completed sprint in the last 30 days: '
                f'{", ".join(untouched_30d[:6])}. '
                'Focus rotation should prioritise these areas.'
            ),
            'suggested_category': untouched_30d[0],
            'signal_data': {
                'untouched_categories': untouched_30d,
                'active_categories': [
                    cat for sig, cat in all_pool_signatures.items()
                    if sig in completed_sigs_30d
                ],
            },
        })

    # ── 3. Recent completion burst — all recent tasks completed in one session ─
    # When all recent tasks were completed in a very short window (< 1 hour total),
    # delivery depth may be too shallow.
    completed_recent = [
        t for t in recent_tasks[:15]
        if t.get('status') == 'COMPLETED' and _parse_iso(t.get('finished_at'))
    ]
    if len(completed_recent) >= 10:
        timestamps = [_parse_iso(t['finished_at']) for t in completed_recent]  # type: ignore[arg-type]
        span = (max(timestamps) - min(timestamps)).total_seconds() if timestamps else 0  # type: ignore[type-var]
        if span < 3600:  # all 10+ tasks completed within 1 hour
            issues.append({
                'issue_type': 'shallow_sprint_velocity',
                'severity': 'medium',
                'title': f'{len(completed_recent)} tasks completed in under 1 hour — verify depth',
                'description': (
                    f'{len(completed_recent)} tasks completed in {int(span / 60)} minutes. '
                    'Rapid completion suggests worker is generating scaffolding rather than '
                    'substantive code changes. Next sprint should target a specific, '
                    'measurable code change.'
                ),
                'suggested_category': None,
                'signal_data': {
                    'count': len(completed_recent),
                    'span_minutes': int(span / 60),
                },
            })

    # ── 4. Signature cooldown — pool categories recently completed ────────────
    # Report which signatures are in cooldown so the planner knows what to skip.
    on_cooldown = {
        sig: cat for sig, cat in all_pool_signatures.items()
        if sig in completed_sigs_7d
    }
    if len(on_cooldown) == len(all_pool_signatures):
        issues.append({
            'issue_type': 'all_signatures_on_cooldown',
            'severity': 'low',
            'title': 'All pool categories completed in the last 7 days',
            'description': (
                'Every pool template was completed within the last 7 days. '
                'The planner should generate a problem-specific task based on '
                'actual product signals rather than cycling through static templates again.'
            ),
            'suggested_category': None,
            'signal_data': {'on_cooldown_count': len(on_cooldown)},
        })

    return issues


# ---------------------------------------------------------------------------
# Product signal issue detection — real user engagement metrics
# ---------------------------------------------------------------------------

# Thresholds for triggering product issues
_LOW_COMPLETION_RATE = 0.30   # < 30% completion rate → action UX problem
_HIGH_SNOOZE_RATE = 0.40      # > 40% snooze rate → notification fatigue
_LOW_INSIGHT_CONVERSION = 0.10  # < 10% insight→action → bridge missing
_LOW_DOC_CONVERSION = 0.05    # < 5% document→action → parser/UX gap
_HIGH_SNOOZE_COUNT = 10       # absolute snooze count threshold


def _detect_product_signal_issues(signals: dict[str, Any]) -> list[dict[str, Any]]:
    """Convert real product engagement signals into actionable issues.

    Planner ordering per spec:
      1. High-severity product issues from real signals (this function)
      2. Stale/REPLAN recovery (handled by caller)
      3. Task pool fallback

    Issues returned are sorted high → low severity so the planner picks
    the most urgent real problem first.
    """
    issues: list[dict[str, Any]] = []

    completion_rate = signals.get('completion_rate')
    snooze_rate = signals.get('snooze_rate')
    snooze_count = signals.get('snooze_count', 0)
    insight_conversion = signals.get('insight_action_conversion')
    doc_conversion = signals.get('doc_action_conversion')
    outcome_rate = signals.get('outcome_improvement_rate')
    total_actions = signals.get('total_actions', 0)

    # ── High snooze rate → notification optimization task ────────────────────
    if (
        (snooze_rate is not None and snooze_rate > _HIGH_SNOOZE_RATE)
        or snooze_count >= _HIGH_SNOOZE_COUNT
    ):
        pct = f'{int(snooze_rate * 100)}%' if snooze_rate is not None else f'{snooze_count} snoozes'
        issues.append({
            'issue_type': 'high_snooze_rate',
            'severity': 'high',
            'title': f'使用者忽略了 {pct} 的健康提醒 — 通知需優化',
            'description': (
                f'行動暫緩率達 {pct}（共 {snooze_count} 次暫緩）。'
                f'這代表通知內容、時機或頻率有問題。'
                f'使用者正在逃避系統而非接受協助。'
            ),
            'suggested_category': 'notification_optimization',
            'signal_data': {
                'snooze_rate': snooze_rate,
                'snooze_count': snooze_count,
                'total_actions': total_actions,
            },
        })

    # ── Low completion rate → action UX/feedback task ────────────────────────
    if completion_rate is not None and completion_rate < _LOW_COMPLETION_RATE and total_actions >= 3:
        issues.append({
            'issue_type': 'low_action_completion_rate',
            'severity': 'high',
            'title': f'行動完成率僅 {int(completion_rate * 100)}% — 需改善行動 UX 或回饋機制',
            'description': (
                f'使用者只完成了 {int(completion_rate * 100)}% 的健康行動'
                f'（共 {total_actions} 個行動，完成 {signals.get("completed_actions", 0)} 個）。'
                f'低完成率代表行動太難、描述不夠清楚，或缺少完成後的正面回饋。'
            ),
            'suggested_category': 'action_ux_improvement',
            'signal_data': {
                'completion_rate': completion_rate,
                'completed': signals.get('completed_actions', 0),
                'total': total_actions,
            },
        })

    # ── Low insight-to-action conversion → bridge task ───────────────────────
    if (
        insight_conversion is not None
        and insight_conversion < _LOW_INSIGHT_CONVERSION
        and signals.get('insight_count', 0) >= 3
    ):
        issues.append({
            'issue_type': 'low_insight_action_conversion',
            'severity': 'medium',
            'title': f'洞察轉化率僅 {int(insight_conversion * 100)}% — 洞察到行動橋接需強化',
            'description': (
                f'系統共產生 {signals.get("insight_count", 0)} 個健康洞察，'
                f'但只有 {int(insight_conversion * 100)}% 轉化為行動。'
                f'使用者看到洞察後無法輕鬆採取行動，需要增加「根據洞察建立行動」的 CTA。'
            ),
            'suggested_category': 'insight_action_bridge',
            'signal_data': {
                'insight_count': signals.get('insight_count', 0),
                'insight_sourced_actions': signals.get('insight_action_conversion', 0),
                'conversion_rate': insight_conversion,
            },
        })

    # ── Low document-to-action conversion → parser/UX gap ────────────────────
    if (
        doc_conversion is not None
        and doc_conversion < _LOW_DOC_CONVERSION
        and signals.get('report_count', 0) >= 2
    ):
        issues.append({
            'issue_type': 'low_document_action_conversion',
            'severity': 'medium',
            'title': f'健檢報告轉化率低 — 報告解讀沒有轉化為具體行動',
            'description': (
                f'使用者上傳了 {signals.get("report_count", 0)} 份健檢報告，'
                f'但只有 {int(doc_conversion * 100)}% 的報告產生對應行動。'
                f'可能原因：異常項目的推薦行動功能不夠完善。'
            ),
            'suggested_category': 'report_action_bridge',
            'signal_data': {
                'report_count': signals.get('report_count', 0),
                'doc_conversion': doc_conversion,
            },
        })

    # ── No outcomes tracked → outcome feedback loop missing ──────────────────
    if total_actions >= 5 and signals.get('total_outcomes', 0) == 0:
        issues.append({
            'issue_type': 'no_outcome_tracking',
            'severity': 'low',
            'title': '完成行動後未追蹤健康改善結果',
            'description': (
                f'使用者已完成 {signals.get("completed_actions", 0)} 個行動，'
                f'但 0 個行動有記錄健康結果（outcomes）。'
                f'缺少結果追蹤導致使用者看不到努力的成效，降低長期黏著度。'
            ),
            'suggested_category': 'outcome_feedback_loop',
            'signal_data': {
                'completed_actions': signals.get('completed_actions', 0),
                'total_outcomes': 0,
            },
        })

    # Sort by severity
    _sev_order = {'high': 0, 'medium': 1, 'low': 2}
    issues.sort(key=lambda i: _sev_order.get(i['severity'], 3))
    return issues


def build_problem_task_draft_markdown(issue: dict[str, Any]) -> str:
    """Build a specific, non-generic task draft markdown from a detected issue.

    Returns a draft_markdown string ready for TaskDraft construction.
    The content is grounded in the specific numbers and context of the issue,
    not a static template.
    """
    issue_type = issue['issue_type']
    title_prefix = '產品問題衝刺: '

    if issue_type == 'quality_gate_failures':
        data = issue['signal_data']
        count = data['replan_count']
        task_ids = data.get('task_ids', [])[:5]
        reason = data.get('sample_reason', '')
        title = f'{title_prefix}修復 {count} 個 REPLAN_REQUIRED 任務的交付問題'
        return (
            f'{title}\n\n'
            f'User Value: Workers are producing incomplete deliveries that fail the quality gate. '
            f'{count} tasks (IDs: {task_ids}) are stuck. '
            f'Until fixed, the orchestrator cannot make forward progress.\n\n'
            f'Product Maturity Impact: A quality gate that rejects all deliveries signals a '
            f'calibration mismatch between what the gate expects and what workers produce. '
            f'Fixing this unblocks the entire sprint pipeline.\n\n'
            f'Expected Change: REPLAN_REQUIRED count drops to 0. The quality gate only '
            f'rejects genuinely incomplete work, not well-intentioned structural deliveries.\n\n'
            f'Objective: Investigate why the quality gate is rejecting these {count} tasks. '
            f'Sample rejection reason: "{reason[:80]}". '
            f'Fix either the gate calibration or the worker output format so that structured '
            f'deliveries pass.\n\n'
            f'Phase 1: Read the completed.md for each REPLAN_REQUIRED task. '
            f'Identify the exact pattern causing rejection (placeholder text, short content, etc.).\n'
            f'Phase 2: Update the worker completion template in worker_tick.py to generate '
            f'substantive evidence rather than HTML comment placeholders.\n'
            f'Phase 3: For each stuck task, rewrite completed.md with real evidence from the '
            f'contract fields (user_value, product_maturity_impact, expected_change).\n'
            f'Phase 4: Reset stuck tasks to QUEUED. Run worker ticks. Verify all pass GATE_PASS.\n\n'
            f'Scope: backend/app/orchestrator/worker_tick.py, '
            f'backend/app/orchestrator/task_result_quality_gate.py, '
            f'runtime/agent_orchestrator/tasks/\n'
            f'Acceptance Criteria: All REPLAN_REQUIRED tasks resolve to COMPLETED; '
            f'new tasks generated by worker_tick no longer contain HTML comment placeholders; '
            f'make backend-test passes.\n'
            f'focus_keys: quality_gate, replan, worker_delivery, gate_calibration\n'
            f'expected_duration_minutes: 120'
        )

    if issue_type == 'category_neglected':
        data = issue['signal_data']
        untouched = data.get('untouched_categories', [])[:4]
        suggested = issue.get('suggested_category') or (untouched[0] if untouched else 'behavior_loop_optimization')
        title = f'{title_prefix}補強長期未覆蓋的產品領域: {suggested}'
        return (
            f'{title}\n\n'
            f'User Value: {len(untouched)} product areas have had no sprint in 30+ days: '
            f'{", ".join(untouched)}. These areas have accumulated unaddressed '
            f'product debt that affects user experience.\n\n'
            f'Product Maturity Impact: Unbalanced product development creates gaps in '
            f'user experience quality. The neglected area "{suggested}" likely has the '
            f'highest opportunity for improvement relative to effort.\n\n'
            f'Expected Change: The {suggested} area receives at least one concrete '
            f'improvement that measurably advances user value in that domain.\n\n'
            f'Objective: Focus this sprint entirely on "{suggested}". '
            f'Make the highest-impact change possible in that area.\n\n'
            f'Phase 1: Audit the current state of "{suggested}" in the codebase. '
            f'What exists? What is broken or missing? What do users encounter?\n'
            f'Phase 2: Identify the single highest-impact change. '
            f'Think: what is the one thing a user in this area needs most?\n'
            f'Phase 3: Implement that change. Keep scope tight — one real improvement '
            f'is better than five half-finished ideas.\n'
            f'Phase 4: Run make backend-test and npm run build. '
            f'Document what changed and why it matters to the user.\n\n'
            f'Scope: backend/app/, frontend/app/platform/{suggested.replace("_", "-")}/\n'
            f'Acceptance Criteria: At least one concrete, tested change in the {suggested} area; '
            f'make backend-test passes; npm run build passes.\n'
            f'focus_keys: {", ".join(untouched[:4])}, product_debt\n'
            f'expected_duration_minutes: 480'
        )

    if issue_type == 'shallow_sprint_velocity':
        data = issue['signal_data']
        count = data['count']
        span = data['span_minutes']
        title = f'{title_prefix}提升交付深度 — {count} 個任務在 {span} 分鐘內完成，可能過於表面'
        return (
            f'{title}\n\n'
            f'User Value: When {count} sprints complete in {span} minutes, the worker is likely '
            f'generating boilerplate rather than real product improvements. '
            f'Users deserve code that actually runs and changes their experience.\n\n'
            f'Product Maturity Impact: Sprint velocity metrics are meaningless if the delivery '
            f'is scaffolding. This sprint must produce at least one file change that can be '
            f'verified by running the test suite.\n\n'
            f'Expected Change: The completed delivery includes a verified changed_files list '
            f'with at least 2 real modified files and passing test evidence.\n\n'
            f'Objective: Pick the highest-priority area from the product backlog and make a '
            f'real, verifiable code change. No scaffolding, no placeholder text.\n\n'
            f'Phase 1: Read the 5 most recent completed.md files. '
            f'Identify what actually changed vs. what was scaffolding.\n'
            f'Phase 2: Pick the area with the most scaffolding and no real change. '
            f'Make the actual code change that was promised.\n'
            f'Phase 3: Run make backend-test to confirm the change works.\n'
            f'Phase 4: Update completed.md with exact file names changed, line counts, '
            f'and test output as evidence.\n\n'
            f'Scope: backend/app/, frontend/app/platform/\n'
            f'Acceptance Criteria: changed_files list contains ≥2 real modified files; '
            f'make backend-test passes; completed.md cites specific line numbers changed.\n'
            f'focus_keys: delivery_depth, code_quality, test_coverage, real_changes\n'
            f'expected_duration_minutes: 480'
        )

    if issue_type == 'all_signatures_on_cooldown':
        count = issue['signal_data'].get('on_cooldown_count', 12)
        title = f'{title_prefix}全類別輪替完成 — 選擇下一個最高價值優化領域'
        return (
            f'{title}\n\n'
            f'User Value: {count} 個任務池類別已在近期全數完成，系統需要基於真實產品信號選擇下一個'
            f'最具用戶價值的改善重點，而非重複已完成的靜態模板。\n\n'
            f'Product Maturity Impact: 任務池全輪替後，選擇最能提升用戶留存與日常使用體驗的領域'
            f'進行深度改善，是產品成熟度的關鍵指標。\n\n'
            f'Expected Change: 本次衝刺聚焦一個高用戶價值領域，交付可量測的產品改善，'
            f'為後續任務輪替建立新的優先方向。\n\n'
            f'Objective: 審視 backend/app/、frontend/app/platform/ 各模組近況，'
            f'找出最具用戶影響力的未完成改善點，並實作一個具體可測試的功能改善。\n\n'
            f'Phase 1: 閱讀最近 5 個 completed.md，找出交付深度不足或用戶影響力最高的領域。'
            f'記錄每個領域的現況與缺口。\n'
            f'Phase 2: 選定最高優先領域（以用戶每日使用頻率與留存影響為標準），'
            f'設計一個具體、可在 8 小時內完成的改善方案。\n'
            f'Phase 3: 實作改善方案。修改至少 2 個真實檔案，確保改動可被測試驗證。\n'
            f'Phase 4: 執行 make backend-test 與 npm run build，確認所有測試通過。'
            f'在完成報告中記錄改動的檔案、行數與對用戶的實際影響。\n\n'
            f'Scope: backend/app/, frontend/app/platform/\n'
            f'Acceptance Criteria: 至少 2 個真實檔案被修改；make backend-test 通過；'
            f'npm run build 通過；completed.md 包含具體的 changed_files 與測試證據。\n'
            f'focus_keys: product_value, user_retention, delivery_depth, real_changes\n'
            f'expected_duration_minutes: 480'
        )

    if issue_type == 'high_snooze_rate':
        data = issue['signal_data']
        snooze_count = data.get('snooze_count', 0)
        snooze_pct = f'{int(data["snooze_rate"] * 100)}%' if data.get('snooze_rate') else f'{snooze_count}次'
        title = f'{title_prefix}降低通知疲勞 — {snooze_pct} 的健康提醒被暫緩'
        return (
            f'{title}\n\n'
            f'User Value: 使用者已暫緩了 {snooze_count} 次健康提醒（暫緩率 {snooze_pct}）。'
            f'這代表通知時機、內容或頻率不符合使用者節奏，使用者正在迴避系統協助。\n\n'
            f'Product Maturity Impact: 高暫緩率是系統與使用者生活脫節的強力信號。'
            f'未修復的通知疲勞會導致使用者最終關閉所有提醒，失去 Daily Health Loop 的核心價值。\n\n'
            f'Expected Change: 暫緩率在 2 週內降至 25% 以下；'
            f'通知在使用者的黃金時段出現（而非固定時間）；'
            f'行動描述更清晰讓使用者知道「做什麼」而非「被提醒」。\n\n'
            f'Objective: 審查通知機制與行動卡片內容，減少不必要的打擾。\n\n'
            f'Phase 1: 分析暫緩記錄 — 找出哪些行動類型被最多次暫緩，'
            f'以及暫緩的時間模式（早/晚/週末）。\n'
            f'Phase 2: 重新設計高暫緩率行動的通知文案。'
            f'使用具體、可立即執行的語言而非提醒式語言。\n'
            f'Phase 3: 實作「通知時段偏好設定」或「智慧延後」功能，'
            f'讓使用者能設定自己的最佳提醒時間。\n'
            f'Phase 4: 運行測試並更新 frontend 行動卡片的文案標準。\n\n'
            f'Scope: frontend/app/platform/actions/, backend/app/services/, '
            f'backend/app/api/actions.py\n'
            f'Acceptance Criteria: 行動卡片文案更新；'
            f'通知偏好設定 UI 可用或通知智慧延後功能上線；'
            f'make backend-test 通過；npm run build 通過。\n'
            f'focus_keys: notification_optimization, snooze_rate, user_engagement\n'
            f'expected_duration_minutes: 360'
        )

    if issue_type == 'low_action_completion_rate':
        data = issue['signal_data']
        rate_pct = f'{int(data.get("completion_rate", 0) * 100)}%'
        completed = data.get('completed', 0)
        total = data.get('total', 0)
        title = f'{title_prefix}提升行動完成率 — 目前僅 {rate_pct}（{completed}/{total}）'
        return (
            f'{title}\n\n'
            f'User Value: 使用者只完成了 {rate_pct} 的健康行動（{completed}/{total} 個）。'
            f'行動完成是 PersonalHealthOS 核心價值交付的最後一哩路。'
            f'未完成的行動意味著健康改善停留在計劃而非實踐。\n\n'
            f'Product Maturity Impact: 完成率是衡量產品能否有效引導使用者改變行為的核心指標。'
            f'{rate_pct} 的完成率代表 6-7 成的努力都沒有轉化為實際健康行動。\n\n'
            f'Expected Change: 完成率在 4 週內提升至 45% 以上；'
            f'完成一個行動後 UI 顯示明確的正向回饋（streak、改善指標）；'
            f'太難完成的行動可以被分解為更小的步驟。\n\n'
            f'Objective: 找出是什麼阻止使用者完成行動，並針對性地改善 UX 和行動設計。\n\n'
            f'Phase 1: 檢查行動列表 — 有哪些行動被創建後從未完成？'
            f'這些行動的類別和難度是否有規律？\n'
            f'Phase 2: 改善行動卡片的完成體驗 — 增加「完成」按鈕的顯著性，'
            f'完成後顯示健康數值改善或 streak 里程碑。\n'
            f'Phase 3: 為長期未完成的行動增加「分解為更小步驟」功能，'
            f'或自動調整難度標籤（困難→中等）。\n'
            f'Phase 4: 確認 ActionStreak 邏輯正常運作，'
            f'streak 在 UI 中清晰可見並提供鼓勵。\n\n'
            f'Scope: frontend/app/platform/actions/, backend/app/services/health_ai_engine/, '
            f'backend/app/models/entities.py\n'
            f'Acceptance Criteria: 行動完成流程 UX 改善可展示；'
            f'ActionStreak 正確累計；make backend-test 通過；npm run build 通過。\n'
            f'focus_keys: action_completion, behavior_loop, user_engagement, streak\n'
            f'expected_duration_minutes: 480'
        )

    if issue_type == 'low_insight_action_conversion':
        data = issue['signal_data']
        count = data.get('insight_count', 0)
        rate_pct = f'{int(data.get("conversion_rate", 0) * 100)}%'
        title = f'{title_prefix}洞察→行動橋接 — {count} 個洞察中只有 {rate_pct} 轉化為行動'
        return (
            f'{title}\n\n'
            f'User Value: 系統已產生 {count} 個健康洞察，但只有 {rate_pct} 促使使用者建立了對應行動。'
            f'洞察的最終目的是引導使用者採取行動。沒有行動的洞察是浪費的健康知識。\n\n'
            f'Product Maturity Impact: 洞察-行動轉化率反映了系統能否有效「閉環」。'
            f'低轉化率代表洞察卡片缺少直達行動的 CTA，或行動建議和洞察內容沒有明顯連結。\n\n'
            f'Expected Change: 洞察卡片增加「立即建立對應行動」按鈕；'
            f'轉化率在 4 週後提升至 30% 以上；'
            f'從洞察創建的行動在行動列表中標記來源。\n\n'
            f'Objective: 在每個洞察卡片底部新增 CTA，直接帶使用者進入行動建立流程。\n\n'
            f'Phase 1: 在 InsightCard 元件加入「建立對應行動」CTA 按鈕。'
            f'點擊後帶入洞察 ID 作為 source_id，pre-fill 行動表單。\n'
            f'Phase 2: 在後端 HealthAction 模型確保 source_type=insight 的 FK 正確記錄。\n'
            f'Phase 3: 在 health_assistant_service.py 的 build_product_signals() '
            f'中計算 insight_action_conversion，讓後續 sprint 可追蹤改善效果。\n'
            f'Phase 4: 更新 Insights 頁面 UI，顯示每個洞察的「已對應行動」標記。\n\n'
            f'Scope: frontend/app/platform/insights/, backend/app/api/insights.py, '
            f'backend/app/services/health_assistant_service.py\n'
            f'Acceptance Criteria: InsightCard 有 CTA 按鈕；'
            f'點擊後能建立與洞察關聯的行動；make backend-test 通過；npm run build 通過。\n'
            f'focus_keys: insight_action_bridge, conversion_rate, user_value\n'
            f'expected_duration_minutes: 360'
        )

    if issue_type in ('low_document_action_conversion', 'low_doc_action_conversion'):
        data = issue['signal_data']
        report_count = data.get('report_count', 0)
        rate_pct = f'{int(data.get("doc_conversion", 0) * 100)}%'
        title = f'{title_prefix}健檢報告行動化 — {report_count} 份報告中只有 {rate_pct} 產生行動'
        return (
            f'{title}\n\n'
            f'User Value: 使用者上傳了 {report_count} 份健檢報告，'
            f'但只有 {rate_pct} 的報告促使他們建立了具體的改善行動。'
            f'健檢報告是使用者願意主動提供的最高品質健康數據，不利用它等於浪費最寶貴的輸入。\n\n'
            f'Product Maturity Impact: 文件→行動轉化是 PersonalHealthOS 差異化能力的核心：'
            f'把體檢數字變成日常健康行動計劃。低轉化率代表這條路徑尚未打通。\n\n'
            f'Expected Change: 每份有異常項目的報告至少自動建議 1 個行動；'
            f'使用者從報告詳情頁可以一鍵採納建議行動；轉化率在 4 週後提升至 40%。\n\n'
            f'Objective: 為有異常指標的健檢報告加入「建議行動」區塊和一鍵採納功能。\n\n'
            f'Phase 1: 在報告詳情頁（frontend/app/platform/documents/）'
            f'新增「建議健康行動」區塊，顯示基於異常指標自動產生的行動建議。\n'
            f'Phase 2: 確保 health_assistant_service.py 的 get_action_recommendations() '
            f'正確把 lab_report_items 的異常項目納入推薦候選。\n'
            f'Phase 3: 增加「一鍵加入行動計劃」功能，'
            f'點擊後創建 source_type=lab_report 的 HealthAction。\n'
            f'Phase 4: 測試端對端流程：上傳報告 → 解析異常 → 顯示建議 → 採納行動。\n\n'
            f'Scope: frontend/app/platform/documents/, '
            f'backend/app/api/health_assistant.py, backend/app/services/health_assistant_service.py\n'
            f'Acceptance Criteria: 報告詳情頁顯示基於異常指標的行動建議；'
            f'一鍵採納功能可用；make backend-test 通過；npm run build 通過。\n'
            f'focus_keys: document_action_bridge, lab_report, abnormal_items\n'
            f'expected_duration_minutes: 480'
        )

    if issue_type == 'no_outcome_tracking':
        data = issue['signal_data']
        completed = data.get('completed_actions', 0)
        title = f'{title_prefix}建立健康結果追蹤 — {completed} 個完成行動無結果記錄'
        return (
            f'{title}\n\n'
            f'User Value: 使用者已完成 {completed} 個健康行動，'
            f'但沒有一個行動記錄了後續的健康指標變化。'
            f'使用者不知道自己的努力是否有效，難以維持長期動力。\n\n'
            f'Product Maturity Impact: ActionOutcome 追蹤是「健康改善閉環」的最後一塊：'
            f'行動 → 執行 → 可見的健康改善。缺少這個環節讓系統停留在任務管理工具而非健康教練。\n\n'
            f'Expected Change: 完成行動 7 天後自動提示「記錄改善結果」；'
            f'在行動詳情頁顯示 before/after 健康指標對比；ActionOutcome 在 UI 中可見。\n\n'
            f'Objective: 打通行動→結果追蹤的完整流程。\n\n'
            f'Phase 1: 檢查 ActionOutcome 模型和 API 是否完整，確保前端可以提交結果。\n'
            f'Phase 2: 在行動完成後的 UI 流程加入「記錄改善效果」步驟，'
            f'讓使用者輸入最新健康指標數值。\n'
            f'Phase 3: 在行動卡片或詳情頁顯示 before/after 對比（若有 outcome 資料）。\n'
            f'Phase 4: 確認 health_assistant_service.py 的 build_product_signals() '
            f'正確計算 outcome_improvement_rate。\n\n'
            f'Scope: frontend/app/platform/actions/, backend/app/api/actions.py, '
            f'backend/app/models/entities.py\n'
            f'Acceptance Criteria: 使用者可以在完成行動後記錄健康指標；'
            f'行動詳情頁顯示改善對比；make backend-test 通過；npm run build 通過。\n'
            f'focus_keys: outcome_tracking, behavior_loop, health_improvement\n'
            f'expected_duration_minutes: 360'
        )

    # Generic fallback for unknown issue types
    title = f'{title_prefix}{issue["title"]}'
    return (
        f'{title}\n\n'
        f'User Value: {issue["description"]}\n\n'
        f'Product Maturity Impact: Addressing this systemic issue unblocks forward product progress '
        f'and prevents the orchestrator from cycling through exhausted work.\n\n'
        f'Expected Change: The detected issue is resolved and the orchestrator generates '
        f'meaningful new work in subsequent cycles.\n\n'
        f'Objective: Investigate and resolve: {issue["description"]}\n\n'
        f'Phase 1: Analyse the signal data: {issue["signal_data"]}.\n'
        f'Phase 2: Determine root cause and design a targeted fix.\n'
        f'Phase 3: Implement the fix with the smallest safe change set.\n'
        f'Phase 4: Verify with make backend-test.\n\n'
        f'Scope: backend/app/orchestrator/\n'
        f'Acceptance Criteria: Issue resolved; make backend-test passes.\n'
        f'focus_keys: orchestrator, product_health, signal_detection\n'
        f'expected_duration_minutes: 240'
    )
