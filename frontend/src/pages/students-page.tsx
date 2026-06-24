import type { ChangeEvent, FormEvent } from "react";
import { useEffect, useState } from "react";

import { StatusPill } from "../components/status-pill";
import { getApiErrorMessage } from "../lib/error-messages";
import {
  assignStudentRfid,
  createStudent,
  fetchStudents,
  updateStudent,
} from "../lib/management";
import type { StudentRecord } from "../types/management";

function formatTimestamp(value: string | null) {
  if (!value) {
    return "Sin registro";
  }

  return new Intl.DateTimeFormat("es-PE", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export function StudentsPage() {
  const [students, setStudents] = useState<StudentRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [feedback, setFeedback] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [saving, setSaving] = useState(false);
  const [assigningRfid, setAssigningRfid] = useState(false);
  const [selectedStudentId, setSelectedStudentId] = useState<string | null>(null);
  const [createForm, setCreateForm] = useState({
    nombre_completo: "",
    codigo: "",
    grado_seccion: "",
  });
  const [editForm, setEditForm] = useState({
    nombre_completo: "",
    grado_seccion: "",
    estado: "activo" as "activo" | "inactivo",
    tag_rfid: "",
  });

  useEffect(() => {
    let cancelled = false;

    async function loadStudents() {
      setLoading(true);
      setError(null);

      try {
        const response = await fetchStudents();
        if (!cancelled) {
          setStudents(response.data);
        }
      } catch (requestError) {
        if (!cancelled) {
          setError(
            getApiErrorMessage(
              requestError,
              "No pudimos cargar el listado de estudiantes.",
            ),
          );
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    void loadStudents();

    return () => {
      cancelled = true;
    };
  }, []);

  function handleCreateChange(
    field: keyof typeof createForm,
    event: ChangeEvent<HTMLInputElement>,
  ) {
    const nextValue = event.target.value;
    setCreateForm((current) => ({
      ...current,
      [field]: nextValue,
    }));
  }

  function handleEditChange(
    field: keyof typeof editForm,
    event: ChangeEvent<HTMLInputElement | HTMLSelectElement>,
  ) {
    const nextValue = event.target.value;
    setEditForm((current) => ({
      ...current,
      [field]: nextValue,
    }));
  }

  function selectStudent(student: StudentRecord) {
    setSelectedStudentId(student.id);
    setEditForm({
      nombre_completo: student.nombre_completo,
      grado_seccion: student.grado_seccion,
      estado: student.estado,
      tag_rfid: student.tag_rfid ?? "",
    });
    setFeedback(null);
    setError(null);
  }

  async function handleCreateStudent(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setCreating(true);
    setError(null);
    setFeedback(null);

    try {
      const created = await createStudent({
        nombre_completo: createForm.nombre_completo.trim(),
        codigo: createForm.codigo.trim(),
        grado_seccion: createForm.grado_seccion.trim(),
      });
      setStudents((current) => [created, ...current]);
      setCreateForm({
        nombre_completo: "",
        codigo: "",
        grado_seccion: "",
      });
      selectStudent(created);
      setFeedback("Estudiante registrado correctamente.");
    } catch (requestError) {
      setError(
        getApiErrorMessage(
          requestError,
          "No pudimos registrar el estudiante.",
        ),
      );
    } finally {
      setCreating(false);
    }
  }

  async function handleUpdateStudent(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedStudentId) {
      setError("Selecciona un estudiante antes de intentar editarlo.");
      return;
    }

    setSaving(true);
    setError(null);
    setFeedback(null);

    try {
      const updated = await updateStudent(selectedStudentId, {
        nombre_completo: editForm.nombre_completo.trim(),
        grado_seccion: editForm.grado_seccion.trim(),
        estado: editForm.estado,
      });
      setStudents((current) =>
        current.map((student) =>
          student.id === updated.id ? updated : student,
        ),
      );
      selectStudent(updated);
      setFeedback("Estudiante actualizado correctamente.");
    } catch (requestError) {
      setError(
        getApiErrorMessage(
          requestError,
          "No pudimos actualizar el estudiante.",
        ),
      );
    } finally {
      setSaving(false);
    }
  }

  async function handleAssignRfid() {
    if (!selectedStudentId) {
      setError("Selecciona un estudiante antes de asociar una pulsera RFID.");
      return;
    }

    setAssigningRfid(true);
    setError(null);
    setFeedback(null);

    try {
      const updated = await assignStudentRfid(
        selectedStudentId,
        editForm.tag_rfid.trim().toUpperCase(),
      );
      setStudents((current) =>
        current.map((student) =>
          student.id === updated.id ? updated : student,
        ),
      );
      selectStudent(updated);
      setFeedback("Pulsera RFID asociada correctamente.");
    } catch (requestError) {
      setError(
        getApiErrorMessage(
          requestError,
          "No pudimos asociar la pulsera RFID.",
        ),
      );
    } finally {
      setAssigningRfid(false);
    }
  }

  const selectedStudent =
    selectedStudentId === null
      ? null
      : students.find((student) => student.id === selectedStudentId) ?? null;

  return (
    <section className="page-section">
      <header className="page-header">
        <span className="eyebrow">Gestion</span>
        <h2>Estudiantes y pulseras RFID</h2>
        <p>
          Este modulo ya permite registrar estudiantes, editar su estado y
          asociarles una pulsera RFID usando el `Servicio_Gestion`.
        </p>
      </header>

      <section className="management-grid">
        <article className="monitor-card">
          <div className="section-heading">
            <div>
              <span className="eyebrow">Alta</span>
              <h3>Registrar estudiante</h3>
            </div>
          </div>

          <form className="management-form" onSubmit={handleCreateStudent}>
            <label>
              Nombre completo
              <input
                onChange={(event) => handleCreateChange("nombre_completo", event)}
                placeholder="Ana Garcia"
                value={createForm.nombre_completo}
              />
            </label>
            <label>
              Codigo
              <input
                onChange={(event) => handleCreateChange("codigo", event)}
                placeholder="STU001"
                value={createForm.codigo}
              />
            </label>
            <label>
              Grado / seccion
              <input
                onChange={(event) => handleCreateChange("grado_seccion", event)}
                placeholder="3A"
                value={createForm.grado_seccion}
              />
            </label>

            <div className="button-row">
              <button className="primary-button" disabled={creating} type="submit">
                {creating ? "Registrando..." : "Registrar estudiante"}
              </button>
            </div>
          </form>
        </article>

        <article className="monitor-card">
          <div className="section-heading">
            <div>
              <span className="eyebrow">Edicion</span>
              <h3>Actualizar estudiante</h3>
            </div>
            <StatusPill tone={selectedStudent ? "success" : "neutral"}>
              {selectedStudent ? "Estudiante cargado" : "Sin seleccion"}
            </StatusPill>
          </div>

          {selectedStudent ? (
            <form className="management-form" onSubmit={handleUpdateStudent}>
              <label>
                Nombre completo
                <input
                  onChange={(event) => handleEditChange("nombre_completo", event)}
                  value={editForm.nombre_completo}
                />
              </label>
              <label>
                Grado / seccion
                <input
                  onChange={(event) => handleEditChange("grado_seccion", event)}
                  value={editForm.grado_seccion}
                />
              </label>
              <label>
                Estado
                <select
                  onChange={(event) => handleEditChange("estado", event)}
                  value={editForm.estado}
                >
                  <option value="activo">Activo</option>
                  <option value="inactivo">Inactivo</option>
                </select>
              </label>
              <label>
                UID RFID
                <input
                  onChange={(event) => handleEditChange("tag_rfid", event)}
                  placeholder="A1B2C3D4"
                  value={editForm.tag_rfid}
                />
              </label>

              <div className="button-row">
                <button className="primary-button" disabled={saving} type="submit">
                  {saving ? "Guardando..." : "Guardar cambios"}
                </button>
                <button
                  className="link-button"
                  disabled={assigningRfid}
                  onClick={handleAssignRfid}
                  type="button"
                >
                  {assigningRfid ? "Asociando..." : "Asociar RFID"}
                </button>
              </div>
            </form>
          ) : (
            <p className="empty-copy">
              Selecciona un estudiante del listado para editarlo o asociarle un
              tag RFID.
            </p>
          )}
        </article>
      </section>

      {(feedback || error) && (
        <div className="form-alert">{error ?? feedback}</div>
      )}

      <section className="monitor-card">
        <div className="section-heading">
          <div>
            <span className="eyebrow">Listado</span>
            <h3>Estudiantes registrados</h3>
          </div>
          <StatusPill tone={loading ? "warning" : "neutral"}>
            {loading ? "Cargando..." : `${students.length} visibles`}
          </StatusPill>
        </div>

        {loading ? (
          <p className="empty-copy">Cargando estudiantes registrados...</p>
        ) : students.length === 0 ? (
          <p className="empty-copy">
            Aun no hay estudiantes registrados en el sistema.
          </p>
        ) : (
          <div className="management-card-grid">
            {students.map((student) => (
              <article className="node-card management-card" key={student.id}>
                <div className="node-card-header">
                  <div>
                    <strong>{student.nombre_completo}</strong>
                    <span>{student.codigo}</span>
                  </div>
                  <StatusPill
                    tone={student.estado === "activo" ? "success" : "danger"}
                  >
                    {student.estado === "activo" ? "Activo" : "Inactivo"}
                  </StatusPill>
                </div>

                <dl className="node-meta">
                  <div>
                    <dt>Grado / seccion</dt>
                    <dd>{student.grado_seccion}</dd>
                  </div>
                  <div>
                    <dt>RFID activo</dt>
                    <dd>{student.tag_rfid ?? "Sin asignar"}</dd>
                  </div>
                  <div>
                    <dt>Actualizado</dt>
                    <dd>{formatTimestamp(student.updated_at)}</dd>
                  </div>
                </dl>

                <div className="button-row">
                  <button
                    className="ghost-button"
                    onClick={() => selectStudent(student)}
                    type="button"
                  >
                    Editar
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
