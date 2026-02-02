'use client';

import { useState, useEffect } from 'react';
import dynamic from 'next/dynamic';

// Dynamic import for react-quill (doesn't support SSR)
const ReactQuill = dynamic(() => import('react-quill'), { 
  ssr: false,
  loading: () => <div className="h-[300px] bg-gray-100 rounded-lg animate-pulse flex items-center justify-center text-gray-500">טוען עורך...</div>
});

const API_URL = '';

interface Template {
  id: number;
  name: string;
  subject: string;
  body_text: string;
  body_html?: string;
  category: string;
  is_active: boolean;
  variables: string[];
  usage_count: number;
  open_rate: number;
  click_rate: number;
  created_at: string;
}

interface Category {
  id: string;
  name: string;
  icon: string;
}

interface VariableGroup {
  key: string;
  label: string;
  example: string;
}

export default function TemplatesPage() {
  const [templates, setTemplates] = useState<Template[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [availableVariables, setAvailableVariables] = useState<Record<string, VariableGroup[]>>({});
  const [loading, setLoading] = useState(true);
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [editingTemplate, setEditingTemplate] = useState<Template | null>(null);
  const [isCreating, setIsCreating] = useState(false);
  const [previewData, setPreviewData] = useState<{subject: string; body_text: string} | null>(null);
  const [editorTab, setEditorTab] = useState<'text' | 'html' | 'preview'>('text');

  // Form state
  const [formData, setFormData] = useState({
    name: '',
    subject: '',
    body_text: '',
    body_html: '',
    category: 'first_contact'
  });

  useEffect(() => {
    loadData();
  }, [selectedCategory]);

  async function loadData() {
    setLoading(true);
    try {
      // Load templates
      let url = `${API_URL}/api/templates/`;
      if (selectedCategory !== 'all') {
        url += `?category=${selectedCategory}`;
      }
      const res = await fetch(url);
      const data = await res.json();
      setTemplates(data);

      // Load categories
      const catRes = await fetch(`${API_URL}/api/templates/categories`);
      const catData = await catRes.json();
      setCategories(catData);

      // Load variables
      const varRes = await fetch(`${API_URL}/api/templates/variables`);
      const varData = await varRes.json();
      setAvailableVariables(varData);
    } catch (error) {
      console.error('Error loading data:', error);
    }
    setLoading(false);
  }

  function startEditing(template: Template) {
    setEditingTemplate(template);
    setFormData({
      name: template.name,
      subject: template.subject,
      body_text: template.body_text,
      body_html: template.body_html || '',
      category: template.category
    });
    setIsCreating(false);
    setEditorTab('text');
  }

  function startCreating() {
    setEditingTemplate(null);
    setFormData({
      name: '',
      subject: '',
      body_text: '',
      body_html: '',
      category: 'first_contact'
    });
    setIsCreating(true);
    setEditorTab('text');
  }

  function cancelEditing() {
    setEditingTemplate(null);
    setIsCreating(false);
    setFormData({
      name: '',
      subject: '',
      body_text: '',
      body_html: '',
      category: 'first_contact'
    });
    setPreviewData(null);
  }

  async function saveTemplate() {
    try {
      if (editingTemplate) {
        // Update
        const res = await fetch(`${API_URL}/api/templates/${editingTemplate.id}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(formData)
        });
        if (res.ok) {
          loadData();
          cancelEditing();
        }
      } else {
        // Create
        const res = await fetch(`${API_URL}/api/templates/`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(formData)
        });
        if (res.ok) {
          loadData();
          cancelEditing();
        }
      }
    } catch (error) {
      console.error('Error saving:', error);
    }
  }

  async function deleteTemplate(id: number) {
    if (!confirm('האם למחוק את התבנית?')) return;
    
    try {
      const res = await fetch(`${API_URL}/api/templates/${id}`, {
        method: 'DELETE'
      });
      if (res.ok) {
        loadData();
      }
    } catch (error) {
      console.error('Error deleting:', error);
    }
  }

  async function duplicateTemplate(id: number) {
    try {
      const res = await fetch(`${API_URL}/api/templates/${id}/duplicate`, {
        method: 'POST'
      });
      if (res.ok) {
        loadData();
      }
    } catch (error) {
      console.error('Error duplicating:', error);
    }
  }

  async function previewTemplate() {
    if (!editingTemplate) return;
    
    try {
      const res = await fetch(`${API_URL}/api/templates/${editingTemplate.id}/preview`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ variables: {} })
      });
      if (res.ok) {
        const data = await res.json();
        setPreviewData(data);
      }
    } catch (error) {
      console.error('Error previewing:', error);
    }
  }

  function insertVariable(variable: string) {
    const varText = `{{${variable}}}`;
    setFormData(prev => ({
      ...prev,
      body_text: prev.body_text + varText
    }));
  }

  function getCategoryName(id: string) {
    return categories.find(c => c.id === id)?.name || id;
  }

  function getCategoryIcon(id: string) {
    return categories.find(c => c.id === id)?.icon || '📧';
  }

  return (
    <div className="p-6 max-w-7xl mx-auto" dir="rtl">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold">📝 תבניות מייל</h1>
        <button
          onClick={startCreating}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          + תבנית חדשה
        </button>
      </div>

      {/* Category Filter */}
      <div className="flex gap-2 mb-6 flex-wrap">
        <button
          onClick={() => setSelectedCategory('all')}
          className={`px-4 py-2 rounded-lg transition ${
            selectedCategory === 'all'
              ? 'bg-blue-600 text-white'
              : 'bg-gray-100 hover:bg-gray-200'
          }`}
        >
          הכל
        </button>
        {categories.map(cat => (
          <button
            key={cat.id}
            onClick={() => setSelectedCategory(cat.id)}
            className={`px-4 py-2 rounded-lg transition ${
              selectedCategory === cat.id
                ? 'bg-blue-600 text-white'
                : 'bg-gray-100 hover:bg-gray-200'
            }`}
          >
            {cat.icon} {cat.name}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="text-center py-12">
          <div className="animate-spin h-8 w-8 border-4 border-blue-500 border-t-transparent rounded-full mx-auto mb-4"></div>
        </div>
      ) : (
        <>
          {/* Templates List */}
          {!isCreating && !editingTemplate && (
            <div className="bg-white rounded-lg shadow overflow-hidden">
              {templates.length === 0 ? (
                <div className="text-center py-12 text-gray-500">
                  <p className="text-lg mb-4">אין תבניות עדיין</p>
                  <button
                    onClick={startCreating}
                    className="px-4 py-2 bg-blue-600 text-white rounded-lg"
                  >
                    צור תבנית ראשונה
                  </button>
                </div>
              ) : (
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">שם</th>
                      <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">קטגוריה</th>
                      <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">שימושים</th>
                      <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">פתיחות</th>
                      <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">קליקים</th>
                      <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">פעולות</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-200">
                    {templates.map(template => (
                      <tr key={template.id} className="hover:bg-gray-50">
                        <td className="px-4 py-3">
                          <div className="font-medium">{template.name}</div>
                          <div className="text-sm text-gray-500">{template.subject}</div>
                        </td>
                        <td className="px-4 py-3">
                          <span className="px-2 py-1 text-xs bg-gray-100 rounded-full">
                            {getCategoryIcon(template.category)} {getCategoryName(template.category)}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-sm">{template.usage_count}</td>
                        <td className="px-4 py-3 text-sm">{template.open_rate.toFixed(1)}%</td>
                        <td className="px-4 py-3 text-sm">{template.click_rate.toFixed(1)}%</td>
                        <td className="px-4 py-3">
                          <div className="flex gap-2">
                            <button
                              onClick={() => startEditing(template)}
                              className="text-blue-600 hover:text-blue-800"
                            >
                              ✏️
                            </button>
                            <button
                              onClick={() => duplicateTemplate(template.id)}
                              className="text-gray-600 hover:text-gray-800"
                            >
                              📋
                            </button>
                            <button
                              onClick={() => deleteTemplate(template.id)}
                              className="text-red-600 hover:text-red-800"
                            >
                              🗑️
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          )}

          {/* Template Editor */}
          {(isCreating || editingTemplate) && (
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-xl font-bold mb-6">
                {isCreating ? 'יצירת תבנית חדשה' : 'עריכת תבנית'}
              </h2>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {/* Editor Column */}
                <div className="md:col-span-2 space-y-4">
                  <div>
                    <label className="block text-sm font-medium mb-1">שם התבנית</label>
                    <input
                      type="text"
                      value={formData.name}
                      onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
                      className="w-full p-2 border rounded-lg"
                      placeholder="הצעה למחשבון..."
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium mb-1">קטגוריה</label>
                    <select
                      value={formData.category}
                      onChange={(e) => setFormData(prev => ({ ...prev, category: e.target.value }))}
                      className="w-full p-2 border rounded-lg"
                    >
                      {categories.map(cat => (
                        <option key={cat.id} value={cat.id}>
                          {cat.icon} {cat.name}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-medium mb-1">נושא המייל</label>
                    <input
                      type="text"
                      value={formData.subject}
                      onChange={(e) => setFormData(prev => ({ ...prev, subject: e.target.value }))}
                      className="w-full p-2 border rounded-lg"
                      placeholder="הזדמנות ל{{site_name}}..."
                    />
                  </div>

                  {/* Editor Tabs */}
                  <div>
                    <div className="flex border-b mb-2">
                      <button
                        onClick={() => setEditorTab('text')}
                        className={`px-4 py-2 font-medium transition ${
                          editorTab === 'text'
                            ? 'border-b-2 border-blue-600 text-blue-600'
                            : 'text-gray-500 hover:text-gray-700'
                        }`}
                      >
                        📝 טקסט
                      </button>
                      <button
                        onClick={() => setEditorTab('html')}
                        className={`px-4 py-2 font-medium transition ${
                          editorTab === 'html'
                            ? 'border-b-2 border-blue-600 text-blue-600'
                            : 'text-gray-500 hover:text-gray-700'
                        }`}
                      >
                        🎨 עורך ויזואלי
                      </button>
                      <button
                        onClick={() => setEditorTab('preview')}
                        className={`px-4 py-2 font-medium transition ${
                          editorTab === 'preview'
                            ? 'border-b-2 border-blue-600 text-blue-600'
                            : 'text-gray-500 hover:text-gray-700'
                        }`}
                      >
                        👁️ תצוגה מקדימה
                      </button>
                    </div>

                    {editorTab === 'text' && (
                      <div>
                        <div className="text-xs text-gray-500 mb-2">
                          💡 טקסט פשוט - יומר אוטומטית ל-HTML בעת השליחה
                        </div>
                        <textarea
                          value={formData.body_text}
                          onChange={(e) => setFormData(prev => ({ ...prev, body_text: e.target.value }))}
                          className="w-full p-3 border rounded-lg font-mono text-sm"
                          rows={14}
                          dir="rtl"
                          placeholder="שלום {{contact_name}},&#10;&#10;ראיתי את האתר שלכם {{site_name}}..."
                        />
                      </div>
                    )}

                    {editorTab === 'html' && (
                      <div>
                        <div className="text-xs text-gray-500 mb-2">
                          🎨 עורך ויזואלי - עצב את ההודעה עם בולד, צבעים, קישורים ועוד
                        </div>
                        <ReactQuill
                          theme="snow"
                          value={formData.body_html || formData.body_text}
                          onChange={(content) => setFormData(prev => ({ 
                            ...prev, 
                            body_html: content,
                            body_text: content.replace(/<[^>]*>/g, '').replace(/&nbsp;/g, ' ')
                          }))}
                          modules={{
                            toolbar: [
                              [{ 'header': [1, 2, 3, false] }],
                              ['bold', 'italic', 'underline', 'strike'],
                              [{ 'color': [] }, { 'background': [] }],
                              [{ 'list': 'ordered'}, { 'list': 'bullet' }],
                              [{ 'align': [] }],
                              ['link'],
                              ['clean']
                            ]
                          }}
                          placeholder="כתוב את ההודעה שלך כאן..."
                        />
                        <div className="mt-3 p-3 bg-yellow-50 border border-yellow-200 rounded-lg text-sm">
                          <strong>💡 טיפ:</strong> להוסיף משתנה, פשוט כתוב: {'{'}{'{'}<span className="text-blue-600">domain</span>{'}'}{'}'}
                          <br />
                          משתנים זמינים: domain, calculator_name, contact_name, domains_only, calculators_list
                        </div>
                      </div>
                    )}

                    {editorTab === 'preview' && (
                      <div className="border rounded-lg bg-white min-h-[300px]">
                        <div className="bg-gray-100 px-4 py-2 border-b text-sm text-gray-600">
                          📧 תצוגה מקדימה של המייל (עם נתונים לדוגמה)
                        </div>
                        <div className="p-4">
                          <div className="mb-4 pb-4 border-b">
                            <span className="text-gray-500">נושא:</span>
                            <span className="font-medium mr-2">
                              {(formData.subject || '(ללא נושא)')
                                .replace(/\{\{site_name\}\}/g, 'משכנתא פלוס')
                                .replace(/\{\{calculator_name\}\}/g, 'מחשבון משכנתא')
                              }
                            </span>
                          </div>
                          {(() => {
                            // Sample data for preview
                            const sampleData: Record<string, string> = {
                              'domain': 'example-finance.co.il',
                              'domains_only': '• example-finance.co.il\n• loan-center.co.il\n• my-mortgage.co.il',
                              'domains_list': '• example-finance.co.il - מחשבון משכנתא\n• loan-center.co.il - מחשבון הלוואות\n• my-mortgage.co.il - מחשבון ריבית',
                              'calculators_list': '• מחשבון משכנתא\n• מחשבון הלוואות\n• מחשבון ריבית אפקטיבית',
                              'site_name': 'משכנתא פלוס',
                              'contact_name': 'יוסי כהן',
                              'calculator_name': 'מחשבון משכנתא',
                              'my_name': 'אייל',
                              'my_company': 'רק תבקש',
                              'my_phone': '050-1234567',
                              'today': new Date().toLocaleDateString('he-IL'),
                            };
                            
                            let content = formData.body_html || formData.body_text || '(ללא תוכן)';
                            
                            // Replace all variables
                            Object.entries(sampleData).forEach(([key, value]) => {
                              content = content.replace(new RegExp(`\\{\\{${key}\\}\\}`, 'g'), value);
                            });
                            
                            if (formData.body_html) {
                              return (
                                <div 
                                  className="prose prose-sm max-w-none"
                                  dir="rtl"
                                  dangerouslySetInnerHTML={{ __html: content }}
                                />
                              );
                            }
                            return (
                              <div className="whitespace-pre-wrap" dir="rtl">
                                {content}
                              </div>
                            );
                          })()}
                        </div>
                      </div>
                    )}
                  </div>

                  <div className="flex gap-2">
                    <button
                      onClick={cancelEditing}
                      className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg"
                    >
                      ביטול
                    </button>
                    <button
                      onClick={previewTemplate}
                      disabled={!editingTemplate}
                      className="px-4 py-2 text-blue-600 hover:bg-blue-50 rounded-lg disabled:opacity-50"
                    >
                      👁️ תצוגה מקדימה
                    </button>
                    <button
                      onClick={saveTemplate}
                      className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                    >
                      💾 שמור
                    </button>
                  </div>
                </div>

                {/* Variables Panel */}
                <div className="bg-gray-50 rounded-lg p-4">
                  <h3 className="font-medium mb-4">הוספת משתנה</h3>
                  
                  {Object.entries(availableVariables).map(([group, vars]) => (
                    <div key={group} className="mb-4">
                      <p className="text-sm text-gray-500 mb-2">
                        {group === 'lead' && '📋 פרטי הליד'}
                        {group === 'contact' && '👤 איש קשר'}
                        {group === 'calculator' && '🔢 מחשבון'}
                        {group === 'date' && '📅 תאריכים'}
                        {group === 'sender' && '✉️ השולח'}
                      </p>
                      <div className="flex flex-wrap gap-1">
                        {vars.map((v: VariableGroup) => (
                          <button
                            key={v.key}
                            onClick={() => insertVariable(v.key)}
                            className="px-2 py-1 text-xs bg-white border rounded hover:bg-blue-50 hover:border-blue-300"
                            title={v.example}
                          >
                            {v.label}
                          </button>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Preview Panel */}
              {previewData && (
                <div className="mt-6 border-t pt-6">
                  <h3 className="font-medium mb-4">תצוגה מקדימה</h3>
                  <div className="bg-gray-50 rounded-lg p-4">
                    <p className="font-medium mb-2">נושא: {previewData.subject}</p>
                    <div className="bg-white p-4 rounded border whitespace-pre-wrap">
                      {previewData.body_text}
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}
