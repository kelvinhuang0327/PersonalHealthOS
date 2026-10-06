import { useRouter } from 'next/router';
import { useEffect, useMemo, useState } from 'react';
import { AlertTriangle, CheckCircle2, FileBadge2, ShieldAlert } from 'lucide-react';
import { Badge } from '../app/components/ui/badge';
import { Button } from '../app/components/ui/button';
import { Card } from '../app/components/ui/card';
import { Layout } from '../components/Layout';
import { DocumentReviewTable, type ReviewItem } from '../components/redesign/document-review-table';
import { DocumentFlowStepper } from '../components/redesign/document-flow-stepper';
import { PageHeader } from '../components/redesign/page-header';
import { api } from '../lib/api';

function parseStoredRows(id: string) {
  try {
    const raw = sessionStorage.getItem(`parsed_edit_${id}`);
    if (!raw) return null;
    return JSON.parse(raw) as ReviewItem[];
  } catch {
    return null;
  }
}

export default function DocumentsConfirmationPage() {
  const router = useRouter();
  const { id } = router.query;
  const [doc, setDoc] = useState<any>(null);
  const [parsed, setParsed] = useState<any>(null);
  const [rows, setRows] = useState<ReviewItem[]>([]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!id || typeof id !== 'string') return;
    api.listDocuments().then((records: any[]) => setDoc(records.find((row) => row.id === id) || null));
    const raw = sessionStorage.getItem(`parsed_${id}`);
    if (!raw) return;
    const parsedData = JSON.parse(raw);
    setParsed(parsedData);
    const storedRows = parseStoredRows(id);
    if (storedRows) {
      setRows(storedRows);
      return;
    }
    setRows(
      (parsedData.parsed_items_preview || []).map((item: any) => ({
        item_name: item.item_name,
        value_num: item.value_num,
        unit: item.unit,
        ref_range: item.ref_range || item.reference_range || '',
        abnormal_flag: item.abnormal_flag || '',
        note: item.note || '',
      }))
    );
  }, [id]);

  useEffect(() => {
    if (!id || typeof id !== 'string' || rows.length === 0) return;
    sessionStorage.setItem(`parsed_edit_${id}`, JSON.stringify(rows));
  }, [id, rows]);

  const unresolvedCount = useMemo(
    () =>
      rows.filter((row) => {
        const missingName = !String(row.item_name || '').trim();
        const missingValue = row.value_num === '' || row.value_num == null;
        const missingUnit = !String(row.unit || '').trim();
        return missingName || missingValue || missingUnit;
      }).length,
    [rows]
  );
  const abnormalCount = useMemo(
    () => rows.filter((row) => ['H', 'L'].includes(String(row.abnormal_flag || '').toUpperCase())).length,
    [rows]
  );

  const updateRow = (index: number, next: ReviewItem) => {
    setRows((current) => current.map((row, rowIndex) => (rowIndex === index ? next : row)));
  };

  const confirmDocument = async () => {
    if (!id || typeof id !== 'string') return;
    setSaving(true);
    setError('');
    try {
      await api.confirmDocument(id, {
        confirmed_data: {
          report_id: parsed?.report_id,
          extracted_items: rows.length,
          abnormal_items: abnormalCount,
          unresolved_items: unresolvedCount,
          reviewed_at: new Date().toISOString(),
          items: rows,
        },
      });
      sessionStorage.removeItem(`parsed_edit_${id}`);
      await router.push('/documents');
    } catch (confirmError) {
      setError(confirmError instanceof Error ? confirmError.message : '確認失敗');
    } finally {
      setSaving(false);
    }
  };

  return (
    <Layout>
      <PageHeader
        label="報告 / 確認"
        title="健檢報告確認"
        description="這一步是把 AI 抽取結果轉成可信任資料的關鍵。請優先檢查異常值、缺單位欄位、與任何看起來不合理的參考區間。"
        aside={
          <Card className="rounded-[24px] border-amber-100 bg-amber-50/80 p-5 shadow-none">
            <p className="text-sm font-semibold text-amber-900">確認前檢查三件事</p>
            <ol className="mt-3 space-y-3 text-sm text-amber-950">
              <li>1. 檢驗名稱與數值是否被 OCR 誤讀</li>
              <li>2. 參考區間是否來自原始報告，而不是系統推定</li>
              <li>3. 異常標記是否真的與原始參考區間一致</li>
            </ol>
          </Card>
        }
      />

      <div className="mb-6">
        <DocumentFlowStepper
          currentStep={3}
          steps={[
            { key: 'upload', label: '上傳文件', description: '已完成文件上傳。' },
            { key: 'parse', label: 'AI 解析', description: '已抽取欄位，等待你確認。' },
            { key: 'confirm', label: '人工確認', description: '核對後寫入長期健康資料。' },
          ]}
        />
      </div>

      <div className="grid mb-6 gap-4 lg:grid-cols-4">
        <Card className="rounded-[24px] p-5">
          <div className="flex items-center gap-2 text-slate-500">
            <FileBadge2 className="h-4 w-4 text-cyan-700" />
            <span className="text-sm">抽取項目</span>
          </div>
          <p className="mt-3 font-['Figtree'] text-3xl font-semibold text-slate-950">{rows.length}</p>
        </Card>
        <Card className="rounded-[24px] p-5">
          <div className="flex items-center gap-2 text-slate-500">
            <ShieldAlert className="h-4 w-4 text-amber-600" />
            <span className="text-sm">異常標記</span>
          </div>
          <p className="mt-3 font-['Figtree'] text-3xl font-semibold text-slate-950">{abnormalCount}</p>
        </Card>
        <Card className="rounded-[24px] p-5">
          <div className="flex items-center gap-2 text-slate-500">
            <AlertTriangle className="h-4 w-4 text-rose-600" />
            <span className="text-sm">未完成欄位</span>
          </div>
          <p className="mt-3 font-['Figtree'] text-3xl font-semibold text-slate-950">{unresolvedCount}</p>
        </Card>
        <Card className="rounded-[24px] p-5">
          <div className="flex items-center gap-2 text-slate-500">
            <CheckCircle2 className="h-4 w-4 text-emerald-600" />
            <span className="text-sm">文件狀態</span>
          </div>
          <p className="mt-3 text-lg font-semibold text-slate-950">{doc?.parse_status || 'parsed'}</p>
        </Card>
      </div>

      <div className="support-grid mb-6">
        <div className="xl:col-span-8">
          <Card className="rounded-[28px] p-6">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="section-label">Review Table</p>
                <h3 className="mt-2 font-['Figtree'] text-2xl font-semibold">逐欄確認解析結果</h3>
              </div>
              <Badge className={abnormalCount > 0 ? 'bg-amber-100 text-amber-700' : 'bg-emerald-100 text-emerald-700'}>
                {abnormalCount > 0 ? `${abnormalCount} 項需留意` : '目前未標記異常'}
              </Badge>
            </div>
            <p className="mt-2 text-sm leading-6 text-slate-600">
              你可以直接修改檢驗項目名稱、數值、單位、參考區間與異常標記。確認後，系統才會把這些資料寫入時間軸與分析模型。
            </p>
            <div className="mt-5">
              <DocumentReviewTable items={rows} editable onChange={updateRow} />
            </div>
          </Card>
        </div>

        <div className="xl:col-span-4">
          <div className="sticky-rail space-y-4">
            <Card className="rounded-[28px] p-6">
              <p className="section-label">Document</p>
              <h3 className="mt-2 font-['Figtree'] text-2xl font-semibold">本次文件資訊</h3>
              <div className="mt-4 space-y-3 text-sm text-slate-700">
                <div className="rounded-2xl bg-slate-50 p-4">
                  <p className="text-xs uppercase tracking-[0.14em] text-slate-500">檔名</p>
                  <p className="mt-2 font-semibold text-slate-900">{doc?.original_filename || '-'}</p>
                </div>
                <div className="rounded-2xl bg-slate-50 p-4">
                  <p className="text-xs uppercase tracking-[0.14em] text-slate-500">上傳時間</p>
                  <p className="mt-2">{doc?.uploaded_at ? new Date(doc.uploaded_at).toLocaleString('zh-TW') : '-'}</p>
                </div>
                <div className="rounded-2xl bg-slate-50 p-4">
                  <p className="text-xs uppercase tracking-[0.14em] text-slate-500">報告識別</p>
                  <p className="mt-2">{parsed?.report_id || '-'}</p>
                </div>
              </div>
            </Card>

            <Card className="rounded-[28px] p-6">
              <p className="section-label">Write Policy</p>
              <h3 className="mt-2 font-['Figtree'] text-2xl font-semibold">確認後會發生什麼</h3>
              <ul className="mt-4 space-y-3 text-sm leading-7 text-slate-700">
                <li>1. 儲存結構化檢驗資料</li>
                <li>2. 更新健康時間軸與歷史比較</li>
                <li>3. 重新計算健康分數與風險提醒</li>
                <li>4. 重新生成摘要與建議追蹤項目</li>
              </ul>
              <div className="mt-4 rounded-2xl border border-emerald-200 bg-emerald-50 p-4">
                <p className="text-sm font-semibold text-emerald-900">現在只差最後一步</p>
                <p className="mt-1 text-sm leading-6 text-emerald-800">
                  如果欄位看起來都正確，按下確認後，這份報告就會正式進入你的健康故事與風險模型。
                </p>
              </div>
            </Card>

            {error ? <p className="rounded-2xl bg-rose-50 px-4 py-3 text-sm text-rose-700">{error}</p> : null}
            <div className="flex flex-col gap-3">
              <Button type="button" onClick={confirmDocument} disabled={saving}>
                {saving ? '確認中...' : '確認資料'}
              </Button>
              <button
                type="button"
                className="rounded-2xl border border-slate-200 px-4 py-3 text-sm font-semibold text-slate-700 transition hover:border-cyan-200 hover:text-cyan-900"
                onClick={() => router.push('/documents')}
              >
                返回文件列表
              </button>
            </div>
          </div>
        </div>
      </div>
    </Layout>
  );
}
