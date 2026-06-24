import type { AccessEventResult } from "./access";

export type ReportEventApiRecord = {
  evento_id: string;
  tag_rfid: string;
  nodo_id: string;
  ambiente_nombre: string | null;
  estudiante_nombre: string | null;
  timestamp_utc: string | null;
  resultado: AccessEventResult;
  codigo_resultado: string | null;
};

export type ReportEventsApiResponse = {
  data: ReportEventApiRecord[];
  total: number;
  page?: number;
  page_size?: number;
  pages?: number;
};

export type AttendanceSummaryApiRecord = {
  ambiente: {
    id: string;
    nombre: string;
  };
  autorizados: number;
  denegados: number;
  total: number;
};

export type AttendanceSummaryApiResponse = {
  data: AttendanceSummaryApiRecord[];
  total: number;
  id_estudiante: string;
  fecha_inicio: string;
  fecha_fin: string;
};

export type ReportFilters = {
  startDate: string;
  endDate: string;
  studentId: string;
  environmentId: string;
  page: number;
  pageSize: number;
};

export type ReportEvent = {
  id: string;
  tagRfid: string;
  nodeId: string;
  environmentName: string | null;
  studentName: string | null;
  timestamp: string | null;
  result: AccessEventResult;
  resultCode: string | null;
};

export type AttendanceSummaryRecord = {
  environmentId: string;
  environmentName: string;
  authorized: number;
  denied: number;
  total: number;
};

export type ReportEventsResult = {
  data: ReportEvent[];
  total: number;
  page: number;
  pageSize: number;
  pages: number;
};

export type AttendanceSummaryResult = {
  data: AttendanceSummaryRecord[];
  total: number;
  studentId: string;
  startDate: string;
  endDate: string;
};
