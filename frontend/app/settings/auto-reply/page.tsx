'use client';

import { useState, useEffect } from 'react';

const API_URL = typeof window !== 'undefined' && window.location.hostname === 'localhost' 
  ? 'http://localhost:8001' 
  : '';

interface AutoReplySettings {
  id: number;
  whatsapp_enabled: boolean;
  whatsapp_mode: string;
  whatsapp_delay_seconds: number;
  email_enabled: boolean;
  email_mode: string;
  email_delay_seconds: number;
  sms_enabled: boolean;
  sms_mode: string;
  sms_delay_seconds: number;
  business_hours_only: boolean;
  business_hours_start: string;
  business_hours_end: string;
  max_auto_replies_per_lead: number;
  keywords_trigger_human: string[];
}

interface Template {
  id: number;
  name: string;
}

export default function AutoReplySettingsPage() {
  const [settings, setSettings] = useState<AutoReplySettings | null>(null);
  const [templates, setTemplates] = useState<Template[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [newKeyword, setNewKeyword] = useState('');

  useEffect(() => {
    loadData();
  }, []);

  async function loadData() {
    setLoading(true);
    try {
      // Load settings
      const settingsRes = await fetch(`${API_URL}/api/admin/auto-reply/settings`);
      if (settingsRes.ok) {
        const data = await settingsRes.json();
        setSettings(data);
      }

      // Load templates
      const templatesRes = await fetch(`${API_URL}/api/templates/`);
      if (templatesRes.ok) {
        const data = await templatesRes.json();
        setTemplates(data);
      }
    } catch (error) {
      console.error('Error loading settings:', error);
    }
    setLoading(false);
  }

  async function saveSettings() {
    if (!settings) return;
    
    setSaving(true);
    try {
      const response = await fetch(`${API_URL}/api/admin/auto-reply/settings`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(settings)
      });
      
      if (response.ok) {
        alert('ההגדרות נשמרו בהצלחה!');
      } else {
        alert('שגיאה בשמירת ההגדרות');
      }
    } catch (error) {
      console.error('Error saving:', error);
      alert('שגיאה בשמירה');
    }
    setSaving(false);
  }

  function updateSettings(field: string, value: any) {
    if (!settings) return;
    setSettings({ ...settings, [field]: value });
  }

  function addKeyword() {
    if (!newKeyword.trim() || !settings) return;
    const keywords = [...(settings.keywords_trigger_human || []), newKeyword.trim()];
    setSettings({ ...settings, keywords_trigger_human: keywords });
    setNewKeyword('');
  }

  function removeKeyword(index: number) {
    if (!settings) return;
    const keywords = settings.keywords_trigger_human.filter((_, i) => i !== index);
    setSettings({ ...settings, keywords_trigger_human: keywords });
  }

  if (loading) {
    return (
      <div className="p-6 max-w-4xl mx-auto" dir="rtl">
        <div className="text-center py-12">
          <div className="animate-spin h-8 w-8 border-4 border-blue-500 border-t-transparent rounded-full mx-auto mb-4"></div>
          <p>טוען הגדרות...</p>
        </div>
      </div>
    );
  }

  if (!settings) {
    return (
      <div className="p-6 max-w-4xl mx-auto" dir="rtl">
        <div className="text-center py-12 text-red-500">
          שגיאה בטעינת ההגדרות
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-4xl mx-auto" dir="rtl">
      <h1 className="text-3xl font-bold mb-6">🤖 הגדרות מענה אוטומטי</h1>

      {/* Email Settings */}
      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <h2 className="text-xl font-bold mb-4 flex items-center gap-2">
          📧 מענה אוטומטי למייל
        </h2>

        <div className="space-y-4">
          {/* Enable/Disable */}
          <div className="flex items-center gap-4">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={settings.email_enabled}
                onChange={(e) => updateSettings('email_enabled', e.target.checked)}
                className="w-5 h-5 rounded"
              />
              <span className="font-medium">מופעל</span>
            </label>
          </div>

          {/* Mode Selection */}
          <div className="p-4 bg-gray-50 rounded-lg">
            <label className="block text-sm font-medium mb-3">מצב מענה:</label>
            <div className="space-y-2">
              {[
                { id: 'off', label: 'כבוי', desc: 'מענה ידני בלבד' },
                { id: 'suggest', label: 'הצעה + אישור', desc: 'AI מציע תשובה, אני מאשר לפני שליחה' },
                { id: 'auto', label: 'אוטומטי מלא', desc: 'AI עונה מיד בלי להמתין לאישור' }
              ].map(mode => (
                <label key={mode.id} className="flex items-start gap-3 p-3 bg-white rounded-lg border cursor-pointer hover:border-blue-300">
                  <input
                    type="radio"
                    name="email_mode"
                    value={mode.id}
                    checked={settings.email_mode === mode.id}
                    onChange={(e) => updateSettings('email_mode', e.target.value)}
                    className="mt-1"
                  />
                  <div>
                    <span className="font-medium">{mode.label}</span>
                    <p className="text-sm text-gray-500">{mode.desc}</p>
                  </div>
                </label>
              ))}
            </div>
          </div>

          {/* Delay */}
          {settings.email_mode === 'auto' && (
            <div>
              <label className="block text-sm font-medium mb-2">
                זמן המתנה לפני שליחה אוטומטית:
              </label>
              <select
                value={settings.email_delay_seconds}
                onChange={(e) => updateSettings('email_delay_seconds', parseInt(e.target.value))}
                className="p-2 border rounded-lg"
              >
                <option value={0}>מיידי</option>
                <option value={30}>30 שניות</option>
                <option value={60}>דקה</option>
                <option value={120}>2 דקות</option>
                <option value={300}>5 דקות</option>
              </select>
            </div>
          )}
        </div>
      </div>

      {/* Business Hours */}
      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <h2 className="text-xl font-bold mb-4 flex items-center gap-2">
          ⏰ שעות פעילות
        </h2>

        <div className="space-y-4">
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={settings.business_hours_only}
              onChange={(e) => updateSettings('business_hours_only', e.target.checked)}
              className="w-5 h-5 rounded"
            />
            <span>ענה רק בשעות עבודה</span>
          </label>

          {settings.business_hours_only && (
            <div className="flex items-center gap-4 p-4 bg-gray-50 rounded-lg">
              <div>
                <label className="block text-sm text-gray-500 mb-1">מ:</label>
                <input
                  type="time"
                  value={settings.business_hours_start}
                  onChange={(e) => updateSettings('business_hours_start', e.target.value)}
                  className="p-2 border rounded-lg"
                />
              </div>
              <div>
                <label className="block text-sm text-gray-500 mb-1">עד:</label>
                <input
                  type="time"
                  value={settings.business_hours_end}
                  onChange={(e) => updateSettings('business_hours_end', e.target.value)}
                  className="p-2 border rounded-lg"
                />
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Limits */}
      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <h2 className="text-xl font-bold mb-4 flex items-center gap-2">
          🚫 הגבלות
        </h2>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-2">
              מקסימום תשובות אוטומטיות לליד:
            </label>
            <input
              type="number"
              min={1}
              max={10}
              value={settings.max_auto_replies_per_lead}
              onChange={(e) => updateSettings('max_auto_replies_per_lead', parseInt(e.target.value))}
              className="w-24 p-2 border rounded-lg"
            />
            <p className="text-sm text-gray-500 mt-1">
              אחרי מספר זה - יעבור לטיפול ידני
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium mb-2">
              מילים שמעבירות לטיפול ידני:
            </label>
            <p className="text-sm text-gray-500 mb-2">
              הודעות שמכילות מילים אלה יעברו לטיפול אנושי במקום תשובה אוטומטית
            </p>
            
            <div className="flex flex-wrap gap-2 mb-3">
              {(settings.keywords_trigger_human || []).map((keyword, index) => (
                <span
                  key={index}
                  className="px-3 py-1 bg-red-100 text-red-800 rounded-full text-sm flex items-center gap-1"
                >
                  {keyword}
                  <button
                    onClick={() => removeKeyword(index)}
                    className="hover:text-red-600"
                  >
                    ×
                  </button>
                </span>
              ))}
            </div>

            <div className="flex gap-2">
              <input
                type="text"
                value={newKeyword}
                onChange={(e) => setNewKeyword(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && addKeyword()}
                placeholder="הוסף מילה..."
                className="p-2 border rounded-lg flex-1"
              />
              <button
                onClick={addKeyword}
                className="px-4 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg"
              >
                + הוסף
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* WhatsApp Settings (simplified) */}
      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <h2 className="text-xl font-bold mb-4 flex items-center gap-2">
          💬 WhatsApp
        </h2>

        <div className="flex items-center gap-4">
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={settings.whatsapp_enabled}
              onChange={(e) => updateSettings('whatsapp_enabled', e.target.checked)}
              className="w-5 h-5 rounded"
            />
            <span className="font-medium">מופעל</span>
          </label>

          <select
            value={settings.whatsapp_mode}
            onChange={(e) => updateSettings('whatsapp_mode', e.target.value)}
            className="p-2 border rounded-lg"
            disabled={!settings.whatsapp_enabled}
          >
            <option value="off">כבוי</option>
            <option value="suggest">הצעה + אישור</option>
            <option value="auto">אוטומטי</option>
          </select>
        </div>
      </div>

      {/* Save Button */}
      <div className="flex justify-end">
        <button
          onClick={saveSettings}
          disabled={saving}
          className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 flex items-center gap-2"
        >
          {saving ? (
            <>
              <div className="animate-spin h-5 w-5 border-2 border-white border-t-transparent rounded-full" />
              שומר...
            </>
          ) : (
            '💾 שמור הגדרות'
          )}
        </button>
      </div>
    </div>
  );
}
