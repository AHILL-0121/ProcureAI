'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useRef } from 'react';
import { GearSix, Plus } from '@phosphor-icons/react';
import { useAuth } from '@/lib/auth';
import { can } from '@/lib/format';
import { ACCEPT, useUpload } from '@/lib/hooks';
import { NAV } from './Sidebar';

export function MobileBar() {
  const pathname = usePathname();
  const { user } = useAuth();
  const { send } = useUpload();
  const input = useRef<HTMLInputElement>(null);
  const [tray, overview, invoices] = NAV;
  const Item = ({ it }: { it: (typeof NAV)[number] }) => {
    const Icon = it.icon;
    const active = it.match(pathname);
    return (
      <Link href={it.href} aria-current={active ? 'page' : undefined}>
        <Icon size={20} weight={active ? 'bold' : 'regular'} aria-hidden />
        {it.label}
      </Link>
    );
  };
  return (
    <nav className="bbar" aria-label="Main navigation">
      <Item it={tray} />
      <Item it={overview} />
      {can.edit(user?.role) ? (
        <button type="button" className="bbar__add" onClick={() => input.current?.click()} aria-label="Add invoices">
          <Plus size={22} weight="bold" aria-hidden />
          <input ref={input} type="file" accept={ACCEPT} multiple hidden onChange={(e) => {
            const files = Array.from(e.target.files ?? []);
            e.target.value = '';
            if (files.length) send(files);
          }} />
        </button>
      ) : <span />}
      <Item it={invoices} />
      <Link href="/app/settings" aria-current={pathname.startsWith('/app/settings') ? 'page' : undefined}>
        <GearSix size={20} aria-hidden />
        More
      </Link>
    </nav>
  );
}
