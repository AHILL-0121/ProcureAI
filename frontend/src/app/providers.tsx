'use client';

import { useState, type ReactNode } from 'react';
import { MotionConfig } from 'motion/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { WakeSlip } from '@/components/WakeSlip';
import { AuthProvider } from '@/lib/auth';
import { PrefsProvider, usePrefs } from '@/lib/prefs';
import { ToastProvider } from '@/lib/toast';

function Motion({ children }: { children: ReactNode }) {
  const { fx } = usePrefs();
  return <MotionConfig reducedMotion={fx === 'off' ? 'always' : 'user'}>{children}</MotionConfig>;
}

export function Providers({ children }: { children: ReactNode }) {
  const [client] = useState(() => new QueryClient({
    defaultOptions: {
      queries: { staleTime: 15_000, retry: 1, refetchOnWindowFocus: false },
    },
  }));
  return (
    <QueryClientProvider client={client}>
      <PrefsProvider>
        <Motion>
          <ToastProvider>
            <AuthProvider>{children}</AuthProvider>
            <WakeSlip />
          </ToastProvider>
        </Motion>
      </PrefsProvider>
    </QueryClientProvider>
  );
}
