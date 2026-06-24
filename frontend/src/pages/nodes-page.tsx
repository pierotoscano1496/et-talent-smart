import type { ChangeEvent, FormEvent } from "react";
import { useEffect, useState } from "react";

import { StatusPill } from "../components/status-pill";
import { getApiErrorMessage } from "../lib/error-messages";
import {
  createNode,
  fetchAdminNodes,
  fetchEnvironments,
  manageNodeToken,
  updateNodeStatus,
} from "../lib/management";
import type {
  AdminNodeStatusRecord,
  EnvironmentRecord,
  NodeTokenAction,
} from "../types/management";

function formatTimestamp(value: string | null) {
  if (!value) {
    return "Sin heartbeat";
  }

  return new Intl.DateTimeFormat("es-PE", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export function NodesPage() {
  const [nodes, setNodes] = useState<AdminNodeStatusRecord[]>([]);
  const [environments, setEnvironments] = useState<EnvironmentRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [saving, setSaving] = useState(false);
  const [managingToken, setManagingToken] = useState(false);
  const [feedback, setFeedback] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selectedNodeId, setSelectedNodeId] = useState<string>("");
  const [selectedNodeState, setSelectedNodeState] = useState<
    "activo" | "inactivo"
  >("activo");
  const [lastTokenResult, setLastTokenResult] = useState<{
    nodeId: string;
    action: NodeTokenAction;
    status: string;
    token: string | null;
  } | null>(null);
  const [form, setForm] = useState({
    identificador: "",
    descripcion: "",
    estado: "activo" as "activo" | "inactivo",
    id_ambiente: "",
  });

  useEffect(() => {
    let cancelled = false;

    async function loadPage() {
      setLoading(true);
      setError(null);

      try {
        const [environmentResponse, nodeResponse] = await Promise.all([
          fetchEnvironments(),
          fetchAdminNodes(),
        ]);

        if (cancelled) {
          return;
        }

        setEnvironments(environmentResponse.data);
        setNodes(nodeResponse);

        if (nodeResponse.length > 0) {
          setSelectedNodeId(nodeResponse[0].id);
          setSelectedNodeState(
            nodeResponse[0].estado === "inactivo" ? "inactivo" : "activo",
          );
        }
      } catch (requestError) {
        if (!cancelled) {
          setError(
            getApiErrorMessage(
              requestError,
              "No pudimos cargar la administracion de nodos.",
            ),
          );
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    void loadPage();

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

  function selectNode(node: AdminNodeStatusRecord) {
    setSelectedNodeId(node.id);
    setSelectedNodeState(node.estado === "inactivo" ? "inactivo" : "activo");
    setFeedback(null);
    setError(null);
  }

  async function handleCreateNode(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setCreating(true);
    setError(null);
    setFeedback(null);

    try {
      const created = await createNode({
        identificador: form.identificador.trim(),
        descripcion: form.descripcion.trim(),
        estado: form.estado,
        id_ambiente: form.id_ambiente,
      });

      const matchingEnvironment = environments.find(
        (environment) => environment.id === created.ambiente_id,
      );

      setNodes((current) => [
        {
          id: created.id,
          identificador: created.identificador,
          descripcion: created.descripcion,
          estado: created.estado,
          estado_conectividad: created.estado_conectividad,
          ultimo_heartbeat: created.ultimo_heartbeat,
          updated_at: created.updated_at,
          ambiente: {
            id: created.ambiente_id,
            nombre:
              created.ambiente_nombre ??
              matchingEnvironment?.nombre ??
              "Ambiente no resuelto",
          },
        },
        ...current,
      ]);

      setForm({
        identificador: "",
        descripcion: "",
        estado: "activo",
        id_ambiente: "",
      });
      setSelectedNodeId(created.id);
      setSelectedNodeState(created.estado);
      setFeedback("Nodo registrado correctamente.");
    } catch (requestError) {
      setError(
        getApiErrorMessage(
          requestError,
          "No pudimos registrar el nodo.",
        ),
      );
    } finally {
      setCreating(false);
    }
  }

  async function handleUpdateStatus() {
    if (!selectedNodeId) {
      setError("Selecciona un nodo antes de cambiar su estado.");
      return;
    }

    setSaving(true);
    setError(null);
    setFeedback(null);

    try {
      const updated = await updateNodeStatus(selectedNodeId, selectedNodeState);
      setNodes((current) =>
        current.map((node) =>
          node.id === updated.id
            ? {
                ...node,
                identificador: updated.identificador,
                descripcion: updated.descripcion,
                estado: updated.estado,
                estado_conectividad: updated.estado_conectividad,
                ultimo_heartbeat: updated.ultimo_heartbeat,
                updated_at: updated.updated_at,
                ambiente: {
                  id: updated.ambiente_id,
                  nombre:
                    updated.ambiente_nombre ??
                    node.ambiente.nombre,
                },
              }
            : node,
        ),
      );
      setFeedback("Estado operativo del nodo actualizado.");
    } catch (requestError) {
      setError(
        getApiErrorMessage(
          requestError,
          "No pudimos actualizar el estado del nodo.",
        ),
      );
    } finally {
      setSaving(false);
    }
  }

  async function handleTokenAction(action: NodeTokenAction) {
    if (!selectedNodeId) {
      setError("Selecciona un nodo antes de gestionar su token.");
      return;
    }

    setManagingToken(true);
    setError(null);
    setFeedback(null);

    try {
      const result = await manageNodeToken(selectedNodeId, action);
      setLastTokenResult({
        nodeId: result.nodo_id,
        action: result.accion,
        status: result.estado_token,
        token: result.token ?? null,
      });
      setFeedback(
        action === "revoke"
          ? "Token revocado correctamente."
          : "Token generado correctamente. Guardalo en el firmware del nodo.",
      );
    } catch (requestError) {
      setError(
        getApiErrorMessage(
          requestError,
          "No pudimos gestionar el token del nodo.",
        ),
      );
    } finally {
      setManagingToken(false);
    }
  }

  const selectedNode =
    selectedNodeId === ""
      ? null
      : nodes.find((node) => node.id === selectedNodeId) ?? null;

  return (
    <section className="page-section">
      <header className="page-header">
        <span className="eyebrow">Gestion</span>
        <h2>Nodos de acceso</h2>
        <p>
          Este modulo registra nodos, cambia su estado operativo y gestiona
          tokens. Para el listado operativo reaprovecha `GET /access/nodes/status`.
        </p>
      </header>

      <section className="management-grid">
        <article className="monitor-card">
          <div className="section-heading">
            <div>
              <span className="eyebrow">Alta</span>
              <h3>Registrar nodo</h3>
            </div>
          </div>

          <form className="management-form" onSubmit={handleCreateNode}>
            <label>
              Identificador
              <input
                onChange={(event) => handleChange("identificador", event)}
                placeholder="NODO-LAB-01"
                value={form.identificador}
              />
            </label>
            <label>
              Descripcion
              <input
                onChange={(event) => handleChange("descripcion", event)}
                placeholder="Ingreso laboratorio A"
                value={form.descripcion}
              />
            </label>
            <label>
              Ambiente
              <select
                onChange={(event) => handleChange("id_ambiente", event)}
                value={form.id_ambiente}
              >
                <option value="">Selecciona un ambiente</option>
                {environments.map((environment) => (
                  <option key={environment.id} value={environment.id}>
                    {environment.nombre}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Estado inicial
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
                {creating ? "Registrando..." : "Registrar nodo"}
              </button>
            </div>
          </form>
        </article>

        <article className="monitor-card">
          <div className="section-heading">
            <div>
              <span className="eyebrow">Operacion</span>
              <h3>Estado y token</h3>
            </div>
            <StatusPill tone={selectedNode ? "success" : "neutral"}>
              {selectedNode ? "Nodo cargado" : "Sin seleccion"}
            </StatusPill>
          </div>

          {selectedNode ? (
            <div className="management-form">
              <label>
                Nodo seleccionado
                <input readOnly value={selectedNode.identificador} />
              </label>
              <label>
                Estado operativo
                <select
                  onChange={(event) =>
                    setSelectedNodeState(
                      event.target.value === "inactivo" ? "inactivo" : "activo",
                    )
                  }
                  value={selectedNodeState}
                >
                  <option value="activo">Activo</option>
                  <option value="inactivo">Inactivo</option>
                </select>
              </label>

              <div className="button-row">
                <button
                  className="primary-button"
                  disabled={saving}
                  onClick={handleUpdateStatus}
                  type="button"
                >
                  {saving ? "Guardando..." : "Guardar estado"}
                </button>
                <button
                  className="link-button"
                  disabled={managingToken}
                  onClick={() => handleTokenAction("generate")}
                  type="button"
                >
                  Generar token
                </button>
                <button
                  className="link-button"
                  disabled={managingToken}
                  onClick={() => handleTokenAction("regenerate")}
                  type="button"
                >
                  Regenerar token
                </button>
                <button
                  className="ghost-button"
                  disabled={managingToken}
                  onClick={() => handleTokenAction("revoke")}
                  type="button"
                >
                  Revocar token
                </button>
              </div>

              {lastTokenResult && lastTokenResult.nodeId === selectedNode.id && (
                <div className="token-result">
                  <strong>
                    Ultima accion: {lastTokenResult.action} ({lastTokenResult.status})
                  </strong>
                  <code>{lastTokenResult.token ?? "Sin token plano devuelto."}</code>
                </div>
              )}
            </div>
          ) : (
            <p className="empty-copy">
              Selecciona un nodo del listado para administrar su estado y su token.
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
            <h3>Nodos visibles</h3>
          </div>
          <StatusPill tone={loading ? "warning" : "neutral"}>
            {loading ? "Cargando..." : `${nodes.length} visibles`}
          </StatusPill>
        </div>

        {loading ? (
          <p className="empty-copy">Cargando nodos registrados...</p>
        ) : nodes.length === 0 ? (
          <p className="empty-copy">
            Aun no hay nodos visibles para administrar.
          </p>
        ) : (
          <div className="management-card-grid">
            {nodes.map((node) => (
              <article className="node-card management-card" key={node.id}>
                <div className="node-card-header">
                  <div>
                    <strong>{node.identificador}</strong>
                    <span>{node.ambiente.nombre}</span>
                  </div>
                  <StatusPill
                    tone={
                      node.estado_conectividad === "en-linea"
                        ? "success"
                        : "danger"
                    }
                  >
                    {node.estado_conectividad === "en-linea"
                      ? "En linea"
                      : "Sin conexion"}
                  </StatusPill>
                </div>

                <p>{node.descripcion || "Sin descripcion operativa."}</p>

                <dl className="node-meta">
                  <div>
                    <dt>Estado</dt>
                    <dd>{node.estado}</dd>
                  </div>
                  <div>
                    <dt>Heartbeat</dt>
                    <dd>{formatTimestamp(node.ultimo_heartbeat)}</dd>
                  </div>
                </dl>

                <div className="button-row">
                  <button
                    className="ghost-button"
                    onClick={() => selectNode(node)}
                    type="button"
                  >
                    Administrar
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
