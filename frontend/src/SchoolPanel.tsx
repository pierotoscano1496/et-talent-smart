import { useEffect, useState } from 'react'
import { request } from './api'
import { Timetable } from './CoordinatorPanel'
import { days, Notice } from './management'
import type { Block } from './management'

type PersonalSchedule = { classroom: string; blocks: (Block & { teacher?: string })[] }
export default function SchoolPanel({ panel }: { panel: string }) {
  const [schedules, setSchedules] = useState<PersonalSchedule[]>([])
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  useEffect(() => {
    let active = true
    void request<PersonalSchedule[]>('/api/my-schedule/').then(data => { if (active) setSchedules(data) }).catch(err => { if (active) setError(err.message) }).finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [])
  return <section className="space-y-6"><h2 className="text-3xl font-bold text-navy">{panel} publicados</h2><p className="text-slate">Jornada escolar de 07:30 a 16:30. Las actualizaciones en borrador no cambian esta publicación.</p><Notice error={error} />
    {loading ? <p role="status">Cargando horario…</p> : !error && (!schedules.length ? <p className="dash-card">Aún no tienes un horario publicado disponible.</p> : schedules.map(schedule => <article key={schedule.classroom} className="space-y-4"><h3 className="text-xl font-bold text-navy">{schedule.classroom}</h3><Timetable blocks={schedule.blocks} /><div className="dash-card overflow-x-auto"><table className="w-full text-left text-sm"><thead><tr>{['Día', 'Horario', 'Actividad', 'Docente', 'Aula / espacio'].map(title => <th key={title} className="p-2">{title}</th>)}</tr></thead><tbody>{[...schedule.blocks].sort((a, b) => a.day - b.day || a.start.localeCompare(b.start)).map((block, index) => <tr className="border-t border-ink/10" key={index}><td className="p-2">{days[block.day]}</td><td className="p-2">{block.start}–{block.end}</td><td className="p-2">{block.title || block.kind}</td><td className="p-2">{block.teacher || '—'}</td><td className="p-2">{block.room || '—'}</td></tr>)}</tbody></table></div></article>))}
  </section>
}
