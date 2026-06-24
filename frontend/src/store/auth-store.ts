import axios from "axios";
import { useEffect } from "react";
import { create } from "zustand";

import type { SessionSnapshot, UserRole } from "../types/auth";

const STORAGE_KEY = "et-control-acceso-auth";
const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || "";

type AuthState = {
  token: string | null;
  role: UserRole | null;
  displayName: string | null;
  firstLogin: boolean;
  hydrated: boolean;
  notice: string | null;
  setSession: (session: SessionSnapshot) => void;
  clearSession: (notice?: string | null) => void;
  markPasswordChanged: () => void;
  hydrateFromStorage: () => void;
  consumeNotice: () => void;
  remoteLogout: (notice?: string) => Promise<void>;
};

function persistSession(session: SessionSnapshot | null) {
  if (!session) {
    window.localStorage.removeItem(STORAGE_KEY);
    return;
  }
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(session));
}

export const useAuthStore = create<AuthState>((set, get) => ({
  token: null,
  role: null,
  displayName: null,
  firstLogin: false,
  hydrated: false,
  notice: null,
  setSession: (session) => {
    persistSession(session);
    set({
      token: session.token,
      role: session.role,
      displayName: session.displayName,
      firstLogin: session.firstLogin,
      notice: null,
      hydrated: true,
    });
  },
  clearSession: (notice = null) => {
    persistSession(null);
    set({
      token: null,
      role: null,
      displayName: null,
      firstLogin: false,
      notice,
      hydrated: true,
    });
  },
  markPasswordChanged: () => {
    const snapshot = get();
    if (!snapshot.token || !snapshot.role || !snapshot.displayName) {
      return;
    }
    const nextSession: SessionSnapshot = {
      token: snapshot.token,
      role: snapshot.role,
      displayName: snapshot.displayName,
      firstLogin: false,
    };
    persistSession(nextSession);
    set({ firstLogin: false });
  },
  hydrateFromStorage: () => {
    if (get().hydrated) {
      return;
    }
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      set({ hydrated: true });
      return;
    }
    try {
      const parsed = JSON.parse(raw) as SessionSnapshot;
      set({
        token: parsed.token,
        role: parsed.role,
        displayName: parsed.displayName,
        firstLogin: parsed.firstLogin,
        hydrated: true,
      });
    } catch {
      persistSession(null);
      set({ hydrated: true });
    }
  },
  consumeNotice: () => set({ notice: null }),
  remoteLogout: async (notice) => {
    try {
      if (get().token) {
        await axios.post(
          `${apiBaseUrl}/auth/logout`,
          {},
          {
            headers: {
              Authorization: `Bearer ${get().token}`,
            },
          },
        );
      }
    } catch {
      // Cierre best-effort; de todas formas limpiamos el cliente.
    } finally {
      get().clearSession(notice ?? null);
    }
  },
}));

export function useHydrateAuth() {
  const hydrateFromStorage = useAuthStore((state) => state.hydrateFromStorage);

  useEffect(() => {
    hydrateFromStorage();
  }, [hydrateFromStorage]);
}
