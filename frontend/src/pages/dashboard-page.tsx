import { ChangeEvent } from "react";

import { StatusPill } from "../components/status-pill";
import { useAccessEvents } from "../hooks/use-access-events";

function formatTimestamp(value: string | null) {
  if (!value) {
    return "Sin registro";
  }

  return new Intl.DateTimeFormat("es-PE", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export function DashboardPage() {
  const {
    events,
    totalEvents,
    nodes,
    totalNodes,
    onlineNodes,
    filters,
    setFilters,
    environmentOptions,
    isBootstrapping,
    error,
    streamState,
  } = useAccessEvents();

  function handleFilterChange(
    field: "environment" | "date" | "result",
    event: ChangeEvent<HTMLSelectElement | HTMLInputElement>,
  ) {
    const nextValue = event.target.value;
    setFilters((current) => ({
      ...current,
      [field]: nextValue,
    }));
  }

  const streamTone =
    streamState === "live"
      ? "success"
      : streamState === "retrying"
        ? "warning"
        : streamState === "connecting"
          ? "neutral"
          : "danger";

  const streamLabel =
    streamState === "live"
      ? "SSE en vivo"
      : streamState === "retrying"
        ? "Reconectando"
        : streamState === "connecting"
          ? "Conectando"
          : "Sin stream";

  return (
    <section className="page-section">
      <header className="page-header">
        <span className="eyebrow">Monitoreo</span>
        <h2>Panel operativo en tiempo real</h2>
        <p>
          Esta vista consume `GET /access/events`, `GET /access/nodes/status` y
          el stream autenticado `GET /access/events/stream` para reflejar
          actividad y conectividad de nodos.
        </p>
      </header>

      <div className="stat-grid">
        <article className="stat-card warm">
          <strong>Canal en tiempo real</strong>
          <span>{streamLabel}</span>
          <div className="stat-card-footer">
            <StatusPill tone={streamTone}>{streamLabel}</StatusPill>
          </div>
        </article>
        <article className="stat-card">
          <strong>Nodos conectados</strong>
          <span>
            {onlineNodes} de {totalNodes} nodos reportan estado `en-linea`.
          </span>
        </article>
        <article className="stat-card cool">
          <strong>Eventos visibles</strong>
          <span>
            {events.length} eventos filtrados de un total local de {totalEvents}.
          </span>
        </article>
      </div>

      <section className="filters-card">
        <div className="filters-heading">
          <div>
            <span className="eyebrow">Filtros AND</span>
            <h3>Acota el monitoreo operativo</h3>
          </div>
          {error && <div className="form-alert compact">{error}</div>}
        </div>

        <div className="filters-grid">
          <label>
            Ambiente
            <select
              onChange={(event) => handleFilterChange("environment", event)}
              value={filters.environment}
            >
              <option value="">Todos</option>
              {environmentOptions.map((environment) => (
                <option key={environment} value={environment}>
                  {environment}
                </option>
              ))}
            </select>
          </label>

          <label>
            Fecha
            <input
              onChange={(event) => handleFilterChange("date", event)}
              type="date"
              value={filters.date}
            />
          </label>

          <label>
            Resultado
            <select
              onChange={(event) => handleFilterChange("result", event)}
              value={filters.result}
            >
              <option value="all">Todos</option>
              <option value="autorizado">Autorizado</option>
              <option value="denegado">Denegado</option>
            </select>
          </label>
        </div>
      </section>

      <section className="monitor-grid">
        <article className="monitor-card">
          <div className="section-heading">
            <div>
              <span className="eyebrow">Estado de nodos</span>
              <h3>Conectividad por ambiente</h3>
            </div>
          </div>

          <div className="nodes-grid">
            {nodes.length === 0 && !isBootstrapping ? (
              <p className="empty-copy">
                Aun no hay nodos registrados para mostrar.
              </p>
            ) : (
              nodes.map((node) => (
                <article className="node-card" key={node.id}>
                  <div className="node-card-header">
                    <div>
                      <strong>{node.identifier}</strong>
                      <span>{node.environmentName}</span>
                    </div>
                    <StatusPill
                      tone={
                        node.connectivity === "en-linea" ? "success" : "danger"
                      }
                    >
                      {node.connectivity === "en-linea"
                        ? "En linea"
                        : "Sin conexion"}
                    </StatusPill>
                  </div>

                  <p>{node.description || "Sin descripcion operativa."}</p>

                  <dl className="node-meta">
                    <div>
                      <dt>Estado operativo</dt>
                      <dd>{node.state}</dd>
                    </div>
                    <div>
                      <dt>Ultimo heartbeat</dt>
                      <dd>{formatTimestamp(node.lastHeartbeat)}</dd>
                    </div>
                  </dl>
                </article>
              ))
            )}
          </div>
        </article>

        <article className="monitor-card">
          <div className="section-heading">
            <div>
              <span className="eyebrow">Eventos recientes</span>
              <h3>Ingreso de estudiantes</h3>
            </div>
          </div>

          {isBootstrapping ? (
            <p className="empty-copy">Cargando monitoreo inicial...</p>
          ) : events.length === 0 ? (
            <p className="empty-copy">
              No hay eventos que coincidan con los filtros activos.
            </p>
          ) : (
            <div className="table-wrap">
              <table className="events-table">
                <thead>
                  <tr>
                    <th>Estudiante</th>
                    <th>Ambiente</th>
                    <th>Timestamp</th>
                    <th>Resultado</th>
                  </tr>
                </thead>
                <tbody>
                  {events.map((event) => (
                    <tr key={event.id}>
                      <td>
                        <strong>{event.studentName ?? "Tag no registrado"}</strong>
                        <span className="subtext">
                          {event.studentCode ?? event.tagRfid ?? "Sin codigo"}
                        </span>
                      </td>
                      <td>{event.environmentName ?? "Ambiente no resuelto"}</td>
                      <td>{formatTimestamp(event.timestamp)}</td>
                      <td>
                        <StatusPill
                          tone={
                            event.result === "autorizado" ? "success" : "danger"
                          }
                        >
                          {event.result === "autorizado"
                            ? "Autorizado"
                            : event.resultCode
                              ? `Denegado: ${event.resultCode}`
                              : "Denegado"}
                        </StatusPill>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </article>
      </section>
    </section>
  );
}
