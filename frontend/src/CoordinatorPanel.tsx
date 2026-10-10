import { useEffect, useState } from 'react'
import { listAll, request } from './api'
import { button, days, field, groupName, Label, Notice, secondary, useAction } from './management'
import type { Block, Classroom, Course, Person, Schedule } from './management'

type Data = { groups: Classroom[]; courses: Course[]; students: Person[]; teachers: Person[]; schedules: Schedule[] }
const empty: Data = { groups: [], courses: [], students: [], teachers: [], schedules: [] }
async function fetchData(): Promise<Data> {
  const [groups, courses, students, teachers, schedules] = await Promise.all([
    listAll<Classroom>('/api/classrooms/'), listAll<Course>('/api/courses/'), listAll<Person>('/api/directory/'),
    listAll<Person>('/api/directory/?role=docente'), listAll<Schedule>('/api/schedules/'),
  ])
  return { groups, courses, students, teachers, schedules }
}
export default function CoordinatorPanel({ panel }: { panel: string }) {
  const [data, setData] = useState<Data>(empty)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const load = async () => setData(await fetchData())
  useEffect(() => { let active = true; void fetchData().then(value => { if (active) setData(value) }).catch(err => { if (active) setError(err.message) }).finally(() => { if (active) setLoading(false) }); return () => { active = false } }, [])
  if (loading) return <p role="status">Cargando gestión académica…</p>
  if (error) return <Notice error={error} />
  return <section className="space-y-6"><h2 className="text-3xl font-bold text-navy">{panel}</h2>
    {panel === 'Grados y secciones' && <Groups data={data} reload={load} />}
    {panel === 'Cursos' && <Courses data={data} reload={load} />}
    {panel === 'Horarios' && <Schedules data={data} reload={load} />}
    {panel === 'Eventos' && <Events data={data} reload={load} />}
  </section>
}
type Props = { data: Data; reload: () => Promise<void> }
function Groups({ data, reload }: Props) {
  const action = useAction()
  const [group, setGroup] = useState({ year: new Date().getFullYear(), grade: '', section: '' })
  const [student, setStudent] = useState('')
  const [target, setTarget] = useState('')
  const [search, setSearch] = useState('')
  return <><p className="text-slate">Organiza los grupos del año y asigna a cada estudiante su grado y sección.</p><Notice error={action.error} message={action.message} />
    <div className="grid gap-6 lg:grid-cols-2">
      <form className="dash-card space-y-4" onSubmit={e => { e.preventDefault(); void action.run(async () => { await request('/api/classrooms/', { method: 'POST', body: JSON.stringify(group) }); await reload(); setGroup({ ...group, grade: '', section: '' }) }, 'Grado y sección creados.') }}><h3 className="text-lg font-bold">Crear grado y sección</h3><fieldset disabled={action.busy} className="grid gap-4 sm:grid-cols-3"><Label title="Año académico"><input className={field} type="number" min={2000} max={2200} required value={group.year} onChange={e => setGroup({ ...group, year: Number(e.target.value) })} /></Label><Label title="Grado"><input className={field} maxLength={40} required value={group.grade} onChange={e => setGroup({ ...group, grade: e.target.value })} /></Label><Label title="Sección"><input className={field} maxLength={40} required value={group.section} onChange={e => setGroup({ ...group, section: e.target.value })} /></Label><button className={button}>Crear grupo</button></fieldset></form>
      <form className="dash-card space-y-4" onSubmit={e => { e.preventDefault(); void action.run(async () => { await request(`/api/classrooms/${target}/assign/`, { method: 'POST', body: JSON.stringify({ student_id: Number(student) }) }); await reload() }, 'Estudiante asignado.') }}><h3 className="text-lg font-bold">Asignar estudiante</h3><fieldset disabled={action.busy} className="space-y-4"><Label title="Buscar estudiante"><input type="search" className={field} value={search} onChange={e => setSearch(e.target.value)} /></Label><Label title="Estudiante"><select required className={field} value={student} onChange={e => setStudent(e.target.value)}><option value="">Selecciona un estudiante</option>{data.students.filter(p => p.id === Number(student) || p.name.toLowerCase().includes(search.toLowerCase())).map(p => <option key={p.id} value={p.id}>{p.name || `Estudiante ${p.id}`} · {p.grade ? `${p.grade}° ${p.section}` : 'Sin grupo'}</option>)}</select></Label><Label title="Grado y sección de destino"><select required className={field} value={target} onChange={e => setTarget(e.target.value)}><option value="">Selecciona un grupo</option>{data.groups.map(g => <option key={g.id} value={g.id}>{groupName(g)}</option>)}</select></Label><button className={button}>Asignar grado y sección</button></fieldset></form>
    </div><div className="grid gap-4 md:grid-cols-3">{data.groups.map(g => <article key={g.id} className="dash-card"><h3 className="font-bold">{groupName(g)}</h3><p className="mt-2 text-sm text-slate">{data.students.filter(p => p.classroom === g.id).length} estudiantes asignados</p></article>)}</div>
  </>
}
function Courses({ data, reload }: Props) {
  const action = useAction()
  const [editing, setEditing] = useState<number | null>(null)
  const [form, setForm] = useState({ name: '', classroom: '', teacher: '' })
  return <><p className="text-slate">Asigna cada curso a un grado, sección y docente.</p><Notice error={action.error} message={action.message} />
    <form className="dash-card" onSubmit={e => { e.preventDefault(); void action.run(async () => { await request(editing ? `/api/courses/${editing}/` : '/api/courses/', { method: editing ? 'PATCH' : 'POST', body: JSON.stringify({ ...form, classroom: Number(form.classroom), teacher: Number(form.teacher) }) }); await reload(); setEditing(null); setForm({ name: '', classroom: '', teacher: '' }) }, 'Curso y docente guardados.') }}><fieldset disabled={action.busy} className="grid items-end gap-4 md:grid-cols-3"><Label title="Nombre del curso"><input required maxLength={120} className={field} value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} /></Label><Label title="Año, grado y sección"><select required disabled={editing !== null} className={field} value={form.classroom} onChange={e => setForm({ ...form, classroom: e.target.value })}><option value="">Selecciona un grupo</option>{data.groups.map(g => <option key={g.id} value={g.id}>{groupName(g)}</option>)}</select></Label><Label title="Docente"><select required className={field} value={form.teacher} onChange={e => setForm({ ...form, teacher: e.target.value })}><option value="">Selecciona un docente</option>{data.teachers.map(p => <option key={p.id} value={p.id}>{p.name || `Docente ${p.id}`}</option>)}</select></Label><button className={button}>{editing ? 'Guardar curso' : 'Crear curso'}</button>{editing && <button type="button" className={secondary} onClick={() => { setEditing(null); setForm({ name: '', classroom: '', teacher: '' }) }}>Cancelar edición</button>}</fieldset></form>
    {!data.teachers.length && <p className="dash-card">El administrador debe crear primero las cuentas de los docentes.</p>}
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">{data.courses.map(course => <article key={course.id} className="dash-card space-y-3"><h3 className="text-lg font-bold">{course.name}</h3><p className="text-sm">{data.groups.find(g => g.id === course.classroom) && groupName(data.groups.find(g => g.id === course.classroom)!)}</p><p className="text-sm text-slate">{data.teachers.find(p => p.id === course.teacher)?.name}</p><button disabled={action.busy} className={secondary} onClick={() => { setEditing(course.id); setForm({ name: course.name, classroom: String(course.classroom), teacher: String(course.teacher) }) }}>Editar curso y docente</button></article>)}</div>
  </>
}
function Schedules({ data, reload }: Props) {
  const [target, setTarget] = useState(String(data.groups[0]?.id || ''))
  const [draft, setDraft] = useState<Block[]>([])
  const action = useAction()
  const schedule = data.schedules.find(s => s.classroom === Number(target))
  useEffect(() => { setDraft(schedule?.draft || []) }, [target, schedule])
  const dirty = JSON.stringify(draft) !== JSON.stringify(schedule?.draft || [])
  function changeGroup(value: string) {
    if (!dirty || window.confirm('Hay cambios sin guardar. ¿Descartarlos y cambiar de grupo?')) setTarget(value)
  }
  const courses = data.courses.filter(c => c.classroom === Number(target))
  function update(index: number, changes: Partial<Block>) { setDraft(draft.map((b, i) => i === index ? { ...b, ...changes } : b)) }
  async function save() {
    return request<Schedule>(schedule ? `/api/schedules/${schedule.id}/` : '/api/schedules/', { method: schedule ? 'PATCH' : 'POST', body: JSON.stringify({ classroom: Number(target), draft }) })
  }
  return <><p className="text-slate">Molde anual de 07:30 a 16:30. Editar el borrador no cambia el horario publicado.</p><Notice error={action.error} message={action.message} />
    <Label title="Año, grado y sección"><select className={field} disabled={action.busy} value={target} onChange={e => changeGroup(e.target.value)}><option value="">Selecciona un grupo</option>{data.groups.map(g => <option value={g.id} key={g.id}>{groupName(g)}</option>)}</select></Label>
    {target ? <><div className="flex flex-wrap gap-3 text-sm"><span className="rounded-full bg-pale px-4 py-2">{dirty ? 'Cambios sin guardar' : 'Borrador guardado'}</span><span className="rounded-full bg-blue/20 px-4 py-2">{schedule?.published_at ? `Publicado: ${new Date(schedule.published_at).toLocaleString('es-PE', { timeZone: 'America/Lima' })}` : 'Aún no publicado'}</span></div>
      <Timetable blocks={draft} courses={courses} />
      <form className="space-y-4" onSubmit={e => { e.preventDefault(); void action.run(async () => { await save(); await reload() }, 'Borrador guardado. La publicación vigente no cambió.') }}><fieldset disabled={action.busy} className="space-y-4">
        {draft.map((block, index) => <div className="dash-card grid items-end gap-3 sm:grid-cols-3 xl:grid-cols-6" key={index}>
          <Label title="Día"><select className={field} value={block.day} onChange={e => update(index, { day: Number(e.target.value) })}>{days.map((day, i) => <option key={day} value={i}>{day}</option>)}</select></Label>
          <Label title="Inicio"><input className={field} required type="time" min="07:30" max="16:29" value={block.start} onChange={e => update(index, { start: e.target.value })} /></Label>
          <Label title="Fin"><input className={field} required type="time" min="07:31" max="16:30" value={block.end} onChange={e => update(index, { end: e.target.value })} /></Label>
          <Label title="Tipo"><select className={field} value={block.kind} onChange={e => update(index, { kind: e.target.value, course_id: null, title: '' })}>{['curso', 'receso', 'almuerzo', 'evento'].map(kind => <option key={kind} value={kind}>{kind === 'evento' ? 'Evento extracurricular' : kind}</option>)}</select></Label>
          {block.kind === 'curso' ? <Label title="Curso / docente"><select required className={field} value={block.course_id || ''} onChange={e => update(index, { course_id: Number(e.target.value) })}><option value="">Selecciona un curso</option>{courses.map(c => <option key={c.id} value={c.id}>{c.name} · {data.teachers.find(p => p.id === c.teacher)?.name}</option>)}</select></Label> : <Label title="Título"><input className={field} maxLength={120} required={block.kind === 'evento'} value={block.title || ''} onChange={e => update(index, { title: e.target.value })} /></Label>}
          <Label title="Aula o espacio"><input className={field} maxLength={120} value={block.room || ''} onChange={e => update(index, { room: e.target.value })} /></Label>
          <button type="button" className={secondary} onClick={() => setDraft(draft.filter((_, i) => i !== index))}>Quitar bloque {index + 1}</button>
        </div>)}
        <div className="flex flex-wrap gap-3"><button type="button" className={secondary} onClick={() => setDraft([...draft, { day: 0, start: '07:30', end: '08:15', kind: 'curso', course_id: null }])}>Añadir bloque</button><button className={button}>Guardar borrador</button><button type="button" className={button} disabled={dirty || !schedule} onClick={() => void action.run(async () => { await request(`/api/schedules/${schedule!.id}/publish/`, { method: 'POST' }); await reload() }, 'Horario publicado para los estudiantes y docentes.')}>Publicar horario</button></div>
        {dirty && <p className="text-sm text-slate">Guarda los cambios antes de publicar.</p>}
      </fieldset></form>
      {schedule?.published && <details className="dash-card"><summary className="cursor-pointer font-bold">Ver publicación vigente</summary><Timetable blocks={schedule.published} courses={courses} /></details>}
    </> : <p className="dash-card">Crea primero un grado y sección.</p>}
  </>
}
export function Timetable({ blocks, courses = [] }: { blocks: Block[]; courses?: Course[] }) {
  const minutes = (value: string) => { const [hour, minute] = value.split(':').map(Number); return hour * 60 + minute - 450 }
  return <div className="dash-card overflow-x-auto"><div className="min-w-[1000px]"><div className="grid grid-cols-[60px_repeat(7,1fr)] text-center text-xs font-bold"><span>Hora</span>{days.map(day => <span key={day}>{day}</span>)}</div><div className="mt-4 grid grid-cols-[60px_repeat(7,1fr)]"><div className="relative h-[540px] text-[10px] text-slate">{Array.from({ length: 19 }, (_, i) => <span key={i} className="absolute" style={{ top: i * 30 - 6 }}>{`${String(Math.floor((450 + i * 30) / 60)).padStart(2, '0')}:${(450 + i * 30) % 60 ? '30' : '00'}`}</span>)}</div>{days.map((day, index) => <div key={day} className="relative h-[540px] border-l border-ink/10 bg-[repeating-linear-gradient(to_bottom,transparent_0px,transparent_29px,#e5e7eb_29px,#e5e7eb_30px)]">{blocks.filter(b => b.day === index).map((b, i) => <div key={i} className={`absolute inset-x-1 overflow-hidden rounded-lg border p-1 text-[10px] ${b.kind === 'curso' ? 'border-blue bg-blue/30' : b.kind === 'evento' ? 'border-pink bg-pale' : 'border-ink/10 bg-slate/10'}`} style={{ top: Math.max(0, minutes(b.start)), height: Math.max(16, minutes(b.end) - minutes(b.start)) }} title={`${b.start}–${b.end} · ${b.title || courses.find(c => c.id === b.course_id)?.name || b.kind}`}><strong className="block">{b.start}–{b.end}</strong>{b.title || courses.find(c => c.id === b.course_id)?.name || b.kind}{b.room && <span className="block">{b.room}</span>}</div>)}</div>)}</div></div></div>
}
function Events({ data, reload }: Props) {
  const action = useAction()
  const [form, setForm] = useState({ year: new Date().getFullYear(), all_classrooms: false, classroom_ids: [] as number[], day: 0, start: '14:00', end: '15:00', title: '', room: '' })
  return <><p className="text-slate">Añade un evento extracurricular al borrador semanal de algunos grupos o de todos los del año. Después revisa y publica cada horario.</p><Notice error={action.error} message={action.message} /><form className="dash-card max-w-3xl" onSubmit={e => { e.preventDefault(); void action.run(async () => { await request('/api/schedules/events/', { method: 'POST', body: JSON.stringify({ ...form, classroom_ids: form.all_classrooms ? [] : form.classroom_ids }) }); await reload() }, 'Evento añadido a los borradores. Revisa los conflictos en Horarios antes de publicar.') }}><fieldset disabled={action.busy} className="grid gap-4 sm:grid-cols-2">
    <Label title="Nombre del evento"><input className={field} required maxLength={120} value={form.title} onChange={e => setForm({ ...form, title: e.target.value })} /></Label><Label title="Año académico"><input className={field} required type="number" min={2000} max={2200} value={form.year} onChange={e => setForm({ ...form, year: Number(e.target.value), classroom_ids: [] })} /></Label>
    <Label title="Día"><select className={field} value={form.day} onChange={e => setForm({ ...form, day: Number(e.target.value) })}>{days.map((day, i) => <option key={day} value={i}>{day}</option>)}</select></Label><Label title="Lugar"><input className={field} maxLength={120} value={form.room} onChange={e => setForm({ ...form, room: e.target.value })} /></Label>
    <Label title="Inicio"><input className={field} type="time" required min="07:30" max="16:29" value={form.start} onChange={e => setForm({ ...form, start: e.target.value })} /></Label><Label title="Fin"><input className={field} type="time" required min="07:31" max="16:30" value={form.end} onChange={e => setForm({ ...form, end: e.target.value })} /></Label>
    <label className="flex items-center gap-3 text-sm sm:col-span-2"><input type="checkbox" checked={form.all_classrooms} onChange={e => setForm({ ...form, all_classrooms: e.target.checked })} />Todos los grados y secciones del año</label>
    {!form.all_classrooms && <Label title="Grados y secciones destinatarios"><select className={field} multiple required size={5} value={form.classroom_ids.map(String)} onChange={e => setForm({ ...form, classroom_ids: Array.from(e.target.selectedOptions, option => Number(option.value)) })}>{data.groups.filter(g => g.year === form.year).map(g => <option key={g.id} value={g.id}>{groupName(g)}</option>)}</select></Label>}
    <div className="sm:col-span-2"><button className={button}>Añadir evento a borradores</button></div>
  </fieldset></form></>
}
