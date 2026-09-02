const views = document.querySelectorAll('.view');
const showView = (id) => {
  views.forEach((view) => { const active = view.id === id; view.classList.toggle('active', active); view.setAttribute('aria-hidden', String(!active)); });
  window.scrollTo({ top: 0, behavior: 'instant' });
};

document.querySelectorAll('.open-login').forEach((button) => button.addEventListener('click', () => showView('login')));
document.querySelectorAll('[data-view]').forEach((button) => button.addEventListener('click', () => showView(button.dataset.view)));
document.querySelector('.menu-toggle').addEventListener('click', (event) => {
  const open = document.querySelector('.site-header').classList.toggle('menu-open');
  event.currentTarget.setAttribute('aria-expanded', String(open));
});
document.querySelectorAll('.nav a').forEach((link) => link.addEventListener('click', () => document.querySelector('.site-header').classList.remove('menu-open')));

document.querySelector('.toggle-password').addEventListener('click', (event) => {
  const input = event.currentTarget.previousElementSibling;
  input.type = input.type === 'password' ? 'text' : 'password';
  event.currentTarget.setAttribute('aria-label', input.type === 'password' ? 'Mostrar contraseña' : 'Ocultar contraseña');
});

document.querySelector('#login-form').addEventListener('submit', (event) => {
  event.preventDefault();
  const button = event.currentTarget.querySelector('.login-submit');
  button.textContent = 'Conectando…'; button.disabled = true;
  setTimeout(() => { button.innerHTML = 'Ingresar <span>→</span>'; button.disabled = false; event.currentTarget.reset(); showView('dashboard'); }, 650);
});

const panelTitles = { home: 'Hola, estudiante', schedule: 'Mi horario', attendance: 'Mi asistencia', courses: 'Mis cursos', notices: 'Comunicados', device: 'Talent Smart', profile: 'Mi perfil', settings: 'Configuración' };
const openPanel = (name) => {
  document.querySelectorAll('.dash-panel').forEach((panel) => panel.classList.toggle('active', panel.id === `panel-${name}`));
  document.querySelectorAll('.dash-nav button, .nav-bottom button').forEach((button) => button.classList.toggle('active', button.dataset.panel === name));
  document.querySelector('#panel-title').innerHTML = `${panelTitles[name]} <span>✦</span>`;
  document.querySelector('.sidebar').classList.remove('open');
};
document.querySelectorAll('[data-panel], [data-go]').forEach((button) => button.addEventListener('click', () => openPanel(button.dataset.panel || button.dataset.go)));
document.querySelector('.dash-menu').addEventListener('click', () => document.querySelector('.sidebar').classList.toggle('open'));
document.querySelector('#logout').addEventListener('click', () => { openPanel('home'); showView('landing'); });

const observer = new IntersectionObserver((entries) => entries.forEach((entry) => { if (entry.isIntersecting) entry.target.classList.add('visible'); }), { threshold: .12 });
document.querySelectorAll('.reveal').forEach((element) => observer.observe(element));
