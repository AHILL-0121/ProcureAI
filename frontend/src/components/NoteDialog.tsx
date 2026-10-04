'use client';

import { useEffect, useState } from 'react';
import * as Dialog from '@radix-ui/react-dialog';
import { Key } from './ui';

/** A pencil-note dialog used to capture a reason (reject, override, hold). */
export function NoteDialog({ open, onOpenChange, title, description, confirmLabel, required = true, tone = 'plain', onConfirm }: {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  title: string;
  description?: string;
  confirmLabel: string;
  required?: boolean;
  tone?: 'plain' | 'danger' | 'primary';
  onConfirm: (note: string) => Promise<void> | void;
}) {
  const [note, setNote] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (open) {
      setNote('');
      setError(null);
    }
  }, [open]);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (required && !note.trim()) {
      setError('Write a short reason so the audit trail explains this decision.');
      return;
    }
    setBusy(true);
    try {
      await onConfirm(note.trim());
      onOpenChange(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong');
    } finally {
      setBusy(false);
    }
  };

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="overlay" />
        <Dialog.Content className="note-dialog">
          <form onSubmit={submit}>
            <Dialog.Title className="display note-dialog__title">{title}</Dialog.Title>
            {description && <Dialog.Description className="muted">{description}</Dialog.Description>}
            <label className="label" htmlFor="note-text">Reason{required ? '' : ' (optional)'}</label>
            <textarea id="note-text" className="note-dialog__text hand" rows={4} value={note} onChange={(e) => setNote(e.target.value)} autoFocus />
            {error && <p className="field-error" role="alert">{error}</p>}
            <div className="note-dialog__actions">
              <Dialog.Close asChild><Key>Cancel</Key></Dialog.Close>
              <Key type="submit" variant={tone === 'danger' ? 'danger' : tone === 'primary' ? 'primary' : 'plain'} busy={busy}>{confirmLabel}</Key>
            </div>
          </form>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
