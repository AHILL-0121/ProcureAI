'use client';

import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import { useRouter } from 'next/navigation';
import { useQueryClient } from '@tanstack/react-query';
import { ApiError, get, getToken, post, setToken, setUnauthorizedHandler } from './api';
import type { User } from './types';

interface AuthState {
  user: User | null;
  ready: boolean;
  signIn: (email: string, password: string) => Promise<void>;
  signOut: () => void;
}

const AuthContext = createContext<AuthState>({
  user: null,
  ready: false,
  signIn: async () => {},
  signOut: () => {},
});

export function useAuth() {
  return useContext(AuthContext);
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [ready, setReady] = useState(false);
  const router = useRouter();
  const qc = useQueryClient();

  const signOut = useCallback(() => {
    setToken(null);
    setUser(null);
    qc.clear();
    router.replace('/login');
  }, [qc, router]);

  useEffect(() => {
    setUnauthorizedHandler(signOut);
    if (!getToken()) {
      setReady(true);
      return;
    }
    get<User>('/auth/me')
      .then(setUser)
      .catch(() => setToken(null))
      .finally(() => setReady(true));
    return () => setUnauthorizedHandler(null);
  }, [signOut]);

  const signIn = useCallback(async (email: string, password: string) => {
    try {
      const res = await post<{ access_token: string; user: User }>('/auth/login', { email, password });
      setToken(res.access_token);
      setUser(res.user);
    } catch (e) {
      throw e instanceof ApiError ? e : new Error('Sign-in failed');
    }
  }, []);

  const value = useMemo(() => ({ user, ready, signIn, signOut }), [user, ready, signIn, signOut]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
