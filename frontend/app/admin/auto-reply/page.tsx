'use client'

import { useState, useEffect } from 'react'
import { Bot, Save, RefreshCw, MessageSquare, Mail, Phone } from 'lucide-react'

interface AutoReplySettings {
  whatsapp_enabled: boolean
  whatsapp_mode: 'off' | 'suggest' | 'auto'
  whatsapp_delay_seconds: number
  email_enabled: boolean
  email_mode: 'off' | 'suggest' | 'auto'
  email_delay_seconds: number
  sms_enabled: boolean
  sms_mode: 'off' | 'suggest' | 'auto'
  sms_delay_seconds: number
  business_hours_only: boolean
  business_hours_start: string
  business_hours_end: string
  max_auto_replies_per_lead: number
  keywords_trigger_human: string[]
}

const modeLabels = {
  off: 'כבוי',
  suggest: 'הצעות בלבד',
  auto: 'אוטומטי מלא'
}

export default function AutoReplyPage() {
  const [settings, setSettings] = useState<AutoReplySettings>({
    whatsapp_enabled: true,
    whatsapp_mode: 'suggest',
    whatsapp_delay_seconds: 30,
    email_enabled: true,
    email_mode: 'suggest',
    email_delay_seconds: 60,
    sms_enabled: false,
    sms_mode: 'off',
    sms_delay_seconds: 60,
    business_hours_only: true,
    business_hours_start: '09:00',
    business_hours_end: '18:00',
    max_auto_replies_per_lead: 3,
    keywords_trigger_human: ['אנושי', 'נציג', 'טלפון', 'דחוף']
  })
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    fetchSettings()
  }, [])

  const fetchSettings = async () => {
    try {
      const response = await fetch('/api/admin/auto-reply/settings')
      if (response.ok) {
        const data = await response.json()
        setSettings(data)
      }
    } catch (error) {
      console.error('Failed to fetch settings:', error)
    } finally {
      setLoading(false)
    }
  }

  const saveSettings = async () => {
    setSaving(true)
    try {
      await fetch('/api/admin/auto-reply/settings', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(settings)
      })
      alert('ההגדרות נשמרו בהצלחה!')
    } catch (error) {
      console.error('Failed to save settings:', error)
      alert('שגיאה בשמירת ההגדרות')
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return <div className="p-8 text-center">טוען...</div>
  }

  return (
    <div className="space-y-6">
      {/* כותרת */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
          <Bot className="w-7 h-7" />
          הגדרות Auto-Reply
        </h1>
        <button 
          onClick={saveSettings}
          disabled={saving}
          className="btn btn-primary flex items-center gap-2"
        >
          {saving ? <RefreshCw className="w-5 h-5 animate-spin" /> : <Save className="w-5 h-5" />}
          {saving ? 'שומר...' : 'שמור הגדרות'}
        </button>
      </div>

      {/* ערוצים */}
      <div className="grid lg:grid-cols-3 gap-6">
        {/* WhatsApp */}
        <div className="card">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center">
              <MessageSquare className="w-6 h-6 text-green-600" />
            </div>
            <div>
              <h3 className="font-semibold">WhatsApp</h3>
              <span className={`text-xs ${settings.whatsapp_enabled ? 'text-green-600' : 'text-gray-400'}`}>
                {settings.whatsapp_enabled ? 'פעיל' : 'כבוי'}
              </span>
            </div>
            <label className="mr-auto flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={settings.whatsapp_enabled}
                onChange={(e) => setSettings({ ...settings, whatsapp_enabled: e.target.checked })}
                className="sr-only"
              />
              <div className={`w-11 h-6 rounded-full transition-colors ${settings.whatsapp_enabled ? 'bg-green-600' : 'bg-gray-300'}`}>
                <div className={`w-4 h-4 bg-white rounded-full mt-1 transition-transform ${settings.whatsapp_enabled ? 'mr-1' : 'mr-6'}`} />
              </div>
            </label>
          </div>

          <div className="space-y-3">
            <div>
              <label className="label">מצב</label>
              <select
                className="input"
                value={settings.whatsapp_mode}
                onChange={(e) => setSettings({ ...settings, whatsapp_mode: e.target.value as any })}
                disabled={!settings.whatsapp_enabled}
              >
                <option value="off">כבוי</option>
                <option value="suggest">הצעות בלבד</option>
                <option value="auto">אוטומטי מלא</option>
              </select>
            </div>
            <div>
              <label className="label">השהייה (שניות)</label>
              <input
                type="number"
                className="input"
                value={settings.whatsapp_delay_seconds}
                onChange={(e) => setSettings({ ...settings, whatsapp_delay_seconds: parseInt(e.target.value) })}
                disabled={!settings.whatsapp_enabled}
              />
            </div>
          </div>
        </div>

        {/* Email */}
        <div className="card">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
              <Mail className="w-6 h-6 text-blue-600" />
            </div>
            <div>
              <h3 className="font-semibold">Email</h3>
              <span className={`text-xs ${settings.email_enabled ? 'text-green-600' : 'text-gray-400'}`}>
                {settings.email_enabled ? 'פעיל' : 'כבוי'}
              </span>
            </div>
            <label className="mr-auto flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={settings.email_enabled}
                onChange={(e) => setSettings({ ...settings, email_enabled: e.target.checked })}
                className="sr-only"
              />
              <div className={`w-11 h-6 rounded-full transition-colors ${settings.email_enabled ? 'bg-green-600' : 'bg-gray-300'}`}>
                <div className={`w-4 h-4 bg-white rounded-full mt-1 transition-transform ${settings.email_enabled ? 'mr-1' : 'mr-6'}`} />
              </div>
            </label>
          </div>

          <div className="space-y-3">
            <div>
              <label className="label">מצב</label>
              <select
                className="input"
                value={settings.email_mode}
                onChange={(e) => setSettings({ ...settings, email_mode: e.target.value as any })}
                disabled={!settings.email_enabled}
              >
                <option value="off">כבוי</option>
                <option value="suggest">הצעות בלבד</option>
                <option value="auto">אוטומטי מלא</option>
              </select>
            </div>
            <div>
              <label className="label">השהייה (שניות)</label>
              <input
                type="number"
                className="input"
                value={settings.email_delay_seconds}
                onChange={(e) => setSettings({ ...settings, email_delay_seconds: parseInt(e.target.value) })}
                disabled={!settings.email_enabled}
              />
            </div>
          </div>
        </div>

        {/* SMS */}
        <div className="card">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center">
              <Phone className="w-6 h-6 text-purple-600" />
            </div>
            <div>
              <h3 className="font-semibold">SMS</h3>
              <span className={`text-xs ${settings.sms_enabled ? 'text-green-600' : 'text-gray-400'}`}>
                {settings.sms_enabled ? 'פעיל' : 'כבוי'}
              </span>
            </div>
            <label className="mr-auto flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={settings.sms_enabled}
                onChange={(e) => setSettings({ ...settings, sms_enabled: e.target.checked })}
                className="sr-only"
              />
              <div className={`w-11 h-6 rounded-full transition-colors ${settings.sms_enabled ? 'bg-green-600' : 'bg-gray-300'}`}>
                <div className={`w-4 h-4 bg-white rounded-full mt-1 transition-transform ${settings.sms_enabled ? 'mr-1' : 'mr-6'}`} />
              </div>
            </label>
          </div>

          <div className="space-y-3">
            <div>
              <label className="label">מצב</label>
              <select
                className="input"
                value={settings.sms_mode}
                onChange={(e) => setSettings({ ...settings, sms_mode: e.target.value as any })}
                disabled={!settings.sms_enabled}
              >
                <option value="off">כבוי</option>
                <option value="suggest">הצעות בלבד</option>
                <option value="auto">אוטומטי מלא</option>
              </select>
            </div>
            <div>
              <label className="label">השהייה (שניות)</label>
              <input
                type="number"
                className="input"
                value={settings.sms_delay_seconds}
                onChange={(e) => setSettings({ ...settings, sms_delay_seconds: parseInt(e.target.value) })}
                disabled={!settings.sms_enabled}
              />
            </div>
          </div>
        </div>
      </div>

      {/* הגדרות כלליות */}
      <div className="card">
        <h3 className="font-semibold mb-4">הגדרות כלליות</h3>
        
        <div className="grid md:grid-cols-2 gap-6">
          {/* שעות פעילות */}
          <div>
            <div className="flex items-center gap-2 mb-3">
              <input
                type="checkbox"
                id="business_hours"
                checked={settings.business_hours_only}
                onChange={(e) => setSettings({ ...settings, business_hours_only: e.target.checked })}
                className="w-4 h-4"
              />
              <label htmlFor="business_hours" className="font-medium">הפעל רק בשעות פעילות</label>
            </div>
            
            {settings.business_hours_only && (
              <div className="flex gap-4">
                <div className="flex-1">
                  <label className="label">משעה</label>
                  <input
                    type="time"
                    className="input"
                    value={settings.business_hours_start}
                    onChange={(e) => setSettings({ ...settings, business_hours_start: e.target.value })}
                  />
                </div>
                <div className="flex-1">
                  <label className="label">עד שעה</label>
                  <input
                    type="time"
                    className="input"
                    value={settings.business_hours_end}
                    onChange={(e) => setSettings({ ...settings, business_hours_end: e.target.value })}
                  />
                </div>
              </div>
            )}
          </div>

          {/* הגבלות */}
          <div>
            <label className="label">מקסימום תגובות אוטומטיות לליד</label>
            <input
              type="number"
              className="input w-32"
              value={settings.max_auto_replies_per_lead}
              onChange={(e) => setSettings({ ...settings, max_auto_replies_per_lead: parseInt(e.target.value) })}
              min={1}
              max={10}
            />
            <p className="text-xs text-gray-500 mt-1">
              אחרי מספר זה התגובות יעברו לאישור ידני
            </p>
          </div>

          {/* מילות מפתח להעברה לנציג */}
          <div className="md:col-span-2">
            <label className="label">מילות מפתח להעברה לנציג אנושי</label>
            <input
              type="text"
              className="input"
              value={settings.keywords_trigger_human.join(', ')}
              onChange={(e) => setSettings({ 
                ...settings, 
                keywords_trigger_human: e.target.value.split(',').map(k => k.trim()).filter(Boolean) 
              })}
              placeholder="אנושי, נציג, טלפון, דחוף"
            />
            <p className="text-xs text-gray-500 mt-1">
              אם הודעה נכנסת מכילה אחת מהמילים האלה, היא תועבר לטיפול ידני
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
