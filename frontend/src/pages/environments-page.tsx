import type { ChangeEvent, FormEvent } from "react";
import { useEffect, useState } from "react";

import { StatusPill } from "../components/status-pill";
import { getApiErrorMessage } from "../lib/error-messages";
import { createEnvironment, fetchEnvironments } from "../lib/management";
import type { EnvironmentRecord } from "../types/management";

function formatTimestamp(value: string | null) {
  if (!value) {
    return "Sin registro";
  }

  return new Intl.DateTimeFormat("es-PE", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export function EnvironmentsPage() {
  const [environments, setEnvironments] = useState<EnvironmentRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [feedback, setFeedback] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState({
    nombre: "",
    descripcion: "",
    ubicacion: "",
    estado: "activo" as "activo" | "inactivo",
  });

  useEffect(() => {
    let cancelled = false;

    async function loadEnvironments() {
      setLoading(true);
      setError(null);

      try {
        const response = await fetchEnvironments();
        if (!cancelled) {
          setEnvironments(response.data);
        }
      } catch (requestError) {
        if (!cancelled) {
          setError(
            getApiErrorMessage(
              requestError,
              "No pudimos cargar los ambientes registrados.",
            ),
          );
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    void loadEnvironments();

    return () => {
      cancelled = true;
    };
  }, []);

  function handleChange(
    field: keyof typeof form,
    event: ChangeEvent<HTMLInputElement | HTMLSelectElement>,
  ) {
    const nextValue = event.target.value;
    setForm((current) => ({
      ...current,
      [field]: nextValue,
    }));
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setCreating(true);
    setError(null);
    setFeedback(null);

    try {
      const created = await createEnvironment({
        nombre: form.nombre.trim(),
        descripcion: form.descripcion.trim(),
        ubicacion: form.ubicacion.trim(),
        estado: form.estado,
      });
      setEnvironments((current) => [created, ...current]);
      setForm({
        nombre: "",
        descripcion: "",
        ubicacion: "",
        estado: "activo",
      });
      setFeedback("Ambiente registrado correctamente.");
    } catch (requestError) {
      setError(
        getApiErrorMessage(
          requestError,
          "No pudimos registrar el ambiente.",
        ),
      );
    } finally {
      setCreating(false);
    }
  }

  return (
    <section className="page-section">
      <header className="page-header">
        <span className="eyebrow">Gestion</span>
        <h2>Ambientes educativos</h2>
        <p>
          Este modulo ya permite dar de alta y consultar ambientes registrados
          en el `Servicio_Gestion`.
        </p>
      </header>

      <section className="management-grid">
        <article className="monitor-card">
          <div className="section-heading">
            <div>
              <span className="eyebrow">Alta</span>
              <h3>Registrar ambiente</h3>
            </div>
          </div>

          <form className="management-form" onSubmit={handleSubmit}>
            <label>
              Nombre
              <input
                onChange={(event) => handleChange("nombre", event)}
                placeholder="Laboratorio A"
                value={form.nombre}
              />
            </label>
            <label>
              Descripcion
              <input
                onChange={(event) => handleChange("descripcion", event)}
                placeholder="Sala de computo"
                value={form.descripcion}
              />
            </label>
            <label>
              Ubicacion
              <input
                onChange={(event) => handleChange("ubicacion", event)}
                placeholder="Pabellon 1"
                value={form.ubicacion}
              />
            </label>
            <label>
              Estado
              <select
                onChange={(event) => handleChange("estado", event)}
                value={form.estado}
              >
                <option value="activo">Activo</option>
                <option value="inactivo">Inactivo</option>
              </select>
            </label>

            <div className="button-row">
              <button className="primary-button" disabled={creating} type="submit">
                {creating ? "Registrando..." : "Registrar ambiente"}
              </button>
            </div>
          </form>
        </article>

        <article className="monitor-card">
          <div className="section-heading">
            <div>
              <span className="eyebrow">Nota</span>
              <h3>Alcance actual</h3>
            </div>
          </div>

          <p className="inline-note">
            El backend actual ya expone alta y listado de ambientes, pero no
            cuenta aun con un endpoint de edicion para este recurso. La pantalla
            queda util para operacion administrativa inmediata.
          </p>
        </article>
      </section>

      {(feedback || error) && (
        <div className="form-alert">{error ?? feedback}</div>
      )}

      <section className="monitor-card">
        <div className="section-heading">
          <div>
            <span className="eyebrow">Listado</span>
            <h3>Ambientes registrados</h3>
          </div>
          <StatusPill tone={loading ? "warning" : "neutral"}>
            {loading ? "Cargando..." : `${environments.length} visibles`}
          </StatusPill>
        </div>

        {loading ? (
          <p className="empty-copy">Cargando ambientes registrados...</p>
        ) : environments.length === 0 ? (
          <p className="empty-copy">
            Aun no hay ambientes registrados en el sistema.
          </p>
        ) : (
          <div className="management-card-grid">
            {environments.map((environment) => (
              <article className="node-card management-card" key={environment.id}>
                <div className="node-card-header">
                  <div>
                    <strong>{environment.nombre}</strong>
                    <span>{environment.ubicacion || "Ubicacion no registrada"}</span>
                  </div>
                  <StatusPill
                    tone={
                      environment.estado === "activo" ? "success" : "danger"
                    }
                  >
                    {environment.estado === "activo" ? "Activo" : "Inactivo"}
                  </StatusPill>
                </div>

                <p>{environment.descripcion || "Sin descripcion operativa."}</p>

                <dl className="node-meta">
                  <div>
                    <dt>ID</dt>
                    <dd className="break-text">{environment.id}</dd>
                  </div>
                  <div>
                    <dt>Actualizado</dt>
                    <dd>{formatTimestamp(environment.updated_at)}</dd>
                  </div>
                </dl>
              </article>
            ))}
          </div>
        )}
      </section>
    </section>
  );
}
