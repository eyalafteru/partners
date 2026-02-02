'use client'

import { useState, useEffect } from 'react'
import { Plus, Edit, Trash2, ExternalLink, Calculator } from 'lucide-react'

interface CalcItem {
  id: number
  name: string
  target_url: string
  intent_description: string
  keywords: string[]
  is_active: boolean
}

export default function CalculatorsPage() {
  const [calculators, setCalculators] = useState<CalcItem[]>([])
  const [loading, setLoading] = useState(true)
  const [showModal, setShowModal] = useState(false)
  const [editingCalc, setEditingCalc] = useState<CalcItem | null>(null)

  useEffect(() => {
    fetchCalculators()
  }, [])

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

  const deleteCalculator = async (id: number) => {
    if (!confirm('האם למחוק את המחשבון?')) return
    
    try {
      await fetch(`/api/calculators/${id}`, { method: 'DELETE' })
      fetchCalculators()
    } catch (error) {
      console.error('Failed to delete calculator:', error)
    }
  }

  return (
    <div className="space-y-6">
      {/* כותרת */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">ניהול מחשבונים</h1>
        <button 
          onClick={() => { setEditingCalc(null); setShowModal(true) }}
          className="btn btn-primary flex items-center gap-2"
        >
          <Plus className="w-5 h-5" />
          הוסף מחשבון
        </button>
      </div>

      {/* רשימת מחשבונים */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {loading ? (
          Array(6).fill(0).map((_, i) => (
            <div key={i} className="card h-40 animate-pulse bg-gray-100"></div>
          ))
        ) : calculators.length === 0 ? (
          <div className="col-span-full card text-center py-12">
            <Calculator className="w-16 h-16 mx-auto mb-4 text-gray-300" />
            <p className="text-gray-500 mb-4">אין מחשבונים עדיין</p>
            <button 
              onClick={() => setShowModal(true)}
              className="btn btn-primary"
            >
              הוסף מחשבון ראשון
            </button>
          </div>
        ) : (
          calculators.map((calc) => (
            <div key={calc.id} className="card">
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-2">
                  <Calculator className="w-5 h-5 text-primary-600" />
                  <h3 className="font-semibold">{calc.name}</h3>
                </div>
                <span className={`badge ${calc.is_active ? 'badge-success' : 'badge-danger'}`}>
                  {calc.is_active ? 'פעיל' : 'מושבת'}
                </span>
              </div>
              
              <a 
                href={calc.target_url}
                target="_blank"
                rel="noopener"
                className="text-sm text-primary-600 hover:underline flex items-center gap-1 mb-3"
              >
                {calc.target_url.slice(0, 40)}...
                <ExternalLink className="w-3 h-3" />
              </a>
              
              {calc.intent_description && (
                <p className="text-sm text-gray-600 mb-3 line-clamp-2">
                  {calc.intent_description}
                </p>
              )}
              
              {calc.keywords && calc.keywords.length > 0 && (
                <div className="flex flex-wrap gap-1 mb-3">
                  {calc.keywords.slice(0, 3).map((kw, i) => (
                    <span key={i} className="px-2 py-0.5 bg-gray-100 rounded text-xs">
                      {kw}
                    </span>
                  ))}
                </div>
              )}
              
              <div className="flex items-center justify-end gap-2 pt-3 border-t border-gray-100">
                <button 
                  onClick={() => { setEditingCalc(calc); setShowModal(true) }}
                  className="p-2 text-gray-600 hover:bg-gray-100 rounded"
                >
                  <Edit className="w-4 h-4" />
                </button>
                <button 
                  onClick={() => deleteCalculator(calc.id)}
                  className="p-2 text-danger-600 hover:bg-danger-50 rounded"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Modal */}
      {showModal && (
        <CalculatorModal 
          calculator={editingCalc}
          onClose={() => setShowModal(false)} 
          onSaved={fetchCalculators} 
        />
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
  const [name, setName] = useState(calculator?.name || '')
  const [targetUrl, setTargetUrl] = useState(calculator?.target_url || '')
  const [description, setDescription] = useState(calculator?.intent_description || '')
  const [keywords, setKeywords] = useState(calculator?.keywords?.join(', ') || '')
  const [isActive, setIsActive] = useState(calculator?.is_active ?? true)
  const [submitting, setSubmitting] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSubmitting(true)

    try {
      const data = {
        name,
        target_url: targetUrl,
        intent_description: description,
        keywords: keywords.split(',').map(k => k.trim()).filter(Boolean),
        is_active: isActive
      }

      const url = calculator ? `/api/calculators/${calculator.id}` : '/api/calculators'
      const method = calculator ? 'PUT' : 'POST'

      const response = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
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
      <div className="bg-white rounded-lg w-full max-w-lg p-6">
        <h2 className="text-xl font-bold mb-4">
          {calculator ? 'עריכת מחשבון' : 'מחשבון חדש'}
        </h2>
        
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="label">שם המחשבון</label>
            <input
              type="text"
              className="input"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="למשל: מחשבון מס רכישה"
              required
            />
          </div>

          <div>
            <label className="label">קישור</label>
            <input
              type="url"
              className="input"
              value={targetUrl}
              onChange={(e) => setTargetUrl(e.target.value)}
              placeholder="https://..."
              required
            />
          </div>

          <div>
            <label className="label">תיאור (למי מתאים)</label>
            <textarea
              className="input h-24"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="תיאור מפורט למי המחשבון מתאים..."
            />
          </div>

          <div>
            <label className="label">מילות מפתח (מופרדות בפסיק)</label>
            <input
              type="text"
              className="input"
              value={keywords}
              onChange={(e) => setKeywords(e.target.value)}
              placeholder="מס רכישה, נדלן, דירה"
            />
          </div>

          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="isActive"
              checked={isActive}
              onChange={(e) => setIsActive(e.target.checked)}
              className="w-4 h-4"
            />
            <label htmlFor="isActive" className="text-sm">מחשבון פעיל</label>
          </div>

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
