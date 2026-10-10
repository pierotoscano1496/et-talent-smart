import { cloneElement, isValidElement, useId, useState } from 'react'
import type { ReactNode } from 'react'

export type Person = { id: number; name: string; role: string; classroom: number | null; grade: string; section: string; year: number | null; is_active: boolean }
export type Classroom = { id: number; year: number; grade: string; section: string }
export type Course = { id: number; name: string; classroom: number; teacher: number }
export type Block = { day: number; start: string; end: string; kind: string; course_id?: number | null; title?: string; room?: string }
export type Schedule = { id: number; classroom: number; draft: Block[]; published: Block[] | null; published_at: string | null }
export const days = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
export const roles: Record<string, string> = { administrador: 'Administrador', coordinador: 'Coordinador', auxiliar: 'Auxiliar de educación', docente: 'Docente', estudiante: 'Estudiante', padre: 'Padre de familia' }
export const field = 'mt-2 w-full rounded-xl border border-ink/20 bg-white p-3 text-sm text-ink focus:outline-pink disabled:bg-pale/30'
export const button = 'rounded-xl bg-navy px-5 py-3 text-sm font-semibold text-white disabled:opacity-50'
export const secondary = 'rounded-xl border border-ink/20 px-4 py-3 text-sm font-semibold text-navy disabled:opacity-50'
export const groupName = (group: Classroom) => `${group.year} · ${group.grade}° · ${group.section}`
export function Label({ children, title }: { children: ReactNode; title: string }) {
  const id = useId()
  return <label className="block text-sm font-semibold text-navy"><span id={id}>{title}</span>{isValidElement<{ 'aria-labelledby'?: string }>(children) ? cloneElement(children, { 'aria-labelledby': id }) : children}</label>
}
export function Notice({ error, message }: { error?: string; message?: string }) {
  return <>{error && <p role="alert" className="my-4 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-900">{error}</p>}{message && <p role="status" className="my-4 rounded-xl bg-blue/20 p-4 text-sm text-navy">{message}</p>}</>
}
export function useAction() {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  async function run(work: () => Promise<void>, success = 'Cambios guardados.') {
    setBusy(true); setError(''); setMessage('')
    try { await work(); setMessage(success) }
    catch (err) { setError((err as Error).message) }
    finally { setBusy(false) }
  }
  return { busy, error, message, run, setError }
}
