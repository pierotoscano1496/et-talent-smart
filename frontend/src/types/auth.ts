export type UserRole = "ADMINISTRADOR" | "AUXILIAR_EDUCACION";

export type LoginResponse = {
  token: string;
  rol: UserRole;
  nombre: string;
  primer_login: boolean;
};

export type SessionSnapshot = {
  token: string;
  role: UserRole;
  displayName: string;
  firstLogin: boolean;
};
