'use client';

import React, { useState, useEffect } from 'react';

// Types
interface PostStrategy {
  id: number;
  name: string;
  slug: string;
  icon: string;
  description: string | null;
  system_prompt: string | null;
  post_template: string | null;
  example_post: string | null;
  is_active: boolean;
  sort_order: number;
  times_used: number;
  created_at: string;
}

interface DebugPromptResult {
  strategy_name: string;
  system_prompt: string;
  user_prompt: string;
  post_template: string | null;
  will_use_template: boolean;
  final_output_preview: string | null;
}

interface GenerateResult {
  strategy_name: string;
  generated_content: string | null;
  error: string | null;
  used_ai: boolean;
}

// API Base
const API_BASE = typeof window !== 'undefined' && window.location.hostname !== 'localhost' 
  ? '/api/strategies' 
  : 'http://localhost:8001/api/strategies';

export default function PostStrategiesPage() {
  const [strategies, setStrategies] = useState<PostStrategy[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editingStrategy, setEditingStrategy] = useState<PostStrategy | null>(null);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [previewResult, setPreviewResult] = useState<string | null>(null);
  const [debugResult, setDebugResult] = useState<DebugPromptResult | null>(null);
  const [generateResult, setGenerateResult] = useState<GenerateResult | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  
  // Form state
  const [formData, setFormData] = useState({
    name: '',
    slug: '',
    icon: '📝',
    description: '',
    system_prompt: '',
    post_template: '',
    example_post: '',
    sort_order: 0,
  });

  // Fetch strategies
  useEffect(() => {
    fetchStrategies();
  }, []);

  const fetchStrategies = async () => {
    try {
      setLoading(true);
      const res = await fetch(`${API_BASE}?active_only=false`);
      if (!res.ok) throw new Error('Failed to fetch strategies');
      const data = await res.json();
      setStrategies(data);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const res = await fetch(API_BASE, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData),
      });
      if (!res.ok) throw new Error('Failed to create strategy');
      await fetchStrategies();
      setShowCreateForm(false);
      setFormData({
        name: '',
        slug: '',
        icon: '📝',
        description: '',
        system_prompt: '',
        post_template: '',
        example_post: '',
        sort_order: 0,
      });
    } catch (err: any) {
      setError(err.message);
    }
  };

  const handleUpdate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingStrategy) return;
    
    try {
      const res = await fetch(`${API_BASE}/${editingStrategy.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData),
      });
      if (!res.ok) throw new Error('Failed to update strategy');
      await fetchStrategies();
      setEditingStrategy(null);
    } catch (err: any) {
      setError(err.message);
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm('האם למחוק את האסטרטגיה?')) return;
    
    try {
      const res = await fetch(`${API_BASE}/${id}`, { method: 'DELETE' });
      if (!res.ok) throw new Error('Failed to delete strategy');
      await fetchStrategies();
    } catch (err: any) {
      setError(err.message);
    }
  };

  const handlePreview = async (strategyId: number) => {
    try {
      const res = await fetch(`${API_BASE}/${strategyId}/preview`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          calculator_name: 'מחשבון משכנתא',
          calculator_url: 'https://loan-israel.co.il/mashkanta/',
        }),
      });
      if (!res.ok) throw new Error('Failed to generate preview');
      const data = await res.json();
      setPreviewResult(data.preview_text);
    } catch (err: any) {
      setError(err.message);
    }
  };

  const handleDebug = async (strategyId: number) => {
    try {
      const res = await fetch(`${API_BASE}/${strategyId}/debug-prompt`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          calculator_name: 'מחשבון משכנתא',
          calculator_url: 'https://loan-israel.co.il/mashkanta/',
          calculator_summary: 'מחשבון משכנתא חכם לחישוב החזר חודשי',
          group_name: 'נדל"ן ומשכנתאות ישראל'
        }),
      });
      if (!res.ok) throw new Error('Failed to get debug info');
      const data = await res.json();
      setDebugResult(data);
    } catch (err: any) {
      setError(err.message);
    }
  };

  const handleGenerateWithAI = async (strategyId: number) => {
    setIsGenerating(true);
    try {
      const res = await fetch(`${API_BASE}/${strategyId}/generate-with-ai`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          calculator_name: 'מחשבון משכנתא',
          calculator_url: 'https://loan-israel.co.il/mashkanta/',
          calculator_summary: 'מחשבון משכנתא חכם לחישוב החזר חודשי, ריביות, ולוח סילוקין',
          group_name: 'נדל"ן ומשכנתאות ישראל'
        }),
      });
      if (!res.ok) throw new Error('Failed to generate with AI');
      const data = await res.json();
      setGenerateResult(data);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setIsGenerating(false);
    }
  };

  const startEdit = (strategy: PostStrategy) => {
    setEditingStrategy(strategy);
    setFormData({
      name: strategy.name,
      slug: strategy.slug,
      icon: strategy.icon || '📝',
      description: strategy.description || '',
      system_prompt: strategy.system_prompt || '',
      post_template: strategy.post_template || '',
      example_post: strategy.example_post || '',
      sort_order: strategy.sort_order,
    });
  };

  if (loading) {
    return (
      <div className="p-8 text-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
        <p className="mt-4 text-gray-600">טוען אסטרטגיות...</p>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-6xl mx-auto" dir="rtl">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">📝 ניהול אסטרטגיות כתיבה</h1>
        <button
          onClick={() => setShowCreateForm(true)}
          className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
        >
          + אסטרטגיה חדשה
        </button>
      </div>

      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
          {error}
          <button onClick={() => setError(null)} className="float-left font-bold">×</button>
        </div>
      )}

      {/* Preview Modal */}
      {previewResult && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white p-6 rounded-lg shadow-xl w-full max-w-2xl">
            <h3 className="font-bold text-lg mb-4">👀 תצוגה מקדימה (מתבנית)</h3>
            <div className="bg-gray-50 p-4 rounded border whitespace-pre-wrap text-sm">
              {previewResult}
            </div>
            <button
              onClick={() => setPreviewResult(null)}
              className="mt-4 px-4 py-2 bg-gray-200 rounded hover:bg-gray-300"
            >
              סגור
            </button>
          </div>
        </div>
      )}

      {/* Debug Modal */}
      {debugResult && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 overflow-y-auto">
          <div className="bg-white p-6 rounded-lg shadow-xl w-full max-w-4xl m-4 max-h-[90vh] overflow-y-auto">
            <h3 className="font-bold text-lg mb-4">🔍 Debug: פרומפטים ל-{debugResult.strategy_name}</h3>
            
            <div className="space-y-4">
              <div className="bg-yellow-50 border border-yellow-200 p-3 rounded">
                <p className="text-sm font-semibold text-yellow-800 mb-1">
                  {debugResult.will_use_template ? '📝 ישתמש בתבנית (לא AI)' : '🤖 ישתמש ב-AI'}
                </p>
              </div>
              
              <div>
                <h4 className="font-semibold text-sm text-gray-700 mb-2">System Prompt (הנחיות למודל):</h4>
                <pre className="bg-blue-50 p-3 rounded border border-blue-200 text-xs whitespace-pre-wrap font-mono">
                  {debugResult.system_prompt}
                </pre>
              </div>
              
              <div>
                <h4 className="font-semibold text-sm text-gray-700 mb-2">User Prompt (בקשה למודל):</h4>
                <pre className="bg-green-50 p-3 rounded border border-green-200 text-xs whitespace-pre-wrap font-mono max-h-60 overflow-y-auto">
                  {debugResult.user_prompt}
                </pre>
              </div>
              
              {debugResult.post_template && (
                <div>
                  <h4 className="font-semibold text-sm text-gray-700 mb-2">תבנית פוסט (אם יש - עוקפת את ה-AI!):</h4>
                  <pre className="bg-purple-50 p-3 rounded border border-purple-200 text-xs whitespace-pre-wrap font-mono">
                    {debugResult.post_template}
                  </pre>
                </div>
              )}
              
              {debugResult.final_output_preview && (
                <div>
                  <h4 className="font-semibold text-sm text-gray-700 mb-2">תוצאה סופית (מתבנית):</h4>
                  <pre className="bg-gray-100 p-3 rounded border text-xs whitespace-pre-wrap">
                    {debugResult.final_output_preview}
                  </pre>
                </div>
              )}
            </div>
            
            <button
              onClick={() => setDebugResult(null)}
              className="mt-4 px-4 py-2 bg-gray-200 rounded hover:bg-gray-300"
            >
              סגור
            </button>
          </div>
        </div>
      )}

      {/* Generate Result Modal */}
      {generateResult && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white p-6 rounded-lg shadow-xl w-full max-w-3xl m-4">
            <h3 className="font-bold text-lg mb-4">
              🤖 תוצאת AI: {generateResult.strategy_name}
            </h3>
            
            {generateResult.error ? (
              <div className="bg-red-50 border border-red-200 p-4 rounded text-red-700">
                ❌ שגיאה: {generateResult.error}
              </div>
            ) : (
              <div className="bg-green-50 border border-green-200 p-4 rounded">
                <h4 className="font-semibold text-green-800 mb-2">✅ פוסט נוצר בהצלחה:</h4>
                <div className="bg-white p-4 rounded border whitespace-pre-wrap text-sm">
                  {generateResult.generated_content}
                </div>
              </div>
            )}
            
            <button
              onClick={() => setGenerateResult(null)}
              className="mt-4 px-4 py-2 bg-gray-200 rounded hover:bg-gray-300"
            >
              סגור
            </button>
          </div>
        </div>
      )}

      {/* Create/Edit Form Modal */}
      {(showCreateForm || editingStrategy) && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white p-6 rounded-lg shadow-xl w-full max-w-3xl max-h-[90vh] overflow-y-auto">
            <h3 className="font-bold text-lg mb-4">
              {editingStrategy ? `✏️ עריכת: ${editingStrategy.name}` : '➕ אסטרטגיה חדשה'}
            </h3>
            <form onSubmit={editingStrategy ? handleUpdate : handleCreate} className="space-y-4">
              {/* Helper: Available Variables */}
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                <h4 className="font-semibold text-blue-800 mb-2">📝 משתנים דינמיים זמינים:</h4>
                <p className="text-sm text-blue-700 mb-2">השתמש במשתנים הבאים ב-System Prompt ובתבנית הפוסט - הם יוחלפו אוטומטית:</p>
                <div className="grid grid-cols-2 gap-2 text-sm">
                  <div className="bg-white rounded p-2 border border-blue-100">
                    <code className="text-blue-600 font-mono">{'{group_name}'}</code>
                    <span className="text-gray-600 mr-2"> - שם הקבוצה</span>
                  </div>
                  <div className="bg-white rounded p-2 border border-blue-100">
                    <code className="text-blue-600 font-mono">{'{calculator_name}'}</code>
                    <span className="text-gray-600 mr-2"> - שם המחשבון</span>
                  </div>
                  <div className="bg-white rounded p-2 border border-blue-100">
                    <code className="text-blue-600 font-mono">{'{calculator_url}'}</code>
                    <span className="text-gray-600 mr-2"> - קישור למחשבון</span>
                  </div>
                  <div className="bg-white rounded p-2 border border-blue-100">
                    <code className="text-blue-600 font-mono">{'{calculator_summary}'}</code>
                    <span className="text-gray-600 mr-2"> - תיאור המחשבון</span>
                  </div>
                </div>
                <p className="text-xs text-blue-600 mt-2">
                  💡 דוגמה: &quot;כתוב פוסט אישי לקבוצה {'{group_name}'} על המחשבון {'{calculator_name}'}&quot;
                </p>
              </div>

              <div className="grid grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-1">שם</label>
                  <input
                    type="text"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    className="w-full border rounded px-3 py-2"
                    required
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">Slug</label>
                  <input
                    type="text"
                    value={formData.slug}
                    onChange={(e) => setFormData({ ...formData, slug: e.target.value })}
                    className="w-full border rounded px-3 py-2"
                    required
                    pattern="[a-z_]+"
                    placeholder="snake_case"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">אייקון</label>
                  <input
                    type="text"
                    value={formData.icon}
                    onChange={(e) => setFormData({ ...formData, icon: e.target.value })}
                    className="w-full border rounded px-3 py-2 text-2xl text-center"
                    maxLength={4}
                  />
                </div>
              </div>
              
              <div>
                <label className="block text-sm font-medium mb-1">תיאור</label>
                <input
                  type="text"
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  className="w-full border rounded px-3 py-2"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium mb-1">
                  System Prompt (הנחיות ל-AI) 
                  <span className="text-blue-500 text-xs mr-2">תומך במשתנים דינמיים</span>
                </label>
                <textarea
                  value={formData.system_prompt}
                  onChange={(e) => setFormData({ ...formData, system_prompt: e.target.value })}
                  className="w-full border rounded px-3 py-2 font-mono text-sm"
                  rows={4}
                  placeholder={`אתה אייל עובדיה. כתוב פוסט אישי לקבוצה "{group_name}" על המחשבון {calculator_name}...`}
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium mb-1">
                  תבנית פוסט / הנחיות נוספות
                  <span className="text-blue-500 text-xs mr-2">תומך במשתנים: {'{group_name}'}, {'{calculator_name}'}, {'{calculator_url}'}, {'{calculator_summary}'}</span>
                </label>
                <textarea
                  value={formData.post_template}
                  onChange={(e) => setFormData({ ...formData, post_template: e.target.value })}
                  className="w-full border rounded px-3 py-2"
                  rows={6}
                  placeholder="הנחיות נוספות לסגנון הפוסט..."
                />
              </div>
              
              <div className="flex gap-2">
                <button type="submit" className="px-4 py-2 bg-blue-600 text-white rounded">
                  {editingStrategy ? 'שמור' : 'צור'}
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setShowCreateForm(false);
                    setEditingStrategy(null);
                  }}
                  className="px-4 py-2 bg-gray-200 rounded"
                >
                  ביטול
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Strategies Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {strategies.map((strategy) => (
          <div
            key={strategy.id}
            className={`bg-white rounded-lg shadow p-4 border-r-4 ${
              strategy.is_active ? 'border-green-500' : 'border-gray-300'
            }`}
          >
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-2">
                <span className="text-2xl">{strategy.icon}</span>
                <div>
                  <h3 className="font-bold">{strategy.name}</h3>
                  <p className="text-xs text-gray-500">{strategy.slug}</p>
                </div>
              </div>
              <div className="flex gap-1">
                <button
                  onClick={() => handleDebug(strategy.id)}
                  className="p-1 text-purple-600 hover:bg-purple-50 rounded"
                  title="🔍 Debug - ראה פרומפטים"
                >
                  🔍
                </button>
                <button
                  onClick={() => handleGenerateWithAI(strategy.id)}
                  disabled={isGenerating}
                  className="p-1 text-green-600 hover:bg-green-50 rounded disabled:opacity-50"
                  title="🤖 צור עם AI"
                >
                  {isGenerating ? '⏳' : '🤖'}
                </button>
                <button
                  onClick={() => handlePreview(strategy.id)}
                  className="p-1 text-blue-600 hover:bg-blue-50 rounded"
                  title="תצוגה מקדימה (תבנית)"
                >
                  👁️
                </button>
                <button
                  onClick={() => startEdit(strategy)}
                  className="p-1 text-gray-600 hover:bg-gray-50 rounded"
                  title="עריכה"
                >
                  ✏️
                </button>
                <button
                  onClick={() => handleDelete(strategy.id)}
                  className="p-1 text-red-600 hover:bg-red-50 rounded"
                  title="מחיקה"
                >
                  🗑️
                </button>
              </div>
            </div>
            
            <p className="text-sm text-gray-600 mt-2">{strategy.description}</p>
            
            {/* סימון תבנית vs AI */}
            <div className="mt-2 flex gap-2 text-xs">
              {strategy.post_template ? (
                <span className="bg-purple-100 text-purple-700 px-2 py-0.5 rounded">
                  📝 תבנית קבועה
                </span>
              ) : (
                <span className="bg-green-100 text-green-700 px-2 py-0.5 rounded">
                  🤖 AI דינמי
                </span>
              )}
              {strategy.system_prompt && (
                <span className="bg-blue-100 text-blue-700 px-2 py-0.5 rounded">
                  💬 System Prompt
                </span>
              )}
            </div>
            
            <div className="mt-3 flex items-center justify-between text-xs text-gray-500">
              <span>נעשה שימוש: {strategy.times_used} פעמים</span>
              <span className={strategy.is_active ? 'text-green-600' : 'text-gray-400'}>
                {strategy.is_active ? '● פעיל' : '○ לא פעיל'}
              </span>
            </div>
          </div>
        ))}
      </div>

      {strategies.length === 0 && (
        <div className="text-center py-12 text-gray-500">
          <p className="text-4xl mb-4">📝</p>
          <p>אין אסטרטגיות עדיין</p>
          <button
            onClick={() => setShowCreateForm(true)}
            className="mt-4 px-4 py-2 bg-blue-600 text-white rounded"
          >
            צור אסטרטגיה ראשונה
          </button>
        </div>
      )}
    </div>
  );
}
