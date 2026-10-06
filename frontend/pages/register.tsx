import { FormEvent, useState } from 'react';
import { useRouter } from 'next/router';
import { api } from '../lib/api';

export default function RegisterPage() {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    try {
      await api.register(email, password);
      router.push('/login');
    } catch (err: any) {
      setError(err.message || '註冊失敗');
    }
  };

  return (
    <div className="container">
      <div className="card">
        <h1>建立帳號</h1>
        <form onSubmit={onSubmit}>
          <input placeholder="電子郵件" value={email} onChange={(e) => setEmail(e.target.value)} />
          <input
            placeholder="密碼（至少 8 碼）"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
          <button type="submit">建立帳號</button>
        </form>
        {error && <p style={{ color: 'red' }}>{error}</p>}
      </div>
    </div>
  );
}
