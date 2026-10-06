import { Badge } from '../../app/components/ui/badge';
import { Card } from '../../app/components/ui/card';
import { ExplainabilityPanel } from '../../app/components/platform/explainability-panel';

export function HistoryTimeline({ items }: { items: any[] }) {
  if (!items.length) {
    return (
      <Card className="rounded-[24px] p-8 text-sm text-slate-500">
        目前尚無可呈現的歷史事件。先新增症狀、身體指標或上傳健檢報告，系統才會形成可分析的時間軸。
      </Card>
    );
  }

  return (
    <div className="relative space-y-4 border-l border-slate-200 pl-5">
      {items.map((item, index) => (
        <div key={`${item.type || item.event_type}-${index}`} className="relative">
          <span className="absolute -left-[29px] top-7 h-3.5 w-3.5 rounded-full border-4 border-white bg-cyan-500 shadow-sm" />
          <Card className="rounded-[24px] p-5">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div>
                <p className="font-semibold text-slate-900">{item.title || item.label || '未命名事件'}</p>
                <p className="mt-1 text-xs text-slate-500">
                  {item.start_date || item.event_time || '-'}
                  {item.end_date ? ` ~ ${item.end_date}` : ''}
                </p>
              </div>
              <Badge className="bg-slate-100 text-slate-700">{item.type || item.event_type || 'event'}</Badge>
            </div>
            <p className="mt-3 text-sm leading-6 text-slate-700">{item.description || '此事件目前沒有補充說明。'}</p>
            {item.temporal_type ? <p className="mt-2 text-xs uppercase tracking-[0.14em] text-slate-400">{item.temporal_type}</p> : null}
            {(item.type === 'insight' || item.type === 'alert') ? (
              <ExplainabilityPanel
                explain={{
                  rule_id: item?.data?.rule_id || item?.rule_id,
                  category: item?.data?.category || item?.category || item.type,
                  priority: item?.data?.priority || item?.priority,
                  confidence: item?.data?.confidence || item?.confidence,
                  evidence_level: item?.data?.evidence_level || item?.evidence_level,
                  guideline_source: item?.data?.guideline_source || item?.guideline_source,
                }}
              />
            ) : null}
          </Card>
        </div>
      ))}
    </div>
  );
}
