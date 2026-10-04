'use client';

import { Suspense, useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { StampLogo } from '@/components/Logo';
import { Key } from '@/components/ui';
import { useAuth } from '@/lib/auth';
import { wakeServer } from '@/lib/wake';

function LoginForm() {
  const { user, signIn, ready } = useAuth();
  const router = useRouter();
  const params = useSearchParams();
  const next = params.get('next') || '/app/in-tray';
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (ready && user) router.replace(next.startsWith('/app') ? next : '/app/in-tray');
  }, [ready, user, router, next]);

  useEffect(() => {
    void wakeServer();
  }, []);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      // On a cold start, wait for the server instead of failing the first attempt
      if (!(await wakeServer())) throw new Error('The server is not answering. Try again in a minute.');
      await signIn(email, password);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Sign-in failed');
    } finally {
      setBusy(false);
    }
  };

  return (
    <form className="login sheet" onSubmit={submit}>
      <div className="login__head">
        <StampLogo size={64} />
        <div>
          <p className="label">Accounts payable</p>
          <h1 className="display">Sign in to the ledger</h1>
        </div>
      </div>
      <div className="form-field">
        <label className="label" htmlFor="email">Email</label>
        <input id="email" type="email" autoComplete="username" value={email} onChange={(e) => setEmail(e.target.value)} required />
      </div>
      <div className="form-field">
        <label className="label" htmlFor="password">Password</label>
        <input id="password" type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} required />
      </div>
      {error && <p className="field-error" role="alert">{error}</p>}
      <Key type="submit" variant="primary" busy={busy} className="login__submit">Open the in-tray</Key>
      <p className="login__foot muted">
        First run in development? The server creates <span className="num">admin@procureai.local</span> with the password
        shown in its log. <Link href="/">About ProcureAI</Link>
      </p>
    </form>
  );
}

export default function LoginPage() {
  return (
    <div className="login-desk">
      <Suspense>
        <LoginForm />
      </Suspense>
    </div>
  );
}
