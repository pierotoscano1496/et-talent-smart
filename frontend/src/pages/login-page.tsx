import axios from "axios";
import { FormEvent, useMemo, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import { getFriendlyErrorMessage } from "../lib/error-messages";
import { loginRequest } from "../lib/api";
import { useAuthStore } from "../store/auth-store";

export function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const setSession = useAuthStore((state) => state.setSession);
  const notice = useAuthStore((state) => state.notice);
  const consumeNotice = useAuthStore((state) => state.consumeNotice);

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const redirectTarget = useMemo(() => {
    const from = location.state?.from?.pathname as string | undefined;
    return from && from !== "/login" ? from : "/dashboard";
  }, [location.state]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    consumeNotice();

    try {
      const payload = await loginRequest(email.trim(), password);
      setSession({
        token: payload.token,
        role: payload.rol,
        displayName: payload.nombre,
        firstLogin: payload.primer_login,
      });
      navigate(payload.primer_login ? "/change-password" : redirectTarget, {
        replace: true,
      });
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

  return (
    <section className="auth-screen">
      <div className="auth-card">
        <div className="auth-copy">
          <span className="eyebrow">Ingreso seguro</span>
          <h1>Centro de control para accesos RFID</h1>
          <p>
            Ingresa con tu cuenta institucional para administrar usuarios,
            ambientes y monitoreo de ingresos.
          </p>
        </div>

        <form className="auth-form" onSubmit={handleSubmit}>
          <label>
            Correo electronico
            <input
              autoComplete="email"
              onChange={(event) => setEmail(event.target.value)}
              placeholder="admin@escuela.pe"
              type="email"
              value={email}
            />
          </label>

          <label>
            Contrasena
            <input
              autoComplete="current-password"
              onChange={(event) => setPassword(event.target.value)}
              placeholder="Tu contrasena"
              type="password"
              value={password}
            />
          </label>

          {(notice || error) && (
            <div className="form-alert" role="alert">
              {error ?? notice}
            </div>
          )}

          <button className="primary-button" disabled={submitting} type="submit">
            {submitting ? "Validando..." : "Iniciar sesion"}
          </button>
        </form>
      </div>
    </section>
  );
}
