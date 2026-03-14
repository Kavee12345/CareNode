import { useState, useEffect } from 'react'
import { Plus, Activity, Trash2, AlertTriangle, Info, Heart, Pill, FlaskConical } from 'lucide-react'
import { healthApi } from '../api/health'
import type { HealthEvent } from '../types'
import { format } from 'date-fns'
import clsx from 'clsx'

const EVENT_TYPE_CONFIG: Record<string, { icon: React.ElementType; color: string; bg: string }> = {
  symptom: { icon: Activity, color: 'text-red-600', bg: 'bg-red-50' },
  lab_result: { icon: FlaskConical, color: 'text-blue-600', bg: 'bg-blue-50' },
  prescription: { icon: Pill, color: 'text-purple-600', bg: 'bg-purple-50' },
  vital: { icon: Heart, color: 'text-pink-600', bg: 'bg-pink-50' },
  pattern_detected: { icon: Info, color: 'text-orange-600', bg: 'bg-orange-50' },
  visit: { icon: Activity, color: 'text-green-600', bg: 'bg-green-50' },
}

const SEVERITY_CONFIG = {
  high: 'bg-red-100 text-red-700',
  medium: 'bg-yellow-100 text-yellow-700',
  low: 'bg-green-100 text-green-700',
}

export default function HealthTimelinePage() {
  const [events, setEvents] = useState<HealthEvent[]>([])
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({
    event_type: 'symptom',
    title: '',
    description: '',
    event_date: new Date().toISOString().split('T')[0],
    severity: 'low',
  })

  const load = async () => {
    const { data } = await healthApi.getTimeline()
    setEvents(data)
  }

  useEffect(() => { load() }, [])

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    await healthApi.createEvent(form)
    setShowForm(false)
    setForm({ event_type: 'symptom', title: '', description: '', event_date: new Date().toISOString().split('T')[0], severity: 'low' })
    load()
  }

  const handleDelete = async (id: string) => {
    if (!confirm('Delete this health event?')) return
    await healthApi.deleteEvent(id)
    load()
  }

  // Group by month
  const grouped = events.reduce<Record<string, HealthEvent[]>>((acc, event) => {
    const month = format(new Date(event.event_date), 'MMMM yyyy')
    acc[month] = acc[month] || []
    acc[month].push(event)
    return acc
  }, {})

  return (
    <div className="p-6 max-w-3xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Health Timeline</h1>
          <p className="text-gray-500 mt-1">Your chronological health history, auto-populated from chats and documents.</p>
        </div>
        <button
          onClick={() => setShowForm(!showForm)}
          className="btn-primary flex items-center gap-2 text-sm"
        >
          <Plus className="w-4 h-4" /> Add event
        </button>
      </div>

      {/* Add event form */}
      {showForm && (
        <form onSubmit={handleCreate} className="card p-4 mb-6 space-y-3">
          <h3 className="font-semibold text-gray-800">New Health Event</h3>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Type</label>
              <select className="input" value={form.event_type} onChange={(e) => setForm({ ...form, event_type: e.target.value })}>
                <option value="symptom">Symptom</option>
                <option value="lab_result">Lab Result</option>
                <option value="prescription">Prescription</option>
                <option value="vital">Vital Sign</option>
                <option value="visit">Doctor Visit</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Date</label>
              <input type="date" className="input" value={form.event_date} onChange={(e) => setForm({ ...form, event_date: e.target.value })} required />
            </div>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Title</label>
            <input className="input" placeholder="e.g., Blood pressure 140/90" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} required />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Description (optional)</label>
            <textarea className="input" rows={2} value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Severity</label>
            <select className="input" value={form.severity} onChange={(e) => setForm({ ...form, severity: e.target.value })}>
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
            </select>
          </div>
          <div className="flex gap-2 pt-1">
            <button type="submit" className="btn-primary text-sm">Save</button>
            <button type="button" onClick={() => setShowForm(false)} className="btn-secondary text-sm">Cancel</button>
          </div>
        </form>
      )}

      {/* Timeline */}
      {events.length === 0 ? (
        <div className="card p-12 text-center">
          <Activity className="w-10 h-10 text-gray-300 mx-auto mb-3" />
          <p className="text-gray-500">No health events yet. They'll appear automatically from your chat conversations, or you can add them manually.</p>
        </div>
      ) : (
        <div className="space-y-8">
          {Object.entries(grouped).map(([month, monthEvents]) => (
            <div key={month}>
              <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">{month}</h3>
              <div className="space-y-3">
                {monthEvents.map((event) => {
                  const cfg = EVENT_TYPE_CONFIG[event.event_type] || EVENT_TYPE_CONFIG.visit
                  const Icon = cfg.icon
                  return (
                    <div key={event.id} className="card p-4 flex items-start gap-3 group">
                      <div className={clsx('w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0', cfg.bg)}>
                        <Icon className={clsx('w-4 h-4', cfg.color)} />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-start justify-between gap-2">
                          <p className="text-sm font-medium text-gray-900">{event.title}</p>
                          <div className="flex items-center gap-2 flex-shrink-0">
                            {event.severity && (
                              <span className={clsx('text-xs px-2 py-0.5 rounded-full font-medium', SEVERITY_CONFIG[event.severity as keyof typeof SEVERITY_CONFIG] || 'bg-gray-100 text-gray-600')}>
                                {event.severity}
                              </span>
                            )}
                            <button
                              onClick={() => handleDelete(event.id)}
                              className="opacity-0 group-hover:opacity-100 p-1 text-gray-400 hover:text-red-500 transition-all"
                            >
                              <Trash2 className="w-3 h-3" />
                            </button>
                          </div>
                        </div>
                        {event.description && (
                          <p className="text-xs text-gray-500 mt-1">{event.description}</p>
                        )}
                        <p className="text-xs text-gray-400 mt-1">
                          {format(new Date(event.event_date), 'MMMM d, yyyy')} · {event.event_type.replace('_', ' ')}
                        </p>
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
