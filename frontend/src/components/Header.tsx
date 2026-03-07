'use client';

import { useState, useCallback } from 'react';
import { apiUpload } from '@/lib/utils';
import type { ProcessingResult } from '@/lib/types';
import { tokens } from '@/lib/design-tokens';
import { Badge } from './UIComponents';

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
    <header className="flex items-center justify-between px-6 py-3 warm-header">
      <div className="flex items-center gap-2">
        <h2 className="text-sm font-medium" style={{
          background: `linear-gradient(to right, ${tokens.slate}, ${tokens.mist})`,
          WebkitBackgroundClip: 'text',
          WebkitTextFillColor: 'transparent',
          backgroundClip: 'text'
        }}>Intelligent Procurement Automation</h2>
      </div>

      <div className="flex items-center gap-4">
        {/* Upload Result Badge */}
        {lastResult && (
          <div className="animate-slide-in-right">
            <Badge type={lastResult.status === 'SUCCESS' ? 'MATCHED' : 'FAILED'} />
            <span className="ml-2 text-xs" style={{ color: tokens.slate }}>
              {lastResult.status === 'SUCCESS'
                ? `${lastResult.match_result} - ${lastResult.invoice_number}`
                : lastResult.error}
            </span>
          </div>
        )}

        {/* Upload Button */}
        <label 
          className="flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-medium cursor-pointer transition-all duration-300"
          style={{
            background: uploading 
              ? tokens.sand 
              : `linear-gradient(135deg, ${tokens.amber}, ${tokens.ember})`,
            color: 'white',
            boxShadow: uploading ? 'none' : `0 4px 14px ${tokens.amber}50`,
            cursor: uploading ? 'wait' : 'pointer',
            opacity: uploading ? 0.6 : 1
          }}
        >
          <UploadIcon className={`h-4 w-4 ${uploading ? 'animate-spin' : ''}`} />
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
