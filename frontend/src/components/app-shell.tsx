import { NavLink, Outlet, useNavigate } from "react-router-dom";

import { useAuthStore } from "../store/auth-store";
import type { UserRole } from "../types/auth";

type NavItem = {
  to: string;
  label: string;
  roles?: UserRole[];
};

const navItems: NavItem[] = [
  { to: "/dashboard", label: "Monitoreo" },
  { to: "/students", label: "Estudiantes", roles: ["ADMINISTRADOR"] },
  { to: "/environments", label: "Ambientes", roles: ["ADMINISTRADOR"] },
  { to: "/nodes", label: "Nodos", roles: ["ADMINISTRADOR"] },
  { to: "/users", label: "Usuarios", roles: ["ADMINISTRADOR"] },
  {
    to: "/reports",
    label: "Reportes",
    roles: ["ADMINISTRADOR", "AUXILIAR_EDUCACION"],
  },
];

export function AppShell() {
  const navigate = useNavigate();
  const role = useAuthStore((state) => state.role);
  const displayName = useAuthStore((state) => state.displayName);
  const remoteLogout = useAuthStore((state) => state.remoteLogout);

  async function handleLogout() {
    await remoteLogout("Sesion cerrada.");
    navigate("/login", { replace: true });
  }

  return (
    <div className="app-shell">
      <aside className="sidebar-card">
        <div className="brand-block">
          <span className="eyebrow">ET Control de Acceso</span>
          <h1>Cabina Operativa RFID</h1>
          <p>
            Base web para autenticacion, gestion administrativa y monitoreo del
            sistema.
          </p>
        </div>

        <div className="user-chip">
          <div>
            <strong>{displayName ?? "Usuario"}</strong>
            <span>{role}</span>
          </div>
          <button className="ghost-button" onClick={handleLogout} type="button">
            Cerrar sesion
          </button>
        </div>

        <nav className="side-nav" aria-label="Navegacion principal">
          {navItems
            .filter((item) => !item.roles || (role ? item.roles.includes(role) : false))
            .map((item) => (
              <NavLink
                key={item.to}
                className={({ isActive }) =>
                  isActive ? "nav-link active" : "nav-link"
                }
                to={item.to}
              >
                {item.label}
              </NavLink>
            ))}
        </nav>
      </aside>

      <main className="content-panel">
        <Outlet />
      </main>
    </div>
  );
}
