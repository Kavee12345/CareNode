import { useState, useEffect } from 'react'
import { Plus, Pill, CheckCircle, XCircle, Clock, Trash2 } from 'lucide-react'
import { healthApi } from '../api/health'
import type { Prescription } from '../types'
import { format } from 'date-fns'
import clsx from 'clsx'

const STATUS_CONFIG = {
  active: { color: 'bg-green-100 text-green-700', icon: CheckCircle, label: 'Active' },
  completed: { color: 'bg-gray-100 text-gray-600', icon: CheckCircle, label: 'Completed' },
  discontinued: { color: 'bg-red-100 text-red-600', icon: XCircle, label: 'Discontinued' },
}

export default function PrescriptionsPage() {
  const [prescriptions, setPrescriptions] = useState<Prescription[]>([])
  const [filter, setFilter] = useState<string | undefined>('active')
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({
    medication_name: '',
    dosage: '',
    frequency: '',
    start_date: new Date().toISOString().split('T')[0],
    end_date: '',
    prescribing_doctor: '',
    notes: '',
  })

  const load = async () => {
    const { data } = await healthApi.listPrescriptions(filter)
    setPrescriptions(data)
  }

  useEffect(() => { load() }, [filter])

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    await healthApi.createPrescription(form)
    setShowForm(false)
    setForm({ medication_name: '', dosage: '', frequency: '', start_date: new Date().toISOString().split('T')[0], end_date: '', prescribing_doctor: '', notes: '' })
    load()
  }

  const handleStatusChange = async (id: string, status: string) => {
    await healthApi.updatePrescription(id, { status })
    load()
  }

  const handleDelete = async (id: string) => {
    if (!confirm('Remove this prescription?')) return
    await healthApi.deletePrescription(id)
    load()
  }

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Medications</h1>
          <p className="text-gray-500 mt-1">Track your prescriptions and medication history.</p>
        </div>
        <button onClick={() => setShowForm(!showForm)} className="btn-primary flex items-center gap-2 text-sm">
          <Plus className="w-4 h-4" /> Add medication
        </button>
      </div>

      {/* Filter tabs */}
      <div className="flex gap-2 mb-6">
        {[undefined, 'active', 'completed', 'discontinued'].map((s) => (
          <button
            key={s ?? 'all'}
            onClick={() => setFilter(s)}
            className={clsx(
              'px-3 py-1.5 rounded-lg text-sm font-medium transition-colors',
              filter === s ? 'bg-primary-100 text-primary-700' : 'text-gray-600 hover:bg-gray-100'
            )}
          >
            {s ? s.charAt(0).toUpperCase() + s.slice(1) : 'All'}
          </button>
        ))}
      </div>

      {/* Add form */}
      {showForm && (
        <form onSubmit={handleCreate} className="card p-4 mb-6 space-y-3">
          <h3 className="font-semibold text-gray-800">Add Medication</h3>
          <div className="grid grid-cols-2 gap-3">
            <div className="col-span-2">
              <label className="block text-xs font-medium text-gray-600 mb-1">Medication name *</label>
              <input className="input" placeholder="e.g., Metformin" value={form.medication_name} onChange={(e) => setForm({ ...form, medication_name: e.target.value })} required />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Dosage</label>
              <input className="input" placeholder="e.g., 500mg" value={form.dosage} onChange={(e) => setForm({ ...form, dosage: e.target.value })} />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Frequency</label>
              <input className="input" placeholder="e.g., Twice daily" value={form.frequency} onChange={(e) => setForm({ ...form, frequency: e.target.value })} />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Start date</label>
              <input type="date" className="input" value={form.start_date} onChange={(e) => setForm({ ...form, start_date: e.target.value })} />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">End date</label>
              <input type="date" className="input" value={form.end_date} onChange={(e) => setForm({ ...form, end_date: e.target.value })} />
            </div>
            <div className="col-span-2">
              <label className="block text-xs font-medium text-gray-600 mb-1">Prescribing doctor</label>
              <input className="input" placeholder="Dr. Smith" value={form.prescribing_doctor} onChange={(e) => setForm({ ...form, prescribing_doctor: e.target.value })} />
            </div>
            <div className="col-span-2">
              <label className="block text-xs font-medium text-gray-600 mb-1">Notes</label>
              <textarea className="input" rows={2} value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} />
            </div>
          </div>
          <div className="flex gap-2">
            <button type="submit" className="btn-primary text-sm">Save</button>
            <button type="button" onClick={() => setShowForm(false)} className="btn-secondary text-sm">Cancel</button>
          </div>
        </form>
      )}

      {/* List */}
      {prescriptions.length === 0 ? (
        <div className="card p-12 text-center">
          <Pill className="w-10 h-10 text-gray-300 mx-auto mb-3" />
          <p className="text-gray-500">No medications found. Add them manually or upload a prescription document.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {prescriptions.map((rx) => {
            const cfg = STATUS_CONFIG[rx.status as keyof typeof STATUS_CONFIG] || STATUS_CONFIG.active
            const StatusIcon = cfg.icon
            return (
              <div key={rx.id} className="card p-4 flex items-start gap-4 group">
                <div className="w-10 h-10 bg-purple-50 rounded-lg flex items-center justify-center flex-shrink-0">
                  <Pill className="w-5 h-5 text-purple-600" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-start justify-between gap-2">
                    <p className="font-medium text-gray-900">{rx.medication_name}</p>
                    <div className="flex items-center gap-2">
                      <span className={clsx('flex items-center gap-1 text-xs px-2 py-0.5 rounded-full font-medium', cfg.color)}>
                        <StatusIcon className="w-3 h-3" />
                        {cfg.label}
                      </span>
                    </div>
                  </div>
                  <div className="flex flex-wrap gap-x-4 gap-y-1 mt-1">
                    {rx.dosage && <p className="text-sm text-gray-600">{rx.dosage}</p>}
                    {rx.frequency && <p className="text-sm text-gray-500">{rx.frequency}</p>}
                    {rx.prescribing_doctor && <p className="text-sm text-gray-400">Dr. {rx.prescribing_doctor}</p>}
                  </div>
                  {(rx.start_date || rx.end_date) && (
                    <p className="text-xs text-gray-400 mt-1">
                      {rx.start_date && format(new Date(rx.start_date), 'MMM d, yyyy')}
                      {rx.end_date && ` → ${format(new Date(rx.end_date), 'MMM d, yyyy')}`}
                    </p>
                  )}
                  {rx.notes && <p className="text-xs text-gray-500 mt-1 italic">{rx.notes}</p>}
                  {/* Status actions */}
                  {rx.status === 'active' && (
                    <div className="flex gap-2 mt-2">
                      <button onClick={() => handleStatusChange(rx.id, 'completed')} className="text-xs text-green-600 hover:underline">Mark completed</button>
                      <button onClick={() => handleStatusChange(rx.id, 'discontinued')} className="text-xs text-red-500 hover:underline">Discontinue</button>
                    </div>
                  )}
                </div>
                <button
                  onClick={() => handleDelete(rx.id)}
                  className="opacity-0 group-hover:opacity-100 p-1.5 text-gray-400 hover:text-red-500 rounded-lg hover:bg-red-50 transition-all"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
