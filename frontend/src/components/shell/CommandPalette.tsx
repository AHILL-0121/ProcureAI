'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Command } from 'cmdk';
import * as Dialog from '@radix-ui/react-dialog';
import { useQuery } from '@tanstack/react-query';
import { get, qs } from '@/lib/api';
import { money } from '@/lib/format';
import { useDebounced } from '@/lib/hooks';
import { usePrefs } from '@/lib/prefs';
import type { InvoiceSummary, Page, POSummary } from '@/lib/types';

export function CommandPalette({ open, onOpenChange }: { open: boolean; onOpenChange: (v: boolean) => void }) {
  const router = useRouter();
  const [q, setQ] = useState('');
  const term = useDebounced(q.trim(), 200);
  const { setFx, setDensity, density } = usePrefs();

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        onOpenChange(!open);
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open, onOpenChange]);

  const invoices = useQuery({
    queryKey: ['palette', 'inv', term],
    queryFn: () => get<Page<InvoiceSummary>>(`/invoices${qs({ search: term, page_size: 6 })}`),
    enabled: open && term.length >= 2,
  });
  const pos = useQuery({
    queryKey: ['palette', 'po', term],
    queryFn: () => get<{ items: POSummary[] }>(`/purchase-orders${qs({ q: term, page_size: 5 })}`),
    enabled: open && term.length >= 2,
  });

  const go = (href: string) => {
    onOpenChange(false);
    setQ('');
    router.push(href);
  };

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="overlay" />
        <Dialog.Content className="palette" aria-describedby={undefined}>
          <Dialog.Title className="sr-only">Search and commands</Dialog.Title>
          <Command label="Search and commands" shouldFilter={false}>
            <div className="palette__tab label">Index</div>
            <Command.Input value={q} onValueChange={setQ} placeholder="Invoice number, PO, vendor, or a command…" autoFocus />
            <Command.List>
              <Command.Empty>{term.length < 2 ? 'Type at least two characters.' : 'Nothing found.'}</Command.Empty>
              {term.length < 2 && (
                <Command.Group heading="Go to">
                  <Command.Item onSelect={() => go('/app/in-tray')}>In-tray</Command.Item>
                  <Command.Item onSelect={() => go('/app')}>Overview</Command.Item>
                  <Command.Item onSelect={() => go('/app/invoices')}>All invoices</Command.Item>
                  <Command.Item onSelect={() => go('/app/purchase-orders')}>Purchase orders</Command.Item>
                  <Command.Item onSelect={() => go('/app/settings')}>Settings</Command.Item>
                </Command.Group>
              )}
              {term.length < 2 && (
                <Command.Group heading="Preferences">
                  <Command.Item onSelect={() => { setFx('full'); onOpenChange(false); }}>Paper effects: full</Command.Item>
                  <Command.Item onSelect={() => { setFx('subtle'); onOpenChange(false); }}>Paper effects: subtle</Command.Item>
                  <Command.Item onSelect={() => { setFx('off'); onOpenChange(false); }}>Paper effects: off</Command.Item>
                  <Command.Item onSelect={() => { setDensity(density === 'ledger' ? 'comfortable' : 'ledger'); onOpenChange(false); }}>
                    Row density: {density === 'ledger' ? 'comfortable' : 'ledger (compact)'}
                  </Command.Item>
                </Command.Group>
              )}
              {!!invoices.data?.items.length && (
                <Command.Group heading="Invoices">
                  {invoices.data.items.map((i) => (
                    <Command.Item key={i.id} value={i.id} onSelect={() => go(`/app/invoices/${i.id}`)}>
                      <span className="num">{i.invoice_number || i.original_filename}</span>
                      <span className="muted">{i.vendor_name}</span>
                      <span className="num palette__amt">{money(i.total_amount, i.currency)}</span>
                    </Command.Item>
                  ))}
                </Command.Group>
              )}
              {!!pos.data?.items.length && (
                <Command.Group heading="Purchase orders">
                  {pos.data.items.map((p) => (
                    <Command.Item key={p.po_number} value={p.po_number} onSelect={() => go(`/app/purchase-orders/${p.po_number}`)}>
                      <span className="num">{p.po_number}</span>
                      <span className="muted">{p.vendor_name}</span>
                      <span className="num palette__amt">{money(p.total_amount, p.currency)}</span>
                    </Command.Item>
                  ))}
                </Command.Group>
              )}
            </Command.List>
          </Command>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
