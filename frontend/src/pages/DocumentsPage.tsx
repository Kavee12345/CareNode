import { useState, useEffect, useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import { FileText, Upload, Trash2, Download, RefreshCw, CheckCircle, Clock, XCircle, Loader } from 'lucide-react'
import { documentsApi } from '../api/documents'
import type { Document } from '../types'
import { format } from 'date-fns'
import clsx from 'clsx'

const STATUS_CONFIG = {
  done: { icon: CheckCircle, color: 'text-green-600', bg: 'bg-green-50', label: 'Processed' },
  pending: { icon: Clock, color: 'text-yellow-600', bg: 'bg-yellow-50', label: 'Queued' },
  processing: { icon: Loader, color: 'text-blue-600', bg: 'bg-blue-50', label: 'Processing' },
  failed: { icon: XCircle, color: 'text-red-600', bg: 'bg-red-50', label: 'Failed' },
}

const DOC_TYPE_LABELS: Record<string, string> = {
  lab_report: 'Lab Report',
  prescription: 'Prescription',
  imaging: 'Imaging',
  other: 'Document',
}

export default function DocumentsPage() {
  const [documents, setDocuments] = useState<Document[]>([])
  const [total, setTotal] = useState(0)
  const [uploading, setUploading] = useState(false)
  const [uploadError, setUploadError] = useState('')

  const load = async () => {
    const { data } = await documentsApi.list()
    setDocuments(data.items)
    setTotal(data.total)
  }

  useEffect(() => { load() }, [])

  // Poll for processing status
  useEffect(() => {
    const hasProcessing = documents.some((d) => d.processing_status === 'pending' || d.processing_status === 'processing')
    if (!hasProcessing) return
    const interval = setInterval(load, 3000)
    return () => clearInterval(interval)
  }, [documents])

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    if (acceptedFiles.length === 0) return
    setUploading(true)
    setUploadError('')
    for (const file of acceptedFiles) {
      try {
        await documentsApi.upload(file)
      } catch (err: unknown) {
        const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
        setUploadError(msg || `Failed to upload ${file.name}`)
      }
    }
    setUploading(false)
    load()
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'image/png': ['.png'],
      'image/jpeg': ['.jpg', '.jpeg'],
      'text/plain': ['.txt'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
    },
    maxSize: 50 * 1024 * 1024,
    multiple: true,
  })

  const handleDownload = async (doc: Document) => {
    const { data } = await documentsApi.getDownloadUrl(doc.id)
    window.open(data.url, '_blank')
  }

  const handleDelete = async (id: string) => {
    if (!confirm('Delete this document? This will also remove its health data from your agent.')) return
    await documentsApi.delete(id)
    load()
  }

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Health Documents</h1>
          <p className="text-gray-500 mt-1">Upload reports, prescriptions, and lab results. Your agent learns from them.</p>
        </div>
        <button onClick={load} className="btn-secondary flex items-center gap-2 text-sm">
          <RefreshCw className="w-4 h-4" /> Refresh
        </button>
      </div>

      {/* Drop zone */}
      <div
        {...getRootProps()}
        className={clsx(
          'border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-colors mb-6',
          isDragActive ? 'border-primary-400 bg-primary-50' : 'border-gray-300 hover:border-primary-300 hover:bg-gray-50'
        )}
      >
        <input {...getInputProps()} />
        <Upload className={clsx('w-8 h-8 mx-auto mb-3', isDragActive ? 'text-primary-500' : 'text-gray-400')} />
        {uploading ? (
          <p className="text-primary-600 font-medium">Uploading...</p>
        ) : isDragActive ? (
          <p className="text-primary-600 font-medium">Drop files here</p>
        ) : (
          <>
            <p className="text-gray-700 font-medium">Drop files here, or click to browse</p>
            <p className="text-gray-400 text-sm mt-1">PDF, PNG, JPG, DOCX, TXT · Max 50MB each</p>
          </>
        )}
      </div>

      {uploadError && (
        <div className="mb-4 bg-red-50 border border-red-200 rounded-lg px-4 py-3 text-sm text-red-700">
          {uploadError}
        </div>
      )}

      {/* Documents list */}
      {documents.length === 0 ? (
        <div className="card p-12 text-center">
          <FileText className="w-10 h-10 text-gray-300 mx-auto mb-3" />
          <p className="text-gray-500">No documents yet. Upload your first health record above.</p>
        </div>
      ) : (
        <div className="card overflow-hidden">
          <div className="px-4 py-3 border-b border-gray-200 flex items-center justify-between">
            <p className="text-sm font-medium text-gray-700">{total} document{total !== 1 ? 's' : ''}</p>
          </div>
          <ul className="divide-y divide-gray-100">
            {documents.map((doc) => {
              const cfg = STATUS_CONFIG[doc.processing_status as keyof typeof STATUS_CONFIG] || STATUS_CONFIG.pending
              const StatusIcon = cfg.icon
              return (
                <li key={doc.id} className="flex items-center gap-4 px-4 py-3 hover:bg-gray-50 transition-colors">
                  <div className="w-9 h-9 bg-gray-100 rounded-lg flex items-center justify-center flex-shrink-0">
                    <FileText className="w-4 h-4 text-gray-500" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900 truncate">{doc.original_name}</p>
                    <p className="text-xs text-gray-400 mt-0.5">
                      {DOC_TYPE_LABELS[doc.doc_type || 'other']} ·{' '}
                      {doc.file_size_bytes ? `${(doc.file_size_bytes / 1024).toFixed(0)} KB` : ''} ·{' '}
                      {format(new Date(doc.created_at), 'MMM d, yyyy')}
                    </p>
                  </div>
                  <div className={clsx('flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium', cfg.bg, cfg.color)}>
                    <StatusIcon className={clsx('w-3 h-3', doc.processing_status === 'processing' && 'animate-spin')} />
                    {cfg.label}
                  </div>
                  <div className="flex items-center gap-1">
                    <button
                      onClick={() => handleDownload(doc)}
                      className="p-1.5 text-gray-400 hover:text-gray-700 rounded-lg hover:bg-gray-100"
                      title="Download"
                    >
                      <Download className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => handleDelete(doc.id)}
                      className="p-1.5 text-gray-400 hover:text-red-500 rounded-lg hover:bg-red-50"
                      title="Delete"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </li>
              )
            })}
          </ul>
        </div>
      )}
    </div>
  )
}
