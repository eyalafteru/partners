'use client'

import { useState, useEffect } from 'react'
import { User, Save, Eye, Play, AlertCircle, CheckCircle } from 'lucide-react'

interface EyalStory {
  id: number
  story_content: string
  forbidden_phrases: string | null
  ai_instructions: string | null
  created_at: string
  updated_at: string | null
}

// Default empty story for when API fails or returns nothing
const EMPTY_STORY: EyalStory = {
  id: 1,
  story_content: '',
  forbidden_phrases: '',
  ai_instructions: '',
  created_at: new Date().toISOString(),
  updated_at: null
}

export default function EyalStoryPage() {
  const [story, setStory] = useState<EyalStory | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [testing, setTesting] = useState(false)
  const [showPreview, setShowPreview] = useState(false)
  const [previewContent, setPreviewContent] = useState('')
  const [testResult, setTestResult] = useState('')
  const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null)

  useEffect(() => {
    fetchStory()
  }, [])

  const fetchStory = async () => {
    try {
      const response = await fetch('/api/eyal-story')
      if (response.ok) {
        const data = await response.json()
        setStory(data)
      } else {
        // If API fails, use empty story so user can still edit
        console.error('API returned error:', response.status)
        setStory(EMPTY_STORY)
        setMessage({ type: 'error', text: `שגיאה בטעינת הסיפור (${response.status}) - אפשר להתחיל לכתוב` })
      }
    } catch (error) {
      console.error('Failed to fetch story:', error)
      // Use empty story so user can still edit
      setStory(EMPTY_STORY)
      setMessage({ type: 'error', text: 'שגיאה בטעינת הסיפור - אפשר להתחיל לכתוב' })
    } finally {
      setLoading(false)
    }
  }

  const saveStory = async () => {
    if (!story) return
    setSaving(true)
    setMessage(null)

    try {
      const response = await fetch('/api/eyal-story', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          story_content: story.story_content,
          forbidden_phrases: story.forbidden_phrases,
          ai_instructions: story.ai_instructions
        })
      })

      if (response.ok) {
        const data = await response.json()
        setStory(data)
        setMessage({ type: 'success', text: 'הסיפור נשמר בהצלחה!' })
      } else {
        throw new Error('Failed to save')
      }
    } catch (error) {
      console.error('Failed to save story:', error)
      setMessage({ type: 'error', text: 'שגיאה בשמירת הסיפור' })
    } finally {
      setSaving(false)
    }
  }

  const loadPreview = async () => {
    try {
      const response = await fetch('/api/eyal-story/prompt')
      if (response.ok) {
        const data = await response.json()
        setPreviewContent(data.prompt)
        setShowPreview(true)
      }
    } catch (error) {
      console.error('Failed to load preview:', error)
    }
  }

  const testGeneration = async () => {
    setTesting(true)
    setTestResult('')

    try {
      const response = await fetch('/api/eyal-story/test-generation', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          group_name: 'בעלי עסקים קטנים',
          calculator_name: 'מחשבון החזר משכנתא'
        })
      })

      if (response.ok) {
        const data = await response.json()
        setTestResult(data.post_content || 'לא התקבלה תוצאה')
      } else {
        throw new Error('Test failed')
      }
    } catch (error) {
      console.error('Failed to test:', error)
      setTestResult('שגיאה ביצירת פוסט לדוגמה')
    } finally {
      setTesting(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-gray-500">טוען...</div>
      </div>
    )
  }

  return (
    <div className="h-full overflow-auto">
      <div className="max-w-5xl mx-auto p-6 space-y-6">
        {/* כותרת */}
        <div className="bg-white rounded-lg shadow-sm p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-full bg-primary-100 flex items-center justify-center">
                <User className="w-6 h-6 text-primary-600" />
              </div>
              <div>
                <h1 className="text-2xl font-bold">הסיפור של אייל עובדיה</h1>
                <p className="text-gray-500">ניהול הסיפור האישי לשימוש ביצירת פוסטים</p>
              </div>
            </div>
            <div className="flex gap-2">
              <button
                onClick={loadPreview}
                className="btn btn-secondary flex items-center gap-2"
              >
                <Eye className="w-4 h-4" />
                תצוגה מקדימה
              </button>
              <button
                onClick={saveStory}
                disabled={saving}
                className="btn btn-primary flex items-center gap-2"
              >
                <Save className="w-4 h-4" />
                {saving ? 'שומר...' : 'שמור שינויים'}
              </button>
            </div>
          </div>

          {/* הודעה */}
          {message && (
            <div className={`flex items-center gap-2 p-3 rounded-lg ${
              message.type === 'success' ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'
            }`}>
              {message.type === 'success' ? (
                <CheckCircle className="w-5 h-5" />
              ) : (
                <AlertCircle className="w-5 h-5" />
              )}
              {message.text}
            </div>
          )}
        </div>

        {/* הסיפור המלא */}
        <div className="bg-white rounded-lg shadow-sm p-6">
          <label className="block text-lg font-semibold mb-2">
            הסיפור המלא
          </label>
          <p className="text-gray-500 text-sm mb-4">
            כתוב כאן את כל הסיפור של אייל - עובדות, רקע, הישגים, ערכים. הסיפור הזה יוזרק לכל פוסט שנוצר.
          </p>
          <textarea
            className="w-full h-96 p-4 border border-gray-300 rounded-lg font-mono text-sm resize-y focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
            value={story?.story_content || ''}
            onChange={(e) => setStory(prev => ({ ...(prev || EMPTY_STORY), story_content: e.target.value }))}
            placeholder="כתוב כאן את הסיפור המלא של אייל..."
            dir="rtl"
          />
        </div>

        {/* משפטים אסורים */}
        <div className="bg-white rounded-lg shadow-sm p-6">
          <label className="block text-lg font-semibold mb-2 text-red-600">
            ⛔ משפטים אסורים
          </label>
          <p className="text-gray-500 text-sm mb-4">
            משפטים שה-AI לא ישתמש בהם. שורה אחת לכל משפט. לדוגמה: "פי 3 יותר זמן", "מספר X של לקוחות"
          </p>
          <textarea
            className="w-full h-40 p-4 border border-red-200 rounded-lg font-mono text-sm resize-y focus:ring-2 focus:ring-red-500 focus:border-red-500 bg-red-50"
            value={story?.forbidden_phrases || ''}
            onChange={(e) => setStory(prev => ({ ...(prev || EMPTY_STORY), forbidden_phrases: e.target.value }))}
            placeholder="פי 3 יותר זמן&#10;אלפי לקוחות&#10;הצלחה מסחררת"
            dir="rtl"
          />
        </div>

        {/* הוראות נוספות */}
        <div className="bg-white rounded-lg shadow-sm p-6">
          <label className="block text-lg font-semibold mb-2 text-blue-600">
            📝 הוראות נוספות ל-AI
          </label>
          <p className="text-gray-500 text-sm mb-4">
            הוראות נוספות שיתווספו לכל פרומפט. לדוגמה: "אל תמציא מספרים", "השתמש בטון צנוע"
          </p>
          <textarea
            className="w-full h-40 p-4 border border-blue-200 rounded-lg font-mono text-sm resize-y focus:ring-2 focus:ring-blue-500 focus:border-blue-500 bg-blue-50"
            value={story?.ai_instructions || ''}
            onChange={(e) => setStory(prev => ({ ...(prev || EMPTY_STORY), ai_instructions: e.target.value }))}
            placeholder="אל תמציא עובדות או מספרים שלא מופיעים בסיפור&#10;השתמש בטון צנוע ואותנטי&#10;אל תהיה מכירתי מדי"
            dir="rtl"
          />
        </div>

        {/* בדיקת יצירת פוסט */}
        <div className="bg-white rounded-lg shadow-sm p-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-lg font-semibold flex items-center gap-2">
                <Play className="w-5 h-5" />
                בדיקת יצירת פוסט
              </h2>
              <p className="text-gray-500 text-sm">
                צור פוסט לדוגמה כדי לראות איך הסיפור משפיע על התוצאה
              </p>
            </div>
            <button
              onClick={testGeneration}
              disabled={testing}
              className="btn btn-success flex items-center gap-2"
            >
              <Play className="w-4 h-4" />
              {testing ? 'יוצר פוסט...' : 'צור פוסט לדוגמה'}
            </button>
          </div>

          {testResult && (
            <div className="bg-gray-50 rounded-lg p-4 mt-4">
              <label className="block font-semibold mb-2">תוצאה:</label>
              <pre className="whitespace-pre-wrap text-sm" dir="rtl">{testResult}</pre>
            </div>
          )}
        </div>

        {/* תצוגה מקדימה - Modal */}
        {showPreview && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-lg max-w-4xl w-full max-h-[80vh] overflow-hidden">
              <div className="p-4 border-b border-gray-200 flex items-center justify-between">
                <h3 className="font-semibold">תצוגה מקדימה של הפרומפט המלא</h3>
                <button
                  onClick={() => setShowPreview(false)}
                  className="text-gray-500 hover:text-gray-700"
                >
                  ✕
                </button>
              </div>
              <div className="p-4 overflow-auto max-h-[60vh]">
                <pre className="whitespace-pre-wrap text-sm font-mono bg-gray-50 p-4 rounded-lg" dir="rtl">
                  {previewContent}
                </pre>
              </div>
              <div className="p-4 border-t border-gray-200 text-left">
                <button
                  onClick={() => setShowPreview(false)}
                  className="btn btn-secondary"
                >
                  סגור
                </button>
              </div>
            </div>
          </div>
        )}

        {/* מידע נוסף */}
        {story?.updated_at && (
          <div className="text-center text-gray-400 text-sm">
            עודכן לאחרונה: {new Date(story.updated_at).toLocaleString('he-IL')}
          </div>
        )}
      </div>
    </div>
  )
}
