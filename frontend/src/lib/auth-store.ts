import { useSyncExternalStore } from "react";

export interface Tokens {
  access_token: string;
  refresh_token: string;
  token_type?: string;
}

export interface AuthState {
  tokens: Tokens | null;
  email: string | null;
}

const STORAGE_KEY = "thinkbook.auth";
const EMAIL_KEY = "thinkbook.email";

function read(): AuthState {
  if (typeof window === "undefined") return { tokens: null, email: null };
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    const tokens = raw ? (JSON.parse(raw) as Tokens) : null;
    const email = localStorage.getItem(EMAIL_KEY);
    return { tokens, email };
  } catch {
    return { tokens: null, email: null };
  }
}

let state: AuthState = { tokens: null, email: null };
let hydrated = false;
const listeners = new Set<() => void>();

function emit() {
  for (const l of listeners) l();
}

export function hydrateAuth() {
  if (hydrated) return;
  hydrated = true;
  state = read();
  emit();
}

export function getAuth(): AuthState {
  return state;
}

export function getAccessToken(): string | null {
  return state.tokens?.access_token ?? null;
}

export function getRefreshToken(): string | null {
  return state.tokens?.refresh_token ?? null;
}

export function setTokens(tokens: Tokens, email?: string) {
  state = { tokens, email: email ?? state.email };
  if (typeof window !== "undefined") {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(tokens));
    if (email) localStorage.setItem(EMAIL_KEY, email);
  }
  emit();
}

export function updateTokens(tokens: Tokens) {
  state = { ...state, tokens };
  if (typeof window !== "undefined") {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(tokens));
  }
  emit();
}

export function clearAuth() {
  state = { tokens: null, email: null };
  if (typeof window !== "undefined") {
    localStorage.removeItem(STORAGE_KEY);
    localStorage.removeItem(EMAIL_KEY);
  }
  emit();
}

function subscribe(cb: () => void) {
  listeners.add(cb);
  return () => listeners.delete(cb);
}

export function useAuth(): AuthState {
  return useSyncExternalStore(
    subscribe,
    () => state,
    () => ({ tokens: null, email: null }),
  );
}