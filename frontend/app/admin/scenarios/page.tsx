'use client'

import { useState, useEffect } from 'react'
import { 
  MessageSquare, 
  Plus, 
  Edit2, 
  Trash2, 
  Save, 
  X, 
  RefreshCw,
  PlayCircle,
  PauseCircle,
  Sparkles,
  Filter,
  Download
} from 'lucide-react'

interface Scenario {
  id: number
  name: string
  display_name: string
  category: string
  keywords: string[]
  response_subject: string | null
  response_body: string
  requires_human: boolean
  priority: number
  is_active: boolean
  sender_name: string
  sender_title: string
  created_at: string | null
  updated_at: string | null
}

interface Category {
  value: string
  label: string
  color: string
}

const CATEGORIES: Category[] = [
  { value: 'positive', label: 'חיובי', color: 'bg-green-100 text-green-800' },
  { value: 'negative', label: 'שלילי', color: 'bg-red-100 text-red-800' },
  { value: 'question', label: 'שאלה', color: 'bg-blue-100 text-blue-800' },
  { value: 'technical', label: 'טכני', color: 'bg-purple-100 text-purple-800' },
  { value: 'deferral', label: 'דחייה', color: 'bg-yellow-100 text-yellow-800' },
  { value: 'human', label: 'העברה לאנושי', color: 'bg-orange-100 text-orange-800' },
]

const TEMPLATE_VARIABLES = [
  { name: '{{lead_name}}', description: 'שם הליד' },
  { name: '{{domain}}', description: 'דומיין האתר' },
  { name: '{{calculators_link}}', description: 'קישור למחשבונים' },
  { name: '{{sender_name}}', description: 'שם השולח' },
  { name: '{{sender_title}}', description: 'תפקיד השולח' },
]

export default function ScenariosPage() {
  const [scenarios, setScenarios] = useState<Scenario[]>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [editingScenario, setEditingScenario] = useState<Scenario | null>(null)
  const [isCreating, setIsCreating] = useState(false)
  const [filterCategory, setFilterCategory] = useState<string>('')
  const [showVariables, setShowVariables] = useState(false)

  useEffect(() => {
    fetchScenarios()
  }, [filterCategory])

  const fetchScenarios = async () => {
    try {
      const url = filterCategory 
        ? `/api/admin/scenarios?category=${filterCategory}`
        : '/api/admin/scenarios'
      
      const response = await fetch(url)
      if (response.ok) {
        const data = await response.json()
        setScenarios(data.scenarios)
      }
    } catch (error) {
      console.error('Failed to fetch scenarios:', error)
    } finally {
      setLoading(false)
    }
  }

  const seedScenarios = async () => {
    setSaving(true)
    try {
      const response = await fetch('/api/admin/scenarios/seed', {
        method: 'POST'
      })
      if (response.ok) {
        const data = await response.json()
        alert(`נוצרו ${data.created} תרחישים, דולגו ${data.skipped} קיימים`)
        fetchScenarios()
      }
    } catch (error) {
      console.error('Failed to seed scenarios:', error)
      alert('שגיאה בטעינת תרחישים')
    } finally {
      setSaving(false)
    }
  }

  const toggleScenario = async (id: number) => {
    try {
      const response = await fetch(`/api/admin/scenarios/${id}/toggle`, {
        method: 'POST'
      })
      if (response.ok) {
        fetchScenarios()
      }
    } catch (error) {
      console.error('Failed to toggle scenario:', error)
    }
  }

  const deleteScenario = async (id: number) => {
    if (!confirm('האם למחוק את התרחיש?')) return
    
    try {
      const response = await fetch(`/api/admin/scenarios/${id}`, {
        method: 'DELETE'
      })
      if (response.ok) {
        fetchScenarios()
      }
    } catch (error) {
      console.error('Failed to delete scenario:', error)
    }
  }

  const saveScenario = async () => {
    if (!editingScenario) return
    
    setSaving(true)
    try {
      const url = isCreating 
        ? '/api/admin/scenarios'
        : `/api/admin/scenarios/${editingScenario.id}`
      
      const response = await fetch(url, {
        method: isCreating ? 'POST' : 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(editingScenario)
      })
      
      if (response.ok) {
        setEditingScenario(null)
        setIsCreating(false)
        fetchScenarios()
        alert('התרחיש נשמר בהצלחה!')
      } else {
        const error = await response.json()
        alert(`שגיאה: ${error.detail}`)
      }
    } catch (error) {
      console.error('Failed to save scenario:', error)
      alert('שגיאה בשמירה')
    } finally {
      setSaving(false)
    }
  }

  const startCreate = () => {
    setIsCreating(true)
    setEditingScenario({
      id: 0,
      name: '',
      display_name: '',
      category: 'positive',
      keywords: [],
      response_subject: '',
      response_body: '',
      requires_human: false,
      priority: 50,
      is_active: true,
      sender_name: 'אייל עובדיה',
      sender_title: 'מנהל מקצועי | רק תבקש',
      created_at: null,
      updated_at: null
    })
  }

  const getCategoryStyle = (category: string) => {
    const cat = CATEGORIES.find(c => c.value === category)
    return cat?.color || 'bg-gray-100 text-gray-800'
  }

  const getCategoryLabel = (category: string) => {
    const cat = CATEGORIES.find(c => c.value === category)
    return cat?.label || category
  }

  if (loading) {
    return <div className="p-8 text-center">טוען...</div>
  }

  return (
    <div className="space-y-6">
      {/* כותרת */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
          <MessageSquare className="w-7 h-7" />
          ניהול תרחישי תשובות
        </h1>
        <div className="flex gap-2">
          <button 
            onClick={seedScenarios}
            disabled={saving}
            className="btn btn-secondary flex items-center gap-2"
          >
            <Download className="w-5 h-5" />
            טען תרחישי ברירת מחדל
          </button>
          <button 
            onClick={startCreate}
            className="btn btn-primary flex items-center gap-2"
          >
            <Plus className="w-5 h-5" />
            תרחיש חדש
          </button>
        </div>
      </div>

      {/* פילטרים */}
      <div className="card flex items-center gap-4">
        <Filter className="w-5 h-5 text-gray-400" />
        <span className="text-sm text-gray-600">סנן לפי קטגוריה:</span>
        <div className="flex gap-2">
          <button
            onClick={() => setFilterCategory('')}
            className={`px-3 py-1 rounded-full text-sm ${
              filterCategory === '' ? 'bg-gray-800 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            הכל ({scenarios.length})
          </button>
          {CATEGORIES.map(cat => (
            <button
              key={cat.value}
              onClick={() => setFilterCategory(cat.value)}
              className={`px-3 py-1 rounded-full text-sm ${
                filterCategory === cat.value ? 'bg-gray-800 text-white' : `${cat.color} hover:opacity-80`
              }`}
            >
              {cat.label}
            </button>
          ))}
        </div>
      </div>

      {/* טבלת תרחישים */}
      <div className="card overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-right text-sm font-medium text-gray-600">סטטוס</th>
              <th className="px-4 py-3 text-right text-sm font-medium text-gray-600">שם תרחיש</th>
              <th className="px-4 py-3 text-right text-sm font-medium text-gray-600">קטגוריה</th>
              <th className="px-4 py-3 text-right text-sm font-medium text-gray-600">מילות מפתח</th>
              <th className="px-4 py-3 text-right text-sm font-medium text-gray-600">עדיפות</th>
              <th className="px-4 py-3 text-right text-sm font-medium text-gray-600">אנושי</th>
              <th className="px-4 py-3 text-right text-sm font-medium text-gray-600">פעולות</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {scenarios.map(scenario => (
              <tr key={scenario.id} className={`hover:bg-gray-50 ${!scenario.is_active ? 'opacity-50' : ''}`}>
                <td className="px-4 py-3">
                  <button
                    onClick={() => toggleScenario(scenario.id)}
                    className={`p-1 rounded-full ${scenario.is_active ? 'text-green-600' : 'text-gray-400'}`}
                  >
                    {scenario.is_active ? (
                      <PlayCircle className="w-6 h-6" />
                    ) : (
                      <PauseCircle className="w-6 h-6" />
                    )}
                  </button>
                </td>
                <td className="px-4 py-3">
                  <div className="font-medium text-gray-900">{scenario.display_name}</div>
                  <div className="text-xs text-gray-500">{scenario.name}</div>
                </td>
                <td className="px-4 py-3">
                  <span className={`px-2 py-1 rounded-full text-xs font-medium ${getCategoryStyle(scenario.category)}`}>
                    {getCategoryLabel(scenario.category)}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <div className="flex flex-wrap gap-1 max-w-xs">
                    {scenario.keywords.slice(0, 3).map((kw, i) => (
                      <span key={i} className="px-2 py-0.5 bg-gray-100 text-gray-600 rounded text-xs">
                        {kw}
                      </span>
                    ))}
                    {scenario.keywords.length > 3 && (
                      <span className="text-gray-400 text-xs">+{scenario.keywords.length - 3}</span>
                    )}
                  </div>
                </td>
                <td className="px-4 py-3 text-center">
                  <span className="font-mono text-sm">{scenario.priority}</span>
                </td>
                <td className="px-4 py-3 text-center">
                  {scenario.requires_human && (
                    <span className="text-orange-500">⚠️</span>
                  )}
                </td>
                <td className="px-4 py-3">
                  <div className="flex gap-2">
                    <button
                      onClick={() => {
                        setIsCreating(false)
                        setEditingScenario(scenario)
                      }}
                      className="p-1 text-blue-600 hover:bg-blue-50 rounded"
                    >
                      <Edit2 className="w-5 h-5" />
                    </button>
                    <button
                      onClick={() => deleteScenario(scenario.id)}
                      className="p-1 text-red-600 hover:bg-red-50 rounded"
                    >
                      <Trash2 className="w-5 h-5" />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
            {scenarios.length === 0 && (
              <tr>
                <td colSpan={7} className="px-4 py-8 text-center text-gray-500">
                  אין תרחישים. לחץ על &quot;טען תרחישי ברירת מחדל&quot; להתחלה.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* מודל עריכה/יצירה */}
      {editingScenario && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg w-full max-w-3xl max-h-[90vh] overflow-y-auto">
            <div className="p-6 border-b flex items-center justify-between">
              <h2 className="text-xl font-bold">
                {isCreating ? 'יצירת תרחיש חדש' : 'עריכת תרחיש'}
              </h2>
              <button 
                onClick={() => {
                  setEditingScenario(null)
                  setIsCreating(false)
                }}
                className="p-1 hover:bg-gray-100 rounded"
              >
                <X className="w-6 h-6" />
              </button>
            </div>

            <div className="p-6 space-y-4">
              {/* שורה 1: שם ושם תצוגה */}
              <div className="grid md:grid-cols-2 gap-4">
                <div>
                  <label className="label">מזהה טכני (אנגלית)</label>
                  <input
                    type="text"
                    className="input"
                    value={editingScenario.name}
                    onChange={e => setEditingScenario({
                      ...editingScenario,
                      name: e.target.value.toLowerCase().replace(/\s/g, '_')
                    })}
                    placeholder="interested_general"
                    disabled={!isCreating}
                  />
                </div>
                <div>
                  <label className="label">שם תצוגה (עברית)</label>
                  <input
                    type="text"
                    className="input"
                    value={editingScenario.display_name}
                    onChange={e => setEditingScenario({
                      ...editingScenario,
                      display_name: e.target.value
                    })}
                    placeholder="מעוניין בכללי"
                  />
                </div>
              </div>

              {/* שורה 2: קטגוריה ועדיפות */}
              <div className="grid md:grid-cols-3 gap-4">
                <div>
                  <label className="label">קטגוריה</label>
                  <select
                    className="input"
                    value={editingScenario.category}
                    onChange={e => setEditingScenario({
                      ...editingScenario,
                      category: e.target.value
                    })}
                  >
                    {CATEGORIES.map(cat => (
                      <option key={cat.value} value={cat.value}>{cat.label}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="label">עדיפות (1-200)</label>
                  <input
                    type="number"
                    className="input"
                    value={editingScenario.priority}
                    onChange={e => setEditingScenario({
                      ...editingScenario,
                      priority: parseInt(e.target.value) || 50
                    })}
                    min={1}
                    max={200}
                  />
                </div>
                <div className="flex items-end">
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={editingScenario.requires_human}
                      onChange={e => setEditingScenario({
                        ...editingScenario,
                        requires_human: e.target.checked
                      })}
                      className="w-4 h-4"
                    />
                    <span>דורש טיפול אנושי</span>
                  </label>
                </div>
              </div>

              {/* מילות מפתח */}
              <div>
                <label className="label">מילות מפתח (מופרדות בפסיקים)</label>
                <input
                  type="text"
                  className="input"
                  value={editingScenario.keywords.join(', ')}
                  onChange={e => setEditingScenario({
                    ...editingScenario,
                    keywords: e.target.value.split(',').map(k => k.trim()).filter(Boolean)
                  })}
                  placeholder="מעוניין, אשמח, כן, מצוין"
                />
              </div>

              {/* נושא התשובה */}
              <div>
                <label className="label">נושא המייל</label>
                <input
                  type="text"
                  className="input"
                  value={editingScenario.response_subject || ''}
                  onChange={e => setEditingScenario({
                    ...editingScenario,
                    response_subject: e.target.value
                  })}
                  placeholder="מצוין! הנה כל מה שצריך להתחיל"
                />
              </div>

              {/* תוכן התשובה */}
              <div>
                <div className="flex items-center justify-between mb-1">
                  <label className="label mb-0">תוכן התשובה</label>
                  <button
                    onClick={() => setShowVariables(!showVariables)}
                    className="text-sm text-blue-600 hover:underline flex items-center gap-1"
                  >
                    <Sparkles className="w-4 h-4" />
                    משתנים זמינים
                  </button>
                </div>
                
                {showVariables && (
                  <div className="mb-2 p-3 bg-blue-50 rounded-lg">
                    <div className="text-sm text-blue-800 mb-2">משתנים להחלפה:</div>
                    <div className="flex flex-wrap gap-2">
                      {TEMPLATE_VARIABLES.map(v => (
                        <button
                          key={v.name}
                          onClick={() => {
                            const textarea = document.getElementById('response_body') as HTMLTextAreaElement
                            const start = textarea.selectionStart
                            const end = textarea.selectionEnd
                            const text = editingScenario.response_body
                            const newText = text.substring(0, start) + v.name + text.substring(end)
                            setEditingScenario({
                              ...editingScenario,
                              response_body: newText
                            })
                          }}
                          className="px-2 py-1 bg-white text-blue-700 rounded text-sm hover:bg-blue-100"
                          title={v.description}
                        >
                          {v.name}
                        </button>
                      ))}
                    </div>
                  </div>
                )}
                
                <textarea
                  id="response_body"
                  className="input min-h-[200px]"
                  value={editingScenario.response_body}
                  onChange={e => setEditingScenario({
                    ...editingScenario,
                    response_body: e.target.value
                  })}
                  placeholder="שלום {{lead_name}},

תודה על פנייתך!

{{sender_name}}
{{sender_title}}"
                />
              </div>

              {/* פרטי שולח */}
              <div className="grid md:grid-cols-2 gap-4">
                <div>
                  <label className="label">שם השולח</label>
                  <input
                    type="text"
                    className="input"
                    value={editingScenario.sender_name}
                    onChange={e => setEditingScenario({
                      ...editingScenario,
                      sender_name: e.target.value
                    })}
                    placeholder="אייל עובדיה"
                  />
                </div>
                <div>
                  <label className="label">תפקיד השולח</label>
                  <input
                    type="text"
                    className="input"
                    value={editingScenario.sender_title}
                    onChange={e => setEditingScenario({
                      ...editingScenario,
                      sender_title: e.target.value
                    })}
                    placeholder="מנהל מקצועי | רק תבקש"
                  />
                </div>
              </div>
            </div>

            <div className="p-6 border-t flex justify-end gap-3">
              <button
                onClick={() => {
                  setEditingScenario(null)
                  setIsCreating(false)
                }}
                className="btn btn-secondary"
              >
                ביטול
              </button>
              <button
                onClick={saveScenario}
                disabled={saving || !editingScenario.name || !editingScenario.display_name}
                className="btn btn-primary flex items-center gap-2"
              >
                {saving ? (
                  <RefreshCw className="w-5 h-5 animate-spin" />
                ) : (
                  <Save className="w-5 h-5" />
                )}
                {saving ? 'שומר...' : 'שמור'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
