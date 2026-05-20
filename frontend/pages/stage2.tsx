import Link from 'next/link';

import { Layout } from '../components/Layout';

export default function Stage2HubPage() {
  return (
    <Layout>
      <div className="card">
        <h1>Stage 2 Health Intelligence</h1>
        <p>選擇功能：</p>
        <div className="grid">
          <Link href="/timeline">健康時間軸</Link>
          <Link href="/trends">健康趨勢分析</Link>
          <Link href="/health-score">健康分數</Link>
        </div>
      </div>
    </Layout>
  );
}
