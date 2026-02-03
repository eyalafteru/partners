'use client'

import { useState, useEffect } from 'react'
import { Loader2, ExternalLink, Mail, Phone, Building, User, AlertCircle, CheckCircle, XCircle, Filter, Ban } from 'lucide-react'

interface DomainItemV2 {
  id: number
  domain: string
  url: string
  title: string
  pipeline_stage: number
  pipeline_stage_label: string
  retry_count: number
  business_type: string | null
  business_type_reason: string | null
  whois_name: string | null
  whois_org: string | null
  whois_email: string | null
  whois_phone: string | null
  whois_private: boolean
  emails: string[]
  phones: string[]
  has_content: boolean
  content_preview: string
  is_blacklisted: boolean
  error_message: string | null
  created_at: string | null
  stage_updated_at: string | null
}

interface DomainsTableV2Props {
  scanId: number
  refreshTrigger?: number
}

const STAGE_COLORS: Record<number, string> = {
  0: 'bg-gray-100 text-gray-700',     // PENDING
  1: 'bg-blue-100 text-blue-700',     // SCRAPED
  2: 'bg-purple-100 text-purple-700', // CLASSIFIED
  3: 'bg-indigo-100 text-indigo-700', // WHOIS_DONE
  4: 'bg-green-100 text-green-700',   // LEAD_CREATED
  5: 'bg-yellow-100 text-yellow-700', // FILTERED
  6: 'bg-red-100 text-red-700',       // FAILED
}

const BUSINESS_TYPE_LABELS: Record<string, { label: string, color: string, icon: string }> = {
  'lead_site': { label: 'אתר לידים', color: 'text-green-600 bg-green-50', icon: '🎯' },
  'small_business': { label: 'עסק קטן', color: 'text-blue-600 bg-blue-50', icon: '💼' },
  'content_site': { label: 'תוכן/בלוג', color: 'text-gray-600 bg-gray-50', icon: '📰' },
  'corporation': { label: 'תאגיד', color: 'text-orange-600 bg-orange-50', icon: '🏢' },
  'bank': { label: 'בנק', color: 'text-red-600 bg-red-50', icon: '🏦' },
  'insurance': { label: 'ביטוח', color: 'text-red-600 bg-red-50', icon: '🛡️' },
  'fintech': { label: 'פינטק', color: 'text-purple-600 bg-purple-50', icon: '🚀' },
  'government': { label: 'ממשלתי', color: 'text-gray-600 bg-gray-50', icon: '🏛️' },
  'unknown': { label: 'לא ידוע', color: 'text-gray-400 bg-gray-50', icon: '❓' },
}

export default function DomainsTableV2({ scanId, refreshTrigger }: DomainsTableV2Props) {
  const [domains, setDomains] = useState<DomainItemV2[]>([])
  const [loading, setLoading] = useState(true)
  const [stageFilter, setStageFilter] = useState<number | null>(null)
  const [limit] = useState(100)
  const [offset, setOffset] = useState(0)

  const fetchDomains = async () => {
    setLoading(true)
    try {
      let url = `/api/scans/${scanId}/queue/v2?limit=${limit}&offset=${offset}`
      if (stageFilter !== null) {
        url += `&stage=${stageFilter}`
      }
      const response = await fetch(url)
      if (response.ok) {
        const data = await response.json()
        setDomains(data)
      }
    } catch (error) {
      console.error('Failed to fetch domains:', error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchDomains()
  }, [scanId, offset, stageFilter, refreshTrigger])

  // Auto-refresh every 5 seconds
  useEffect(() => {
    const interval = setInterval(fetchDomains, 5000)
    return () => clearInterval(interval)
  }, [scanId, offset, stageFilter])

  const blacklistDomain = async (id: number) => {
    try {
      await fetch(`/api/scans/domains/${id}/blacklist`, { method: 'POST' })
      fetchDomains()
    } catch (error) {
      console.error('Failed to blacklist:', error)
    }
  }

  const renderPipelineProgress = (stage: number) => {
    const stages = 5
    const completed = Math.min(stage, 4)
    
    return (
      <div className="flex items-center gap-1">
        {[0, 1, 2, 3, 4].map((s) => (
          <div
            key={s}
            className={`w-2 h-2 rounded-full transition-colors ${
              s < completed ? 'bg-green-500' :
              s === completed && stage < 4 ? 'bg-blue-500 animate-pulse' :
              stage === 4 ? 'bg-green-500' :
              stage === 5 ? 'bg-yellow-500' :
              stage === 6 ? 'bg-red-500' :
              'bg-gray-300'
            }`}
          />
        ))}
        <span className="text-xs text-gray-500 mr-1">
          {stage < 6 ? `${Math.min(stage + 1, 5)}/5` : '❌'}
        </span>
      </div>
    )
  }

  if (loading && domains.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow p-8 text-center">
        <Loader2 className="w-8 h-8 animate-spin text-blue-500 mx-auto" />
        <p className="text-gray-500 mt-2">טוען דומיינים...</p>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-lg shadow overflow-hidden">
      {/* Header with filters */}
      <div className="p-4 border-b bg-gray-50">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold text-gray-900">
            דומיינים ({domains.length})
          </h3>
          <div className="flex items-center gap-2">
            <select
              value={stageFilter ?? ''}
              onChange={(e) => setStageFilter(e.target.value ? Number(e.target.value) : null)}
              className="text-sm border rounded-lg px-3 py-1.5"
            >
              <option value="">כל השלבים</option>
              <option value="0">ממתין</option>
              <option value="1">תוכן נסרק</option>
              <option value="2">סווג</option>
              <option value="3">WHOIS נבדק</option>
              <option value="4">ליד נוצר</option>
              <option value="5">סונן</option>
              <option value="6">נכשל</option>
            </select>
          </div>
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-gray-600">
            <tr>
              <th className="px-4 py-3 text-right">דומיין</th>
              <th className="px-4 py-3 text-center">Progress</th>
              <th className="px-4 py-3 text-center">סטטוס</th>
              <th className="px-4 py-3 text-center">סוג עסק</th>
              <th className="px-4 py-3 text-right">WHOIS</th>
              <th className="px-4 py-3 text-right">פרטי קשר</th>
              <th className="px-4 py-3 text-center">פעולות</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {domains.map((item) => {
              const businessType = BUSINESS_TYPE_LABELS[item.business_type || 'unknown'] || BUSINESS_TYPE_LABELS['unknown']
              const bestEmail = item.whois_email || (item.emails?.length > 0 ? item.emails[0] : null)
              const bestPhone = item.whois_phone || (item.phones?.length > 0 ? item.phones[0] : null)
              
              return (
                <tr key={item.id} className={`hover:bg-gray-50 ${item.is_blacklisted ? 'bg-red-50/30' : ''}`}>
                  {/* Domain */}
                  <td className="px-4 py-3">
                    <div className="flex flex-col">
                      <a
                        href={item.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-blue-600 hover:underline font-medium flex items-center gap-1"
                      >
                        {item.domain}
                        <ExternalLink className="w-3 h-3" />
                      </a>
                      {item.title && (
                        <span className="text-xs text-gray-500 truncate max-w-xs">
                          {item.title}
                        </span>
                      )}
                    </div>
                  </td>

                  {/* Progress */}
                  <td className="px-4 py-3">
                    <div className="flex justify-center">
                      {renderPipelineProgress(item.pipeline_stage)}
                    </div>
                  </td>

                  {/* Status */}
                  <td className="px-4 py-3">
                    <div className="flex justify-center">
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${STAGE_COLORS[item.pipeline_stage] || STAGE_COLORS[0]}`}>
                        {item.pipeline_stage_label}
                      </span>
                    </div>
                  </td>

                  {/* Business Type */}
                  <td className="px-4 py-3">
                    <div className="flex justify-center">
                      {item.business_type ? (
                        <span className={`px-2 py-1 rounded-lg text-xs flex items-center gap-1 ${businessType.color}`}>
                          <span>{businessType.icon}</span>
                          {businessType.label}
                        </span>
                      ) : (
                        <span className="text-gray-400">-</span>
                      )}
                    </div>
                  </td>

                  {/* WHOIS */}
                  <td className="px-4 py-3">
                    <div className="flex flex-col text-xs">
                      {item.whois_org ? (
                        <div className="flex items-center gap-1 text-gray-700">
                          <Building className="w-3 h-3" />
                          <span className="truncate max-w-[150px]">{item.whois_org}</span>
                        </div>
                      ) : item.whois_name ? (
                        <div className="flex items-center gap-1 text-gray-700">
                          <User className="w-3 h-3" />
                          <span className="truncate max-w-[150px]">{item.whois_name}</span>
                        </div>
                      ) : item.whois_private ? (
                        <span className="text-gray-400">🔒 פרטי</span>
                      ) : (
                        <span className="text-gray-400">-</span>
                      )}
                    </div>
                  </td>

                  {/* Contact Info */}
                  <td className="px-4 py-3">
                    <div className="flex flex-col gap-1 text-xs">
                      {bestEmail && (
                        <div className="flex items-center gap-1 text-blue-600">
                          <Mail className="w-3 h-3" />
                          <span className="truncate max-w-[150px]">{bestEmail}</span>
                        </div>
                      )}
                      {bestPhone && (
                        <div className="flex items-center gap-1 text-green-600">
                          <Phone className="w-3 h-3" />
                          <span>{bestPhone}</span>
                        </div>
                      )}
                      {!bestEmail && !bestPhone && (
                        <span className="text-gray-400">-</span>
                      )}
                    </div>
                  </td>

                  {/* Actions */}
                  <td className="px-4 py-3">
                    <div className="flex justify-center">
                      {!item.is_blacklisted && item.pipeline_stage < 5 && (
                        <button
                          onClick={() => blacklistDomain(item.id)}
                          className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded transition-colors"
                          title="הוסף לרשימה שחורה"
                        >
                          <Ban className="w-4 h-4" />
                        </button>
                      )}
                      {item.is_blacklisted && (
                        <span className="text-red-500 text-xs">חסום</span>
                      )}
                    </div>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {domains.length >= limit && (
        <div className="p-4 border-t flex justify-center gap-2">
          <button
            onClick={() => setOffset(Math.max(0, offset - limit))}
            disabled={offset === 0}
            className="px-4 py-2 text-sm border rounded-lg disabled:opacity-50 hover:bg-gray-50"
          >
            הקודם
          </button>
          <span className="px-4 py-2 text-sm text-gray-600">
            עמוד {Math.floor(offset / limit) + 1}
          </span>
          <button
            onClick={() => setOffset(offset + limit)}
            className="px-4 py-2 text-sm border rounded-lg hover:bg-gray-50"
          >
            הבא
          </button>
        </div>
      )}
    </div>
  )
}
