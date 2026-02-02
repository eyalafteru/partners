'use client'

import { useState, useEffect } from 'react'
import { Calculator, Plus, Edit, Trash2, ExternalLink, Copy, Filter, Loader2, Sparkles, RefreshCw, FileText } from 'lucide-react'

interface CalcItem {
  id: number
  name: string
  intent_description: string | null
  target_url: string
  embed_code_template: string | null
  keywords: string[] | null
  category: string | null
  is_active: boolean
  ai_summary: string | null
  scraped_content: string | null
  scraped_at: string | null
  created_at?: string
}

interface ScanStatus {
  is_running: boolean
  current_calc: string | null
  processed: number
  total: number
}

const CATEGORIES = [
  { id: 'all', name: 'הכל', color: 'bg-gray-100 text-gray-800' },
  { id: 'שכר ותעסוקה', name: 'שכר ותעסוקה', color: 'bg-blue-100 text-blue-800' },
  { id: 'הלוואות ומימון', name: 'הלוואות ומימון', color: 'bg-green-100 text-green-800' },
  { id: 'מחשבוני רכב והוצאות', name: 'מחשבוני רכב והוצאות', color: 'bg-orange-100 text-orange-800' },
  { id: 'נדל״ן ומשכנתא', name: 'נדל״ן ומשכנתא', color: 'bg-purple-100 text-purple-800' },
  { id: 'פנסיה וחיסכון', name: 'פנסיה וחיסכון', color: 'bg-yellow-100 text-yellow-800' },
]

export default function CalculatorsPage() {
  const [calculators, setCalculators] = useState<CalcItem[]>([])
  const [loading, setLoading] = useState(true)
  const [showModal, setShowModal] = useState(false)
  const [editingCalc, setEditingCalc] = useState<CalcItem | null>(null)
  const [selectedCategory, setSelectedCategory] = useState('all')
  const [scanStatus, setScanStatus] = useState<ScanStatus | null>(null)
  const [scanningIds, setScanningIds] = useState<Set<number>>(new Set())
  const [expandedSummary, setExpandedSummary] = useState<number | null>(null)
  const [viewingContent, setViewingContent] = useState<CalcItem | null>(null)

  useEffect(() => {
    fetchCalculators()
    fetchScanStatus()
  }, [])

  // Auto-refresh scan status when running OR when there are active individual scans
  useEffect(() => {
    if (scanStatus?.is_running || scanningIds.size > 0) {
      const interval = setInterval(() => {
        fetchScanStatus()
        fetchCalculators()
        
        // Individual scan tracking is handled via fetchCalculators refresh
      }, 3000)
      return () => clearInterval(interval)
    }
  }, [scanStatus?.is_running, scanningIds.size])

  const fetchCalculators = async () => {
    try {
      const response = await fetch('/api/calculators')
      if (response.ok) {
        const data = await response.json()
        setCalculators(data)
      }
    } catch (error) {
      console.error('Failed to fetch calculators:', error)
    } finally {
      setLoading(false)
    }
  }

  const fetchScanStatus = async () => {
    try {
      const response = await fetch('/api/calculators/scan/status')
      if (response.ok) {
        const data = await response.json()
        setScanStatus(data)
      }
    } catch (error) {
      // Silently ignore
    }
  }

  const scanAllCalculators = async () => {
    try {
      const response = await fetch('/api/calculators/scan/all', { method: 'POST' })
      if (response.ok) {
        fetchScanStatus()
      }
    } catch (error) {
      console.error('Failed to start scan:', error)
    }
  }

  const scanSingleCalculator = async (calcId: number) => {
    setScanningIds(prev => new Set(prev).add(calcId))
    try {
      const response = await fetch(`/api/calculators/${calcId}/scan`, { method: 'POST' })
      if (response.ok) {
        // Wait a bit for the scan to complete
        setTimeout(() => {
          fetchCalculators()
          setScanningIds(prev => {
            const newSet = new Set(prev)
            newSet.delete(calcId)
            return newSet
          })
        }, 60000) // Remove loader after 60 seconds
      }
    } catch (error) {
      console.error('Failed to scan calculator:', error)
      setScanningIds(prev => {
        const newSet = new Set(prev)
        newSet.delete(calcId)
        return newSet
      })
    }
  }

  const deleteCalculator = async (id: number) => {
    if (!confirm('Delete calculator?')) return
    
    try {
      await fetch(`/api/calculators/${id}`, { method: 'DELETE' })
      fetchCalculators()
    } catch (error) {
      console.error('Failed to delete:', error)
    }
  }

  const copyEmbed = (code: string) => {
    navigator.clipboard.writeText(code)
    alert('Embed code copied!')
  }

  // Filter calculators by category
  const filteredCalculators = selectedCategory === 'all' 
    ? calculators 
    : calculators.filter(c => c.category === selectedCategory)

  // Get category color
  const getCategoryColor = (category: string | null) => {
    const cat = CATEGORIES.find(c => c.id === category)
    return cat?.color || 'bg-gray-100 text-gray-800'
  }

  // Count by category
  const categoryCounts = CATEGORIES.map(cat => ({
    ...cat,
    count: cat.id === 'all' 
      ? calculators.length 
      : calculators.filter(c => c.category === cat.id).length
  }))

  const summarizedCount = calculators.filter(c => c.ai_summary).length

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
          <Calculator className="w-7 h-7" />
          ספריית מחשבונים
        </h1>
        <div className="flex items-center gap-2">
          <button 
            onClick={scanAllCalculators}
            disabled={scanStatus?.is_running}
            className={`btn flex items-center gap-2 ${
              scanStatus?.is_running
                ? 'bg-purple-300 cursor-not-allowed'
                : 'bg-purple-500 hover:bg-purple-600 text-white'
            }`}
          >
            {scanStatus?.is_running ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                סורק ({scanStatus.processed}/{scanStatus.total})
              </>
            ) : (
              <>
                <Sparkles className="w-5 h-5" />
                סרוק וצור תקצירים
              </>
            )}
          </button>
          <button 
            onClick={() => { setEditingCalc(null); setShowModal(true) }}
            className="btn btn-primary flex items-center gap-2"
          >
            <Plus className="w-5 h-5" />
            הוסף מחשבון
          </button>
        </div>
      </div>

      {/* Scan Status Banner */}
      {scanStatus?.is_running && (
        <div className="card bg-gradient-to-r from-purple-50 to-blue-50 border border-purple-200">
          <div className="flex items-center gap-3">
            <Loader2 className="w-6 h-6 animate-spin text-purple-600" />
            <div>
              <p className="font-medium text-purple-800">סורק ומייצר תקצירים AI...</p>
              <p className="text-sm text-purple-600">
                מחשבון נוכחי: {scanStatus.current_calc} ({scanStatus.processed}/{scanStatus.total})
              </p>
            </div>
          </div>
          <div className="mt-3 w-full bg-purple-200 rounded-full h-2">
            <div 
              className="bg-purple-600 h-2 rounded-full transition-all duration-500"
              style={{ width: `${(scanStatus.processed / scanStatus.total) * 100}%` }}
            />
          </div>
        </div>
      )}

      {/* Summary Stats */}
      <div className="flex items-center gap-4 text-sm text-gray-600">
        <span className="flex items-center gap-1">
          <Sparkles className="w-4 h-4 text-purple-500" />
          {summarizedCount}/{calculators.length} עם תקציר AI
        </span>
      </div>

      {/* Category Filter Bar */}
      <div className="card">
        <div className="flex items-center gap-2 mb-3">
          <Filter className="w-5 h-5 text-gray-500" />
          <span className="font-medium text-gray-700">סינון לפי קטגוריה:</span>
        </div>
        <div className="flex flex-wrap gap-2">
          {categoryCounts.map(cat => (
            <button
              key={cat.id}
              onClick={() => setSelectedCategory(cat.id)}
              className={`px-4 py-2 rounded-full text-sm font-medium transition-all ${
                selectedCategory === cat.id
                  ? 'ring-2 ring-primary-500 ring-offset-2 ' + cat.color
                  : cat.color + ' hover:opacity-80'
              }`}
            >
              {cat.name}
              <span className="ml-2 px-2 py-0.5 bg-white/50 rounded-full text-xs">
                {cat.count}
              </span>
            </button>
          ))}
        </div>
      </div>

      <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
        {loading ? (
          Array(6).fill(0).map((_, i) => (
            <div key={i} className="card h-48 animate-pulse bg-gray-100"></div>
          ))
        ) : filteredCalculators.length === 0 ? (
          <div className="md:col-span-2 lg:col-span-3 card text-center py-12">
            <Calculator className="w-16 h-16 mx-auto mb-4 text-gray-300" />
            <p className="text-gray-500 mb-4">
              {calculators.length === 0 ? 'לא נוספו מחשבונים עדיין' : 'אין מחשבונים בקטגוריה זו'}
            </p>
            {calculators.length === 0 && (
              <button onClick={() => setShowModal(true)} className="btn btn-primary">
                הוסף מחשבון ראשון
              </button>
            )}
          </div>
        ) : (
          filteredCalculators.map((calc) => (
            <div key={calc.id} className="card hover:shadow-lg transition-shadow">
              <div className="flex items-start justify-between mb-3">
                <div className="flex-1">
                  <h3 className="font-semibold text-lg">{calc.name}</h3>
                  <div className="flex items-center gap-2 mt-1">
                    <span className={`text-xs px-2 py-1 rounded-full ${getCategoryColor(calc.category)}`}>
                      {calc.category || 'ללא קטגוריה'}
                    </span>
                    <span className={`text-xs ${calc.is_active ? 'text-green-600' : 'text-gray-400'}`}>
                      {calc.is_active ? '● פעיל' : '○ לא פעיל'}
                    </span>
                    {calc.ai_summary && (
                      <span className="text-xs px-2 py-1 rounded-full bg-purple-100 text-purple-700 flex items-center gap-1">
                        <Sparkles className="w-3 h-3" />
                        יש תקציר
                      </span>
                    )}
                  </div>
                </div>
              </div>

              {/* AI Summary */}
              {calc.ai_summary ? (
                <div className="mb-3 p-2 bg-purple-50 rounded-lg">
                  <div 
                    className="cursor-pointer hover:bg-purple-100 transition-colors rounded p-1 -m-1"
                    onClick={() => setExpandedSummary(expandedSummary === calc.id ? null : calc.id)}
                  >
                    <p className={`text-sm text-gray-700 ${expandedSummary === calc.id ? '' : 'line-clamp-2'}`}>
                      {calc.ai_summary}
                    </p>
                    <span className="text-xs text-purple-500 mt-1">
                      {expandedSummary === calc.id ? 'לחץ לצמצום' : 'לחץ להרחבה'}
                    </span>
                  </div>
                  <div className="flex items-center justify-between mt-2 pt-2 border-t border-purple-200">
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-gray-500">
                        {calc.scraped_at ? `נסרק: ${new Date(calc.scraped_at).toLocaleDateString('he-IL')}` : ''}
                      </span>
                      {calc.scraped_content && (
                        <button
                          onClick={() => setViewingContent(calc)}
                          className="text-xs px-2 py-1 text-blue-600 hover:bg-blue-50 rounded flex items-center gap-1"
                          title="צפה בתוכן שנסרק"
                        >
                          <FileText className="w-3 h-3" />
                          תוכן
                        </button>
                      )}
                    </div>
                    <button
                      onClick={() => scanSingleCalculator(calc.id)}
                      disabled={scanningIds.has(calc.id)}
                      className="text-xs px-2 py-1 text-purple-600 hover:bg-purple-100 rounded flex items-center gap-1 disabled:opacity-50"
                    >
                      {scanningIds.has(calc.id) ? (
                        <Loader2 className="w-3 h-3 animate-spin" />
                      ) : (
                        <RefreshCw className="w-3 h-3" />
                      )}
                      עדכן
                    </button>
                  </div>
                </div>
              ) : (
                <div className="mb-3 p-2 bg-gray-50 rounded-lg">
                  {scanningIds.has(calc.id) ? (
                    <div className="flex items-center gap-2 text-purple-600">
                      <Loader2 className="w-4 h-4 animate-spin" />
                      <div>
                        <p className="text-sm font-medium">מייצר תקציר AI...</p>
                        <p className="text-xs text-purple-500">סורק את עמוד המחשבון ומנתח עם AI</p>
                      </div>
                    </div>
                  ) : (
                    <div className="flex items-center justify-between">
                      <span className="text-xs text-gray-500">אין תקציר AI</span>
                      <button
                        onClick={() => scanSingleCalculator(calc.id)}
                        className="text-xs px-3 py-1.5 bg-purple-500 text-white rounded hover:bg-purple-600 flex items-center gap-1 transition-colors"
                      >
                        <RefreshCw className="w-3 h-3" />
                        צור תקציר
                      </button>
                    </div>
                  )}
                </div>
              )}

              <div className="flex flex-wrap gap-1 mb-4">
                {calc.keywords?.slice(0, 4).map((kw, i) => (
                  <span key={i} className="text-xs px-2 py-0.5 bg-gray-100 text-gray-600 rounded">
                    {kw}
                  </span>
                ))}
                {(calc.keywords?.length || 0) > 4 && (
                  <span className="text-xs px-2 py-0.5 bg-gray-100 text-gray-500 rounded">
                    +{(calc.keywords?.length || 0) - 4}
                  </span>
                )}
              </div>

              <div className="flex items-center gap-2 pt-3 border-t border-gray-100">
                <a
                  href={calc.target_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="btn btn-secondary flex-1 flex items-center justify-center gap-1"
                >
                  <ExternalLink className="w-4 h-4" />
                  View
                </a>
                <button
                  onClick={() => copyEmbed(calc.embed_code_template || '')}
                  className="btn btn-secondary"
                  title="Copy embed code"
                >
                  <Copy className="w-4 h-4" />
                </button>
                <button
                  onClick={() => { setEditingCalc(calc); setShowModal(true) }}
                  className="btn btn-secondary"
                  title="Edit"
                >
                  <Edit className="w-4 h-4" />
                </button>
                <button
                  onClick={() => deleteCalculator(calc.id)}
                  className="btn btn-secondary text-danger-600"
                  title="Delete"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>
          ))
        )}
      </div>

      {showModal && (
        <CalculatorModal
          calculator={editingCalc}
          onClose={() => setShowModal(false)}
          onSaved={fetchCalculators}
        />
      )}

      {/* Modal: View Scraped Content */}
      {viewingContent && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col">
            {/* Header */}
            <div className="p-6 border-b border-gray-200 flex items-center justify-between">
              <div>
                <h3 className="text-xl font-bold text-gray-800 flex items-center gap-2">
                  <FileText className="w-5 h-5 text-blue-500" />
                  תוכן שנסרק: {viewingContent.name}
                </h3>
                <p className="text-sm text-gray-500 mt-1">
                  נסרק: {viewingContent.scraped_at ? new Date(viewingContent.scraped_at).toLocaleString('he-IL') : 'לא ידוע'}
                </p>
              </div>
              <button
                onClick={() => setViewingContent(null)}
                className="text-gray-400 hover:text-gray-600 text-2xl leading-none"
              >
                ×
              </button>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto p-6">
              {viewingContent.scraped_content ? (
                <div className="prose prose-sm max-w-none">
                  <div className="bg-white rounded-lg p-6 border border-gray-200 shadow-sm">
                    <div 
                      className="text-base text-gray-800 leading-loose space-y-4"
                      style={{
                        whiteSpace: 'pre-line',
                        wordBreak: 'break-word',
                        direction: 'rtl',
                        fontFamily: 'Arial, sans-serif'
                      }}
                    >
                      {viewingContent.scraped_content
                        .split(/([.!?]\s+)/)
                        .filter(s => s.trim())
                        .map((sentence, i) => {
                          if (sentence.match(/[.!?]\s+/)) return sentence;
                          if (sentence.length < 10) return sentence;
                          return (
                            <span key={i}>
                              {sentence}
                              {i % 3 === 2 ? '\n\n' : ' '}
                            </span>
                          );
                        })
                      }
                    </div>
                  </div>
                </div>
              ) : (
                <div className="text-center py-12">
                  <FileText className="w-16 h-16 text-gray-300 mx-auto mb-4" />
                  <p className="text-gray-500">אין תוכן זמין</p>
                </div>
              )}
            </div>

            {/* Footer */}
            <div className="p-4 border-t border-gray-200 flex justify-between items-center bg-gray-50">
              <div className="text-sm text-gray-600">
                אורך: {viewingContent.scraped_content?.length.toLocaleString()} תווים
              </div>
              <button
                onClick={() => setViewingContent(null)}
                className="btn btn-secondary"
              >
                סגור
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function CalculatorModal({
  calculator,
  onClose,
  onSaved
}: {
  calculator: CalcItem | null
  onClose: () => void
  onSaved: () => void
}) {
  const [form, setForm] = useState({
    name: calculator?.name || '',
    description: calculator?.intent_description || '',
    url: calculator?.target_url || '',
    embed_code: calculator?.embed_code_template || '',
    category: calculator?.category || 'הלוואות ומימון',
    keywords: calculator?.keywords?.join(', ') || '',
    is_active: calculator?.is_active ?? true
  })
  const [submitting, setSubmitting] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSubmitting(true)

    try {
      const apiUrl = calculator 
        ? `/api/calculators/${calculator.id}` 
        : '/api/calculators'
      const method = calculator ? 'PUT' : 'POST'

      const response = await fetch(apiUrl, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: form.name,
          target_url: form.url,
          intent_description: form.description,
          embed_code_template: form.embed_code,
          category: form.category,
          keywords: form.keywords.split(',').map(k => k.trim()).filter(Boolean),
          is_active: form.is_active
        })
      })

      if (response.ok) {
        onSaved()
        onClose()
      }
    } catch (error) {
      console.error('Failed to save calculator:', error)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg w-full max-w-lg max-h-[90vh] overflow-auto p-6">
        <h2 className="text-xl font-bold mb-4">
          {calculator ? 'Edit Calculator' : 'Add New Calculator'}
        </h2>
        
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="label">Name</label>
            <input
              type="text"
              className="input"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              placeholder="Mortgage Calculator"
              required
            />
          </div>

          <div>
            <label className="label">Description</label>
            <textarea
              className="input h-20"
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
              placeholder="Short description..."
            />
          </div>

          <div>
            <label className="label">URL</label>
            <input
              type="url"
              className="input"
              value={form.url}
              onChange={(e) => setForm({ ...form, url: e.target.value })}
              placeholder="https://example.com/calculator"
              required
            />
          </div>

          <div>
            <label className="label">Embed Code</label>
            <textarea
              className="input h-24 font-mono text-sm"
              value={form.embed_code}
              onChange={(e) => setForm({ ...form, embed_code: e.target.value })}
              placeholder="<iframe src='...'></iframe>"
            />
          </div>

          <div>
            <label className="label">Category</label>
            <select
              className="input"
              value={form.category}
              onChange={(e) => setForm({ ...form, category: e.target.value })}
            >
              <option value="שכר ותעסוקה">שכר ותעסוקה</option>
              <option value="הלוואות ומימון">הלוואות ומימון</option>
              <option value="מחשבוני רכב והוצאות">מחשבוני רכב והוצאות</option>
              <option value="נדל״ן ומשכנתא">נדל״ן ומשכנתא</option>
              <option value="פנסיה וחיסכון">פנסיה וחיסכון</option>
            </select>
          </div>

          <div>
            <label className="label">Keywords (comma separated)</label>
            <input
              type="text"
              className="input"
              value={form.keywords}
              onChange={(e) => setForm({ ...form, keywords: e.target.value })}
              placeholder="mortgage, interest, loan"
            />
          </div>

          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="is_active"
              checked={form.is_active}
              onChange={(e) => setForm({ ...form, is_active: e.target.checked })}
              className="w-4 h-4"
            />
            <label htmlFor="is_active">Active</label>
          </div>

          <div className="flex gap-2 pt-4">
            <button type="button" onClick={onClose} className="btn btn-secondary flex-1">
              Cancel
            </button>
            <button type="submit" disabled={submitting} className="btn btn-primary flex-1">
              {submitting ? 'Saving...' : 'Save'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
