import type { Metadata } from 'next';
import './globals.css';
import Sidebar from '@/components/Sidebar';
import Header from '@/components/Header';
import { WebSocketProvider } from '@/components/WebSocketProvider';
import { ToastProvider } from '@/components/Toast';

export const metadata: Metadata = {
  title: 'ProcureAI - Intelligent Procurement Automation',
  description: 'Multi-Agent AI System for Three-Way Match Automation powered by Llama 3.1',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="antialiased">
        <WebSocketProvider>
          <ToastProvider>
            {/* Animated background orbs */}
            <div className="bg-orb w-96 h-96 bg-emerald-200/40 top-[-10%] left-[-5%] animate-float" />
            <div className="bg-orb w-80 h-80 bg-teal-200/30 bottom-[10%] right-[-5%] animate-float" style={{ animationDelay: '3s' }} />
            <div className="bg-orb w-64 h-64 bg-cyan-200/20 top-[40%] left-[30%] animate-float" style={{ animationDelay: '5s' }} />

            <div className="relative z-10 flex h-screen overflow-hidden">
              <Sidebar />
              <div className="flex flex-1 flex-col overflow-hidden">
                <Header />
                <main className="flex-1 overflow-y-auto p-6">
                  {children}
                </main>
              </div>
            </div>
          </ToastProvider>
        </WebSocketProvider>
      </body>
    </html>
  );
}
