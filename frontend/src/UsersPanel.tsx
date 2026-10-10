import { useEffect, useState } from 'react'
import { currentAccount, listAll, request } from './api'
import { button, field, Label, Notice, roles, secondary, useAction } from './management'

type User = { id: number; email: string; first_name: string; last_name: string; role: string; rfid_uid: string | null; is_active: boolean; children: number[] }
const blank = { first_name: '', last_name: '', email: '', password: '', role: 'estudiante', rfid_uid: '', is_active: true, children: [] as number[] }
export default function UsersPanel() {
  const [users, setUsers] = useState<User[]>([])
  const [selected, setSelected] = useState<number | null>(null)
  const [form, setForm] = useState(blank)
  const [search, setSearch] = useState('')
  const [roleFilter, setRoleFilter] = useState('')
  const [loading, setLoading] = useState(true)
  const action = useAction()
  const load = async () => setUsers(await listAll<User>('/api/users/'))
  useEffect(() => { let active = true; void listAll<User>('/api/users/').then(data => { if (active) setUsers(data) }).catch(err => { if (active) action.setError(err.message) }).finally(() => { if (active) setLoading(false) }); return () => { active = false } }, [])
  const visible = users.filter(user => (!roleFilter || user.role === roleFilter) && `${user.first_name} ${user.last_name} ${user.email}`.toLowerCase().includes(search.toLowerCase()))
  const ownAccount = selected === currentAccount()?.id
  return <section className="space-y-6">
    <div><h2 className="text-3xl font-bold text-navy">Cuentas y llaves RFID</h2><p className="mt-2 text-slate">Crea las cuentas institucionales y asigna una llave única a cada estudiante.</p></div>
    <Notice error={action.error} message={action.message} />
    <div className="grid items-start gap-6 xl:grid-cols-[1fr_1.2fr]">
      <form className="dash-card space-y-4" onSubmit={event => { event.preventDefault(); void action.run(async () => {
        const payload: Record<string, unknown> = { ...form, rfid_uid: form.role === 'estudiante' ? form.rfid_uid.trim().toUpperCase() || null : null, children: form.role === 'padre' ? form.children : [] }
        if (!form.password) delete payload.password
        await request(selected ? `/api/users/${selected}/` : '/api/users/', { method: selected ? 'PATCH' : 'POST', body: JSON.stringify(payload) })
        setSelected(null); setForm(blank); await load()
      }, selected ? 'Cuenta actualizada.' : 'Cuenta creada.') }}>
        <div className="flex items-center justify-between gap-3"><h3 className="text-lg font-bold text-navy">{selected ? 'Editar cuenta' : 'Nueva cuenta'}</h3>{selected && <button type="button" className={secondary} disabled={action.busy} onClick={() => { setSelected(null); setForm(blank) }}>Cancelar</button>}</div>
        <fieldset disabled={action.busy || loading} className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2"><Label title="Nombres"><input className={field} required maxLength={150} value={form.first_name} onChange={e => setForm({ ...form, first_name: e.target.value })} /></Label><Label title="Apellidos"><input className={field} required maxLength={150} value={form.last_name} onChange={e => setForm({ ...form, last_name: e.target.value })} /></Label></div>
          <Label title="Correo institucional"><input type="email" className={field} required value={form.email} onChange={e => setForm({ ...form, email: e.target.value })} /></Label>
          <Label title={selected ? 'Nueva contraseña (opcional)' : 'Contraseña inicial'}><input type="password" autoComplete="new-password" minLength={8} className={field} required={!selected} value={form.password} onChange={e => setForm({ ...form, password: e.target.value })} /></Label>
          <Label title="Rol"><select className={field} disabled={ownAccount} value={form.role} onChange={e => setForm({ ...form, role: e.target.value, rfid_uid: '', children: [] })}>{Object.entries(roles).map(([value, name]) => <option key={value} value={value}>{name}</option>)}</select></Label>
          {form.role === 'estudiante' && <Label title="Llave RFID (vacío para retirar o asignar después)"><input className={field} maxLength={64} value={form.rfid_uid} onChange={e => setForm({ ...form, rfid_uid: e.target.value })} /></Label>}
          {form.role === 'padre' && <Label title="Hijos vinculados (selección múltiple)"><select multiple size={5} className={field} value={form.children.map(String)} onChange={e => setForm({ ...form, children: Array.from(e.target.selectedOptions, option => Number(option.value)) })}>{users.filter(user => user.role === 'estudiante').map(user => <option key={user.id} value={user.id}>{user.first_name} {user.last_name} · {user.email}</option>)}</select></Label>}
          <label className="flex items-center gap-3 text-sm"><input type="checkbox" disabled={ownAccount} checked={form.is_active} onChange={e => setForm({ ...form, is_active: e.target.checked })} />Cuenta activa</label>
          <p className="text-xs leading-5 text-slate">Los grados y secciones son asignados por el coordinador.</p>
          <button className={button}>{action.busy ? 'Guardando…' : selected ? 'Guardar cuenta' : 'Crear cuenta'}</button>
        </fieldset>
      </form>
      <div className="dash-card min-w-0"><div className="grid gap-4 sm:grid-cols-2"><Label title="Buscar usuario"><input type="search" className={field} value={search} onChange={e => setSearch(e.target.value)} placeholder="Nombre o correo" /></Label><Label title="Filtrar por rol"><select className={field} value={roleFilter} onChange={e => setRoleFilter(e.target.value)}><option value="">Todos los roles</option>{Object.entries(roles).map(([value, name]) => <option key={value} value={value}>{name}</option>)}</select></Label></div>
        {loading ? <p role="status" className="mt-5">Cargando cuentas…</p> : <><p className="my-4 text-sm text-slate">{visible.length} cuentas</p><div className="overflow-x-auto"><table className="w-full text-left text-sm"><thead><tr><th className="p-2">Usuario</th><th className="p-2">Rol / estado</th><th className="p-2">Llave</th><th className="p-2">Acción</th></tr></thead><tbody>{visible.map(user => <tr className="border-t border-ink/10" key={user.id}><td className="p-2"><strong>{user.first_name} {user.last_name}</strong><span className="block text-xs text-slate">{user.email}</span></td><td className="p-2">{roles[user.role]}<span className="block text-xs">{user.is_active ? 'Activa' : 'Inactiva'}</span></td><td className="p-2">{user.rfid_uid || '—'}</td><td className="p-2"><button className={secondary} disabled={action.busy} onClick={() => { setSelected(user.id); setForm({ first_name: user.first_name, last_name: user.last_name, email: user.email, role: user.role, password: '', rfid_uid: user.rfid_uid || '', is_active: user.is_active, children: user.children }) }}>Editar</button></td></tr>)}</tbody></table></div>{!visible.length && <p>No se encontraron cuentas.</p>}</>}
      </div>
    </div>
  </section>
}
