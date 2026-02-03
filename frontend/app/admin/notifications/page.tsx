'use client'

import { useState, useEffect } from 'react'
import { Bell, Phone, Plus, Trash2, Send, CheckCircle, XCircle, RefreshCw } from 'lucide-react'

interface NotificationPhone {
  id: number
  phone: string
  name: string | null
  is_active: boolean
  created_at: string
}

interface NotificationLog {
  id: number
  phone: string
  message: string
  status: string
  error: string | null
  related_email_id: number | null
  created_at: string
}

export default function NotificationsPage() {
  const [phones, setPhones] = useState<NotificationPhone[]>([])
  const [logs, setLogs] = useState<NotificationLog[]>([])
  const [loading, setLoading] = useState(true)
  const [newPhone, setNewPhone] = useState('')
  const [newName, setNewName] = useState('')
  const [testing, setTesting] = useState(false)
  const [message, setMessage] = useState<{type: 'success' | 'error', text: string} | null>(null)

  useEffect(() => {
    fetchData()
  }, [])

  const fetchData = async () => {
    try {
      const [phonesRes, logsRes] = await Promise.all([
        fetch('/api/notifications/phones'),
        fetch('/api/notifications/logs?limit=20')
      ])
      
      if (phonesRes.ok) setPhones(await phonesRes.json())
      if (logsRes.ok) setLogs(await logsRes.json())
    } catch (error) {
      console.error('Failed to fetch:', error)
    } finally {
      setLoading(false)
    }
  }

  const addPhone = async () => {
    if (!newPhone) return
    
    try {
      const res = await fetch('/api/notifications/phones', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ phone: newPhone, name: newName || null })
      })
      
      if (res.ok) {
        setNewPhone('')
        setNewName('')
        fetchData()
        setMessage({ type: 'success', text: 'מספר נוסף בהצלחה!' })
      } else {
        const error = await res.json()
        setMessage({ type: 'error', text: error.detail || 'שגיאה בהוספה' })
      }
    } catch (error) {
      setMessage({ type: 'error', text: 'שגיאה בהוספה' })
    }
    
    setTimeout(() => setMessage(null), 3000)
  }

  const deletePhone = async (id: number) => {
    if (!confirm('למחוק את המספר?')) return
    
    try {
      await fetch(`/api/notifications/phones/${id}`, { method: 'DELETE' })
      fetchData()
    } catch (error) {
      console.error('Failed to delete:', error)
    }
  }

  const togglePhone = async (id: number) => {
    try {
      await fetch(`/api/notifications/phones/${id}/toggle`, { method: 'PATCH' })
      fetchData()
    } catch (error) {
      console.error('Failed to toggle:', error)
    }
  }

  const testNotifications = async () => {
    setTesting(true)
    try {
      const res = await fetch('/api/notifications/test', { method: 'POST' })
      if (res.ok) {
        const data = await res.json()
        setMessage({ type: 'success', text: `נשלחו ${data.results.length} התראות!` })
        fetchData()
      } else {
        const error = await res.json()
        setMessage({ type: 'error', text: error.detail || 'שגיאה בשליחה' })
      }
    } catch (error) {
      setMessage({ type: 'error', text: 'שגיאה בשליחה' })
    } finally {
      setTesting(false)
      setTimeout(() => setMessage(null), 3000)
    }
  }

  const formatDate = (date: string) => {
    return new Date(date).toLocaleString('he-IL', {
      day: '2-digit',
      month: '2-digit',
      year: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="w-8 h-8 animate-spin text-primary" />
      </div>
    )
  }

  return (
    <div className="space-y-6 p-6" dir="rtl">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Bell className="w-8 h-8 text-green-500" />
          <h1 className="text-2xl font-bold">ניהול התראות WhatsApp</h1>
        </div>
        
        <button
          onClick={testNotifications}
          disabled={testing || phones.length === 0}
          className="flex items-center gap-2 px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600 disabled:opacity-50"
        >
          {testing ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
          שלח בדיקה
        </button>
      </div>

      {/* Message */}
      {message && (
        <div className={`p-4 rounded-lg ${message.type === 'success' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
          {message.text}
        </div>
      )}

      {/* Add Phone Form */}
      <div className="card p-4">
        <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <Plus className="w-5 h-5" />
          הוספת מספר חדש
        </h2>
        <div className="flex gap-4">
          <input
            type="text"
            placeholder="מספר טלפון (למשל: 0542575411)"
            value={newPhone}
            onChange={(e) => setNewPhone(e.target.value)}
            className="flex-1 px-4 py-2 border rounded-lg"
          />
          <input
            type="text"
            placeholder="שם (אופציונלי)"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            className="w-48 px-4 py-2 border rounded-lg"
          />
          <button
            onClick={addPhone}
            disabled={!newPhone}
            className="px-6 py-2 bg-primary text-white rounded-lg hover:bg-primary-dark disabled:opacity-50"
          >
            הוסף
          </button>
        </div>
      </div>

      {/* Phones List */}
      <div className="card p-4">
        <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <Phone className="w-5 h-5" />
          מספרים להתראות ({phones.length})
        </h2>
        
        {phones.length === 0 ? (
          <p className="text-gray-500 text-center py-8">אין מספרים מוגדרים</p>
        ) : (
          <div className="space-y-2">
            {phones.map(phone => (
              <div 
                key={phone.id}
                className={`flex items-center justify-between p-3 rounded-lg border ${phone.is_active ? 'bg-white' : 'bg-gray-100'}`}
              >
                <div className="flex items-center gap-4">
                  <button
                    onClick={() => togglePhone(phone.id)}
                    className={`w-10 h-6 rounded-full transition-colors ${phone.is_active ? 'bg-green-500' : 'bg-gray-300'}`}
                  >
                    <div className={`w-5 h-5 bg-white rounded-full shadow transition-transform ${phone.is_active ? 'translate-x-4' : 'translate-x-1'}`} />
                  </button>
                  <span className="font-mono text-lg">{phone.phone}</span>
                  {phone.name && <span className="text-gray-500">({phone.name})</span>}
                </div>
                <button
                  onClick={() => deletePhone(phone.id)}
                  className="p-2 text-red-500 hover:bg-red-50 rounded"
                >
                  <Trash2 className="w-5 h-5" />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Logs */}
      <div className="card p-4">
        <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <RefreshCw className="w-5 h-5" />
          לוג התראות אחרונות
        </h2>
        
        {logs.length === 0 ? (
          <p className="text-gray-500 text-center py-8">אין התראות</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="text-right border-b">
                  <th className="p-2">סטטוס</th>
                  <th className="p-2">מספר</th>
                  <th className="p-2">הודעה</th>
                  <th className="p-2">תאריך</th>
                </tr>
              </thead>
              <tbody>
                {logs.map(log => (
                  <tr key={log.id} className="border-b hover:bg-gray-50">
                    <td className="p-2">
                      {log.status === 'sent' ? (
                        <CheckCircle className="w-5 h-5 text-green-500" />
                      ) : (
                        <XCircle className="w-5 h-5 text-red-500" />
                      )}
                    </td>
                    <td className="p-2 font-mono">{log.phone}</td>
                    <td className="p-2 text-sm text-gray-600 max-w-md truncate">{log.message}</td>
                    <td className="p-2 text-sm">{formatDate(log.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
