const $ = (id) => document.getElementById(id);
let token = null, account = null, timer = null, generation = 0, refreshing = false;
const endpoint = (path) => new URL('api/' + path, new URL('./', location.href));
function clearSession() {
  generation++; token = null; account = null; clearInterval(timer); refreshing = false;
  $('workspace').hidden = true; $('logout').hidden = true; $('loginPanel').hidden = false;
  for (const id of ['readings', 'devices', 'studentSelect']) $(id).replaceChildren();
  for (const id of ['summary', 'status', 'searchMessage', 'keyMessage', 'userMessage']) $(id).textContent = '';
  for (const id of ['loginForm', 'searchForm', 'keyForm', 'userForm']) $(id).reset();
}
async function api(path, options = {}) {
  const session = generation;
  const response = await fetch(endpoint(path), { ...options, headers: {
    ...(token ? { Authorization: 'Bearer ' + token } : {}),
    ...(options.body ? { 'Content-Type': 'application/json' } : {}), ...options.headers
  }});
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    if (response.status === 401 && session === generation && token) {
      clearSession(); $('loginMessage').textContent = 'La sesión venció. Ingresa nuevamente.';
    }
    throw new Error(typeof data.detail === 'string' ? data.detail : JSON.stringify(data));
  }
  return data;
}
const date = (value) => new Date(value).toLocaleString('es-PE', { timeZone: 'America/Lima' });
async function refresh() {
  if (!token || refreshing) return;
  const session = generation; refreshing = true;
  try {
    const auxiliary = account.role === 'auxiliar';
    const [devices, summary, readings] = await Promise.all([
      api('rfid/devices/'), auxiliary ? api('rfid/summary/') : null,
      auxiliary ? api('rfid/readings/') : null
    ]);
    if (session !== generation) return;
    $('devices').replaceChildren(...devices.map((device) => {
      const li = document.createElement('li');
      li.textContent = device.device_id + ' · ' + device.location_id + ' · ' + device.state + ' · ' + date(device.reported_at);
      return li;
    }));
    if (!devices.length) $('devices').textContent = 'Todavía no hay estados reportados.';
    if (auxiliary) {
      $('summary').textContent = summary.date + ': ' + summary.attendance + ' asistencias · ' + summary.readings + ' lecturas · ' + summary.allowed + ' autorizadas · ' + summary.denied + ' denegadas';
      $('readings').replaceChildren(...readings.results.map((reading) => {
        const tr = document.createElement('tr');
        for (const value of [date(reading.recorded_at), reading.student_name, reading.uid, reading.device_id, reading.location_id, reading.authorized ? 'Autorizada' : 'Denegada']) {
          const td = document.createElement('td'); td.textContent = value; tr.append(td);
        }
        return tr;
      }));
    }
    $('status').textContent = 'Actualizado: ' + date(Date.now());
  } catch (error) { if (session === generation) $('status').textContent = error.message; }
  finally { if (session === generation) refreshing = false; }
}
$('loginForm').addEventListener('submit', async (event) => {
  event.preventDefault(); const button = event.submitter; button.disabled = true;
  $('loginMessage').textContent = '';
  try {
    const result = await api('auth/login/', { method: 'POST', body: JSON.stringify(Object.fromEntries(new FormData(event.target))) });
    token = result.token; account = result.user;
    if (!['administrador', 'auxiliar'].includes(account.role)) {
      try { await api('auth/logout/', { method: 'POST' }); } finally { clearSession(); }
      throw new Error('Este panel requiere una cuenta de administrador o auxiliar.');
    }
    generation++; $('loginForm').reset(); $('loginPanel').hidden = true;
    $('workspace').hidden = false; $('logout').hidden = false;
    $('identity').textContent = account.name || account.email;
    $('monitor').hidden = account.role !== 'auxiliar'; $('administration').hidden = account.role !== 'administrador';
    await refresh(); if (token) timer = setInterval(refresh, 5000);
  } catch (error) { $('loginMessage').textContent = error.message; }
  finally { button.disabled = false; }
});
$('logout').addEventListener('click', async () => {
  const oldToken = token; clearSession();
  try { await api('auth/logout/', { method: 'POST', headers: { Authorization: 'Bearer ' + oldToken } }); }
  catch { $('loginMessage').textContent = 'Sesión cerrada en este navegador; no se pudo revocar en el servidor.'; }
});
$('refresh').addEventListener('click', refresh);
function formAction(id, messageId, action) {
  $(id).addEventListener('submit', async (event) => {
    event.preventDefault(); const session = generation, button = event.submitter;
    button.disabled = true; $(messageId).textContent = '';
    try { await action(Object.fromEntries(new FormData(event.target)), session); }
    catch (error) { if (session === generation) $(messageId).textContent = error.message; }
    finally { button.disabled = false; }
  });
}
formAction('searchForm', 'searchMessage', async (data, session) => {
  const result = await api('users/?role=estudiante&search=' + encodeURIComponent(data.search));
  if (session !== generation) return;
  const placeholder = new Option('Selecciona un estudiante', '');
  $('studentSelect').replaceChildren(placeholder, ...result.results.map((user) => {
    const option = new Option([user.first_name, user.last_name, user.email].filter(Boolean).join(' · '), user.id);
    option.dataset.uid = user.rfid_uid || ''; return option;
  }));
  $('keyForm').elements.rfid_uid.value = '';
  $('searchMessage').textContent = result.count + ' coincidencias. Se muestran hasta 50; afina la búsqueda si es necesario.';
});
$('studentSelect').addEventListener('change', () => {
  $('keyForm').elements.rfid_uid.value = $('studentSelect').selectedOptions[0]?.dataset.uid || '';
});
formAction('keyForm', 'keyMessage', async (data, session) => {
  const uid = data.rfid_uid.trim().toUpperCase() || null;
  await api('users/' + encodeURIComponent(data.student) + '/', { method: 'PATCH', body: JSON.stringify({ rfid_uid: uid }) });
  if (session !== generation) return;
  const option = Array.from($('studentSelect').options).find((item) => item.value === data.student);
  if (option) option.dataset.uid = uid || '';
  $('keyMessage').textContent = uid ? 'Llave asignada.' : 'Llave retirada.';
});
formAction('userForm', 'userMessage', async (data, session) => {
  await api('users/', { method: 'POST', body: JSON.stringify({ ...data, role: 'estudiante', rfid_uid: data.rfid_uid.trim().toUpperCase() || null }) });
  if (session === generation) { $('userForm').reset(); $('userMessage').textContent = 'Cuenta creada.'; }
});
