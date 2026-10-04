import type { Metadata, Viewport } from 'next';
import { Caveat, IBM_Plex_Mono, IBM_Plex_Sans, IBM_Plex_Sans_Condensed, Libre_Caslon_Display } from 'next/font/google';
import { InkDefs } from '@/components/ui';
import { Providers } from './providers';
import '@/styles/tokens.css';
import '@/styles/base.css';
import '@/styles/app.css';
import '@/styles/screens.css';
import '@/styles/landing.css';

const caslon = Libre_Caslon_Display({ weight: '400', subsets: ['latin'], variable: '--font-caslon', display: 'swap' });
const plex = IBM_Plex_Sans({ weight: ['400', '500', '600'], subsets: ['latin'], variable: '--font-plex', display: 'swap' });
const plexCond = IBM_Plex_Sans_Condensed({ weight: ['500', '600', '700'], subsets: ['latin'], variable: '--font-plex-cond', display: 'swap' });
const plexMono = IBM_Plex_Mono({ weight: ['400', '500', '600'], subsets: ['latin'], variable: '--font-plex-mono', display: 'swap' });
const caveat = Caveat({ weight: ['500', '600'], subsets: ['latin'], variable: '--font-caveat', display: 'swap' });

export const metadata: Metadata = {
  title: { default: 'ProcureAI', template: '%s · ProcureAI' },
  description: 'Three copies, one stamp. Automated three-way invoice matching with a human in-tray for exceptions.',
  icons: { icon: '/favicon.svg' },
};

export const viewport: Viewport = { themeColor: '#ECE9E1', colorScheme: 'light' };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" data-fx="full" className={`${caslon.variable} ${plex.variable} ${plexCond.variable} ${plexMono.variable} ${caveat.variable}`}>
      <body>
        <InkDefs />
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
