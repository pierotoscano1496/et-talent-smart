const API_KEY = "TALENT_SMART_KEY";

const connectionDot = document.getElementById("connectionDot");
const connectionText = document.getElementById("connectionText");
const totalUsers = document.getElementById("totalUsers");
const todayLogs = document.getElementById("todayLogs");
const allowedCount = document.getElementById("allowedCount");
const deniedCount = document.getElementById("deniedCount");
const doorStatus = document.getElementById("doorStatus");
const doorEvent = document.getElementById("doorEvent");
const doorCard = document.getElementById("doorCard");
const logsTable = document.getElementById("logsTable");
const formMessage = document.getElementById("formMessage");

function formatTime(isoDate) {
  const date = new Date(isoDate);
  return date.toLocaleTimeString("es-PE", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit"
  });
}

async function loadData() {
  try {
    const [resumenRes, registrosRes] = await Promise.all([
      fetch("/api/resumen"),
      fetch("/api/registros")
    ]);

    const resumen = await resumenRes.json();
    const registros = await registrosRes.json();

    connectionDot.classList.add("online");
    connectionText.textContent = "Servidor activo";

    totalUsers.textContent = resumen.total_usuarios;
    todayLogs.textContent = resumen.registros_hoy;
    allowedCount.textContent = resumen.accesos_permitidos;
    deniedCount.textContent = resumen.accesos_denegados;

    const puerta = resumen.puerta;
    doorStatus.textContent = puerta.estado;
    doorEvent.textContent = puerta.ultimo_evento;

    if (puerta.estado === "cerrada") {
      doorCard.classList.add("closed");
    } else {
      doorCard.classList.remove("closed");
    }

    renderLogs(registros.registros);
  } catch (error) {
    connectionDot.classList.remove("online");
    connectionText.textContent = "Servidor desconectado";
    logsTable.innerHTML = `
      <tr>
        <td colspan="5">No se pudo conectar con la API local.</td>
      </tr>
    `;
  }
}

function renderLogs(registros) {
  if (!registros.length) {
    logsTable.innerHTML = `
      <tr>
        <td colspan="5">Todavía no hay registros RFID.</td>
      </tr>
    `;
    return;
  }

  logsTable.innerHTML = registros.map(registro => `
    <tr>
      <td>${formatTime(registro.fecha_hora)}</td>
      <td>
        <strong>${registro.nombre}</strong><br />
        <small>${registro.codigo} · ${registro.rol}</small>
      </td>
      <td>${registro.uid}</td>
      <td>${registro.location_id}</td>
      <td>
        <span class="badge ${registro.authorized ? "allowed" : "denied"}">
          ${registro.authorized ? "Permitido" : "Denegado"}
        </span>
      </td>
    </tr>
  `).join("");
}

document.getElementById("userForm").addEventListener("submit", async event => {
  event.preventDefault();

  const payload = {
    nombre: document.getElementById("nombre").value.trim(),
    codigo: document.getElementById("codigo").value.trim(),
    rol: document.getElementById("rol").value,
    uid_rfid: document.getElementById("uid_rfid").value.trim().toUpperCase()
  };

  try {
    const res = await fetch("/api/usuarios", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify(payload)
    });

    const data = await res.json();

    formMessage.textContent = data.message;

    if (data.ok) {
      event.target.reset();
      loadData();
    }
  } catch (error) {
    formMessage.textContent = "No se pudo guardar el usuario.";
  }
});

async function simulateRFID() {
  const uid = document.getElementById("demoUID").value.trim().toUpperCase();
  const demoResult = document.getElementById("demoResult");

  if (!uid) {
    demoResult.textContent = "Escribe un UID RFID.";
    return;
  }

  const payload = {
    uid,
    device_id: "ESP32C6_RFID_01",
    location_id: "PUERTA_PRINCIPAL",
    event_type: "rfid_detected",
    wifi_rssi: -52,
    millis: Date.now()
  };

  try {
    const res = await fetch("/api/rfid/registro", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-API-KEY": API_KEY
      },
      body: JSON.stringify(payload)
    });

    const data = await res.json();
    demoResult.textContent = JSON.stringify(data, null, 2);
    loadData();
  } catch (error) {
    demoResult.textContent = "Error simulando lectura RFID.";
  }
}

async function closeDoor() {
  const demoResult = document.getElementById("demoResult");

  try {
    const res = await fetch("/api/puerta/cerrar", {
      method: "POST"
    });

    const data = await res.json();
    demoResult.textContent = JSON.stringify(data, null, 2);
    loadData();
  } catch (error) {
    demoResult.textContent = "Error simulando cierre de puerta.";
  }
}

loadData();
setInterval(loadData, 2500);
