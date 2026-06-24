import type { ChangeEvent, FormEvent } from "react";
import { useEffect, useMemo, useState } from "react";
import axios from "axios";

import { StatusPill } from "../components/status-pill";
import { getFriendlyErrorMessage } from "../lib/error-messages";
import {
  exportReportEventsCsv,
  fetchAttendanceSummary,
  fetchReportEvents,
  getDefaultReportFilters,
} from "../lib/reports";
import type {
  AttendanceSummaryResult,
  ReportEvent,
  ReportEventsResult,
  ReportFilters,
} from "../types/reports";

const EMPTY_REPORTS_RESULT: ReportEventsResult = {
  data: [],
  total: 0,
  page: 1,
  pageSize: 25,
  pages: 1,
};

function formatTimestamp(value: string | null) {
  if (!value) {
    return "Sin timestamp";
  }

  return new Intl.DateTimeFormat("es-PE", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function formatRangeLabel(startDate: string, endDate: string) {
  if (!startDate || !endDate) {
    return "Rango pendiente";
  }

  return `${startDate} -> ${endDate}`;
}

function getApiErrorMessage(error: unknown, fallback: string) {
  if (axios.isAxiosError(error)) {
    const code = error.response?.data?.error as string | undefined;
    return getFriendlyErrorMessage(code);
  }

  return fallback;
}

function validateFilters(filters: ReportFilters) {
  if (!filters.startDate || !filters.endDate) {
    return "Completa la fecha inicial y final para consultar reportes.";
  }

  if (filters.endDate < filters.startDate) {
    return "La fecha final no puede ser anterior a la fecha inicial.";
  }

  return null;
}

export function ReportsPage() {
  const [draftFilters, setDraftFilters] = useState<ReportFilters>(() =>
    getDefaultReportFilters(),
  );
  const [appliedFilters, setAppliedFilters] = useState<ReportFilters>(() =>
    getDefaultReportFilters(),
  );
  const [eventsResult, setEventsResult] =
    useState<ReportEventsResult>(EMPTY_REPORTS_RESULT);
  const [summaryResult, setSummaryResult] =
    useState<AttendanceSummaryResult | null>(null);
  const [eventsError, setEventsError] = useState<string | null>(null);
  const [summaryError, setSummaryError] = useState<string | null>(null);
  const [isLoadingEvents, setIsLoadingEvents] = useState(true);
  const [isLoadingSummary, setIsLoadingSummary] = useState(false);
  const [isExporting, setIsExporting] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function loadEvents() {
      setIsLoadingEvents(true);
      setEventsError(null);

      try {
        const result = await fetchReportEvents(appliedFilters);
        if (!cancelled) {
          setEventsResult(result);
        }
      } catch (error) {
        if (!cancelled) {
          setEventsResult((current) => ({
            ...current,
            data: [],
            total: 0,
            pages: 1,
          }));
          setEventsError(
            getApiErrorMessage(
              error,
              "No pudimos cargar los reportes de acceso con los filtros actuales.",
            ),
          );
        }
      } finally {
        if (!cancelled) {
          setIsLoadingEvents(false);
        }
      }
    }

    void loadEvents();

    return () => {
      cancelled = true;
    };
  }, [appliedFilters]);

  const deniedCount = useMemo(
    () => eventsResult.data.filter((event) => event.result === "denegado").length,
    [eventsResult.data],
  );

  function handleFilterInputChange(
    field: keyof Pick<
      ReportFilters,
      "startDate" | "endDate" | "studentId" | "environmentId"
    >,
    event: ChangeEvent<HTMLInputElement>,
  ) {
    const nextValue = event.target.value;
    setDraftFilters((current) => ({
      ...current,
      [field]: nextValue,
    }));
  }

  function handlePageSizeChange(event: ChangeEvent<HTMLSelectElement>) {
    const nextPageSize = Number(event.target.value);
    setDraftFilters((current) => ({
      ...current,
      page: 1,
      pageSize: nextPageSize,
    }));
    setAppliedFilters((current) => ({
      ...current,
      page: 1,
      pageSize: nextPageSize,
    }));
  }

  function handleSearchSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const validationError = validateFilters(draftFilters);
    if (validationError) {
      setEventsError(validationError);
      return;
    }

    setAppliedFilters({
      ...draftFilters,
      page: 1,
      pageSize: draftFilters.pageSize,
    });
  }

  function handleClearIds() {
    setDraftFilters((current) => ({
      ...current,
      studentId: "",
      environmentId: "",
    }));
  }

  async function handleExportCsv() {
    const validationError = validateFilters(appliedFilters);
    if (validationError) {
      setEventsError(validationError);
      return;
    }

    setIsExporting(true);
    setEventsError(null);

    try {
      await exportReportEventsCsv(appliedFilters);
    } catch (error) {
      setEventsError(
        getApiErrorMessage(
          error,
          "No pudimos exportar el CSV con el filtro aplicado.",
        ),
      );
    } finally {
      setIsExporting(false);
    }
  }

  async function handleLoadSummary() {
    const validationError = validateFilters(draftFilters);
    if (validationError) {
      setSummaryError(validationError);
      return;
    }

    if (!draftFilters.studentId.trim()) {
      setSummaryResult(null);
      setSummaryError(
        "Ingresa un ID de estudiante para obtener el resumen por ambiente.",
      );
      return;
    }

    setIsLoadingSummary(true);
    setSummaryError(null);

    try {
      const result = await fetchAttendanceSummary(
        draftFilters.studentId.trim(),
        draftFilters.startDate,
        draftFilters.endDate,
      );
      setSummaryResult(result);
    } catch (error) {
      setSummaryResult(null);
      setSummaryError(
        getApiErrorMessage(
          error,
          "No pudimos cargar el resumen por estudiante.",
        ),
      );
    } finally {
      setIsLoadingSummary(false);
    }
  }

  function handlePageChange(nextPage: number) {
    setDraftFilters((current) => ({
      ...current,
      page: nextPage,
    }));
    setAppliedFilters((current) => ({
      ...current,
      page: nextPage,
    }));
  }

  return (
    <section className="page-section">
      <header className="page-header">
        <span className="eyebrow">Analitica</span>
        <h2>Reportes de asistencia</h2>
        <p>
          Consulta `GET /reports/events`, exporta CSV del rango aplicado y
          obtiene el resumen por estudiante con `GET /reports/attendance-summary`.
        </p>
      </header>

      <div className="stat-grid">
        <article className="stat-card cool">
          <strong>Coincidencias</strong>
          <span>{eventsResult.total} eventos cumplen el filtro actual.</span>
          <div className="stat-card-footer">
            <StatusPill tone="neutral">
              {formatRangeLabel(appliedFilters.startDate, appliedFilters.endDate)}
            </StatusPill>
          </div>
        </article>
        <article className="stat-card">
          <strong>Paginacion activa</strong>
          <span>
            Pagina {eventsResult.page} de {eventsResult.pages} con{" "}
            {eventsResult.pageSize} registros por consulta.
          </span>
        </article>
        <article className="stat-card warm">
          <strong>Alertas visibles</strong>
          <span>
            {deniedCount} eventos denegados en la pagina actualmente cargada.
          </span>
        </article>
      </div>

      <section className="filters-card">
        <div className="filters-heading">
          <div>
            <span className="eyebrow">Filtro principal</span>
            <h3>Consulta y exportacion</h3>
          </div>
          {eventsError && <div className="form-alert compact">{eventsError}</div>}
        </div>

        <form className="reports-form" onSubmit={handleSearchSubmit}>
          <div className="filters-grid reports-grid">
            <label>
              Fecha inicial
              <input
                onChange={(event) => handleFilterInputChange("startDate", event)}
                type="date"
                value={draftFilters.startDate}
              />
            </label>

            <label>
              Fecha final
              <input
                onChange={(event) => handleFilterInputChange("endDate", event)}
                type="date"
                value={draftFilters.endDate}
              />
            </label>

            <label>
              ID de estudiante
              <input
                onChange={(event) => handleFilterInputChange("studentId", event)}
                placeholder="UUID opcional"
                value={draftFilters.studentId}
              />
            </label>

            <label>
              ID de ambiente
              <input
                onChange={(event) =>
                  handleFilterInputChange("environmentId", event)
                }
                placeholder="UUID opcional"
                value={draftFilters.environmentId}
              />
            </label>
          </div>

          <div className="report-toolbar">
            <label className="inline-select">
              Registros por pagina
              <select onChange={handlePageSizeChange} value={draftFilters.pageSize}>
                <option value={10}>10</option>
                <option value={25}>25</option>
                <option value={50}>50</option>
                <option value={100}>100</option>
              </select>
            </label>

            <div className="button-row">
              <button className="primary-button" type="submit">
                {isLoadingEvents ? "Consultando..." : "Consultar eventos"}
              </button>
              <button
                className="ghost-button"
                onClick={handleClearIds}
                type="button"
              >
                Limpiar IDs
              </button>
              <button
                className="link-button"
                disabled={isExporting || eventsResult.total === 0}
                onClick={handleExportCsv}
                type="button"
              >
                {isExporting ? "Exportando CSV..." : "Exportar CSV"}
              </button>
            </div>
          </div>

          <p className="inline-note">
            Usa los IDs opcionales solo cuando necesites acotar por estudiante o
            ambiente exacto. El backend limita la consulta a 90 dias y 10 000
            registros.
          </p>
        </form>
      </section>

      <section className="monitor-grid reports-layout">
        <article className="monitor-card">
          <div className="section-heading">
            <div>
              <span className="eyebrow">Listado</span>
              <h3>Eventos encontrados</h3>
            </div>
            <StatusPill tone={isLoadingEvents ? "warning" : "success"}>
              {isLoadingEvents ? "Actualizando" : `${eventsResult.total} total`}
            </StatusPill>
          </div>

          {isLoadingEvents ? (
            <p className="empty-copy">Cargando eventos del rango solicitado...</p>
          ) : eventsResult.data.length === 0 ? (
            <p className="empty-copy">
              No se encontraron eventos para los filtros aplicados.
            </p>
          ) : (
            <>
              <div className="table-wrap">
                <table className="events-table">
                  <thead>
                    <tr>
                      <th>Timestamp</th>
                      <th>Ambiente</th>
                      <th>Estudiante</th>
                      <th>Tag RFID</th>
                      <th>Resultado</th>
                    </tr>
                  </thead>
                  <tbody>
                    {eventsResult.data.map((event: ReportEvent) => (
                      <tr key={event.id}>
                        <td>
                          <strong>{formatTimestamp(event.timestamp)}</strong>
                          <span className="subtext">{event.id}</span>
                        </td>
                        <td>{event.environmentName ?? "Ambiente no resuelto"}</td>
                        <td>{event.studentName ?? "Tag no registrado"}</td>
                        <td>{event.tagRfid}</td>
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

              <div className="pagination-bar">
                <span>
                  Mostrando pagina {eventsResult.page} de {eventsResult.pages}.
                </span>
                <div className="button-row">
                  <button
                    className="ghost-button"
                    disabled={eventsResult.page <= 1 || isLoadingEvents}
                    onClick={() => handlePageChange(eventsResult.page - 1)}
                    type="button"
                  >
                    Anterior
                  </button>
                  <button
                    className="ghost-button"
                    disabled={
                      eventsResult.page >= eventsResult.pages || isLoadingEvents
                    }
                    onClick={() => handlePageChange(eventsResult.page + 1)}
                    type="button"
                  >
                    Siguiente
                  </button>
                </div>
              </div>
            </>
          )}
        </article>

        <article className="monitor-card">
          <div className="section-heading">
            <div>
              <span className="eyebrow">Resumen</span>
              <h3>Asistencia por estudiante</h3>
            </div>
          </div>

          <p className="inline-note">
            El resumen agrega autorizados y denegados por ambiente dentro del
            rango del formulario.
          </p>

          <div className="button-row">
            <button
              className="primary-button"
              disabled={isLoadingSummary}
              onClick={handleLoadSummary}
              type="button"
            >
              {isLoadingSummary ? "Consultando resumen..." : "Ver resumen"}
            </button>
          </div>

          {summaryError && <div className="form-alert compact">{summaryError}</div>}

          {isLoadingSummary ? (
            <p className="empty-copy">Construyendo resumen por ambiente...</p>
          ) : !summaryResult ? (
            <p className="empty-copy">
              Ingresa un `ID de estudiante` y ejecuta la consulta para ver su
              resumen.
            </p>
          ) : summaryResult.data.length === 0 ? (
            <p className="empty-copy">
              No hay eventos agregados para el estudiante y rango seleccionados.
            </p>
          ) : (
            <div className="summary-grid">
              {summaryResult.data.map((row) => (
                <article className="node-card summary-card" key={row.environmentId}>
                  <div className="node-card-header">
                    <div>
                      <strong>{row.environmentName}</strong>
                      <span>{summaryResult.studentId}</span>
                    </div>
                    <StatusPill tone="neutral">{`${row.total} eventos`}</StatusPill>
                  </div>

                  <dl className="node-meta">
                    <div>
                      <dt>Autorizados</dt>
                      <dd>{row.authorized}</dd>
                    </div>
                    <div>
                      <dt>Denegados</dt>
                      <dd>{row.denied}</dd>
                    </div>
                  </dl>
                </article>
              ))}
            </div>
          )}
        </article>
      </section>
    </section>
  );
}
