import { useEffect } from "react";
import { Navigate, useLocation } from "react-router-dom";

import { useAuthStore } from "../store/auth-store";
import type { UserRole } from "../types/auth";

type GuardProps = {
  children: JSX.Element;
};

export function PublicOnlyRoute({ children }: GuardProps) {
  const { token, firstLogin, hydrated } = useAuthStore((state) => ({
    token: state.token,
    firstLogin: state.firstLogin,
    hydrated: state.hydrated,
  }));

  if (!hydrated) {
    return <div className="screen-loader">Cargando sesion...</div>;
  }

  if (!token) {
    return children;
  }

  return (
    <Navigate
      to={firstLogin ? "/change-password" : "/dashboard"}
      replace
    />
  );
}

export function RequireAuth({ children }: GuardProps) {
  const location = useLocation();
  const { token, hydrated } = useAuthStore((state) => ({
    token: state.token,
    hydrated: state.hydrated,
  }));

  if (!hydrated) {
    return <div className="screen-loader">Cargando sesion...</div>;
  }

  if (!token) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }

  return children;
}

export function RequireFirstLoginRoute({ children }: GuardProps) {
  const location = useLocation();
  const firstLogin = useAuthStore((state) => state.firstLogin);
  const remoteLogout = useAuthStore((state) => state.remoteLogout);

  useEffect(() => {
    if (firstLogin && location.pathname !== "/change-password") {
      void remoteLogout(
        "Debes cambiar tu contrasena temporal antes de navegar por la plataforma.",
      );
    }
  }, [firstLogin, location.pathname, remoteLogout]);

  if (firstLogin) {
    return <Navigate to="/login" replace />;
  }

  return children;
}

type RequireRoleProps = GuardProps & {
  roles: UserRole[];
};

export function RequireRole({ children, roles }: RequireRoleProps) {
  const role = useAuthStore((state) => state.role);
  if (!role || !roles.includes(role)) {
    return <Navigate to="/dashboard" replace />;
  }
  return children;
}
