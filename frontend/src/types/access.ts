export type AccessEventResult = "autorizado" | "denegado";

export type AccessEventApiRecord = {
  id: string;
  tag_rfid: string;
  timestamp_utc: string;
  resultado: AccessEventResult;
  codigo_resultado: string | null;
  origen: string;
  nodo: {
    id: string;
    identificador: string;
    estado: string;
  };
  ambiente: {
    id: string;
    nombre: string;
  };
  estudiante: {
    id: string;
    nombre_completo: string;
    codigo: string;
  } | null;
};

export type AccessEventsApiResponse = {
  data: AccessEventApiRecord[];
  total: number;
  page: number;
  page_size: number;
};

export type NodeStatusApiRecord = {
  id: string;
  identificador: string;
  descripcion: string;
  estado: string;
  estado_conectividad: "en-linea" | "sin-conexion";
  ultimo_heartbeat: string | null;
  updated_at: string | null;
  ambiente: {
    id: string;
    nombre: string;
  };
};

export type NodeStatusApiResponse = {
  data: NodeStatusApiRecord[];
  total: number;
};

export type AccessStreamPayload =
  | {
      evento_id: string;
      estudiante: string | null;
      ambiente: string | null;
      timestamp: string;
      resultado: AccessEventResult;
      codigo_resultado?: string | null;
    }
  | {
      tipo: "node_status";
      node_id: string;
      estado: "en-linea" | "sin-conexion";
    };

export type MonitoringEvent = {
  id: string;
  tagRfid: string | null;
  timestamp: string;
  result: AccessEventResult;
  resultCode: string | null;
  studentName: string | null;
  studentCode: string | null;
  environmentId: string | null;
  environmentName: string | null;
  nodeId: string | null;
  nodeIdentifier: string | null;
  source: string;
};

export type MonitoringNode = {
  id: string;
  identifier: string;
  description: string;
  state: string;
  connectivity: "en-linea" | "sin-conexion";
  lastHeartbeat: string | null;
  updatedAt: string | null;
  environmentId: string;
  environmentName: string;
};

export type DashboardFilters = {
  environment: string;
  date: string;
  result: "all" | AccessEventResult;
};
