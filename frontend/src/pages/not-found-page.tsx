import { Link } from "react-router-dom";

export function NotFoundPage() {
  return (
    <section className="auth-screen">
      <div className="auth-card compact">
        <div className="auth-copy">
          <span className="eyebrow">404</span>
          <h1>Ruta no encontrada</h1>
          <p>La pantalla que buscas todavia no existe o fue movida.</p>
        </div>
        <Link className="primary-button link-button" to="/login">
          Volver al ingreso
        </Link>
      </div>
    </section>
  );
}
