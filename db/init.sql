-- =============================================================================
-- db/init.sql
-- Esquema inicial del sistema IoT de Control de Acceso RFID
-- Este script es idempotente (usa IF NOT EXISTS) y se ejecuta al arrancar
-- el contenedor de PostgreSQL.
-- =============================================================================

-- Extensión para generación de UUIDs
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- -----------------------------------------------------------------------------
-- Tabla: usuario_web
-- Usuarios del sistema web (Administradores y Auxiliares de Educación)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS usuario_web (
    id              UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    nombre_completo VARCHAR(100)    NOT NULL,
    email           VARCHAR(254)    NOT NULL,
    password_hash   VARCHAR(60)     NOT NULL,
    rol             VARCHAR(20)     NOT NULL,
    estado          VARCHAR(20)     NOT NULL DEFAULT 'activo',
    primer_login    BOOLEAN         NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_usuario_web_email UNIQUE (email)
);

-- -----------------------------------------------------------------------------
-- Tabla: token_revocado
-- Lista negra de JWTs revocados (logout)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS token_revocado (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    jti         TEXT        NOT NULL,
    revocado_en TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expira_en   TIMESTAMPTZ NOT NULL,
    usuario_id  UUID        NOT NULL,
    CONSTRAINT uq_token_revocado_jti UNIQUE (jti),
    CONSTRAINT fk_token_revocado_usuario FOREIGN KEY (usuario_id)
        REFERENCES usuario_web (id) ON DELETE CASCADE
);

-- -----------------------------------------------------------------------------
-- Tabla: estudiante
-- Estudiantes registrados en el sistema
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS estudiante (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    nombre_completo VARCHAR(100) NOT NULL,
    codigo          VARCHAR(20) NOT NULL,
    grado_seccion   VARCHAR(20) NOT NULL,
    estado          VARCHAR(20) NOT NULL DEFAULT 'activo',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_estudiante_codigo UNIQUE (codigo)
);

-- -----------------------------------------------------------------------------
-- Tabla: tag_rfid
-- Tags RFID asociados a estudiantes
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS tag_rfid (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    uid_hex         VARCHAR(8)  NOT NULL,
    estudiante_id   UUID        NOT NULL,
    asignado_en     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    desasignado_en  TIMESTAMPTZ NULL,
    activo          BOOLEAN     NOT NULL DEFAULT TRUE,
    CONSTRAINT uq_tag_rfid_uid_hex UNIQUE (uid_hex),
    CONSTRAINT fk_tag_rfid_estudiante FOREIGN KEY (estudiante_id)
        REFERENCES estudiante (id) ON DELETE RESTRICT
);

-- -----------------------------------------------------------------------------
-- Tabla: ambiente
-- Espacios físicos educativos controlados por nodos de acceso
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ambiente (
    id          UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    nombre      VARCHAR(80)  NOT NULL,
    descripcion VARCHAR(255) NOT NULL DEFAULT '',
    ubicacion   VARCHAR(120) NOT NULL DEFAULT '',
    estado      VARCHAR(20)  NOT NULL DEFAULT 'activo',
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_ambiente_nombre UNIQUE (nombre)
);

-- -----------------------------------------------------------------------------
-- Tabla: nodo_acceso
-- Nodos físicos ESP32 + RC-522 instalados en los ambientes
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS nodo_acceso (
    id                   UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    identificador        VARCHAR(40) NOT NULL,
    descripcion          VARCHAR(255) NOT NULL DEFAULT '',
    estado               VARCHAR(20) NOT NULL DEFAULT 'activo',
    estado_conectividad  VARCHAR(20) NOT NULL DEFAULT 'sin-conexion',
    ultimo_heartbeat     TIMESTAMPTZ NULL,
    ambiente_id          UUID        NOT NULL,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_nodo_acceso_identificador UNIQUE (identificador),
    CONSTRAINT fk_nodo_acceso_ambiente FOREIGN KEY (ambiente_id)
        REFERENCES ambiente (id) ON DELETE RESTRICT
);

-- -----------------------------------------------------------------------------
-- Tabla: token_nodo
-- Tokens de autenticación de los nodos de acceso (se almacena hash)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS token_nodo (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    nodo_id     UUID        NOT NULL,
    token_hash  TEXT        NOT NULL,
    estado      VARCHAR(20) NOT NULL DEFAULT 'activo',
    generado_en TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    revocado_en TIMESTAMPTZ NULL,
    CONSTRAINT uq_token_nodo_token_hash UNIQUE (token_hash),
    CONSTRAINT fk_token_nodo_nodo FOREIGN KEY (nodo_id)
        REFERENCES nodo_acceso (id) ON DELETE CASCADE
);

-- -----------------------------------------------------------------------------
-- Tabla: evento_acceso
-- Registro de cada lectura RFID en los nodos de acceso
-- estudiante_id es nullable: NULL cuando el tag no está registrado
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS evento_acceso (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    tag_rfid        VARCHAR(8)  NOT NULL,
    nodo_id         UUID        NOT NULL,
    ambiente_id     UUID        NOT NULL,
    estudiante_id   UUID        NULL,
    timestamp_utc   TIMESTAMPTZ NOT NULL,
    resultado       VARCHAR(20) NOT NULL,
    codigo_resultado VARCHAR(50) NULL,
    origen          VARCHAR(30) NOT NULL DEFAULT 'nodo',
    CONSTRAINT fk_evento_acceso_nodo FOREIGN KEY (nodo_id)
        REFERENCES nodo_acceso (id) ON DELETE RESTRICT,
    CONSTRAINT fk_evento_acceso_ambiente FOREIGN KEY (ambiente_id)
        REFERENCES ambiente (id) ON DELETE RESTRICT,
    CONSTRAINT fk_evento_acceso_estudiante FOREIGN KEY (estudiante_id)
        REFERENCES estudiante (id) ON DELETE RESTRICT
);

-- -----------------------------------------------------------------------------
-- Tabla: bitacora_seguridad
-- Registro append-only de intentos de acceso con token inválido
-- Nunca se actualiza ni elimina
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS bitacora_seguridad (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    timestamp       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    node_identifier VARCHAR(40) NOT NULL DEFAULT '',
    motivo_rechazo  VARCHAR(50) NOT NULL,
    ip_origen       INET        NULL,
    detalle         TEXT        NULL
);

-- =============================================================================
-- Índices para rendimiento
-- =============================================================================

-- Índice para consultas de reportes ordenadas por timestamp (más reciente primero)
CREATE INDEX IF NOT EXISTS idx_evento_acceso_timestamp
    ON evento_acceso (timestamp_utc DESC);

-- Índice para monitoreo por nodo
CREATE INDEX IF NOT EXISTS idx_evento_acceso_nodo_timestamp
    ON evento_acceso (nodo_id, timestamp_utc DESC);

-- Índice para reportes por estudiante
CREATE INDEX IF NOT EXISTS idx_evento_acceso_estudiante_timestamp
    ON evento_acceso (estudiante_id, timestamp_utc DESC);

-- Índice parcial para lookup rápido de tags activos durante el procesamiento de acceso
CREATE INDEX IF NOT EXISTS idx_tag_rfid_uid_activo
    ON tag_rfid (uid_hex) WHERE activo = TRUE;
