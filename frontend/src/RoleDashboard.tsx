import { useState } from 'react'
import { currentAccount } from './api'
import UsersPanel from './UsersPanel'
import CoordinatorPanel from './CoordinatorPanel'
import AttendancePanel from './AttendancePanel'
import SchoolPanel from './SchoolPanel'
import { roles } from './management'

const tasks: Record<string, [string, string][]> = {
  administrador: [['Usuarios', 'Crea cuentas institucionales, asigna roles y vincula las llaves RFID de los estudiantes.']],
  coordinador: [['Grados y secciones', 'Organiza el año académico y asigna a los estudiantes su grupo.'], ['Cursos', 'Asigna los cursos a sus docentes y grupos.'], ['Horarios', 'Prepara y publica la jornada de 07:30 a 16:30, con recesos y almuerzo.'], ['Eventos', 'Programa bloques extracurriculares para algunos grupos o todos los del año.']],
  auxiliar: [['Asistencia', 'Consulta la asistencia diaria de todos los estudiantes y descarga reportes.'], ['Retiros tempranos', 'Registra la fecha y hora de salida anticipada de un estudiante.']],
  docente: [['Horarios', 'Consulta las clases y eventos de tu horario publicado.'], ['Asistencia', 'Consulta y descarga la asistencia de los estudiantes de tus cursos.'], ['Justificaciones', 'Registra los motivos de inasistencia de tus estudiantes.']],
  estudiante: [['Horarios', 'Consulta las clases, recesos, almuerzo y eventos de tu grupo.'], ['Asistencia', 'Consulta tus marcaciones diarias registradas con RFID.']],
  padre: [['Asistencia', 'Consulta el ingreso y las incidencias de tus hijos vinculados.']],
}
export default function RoleDashboard({ logout }: { logout: () => void }) {
  const [panel, setPanel] = useState('Inicio')
  const [menu, setMenu] = useState(false)
  const account = currentAccount()
  const available = tasks[account?.role || ''] || []
  const panels = ['Inicio', ...available.map(([name]) => name), 'Mi perfil']
  const show = (name: string) => { setPanel(name); setMenu(false) }
  return <div className="min-h-screen bg-[#f5f2f4] lg:grid lg:grid-cols-[245px_1fr]">
    {menu && <button aria-label="Cerrar menú" className="fixed inset-0 z-30 bg-black/40 lg:hidden" onClick={() => setMenu(false)} />}
    <aside className={`${menu ? 'left-0' : '-left-[260px]'} fixed top-0 z-40 flex h-screen w-[245px] flex-col bg-ink p-5 text-white transition-all lg:sticky lg:left-0`}><span className="text-xl font-bold">Talent <span className="text-pink">Smart</span></span><p className="mt-3 text-xs text-blue">{roles[account?.role || '']}</p><nav aria-label="Menú principal" className="mt-9 space-y-1">{panels.map(name => <button key={name} aria-current={panel === name ? 'page' : undefined} onClick={() => show(name)} className={`block w-full rounded-xl px-4 py-3 text-left text-sm ${panel === name ? 'bg-blue/20 text-white' : 'text-blue/80 hover:bg-white/10'}`}>{name}</button>)}</nav><button onClick={logout} className="mt-auto rounded-xl border border-white/20 px-4 py-3 text-left text-sm text-blue">Cerrar sesión</button></aside>
    <main className="min-w-0"><header className="sticky top-0 z-20 flex min-h-24 items-center justify-between gap-4 border-b border-ink/10 bg-[#f5f2f4]/95 px-4 backdrop-blur sm:px-10"><div className="flex items-center gap-4"><button aria-label="Abrir menú" aria-expanded={menu} onClick={() => setMenu(true)} className="text-xl lg:hidden">☰</button><div><p className="eyebrow text-slate/60">{roles[account?.role || '']}</p><h1 className="text-2xl font-bold text-navy">{panel}</h1></div></div><span className="max-w-52 truncate text-sm text-navy">{account?.name}</span></header>
      <div key={panel} className="p-4 sm:p-8">
        {panel === 'Inicio' ? <section><p className="eyebrow text-pink">Tu espacio institucional</p><h2 className="mt-3 text-3xl font-bold text-navy">Hola, {account?.name}</h2><p className="mt-3 text-slate">Estas son las tareas disponibles para tu cuenta.</p><div className="mt-8 grid gap-5 md:grid-cols-2 xl:grid-cols-3">{available.map(([name, description], i) => <button className="dash-card text-left transition hover:border-pink hover:shadow-lg" key={name} onClick={() => show(name)}><span className="text-sm font-bold text-pink">0{i + 1}</span><h3 className="mt-5 text-xl font-bold text-navy">{name} ↗</h3><p className="mt-3 text-sm leading-6 text-slate">{description}</p></button>)}</div>{account?.role === 'estudiante' && <p className="dash-card mt-6 text-sm">Para marcar tu asistencia, presenta tu llave en el lector del colegio. No necesitas iniciar sesión en la web.</p>}</section>
          : panel === 'Mi perfil' ? <section className="dash-card max-w-xl"><h2 className="text-2xl font-bold text-navy">Mi cuenta institucional</h2><dl className="mt-6 space-y-4"><div><dt className="text-sm text-slate">Nombre</dt><dd>{account?.name}</dd></div><div><dt className="text-sm text-slate">Correo</dt><dd>{account?.email}</dd></div><div><dt className="text-sm text-slate">Rol</dt><dd>{roles[account?.role || '']}</dd></div></dl><p className="mt-6 text-sm text-slate">Solicita al administrador las correcciones de tu cuenta.</p></section>
          : account?.role === 'administrador' && panel === 'Usuarios' ? <UsersPanel />
          : account?.role === 'coordinador' && available.some(([name]) => name === panel) ? <CoordinatorPanel panel={panel} />
          : panel === 'Asistencia' && available.some(([name]) => name === panel) ? <AttendancePanel />
          : ((panel === 'Retiros tempranos' && account?.role === 'auxiliar') || (panel === 'Justificaciones' && account?.role === 'docente')) ? <AttendancePanel incidentsOnly />
          : panel === 'Horarios' && ['estudiante', 'docente'].includes(account?.role || '') ? <SchoolPanel panel={panel} /> : null}
      </div>
    </main>
  </div>
}
