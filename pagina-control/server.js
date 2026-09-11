import express from "express";
import cors from "cors";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();
const PORT = process.env.PORT || 3000;
const API_KEY = process.env.API_KEY || "TALENT_SMART_KEY";

const DB_PATH = path.join(__dirname, "database.json");

app.use(cors());
app.use(express.json());
app.use(express.static(path.join(__dirname, "public")));

function loadDB() {
  if (!fs.existsSync(DB_PATH)) {
    const initialDB = {
      usuarios: [
        {
          id: 1,
          nombre: "Camila Ampuero",
          codigo: "EST-001",
          rol: "Estudiante",
          uid_rfid: "04577F49C42A81",
          estado: "activo"
        },
        {
          id: 2,
          nombre: "Gabriel Ramos",
          codigo: "EST-002",
          rol: "Estudiante",
          uid_rfid: "11223344",
          estado: "activo"
        },
        {
          id: 3,
          nombre: "Docente Principal",
          codigo: "DOC-001",
          rol: "Docente",
          uid_rfid: "55667788",
          estado: "activo"
        }
      ],
      registros: [],
      puerta: {
        estado: "cerrada",
        ultimo_evento: "Sistema iniciado",
        ultima_actualizacion: new Date().toISOString()
      }
    };

    fs.writeFileSync(DB_PATH, JSON.stringify(initialDB, null, 2));
  }

  return JSON.parse(fs.readFileSync(DB_PATH, "utf8"));
}

function saveDB(db) {
  fs.writeFileSync(DB_PATH, JSON.stringify(db, null, 2));
}

function requireApiKey(req, res, next) {
  const apiKey = req.headers["x-api-key"];

  if (apiKey !== API_KEY) {
    return res.status(401).json({
      ok: false,
      authorized: false,
      message: "API KEY inválida"
    });
  }

  next();
}

app.get("/api/health", (req, res) => {
  res.json({
    ok: true,
    message: "API RFID activa",
    server_time: new Date().toISOString()
  });
});

app.get("/api/usuarios", (req, res) => {
  const db = loadDB();
  res.json({
    ok: true,
    usuarios: db.usuarios
  });
});

app.post("/api/usuarios", (req, res) => {
  const db = loadDB();
  const { nombre, codigo, rol, uid_rfid } = req.body;

  if (!nombre || !codigo || !uid_rfid) {
    return res.status(400).json({
      ok: false,
      message: "Nombre, código y UID RFID son obligatorios"
    });
  }

  const exists = db.usuarios.some(
    user => user.uid_rfid.toUpperCase() === uid_rfid.toUpperCase()
  );

  if (exists) {
    return res.status(409).json({
      ok: false,
      message: "Ese UID ya está registrado"
    });
  }

  const nuevoUsuario = {
    id: Date.now(),
    nombre,
    codigo,
    rol: rol || "Estudiante",
    uid_rfid: uid_rfid.toUpperCase(),
    estado: "activo"
  };

  db.usuarios.push(nuevoUsuario);
  saveDB(db);

  res.status(201).json({
    ok: true,
    message: "Usuario registrado",
    usuario: nuevoUsuario
  });
});

app.get("/api/registros", (req, res) => {
  const db = loadDB();

  res.json({
    ok: true,
    registros: db.registros.slice(-100).reverse(),
    puerta: db.puerta,
    total_usuarios: db.usuarios.length
  });
});

app.get("/api/resumen", (req, res) => {
  const db = loadDB();
  const hoy = new Date().toISOString().slice(0, 10);

  const registrosHoy = db.registros.filter(r => r.fecha_hora.startsWith(hoy));
  const permitidos = registrosHoy.filter(r => r.authorized).length;
  const denegados = registrosHoy.filter(r => !r.authorized).length;

  res.json({
    ok: true,
    total_usuarios: db.usuarios.length,
    registros_hoy: registrosHoy.length,
    accesos_permitidos: permitidos,
    accesos_denegados: denegados,
    puerta: db.puerta
  });
});

/*
  Endpoint compatible con el ESP32-C6.

  El ESP32 debe enviar:
  POST /api/rfid/registro
  Header: X-API-KEY: TALENT_SMART_KEY
  Body:
  {
    "uid": "A1B2C3D4",
    "device_id": "ESP32C6_RFID_01",
    "location_id": "PUERTA_PRINCIPAL",
    "event_type": "rfid_detected",
    "wifi_rssi": -54,
    "millis": 12345
  }
*/
app.post("/api/rfid/registro", requireApiKey, (req, res) => {
  const db = loadDB();

  const {
    uid,
    device_id = "ESP32C6_RFID_01",
    location_id = "PUERTA_PRINCIPAL",
    event_type = "rfid_detected",
    wifi_rssi = null,
    millis = null
  } = req.body;

  if (!uid) {
    return res.status(400).json({
      ok: false,
      authorized: false,
      message: "UID requerido"
    });
  }

  const cleanUID = String(uid).trim().toUpperCase();

  const usuario = db.usuarios.find(
    user =>
      user.uid_rfid.toUpperCase() === cleanUID &&
      user.estado === "activo"
  );

  const authorized = Boolean(usuario);

  const registro = {
    id: Date.now(),
    uid: cleanUID,
    usuario_id: usuario ? usuario.id : null,
    nombre: usuario ? usuario.nombre : "No registrado",
    codigo: usuario ? usuario.codigo : "-",
    rol: usuario ? usuario.rol : "-",
    authorized,
    device_id,
    location_id,
    event_type,
    wifi_rssi,
    millis,
    fecha_hora: new Date().toISOString()
  };

  db.registros.push(registro);

  db.puerta = {
    estado: authorized ? "abierta" : "cerrada",
    ultimo_evento: authorized
      ? `Acceso permitido para ${registro.nombre}`
      : `Acceso denegado para UID ${cleanUID}`,
    ultima_actualizacion: new Date().toISOString()
  };

  saveDB(db);

  res.status(200).json({
    ok: true,
    authorized,
    message: authorized ? "Usuario autorizado" : "Usuario no autorizado",
    usuario: usuario
      ? {
          nombre: usuario.nombre,
          codigo: usuario.codigo,
          rol: usuario.rol
        }
      : null
  });
});

app.post("/api/puerta/cerrar", (req, res) => {
  const db = loadDB();

  db.puerta = {
    estado: "cerrada",
    ultimo_evento: "Puerta cerrada por seguridad HC-SR04",
    ultima_actualizacion: new Date().toISOString()
  };

  saveDB(db);

  res.json({
    ok: true,
    puerta: db.puerta
  });
});

app.listen(PORT, () => {
  console.log(`Servidor RFID listo en http://localhost:${PORT}`);
  console.log(`API para ESP32: http://TU_IP_LOCAL:${PORT}/api/rfid/registro`);
  console.log(`API_KEY actual: ${API_KEY}`);
});
