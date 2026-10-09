import { useEffect, useState } from 'react'
import { currentAccount, downloadAttendance, request } from './api'

type Schedule = { classroom: string; blocks: { day: number; start: string; end: string; title?: string; kind: string; course_id?: number; room?: string }[] }
type Attendance = { id: number; student: number; student_name: string; date: string; first_seen: string }
type Incident = { id: number; student: number; date: string; kind: string; exit_time: string | null }
type Page<T> = { results: T[]; next: string | null }
const days = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']

export default function SchoolPanel({ panel }: { panel: string }) {
  const [schedules, setSchedules] = useState<Schedule[]>([])
  const [attendance, setAttendance] = useState<Attendance[]>([])
  const [incidents, setIncidents] = useState<Incident[]>([])
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [filters, setFilters] = useState({ start: '', end: '', grade: '', section: '', student: '' })
  const [query, setQuery] = useState('')
  const [more, setMore] = useState(false)
  const user = currentAccount()
  const pendingQuery = new URLSearchParams(Object.entries(filters).filter(([, value]) => value)).toString()
  const unappliedFilters = pendingQuery !== query.replace(/^\?/, '')

  useEffect(() => {
    let active = true
    setLoading(true)
    setError('')
    setAttendance([])
    setIncidents([])
    setSchedules([])
    const load = async () => {
      try {
        if (panel === 'Asistencia') {
          const [records, events] = await Promise.all([
            request<Page<Attendance>>('/api/attendance/' + query),
            request<Page<Incident>>('/api/incidents/' + query),
          ])
          if (active) { setAttendance(records.results); setIncidents(events.results); setMore(Boolean(records.next || events.next)) }
        } else {
          const data = await request<Schedule[]>('/api/my-schedule/')
          if (active) setSchedules(data)
        }
      } catch (err) { if (active) setError((err as Error).message) }
      finally { if (active) setLoading(false) }
    }
    void load()
    return () => { active = false }
  }, [panel, query])

  return <section>
    <p className="eyebrow text-pink">{user?.name} · {user?.role}</p>
    <h2 className="mt-3 text-4xl font-bold text-navy">{panel === 'Inicio' ? 'Tu espacio escolar' : panel}</h2>
    {panel === 'Asistencia' && <form className="dash-card my-6 flex flex-wrap items-end gap-3" onSubmit={event => {
      event.preventDefault()
      const params = new URLSearchParams(Object.entries(filters).filter(([, value]) => value))
      setQuery('?' + params.toString())
    }}>
      {Object.entries(filters).map(([key, value]) => <label key={key} className="text-sm">{({ start: 'Desde', end: 'Hasta', grade: 'Grado', section: 'Sección', student: 'ID de estudiante' } as Record<string, string>)[key]}
        <input className="mt-2 block rounded-xl border p-2" type={key === 'start' || key === 'end' ? 'date' : 'text'} value={value} onChange={e => setFilters({ ...filters, [key]: e.target.value })} />
      </label>)}
      <button className="pill-button" type="submit">Consultar</button>
      {['auxiliar', 'docente'].includes(user?.role || '') && <button className="pill-button disabled:opacity-50" disabled={loading || !!error || unappliedFilters} type="button" onClick={() => void downloadAttendance(query).catch(err => setError(err.message))}>Descargar CSV</button>}
    </form>}
    {error && <p role="alert" className="dash-card mt-6">{error}</p>}
    {loading ? <p className="mt-6" role="status">Cargando…</p> : !error && (panel === 'Asistencia' ?
      <div className="dash-card mt-6 overflow-x-auto">
        {!attendance.length && !incidents.length && <p>No hay registros para esta consulta.</p>}
        {!!attendance.length && <table className="w-full text-left text-sm"><thead><tr><th className="p-3">Fecha</th><th className="p-3">Estudiante</th><th className="p-3">Ingreso</th></tr></thead><tbody>{attendance.map(row => <tr key={row.id}><td className="p-3">{row.date}</td><td className="p-3">{row.student_name || row.student}</td><td className="p-3">{new Date(row.first_seen).toLocaleTimeString('es-PE', { timeZone: 'America/Lima' })}</td></tr>)}</tbody></table>}
        {incidents.map(event => <p className="border-t py-3 text-sm" key={event.id}>{event.date} · Estudiante {event.student} · {event.kind.replaceAll('_', ' ')} {event.exit_time}</p>)}
        {more && <p className="mt-4 text-sm">Se muestran los primeros 50 resultados de cada lista. Acota las fechas; el CSV incluye todos los resultados filtrados.</p>}
      </div> :
      <div className="mt-8 grid gap-4">
        {!schedules.length && <p className="dash-card">No tienes un horario publicado disponible.</p>}
        {schedules.map(schedule => <article className="dash-card" key={schedule.classroom}><h3 className="font-bold">{schedule.classroom}</h3>{schedule.blocks.map((block, index) => <p key={index} className="border-t py-3 text-sm">{days[block.day]} · {block.start}–{block.end} · {block.title || block.kind} {block.room && '· ' + block.room}</p>)}</article>)}
      </div>)}
  </section>
}
