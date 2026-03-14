import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { MessageSquare, FileText, Activity, Pill, AlertTriangle, Upload } from 'lucide-react'
import { useAuthStore } from '../store/authStore'
import { documentsApi } from '../api/documents'
import { healthApi } from '../api/health'
import { chatApi } from '../api/chat'
import type { Document, HealthEvent, Conversation } from '../types'
import { format } from 'date-fns'

export default function DashboardPage() {
  const { user } = useAuthStore()
  const [docs, setDocs] = useState<Document[]>([])
  const [events, setEvents] = useState<HealthEvent[]>([])
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [prescriptions, setPrescriptions] = useState<number>(0)

  useEffect(() => {
    documentsApi.list(1, 5).then((r) => setDocs(r.data.items))
    healthApi.getTimeline({ }).then((r) => setEvents(r.data.slice(0, 5)))
    chatApi.listConversations().then((r) => setConversations(r.data.items.slice(0, 5)))
    healthApi.listPrescriptions('active').then((r) => setPrescriptions(r.data.length))
  }, [])

  const urgentEvents = events.filter((e) => e.severity === 'high')

  return (
    <div className="p-6 max-w-5xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">
          Good {getGreeting()}, {user?.full_name?.split(' ')[0] || 'there'}
        </h1>
        <p className="text-gray-500 mt-1">Here's a summary of your health dashboard.</p>
      </div>

      {/* Urgent Alert */}
      {urgentEvents.length > 0 && (
        <div className="mb-6 bg-red-50 border border-red-200 rounded-xl p-4 flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
          <div>
            <p className="font-medium text-red-800">Attention needed</p>
            <p className="text-sm text-red-700 mt-0.5">
              {urgentEvents.length} urgent health event(s) in your timeline.{' '}
              <Link to="/timeline" className="underline font-medium">View timeline</Link>
            </p>
          </div>
        </div>
      )}

      {/* Quick action cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        <QuickCard to="/chat" icon={MessageSquare} label="Ask Agent" color="blue" />
        <QuickCard to="/documents" icon={Upload} label="Upload Report" color="purple" />
        <QuickCard to="/timeline" icon={Activity} label="Health Timeline" color="green" />
        <QuickCard to="/prescriptions" icon={Pill} label="Medications" color="orange" />
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        <StatCard label="Documents" value={docs.length} icon={FileText} />
        <StatCard label="Health Events" value={events.length} icon={Activity} />
        <StatCard label="Active Meds" value={prescriptions} icon={Pill} />
        <StatCard label="Conversations" value={conversations.length} icon={MessageSquare} />
      </div>

      {/* Recent activity */}
      <div className="grid md:grid-cols-2 gap-6">
        {/* Recent docs */}
        <div className="card p-5">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold text-gray-900">Recent Documents</h2>
            <Link to="/documents" className="text-xs text-primary-600 hover:underline">View all</Link>
          </div>
          {docs.length === 0 ? (
            <p className="text-sm text-gray-500">No documents uploaded yet.</p>
          ) : (
            <ul className="space-y-3">
              {docs.map((doc) => (
                <li key={doc.id} className="flex items-center gap-3">
                  <FileText className="w-4 h-4 text-gray-400 flex-shrink-0" />
                  <div className="min-w-0">
                    <p className="text-sm text-gray-800 truncate">{doc.original_name}</p>
                    <p className="text-xs text-gray-400">
                      {doc.doc_type || 'document'} · <StatusBadge status={doc.processing_status} />
                    </p>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* Recent conversations */}
        <div className="card p-5">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold text-gray-900">Recent Conversations</h2>
            <Link to="/chat" className="text-xs text-primary-600 hover:underline">View all</Link>
          </div>
          {conversations.length === 0 ? (
            <div className="text-center py-4">
              <p className="text-sm text-gray-500 mb-3">Start your first conversation</p>
              <Link to="/chat" className="btn-primary text-sm px-4 py-1.5 inline-flex">
                Ask a question
              </Link>
            </div>
          ) : (
            <ul className="space-y-3">
              {conversations.map((conv) => (
                <li key={conv.id}>
                  <Link
                    to={`/chat/${conv.id}`}
                    className="flex items-center gap-3 hover:bg-gray-50 rounded-lg p-1 -ml-1 transition-colors"
                  >
                    <MessageSquare className="w-4 h-4 text-gray-400 flex-shrink-0" />
                    <div className="min-w-0">
                      <p className="text-sm text-gray-800 truncate">{conv.title || 'Untitled'}</p>
                      <p className="text-xs text-gray-400">
                        {format(new Date(conv.updated_at), 'MMM d, HH:mm')}
                      </p>
                    </div>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  )
}

function QuickCard({ to, icon: Icon, label, color }: { to: string; icon: React.ElementType; label: string; color: string }) {
  const colors: Record<string, string> = {
    blue: 'bg-blue-50 text-blue-600 hover:bg-blue-100',
    purple: 'bg-purple-50 text-purple-600 hover:bg-purple-100',
    green: 'bg-green-50 text-green-600 hover:bg-green-100',
    orange: 'bg-orange-50 text-orange-600 hover:bg-orange-100',
  }
  return (
    <Link
      to={to}
      className={`flex flex-col items-center justify-center gap-2 p-4 rounded-xl transition-colors ${colors[color]}`}
    >
      <Icon className="w-6 h-6" />
      <span className="text-sm font-medium">{label}</span>
    </Link>
  )
}

function StatCard({ label, value, icon: Icon }: { label: string; value: number; icon: React.ElementType }) {
  return (
    <div className="card p-4">
      <div className="flex items-center gap-2 text-gray-500 mb-2">
        <Icon className="w-4 h-4" />
        <span className="text-xs font-medium uppercase tracking-wide">{label}</span>
      </div>
      <p className="text-2xl font-bold text-gray-900">{value}</p>
    </div>
  )
}

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    done: 'text-green-600',
    pending: 'text-yellow-600',
    processing: 'text-blue-600',
    failed: 'text-red-600',
  }
  return <span className={`font-medium ${colors[status] || 'text-gray-500'}`}>{status}</span>
}

function getGreeting() {
  const h = new Date().getHours()
  if (h < 12) return 'morning'
  if (h < 17) return 'afternoon'
  return 'evening'
}
