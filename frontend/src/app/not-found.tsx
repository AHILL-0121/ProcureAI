import Link from 'next/link';

export default function NotFound() {
  return (
    <div className="login-desk">
      <div className="sheet login">
        <p className="label">Error 404</p>
        <h1 className="display">This page is not in the ledger.</h1>
        <p className="muted">The link may be old, or the invoice was removed.</p>
        <Link href="/app/in-tray" className="key key--primary">Back to the in-tray</Link>
      </div>
    </div>
  );
}
