'use client';

import React, { useState, useEffect, useCallback } from 'react';

const API = typeof window !== 'undefined' && window.location.hostname !== 'localhost' ? '' : 'http://localhost:8001';

// ============================================================
//  Types
// ============================================================

interface Actor {
  id: number;
  name: string;
  url: string;
  post_count: number;
}

interface Category {
  id: number;
  name: string;
  is_alert_worthy?: boolean;
}

interface Post {
  id: number;
  post_url: string;
  description: string;
  posted_at: string | null;
  group_name: string | null;
  group_url: string | null;
  area: string | null;
  status: string;
  ai_reply: string | null;
  ai_confidence: number | null;
  ai_reasoning: string | null;
  whatsapp_sent: boolean;
  whatsapp_sent_at: string | null;
  whatsapp_replied: boolean;
  whatsapp_replied_at: string | null;
  created_at: string | null;
  actor: Actor | null;
  category: Category | null;
}

interface LeadArea {
  id: number;
  name: string;
  is_reply_enabled: boolean;
  is_whatsapp_enabled: boolean;
  is_visible: boolean;
}

interface Stats {
  total: number;
  notified: number;
  replied: number;
  pending_classification: number;
  ignored: number;
  reply_rate: number;
  by_category: { name: string; count: number }[];
}

interface FullCategory {
  id: number;
  name: string;
  description: string | null;
  classification_prompt: string;
  reply_prompt: string | null;
  whatsapp_phone: string | null;
  whatsapp_name: string | null;
  is_alert_worthy: boolean;
  auto_reply_enabled: boolean;
  is_active: boolean;
}

// ============================================================
//  Helpers
// ============================================================

const STATUS_LABELS: Record<string, { label: string; color: string }> = {
  new: { label: 'ממתין לסיווג', color: 'bg-yellow-100 text-yellow-800' },
  classified: { label: 'סווג', color: 'bg-blue-100 text-blue-800' },
  notified: { label: 'נשלחה התראה', color: 'bg-purple-100 text-purple-800' },
  replied: { label: 'טופל', color: 'bg-green-100 text-green-800' },
  ignored: { label: 'לא רלוונטי', color: 'bg-gray-100 text-gray-500' },
};

function truncate(text: string, max = 180) {
  return text.length > max ? text.slice(0, max) + '...' : text;
}

function fmtDate(iso: string | null) {
  if (!iso) return '—';
  return new Date(iso).toLocaleString('he-IL', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' });
}

// ============================================================
//  Main Component
// ============================================================

export default function LeadHunterPage() {
  const [posts, setPosts] = useState<Post[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [categories, setCategories] = useState<FullCategory[]>([]);
  const [areas, setAreas] = useState<LeadArea[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);

  // Filters
  const [filterStatus, setFilterStatus] = useState('');
  const [filterCategory, setFilterCategory] = useState('');
  const [filterArea, setFilterArea] = useState('');
  const [filterReplied, setFilterReplied] = useState('');
  const [offset, setOffset] = useState(0);
  const LIMIT = 50;

  // UI State
  const [expandedPost, setExpandedPost] = useState<number | null>(null);
  const [copiedId, setCopiedId] = useState<number | null>(null);
  const [activeTab, setActiveTab] = useState<'posts' | 'categories' | 'areas'>('posts');
  const [editingCategory, setEditingCategory] = useState<FullCategory | null>(null);
  const [savingCategory, setSavingCategory] = useState(false);
  const [regenerating, setRegenerating] = useState<number | null>(null);
  const [savingArea, setSavingArea] = useState<number | null>(null);

  // ============================================================
  //  Data fetching
  // ============================================================

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${API}/api/lead-hunter/stats`);
      if (res.ok) setStats(await res.json());
    } catch {}
  }, []);

  const fetchCategories = useCallback(async () => {
    try {
      const res = await fetch(`${API}/api/lead-hunter/categories`);
      if (res.ok) setCategories(await res.json());
    } catch {}
  }, []);

  const fetchAreas = useCallback(async () => {
    try {
      const res = await fetch(`${API}/api/lead-hunter/areas`);
      if (res.ok) setAreas(await res.json());
    } catch {}
  }, []);

  const fetchPosts = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (filterStatus) params.set('status', filterStatus);
      if (filterCategory) params.set('category_id', filterCategory);
      if (filterArea) params.set('area', filterArea);
      if (filterReplied === 'replied') params.set('whatsapp_replied', 'true');
      if (filterReplied === 'pending') params.set('whatsapp_replied', 'false');
      params.set('limit', String(LIMIT));
      params.set('offset', String(offset));

      const res = await fetch(`${API}/api/lead-hunter/posts?${params}`);
      if (res.ok) {
        const data = await res.json();
        setPosts(data.posts);
        setTotal(data.total);
      }
    } finally {
      setLoading(false);
    }
  }, [filterStatus, filterCategory, filterArea, filterReplied, offset]);

  useEffect(() => {
    fetchStats();
    fetchCategories();
    fetchAreas();
  }, [fetchStats, fetchCategories, fetchAreas]);

  useEffect(() => {
    fetchPosts();
  }, [fetchPosts]);

  // Auto-refresh every 30s
  useEffect(() => {
    const interval = setInterval(() => {
      fetchStats();
      fetchPosts();
    }, 30_000);
    return () => clearInterval(interval);
  }, [fetchStats, fetchPosts]);

  // ============================================================
  //  Actions
  // ============================================================

  const markReplied = async (postId: number) => {
    await fetch(`${API}/api/lead-hunter/posts/${postId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ whatsapp_replied: true }),
    });
    fetchPosts();
    fetchStats();
  };

  const ignorePost = async (postId: number) => {
    if (!confirm('לסמן כלא רלוונטי?')) return;
    await fetch(`${API}/api/lead-hunter/posts/${postId}/ignore`, { method: 'POST' });
    fetchPosts();
    fetchStats();
  };

  const changeCategory = async (postId: number, newCategoryId: string) => {
    await fetch(`${API}/api/lead-hunter/posts/${postId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ category_id: parseInt(newCategoryId) }),
    });
    fetchPosts();
  };

  const copyReply = (post: Post) => {
    if (!post.ai_reply) return;
    navigator.clipboard.writeText(post.ai_reply);
    setCopiedId(post.id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const regenerateReply = async (postId: number) => {
    setRegenerating(postId);
    try {
      await fetch(`${API}/api/lead-hunter/posts/${postId}/regenerate-reply`, { method: 'POST' });
      fetchPosts();
    } finally {
      setRegenerating(null);
    }
  };

  const updateArea = async (areaId: number, field: keyof LeadArea, value: boolean) => {
    setSavingArea(areaId);
    try {
      await fetch(`${API}/api/lead-hunter/areas/${areaId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ [field]: value }),
      });
      setAreas((prev) => prev.map((a) => a.id === areaId ? { ...a, [field]: value } : a));
    } finally {
      setSavingArea(null);
    }
  };

  const saveCategory = async () => {
    if (!editingCategory) return;
    setSavingCategory(true);
    try {
      await fetch(`${API}/api/lead-hunter/categories/${editingCategory.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          whatsapp_phone: editingCategory.whatsapp_phone,
          whatsapp_name: editingCategory.whatsapp_name,
          reply_prompt: editingCategory.reply_prompt,
          classification_prompt: editingCategory.classification_prompt,
          is_alert_worthy: editingCategory.is_alert_worthy,
        }),
      });
      fetchCategories();
      setEditingCategory(null);
    } finally {
      setSavingCategory(false);
    }
  };

  // ============================================================
  //  Render
  // ============================================================

  return (
    <div className="min-h-screen bg-gray-50 p-4 md:p-6" dir="rtl">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">🎯 Lead Hunter AI</h1>
        <p className="text-gray-500 text-sm mt-1">פוסטים נכנסים מפייסבוק · סיווג AI · התראות WhatsApp</p>
      </div>

      {/* Stats Bar */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-6">
          {[
            { label: 'סה"כ פוסטים', value: stats.total, color: 'text-gray-800' },
            { label: 'התראות נשלחו', value: stats.notified, color: 'text-purple-700' },
            { label: 'ענו / טופלו', value: stats.replied, color: 'text-green-700' },
            { label: 'שיעור מענה', value: `${stats.reply_rate}%`, color: 'text-blue-700' },
            { label: 'ממתינים לסיווג', value: stats.pending_classification, color: 'text-yellow-700' },
          ].map((s) => (
            <div key={s.label} className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
              <div className={`text-2xl font-bold ${s.color}`}>{s.value}</div>
              <div className="text-xs text-gray-500 mt-1">{s.label}</div>
            </div>
          ))}
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-2 mb-4">
        <button
          onClick={() => setActiveTab('posts')}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
            activeTab === 'posts' ? 'bg-blue-600 text-white' : 'bg-white text-gray-600 border border-gray-200 hover:bg-gray-50'
          }`}
        >
          📋 פוסטים
        </button>
        <button
          onClick={() => setActiveTab('categories')}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
            activeTab === 'categories' ? 'bg-blue-600 text-white' : 'bg-white text-gray-600 border border-gray-200 hover:bg-gray-50'
          }`}
        >
          🏷️ קטגוריות
        </button>
        <button
          onClick={() => setActiveTab('areas')}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
            activeTab === 'areas' ? 'bg-blue-600 text-white' : 'bg-white text-gray-600 border border-gray-200 hover:bg-gray-50'
          }`}
        >
          🗺️ אזורים
        </button>
      </div>

      {/* ========== Posts Tab ========== */}
      {activeTab === 'posts' && (
        <>
          {/* Filters */}
          <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100 mb-4 flex flex-wrap gap-3 items-center">
            <select
              value={filterStatus}
              onChange={(e) => { setFilterStatus(e.target.value); setOffset(0); }}
              className="border border-gray-200 rounded-lg px-3 py-2 text-sm"
            >
              <option value="">כל הסטטוסים</option>
              {Object.entries(STATUS_LABELS).map(([v, { label }]) => (
                <option key={v} value={v}>{label}</option>
              ))}
            </select>

            <select
              value={filterCategory}
              onChange={(e) => { setFilterCategory(e.target.value); setOffset(0); }}
              className="border border-gray-200 rounded-lg px-3 py-2 text-sm"
            >
              <option value="">כל הקטגוריות</option>
              {categories.map((c) => (
                <option key={c.id} value={c.id}>{c.name}</option>
              ))}
            </select>

            <select
              value={filterArea}
              onChange={(e) => { setFilterArea(e.target.value); setOffset(0); }}
              className="border border-gray-200 rounded-lg px-3 py-2 text-sm"
            >
              <option value="">כל האזורים</option>
              {areas.map((a) => (
                <option key={a.id} value={a.name}>{a.name}</option>
              ))}
            </select>

            <select
              value={filterReplied}
              onChange={(e) => { setFilterReplied(e.target.value); setOffset(0); }}
              className="border border-gray-200 rounded-lg px-3 py-2 text-sm"
            >
              <option value="">כל המצבים</option>
              <option value="pending">ממתין למענה</option>
              <option value="replied">טופל</option>
            </select>

            <span className="text-sm text-gray-400 mr-auto">{total} תוצאות</span>

            <button
              onClick={() => { fetchPosts(); fetchStats(); }}
              className="px-3 py-2 bg-blue-50 text-blue-700 rounded-lg text-sm hover:bg-blue-100"
            >
              🔄 רענן
            </button>
          </div>

          {/* Posts List */}
          {loading ? (
            <div className="text-center py-12 text-gray-400">טוען...</div>
          ) : posts.length === 0 ? (
            <div className="text-center py-12 text-gray-400">אין פוסטים</div>
          ) : (
            <div className="space-y-3">
              {posts.map((post) => {
                const isExpanded = expandedPost === post.id;
                const statusInfo = STATUS_LABELS[post.status] || { label: post.status, color: 'bg-gray-100 text-gray-600' };

                return (
                  <div key={post.id} className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
                    {/* Post Header */}
                    <div className="p-4">
                      <div className="flex items-start justify-between gap-3">
                        {/* Left: actor + status */}
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="font-semibold text-gray-800 text-sm">
                            👤 {post.actor?.name || 'לא ידוע'}
                          </span>
                          {post.actor && post.actor.post_count > 1 && (
                            <span className="bg-orange-100 text-orange-700 text-xs px-2 py-0.5 rounded-full font-medium">
                              ⚠️ {post.actor.post_count} פוסטים
                            </span>
                          )}
                          <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${statusInfo.color}`}>
                            {statusInfo.label}
                          </span>
                          {post.category && (
                            <span className="bg-blue-50 text-blue-700 text-xs px-2 py-0.5 rounded-full">
                              {post.category.name}
                            </span>
                          )}
                          {post.area && post.area !== 'לא ידוע' && (
                            <span className="bg-emerald-50 text-emerald-700 text-xs px-2 py-0.5 rounded-full">
                              🗺️ {post.area}
                            </span>
                          )}
                        </div>

                        {/* Right: date + WhatsApp indicators */}
                        <div className="flex items-center gap-2 text-xs text-gray-400 flex-shrink-0">
                          {post.whatsapp_sent && (
                            <span title={`נשלח: ${fmtDate(post.whatsapp_sent_at)}`}>
                              📱 {post.whatsapp_replied ? '✅' : '⏳'}
                            </span>
                          )}
                          <span>{fmtDate(post.created_at)}</span>
                        </div>
                      </div>

                      {/* Description */}
                      <p className="text-sm text-gray-700 mt-2 leading-relaxed">
                        {isExpanded ? post.description : truncate(post.description, 200)}
                      </p>

                      {post.description.length > 200 && (
                        <button
                          onClick={() => setExpandedPost(isExpanded ? null : post.id)}
                          className="text-xs text-blue-500 mt-1 hover:underline"
                        >
                          {isExpanded ? 'פחות ▲' : 'עוד ▼'}
                        </button>
                      )}

                      {/* Group + URL + confidence */}
                      <div className="flex items-center gap-3 mt-2 text-xs text-gray-400 flex-wrap">
                        {post.group_name && (
                          <span className="flex items-center gap-1">
                            📍{' '}
                            {post.group_url ? (
                              <a href={post.group_url} target="_blank" rel="noreferrer" className="text-blue-500 hover:underline font-medium">
                                {post.group_name}
                              </a>
                            ) : (
                              <span className="text-gray-600 font-medium">{post.group_name}</span>
                            )}
                          </span>
                        )}
                        <a
                          href={post.post_url}
                          target="_blank"
                          rel="noreferrer"
                          className="flex items-center gap-1 text-blue-500 hover:text-blue-700 hover:underline font-medium"
                        >
                          🔗 לינק לפוסט
                        </a>
                        {post.ai_confidence != null && (
                          <span>🤖 {Math.round(post.ai_confidence * 100)}% ביטחון</span>
                        )}
                      </div>
                    </div>

                    {/* AI Reply section */}
                    {post.ai_reply && (
                      <div className="border-t border-gray-100 px-4 py-3 bg-green-50">
                        <p className="text-xs font-medium text-green-700 mb-1">💬 תגובה מוצעת:</p>
                        <p className="text-sm text-gray-700 leading-relaxed">{post.ai_reply}</p>
                      </div>
                    )}

                    {/* Action buttons */}
                    <div className="border-t border-gray-100 px-4 py-3 flex flex-wrap gap-2 items-center bg-gray-50">
                      {/* Category selector */}
                      <select
                        value={post.category?.id || ''}
                        onChange={(e) => changeCategory(post.id, e.target.value)}
                        className="text-xs border border-gray-200 rounded-lg px-2 py-1.5 bg-white"
                      >
                        <option value="">בחר קטגוריה</option>
                        {categories.map((c) => (
                          <option key={c.id} value={c.id}>{c.name}</option>
                        ))}
                      </select>

                      {/* Copy reply */}
                      {post.ai_reply && (
                        <button
                          onClick={() => copyReply(post)}
                          className="text-xs px-3 py-1.5 bg-white border border-gray-200 rounded-lg hover:bg-gray-100"
                        >
                          {copiedId === post.id ? '✅ הועתק!' : '📋 העתק תגובה'}
                        </button>
                      )}

                      {/* Regenerate */}
                      {post.category && (
                        <button
                          onClick={() => regenerateReply(post.id)}
                          disabled={regenerating === post.id}
                          className="text-xs px-3 py-1.5 bg-white border border-gray-200 rounded-lg hover:bg-gray-100 disabled:opacity-50"
                        >
                          {regenerating === post.id ? '⏳...' : '💡 ייצר תגובה'}
                        </button>
                      )}

                      {/* Links */}
                      <a
                        href={post.post_url}
                        target="_blank"
                        rel="noreferrer"
                        className="text-xs px-3 py-1.5 bg-white border border-gray-200 rounded-lg hover:bg-gray-100"
                      >
                        🔗 לפוסט
                      </a>

                      {post.actor?.url && (
                        <a
                          href={post.actor.url}
                          target="_blank"
                          rel="noreferrer"
                          className="text-xs px-3 py-1.5 bg-white border border-gray-200 rounded-lg hover:bg-gray-100"
                        >
                          👤 פרופיל
                        </a>
                      )}

                      {/* Mark replied */}
                      {post.whatsapp_sent && !post.whatsapp_replied && (
                        <button
                          onClick={() => markReplied(post.id)}
                          className="text-xs px-3 py-1.5 bg-green-600 text-white rounded-lg hover:bg-green-700"
                        >
                          ✅ סמן כטופל
                        </button>
                      )}

                      {/* Ignore */}
                      {post.status !== 'ignored' && (
                        <button
                          onClick={() => ignorePost(post.id)}
                          className="text-xs px-3 py-1.5 bg-white border border-red-200 text-red-500 rounded-lg hover:bg-red-50 mr-auto"
                        >
                          🚫 לא רלוונטי
                        </button>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          {/* Pagination */}
          {total > LIMIT && (
            <div className="flex justify-center gap-3 mt-6">
              <button
                onClick={() => setOffset(Math.max(0, offset - LIMIT))}
                disabled={offset === 0}
                className="px-4 py-2 bg-white border border-gray-200 rounded-lg text-sm disabled:opacity-40 hover:bg-gray-50"
              >
                → הקודם
              </button>
              <span className="text-sm text-gray-500 self-center">
                {offset + 1}–{Math.min(offset + LIMIT, total)} מתוך {total}
              </span>
              <button
                onClick={() => setOffset(offset + LIMIT)}
                disabled={offset + LIMIT >= total}
                className="px-4 py-2 bg-white border border-gray-200 rounded-lg text-sm disabled:opacity-40 hover:bg-gray-50"
              >
                ← הבא
              </button>
            </div>
          )}
        </>
      )}

      {/* ========== Areas Tab ========== */}
      {activeTab === 'areas' && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
          <div className="px-4 py-3 border-b border-gray-100 bg-gray-50">
            <p className="text-sm text-gray-500">שליטה על מה שה-AI עושה עם פוסטים מכל אזור</p>
          </div>
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100">
                <th className="text-right px-4 py-3 font-medium text-gray-700">אזור</th>
                <th className="text-center px-4 py-3 font-medium text-gray-700">ייצר תגובת AI</th>
                <th className="text-center px-4 py-3 font-medium text-gray-700">שלח WhatsApp</th>
                <th className="text-center px-4 py-3 font-medium text-gray-700">הצג בדשבורד</th>
              </tr>
            </thead>
            <tbody>
              {areas.map((area) => (
                <tr key={area.id} className="border-b border-gray-50 hover:bg-gray-50 transition-colors">
                  <td className="px-4 py-3 font-medium text-gray-800">🗺️ {area.name}</td>
                  {(['is_reply_enabled', 'is_whatsapp_enabled', 'is_visible'] as const).map((field) => (
                    <td key={field} className="px-4 py-3 text-center">
                      <button
                        onClick={() => updateArea(area.id, field, !area[field])}
                        disabled={savingArea === area.id}
                        className={`w-12 h-6 rounded-full transition-colors relative disabled:opacity-50 ${
                          area[field] ? 'bg-green-500' : 'bg-gray-200'
                        }`}
                      >
                        <span
                          className={`absolute top-0.5 w-5 h-5 bg-white rounded-full shadow transition-all ${
                            area[field] ? 'right-0.5' : 'left-0.5'
                          }`}
                        />
                      </button>
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
          <div className="px-4 py-3 bg-gray-50 border-t border-gray-100 text-xs text-gray-400 space-y-1">
            <p>• <strong>ייצר תגובת AI</strong> - האם לייצר תגובה מוצעת לפוסטים מאזור זה</p>
            <p>• <strong>שלח WhatsApp</strong> - האם לשלוח התראת WhatsApp על פוסטים מאזור זה</p>
            <p>• <strong>הצג בדשבורד</strong> - האם לכלול פוסטים מאזור זה בתצוגת הדשבורד (הסינון בלבד, לא מוחק)</p>
          </div>
        </div>
      )}

      {/* ========== Categories Tab ========== */}
      {activeTab === 'categories' && (
        <div className="space-y-4">
          {categories.map((cat) => (
            <div key={cat.id} className="bg-white rounded-xl shadow-sm border border-gray-100 p-4">
              <div className="flex items-center justify-between mb-3">
                <div>
                  <h3 className="font-semibold text-gray-800">
                    {cat.is_alert_worthy ? '✅' : '❌'} {cat.name}
                  </h3>
                  <p className="text-sm text-gray-500">{cat.description}</p>
                </div>
                <div className="flex items-center gap-2">
                  {cat.whatsapp_phone && (
                    <span className="text-xs bg-green-50 text-green-700 px-2 py-1 rounded-full">
                      📱 {cat.whatsapp_phone}
                    </span>
                  )}
                  <button
                    onClick={() => setEditingCategory({ ...cat })}
                    className="text-xs px-3 py-1.5 bg-blue-50 text-blue-700 rounded-lg hover:bg-blue-100"
                  >
                    ✏️ ערוך
                  </button>
                </div>
              </div>

              {cat.reply_prompt && (
                <div className="bg-gray-50 rounded-lg p-3 text-xs text-gray-600">
                  <span className="font-medium">פרומפט תגובה:</span> {cat.reply_prompt}
                </div>
              )}
            </div>
          ))}

          {/* Edit Modal */}
          {editingCategory && (
            <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
              <div className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto p-6" dir="rtl">
                <h2 className="text-lg font-bold mb-4">✏️ עריכת קטגוריה: {editingCategory.name}</h2>

                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">טלפון WhatsApp</label>
                    <input
                      type="text"
                      value={editingCategory.whatsapp_phone || ''}
                      onChange={(e) => setEditingCategory({ ...editingCategory, whatsapp_phone: e.target.value })}
                      placeholder="0501234567"
                      className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">שם איש קשר</label>
                    <input
                      type="text"
                      value={editingCategory.whatsapp_name || ''}
                      onChange={(e) => setEditingCategory({ ...editingCategory, whatsapp_name: e.target.value })}
                      placeholder="אייל"
                      className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm"
                    />
                  </div>

                  <div className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      id="alert_worthy"
                      checked={editingCategory.is_alert_worthy}
                      onChange={(e) => setEditingCategory({ ...editingCategory, is_alert_worthy: e.target.checked })}
                    />
                    <label htmlFor="alert_worthy" className="text-sm text-gray-700">שלח התראת WhatsApp לקטגוריה זו</label>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">פרומפט יצירת תגובה</label>
                    <textarea
                      value={editingCategory.reply_prompt || ''}
                      onChange={(e) => setEditingCategory({ ...editingCategory, reply_prompt: e.target.value })}
                      rows={4}
                      className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm"
                      placeholder="כתוב הנחיות לAI לגבי איך לענות לקטגוריה זו..."
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">פרומפט סיווג</label>
                    <textarea
                      value={editingCategory.classification_prompt}
                      onChange={(e) => setEditingCategory({ ...editingCategory, classification_prompt: e.target.value })}
                      rows={3}
                      className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm"
                    />
                  </div>

                  <div className="flex gap-3 pt-2">
                    <button
                      onClick={saveCategory}
                      disabled={savingCategory}
                      className="flex-1 bg-blue-600 text-white rounded-lg py-2 text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
                    >
                      {savingCategory ? 'שומר...' : '💾 שמור'}
                    </button>
                    <button
                      onClick={() => setEditingCategory(null)}
                      className="flex-1 bg-gray-100 text-gray-700 rounded-lg py-2 text-sm font-medium hover:bg-gray-200"
                    >
                      ביטול
                    </button>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
