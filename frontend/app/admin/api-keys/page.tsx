'use client'

import { useState, useEffect } from 'react'
import { Key, Eye, EyeOff, Check, X, RefreshCw, Edit, Plus } from 'lucide-react'

interface APIKey {
  id: number
  service_name: string
  display_name: string
  is_active: boolean
  last_verified: string
  last_error: string
  usage_stats: Record<string, any>
  credentials_masked: Record<string, string>
}

const serviceIcons: Record<string, string> = {
  whatsapp: '💬',
  sendgrid: '📧',
  twilio: '📱',
  apify: '🔍',
  proxy: '🌐',
  ollama: '🤖'
}

export default function APIKeysPage() {
  const [apiKeys, setApiKeys] = useState<APIKey[]>([])
  const [loading, setLoading] = useState(true)
  const [showModal, setShowModal] = useState(false)
  const [editingKey, setEditingKey] = useState<APIKey | null>(null)
  const [verifying, setVerifying] = useState<string | null>(null)

  useEffect(() => {
    fetchAPIKeys()
  }, [])

  const fetchAPIKeys = async () => {
    try {
      const response = await fetch('/api/admin/api-keys')
      if (response.ok) {
        const data = await response.json()
        setApiKeys(data)
      }
    } catch (error) {
      console.error('Failed to fetch API keys:', error)
    } finally {
      setLoading(false)
    }
  }

  const verifyConnection = async (serviceName: string) => {
    setVerifying(serviceName)
    try {
      await fetch(`/api/admin/api-keys/${serviceName}/verify`, { method: 'POST' })
      fetchAPIKeys()
    } catch (error) {
      console.error('Failed to verify:', error)
    } finally {
      setVerifying(null)
    }
  }

  return (
    <div className="space-y-6">
      {/* כותרת */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
          <Key className="w-7 h-7" />
          ניהול API Keys
        </h1>
        <button 
          onClick={() => { setEditingKey(null); setShowModal(true) }}
          className="btn btn-primary flex items-center gap-2"
        >
          <Plus className="w-5 h-5" />
          הוסף שירות
        </button>
      </div>

      {/* רשימת שירותים */}
      <div className="grid gap-4">
        {loading ? (
          Array(4).fill(0).map((_, i) => (
            <div key={i} className="card h-24 animate-pulse bg-gray-100"></div>
          ))
        ) : apiKeys.length === 0 ? (
          <div className="card text-center py-12">
            <Key className="w-16 h-16 mx-auto mb-4 text-gray-300" />
            <p className="text-gray-500 mb-4">לא הוגדרו API Keys</p>
            <button onClick={() => setShowModal(true)} className="btn btn-primary">
              הוסף שירות ראשון
            </button>
          </div>
        ) : (
          apiKeys.map((key) => (
            <div key={key.service_name} className="card">
              <div className="flex items-start justify-between">
                <div className="flex items-start gap-4">
                  <div className="text-3xl">{serviceIcons[key.service_name] || '🔑'}</div>
                  <div>
                    <h3 className="font-semibold text-lg">{key.display_name}</h3>
                    <p className="text-sm text-gray-500">{key.service_name}</p>
                    
                    {/* Credentials מוסתרים */}
                    <div className="mt-2 space-y-1">
                      {Object.entries(key.credentials_masked).map(([field, value]) => (
                        <div key={field} className="text-sm text-gray-600">
                          <span className="font-medium">{field}:</span>{' '}
                          <span className="font-mono">{value}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  {/* סטטוס */}
                  <div className="text-center">
                    {key.is_active ? (
                      <span className="badge badge-success flex items-center gap-1">
                        <Check className="w-3 h-3" />
                        פעיל
                      </span>
                    ) : (
                      <span className="badge badge-danger flex items-center gap-1">
                        <X className="w-3 h-3" />
                        לא פעיל
                      </span>
                    )}
                    {key.last_verified && (
                      <p className="text-xs text-gray-400 mt-1">
                        נבדק: {new Date(key.last_verified).toLocaleDateString('he-IL')}
                      </p>
                    )}
                  </div>

                  {/* פעולות */}
                  <div className="flex gap-2">
                    <button
                      onClick={() => verifyConnection(key.service_name)}
                      disabled={verifying === key.service_name}
                      className="btn btn-secondary"
                      title="בדיקת חיבור"
                    >
                      <RefreshCw className={`w-4 h-4 ${verifying === key.service_name ? 'animate-spin' : ''}`} />
                    </button>
                    <button
                      onClick={() => { setEditingKey(key); setShowModal(true) }}
                      className="btn btn-secondary"
                      title="עריכה"
                    >
                      <Edit className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              </div>

              {/* שגיאה אחרונה */}
              {key.last_error && (
                <div className="mt-3 p-2 bg-danger-50 rounded text-sm text-danger-600">
                  ⚠️ {key.last_error}
                </div>
              )}

              {/* סטטיסטיקות */}
              {key.usage_stats && Object.keys(key.usage_stats).length > 0 && (
                <div className="mt-3 pt-3 border-t border-gray-100">
                  <div className="flex gap-4 text-sm text-gray-600">
                    {Object.entries(key.usage_stats).map(([k, v]) => (
                      <span key={k}>
                        <span className="font-medium">{k}:</span> {String(v)}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ))
        )}
      </div>

      {/* Modal */}
      {showModal && (
        <APIKeyModal 
          apiKey={editingKey}
          onClose={() => setShowModal(false)}
          onSaved={fetchAPIKeys}
        />
      )}
    </div>
  )
}

function APIKeyModal({ 
  apiKey, 
  onClose, 
  onSaved 
}: { 
  apiKey: APIKey | null
  onClose: () => void
  onSaved: () => void 
}) {
  const [serviceName, setServiceName] = useState(apiKey?.service_name || '')
  const [displayName, setDisplayName] = useState(apiKey?.display_name || '')
  const [credentials, setCredentials] = useState<Record<string, string>>({})
  const [submitting, setSubmitting] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSubmitting(true)

    try {
      const url = apiKey 
        ? `/api/admin/api-keys/${apiKey.service_name}` 
        : '/api/admin/api-keys'
      const method = apiKey ? 'PUT' : 'POST'

      const response = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          service_name: serviceName,
          display_name: displayName,
          credentials
        })
      })

      if (response.ok) {
        onSaved()
        onClose()
      }
    } catch (error) {
      console.error('Failed to save API key:', error)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg w-full max-w-md p-6">
        <h2 className="text-xl font-bold mb-4">
          {apiKey ? 'עריכת API Key' : 'הוספת שירות חדש'}
        </h2>
        
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="label">שם השירות</label>
            <select
              className="input"
              value={serviceName}
              onChange={(e) => setServiceName(e.target.value)}
              disabled={!!apiKey}
              required
            >
              <option value="">בחר שירות...</option>
              <option value="whatsapp">WhatsApp (Green-API)</option>
              <option value="sendgrid">Email (SendGrid)</option>
              <option value="twilio">SMS (Twilio)</option>
              <option value="apify">Apify</option>
              <option value="proxy">Proxy Service</option>
              <option value="ollama">Ollama (Local AI)</option>
            </select>
          </div>

          <div>
            <label className="label">שם תצוגה</label>
            <input
              type="text"
              className="input"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              placeholder="למשל: WhatsApp (Green-API)"
              required
            />
          </div>

          <div>
            <label className="label">API Key / Token</label>
            <input
              type="password"
              className="input"
              value={credentials.api_key || credentials.token || ''}
              onChange={(e) => setCredentials({ ...credentials, api_key: e.target.value, token: e.target.value })}
              placeholder="הזן API Key..."
            />
          </div>

          {serviceName === 'whatsapp' && (
            <div>
              <label className="label">Instance ID</label>
              <input
                type="text"
                className="input"
                value={credentials.instance_id || ''}
                onChange={(e) => setCredentials({ ...credentials, instance_id: e.target.value })}
              />
            </div>
          )}

          <div className="flex gap-2 pt-4">
            <button type="button" onClick={onClose} className="btn btn-secondary flex-1">
              ביטול
            </button>
            <button type="submit" disabled={submitting} className="btn btn-primary flex-1">
              {submitting ? 'שומר...' : 'שמור'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
