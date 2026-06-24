import type { ChangeEvent, FormEvent } from "react";
import { useState } from "react";

import { StatusPill } from "../components/status-pill";
import { getApiErrorMessage } from "../lib/error-messages";
import { createWebUser, updateWebUser } from "../lib/management";
import type { WebUserRecord } from "../types/management";

function formatTimestamp(value: string | null) {
  if (!value) {
    return "Sin registro";
  }

  return new Intl.DateTimeFormat("es-PE", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export function UsersPage() {
  const [sessionUsers, setSessionUsers] = useState<WebUserRecord[]>([]);
  const [creating, setCreating] = useState(false);
  const [updating, setUpdating] = useState(false);
  const [feedback, setFeedback] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [createForm, setCreateForm] = useState({
    nombre_completo: "",
    email: "",
    password_temporal: "",
    rol: "ADMINISTRADOR" as "ADMINISTRADOR" | "AUXILIAR_EDUCACION",
    estado: "activo" as "activo" | "inactivo",
  });
  const [updateForm, setUpdateForm] = useState({
    id: "",
    rol: "ADMINISTRADOR" as "ADMINISTRADOR" | "AUXILIAR_EDUCACION",
    estado: "activo" as "activo" | "inactivo",
  });

  function handleCreateChange(
    field: keyof typeof createForm,
    event: ChangeEvent<HTMLInputElement | HTMLSelectElement>,
  ) {
    const nextValue = event.target.value;
    setCreateForm((current) => ({
      ...current,
      [field]: nextValue,
    }));
  }

  function handleUpdateChange(
    field: keyof typeof updateForm,
    event: ChangeEvent<HTMLInputElement | HTMLSelectElement>,
  ) {
    const nextValue = event.target.value;
    setUpdateForm((current) => ({
      ...current,
      [field]: nextValue,
    }));
  }

  function loadUserIntoEditor(user: WebUserRecord) {
    setUpdateForm({
      id: user.id,
      rol: user.rol,
      estado: user.estado,
    });
    setFeedback(null);
    setError(null);
  }

  async function handleCreateUser(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setCreating(true);
    setError(null);
    setFeedback(null);

    try {
      const created = await createWebUser({
        nombre_completo: createForm.nombre_completo.trim(),
        email: createForm.email.trim(),
        password_temporal: createForm.password_temporal,
        rol: createForm.rol,
        estado: createForm.estado,
      });
      setSessionUsers((current) => [created, ...current]);
      setCreateForm({
        nombre_completo: "",
        email: "",
        password_temporal: "",
        rol: "ADMINISTRADOR",
        estado: "activo",
      });
      loadUserIntoEditor(created);
      setFeedback("Usuario web creado correctamente.");
    } catch (requestError) {
      setError(
        getApiErrorMessage(
          requestError,
          "No pudimos crear el usuario web.",
        ),
      );
    } finally {
      setCreating(false);
    }
  }

  async function handleUpdateUser(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setUpdating(true);
    setError(null);
    setFeedback(null);

    try {
      const updated = await updateWebUser(updateForm.id.trim(), {
        rol: updateForm.rol,
        estado: updateForm.estado,
      });
      setSessionUsers((current) => {
        const exists = current.some((user) => user.id === updated.id);
        if (!exists) {
          return [updated, ...current];
        }
        return current.map((user) => (user.id === updated.id ? updated : user));
      });
      loadUserIntoEditor(updated);
      setFeedback("Usuario actualizado correctamente.");
    } catch (requestError) {
      setError(
        getApiErrorMessage(
          requestError,
          "No pudimos actualizar el usuario web.",
        ),
      );
    } finally {
      setUpdating(false);
    }
  }

  return (
    <section className="page-section">
      <header className="page-header">
        <span className="eyebrow">Gestion</span>
        <h2>Usuarios del sistema</h2>
        <p>
          Este modulo ya permite crear usuarios y actualizar su rol o estado.
          El backend actual aun no expone un listado global de usuarios.
        </p>
      </header>

      <section className="management-grid">
        <article className="monitor-card">
          <div className="section-heading">
            <div>
              <span className="eyebrow">Alta</span>
              <h3>Crear usuario web</h3>
            </div>
          </div>

          <form className="management-form" onSubmit={handleCreateUser}>
            <label>
              Nombre completo
              <input
                onChange={(event) => handleCreateChange("nombre_completo", event)}
                placeholder="Admin Principal"
                value={createForm.nombre_completo}
              />
            </label>
            <label>
              Correo electronico
              <input
                onChange={(event) => handleCreateChange("email", event)}
                placeholder="admin@escuela.pe"
                type="email"
                value={createForm.email}
              />
            </label>
            <label>
              Contrasena temporal
              <input
                onChange={(event) =>
                  handleCreateChange("password_temporal", event)
                }
                placeholder="Temporal123"
                type="password"
                value={createForm.password_temporal}
              />
            </label>
            <label>
              Rol
              <select
                onChange={(event) => handleCreateChange("rol", event)}
                value={createForm.rol}
              >
                <option value="ADMINISTRADOR">Administrador</option>
                <option value="AUXILIAR_EDUCACION">Auxiliar de educacion</option>
              </select>
            </label>
            <label>
              Estado
              <select
                onChange={(event) => handleCreateChange("estado", event)}
                value={createForm.estado}
              >
                <option value="activo">Activo</option>
                <option value="inactivo">Inactivo</option>
              </select>
            </label>

            <div className="button-row">
              <button className="primary-button" disabled={creating} type="submit">
                {creating ? "Creando..." : "Crear usuario"}
              </button>
            </div>
          </form>
        </article>

        <article className="monitor-card">
          <div className="section-heading">
            <div>
              <span className="eyebrow">Edicion</span>
              <h3>Actualizar rol o estado</h3>
            </div>
            <StatusPill tone={updateForm.id ? "success" : "neutral"}>
              {updateForm.id ? "ID cargado" : "Sin ID"}
            </StatusPill>
          </div>

          <form className="management-form" onSubmit={handleUpdateUser}>
            <label>
              ID de usuario
              <input
                onChange={(event) => handleUpdateChange("id", event)}
                placeholder="UUID del usuario"
                value={updateForm.id}
              />
            </label>
            <label>
              Rol
              <select
                onChange={(event) => handleUpdateChange("rol", event)}
                value={updateForm.rol}
              >
                <option value="ADMINISTRADOR">Administrador</option>
                <option value="AUXILIAR_EDUCACION">Auxiliar de educacion</option>
              </select>
            </label>
            <label>
              Estado
              <select
                onChange={(event) => handleUpdateChange("estado", event)}
                value={updateForm.estado}
              >
                <option value="activo">Activo</option>
                <option value="inactivo">Inactivo</option>
              </select>
            </label>

            <div className="button-row">
              <button className="primary-button" disabled={updating} type="submit">
                {updating ? "Actualizando..." : "Actualizar usuario"}
              </button>
            </div>
          </form>
        </article>
      </section>

      {(feedback || error) && (
        <div className="form-alert">{error ?? feedback}</div>
      )}

      <section className="monitor-card">
        <div className="section-heading">
          <div>
            <span className="eyebrow">Sesion actual</span>
            <h3>Usuarios tocados desde esta pantalla</h3>
          </div>
          <StatusPill tone="neutral">{`${sessionUsers.length} visibles`}</StatusPill>
        </div>

        {sessionUsers.length === 0 ? (
          <p className="empty-copy">
            Crea o actualiza un usuario para tenerlo disponible en el editor de
            esta sesion.
          </p>
        ) : (
          <div className="management-card-grid">
            {sessionUsers.map((user) => (
              <article className="node-card management-card" key={user.id}>
                <div className="node-card-header">
                  <div>
                    <strong>{user.nombre_completo}</strong>
                    <span>{user.email}</span>
                  </div>
                  <StatusPill
                    tone={user.estado === "activo" ? "success" : "danger"}
                  >
                    {user.estado === "activo" ? "Activo" : "Inactivo"}
                  </StatusPill>
                </div>

                <dl className="node-meta">
                  <div>
                    <dt>Rol</dt>
                    <dd>{user.rol}</dd>
                  </div>
                  <div>
                    <dt>Primer login</dt>
                    <dd>{user.primer_login ? "Pendiente" : "Completado"}</dd>
                  </div>
                  <div>
                    <dt>Actualizado</dt>
                    <dd>{formatTimestamp(user.updated_at)}</dd>
                  </div>
                </dl>

                <div className="button-row">
                  <button
                    className="ghost-button"
                    onClick={() => loadUserIntoEditor(user)}
                    type="button"
                  >
                    Cargar en editor
                  </button>
                </div>
              </article>
            ))}
          </div>
        )}
      </section>
    </section>
  );
}
