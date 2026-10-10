import { useEffect, useState } from 'react'
import { currentAccount, downloadAttendance, listAll, request } from './api'
import { button, field, Label, Notice, useAction } from './management'
import type { Person } from './management'

type Attendance = { id: number; student: number; student_name: string; date: string; first_seen: string }
type Incident = { id: number; student: number; student_name: string; date: string; kind: string; exit_time: string | null; reason: string }
type Page<T> = { results: T[]; next: string | null }
const today = () => new Intl.DateTimeFormat('sv-SE', { timeZone: 'America/Lima' }).format(new Date())
export default function AttendancePanel({ incidentsOnly = false }: { incidentsOnly?: boolean }) {
  const role = currentAccount()?.role
  const canManage = role === 'auxiliar' || role === 'docente'
  const kind = role === 'auxiliar' ? 'retiro_temprano' : 'falta_justificada'
  const action = useAction()
  const [people, setPeople] = useState<Person[]>([])
  const [records, setRecords] = useState<Attendance[]>([])
  const [incidents, setIncidents] = useState<Incident[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [more, setMore] = useState(false)
  const [filters, setFilters] = useState({ start: today().slice(0, 7) + '-01', end: today(), grade: '', section: '', student: '' })
  const pending = new URLSearchParams(Object.entries(filters).filter(([, value]) => value)).toString()
  const [query, setQuery] = useState(pending)
  const [revision, setRevision] = useState(0)
  const [form, setForm] = useState({ student: '', date: today(), exit_time: '', reason: '' })
  useEffect(() => { let active = true; void listAll<Person>('/api/directory/').then(data => { if (active) setPeople(data) }).catch(err => { if (active) setError(err.message) }); return () => { active = false } }, [])
  useEffect(() => {
    let active = true; setLoading(true); setError(''); setRecords([]); setIncidents([])
    void Promise.all([request<Page<Attendance>>('/api/attendance/?' + query), request<Page<Incident>>('/api/incidents/?' + query)]).then(([attendance, events]) => {
      if (active) { setRecords(attendance.results); setIncidents(events.results); setMore(Boolean(attendance.next || events.next)) }
    }).catch(err => { if (active) setError(err.message) }).finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [query, revision])
  const students = people.filter(p => (!filters.grade || p.grade === filters.grade) && (!filters.section || p.section === filters.section))
  return <section className="space-y-6"><div><h2 className="text-3xl font-bold text-navy">{incidentsOnly ? role === 'auxiliar' ? 'Retiros tempranos' : 'Justificar inasistencias' : role === 'padre' ? 'Asistencia de mis hijos' : 'Asistencia diaria'}</h2><p className="mt-2 text-slate">{role === 'docente' ? 'Consulta únicamente a los estudiantes de tus cursos.' : role === 'padre' ? 'Consulta las marcaciones e incidencias de tus hijos vinculados.' : role === 'estudiante' ? 'Tu asistencia se registra en el colegio al presentar tu llave RFID.' : 'Consulta las marcaciones de ingreso y las incidencias de los estudiantes.'}</p></div>
    <Notice error={error || action.error} message={action.message} />
    {incidentsOnly && canManage && <form className="dash-card" onSubmit={e => { e.preventDefault(); void action.run(async () => {
      await request('/api/incidents/', { method: 'POST', body: JSON.stringify({ ...form, student: Number(form.student), kind, exit_time: role === 'auxiliar' ? form.exit_time : null }) })
      const nextFilters = { start: form.date, end: form.date, grade: '', section: '', student: form.student }
      setFilters(nextFilters); setQuery(new URLSearchParams(Object.entries(nextFilters).filter(([, value]) => value)).toString()); setRevision(value => value + 1)
      setForm({ ...form, reason: '', exit_time: '' })
    }, 'Incidencia registrada. Se muestran los registros de ese estudiante y día.') }}><fieldset disabled={action.busy} className="grid items-end gap-4 sm:grid-cols-2"><Label title="Estudiante"><select className={field} required value={form.student} onChange={e => setForm({ ...form, student: e.target.value })}><option value="">Selecciona un estudiante</option>{people.map(p => <option key={p.id} value={p.id}>{p.name || `Estudiante ${p.id}`} · {p.grade} {p.section}</option>)}</select></Label><Label title="Fecha de incidencia"><input type="date" required className={field} value={form.date} onChange={e => setForm({ ...form, date: e.target.value })} /></Label>{role === 'auxiliar' && <Label title="Hora de salida"><input required type="time" className={field} value={form.exit_time} onChange={e => setForm({ ...form, exit_time: e.target.value })} /></Label>}<Label title="Motivo (opcional)"><textarea className={field} value={form.reason} onChange={e => setForm({ ...form, reason: e.target.value })} /></Label><div><button className={button}>Registrar {role === 'auxiliar' ? 'retiro temprano' : 'justificación'}</button></div><p className="text-xs text-slate">No requiere adjuntos ni aprobación.</p></fieldset></form>}
    <form className="dash-card" onSubmit={e => { e.preventDefault(); setQuery(pending); setRevision(value => value + 1) }}><div className="grid items-end gap-4 sm:grid-cols-2 xl:grid-cols-5"><Label title="Desde"><input type="date" required className={field} value={filters.start} onChange={e => setFilters({ ...filters, start: e.target.value })} /></Label><Label title="Hasta"><input type="date" required min={filters.start} className={field} value={filters.end} onChange={e => setFilters({ ...filters, end: e.target.value })} /></Label>
      {role !== 'estudiante' && <><Label title="Grado"><select className={field} value={filters.grade} onChange={e => setFilters({ ...filters, grade: e.target.value, student: '', section: '' })}><option value="">Todos</option>{[...new Set(people.map(p => p.grade).filter(Boolean))].sort().map(g => <option key={g}>{g}</option>)}</select></Label><Label title="Sección"><select className={field} value={filters.section} onChange={e => setFilters({ ...filters, section: e.target.value, student: '' })}><option value="">Todas</option>{[...new Set(people.filter(p => !filters.grade || p.grade === filters.grade).map(p => p.section).filter(Boolean))].sort().map(s => <option key={s}>{s}</option>)}</select></Label><Label title={role === 'padre' ? 'Hijo' : 'Estudiante'}><select className={field} value={filters.student} onChange={e => setFilters({ ...filters, student: e.target.value })}><option value="">Todos los autorizados</option>{students.map(p => <option key={p.id} value={p.id}>{p.name || `Estudiante ${p.id}`}</option>)}</select></Label></>}
    </div><div className="mt-4 flex flex-wrap gap-3"><button className={button} disabled={loading}>Consultar asistencia</button>{canManage && <button type="button" className={button} disabled={loading || !!error || pending !== query || action.busy} onClick={() => void action.run(() => downloadAttendance('?' + query), 'Reporte descargado.')}>Descargar CSV</button>}</div>{pending !== query && <p className="mt-3 text-sm text-slate">Aplica los filtros para actualizar la consulta y el reporte.</p>}</form>
    {loading ? <p role="status">Cargando asistencia…</p> : !error && <div className="dash-card space-y-5"><h3 className="font-bold">Marcaciones de ingreso</h3>{!records.length ? <p className="text-sm text-slate">No hay marcaciones para esta consulta.</p> : <div className="overflow-x-auto"><table className="w-full text-left text-sm"><thead><tr><th className="p-2">Fecha</th><th className="p-2">Estudiante</th><th className="p-2">Primer ingreso (Lima)</th></tr></thead><tbody>{records.map(row => <tr key={row.id} className="border-t border-ink/10"><td className="p-2">{row.date}</td><td className="p-2">{row.student_name || row.student}</td><td className="p-2">{new Date(row.first_seen).toLocaleTimeString('es-PE', { timeZone: 'America/Lima' })}</td></tr>)}</tbody></table></div>}<h3 className="font-bold">Incidencias de la jornada</h3>{incidents.map(item => <article key={item.id} className="rounded-xl bg-pale/30 p-4 text-sm"><strong>{item.student_name || `Estudiante ${item.student}`} · {item.date}</strong><p className="mt-1">{item.kind === 'retiro_temprano' ? `Retiro temprano · ${item.exit_time}` : 'Falta justificada'}</p>{item.reason && <p className="mt-2">{item.reason}</p>}</article>)}{!incidents.length && <p className="text-sm text-slate">No hay incidencias para esta consulta.</p>}{more && <p className="text-sm text-slate">Se muestran hasta 50 registros de cada lista. Acota el periodo; el CSV incluye todos los resultados filtrados.</p>}{role === 'padre' && <p className="text-xs text-slate">Una marcación confirma el registro de ingreso. Por sí sola no confirma que el estudiante continúe en el colegio.</p>}</div>}
  </section>
}
