import { FormEvent, useState } from 'react';
import { useRouter } from 'next/router';
import { api } from '../lib/api';

const DEFAULT_EMAIL = 'demo.default@example.com';
const DEFAULT_PASSWORD = 'Demo12345';

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState(DEFAULT_EMAIL);
  const [password, setPassword] = useState(DEFAULT_PASSWORD);
  const [error, setError] = useState('');

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    try {
      let res;
      try {
        res = await api.login(email, password);
      } catch {
        // 開發模式快速登入：若帳號不存在，先建立再登入。
        await api.register(email, password);
        res = await api.login(email, password);
      }
      localStorage.setItem('token', res.access_token);
      router.push('/platform/dashboard');
    } catch (err: any) {
      setError(err.message || '登入失敗');
    }
  };

  return (
    <div className="container">
      <div className="card">
        <h1>登入</h1>
        <form onSubmit={onSubmit}>
          <input placeholder="電子郵件" value={email} onChange={(e) => setEmail(e.target.value)} />
          <input
            placeholder="密碼"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
          <button type="submit">登入</button>
        </form>
        <p>已預先填入預設帳號，方便快速開始。</p>
        {error && <p style={{ color: 'red' }}>{error}</p>}
        <button className="secondary" onClick={() => router.push('/register')}>
          建立帳號
        </button>
      </div>
    </div>
  );
}
