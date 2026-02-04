'use client';

import React, { useState, useEffect } from 'react';

// Types
interface Group {
  id: number;
  fb_group_id: string;
  name: string;
  url: string | null;
  category: string | null;
  member_count: number;
  is_active: boolean;
  total_posts: number;
  total_replies_received: number;
  last_post_at: string | null;
  created_at: string;
}

interface Campaign {
  id: number;
  name: string;
  topic: string;
  target_audience: string | null;
  status: string;
  image_percentage: number;
  total_posts_generated: number;
  total_posts_approved: number;
  total_posts_published: number;
  total_replies: number;
  created_at: string;
}

interface Post {
  id: number;
  campaign_id: number | null;
  group_id: number;
  content: string;
  has_image: boolean;
  image_url: string | null;
  status: string;
  rejection_reason: string | null;
  replies_count: number;
  published_at: string | null;
  created_at: string;
}

interface Reply {
  id: number;
  post_id: number;
  fb_user_name: string | null;
  fb_user_profile_url: string | null;
  message: string;
  ai_detected_intent: string | null;
  wants_private: boolean;
  status: string;
  suggested_response: string | null;
  suggested_channel: string | null;
  actual_response: string | null;
  response_channel: string | null;
  received_at: string | null;
  created_at: string;
}

interface Stats {
  groups: number;
  campaigns: number;
  posts: Record<string, number>;
  replies: {
    total: number;
    pending: number;
  };
}

// Use relative URL for production (nginx proxy) or localhost for development
const API_BASE = typeof window !== 'undefined' && window.location.hostname !== 'localhost' 
  ? '/api/facebook' 
  : 'http://localhost:8000/api/facebook';

// Tab Component
const TabButton: React.FC<{
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
  badge?: number;
}> = ({ active, onClick, children, badge }) => (
  <button
    onClick={onClick}
    className={`px-4 py-2 font-medium text-sm rounded-t-lg flex items-center gap-2 ${
      active
        ? 'bg-blue-600 text-white'
        : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
    }`}
  >
    {children}
    {badge !== undefined && badge > 0 && (
      <span className="bg-red-500 text-white text-xs px-2 py-0.5 rounded-full">
        {badge}
      </span>
    )}
  </button>
);

// Status Badge
const StatusBadge: React.FC<{ status: string }> = ({ status }) => {
  const colors: Record<string, string> = {
    draft: 'bg-gray-100 text-gray-600',
    pending_approval: 'bg-yellow-100 text-yellow-700',
    approved: 'bg-green-100 text-green-700',
    published: 'bg-blue-100 text-blue-700',
    failed: 'bg-red-100 text-red-700',
    rejected: 'bg-red-100 text-red-700',
    new: 'bg-yellow-100 text-yellow-700',
    ai_suggested: 'bg-purple-100 text-purple-700',
    responded: 'bg-green-100 text-green-700',
    generating: 'bg-blue-100 text-blue-700',
    ready: 'bg-green-100 text-green-700',
  };
  
  return (
    <span className={`px-2 py-1 rounded text-xs font-medium ${colors[status] || 'bg-gray-100 text-gray-600'}`}>
      {status.replace('_', ' ')}
    </span>
  );
};

// ========== Dashboard Tab ==========
const DashboardTab: React.FC<{ stats: Stats | null; onRefresh: () => void }> = ({ stats, onRefresh }) => {
  if (!stats) {
    return <div className="p-8 text-center text-gray-500">טוען סטטיסטיקות...</div>;
  }

  const totalPosts = Object.values(stats.posts).reduce((a, b) => a + b, 0);

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-xl font-bold">📊 סקירה כללית</h2>
        <button
          onClick={onRefresh}
          className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
        >
          רענן
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white p-6 rounded-lg shadow border-r-4 border-blue-500">
          <div className="text-3xl font-bold text-blue-600">{stats.groups}</div>
          <div className="text-gray-600">קבוצות פעילות</div>
        </div>
        <div className="bg-white p-6 rounded-lg shadow border-r-4 border-purple-500">
          <div className="text-3xl font-bold text-purple-600">{stats.campaigns}</div>
          <div className="text-gray-600">קמפיינים</div>
        </div>
        <div className="bg-white p-6 rounded-lg shadow border-r-4 border-green-500">
          <div className="text-3xl font-bold text-green-600">{totalPosts}</div>
          <div className="text-gray-600">סה"כ פוסטים</div>
        </div>
        <div className="bg-white p-6 rounded-lg shadow border-r-4 border-orange-500">
          <div className="text-3xl font-bold text-orange-600">{stats.replies.pending}</div>
          <div className="text-gray-600">תגובות ממתינות</div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-lg font-bold mb-4">📝 סטטוס פוסטים</h3>
          <div className="space-y-2">
            {Object.entries(stats.posts).map(([status, count]) => (
              <div key={status} className="flex justify-between items-center">
                <StatusBadge status={status} />
                <span className="font-bold">{count}</span>
              </div>
            ))}
          </div>
        </div>
        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-lg font-bold mb-4">💬 תגובות</h3>
          <div className="space-y-2">
            <div className="flex justify-between">
              <span>סה"כ תגובות</span>
              <span className="font-bold">{stats.replies.total}</span>
            </div>
            <div className="flex justify-between">
              <span>ממתינות לטיפול</span>
              <span className="font-bold text-orange-600">{stats.replies.pending}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

// ========== Groups Tab ==========
const GroupsTab: React.FC<{
  groups: Group[];
  onAdd: (data: Partial<Group>) => void;
  onSearch: (query: string) => void;
}> = ({ groups, onAdd, onSearch }) => {
  const [showAddForm, setShowAddForm] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [formData, setFormData] = useState({ fb_group_id: '', name: '', url: '', category: '' });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onAdd(formData);
    setFormData({ fb_group_id: '', name: '', url: '', category: '' });
    setShowAddForm(false);
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-xl font-bold">📁 קבוצות פייסבוק ({groups.length})</h2>
        <div className="flex gap-2">
          <button
            onClick={() => setShowAddForm(!showAddForm)}
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            + הוסף קבוצה
          </button>
        </div>
      </div>

      {/* Search Groups */}
      <div className="bg-white p-4 rounded-lg shadow">
        <div className="flex gap-2">
          <input
            type="text"
            placeholder="חפש קבוצות ב-Apify (למשל: הלוואות, נדל&quot;ן)"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="flex-1 border rounded px-3 py-2"
          />
          <button
            onClick={() => onSearch(searchQuery)}
            className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700"
          >
            🔍 חפש והוסף
          </button>
        </div>
      </div>

      {/* Add Form */}
      {showAddForm && (
        <form onSubmit={handleSubmit} className="bg-white p-4 rounded-lg shadow space-y-4">
          <h3 className="font-bold">הוספת קבוצה ידנית</h3>
          <div className="grid grid-cols-2 gap-4">
            <input
              type="text"
              placeholder="מזהה קבוצה"
              value={formData.fb_group_id}
              onChange={(e) => setFormData({ ...formData, fb_group_id: e.target.value })}
              className="border rounded px-3 py-2"
              required
            />
            <input
              type="text"
              placeholder="שם הקבוצה"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              className="border rounded px-3 py-2"
              required
            />
            <input
              type="text"
              placeholder="URL"
              value={formData.url}
              onChange={(e) => setFormData({ ...formData, url: e.target.value })}
              className="border rounded px-3 py-2"
            />
            <input
              type="text"
              placeholder="קטגוריה"
              value={formData.category}
              onChange={(e) => setFormData({ ...formData, category: e.target.value })}
              className="border rounded px-3 py-2"
            />
          </div>
          <div className="flex gap-2">
            <button type="submit" className="px-4 py-2 bg-blue-600 text-white rounded">
              הוסף
            </button>
            <button type="button" onClick={() => setShowAddForm(false)} className="px-4 py-2 bg-gray-200 rounded">
              ביטול
            </button>
          </div>
        </form>
      )}

      {/* Groups Table */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-right text-sm font-medium text-gray-500">שם</th>
              <th className="px-4 py-3 text-right text-sm font-medium text-gray-500">קטגוריה</th>
              <th className="px-4 py-3 text-right text-sm font-medium text-gray-500">חברים</th>
              <th className="px-4 py-3 text-right text-sm font-medium text-gray-500">פוסטים</th>
              <th className="px-4 py-3 text-right text-sm font-medium text-gray-500">סטטוס</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {groups.map((group) => (
              <tr key={group.id} className="hover:bg-gray-50">
                <td className="px-4 py-3">
                  <div className="font-medium">{group.name}</div>
                  <div className="text-xs text-gray-500">{group.fb_group_id}</div>
                </td>
                <td className="px-4 py-3 text-sm">{group.category || '-'}</td>
                <td className="px-4 py-3 text-sm">{group.member_count.toLocaleString()}</td>
                <td className="px-4 py-3 text-sm">{group.total_posts}</td>
                <td className="px-4 py-3">
                  <span className={`px-2 py-1 rounded text-xs ${group.is_active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-600'}`}>
                    {group.is_active ? 'פעילה' : 'לא פעילה'}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {groups.length === 0 && (
          <div className="p-8 text-center text-gray-500">
            אין קבוצות עדיין. חפש והוסף קבוצות.
          </div>
        )}
      </div>
    </div>
  );
};

// ========== Campaigns Tab ==========
const CampaignsTab: React.FC<{
  campaigns: Campaign[];
  groups: Group[];
  onCreate: (data: any) => void;
  onGenerate: (id: number) => void;
}> = ({ campaigns, groups, onCreate, onGenerate }) => {
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [formData, setFormData] = useState({
    name: '',
    topic: 'מחשבונים פיננסיים להטמעה בחינם',
    target_audience: '',
    target_group_ids: [] as number[],
    image_percentage: 50,
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onCreate(formData);
    setFormData({ name: '', topic: 'מחשבונים פיננסיים להטמעה בחינם', target_audience: '', target_group_ids: [], image_percentage: 50 });
    setShowCreateForm(false);
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-xl font-bold">🚀 קמפיינים ({campaigns.length})</h2>
        <button
          onClick={() => setShowCreateForm(!showCreateForm)}
          className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
        >
          + קמפיין חדש
        </button>
      </div>

      {/* Create Form */}
      {showCreateForm && (
        <form onSubmit={handleSubmit} className="bg-white p-6 rounded-lg shadow space-y-4">
          <h3 className="font-bold text-lg">יצירת קמפיין חדש</h3>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1">שם הקמפיין</label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                className="w-full border rounded px-3 py-2"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">נושא</label>
              <input
                type="text"
                value={formData.topic}
                onChange={(e) => setFormData({ ...formData, topic: e.target.value })}
                className="w-full border rounded px-3 py-2"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">קהל יעד</label>
              <input
                type="text"
                value={formData.target_audience}
                onChange={(e) => setFormData({ ...formData, target_audience: e.target.value })}
                className="w-full border rounded px-3 py-2"
                placeholder="בעלי אתרים, עסקים קטנים..."
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">אחוז תמונות</label>
              <input
                type="number"
                min="0"
                max="100"
                value={formData.image_percentage}
                onChange={(e) => setFormData({ ...formData, image_percentage: parseInt(e.target.value) })}
                className="w-full border rounded px-3 py-2"
              />
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">קבוצות יעד</label>
            <div className="border rounded p-2 max-h-40 overflow-y-auto">
              {groups.map((group) => (
                <label key={group.id} className="flex items-center gap-2 p-1 hover:bg-gray-50">
                  <input
                    type="checkbox"
                    checked={formData.target_group_ids.includes(group.id)}
                    onChange={(e) => {
                      if (e.target.checked) {
                        setFormData({ ...formData, target_group_ids: [...formData.target_group_ids, group.id] });
                      } else {
                        setFormData({ ...formData, target_group_ids: formData.target_group_ids.filter((id) => id !== group.id) });
                      }
                    }}
                  />
                  <span className="text-sm">{group.name}</span>
                </label>
              ))}
            </div>
          </div>
          <div className="flex gap-2">
            <button type="submit" className="px-4 py-2 bg-blue-600 text-white rounded">
              צור קמפיין
            </button>
            <button type="button" onClick={() => setShowCreateForm(false)} className="px-4 py-2 bg-gray-200 rounded">
              ביטול
            </button>
          </div>
        </form>
      )}

      {/* Campaigns List */}
      <div className="space-y-4">
        {campaigns.map((campaign) => (
          <div key={campaign.id} className="bg-white p-4 rounded-lg shadow">
            <div className="flex justify-between items-start">
              <div>
                <h3 className="font-bold text-lg">{campaign.name}</h3>
                <p className="text-gray-600">{campaign.topic}</p>
                <div className="flex gap-4 mt-2 text-sm text-gray-500">
                  <span>📝 {campaign.total_posts_generated} נוצרו</span>
                  <span>✅ {campaign.total_posts_approved} אושרו</span>
                  <span>📤 {campaign.total_posts_published} פורסמו</span>
                  <span>💬 {campaign.total_replies} תגובות</span>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <StatusBadge status={campaign.status} />
                {campaign.status === 'draft' && (
                  <button
                    onClick={() => onGenerate(campaign.id)}
                    className="px-3 py-1 bg-green-600 text-white text-sm rounded hover:bg-green-700"
                  >
                    ⚡ צור פוסטים
                  </button>
                )}
              </div>
            </div>
          </div>
        ))}
        {campaigns.length === 0 && (
          <div className="bg-white p-8 rounded-lg shadow text-center text-gray-500">
            אין קמפיינים עדיין. צור קמפיין חדש.
          </div>
        )}
      </div>
    </div>
  );
};

// ========== Posts Tab ==========
const PostsTab: React.FC<{
  posts: Post[];
  groups: Group[];
  onApprove: (id: number) => void;
  onReject: (id: number, reason?: string) => void;
  onPublish: (id: number) => void;
  onUpdate: (id: number, content: string) => void;
}> = ({ posts, groups, onApprove, onReject, onPublish, onUpdate }) => {
  const [filter, setFilter] = useState<string>('all');
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editContent, setEditContent] = useState('');

  const filteredPosts = posts.filter((p) => filter === 'all' || p.status === filter);
  const groupsMap = Object.fromEntries(groups.map((g) => [g.id, g.name]));

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-xl font-bold">📝 פוסטים ({filteredPosts.length})</h2>
        <select
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          className="border rounded px-3 py-2"
        >
          <option value="all">הכל</option>
          <option value="pending_approval">ממתינים לאישור</option>
          <option value="approved">מאושרים</option>
          <option value="published">פורסמו</option>
          <option value="rejected">נדחו</option>
          <option value="failed">נכשלו</option>
        </select>
      </div>

      <div className="space-y-4">
        {filteredPosts.map((post) => (
          <div key={post.id} className="bg-white p-4 rounded-lg shadow">
            <div className="flex justify-between items-start mb-2">
              <div className="flex items-center gap-2">
                <StatusBadge status={post.status} />
                <span className="text-sm text-gray-500">{groupsMap[post.group_id] || 'קבוצה לא ידועה'}</span>
                {post.has_image && <span className="text-sm">🖼️</span>}
              </div>
              <div className="flex gap-2">
                {post.status === 'pending_approval' && (
                  <>
                    <button
                      onClick={() => onApprove(post.id)}
                      className="px-3 py-1 bg-green-600 text-white text-sm rounded hover:bg-green-700"
                    >
                      ✓ אשר
                    </button>
                    <button
                      onClick={() => onReject(post.id)}
                      className="px-3 py-1 bg-red-600 text-white text-sm rounded hover:bg-red-700"
                    >
                      ✗ דחה
                    </button>
                    <button
                      onClick={() => {
                        setEditingId(post.id);
                        setEditContent(post.content);
                      }}
                      className="px-3 py-1 bg-gray-200 text-sm rounded hover:bg-gray-300"
                    >
                      ✏️ ערוך
                    </button>
                  </>
                )}
                {post.status === 'approved' && (
                  <button
                    onClick={() => onPublish(post.id)}
                    className="px-3 py-1 bg-blue-600 text-white text-sm rounded hover:bg-blue-700"
                  >
                    📤 פרסם
                  </button>
                )}
              </div>
            </div>

            {editingId === post.id ? (
              <div className="space-y-2">
                <textarea
                  value={editContent}
                  onChange={(e) => setEditContent(e.target.value)}
                  className="w-full border rounded p-2"
                  rows={4}
                />
                <div className="flex gap-2">
                  <button
                    onClick={() => {
                      onUpdate(post.id, editContent);
                      setEditingId(null);
                    }}
                    className="px-3 py-1 bg-blue-600 text-white text-sm rounded"
                  >
                    שמור
                  </button>
                  <button
                    onClick={() => setEditingId(null)}
                    className="px-3 py-1 bg-gray-200 text-sm rounded"
                  >
                    ביטול
                  </button>
                </div>
              </div>
            ) : (
              <div className="whitespace-pre-wrap text-gray-700">{post.content}</div>
            )}

            {post.image_url && (
              <div className="mt-2">
                <img src={post.image_url} alt="Post image" className="max-w-xs rounded" />
              </div>
            )}

            {post.rejection_reason && (
              <div className="mt-2 text-sm text-red-600">סיבת דחייה: {post.rejection_reason}</div>
            )}
          </div>
        ))}
        {filteredPosts.length === 0 && (
          <div className="bg-white p-8 rounded-lg shadow text-center text-gray-500">
            אין פוסטים בסטטוס זה.
          </div>
        )}
      </div>
    </div>
  );
};

// ========== Replies Tab ==========
const RepliesTab: React.FC<{
  replies: Reply[];
  onGenerateResponse: (id: number) => void;
  onSendResponse: (id: number, text?: string, channel?: string) => void;
}> = ({ replies, onGenerateResponse, onSendResponse }) => {
  const [filter, setFilter] = useState<string>('all');
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editResponse, setEditResponse] = useState('');
  const [selectedChannel, setSelectedChannel] = useState<string>('comment');

  const filteredReplies = replies.filter((r) => filter === 'all' || r.status === filter);

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-xl font-bold">💬 תגובות ({filteredReplies.length})</h2>
        <select
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          className="border rounded px-3 py-2"
        >
          <option value="all">הכל</option>
          <option value="new">חדשות</option>
          <option value="ai_suggested">ממתינות לאישור</option>
          <option value="responded">טופלו</option>
        </select>
      </div>

      <div className="space-y-4">
        {filteredReplies.map((reply) => (
          <div key={reply.id} className="bg-white p-4 rounded-lg shadow">
            <div className="flex justify-between items-start mb-3">
              <div>
                <div className="flex items-center gap-2">
                  <span className="font-bold">{reply.fb_user_name || 'משתמש לא ידוע'}</span>
                  <StatusBadge status={reply.status} />
                  {reply.wants_private && (
                    <span className="bg-purple-100 text-purple-700 px-2 py-1 rounded text-xs">
                      📩 מבקש פרטי
                    </span>
                  )}
                </div>
                {reply.ai_detected_intent && (
                  <div className="text-sm text-gray-500">כוונה: {reply.ai_detected_intent}</div>
                )}
              </div>
              <div className="flex gap-2">
                {reply.status === 'new' && (
                  <button
                    onClick={() => onGenerateResponse(reply.id)}
                    className="px-3 py-1 bg-purple-600 text-white text-sm rounded hover:bg-purple-700"
                  >
                    🤖 צור תשובה
                  </button>
                )}
              </div>
            </div>

            <div className="bg-gray-50 p-3 rounded mb-3">
              <div className="text-sm text-gray-500 mb-1">הודעה:</div>
              <div>{reply.message}</div>
            </div>

            {reply.suggested_response && reply.status === 'ai_suggested' && (
              <div className="border border-purple-200 p-3 rounded bg-purple-50 mb-3">
                <div className="text-sm text-purple-700 mb-1">תשובה מוצעת ({reply.suggested_channel}):</div>
                {editingId === reply.id ? (
                  <div className="space-y-2">
                    <textarea
                      value={editResponse}
                      onChange={(e) => setEditResponse(e.target.value)}
                      className="w-full border rounded p-2"
                      rows={3}
                    />
                    <div className="flex gap-2 items-center">
                      <select
                        value={selectedChannel}
                        onChange={(e) => setSelectedChannel(e.target.value)}
                        className="border rounded px-2 py-1"
                      >
                        <option value="comment">תגובה</option>
                        <option value="messenger">מסנג&apos;ר</option>
                      </select>
                      <button
                        onClick={() => {
                          onSendResponse(reply.id, editResponse, selectedChannel);
                          setEditingId(null);
                        }}
                        className="px-3 py-1 bg-green-600 text-white text-sm rounded"
                      >
                        📤 שלח
                      </button>
                      <button
                        onClick={() => setEditingId(null)}
                        className="px-3 py-1 bg-gray-200 text-sm rounded"
                      >
                        ביטול
                      </button>
                    </div>
                  </div>
                ) : (
                  <>
                    <div className="mb-2">{reply.suggested_response}</div>
                    <div className="flex gap-2">
                      <button
                        onClick={() => onSendResponse(reply.id)}
                        className="px-3 py-1 bg-green-600 text-white text-sm rounded hover:bg-green-700"
                      >
                        ✓ אשר ושלח
                      </button>
                      <button
                        onClick={() => {
                          setEditingId(reply.id);
                          setEditResponse(reply.suggested_response || '');
                          setSelectedChannel(reply.suggested_channel || 'comment');
                        }}
                        className="px-3 py-1 bg-gray-200 text-sm rounded hover:bg-gray-300"
                      >
                        ✏️ ערוך
                      </button>
                    </div>
                  </>
                )}
              </div>
            )}

            {reply.status === 'responded' && reply.actual_response && (
              <div className="border border-green-200 p-3 rounded bg-green-50">
                <div className="text-sm text-green-700 mb-1">נשלח ({reply.response_channel || 'comment'}):</div>
                <div>{reply.actual_response}</div>
              </div>
            )}
          </div>
        ))}
        {filteredReplies.length === 0 && (
          <div className="bg-white p-8 rounded-lg shadow text-center text-gray-500">
            אין תגובות בסטטוס זה.
          </div>
        )}
      </div>
    </div>
  );
};

// ========== Main Component ==========
export default function FacebookMarketingPage() {
  const [activeTab, setActiveTab] = useState<string>('dashboard');
  const [stats, setStats] = useState<Stats | null>(null);
  const [groups, setGroups] = useState<Group[]>([]);
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [posts, setPosts] = useState<Post[]>([]);
  const [replies, setReplies] = useState<Reply[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch data
  const fetchData = async () => {
    setLoading(true);
    try {
      const [statsRes, groupsRes, campaignsRes, postsRes, repliesRes] = await Promise.all([
        fetch(`${API_BASE}/stats`),
        fetch(`${API_BASE}/groups`),
        fetch(`${API_BASE}/campaigns`),
        fetch(`${API_BASE}/posts`),
        fetch(`${API_BASE}/replies`),
      ]);

      if (statsRes.ok) setStats(await statsRes.json());
      if (groupsRes.ok) setGroups(await groupsRes.json());
      if (campaignsRes.ok) setCampaigns(await campaignsRes.json());
      if (postsRes.ok) setPosts(await postsRes.json());
      if (repliesRes.ok) setReplies(await repliesRes.json());
      
      setError(null);
    } catch (err) {
      setError('שגיאה בטעינת נתונים');
      console.error(err);
    }
    setLoading(false);
  };

  useEffect(() => {
    fetchData();
  }, []);

  // Actions
  const addGroup = async (data: Partial<Group>) => {
    try {
      const res = await fetch(`${API_BASE}/groups`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });
      if (res.ok) {
        const newGroup = await res.json();
        setGroups([...groups, newGroup]);
      }
    } catch (err) {
      console.error(err);
    }
  };

  const searchGroups = async (query: string) => {
    try {
      const res = await fetch(`${API_BASE}/groups/search`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ search_query: query, max_groups: 20 }),
      });
      if (res.ok) {
        const newGroups = await res.json();
        setGroups([...groups, ...newGroups]);
      }
    } catch (err) {
      console.error(err);
    }
  };

  const createCampaign = async (data: any) => {
    try {
      const res = await fetch(`${API_BASE}/campaigns`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });
      if (res.ok) {
        const newCampaign = await res.json();
        setCampaigns([newCampaign, ...campaigns]);
      }
    } catch (err) {
      console.error(err);
    }
  };

  const generatePosts = async (campaignId: number) => {
    try {
      const res = await fetch(`${API_BASE}/campaigns/${campaignId}/generate`, {
        method: 'POST',
      });
      if (res.ok) {
        fetchData();
      }
    } catch (err) {
      console.error(err);
    }
  };

  const approvePost = async (postId: number) => {
    try {
      const res = await fetch(`${API_BASE}/posts/${postId}/approve`, { method: 'POST' });
      if (res.ok) {
        setPosts(posts.map((p) => (p.id === postId ? { ...p, status: 'approved' } : p)));
      }
    } catch (err) {
      console.error(err);
    }
  };

  const rejectPost = async (postId: number, reason?: string) => {
    try {
      const res = await fetch(`${API_BASE}/posts/${postId}/reject?reason=${reason || ''}`, {
        method: 'POST',
      });
      if (res.ok) {
        setPosts(posts.map((p) => (p.id === postId ? { ...p, status: 'rejected' } : p)));
      }
    } catch (err) {
      console.error(err);
    }
  };

  const publishPost = async (postId: number) => {
    try {
      const res = await fetch(`${API_BASE}/posts/${postId}/publish`, { method: 'POST' });
      if (res.ok) {
        setPosts(posts.map((p) => (p.id === postId ? { ...p, status: 'published' } : p)));
      }
    } catch (err) {
      console.error(err);
    }
  };

  const updatePost = async (postId: number, content: string) => {
    try {
      const res = await fetch(`${API_BASE}/posts/${postId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content }),
      });
      if (res.ok) {
        setPosts(posts.map((p) => (p.id === postId ? { ...p, content } : p)));
      }
    } catch (err) {
      console.error(err);
    }
  };

  const generateReplyResponse = async (replyId: number) => {
    try {
      const res = await fetch(`${API_BASE}/replies/${replyId}/generate`, { method: 'POST' });
      if (res.ok) {
        const updatedReply = await res.json();
        setReplies(replies.map((r) => (r.id === replyId ? updatedReply : r)));
      }
    } catch (err) {
      console.error(err);
    }
  };

  const sendReplyResponse = async (replyId: number, text?: string, channel?: string) => {
    try {
      const res = await fetch(`${API_BASE}/replies/${replyId}/respond`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ response_text: text, channel }),
      });
      if (res.ok) {
        const updatedReply = await res.json();
        setReplies(replies.map((r) => (r.id === replyId ? updatedReply : r)));
      }
    } catch (err) {
      console.error(err);
    }
  };

  const pendingRepliesCount = replies.filter((r) => ['new', 'ai_suggested'].includes(r.status)).length;
  const pendingPostsCount = posts.filter((p) => p.status === 'pending_approval').length;

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center">
        <div className="text-xl text-gray-600">טוען...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-100">
      {/* Header */}
      <div className="bg-blue-600 text-white p-4">
        <h1 className="text-2xl font-bold">📘 Facebook Marketing</h1>
        <p className="text-blue-100">ניהול פרסום בקבוצות פייסבוק</p>
      </div>

      {/* Tabs */}
      <div className="bg-white border-b px-4 flex gap-2 overflow-x-auto">
        <TabButton active={activeTab === 'dashboard'} onClick={() => setActiveTab('dashboard')}>
          📊 סקירה
        </TabButton>
        <TabButton active={activeTab === 'groups'} onClick={() => setActiveTab('groups')}>
          📁 קבוצות
        </TabButton>
        <TabButton active={activeTab === 'campaigns'} onClick={() => setActiveTab('campaigns')}>
          🚀 קמפיינים
        </TabButton>
        <TabButton active={activeTab === 'posts'} onClick={() => setActiveTab('posts')} badge={pendingPostsCount}>
          📝 פוסטים
        </TabButton>
        <TabButton active={activeTab === 'replies'} onClick={() => setActiveTab('replies')} badge={pendingRepliesCount}>
          💬 תגובות
        </TabButton>
      </div>

      {/* Error */}
      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 m-4 rounded">
          {error}
        </div>
      )}

      {/* Content */}
      <div className="p-4">
        {activeTab === 'dashboard' && <DashboardTab stats={stats} onRefresh={fetchData} />}
        {activeTab === 'groups' && <GroupsTab groups={groups} onAdd={addGroup} onSearch={searchGroups} />}
        {activeTab === 'campaigns' && (
          <CampaignsTab
            campaigns={campaigns}
            groups={groups}
            onCreate={createCampaign}
            onGenerate={generatePosts}
          />
        )}
        {activeTab === 'posts' && (
          <PostsTab
            posts={posts}
            groups={groups}
            onApprove={approvePost}
            onReject={rejectPost}
            onPublish={publishPost}
            onUpdate={updatePost}
          />
        )}
        {activeTab === 'replies' && (
          <RepliesTab
            replies={replies}
            onGenerateResponse={generateReplyResponse}
            onSendResponse={sendReplyResponse}
          />
        )}
      </div>
    </div>
  );
}
