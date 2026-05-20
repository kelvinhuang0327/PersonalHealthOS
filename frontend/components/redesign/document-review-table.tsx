import { ChangeEvent } from 'react';
import { Badge } from '../../app/components/ui/badge';
import { Card } from '../../app/components/ui/card';

export type ReviewItem = {
  item_name?: string;
  value_num?: number | string | null;
  unit?: string | null;
  ref_range?: string | null;
  abnormal_flag?: string | null;
  note?: string | null;
};

const abnormalMap: Record<string, { label: string; className: string }> = {
  H: { label: '偏高', className: 'bg-rose-100 text-rose-700' },
  L: { label: '偏低', className: 'bg-amber-100 text-amber-700' },
  N: { label: '正常', className: 'bg-emerald-100 text-emerald-700' },
};

export function DocumentReviewTable({
  items,
  editable = false,
  onChange,
}: {
  items: ReviewItem[];
  editable?: boolean;
  onChange?: (index: number, next: ReviewItem) => void;
}) {
  const updateField =
    (index: number, field: keyof ReviewItem) =>
    (event: ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
      if (!onChange) return;
      onChange(index, {
        ...items[index],
        [field]: field === 'value_num' ? event.target.value : event.target.value,
      });
    };

  return (
    <Card className="overflow-hidden rounded-[24px] p-0">
      <div className="overflow-x-auto">
        <table className="min-w-full border-collapse">
          <thead className="bg-slate-50 text-left text-xs uppercase tracking-[0.14em] text-slate-500">
            <tr>
              <th className="px-4 py-4 font-semibold">檢驗項目</th>
              <th className="px-4 py-4 font-semibold">數值</th>
              <th className="px-4 py-4 font-semibold">單位</th>
              <th className="px-4 py-4 font-semibold">參考區間</th>
              <th className="px-4 py-4 font-semibold">異常標記</th>
              <th className="px-4 py-4 font-semibold">備註</th>
            </tr>
          </thead>
          <tbody>
            {items.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-4 py-12 text-center text-sm text-slate-500">
                  尚未解析出可確認的欄位。
                </td>
              </tr>
            ) : null}
            {items.map((item, index) => {
              const abnormal = abnormalMap[String(item.abnormal_flag || '').toUpperCase()];
              return (
                <tr key={`${item.item_name || 'item'}-${index}`} className="border-t border-slate-100 align-top">
                  <td className="px-4 py-4 text-sm font-semibold text-slate-900">
                    {editable ? (
                      <input value={item.item_name || ''} onChange={updateField(index, 'item_name')} />
                    ) : (
                      item.item_name || '-'
                    )}
                  </td>
                  <td className="px-4 py-4 text-sm text-slate-700">
                    {editable ? (
                      <input value={item.value_num ?? ''} onChange={updateField(index, 'value_num')} />
                    ) : (
                      item.value_num ?? '-'
                    )}
                  </td>
                  <td className="px-4 py-4 text-sm text-slate-700">
                    {editable ? <input value={item.unit || ''} onChange={updateField(index, 'unit')} /> : item.unit || '-'}
                  </td>
                  <td className="px-4 py-4 text-sm text-slate-700">
                    {editable ? (
                      <input value={item.ref_range || ''} onChange={updateField(index, 'ref_range')} />
                    ) : (
                      item.ref_range || '-'
                    )}
                  </td>
                  <td className="px-4 py-4 text-sm">
                    {editable ? (
                      <select value={item.abnormal_flag || ''} onChange={updateField(index, 'abnormal_flag')}>
                        <option value="">未標記</option>
                        <option value="N">正常</option>
                        <option value="H">偏高</option>
                        <option value="L">偏低</option>
                      </select>
                    ) : abnormal ? (
                      <Badge className={abnormal.className}>{abnormal.label}</Badge>
                    ) : (
                      <span className="text-slate-400">未標記</span>
                    )}
                  </td>
                  <td className="px-4 py-4 text-sm text-slate-600">{item.note || '待人工確認後寫入長期資料。'}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </Card>
  );
}
