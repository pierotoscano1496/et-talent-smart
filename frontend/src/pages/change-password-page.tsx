import axios from "axios";
import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";

import { changePasswordRequest } from "../lib/api";
import { getFriendlyErrorMessage } from "../lib/error-messages";
import { useAuthStore } from "../store/auth-store";

export function ChangePasswordPage() {
  const navigate = useNavigate();
  const firstLogin = useAuthStore((state) => state.firstLogin);
  const displayName = useAuthStore((state) => state.displayName);
  const markPasswordChanged = useAuthStore((state) => state.markPasswordChanged);
  const remoteLogout = useAuthStore((state) => state.remoteLogout);

  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (newPassword.trim().length < 8) {
      setError("La nueva contrasena debe tener al menos 8 caracteres.");
      setSuccess(null);
      return;
    }

    if (newPassword !== confirmPassword) {
      setError("La confirmacion de contrasena no coincide.");
      setSuccess(null);
      return;
    }

    setSubmitting(true);
    setError(null);
    setSuccess(null);

    try {
      await changePasswordRequest(currentPassword, newPassword);
      markPasswordChanged();
      setSuccess("Contrasena actualizada correctamente.");
      navigate("/dashboard", { replace: true });
    } catch (requestError) {
      if (axios.isAxiosError(requestError)) {
        const errorCode = requestError.response?.data?.error as string | undefined;
        setError(getFriendlyErrorMessage(errorCode));
      } else {
        setError(getFriendlyErrorMessage(undefined));
      }
    } finally {
      setSubmitting(false);
    }
  }

  async function handleCancel() {
    await remoteLogout(
      "Cerramos tu sesion porque el cambio de contrasena era obligatorio.",
    );
    navigate("/login", { replace: true });
  }

  return (
    <section className="auth-screen">
      <div className="auth-card compact">
        <div className="auth-copy">
          <span className="eyebrow">
            {firstLogin ? "Primer ingreso" : "Seguridad de cuenta"}
          </span>
          <h1>Actualiza tu contrasena</h1>
          <p>
            {displayName
              ? `${displayName}, antes de continuar necesitamos reforzar tu acceso.`
              : "Antes de continuar necesitamos reforzar tu acceso."}
          </p>
        </div>

        <form className="auth-form" onSubmit={handleSubmit}>
          <label>
            Contrasena actual
            <input
              autoComplete="current-password"
              onChange={(event) => setCurrentPassword(event.target.value)}
              type="password"
              value={currentPassword}
            />
          </label>

          <label>
            Nueva contrasena
            <input
              autoComplete="new-password"
              onChange={(event) => setNewPassword(event.target.value)}
              type="password"
              value={newPassword}
            />
          </label>

          <label>
            Confirmar nueva contrasena
            <input
              autoComplete="new-password"
              onChange={(event) => setConfirmPassword(event.target.value)}
              type="password"
              value={confirmPassword}
            />
          </label>

          {(error || success) && (
            <div className="form-alert" role="alert">
              {error ?? success}
            </div>
          )}

          <div className="button-row">
            <button className="primary-button" disabled={submitting} type="submit">
              {submitting ? "Actualizando..." : "Guardar contrasena"}
            </button>
            {firstLogin && (
              <button
                className="ghost-button"
                onClick={handleCancel}
                type="button"
              >
                Cerrar sesion
              </button>
            )}
          </div>
        </form>
      </div>
    </section>
  );
}
