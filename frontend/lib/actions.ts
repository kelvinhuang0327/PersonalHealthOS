export type HealthAction = {
  id: string;
  person_id: string;
  source_type: 'insight' | 'alert' | 'recommendation';
  source_id: string;
  title: string;
  description: string;
  action_type: 'monitor' | 'habit' | 'follow_up' | 'lifestyle';
  priority: 'low' | 'medium' | 'high';
  status: 'todo' | 'in_progress' | 'done' | 'snoozed';
  due_date?: string;
  frequency?: 'daily' | 'weekly' | 'monthly';
  streak?: number;
  streak_count?: number;  // backend field name alias
  last_completed_at?: string;
  impact_status?: 'improved' | 'no_change' | 'worse';
  reminder_status?: 'none' | 'overdue' | 'risk_up' | 'no_data' | 'streak_break';
  snoozed_until?: string;
  snoozed_at?: string;
  snooze_reason?: string;
  resurface_count?: number;
  confidence?: number;
  evidence_level?: 'A' | 'B' | 'C';
  guideline_source?: string;
  rule_id?: string;
  category?: string;
  created_at: string;
  completed_at?: string;
};

export type ActionImpactMeta = {
  label: string;
  badgeClass: string;
  summary: string;
  tone: 'positive' | 'neutral' | 'warning';
};

export type ActionReminderMeta = {
  label: string;
  badgeClass: string;
  summary: string;
};

function normalizePriority(source: Record<string, unknown>) {
  const numericPriority = Number(source.priority);
  if (Number.isFinite(numericPriority)) return numericPriority;
  const severity = String(source.severity || '').toLowerCase();
  if (severity === 'high' || severity === 'warning') return 9;
  return 5;
}

function resolveActionFrequency(sourceType: HealthAction['source_type'], source: Record<string, unknown>): HealthAction['frequency'] {
  const category = String(source.category || '').toLowerCase();
  if (category.includes('sleep') || category.includes('weight') || category.includes('habit') || category.includes('lifestyle')) {
    return 'daily';
  }
  if (sourceType === 'recommendation') return 'daily';
  return 'weekly';
}

export function buildActionFromSource(
  personId: string,
  sourceType: HealthAction['source_type'],
  source: Record<string, unknown>,
  status: HealthAction['status'] = 'todo'
): HealthAction {
  const now = new Date();
  const fallbackTitle = sourceType === 'insight' ? 'Insight follow-up' : sourceType === 'alert' ? 'Risk alert action' : 'Recommendation action';
  const rawTitle =
    String(source.title || '').trim() ||
    String(source.recommendation || '').trim() ||
    String(source.text || '').trim() ||
    fallbackTitle;
  const text = String(source.recommendation || source.description || source.summary || source.text || source.title || fallbackTitle);
  const actionType = sourceType === 'alert' ? 'monitor' : sourceType === 'recommendation' ? 'lifestyle' : 'follow_up';
  const priorityValue = normalizePriority(source);
  return {
    id: `act_${now.getTime()}_${Math.random().toString(36).slice(2, 8)}`,
    person_id: personId,
    source_type: sourceType,
    source_id: String(source.id || source.rule_id || now.getTime()),
    title: rawTitle,
    description: text,
    action_type: actionType,
    priority: priorityValue >= 9 ? 'high' : priorityValue >= 6 ? 'medium' : 'low',
    status,
    due_date: new Date(now.getTime() + 3 * 24 * 60 * 60 * 1000).toISOString(),
    frequency: resolveActionFrequency(sourceType, source),
    streak: 0,
    impact_status: 'no_change',
    reminder_status: 'none',
    confidence: typeof source.confidence === 'number' ? source.confidence : undefined,
    evidence_level: typeof source.evidence_level === 'string' ? (source.evidence_level as 'A' | 'B' | 'C') : undefined,
    guideline_source: typeof source.guideline_source === 'string' ? source.guideline_source : undefined,
    rule_id: typeof source.rule_id === 'string' ? source.rule_id : undefined,
    category: typeof source.category === 'string' ? source.category : undefined,
    created_at: now.toISOString(),
  };
}

export function evaluateImpactStatus(action: HealthAction): HealthAction['impact_status'] {
  const streak = action.streak || 0;
  const ageMs = Date.now() - new Date(action.created_at).getTime();
  const twoDaysMs = 2 * 24 * 60 * 60 * 1000;
  if (action.status === 'done' && (streak >= 4 || (action.priority === 'high' && streak >= 2))) return 'improved';
  if (action.status === 'done') return 'no_change';
  if (action.priority === 'high' && ageMs >= twoDaysMs) return 'worse';
  if (action.reminder_status === 'overdue' || action.reminder_status === 'risk_up') return 'worse';
  return 'no_change';
}

export function evaluateReminderStatus(action: HealthAction): HealthAction['reminder_status'] {
  const ageMs = Date.now() - new Date(action.created_at).getTime();
  const sinceLastCompletedMs = action.last_completed_at ? Date.now() - new Date(action.last_completed_at).getTime() : ageMs;
  const threeDaysMs = 3 * 24 * 60 * 60 * 1000;
  const oneDayMs = 24 * 60 * 60 * 1000;
  const dueDateMs = action.due_date ? new Date(action.due_date).getTime() : 0;
  if (action.frequency === 'daily' && (action.streak || 0) > 0 && sinceLastCompletedMs >= oneDayMs && action.status !== 'done') return 'streak_break';
  if ((action.status === 'todo' || action.status === 'in_progress') && dueDateMs && Date.now() >= dueDateMs) return 'overdue';
  if ((action.status === 'todo' || action.status === 'in_progress') && ageMs >= threeDaysMs) return 'overdue';
  if (action.priority === 'high' && action.status !== 'done') return 'risk_up';
  if (!action.last_completed_at && action.status !== 'done' && ageMs >= 2 * 24 * 60 * 60 * 1000) return 'no_data';
  return 'none';
}

export function getActionImpactMeta(impactStatus: HealthAction['impact_status']): ActionImpactMeta {
  if (impactStatus === 'improved') {
    return {
      label: '你正在變好',
      badgeClass: 'bg-emerald-100 text-emerald-700',
      summary: '這項行動已出現正向回饋，請維持目前節奏。',
      tone: 'positive',
    };
  }
  if (impactStatus === 'worse') {
    return {
      label: '風險沒有下降',
      badgeClass: 'bg-rose-100 text-rose-700',
      summary: '這項任務還沒有帶來改善，建議優先處理。',
      tone: 'warning',
    };
  }
  return {
    label: '還在觀察中',
    badgeClass: 'bg-slate-200 text-slate-700',
    summary: '目前資料還不足以判斷是否改善，持續記錄最重要。',
    tone: 'neutral',
  };
}

export function getActionReminderMeta(reminderStatus: HealthAction['reminder_status']): ActionReminderMeta | null {
  if (reminderStatus === 'overdue') {
    return {
      label: '已逾期',
      badgeClass: 'bg-amber-100 text-amber-700',
      summary: '這項行動已超過建議時間，越早補做越能避免風險累積。',
    };
  }
  if (reminderStatus === 'risk_up') {
    return {
      label: '風險上升',
      badgeClass: 'bg-rose-100 text-rose-700',
      summary: '目前風險高於一般追蹤任務，建議本週先處理這項。',
    };
  }
  if (reminderStatus === 'no_data') {
    return {
      label: '資料不足',
      badgeClass: 'bg-sky-100 text-sky-700',
      summary: '需要再完成幾次紀錄，系統才能判斷是否有效。',
    };
  }
  if (reminderStatus === 'streak_break') {
    return {
      label: '連續中斷',
      badgeClass: 'bg-violet-100 text-violet-700',
      summary: '原本的完成節奏被打斷了，現在補回最能守住改善效果。',
    };
  }
  return null;
}

export function getActionFeedbackTrend(action: HealthAction) {
  const streakBoost = Math.min((action.streak || 0) * 3, 12);
  const base =
    action.impact_status === 'improved'
      ? [46, 54, 61, 70, 82]
      : action.impact_status === 'worse'
      ? [84, 78, 73, 66, 58]
      : [64, 66, 65, 67, 68];
  return base.map((value, index) => {
    const reminderPenalty = action.reminder_status === 'overdue' && index >= 3 ? 8 : 0;
    return Math.max(18, Math.min(96, value + streakBoost - reminderPenalty));
  });
}

export function getActionFeedbackSummary(action: HealthAction) {
  const impact = getActionImpactMeta(action.impact_status);
  const reminder = getActionReminderMeta(action.reminder_status);

  if (action.impact_status === 'improved' && (action.streak || 0) > 0) {
    return `已連續完成 ${action.streak} 次，這個習慣開始產生正向回饋。`;
  }
  if (action.status === 'done') {
    return '這次行動已完成，系統會持續比對後續資料來判斷改善幅度。';
  }
  if (reminder) {
    return reminder.summary;
  }
  return impact.summary;
}

export function getActionExpectedEffect(action: HealthAction) {
  const category = String(action.category || '').toLowerCase();
  const actionType = action.action_type;

  if (actionType === 'monitor') {
    if (category.includes('blood') || category.includes('bp') || category.includes('pressure')) {
      return '幫你更早看出血壓是不是持續偏高。';
    }
    return '幫你更早發現風險有沒有持續累積。';
  }

  if (actionType === 'follow_up') {
    return '幫你確認這個問題是不是還在變化。';
  }

  if (actionType === 'habit' || actionType === 'lifestyle') {
    if (category.includes('sleep')) {
      return '幫你把睡眠拉回穩定，讓白天精神更好。';
    }
    if (category.includes('weight')) {
      return '幫你慢慢把體重與代謝壓回比較穩定的範圍。';
    }
    if (category.includes('uric') || category.includes('gout')) {
      return '幫你降低尿酸持續偏高帶來的發作風險。';
    }
    return '幫你把健康數據慢慢拉回穩定。';
  }

  return '幫你把這個風險從提醒變成可持續追蹤的改善。';
}
