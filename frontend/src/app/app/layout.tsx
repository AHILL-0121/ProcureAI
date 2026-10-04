'use client';

import { useEffect, useState, type ReactNode } from 'react';
import { usePathname, useRouter } from 'next/navigation';
import { CommandPalette } from '@/components/shell/CommandPalette';
import { DropAnywhere } from '@/components/shell/DropAnywhere';
import { MobileBar } from '@/components/shell/MobileBar';
import { ProcessingTray } from '@/components/shell/ProcessingTray';
import { Sidebar } from '@/components/shell/Sidebar';
import { TopBar } from '@/components/shell/TopBar';
import { StampLogo } from '@/components/Logo';
import { useAuth } from '@/lib/auth';
import { RealtimeProvider } from '@/lib/realtime';

export default function AppLayout({ children }: { children: ReactNode }) {
  const { user, ready } = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  const [palette, setPalette] = useState(false);

  useEffect(() => {
    if (ready && !user) router.replace(`/login?next=${encodeURIComponent(pathname)}`);
  }, [ready, user, router, pathname]);

  if (!ready || !user) {
    return (
      <div className="boot" aria-busy="true">
        <StampLogo size={56} className="boot__logo" />
        <span className="label">Opening the ledger…</span>
      </div>
    );
  }

  return (
    <RealtimeProvider enabled>
      <a href="#main" className="skip">Skip to content</a>
      <div className="shell">
        <Sidebar />
        <div className="main">
          <TopBar onSearch={() => setPalette(true)} />
          <main id="main" className="page" key={pathname}>
            {children}
          </main>
        </div>
      </div>
      <ProcessingTray />
      <MobileBar />
      <DropAnywhere />
      <CommandPalette open={palette} onOpenChange={setPalette} />
    </RealtimeProvider>
  );
}
