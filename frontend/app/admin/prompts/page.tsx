'use client'

import { useState, useEffect } from 'react'
import { Bot, Edit, Play, BarChart2, Save } from 'lucide-react'

interface Prompt {
  id: number
  node_name: string
  display_name: string
  description: string
  system_prompt: string
  user_prompt_template: string
  available_variables: string[]
  model_name: string
  temperature: number
  max_tokens: number
  is_active: boolean
}

export default function PromptsPage() {
  const [prompts, setPrompts] = useState<Prompt[]>([])
  const [selectedPrompt, setSelectedPrompt] = useState<Prompt | null>(null)
  const [loading, setLoading] = useState(true)
  const [editing, setEditing] = useState(false)
  const [testVariables, setTestVariables] = useState<Record<string, string>>({})
  const [testResult, setTestResult] = useState('')
  const [testing, setTesting] = useState(false)

  useEffect(() => {
    fetchPrompts()
  }, [])

  const fetchPrompts = async () => {
    try {
      const response = await fetch('/api/prompts')
      if (response.ok) {
        const data = await response.json()
        setPrompts(data)
        if (data.length > 0 && !selectedPrompt) {
          setSelectedPrompt(data[0])
        }
      }
    } catch (error) {
      console.error('Failed to fetch prompts:', error)
    } finally {
      setLoading(false)
    }
  }

  const savePrompt = async () => {
    if (!selectedPrompt) return

    try {
      await fetch(`/api/prompts/${selectedPrompt.node_name}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          system_prompt: selectedPrompt.system_prompt,
          user_prompt_template: selectedPrompt.user_prompt_template,
          temperature: selectedPrompt.temperature,
          max_tokens: selectedPrompt.max_tokens
        })
      })
      setEditing(false)
      fetchPrompts()
    } catch (error) {
      console.error('Failed to save prompt:', error)
    }
  }

  const testPrompt = async () => {
    if (!selectedPrompt) return
    setTesting(true)
    setTestResult('')

    try {
      const response = await fetch(`/api/prompts/${selectedPrompt.node_name}/test`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ variables: testVariables })
      })

      if (response.ok) {
        const data = await response.json()
        setTestResult(data.response || data.full_prompt)
      }
    } catch (error) {
      console.error('Failed to test prompt:', error)
      setTestResult('שגיאה בבדיקה')
    } finally {
      setTesting(false)
    }
  }

  return (
    <div className="h-full flex">
      {/* רשימת פרומפטים */}
      <div className="w-72 border-l border-gray-200 bg-white overflow-hidden flex flex-col">
        <div className="p-4 border-b border-gray-200">
          <h2 className="font-semibold flex items-center gap-2">
            <Bot className="w-5 h-5" />
            ניהול פרומפטים
          </h2>
        </div>
        
        <div className="flex-1 overflow-auto">
          {loading ? (
            <div className="p-4 text-center text-gray-500">טוען...</div>
          ) : (
            prompts.map((prompt) => (
              <button
                key={prompt.node_name}
                onClick={() => { setSelectedPrompt(prompt); setEditing(false) }}
                className={`w-full p-4 text-right border-b border-gray-100 hover:bg-gray-50 ${
                  selectedPrompt?.node_name === prompt.node_name ? 'bg-primary-50' : ''
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="font-medium text-sm">{prompt.display_name}</span>
                  <span className={`w-2 h-2 rounded-full ${prompt.is_active ? 'bg-green-500' : 'bg-gray-300'}`} />
                </div>
                <p className="text-xs text-gray-500 mt-1">{prompt.node_name}</p>
              </button>
            ))
          )}
        </div>
      </div>

      {/* עורך */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {!selectedPrompt ? (
          <div className="flex-1 flex items-center justify-center text-gray-500">
            בחר פרומפט לעריכה
          </div>
        ) : (
          <>
            {/* כותרת */}
            <div className="bg-white border-b border-gray-200 p-4 flex items-center justify-between">
              <div>
                <h3 className="font-semibold">{selectedPrompt.display_name}</h3>
                <p className="text-sm text-gray-500">{selectedPrompt.description}</p>
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => setEditing(!editing)}
                  className={`btn ${editing ? 'btn-primary' : 'btn-secondary'} flex items-center gap-2`}
                >
                  <Edit className="w-4 h-4" />
                  {editing ? 'מצב עריכה' : 'ערוך'}
                </button>
                {editing && (
                  <button onClick={savePrompt} className="btn btn-success flex items-center gap-2">
                    <Save className="w-4 h-4" />
                    שמור
                  </button>
                )}
              </div>
            </div>

            {/* תוכן */}
            <div className="flex-1 overflow-auto p-4 space-y-6">
              {/* System Prompt */}
              <div>
                <label className="label">System Prompt</label>
                <textarea
                  className="input h-40 font-mono text-sm"
                  value={selectedPrompt.system_prompt}
                  onChange={(e) => setSelectedPrompt({ ...selectedPrompt, system_prompt: e.target.value })}
                  disabled={!editing}
                />
              </div>

              {/* User Prompt Template */}
              <div>
                <label className="label">User Prompt Template</label>
                <textarea
                  className="input h-48 font-mono text-sm"
                  value={selectedPrompt.user_prompt_template}
                  onChange={(e) => setSelectedPrompt({ ...selectedPrompt, user_prompt_template: e.target.value })}
                  disabled={!editing}
                />
              </div>

              {/* משתנים */}
              <div>
                <label className="label">משתנים זמינים</label>
                <div className="flex flex-wrap gap-2">
                  {selectedPrompt.available_variables?.map((v) => (
                    <span key={v} className="px-2 py-1 bg-gray-100 rounded text-sm font-mono">
                      {`{{${v}}}`}
                    </span>
                  ))}
                </div>
              </div>

              {/* הגדרות */}
              <div className="grid grid-cols-3 gap-4">
                <div>
                  <label className="label">מודל</label>
                  <input
                    type="text"
                    className="input"
                    value={selectedPrompt.model_name}
                    disabled
                  />
                </div>
                <div>
                  <label className="label">Temperature</label>
                  <input
                    type="number"
                    className="input"
                    value={selectedPrompt.temperature}
                    onChange={(e) => setSelectedPrompt({ ...selectedPrompt, temperature: parseFloat(e.target.value) })}
                    disabled={!editing}
                    step={0.1}
                    min={0}
                    max={1}
                  />
                </div>
                <div>
                  <label className="label">Max Tokens</label>
                  <input
                    type="number"
                    className="input"
                    value={selectedPrompt.max_tokens}
                    onChange={(e) => setSelectedPrompt({ ...selectedPrompt, max_tokens: parseInt(e.target.value) })}
                    disabled={!editing}
                  />
                </div>
              </div>

              {/* בדיקה */}
              <div className="border-t border-gray-200 pt-6">
                <h4 className="font-semibold mb-4 flex items-center gap-2">
                  <Play className="w-5 h-5" />
                  בדיקת פרומפט
                </h4>
                
                <div className="grid grid-cols-2 gap-4 mb-4">
                  {selectedPrompt.available_variables?.slice(0, 4).map((v) => (
                    <div key={v}>
                      <label className="label">{v}</label>
                      <input
                        type="text"
                        className="input"
                        value={testVariables[v] || ''}
                        onChange={(e) => setTestVariables({ ...testVariables, [v]: e.target.value })}
                        placeholder={`ערך ל-${v}...`}
                      />
                    </div>
                  ))}
                </div>
                
                <button
                  onClick={testPrompt}
                  disabled={testing}
                  className="btn btn-primary mb-4"
                >
                  {testing ? 'בודק...' : 'הרץ בדיקה'}
                </button>
                
                {testResult && (
                  <div className="bg-gray-50 rounded-lg p-4">
                    <label className="label">תוצאה</label>
                    <pre className="text-sm whitespace-pre-wrap">{testResult}</pre>
                  </div>
                )}
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
