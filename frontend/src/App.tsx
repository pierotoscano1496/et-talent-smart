import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import { AppShell } from "./components/app-shell";
import {
  PublicOnlyRoute,
  RequireAuth,
  RequireFirstLoginRoute,
  RequireRole,
} from "./router/guards";
import { useHydrateAuth } from "./store/auth-store";
import { ChangePasswordPage } from "./pages/change-password-page";
import { DashboardPage } from "./pages/dashboard-page";
import { EnvironmentsPage } from "./pages/environments-page";
import { LoginPage } from "./pages/login-page";
import { NodesPage } from "./pages/nodes-page";
import { NotFoundPage } from "./pages/not-found-page";
import { ReportsPage } from "./pages/reports-page";
import { StudentsPage } from "./pages/students-page";
import { UsersPage } from "./pages/users-page";

function HomeRedirect() {
  return <Navigate to="/dashboard" replace />;
}

export function App() {
  useHydrateAuth();

  return (
    <BrowserRouter>
      <Routes>
        <Route
          path="/login"
          element={
            <PublicOnlyRoute>
              <LoginPage />
            </PublicOnlyRoute>
          }
        />
        <Route
          path="/change-password"
          element={
            <RequireAuth>
              <ChangePasswordPage />
            </RequireAuth>
          }
        />
        <Route
          path="/"
          element={
            <RequireAuth>
              <RequireFirstLoginRoute>
                <AppShell />
              </RequireFirstLoginRoute>
            </RequireAuth>
          }
        >
          <Route index element={<HomeRedirect />} />
          <Route path="dashboard" element={<DashboardPage />} />
          <Route path="students" element={<RequireRole roles={["ADMINISTRADOR"]}><StudentsPage /></RequireRole>} />
          <Route path="environments" element={<RequireRole roles={["ADMINISTRADOR"]}><EnvironmentsPage /></RequireRole>} />
          <Route path="nodes" element={<RequireRole roles={["ADMINISTRADOR"]}><NodesPage /></RequireRole>} />
          <Route path="users" element={<RequireRole roles={["ADMINISTRADOR"]}><UsersPage /></RequireRole>} />
          <Route path="reports" element={<RequireRole roles={["ADMINISTRADOR", "AUXILIAR_EDUCACION"]}><ReportsPage /></RequireRole>} />
        </Route>
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </BrowserRouter>
  );
}
