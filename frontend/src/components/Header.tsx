'use client';

import { useState, useCallback } from 'react';
import { apiUpload } from '@/lib/utils';
import type { ProcessingResult } from '@/lib/types';

export default function Header() {
  const [uploading, setUploading] = useState(false);
  const [lastResult, setLastResult] = useState<ProcessingResult | null>(null);

  const handleUpload = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploading(true);
    setLastResult(null);

    try {
      const formData = new FormData();
      formData.append('file', file);
      const result = await apiUpload<ProcessingResult>('/invoices/upload', formData);
      setLastResult(result);
    } catch (err: any) {
      setLastResult({ status: 'FAILED', error: err.message, discrepancies: [] });
    } finally {
      setUploading(false);
      e.target.value = '';
    }
  }, []);

  return (
    <header className="flex items-center justify-between px-6 py-3 glass-header">
      <div className="flex items-center gap-2">
        <h2 className="text-sm font-medium bg-gradient-to-r from-surface-500 to-surface-400 bg-clip-text text-transparent">Intelligent Procurement Automation</h2>
      </div>

      <div className="flex items-center gap-4">
        {/* Upload Result Badge */}
        {lastResult && (
          <div className={`animate-slide-in-right text-xs px-3 py-1.5 rounded-full font-medium backdrop-blur-sm ${
            lastResult.status === 'SUCCESS'
              ? 'bg-emerald-100/80 text-emerald-700 border border-emerald-200/50'
              : 'bg-red-100/80 text-red-700 border border-red-200/50'
          }`}>
            {lastResult.status === 'SUCCESS'
              ? `[ok] ${lastResult.match_result} - ${lastResult.invoice_number}`
              : `[x] ${lastResult.error}`}
          </div>
        )}

        {/* Upload Button */}
        <label className={`flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-medium cursor-pointer transition-all duration-300 ${
          uploading
            ? 'glass text-surface-400 cursor-wait'
            : 'btn-primary hover:scale-105'
        }`}>
          <UploadIcon className={`h-4 w-4 ${uploading ? 'animate-spin-slow' : ''}`} />
          {uploading ? 'Processing...' : 'Upload Invoice'}
          <input
            type="file"
            accept=".pdf,.png,.jpg,.jpeg,.txt"
            onChange={handleUpload}
            disabled={uploading}
            className="hidden"
          />
        </label>
      </div>
    </header>
  );
}

function UploadIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
    </svg>
  );
}
