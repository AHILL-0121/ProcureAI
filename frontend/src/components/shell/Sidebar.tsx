'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { motion } from 'motion/react';
import { ChartLine, Files, GearSix, Package, SidebarSimple, Tray } from '@phosphor-icons/react';
import { StampLogo } from '@/components/Logo';
import { useAuth } from '@/lib/auth';
import { roleLabel } from '@/lib/format';
import { useHotkeys, useReviewCount } from '@/lib/hooks';
import { usePrefs } from '@/lib/prefs';

export const NAV = [
  { href: '/app/in-tray', label: 'In-tray', icon: Tray, match: (p: string) => p.startsWith('/app/in-tray') },
  { href: '/app', label: 'Overview', icon: ChartLine, match: (p: string) => p === '/app' },
  { href: '/app/invoices', label: 'Invoices', icon: Files, match: (p: string) => p.startsWith('/app/invoices') },
  { href: '/app/purchase-orders', label: 'Purchase orders', icon: Package, match: (p: string) => p.startsWith('/app/purchase-orders') },
];

export function Sidebar() {
  const pathname = usePathname();
  const { user, signOut } = useAuth();
  const { fx, sidebar, toggleSidebar } = usePrefs();
  const { data: count } = useReviewCount(!!user);
  const closed = sidebar === 'closed';
  useHotkeys({ '[': () => toggleSidebar() }, [toggleSidebar]);

  const items = [...NAV, { href: '/app/settings', label: 'Settings', icon: GearSix, match: (p: string) => p.startsWith('/app/settings') }];

  return (
    <aside className="side" aria-label="Main navigation">
      <div className="side__top">
        <Link href="/app/in-tray" className="brand" aria-label="ProcureAI, go to the in-tray">
          <StampLogo size={closed ? 30 : 40} />
          <b className="display">ProcureAI</b>
        </Link>
        <button
          type="button"
          className="side__toggle"
          onClick={toggleSidebar}
          aria-expanded={!closed}
          aria-label={closed ? 'Open the sidebar' : 'Close the sidebar'}
          title={closed ? 'Open the sidebar ( [ )' : 'Close the sidebar ( [ )'}
        >
          <SidebarSimple size={18} weight={closed ? 'regular' : 'bold'} aria-hidden />
        </button>
      </div>
      <nav className="tabs">
        {items.map((it, i) => {
          const active = it.match(pathname);
          const Icon = it.icon;
          return (
            <Link key={it.href} href={it.href} className={`tab ${active ? 'is-active' : ''} ${i === 4 ? 'tab--sep' : ''}`} aria-current={active ? 'page' : undefined}
              title={closed ? it.label : undefined} aria-label={closed ? it.label : undefined}>
              {active && (
                <motion.span
                  layoutId="tab-active"
                  className="tab__paper"
                  transition={fx === 'off' ? { duration: 0 } : { type: 'spring', stiffness: 260, damping: 28 }}
                />
              )}
              <Icon size={18} weight={active ? 'bold' : 'regular'} aria-hidden />
              <span className="tab__label">{it.label}</span>
              {it.href === '/app/in-tray' && !!count && <span className="tab__count num">{count}</span>}
            </Link>
          );
        })}
      </nav>
      {user && (
        <div className="who">
          <strong title={closed ? `${user.name} · ${roleLabel(user.role)}` : undefined}>{closed ? user.name.slice(0, 1) : user.name}</strong>
          <span className="who__role">{roleLabel(user.role)}</span>
          {!closed && <button type="button" className="linkish" onClick={signOut}>Sign out</button>}
        </div>
      )}
    </aside>
  );
}
