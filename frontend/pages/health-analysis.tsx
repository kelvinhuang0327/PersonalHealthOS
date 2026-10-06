import { useEffect, useState } from 'react';
import { Layout } from '../components/Layout';
import { api } from '../lib/api';

export default function HealthAnalysisPage() {
  const [data, setData] = useState<any>(null);

  useEffect(() => {
    api.getHealthAnalysis().then(setData).catch(() => setData(null));
  }, []);

  return (
    <Layout>
      <div className="card">
        <h1>健康分析</h1>
        {!data?.data_sufficient && <p>資料不足：請補充症狀、健檢或身體指數後再分析。</p>}
        <h3>異常指標</h3>
        <pre>{JSON.stringify(data?.abnormal_indicators || [], null, 2)}</pre>
        <h3>可能健康風險</h3>
        <pre>{JSON.stringify(data?.potential_risks || [], null, 2)}</pre>
        <h3>長期症狀</h3>
        <pre>{JSON.stringify(data?.long_term_symptoms || [], null, 2)}</pre>
        <h3>需要追蹤項目</h3>
        <pre>{JSON.stringify(data?.follow_up_items || [], null, 2)}</pre>
        <h3>健康建議</h3>
        <pre>{JSON.stringify(data?.recommendations || [], null, 2)}</pre>
        <p>醫療免責聲明：{data?.disclaimer || '本平台僅供健康資訊參考，非醫療診斷。'}</p>
      </div>
    </Layout>
  );
}
