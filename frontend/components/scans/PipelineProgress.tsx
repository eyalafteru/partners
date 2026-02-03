'use client'

import { useState, useEffect } from 'react'
import { Play, Pause, RefreshCw, Loader2, CheckCircle, XCircle, Filter } from 'lucide-react'

interface PipelineStatus {
  is_running: boolean
  total: number
  completed: number
  progress_percent: number
  stages: {
    pending: number
    scraped: number
    classified: number
    whois_done: number
    lead_created: number
    filtered: number
    failed: number
  }
  leads_created: number
  filtered_out: number
  failed: number
}

interface PipelineProgressProps {
  scanId: number
  scanName: string
  onRefresh?: () => void
}

const STAGE_LABELS: Record<string, string> = {
  pending: 'ממתין',
  scraped: 'תוכן נסרק',
  classified: 'סווג',
  whois_done: 'WHOIS',
  lead_created: 'ליד נוצר',
  filtered: 'סונן',
  failed: 'נכשל'
}

const STAGE_COLORS: Record<string, string> = {
  pending: 'bg-gray-200',
  scraped: 'bg-blue-200',
  classified: 'bg-purple-200',
  whois_done: 'bg-indigo-200',
  lead_created: 'bg-green-200',
  filtered: 'bg-yellow-200',
  failed: 'bg-red-200'
}

export default function PipelineProgress({ scanId, scanName, onRefresh }: PipelineProgressProps) {
  const [status, setStatus] = useState<PipelineStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [actionLoading, setActionLoading] = useState(false)

  const fetchStatus = async () => {
    try {
      const response = await fetch(`/api/scans/${scanId}/pipeline/status`)
      if (response.ok) {
        const data = await response.json()
        setStatus(data)
      }
    } catch (error) {
      console.error('Failed to fetch pipeline status:', error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchStatus()
    // Refresh every 2 seconds while running
    const interval = setInterval(fetchStatus, 2000)
    return () => clearInterval(interval)
  }, [scanId])

  const startPipeline = async () => {
    setActionLoading(true)
    try {
      const response = await fetch(`/api/scans/${scanId}/pipeline/start`, {
        method: 'POST'
      })
      if (response.ok) {
        fetchStatus()
        onRefresh?.()
      }
    } catch (error) {
      console.error('Failed to start pipeline:', error)
    } finally {
      setActionLoading(false)
    }
  }

  const stopPipeline = async () => {
    setActionLoading(true)
    try {
      const response = await fetch(`/api/scans/${scanId}/pipeline/stop`, {
        method: 'POST'
      })
      if (response.ok) {
        fetchStatus()
      }
    } catch (error) {
      console.error('Failed to stop pipeline:', error)
    } finally {
      setActionLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center justify-center">
          <Loader2 className="w-6 h-6 animate-spin text-blue-500" />
          <span className="mr-2 text-gray-500">טוען...</span>
        </div>
      </div>
    )
  }

  if (!status) return null

  const progressWidth = `${status.progress_percent}%`

  return (
    <div className="bg-white rounded-lg shadow p-6 mb-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-lg font-semibold text-gray-900">{scanName}</h3>
          <p className="text-sm text-gray-500">
            {status.completed} / {status.total} URLs מעובדים
          </p>
        </div>
        <div className="flex gap-2">
          {status.is_running ? (
            <button
              onClick={stopPipeline}
              disabled={actionLoading}
              className="flex items-center gap-2 px-4 py-2 bg-red-100 text-red-700 rounded-lg hover:bg-red-200 transition-colors"
            >
              {actionLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Pause className="w-4 h-4" />}
              עצור
            </button>
          ) : (
            <button
              onClick={startPipeline}
              disabled={actionLoading || status.completed >= status.total}
              className="flex items-center gap-2 px-4 py-2 bg-green-100 text-green-700 rounded-lg hover:bg-green-200 transition-colors disabled:opacity-50"
            >
              {actionLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
              {status.completed >= status.total ? 'הושלם' : 'התחל Pipeline'}
            </button>
          )}
          <button
            onClick={fetchStatus}
            className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="mb-6">
        <div className="flex items-center justify-between text-sm text-gray-600 mb-1">
          <span>התקדמות</span>
          <span className="font-medium">{status.progress_percent}%</span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-4 overflow-hidden">
          <div
            className="h-full bg-gradient-to-l from-green-500 to-blue-500 transition-all duration-500 ease-out"
            style={{ width: progressWidth }}
          />
        </div>
        {status.is_running && (
          <div className="mt-1 flex items-center gap-2 text-sm text-blue-600">
            <Loader2 className="w-3 h-3 animate-spin" />
            <span>עובד...</span>
          </div>
        )}
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-3 md:grid-cols-6 gap-3">
        <div className="bg-gray-50 rounded-lg p-3 text-center">
          <div className="text-2xl font-bold text-gray-700">{status.total}</div>
          <div className="text-xs text-gray-500">סה"כ URLs</div>
        </div>
        <div className="bg-blue-50 rounded-lg p-3 text-center">
          <div className="text-2xl font-bold text-blue-700">{status.stages.scraped}</div>
          <div className="text-xs text-blue-600">נסרקו</div>
        </div>
        <div className="bg-purple-50 rounded-lg p-3 text-center">
          <div className="text-2xl font-bold text-purple-700">{status.stages.classified}</div>
          <div className="text-xs text-purple-600">סווגו</div>
        </div>
        <div className="bg-indigo-50 rounded-lg p-3 text-center">
          <div className="text-2xl font-bold text-indigo-700">{status.stages.whois_done}</div>
          <div className="text-xs text-indigo-600">WHOIS</div>
        </div>
        <div className="bg-green-50 rounded-lg p-3 text-center">
          <div className="text-2xl font-bold text-green-700">{status.leads_created}</div>
          <div className="text-xs text-green-600 flex items-center justify-center gap-1">
            <CheckCircle className="w-3 h-3" />
            לידים
          </div>
        </div>
        <div className="bg-yellow-50 rounded-lg p-3 text-center">
          <div className="text-2xl font-bold text-yellow-700">{status.filtered_out}</div>
          <div className="text-xs text-yellow-600 flex items-center justify-center gap-1">
            <Filter className="w-3 h-3" />
            סוננו
          </div>
        </div>
      </div>

      {/* Failed items */}
      {status.failed > 0 && (
        <div className="mt-3 bg-red-50 rounded-lg p-3 flex items-center gap-2">
          <XCircle className="w-5 h-5 text-red-500" />
          <span className="text-red-700">
            {status.failed} פריטים נכשלו
          </span>
        </div>
      )}
    </div>
  )
}
