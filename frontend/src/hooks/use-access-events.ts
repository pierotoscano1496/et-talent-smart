import { useDeferredValue, useEffect, useMemo, useState } from "react";

import {
  fetchAccessEvents,
  fetchNodeStatuses,
  streamAccessEvents,
} from "../lib/access";
import { useAuthStore } from "../store/auth-store";
import type {
  AccessEventApiRecord,
  AccessStreamPayload,
  DashboardFilters,
  MonitoringEvent,
  MonitoringNode,
  NodeStatusApiRecord,
} from "../types/access";

const STREAM_RETRY_MS = 3000;
const MAX_EVENTS = 250;

function normalizeApiEvent(event: AccessEventApiRecord): MonitoringEvent {
  return {
    id: event.id,
    tagRfid: event.tag_rfid,
    timestamp: event.timestamp_utc,
    result: event.resultado,
    resultCode: event.codigo_resultado,
    studentName: event.estudiante?.nombre_completo ?? null,
    studentCode: event.estudiante?.codigo ?? null,
    environmentId: event.ambiente.id,
    environmentName: event.ambiente.nombre,
    nodeId: event.nodo.id,
    nodeIdentifier: event.nodo.identificador,
    source: event.origen,
  };
}

function normalizeNode(node: NodeStatusApiRecord): MonitoringNode {
  return {
    id: node.id,
    identifier: node.identificador,
    description: node.descripcion,
    state: node.estado,
    connectivity: node.estado_conectividad,
    lastHeartbeat: node.ultimo_heartbeat,
    updatedAt: node.updated_at,
    environmentId: node.ambiente.id,
    environmentName: node.ambiente.nombre,
  };
}

function normalizeStreamEvent(payload: Exclude<AccessStreamPayload, { tipo: "node_status" }>): MonitoringEvent {
  return {
    id: payload.evento_id,
    tagRfid: null,
    timestamp: payload.timestamp,
    result: payload.resultado,
    resultCode: payload.codigo_resultado ?? null,
    studentName: payload.estudiante ?? null,
    studentCode: null,
    environmentId: null,
    environmentName: payload.ambiente ?? null,
    nodeId: null,
    nodeIdentifier: null,
    source: "stream",
  };
}

function isNodeStatusPayload(
  payload: AccessStreamPayload,
): payload is Extract<AccessStreamPayload, { tipo: "node_status" }> {
  return "tipo" in payload && payload.tipo === "node_status";
}

function sortEventsDescending(events: MonitoringEvent[]) {
  return [...events].sort(
    (left, right) =>
      new Date(right.timestamp).getTime() - new Date(left.timestamp).getTime(),
  );
}

function applyFilters(events: MonitoringEvent[], filters: DashboardFilters) {
  return events.filter((event) => {
    const sameEnvironment =
      !filters.environment || event.environmentName === filters.environment;
    const sameResult =
      filters.result === "all" || event.result === filters.result;
    const sameDate =
      !filters.date || event.timestamp.slice(0, 10) === filters.date;

    return sameEnvironment && sameResult && sameDate;
  });
}

function upsertStreamEvent(
  currentEvents: MonitoringEvent[],
  payload: Exclude<AccessStreamPayload, { tipo: "node_status" }>,
) {
  const normalized = normalizeStreamEvent(payload);
  const next = [normalized, ...currentEvents.filter((event) => event.id !== normalized.id)];
  return sortEventsDescending(next).slice(0, MAX_EVENTS);
}

function patchNodeConnectivity(
  currentNodes: MonitoringNode[],
  payload: Extract<AccessStreamPayload, { tipo: "node_status" }>,
) {
  return currentNodes.map((node) =>
    node.identifier === payload.node_id
      ? {
          ...node,
          connectivity: payload.estado,
          updatedAt: new Date().toISOString(),
          lastHeartbeat:
            payload.estado === "en-linea"
              ? new Date().toISOString()
              : node.lastHeartbeat,
        }
      : node,
  );
}

export function useAccessEvents() {
  const token = useAuthStore((state) => state.token);

  const [events, setEvents] = useState<MonitoringEvent[]>([]);
  const [nodes, setNodes] = useState<MonitoringNode[]>([]);
  const [filters, setFilters] = useState<DashboardFilters>({
    environment: "",
    date: "",
    result: "all",
  });
  const [isBootstrapping, setIsBootstrapping] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [streamState, setStreamState] = useState<
    "connecting" | "live" | "retrying" | "offline"
  >("connecting");

  useEffect(() => {
    if (!token) {
      setEvents([]);
      setNodes([]);
      setStreamState("offline");
      setIsBootstrapping(false);
      return;
    }

    let cancelled = false;

    async function bootstrap() {
      setIsBootstrapping(true);
      setError(null);

      try {
        const [eventsResponse, nodesResponse] = await Promise.all([
          fetchAccessEvents(),
          fetchNodeStatuses(),
        ]);

        if (cancelled) {
          return;
        }

        setEvents(sortEventsDescending(eventsResponse.data.map(normalizeApiEvent)));
        setNodes(nodesResponse.data.map(normalizeNode));
      } catch {
        if (!cancelled) {
          setError(
            "No pudimos cargar el monitoreo inicial. Revisa el acceso al backend.",
          );
        }
      } finally {
        if (!cancelled) {
          setIsBootstrapping(false);
        }
      }
    }

    void bootstrap();

    return () => {
      cancelled = true;
    };
  }, [token]);

  useEffect(() => {
    if (!token) {
      return;
    }

    const abortController = new AbortController();
    let retryTimer: number | null = null;

    const connect = async () => {
      setStreamState("connecting");

      try {
        await streamAccessEvents({
          token,
          signal: abortController.signal,
          onMessage: (payload) => {
            setError(null);
            setStreamState("live");

            if (isNodeStatusPayload(payload)) {
              setNodes((currentNodes) =>
                patchNodeConnectivity(currentNodes, payload),
              );
              return;
            }

            setEvents((currentEvents) =>
              upsertStreamEvent(currentEvents, payload),
            );
          },
        });

        if (!abortController.signal.aborted) {
          setStreamState("retrying");
          retryTimer = window.setTimeout(() => {
            void connect();
          }, STREAM_RETRY_MS);
        }
      } catch {
        if (abortController.signal.aborted) {
          return;
        }

        setStreamState("retrying");
        setError(
          "Se perdio la conexion en tiempo real. Intentaremos reconectar automaticamente.",
        );
        retryTimer = window.setTimeout(() => {
          void connect();
        }, STREAM_RETRY_MS);
      }
    };

    void connect();

    return () => {
      abortController.abort();
      if (retryTimer !== null) {
        window.clearTimeout(retryTimer);
      }
    };
  }, [token]);

  const filteredEvents = useMemo(
    () => applyFilters(events, filters),
    [events, filters],
  );
  const deferredFilteredEvents = useDeferredValue(filteredEvents);

  const environmentOptions = useMemo(() => {
    const names = new Set<string>();

    nodes.forEach((node) => names.add(node.environmentName));
    events.forEach((event) => {
      if (event.environmentName) {
        names.add(event.environmentName);
      }
    });

    return [...names].sort((left, right) => left.localeCompare(right));
  }, [events, nodes]);

  const onlineNodes = useMemo(
    () => nodes.filter((node) => node.connectivity === "en-linea").length,
    [nodes],
  );

  return {
    events: deferredFilteredEvents,
    totalEvents: events.length,
    nodes,
    totalNodes: nodes.length,
    onlineNodes,
    filters,
    setFilters,
    environmentOptions,
    isBootstrapping,
    error,
    streamState,
  };
}
