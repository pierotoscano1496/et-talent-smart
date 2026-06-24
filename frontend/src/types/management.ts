import type { NodeStatusApiRecord } from "./access";

export type PaginatedResponse<T> = {
  data: T[];
  total: number;
  page: number;
  page_size: number;
};

export type StudentRecord = {
  id: string;
  nombre_completo: string;
  codigo: string;
  grado_seccion: string;
  estado: "activo" | "inactivo";
  tag_rfid: string | null;
  created_at: string | null;
  updated_at: string | null;
};

export type EnvironmentRecord = {
  id: string;
  nombre: string;
  descripcion: string;
  ubicacion: string;
  estado: "activo" | "inactivo";
  created_at: string | null;
  updated_at: string | null;
};

export type ManagedNodeRecord = {
  id: string;
  identificador: string;
  descripcion: string;
  estado: "activo" | "inactivo";
  estado_conectividad: "en-linea" | "sin-conexion";
  ultimo_heartbeat: string | null;
  ambiente_id: string;
  ambiente_nombre: string | null;
  token_activo?: boolean;
  created_at: string | null;
  updated_at: string | null;
};

export type NodeTokenAction = "generate" | "regenerate" | "revoke";

export type NodeTokenActionResult = {
  nodo_id: string;
  accion: NodeTokenAction;
  estado_token: "activo" | "revocado";
  token?: string;
};

export type WebUserRecord = {
  id: string;
  nombre_completo: string;
  email: string;
  rol: "ADMINISTRADOR" | "AUXILIAR_EDUCACION";
  estado: "activo" | "inactivo";
  primer_login: boolean;
  created_at: string | null;
  updated_at: string | null;
};

export type AdminNodeStatusRecord = NodeStatusApiRecord;
