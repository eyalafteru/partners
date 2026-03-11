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
  auto_reply_enabled: boolean;
  total_posts: number;
  total_replies_received: number;
  last_post_at: string | null;
  created_at: string;
}

// Calculator for campaign linking
interface Calculator {
  id: number;
  name: string;
  category: string | null;
  url: string;
  target_url: string | null;
  has_summary: boolean;
  youtube_url: string | null;
  demo_video_url: string | null;
}

// Post Strategy for content generation
interface PostStrategy {
  id: number;
  name: string;
  slug: string;
  icon: string;
  description: string | null;
  is_active: boolean;
}

interface Campaign {
  id: number;
  name: string;
  topic: string;
  target_audience: string | null;
  status: string;
  image_percentage: number;
  target_group_ids: number[];
  total_posts_generated: number;
  total_posts_approved: number;
  total_posts_published: number;
  total_replies: number;
  created_at: string;
  // New fields for calculator & strategy support
  calculator_id: number | null;
  calculator_mode: 'specific' | 'all' | 'category';
  calculator_category: string | null;
  strategy_ids: number[];
  link_placement: 'first_comment' | 'none';  // הקישור תמיד בתגובה ראשונה, אף פעם לא בפוסט
  auto_responder_enabled: boolean;
  auto_responder_type: 'comment' | 'messenger' | 'ai_decide';
  auto_responder_template: string | null;
  auto_responder_delay_minutes: number;
  auto_responder_daily_limit: number;
  media_preference: 'image' | 'video' | 'both' | 'none';
}

interface Post {
  id: number;
  campaign_id: number | null;
  group_id: number;
  content: string;
  has_image: boolean;
  image_url: string | null;
  youtube_url: string | null;
  status: string;
  rejection_reason: string | null;
  publish_error: string | null;
  replies_count: number;
  published_at: string | null;
  created_at: string;
  // New fields
  calculator_id: number | null;
  strategy_id: number | null;
  first_comment_content: string | null;
  first_comment_posted: boolean;
  auto_replies_sent: number;
  // Debug field
  debug_ai_prompt: string | null;
}

// Debug info for AI prompt viewing
interface PostDebugInfo {
  post_id: number;
  status: string;
  group_name: string | null;
  strategy_name: string | null;
  calculator_name: string | null;
  generated_content: string;
  debug_ai_prompt: string | null;
  has_debug_prompt: boolean;
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
  anti_spam?: {
    posts_today: number;
    max_posts_today: number;
    remaining_today: number;
    posts_this_week: number;
    groups_posted_this_week: number;
    posting_hours: string;
    min_delay_seconds: number;
    max_delay_seconds: number;
    can_post_now: boolean;
  };
}

// Use relative URL for production (nginx proxy); use backend for local dev (localhost / 127.0.0.1)
const isLocalDev = typeof window !== 'undefined' && (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1');
const API_BASE = isLocalDev ? 'http://localhost:8000/api/facebook' : '/api/facebook';

// Main API base for non-facebook endpoints (strategies, calculators)
const API_MAIN = isLocalDev ? 'http://localhost:8000/api' : '/api';

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
    approved_not_sent: 'bg-orange-100 text-orange-700',
    ignored: 'bg-gray-100 text-gray-500',
    generating: 'bg-blue-100 text-blue-700',
    ready: 'bg-green-100 text-green-700',
  };

  const labels: Record<string, string> = {
    draft: 'טיוטה',
    pending_approval: 'ממתין לאישור',
    approved: 'מאושר',
    published: 'פורסם',
    failed: 'נכשל',
    rejected: 'נדחה',
    new: 'חדש',
    ai_suggested: 'הצעת AI',
    responded: 'נענה',
    approved_not_sent: 'ממתין לפרסום',
    ignored: 'לא רלוונטי',
    generating: 'בייצור',
    ready: 'מוכן',
  };
  
  return (
    <span className={`px-2 py-1 rounded text-xs font-medium ${colors[status] || 'bg-gray-100 text-gray-600'}`}>
      {labels[status] || status.replace('_', ' ')}
    </span>
  );
};

// ========== Feed Tab (Unified View) ==========
const FeedTab: React.FC<{
  campaigns: Campaign[];
  posts: Post[];
  replies: Reply[];
  groups: Group[];
  calculators: Calculator[];
  strategies: PostStrategy[];
  calcCategories: string[];
  onCreate: (data: any) => void;
  onGenerate: (id: number) => Promise<void>;
  onUpdateCampaign: (id: number, data: any) => void;
  onDeleteCampaign: (id: number) => Promise<void>;
  onApprovePost: (id: number) => void;
  onRejectPost: (id: number) => Promise<{ group_id: number; campaign_id: number | null } | null>;
  onPublishPost: (id: number) => Promise<void>;
  onApproveAndPublishPost: (id: number) => Promise<void>;
  onUpdatePost: (id: number, content: string) => void;
  onRegeneratePost: (id: number, model?: string) => Promise<void>;
  onAddImage: (id: number, style: 'eyal' | 'generic', regenerate: boolean) => Promise<void>;
  onRegenerateForGroup: (campaignId: number, groupId: number) => Promise<void>;
  onGenerateResponse: (id: number) => Promise<void>;
  onSendResponse: (id: number, text?: string, channel?: string) => Promise<void>;
  onMarkResponded: (id: number) => Promise<void>;
  onSyncComments: (postId: number) => Promise<void>;
  loadingSyncPostId: number | null;
  onDebugPost: (id: number) => Promise<void>;
  availableModels: { id: string; name: string }[];
}> = ({
  campaigns,
  posts,
  replies,
  groups,
  calculators,
  strategies,
  calcCategories,
  onCreate,
  onGenerate,
  onUpdateCampaign,
  onDeleteCampaign,
  onApprovePost,
  onRejectPost,
  onPublishPost,
  onApproveAndPublishPost,
  onUpdatePost,
  onRegeneratePost,
  onAddImage,
  onRegenerateForGroup,
  onGenerateResponse,
  onSendResponse,
  onMarkResponded,
  onSyncComments,
  loadingSyncPostId,
  onDebugPost,
  availableModels,
}) => {
  const [expandedCampaigns, setExpandedCampaigns] = useState<Set<number>>(new Set());
  const [expandedPosts, setExpandedPosts] = useState<Set<number>>(new Set());
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [editingCampaign, setEditingCampaign] = useState<Campaign | null>(null);
  const [filter, setFilter] = useState<string>('all');
  
  // Full form state for create/edit
  const emptyFormData = {
    name: '',
    topic: '',
    target_audience: '',
    target_group_ids: [] as number[],
    calculator_id: null as number | null,
    calculator_category: null as string | null,
    calculator_mode: 'specific' as 'specific' | 'category',
    strategy_ids: [] as number[],
    link_placement: 'first_comment' as 'first_comment' | 'none',
    auto_responder_enabled: true,
    auto_responder_type: 'ai_decide' as 'comment' | 'messenger' | 'ai_decide',
    auto_responder_template: '',
    auto_responder_delay_minutes: 5,
    auto_responder_daily_limit: 50,
    status: 'draft' as string,
    media_preference: 'image' as 'image' | 'video' | 'both' | 'none',
  };
  const [formData, setFormData] = useState(emptyFormData);
  const [editFormData, setEditFormData] = useState(emptyFormData);
  const [sortBy, setSortBy] = useState<'replies' | 'date'>('replies');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [generatingCampaignId, setGeneratingCampaignId] = useState<number | null>(null);
  const [deletedPost, setDeletedPost] = useState<{ groupId: number; campaignId: number; groupName: string; campaignName: string } | null>(null);
  const [loadingNewPost, setLoadingNewPost] = useState(false);
  const [campaignToDelete, setCampaignToDelete] = useState<Campaign | null>(null);
  const [deletingCampaignId, setDeletingCampaignId] = useState<number | null>(null);
  
  // Delete campaign handler
  const handleDeleteCampaign = async () => {
    if (!campaignToDelete) return;
    setDeletingCampaignId(campaignToDelete.id);
    try {
      await onDeleteCampaign(campaignToDelete.id);
    } catch (err) {
      console.error('Error deleting campaign:', err);
    }
    setDeletingCampaignId(null);
    setCampaignToDelete(null);
  };
  
  // Loading states
  const [loadingRegenerate, setLoadingRegenerate] = useState<number | null>(null);
  const [loadingPublish, setLoadingPublish] = useState<number | null>(null);
  const [loadingApproveAndPublish, setLoadingApproveAndPublish] = useState<number | null>(null);
  const [loadingGenerate, setLoadingGenerate] = useState<number | null>(null);
  const [loadingSend, setLoadingSend] = useState<number | null>(null);
  const [addingImageId, setAddingImageId] = useState<number | null>(null);
  const [loadingImage, setLoadingImage] = useState<number | null>(null);
  const [editingPostId, setEditingPostId] = useState<number | null>(null);
  const [editPostContent, setEditPostContent] = useState('');
  const [editingReplyId, setEditingReplyId] = useState<number | null>(null);
  const [editReplyResponse, setEditReplyResponse] = useState('');
  const [selectedChannel, setSelectedChannel] = useState<string>('comment');

  // Calculate reply counts per campaign
  const campaignReplyCounts = React.useMemo(() => {
    const counts: Record<number, number> = {};
    posts.forEach(post => {
      if (post.campaign_id) {
        const postReplies = replies.filter(r => r.post_id === post.id && !['responded', 'ignored'].includes(r.status));
        counts[post.campaign_id] = (counts[post.campaign_id] || 0) + postReplies.length;
      }
    });
    return counts;
  }, [posts, replies]);

  // Sort campaigns - those with new replies first
  const sortedCampaigns = React.useMemo(() => {
    return [...campaigns].sort((a, b) => {
      if (sortBy === 'replies') {
        const aReplies = campaignReplyCounts[a.id] || 0;
        const bReplies = campaignReplyCounts[b.id] || 0;
        if (bReplies !== aReplies) return bReplies - aReplies;
      }
      return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
    });
  }, [campaigns, campaignReplyCounts, sortBy]);

  // Filter campaigns
  const filteredCampaigns = sortedCampaigns.filter(c => {
    // Search filter
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      const matchesCampaign = c.name.toLowerCase().includes(query) || c.topic.toLowerCase().includes(query);
      const matchesPosts = posts.some(p => p.campaign_id === c.id && p.content.toLowerCase().includes(query));
      if (!matchesCampaign && !matchesPosts) return false;
    }
    // Status filter
    if (filter === 'all') return true;
    if (filter === 'with_replies') return (campaignReplyCounts[c.id] || 0) > 0;
    return c.status === filter;
  });

  const toggleCampaign = (id: number) => {
    setExpandedCampaigns(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const togglePost = (id: number) => {
    setExpandedPosts(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const groupsMap = Object.fromEntries(groups.map(g => [g.id, g.name]));
  const campaignsMap = Object.fromEntries(campaigns.map(c => [c.id, c.name]));

  return (
    <div className="space-y-4">
      {/* Header with filters */}
      <div className="flex justify-between items-center flex-wrap gap-4">
        <h2 className="text-xl font-bold">📢 פיד קמפיינים ({filteredCampaigns.length})</h2>
        <div className="flex gap-2 items-center flex-wrap">
          <input
            type="text"
            placeholder="🔍 חיפוש..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="border rounded px-3 py-2 text-sm w-40"
          />
          <select
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            className="border rounded px-3 py-2 text-sm"
          >
            <option value="all">כל הקמפיינים</option>
            <option value="with_replies">עם תגובות חדשות</option>
            <option value="draft">טיוטה</option>
            <option value="ready">מוכן</option>
            <option value="generating">בייצור</option>
          </select>
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as 'replies' | 'date')}
            className="border rounded px-3 py-2 text-sm"
          >
            <option value="replies">מיון לפי תגובות</option>
            <option value="date">מיון לפי תאריך</option>
          </select>
          <button
            onClick={() => setShowCreateForm(!showCreateForm)}
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 text-sm"
          >
            + קמפיין חדש
          </button>
        </div>
      </div>

      {/* Campaigns Feed */}
      <div className="space-y-4">
        {filteredCampaigns.map((campaign) => {
          const campaignPosts = posts.filter(p => p.campaign_id === campaign.id);
          const pendingReplies = campaignReplyCounts[campaign.id] || 0;
          const isExpanded = expandedCampaigns.has(campaign.id);

          return (
            <div key={campaign.id} className="bg-white rounded-lg shadow overflow-hidden">
              {/* Campaign Header - Clickable */}
              <div
                className="p-4 cursor-pointer hover:bg-gray-50 flex justify-between items-center"
                onClick={() => toggleCampaign(campaign.id)}
              >
                <div className="flex items-center gap-3">
                  <span className="text-lg">{isExpanded ? '▼' : '▶'}</span>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-lg">{campaign.name}</span>
                      <StatusBadge status={campaign.status} />
                      {pendingReplies > 0 && (
                        <span className="bg-red-500 text-white text-xs px-2 py-1 rounded-full font-bold animate-pulse">
                          {pendingReplies} תגובות
                        </span>
                      )}
                    </div>
                    <div className="text-sm text-gray-500">
                      {campaignPosts.length} פוסטים | {campaign.target_group_ids.length} קבוצות
                    </div>
                  </div>
                </div>
                <div className="flex gap-2" onClick={(e) => e.stopPropagation()}>
                  <button
                    onClick={() => {
                      setEditingCampaign(campaign);
                      setEditFormData({
                        name: campaign.name,
                        topic: campaign.topic,
                        target_audience: campaign.target_audience || '',
                        target_group_ids: campaign.target_group_ids || [],
                        calculator_id: campaign.calculator_id || null,
                        calculator_category: campaign.calculator_category || null,
                        calculator_mode: campaign.calculator_id ? 'specific' : 'category',
                        strategy_ids: campaign.strategy_ids || [],
                        link_placement: (campaign.link_placement as 'first_comment' | 'none') || 'first_comment',
                        auto_responder_enabled: campaign.auto_responder_enabled ?? true,
                        auto_responder_type: (campaign.auto_responder_type as 'comment' | 'messenger' | 'ai_decide') || 'ai_decide',
                        auto_responder_template: campaign.auto_responder_template || '',
                        auto_responder_delay_minutes: campaign.auto_responder_delay_minutes ?? 5,
                        auto_responder_daily_limit: campaign.auto_responder_daily_limit ?? 50,
                        status: campaign.status || 'draft',
                        media_preference: (campaign.media_preference as 'image' | 'video' | 'both' | 'none') || 'image',
                      });
                    }}
                    className="px-3 py-1 text-sm rounded bg-gray-200 hover:bg-gray-300"
                    title="עריכת קמפיין"
                  >
                    ✏️
                  </button>
                  {/* Delete button - always available */}
                  <button
                    onClick={() => setCampaignToDelete(campaign)}
                    disabled={deletingCampaignId === campaign.id}
                    className={`px-3 py-1 text-sm rounded ${
                      deletingCampaignId === campaign.id
                        ? 'bg-gray-300 cursor-wait'
                        : 'bg-red-100 text-red-700 hover:bg-red-200'
                    }`}
                    title="מחק קמפיין"
                  >
                    {deletingCampaignId === campaign.id ? '⏳' : '🗑️'}
                  </button>
                  <button
                    onClick={async () => {
                      setGeneratingCampaignId(campaign.id);
                      await onGenerate(campaign.id);
                      setGeneratingCampaignId(null);
                    }}
                    disabled={generatingCampaignId === campaign.id}
                    className={`px-3 py-1 text-sm rounded ${
                      generatingCampaignId === campaign.id
                        ? 'bg-gray-300 cursor-wait'
                        : 'bg-green-600 text-white hover:bg-green-700'
                    }`}
                  >
                    {generatingCampaignId === campaign.id ? '⏳ מייצר...' : '🚀 צור פוסטים'}
                  </button>
                </div>
              </div>

              {/* Expanded Content - Posts */}
              <div className={`border-t bg-gray-50 overflow-hidden transition-all duration-300 ease-in-out ${
                isExpanded ? 'max-h-[5000px] opacity-100 p-4' : 'max-h-0 opacity-0 p-0'
              }`}>
                <div className="space-y-3">
                  {campaignPosts.length === 0 ? (
                    <div className="text-center text-gray-500 py-4">
                      אין פוסטים עדיין. לחץ על "צור פוסטים" ליצירת פוסטים.
                    </div>
                  ) : (
                    campaignPosts.map((post) => {
                      const postReplies = replies.filter(r => r.post_id === post.id);
                      const newReplies = postReplies.filter(r => r.status !== 'responded');
                      const isPostExpanded = expandedPosts.has(post.id);

                      return (
                        <div key={post.id} className="bg-white rounded-lg border p-3">
                          {/* Post Header */}
                          <div
                            className="flex justify-between items-start cursor-pointer"
                            onClick={() => togglePost(post.id)}
                          >
                            <div className="flex-1">
                              <div className="flex items-center gap-2 mb-1">
                                <span className="text-sm">{isPostExpanded ? '▼' : '▶'}</span>
                                <span className="font-medium">{groupsMap[post.group_id] || `קבוצה ${post.group_id}`}</span>
                                <StatusBadge status={post.status} />
                                {post.has_image && <span title="יש תמונה">🖼️</span>}
                                {newReplies.length > 0 && (
                                  <span className="bg-red-100 text-red-700 text-xs px-2 py-0.5 rounded">
                                    💬 {newReplies.length}
                                  </span>
                                )}
                              </div>
                              {post.status === 'failed' && post.publish_error && (
                                <div className="text-xs text-red-600 mt-1">❌ {post.publish_error}</div>
                              )}
                              <div className="text-sm text-gray-600 line-clamp-2">
                                {post.content.substring(0, 150)}...
                              </div>
                            </div>
                            <div className="flex gap-1" onClick={(e) => e.stopPropagation()}>
                              {post.status === 'pending_approval' && (
                                <>
                                  <button
                                    onClick={() => onApprovePost(post.id)}
                                    className="px-2 py-1 bg-green-600 text-white text-xs rounded hover:bg-green-700"
                                    title="אשר"
                                  >
                                    ✓
                                  </button>
                                  <button
                                    onClick={async () => {
                                      setLoadingApproveAndPublish(post.id);
                                      await onApproveAndPublishPost(post.id);
                                      setLoadingApproveAndPublish(null);
                                    }}
                                    disabled={loadingApproveAndPublish === post.id}
                                    className={`px-2 py-1 text-xs rounded ${
                                      loadingApproveAndPublish === post.id
                                        ? 'bg-gray-300'
                                        : 'bg-blue-600 text-white hover:bg-blue-700'
                                    }`}
                                    title="אשר ופרסם"
                                  >
                                    {loadingApproveAndPublish === post.id ? '⏳' : '🚀'}
                                  </button>
                                  <button
                                    onClick={async () => {
                                      const result = await onRejectPost(post.id);
                                      if (result && result.campaign_id) {
                                        setDeletedPost({
                                          groupId: result.group_id,
                                          campaignId: result.campaign_id,
                                          groupName: groupsMap[result.group_id] || 'קבוצה',
                                          campaignName: campaignsMap[result.campaign_id] || 'קמפיין'
                                        });
                                      }
                                    }}
                                    className="px-2 py-1 bg-red-600 text-white text-xs rounded hover:bg-red-700"
                                    title="דחה ומחק"
                                  >
                                    ✗
                                  </button>
                                </>
                              )}
                              {post.status === 'approved' && (
                                <button
                                  onClick={async () => {
                                    setLoadingPublish(post.id);
                                    await onPublishPost(post.id);
                                    setLoadingPublish(null);
                                  }}
                                  disabled={loadingPublish === post.id}
                                  className={`px-2 py-1 text-xs rounded ${
                                    loadingPublish === post.id
                                      ? 'bg-gray-300'
                                      : 'bg-blue-600 text-white hover:bg-blue-700'
                                  }`}
                                >
                                  {loadingPublish === post.id ? '⏳' : '📤'}
                                </button>
                              )}
                              {post.status === 'failed' && (
                                <button
                                  onClick={async () => {
                                    setLoadingPublish(post.id);
                                    await onPublishPost(post.id);
                                    setLoadingPublish(null);
                                  }}
                                  disabled={loadingPublish === post.id}
                                  className={`px-2 py-1 text-xs rounded ${
                                    loadingPublish === post.id
                                      ? 'bg-gray-300'
                                      : 'bg-orange-600 text-white hover:bg-orange-700'
                                  }`}
                                  title="פרסם שוב"
                                >
                                  {loadingPublish === post.id ? '⏳' : '🔄'}
                                </button>
                              )}
                              {/* 🐞 Debug Button */}
                              <button
                                onClick={() => onDebugPost(post.id)}
                                className="px-2 py-1 bg-gray-500 text-white text-xs rounded hover:bg-gray-600"
                                title="הצג פרומפט AI"
                              >
                                🐞
                              </button>
                            </div>
                          </div>

                          {/* Post Expanded Content */}
                          {isPostExpanded && (
                            <div className="mt-3 pt-3 border-t space-y-3">
                              {/* Full Post Content */}
                              <div className="bg-gray-50 p-3 rounded text-sm whitespace-pre-wrap">
                                {post.content}
                              </div>

                              {/* Post Image */}
                              {post.image_url && (
                                <div className="mt-2">
                                  <img 
                                    src={post.image_url} 
                                    alt="תמונת הפוסט" 
                                    className="max-w-sm rounded shadow-sm border"
                                  />
                                </div>
                              )}

                              {/* YouTube Video Preview */}
                              {post.youtube_url && (
                                <div className="mt-3 p-3 bg-gradient-to-r from-red-50 to-orange-50 rounded-lg border border-red-200">
                                  <p className="text-sm font-medium mb-2 text-red-700">🎥 וידאו מצורף:</p>
                                  <div className="aspect-video max-w-sm">
                                    <iframe 
                                      src={`https://www.youtube.com/embed/${post.youtube_url.split('/').pop()?.split('?')[0]}`}
                                      className="w-full h-full rounded"
                                      allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                                      allowFullScreen
                                    />
                                  </div>
                                  <a 
                                    href={post.youtube_url} 
                                    target="_blank" 
                                    rel="noopener noreferrer"
                                    className="text-xs text-blue-600 hover:underline mt-2 block"
                                  >
                                    🔗 {post.youtube_url}
                                  </a>
                                </div>
                              )}

                              {/* Post Actions */}
                              <div className="flex gap-2 flex-wrap">
                                <button
                                  onClick={() => {
                                    setEditingPostId(post.id);
                                    setEditPostContent(post.content);
                                  }}
                                  className="px-2 py-1 bg-gray-200 text-xs rounded hover:bg-gray-300"
                                >
                                  ✏️ ערוך
                                </button>
                                <button
                                  onClick={async () => {
                                    setLoadingRegenerate(post.id);
                                    await onRegeneratePost(post.id);
                                    setLoadingRegenerate(null);
                                  }}
                                  disabled={loadingRegenerate === post.id}
                                  className={`px-2 py-1 text-xs rounded ${
                                    loadingRegenerate === post.id
                                      ? 'bg-gray-300'
                                      : 'bg-purple-600 text-white hover:bg-purple-700'
                                  }`}
                                >
                                  {loadingRegenerate === post.id ? '⏳' : '🔄 ייצר מחדש'}
                                </button>
                                <button
                                  onClick={() => setAddingImageId(addingImageId === post.id ? null : post.id)}
                                  className="px-2 py-1 bg-orange-500 text-white text-xs rounded hover:bg-orange-600"
                                >
                                  🖼️ {post.has_image ? 'החלף תמונה' : 'הוסף תמונה'}
                                </button>
                              </div>

                              {/* Image Generation Modal */}
                              {addingImageId === post.id && (
                                <div className="bg-orange-50 p-3 rounded border border-orange-200 mt-2">
                                  {loadingImage === post.id ? (
                                    <div className="flex items-center gap-2 text-orange-600">
                                      <span className="animate-spin">⏳</span>
                                      <span className="font-medium">מייצר תמונה... (זה עלול לקחת עד 30 שניות)</span>
                                    </div>
                                  ) : (
                                    <div className="flex items-center gap-2 flex-wrap">
                                      <span className="text-sm font-medium">סוג תמונה:</span>
                                      <button
                                        onClick={async () => {
                                          setLoadingImage(post.id);
                                          await onAddImage(post.id, 'eyal', post.has_image);
                                          setLoadingImage(null);
                                          setAddingImageId(null);
                                        }}
                                        className="px-3 py-1 bg-blue-600 text-white text-sm rounded hover:bg-blue-700"
                                      >
                                        👤 תמונה של אייל
                                      </button>
                                      <button
                                        onClick={async () => {
                                          setLoadingImage(post.id);
                                          await onAddImage(post.id, 'generic', post.has_image);
                                          setLoadingImage(null);
                                          setAddingImageId(null);
                                        }}
                                        className="px-3 py-1 bg-green-600 text-white text-sm rounded hover:bg-green-700"
                                      >
                                        🎨 תמונה גנרית
                                      </button>
                                      <button
                                        onClick={() => setAddingImageId(null)}
                                        className="px-2 py-1 text-gray-500 text-sm hover:text-gray-700"
                                      >
                                        ✕
                                      </button>
                                    </div>
                                  )}
                                </div>
                              )}

                              {/* Edit Post Form */}
                              {editingPostId === post.id && (
                                <div className="bg-yellow-50 p-3 rounded border border-yellow-200">
                                  <textarea
                                    value={editPostContent}
                                    onChange={(e) => setEditPostContent(e.target.value)}
                                    className="w-full border rounded p-2 text-sm"
                                    rows={4}
                                  />
                                  <div className="flex gap-2 mt-2">
                                    <button
                                      onClick={() => {
                                        onUpdatePost(post.id, editPostContent);
                                        setEditingPostId(null);
                                      }}
                                      className="px-3 py-1 bg-green-600 text-white text-sm rounded"
                                    >
                                      שמור
                                    </button>
                                    <button
                                      onClick={() => setEditingPostId(null)}
                                      className="px-3 py-1 bg-gray-300 text-sm rounded"
                                    >
                                      ביטול
                                    </button>
                                  </div>
                                </div>
                              )}

                              {/* Replies Section */}
                              <div className="bg-blue-50 p-3 rounded border border-blue-200">
                                <div className="flex items-center justify-between gap-2 mb-2">
                                  <h4 className="font-medium text-sm">💬 תגובות ({postReplies.length})</h4>
                                  <button
                                    type="button"
                                    onClick={(e) => { e.stopPropagation(); onSyncComments(post.id); }}
                                    disabled={loadingSyncPostId === post.id}
                                    className={`px-2 py-1 text-xs rounded ${loadingSyncPostId === post.id ? 'bg-gray-300' : 'bg-blue-600 text-white hover:bg-blue-700'}`}
                                    title="משוך תגובות חדשות מפייסבוק"
                                  >
                                    {loadingSyncPostId === post.id ? '⏳ מרענן...' : '🔄 רענן תגובות'}
                                  </button>
                                </div>
                                {postReplies.length > 0 && (
                                  <div className="space-y-2">
                                    {postReplies.map((reply) => (
                                      <div key={reply.id} className={`p-2 rounded text-sm ${
                                        reply.status === 'responded' ? 'bg-green-50' : 'bg-white'
                                      }`}>
                                        <div className="flex justify-between items-start">
                                          <div>
                                            <span className="font-medium">{reply.fb_user_name || 'משתמש'}</span>
                                            <StatusBadge status={reply.status} />
                                          </div>
                                          <div className="flex gap-1">
                                            {(reply.status === 'new' || ((reply.status === 'ai_suggested' || reply.status === 'approved_not_sent') && !reply.suggested_response && !reply.actual_response)) && (
                                              <button
                                                onClick={async () => {
                                                  setLoadingGenerate(reply.id);
                                                  await onGenerateResponse(reply.id);
                                                  setLoadingGenerate(null);
                                                }}
                                                disabled={loadingGenerate === reply.id}
                                                className={`px-2 py-1 text-xs rounded ${
                                                  loadingGenerate === reply.id
                                                    ? 'bg-gray-300'
                                                    : 'bg-purple-600 text-white'
                                                }`}
                                                title="יצירת הצעת תשובה אוטומטית מ-AI"
                                              >
                                                {loadingGenerate === reply.id ? '⏳' : '🤖 צור תשובה'}
                                              </button>
                                            )}
                                            {(reply.status === 'ai_suggested' || reply.status === 'approved_not_sent') && (reply.suggested_response || reply.actual_response) && (
                                              <>
                                                <button
                                                  onClick={() => {
                                                    setEditingReplyId(reply.id);
                                                    setEditReplyResponse(reply.suggested_response || reply.actual_response || '');
                                                  }}
                                                  className="px-2 py-1 bg-blue-600 text-white text-xs rounded"
                                                >
                                                  ✏️ ערוך
                                                </button>
                                                <button
                                                  onClick={async () => {
                                                    const text = reply.actual_response || reply.suggested_response || '';
                                                    await navigator.clipboard.writeText(text);
                                                    setLoadingSend(reply.id);
                                                    await onSendResponse(reply.id, text, 'comment');
                                                    setLoadingSend(null);
                                                  }}
                                                  disabled={loadingSend === reply.id}
                                                  className="px-2 py-1 bg-green-600 text-white text-xs rounded"
                                                >
                                                  {loadingSend === reply.id ? '...' : '✅ אשר'}
                                                </button>
                                              </>
                                            )}
                                          </div>
                                        </div>
                                        <div className="mt-1 text-gray-600">{reply.message}</div>
                                        {reply.suggested_response && (
                                          <div className="mt-1 p-2 bg-purple-50 rounded text-purple-800 text-xs">
                                            💡 {reply.suggested_response}
                                          </div>
                                        )}
                                        {reply.status === 'approved_not_sent' && reply.actual_response && (
                                          <div className="mt-1 p-2 bg-orange-50 rounded text-orange-800 text-xs border border-orange-200">
                                            <div className="font-semibold mb-1">📋 התגובה הועתקה - פרסמו בפייסבוק:</div>
                                            <div className="mt-1 mb-2 p-2 bg-white rounded border font-medium text-gray-800">{reply.actual_response}</div>
                                            <div className="flex gap-2 flex-wrap items-center">
                                              <button
                                                onClick={async () => {
                                                  await navigator.clipboard.writeText(reply.actual_response || '');
                                                }}
                                                className="px-3 py-1 bg-yellow-500 text-white text-xs rounded font-medium"
                                              >
                                                📋 העתק שוב
                                              </button>
                                              {posts.find(p => p.id === reply.post_id)?.fb_post_url && (
                                                <a
                                                  href={posts.find(p => p.id === reply.post_id)?.fb_post_url}
                                                  target="_blank"
                                                  rel="noopener noreferrer"
                                                  className="px-3 py-1 bg-blue-600 text-white text-xs rounded font-medium inline-block"
                                                >
                                                  🔗 פתח בפייסבוק
                                                </a>
                                              )}
                                              <button
                                                onClick={() => onMarkResponded(reply.id)}
                                                className="px-3 py-1 bg-green-600 text-white text-xs rounded font-medium"
                                              >
                                                ✅ פרסמתי - סמן כנענה
                                              </button>
                                            </div>
                                          </div>
                                        )}
                                        {reply.status === 'responded' && reply.actual_response && (
                                          <div className="mt-1 p-2 bg-green-50 rounded text-green-800 text-xs">
                                            ✅ נשלח: {reply.actual_response}
                                          </div>
                                        )}
                                        
                                        {/* Edit Reply Form */}
                                        {editingReplyId === reply.id && (
                                          <div className="mt-2 p-2 bg-yellow-50 rounded">
                                            <textarea
                                              value={editReplyResponse}
                                              onChange={(e) => setEditReplyResponse(e.target.value)}
                                              className="w-full border rounded p-2 text-xs"
                                              rows={2}
                                            />
                                            <div className="flex gap-2 mt-1 items-center">
                                              <select
                                                value={selectedChannel}
                                                onChange={(e) => setSelectedChannel(e.target.value)}
                                                className="border rounded px-2 py-1 text-xs"
                                              >
                                                <option value="comment">תגובה</option>
                                                <option value="messenger">מסנג'ר</option>
                                              </select>
                                              <button
                                                onClick={async () => {
                                                  setLoadingSend(reply.id);
                                                  await onSendResponse(reply.id, editReplyResponse, selectedChannel);
                                                  setLoadingSend(null);
                                                  setEditingReplyId(null);
                                                }}
                                                disabled={loadingSend === reply.id}
                                                className="px-2 py-1 bg-green-600 text-white text-xs rounded"
                                              >
                                                שלח
                                              </button>
                                              <button
                                                onClick={() => setEditingReplyId(null)}
                                                className="px-2 py-1 bg-gray-300 text-xs rounded"
                                              >
                                                ביטול
                                              </button>
                                            </div>
                                          </div>
                                        )}
                                      </div>
                                    ))}
                                  </div>
                                )}
                              </div>
                            </div>
                          )}
                        </div>
                      );
                    })
                  )}
                  
                  {/* Add Post Button */}
                  <button
                    onClick={async () => {
                      setGeneratingCampaignId(campaign.id);
                      await onGenerate(campaign.id);
                      setGeneratingCampaignId(null);
                    }}
                    disabled={generatingCampaignId === campaign.id}
                    className="w-full py-2 border-2 border-dashed border-gray-300 rounded text-gray-500 hover:border-blue-500 hover:text-blue-600"
                  >
                    ➕ צור פוסטים נוספים
                  </button>
                </div>
              </div>
            </div>
          );
        })}

        {filteredCampaigns.length === 0 && (
          <div className="bg-white p-8 rounded-lg shadow text-center text-gray-500">
            אין קמפיינים. לחץ על "קמפיין חדש" ליצירת קמפיין.
          </div>
        )}
      </div>

      {/* Modal לייצור פוסט חדש אחרי מחיקה */}
      {deletedPost && (
        <div 
          className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
          onClick={() => { setLoadingNewPost(false); setDeletedPost(null); }}
        >
          <div className="bg-white p-6 rounded-lg shadow-xl max-w-md" onClick={(e) => e.stopPropagation()}>
            <h3 className="text-lg font-bold mb-4">🗑️ הפוסט נמחק</h3>
            <p className="text-gray-600 mb-4">
              הפוסט לקבוצה <strong>{deletedPost.groupName}</strong> בקמפיין <strong>{deletedPost.campaignName}</strong> נמחק.
            </p>
            <p className="text-sm text-gray-500 mb-4">האם לייצר פוסט חדש לקבוצה זו?</p>
            <div className="flex gap-2 justify-end">
              <button
                type="button"
                onClick={() => {
                  setLoadingNewPost(false);
                  setDeletedPost(null);
                }}
                className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded"
              >
                לא, תודה
              </button>
              <button
                type="button"
                onClick={async () => {
                  if (!deletedPost) return;
                  setLoadingNewPost(true);
                  try {
                    await onRegenerateForGroup(deletedPost.campaignId, deletedPost.groupId);
                  } finally {
                    setLoadingNewPost(false);
                    setDeletedPost(null);
                  }
                }}
                disabled={loadingNewPost}
                className={`px-4 py-2 text-white rounded ${
                  loadingNewPost 
                    ? 'bg-gray-400 cursor-wait' 
                    : 'bg-blue-600 hover:bg-blue-700'
                }`}
              >
                {loadingNewPost ? '⏳ מייצר...' : '✨ ייצר פוסט חדש'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Create Campaign Modal */}
      {showCreateForm && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white p-6 rounded-lg shadow-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
            <h3 className="font-bold text-lg mb-4">✨ יצירת קמפיין חדש</h3>
            <form onSubmit={(e) => {
              e.preventDefault();
              console.log('📋 FeedTab form submit - formData:', formData);
              console.log('📋 FeedTab media_preference:', formData.media_preference);
              onCreate(formData);
              setFormData(emptyFormData);
              setShowCreateForm(false);
            }} className="space-y-4">
              {/* Basic Info */}
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
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">קהל יעד</label>
                <input
                  type="text"
                  value={formData.target_audience}
                  onChange={(e) => setFormData({ ...formData, target_audience: e.target.value })}
                  className="w-full border rounded px-3 py-2"
                  placeholder="למשל: בעלי עסקים קטנים, יזמים"
                />
              </div>

              {/* Groups Selection */}
              <div className="border-t pt-4">
                <h4 className="font-bold text-md mb-3">📁 קבוצות יעד ({formData.target_group_ids.length} נבחרו)</h4>
                <div className="flex gap-2 mb-2">
                  <button type="button" onClick={() => setFormData({ ...formData, target_group_ids: groups.map(g => g.id) })} className="px-2 py-1 text-xs bg-blue-100 text-blue-700 rounded hover:bg-blue-200">בחר הכל</button>
                  <button type="button" onClick={() => setFormData({ ...formData, target_group_ids: [] })} className="px-2 py-1 text-xs bg-gray-100 text-gray-700 rounded hover:bg-gray-200">נקה הכל</button>
                </div>
                <div className="grid grid-cols-2 gap-2 max-h-32 overflow-y-auto">
                  {groups.map((group) => (
                    <label key={group.id} className="flex items-center gap-2 p-2 border rounded hover:bg-gray-50 cursor-pointer text-sm">
                      <input type="checkbox" checked={formData.target_group_ids.includes(group.id)} onChange={(e) => {
                        if (e.target.checked) setFormData({ ...formData, target_group_ids: [...formData.target_group_ids, group.id] });
                        else setFormData({ ...formData, target_group_ids: formData.target_group_ids.filter((id) => id !== group.id) });
                      }} />
                      <span className="truncate">{group.name}</span>
                    </label>
                  ))}
                </div>
              </div>

              {/* Calculator Selection */}
              <div className="border-t pt-4">
                <h4 className="font-bold text-md mb-3">🧮 מחשבון לקמפיין</h4>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium mb-1">סוג בחירה</label>
                    <select value={formData.calculator_mode} onChange={(e) => setFormData({ ...formData, calculator_mode: e.target.value as any, calculator_id: null, calculator_category: null })} className="w-full border rounded px-3 py-2">
                      <option value="specific">מחשבון ספציפי</option>
                      <option value="category">לפי קטגוריה</option>
                    </select>
                  </div>
                  {formData.calculator_mode === 'specific' && (
                    <div>
                      <label className="block text-sm font-medium mb-1">בחר מחשבון</label>
                      <select value={formData.calculator_id || ''} onChange={(e) => {
                        const selectedCalc = calculators.find(c => c.id === Number(e.target.value));
                        setFormData({ ...formData, calculator_id: e.target.value ? Number(e.target.value) : null,
                          ...(selectedCalc && formData.link_placement === 'first_comment' && selectedCalc.target_url ? { auto_responder_template: selectedCalc.target_url } : {})
                        });
                      }} className="w-full border rounded px-3 py-2">
                        <option value="">בחר...</option>
                        {calculators.map((calc) => (<option key={calc.id} value={calc.id}>{calc.name}</option>))}
                      </select>
                      {formData.calculator_id && formData.link_placement === 'first_comment' && (<p className="text-xs text-green-600 mt-1">🔗 קישור לתגובה: {calculators.find(c => c.id === formData.calculator_id)?.target_url}</p>)}
                    </div>
                  )}
                  {formData.calculator_mode === 'category' && (
                    <div>
                      <label className="block text-sm font-medium mb-1">בחר קטגוריה</label>
                      <select value={formData.calculator_category || ''} onChange={(e) => setFormData({ ...formData, calculator_category: e.target.value || null })} className="w-full border rounded px-3 py-2">
                        <option value="">בחר...</option>
                        {calcCategories.map((cat) => (<option key={cat} value={cat}>{cat}</option>))}
                      </select>
                    </div>
                  )}
                </div>
                
                {/* Media Preference Selection */}
                {formData.calculator_id && (() => {
                  const selectedCalc = calculators.find(c => c.id === formData.calculator_id);
                  const hasVideo = (selectedCalc as any)?.youtube_url || (selectedCalc as any)?.demo_video_url;
                  return (
                    <div className="mt-4 border rounded-lg p-3 bg-gradient-to-r from-purple-50 to-blue-50">
                      <label className="block text-sm font-medium mb-2">🎬 סוג מדיה לפוסט</label>
                      <div className="flex gap-4 flex-wrap">
                        <label className="flex items-center gap-2 cursor-pointer">
                          <input type="radio" name="media_pref_simple" value="image" checked={formData.media_preference === 'image'} onChange={() => setFormData({ ...formData, media_preference: 'image' })} />
                          <span>🖼️ תמונה בלבד</span>
                        </label>
                        <label className={`flex items-center gap-2 ${hasVideo ? 'cursor-pointer' : 'opacity-50 cursor-not-allowed'}`}>
                          <input type="radio" name="media_pref_simple" value="video" checked={formData.media_preference === 'video'} onChange={() => setFormData({ ...formData, media_preference: 'video' })} disabled={!hasVideo} />
                          <span>🎥 וידאו בלבד</span>
                        </label>
                        <label className={`flex items-center gap-2 ${hasVideo ? 'cursor-pointer' : 'opacity-50 cursor-not-allowed'}`}>
                          <input type="radio" name="media_pref_simple" value="both" checked={formData.media_preference === 'both'} onChange={() => setFormData({ ...formData, media_preference: 'both' })} disabled={!hasVideo} />
                          <span>🖼️🎥 תמונה + וידאו</span>
                        </label>
                        <label className="flex items-center gap-2 cursor-pointer">
                          <input type="radio" name="media_pref_simple" value="none" checked={formData.media_preference === 'none'} onChange={() => setFormData({ ...formData, media_preference: 'none' })} />
                          <span>📝 טקסט בלבד</span>
                        </label>
                      </div>
                      {!hasVideo && <p className="text-xs text-amber-600 mt-2">⚠️ למחשבון זה אין וידאו ביוטיוב - העלה קודם מעמוד המחשבונים</p>}
                      {hasVideo && (formData.media_preference === 'video' || formData.media_preference === 'both') && (
                        <div className="mt-3 p-2 bg-white rounded border">
                          <p className="text-xs text-gray-600 mb-2">📺 תצוגה מקדימה:</p>
                          <div className="aspect-video max-w-sm">
                            <iframe src={`https://www.youtube.com/embed/${(selectedCalc as any)?.youtube_url?.split('/').pop()?.split('?')[0]}`} className="w-full h-full rounded" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowFullScreen />
                          </div>
                          <a href={(selectedCalc as any)?.youtube_url || ''} target="_blank" rel="noopener noreferrer" className="text-xs text-blue-600 hover:underline mt-1 block">🔗 {(selectedCalc as any)?.youtube_url}</a>
                        </div>
                      )}
                    </div>
                  );
                })()}
                
                <div className="grid grid-cols-2 gap-4 mt-4">
                  <div>
                    <label className="block text-sm font-medium mb-1">מיקום הקישור</label>
                    <select value={formData.link_placement} onChange={(e) => {
                      const newPlacement = e.target.value as 'first_comment' | 'none';
                      const selectedCalc = calculators.find(c => c.id === formData.calculator_id);
                      setFormData({ ...formData, link_placement: newPlacement,
                        ...(selectedCalc && newPlacement === 'first_comment' && selectedCalc.target_url ? { auto_responder_template: selectedCalc.target_url } : {})
                      });
                    }} className="w-full border rounded px-3 py-2">
                      <option value="first_comment">בתגובה ראשונה (מומלץ!)</option>
                      <option value="none">ללא קישור</option>
                    </select>
                    <p className="text-xs text-gray-500 mt-1">💡 הקישור נשלח בתגובה נפרדת כדי לעקוף אנטי-ספאם</p>
                  </div>
                </div>
              </div>
              
              {/* Strategies Selection */}
              <div className="border-t pt-4">
                <h4 className="font-bold text-md mb-2">📝 אסטרטגיות כתיבה ({formData.strategy_ids.length} נבחרו)</h4>
                
                {/* Hint: Match strategies to groups */}
                {formData.target_group_ids.length > 0 && (
                  <div className={`mb-3 p-2 rounded text-sm ${
                    formData.strategy_ids.length === formData.target_group_ids.length 
                      ? 'bg-green-50 border border-green-200 text-green-700'
                      : formData.strategy_ids.length === 0
                        ? 'bg-yellow-50 border border-yellow-200 text-yellow-700'
                        : 'bg-blue-50 border border-blue-200 text-blue-700'
                  }`}>
                    💡 {formData.target_group_ids.length} קבוצות = {formData.target_group_ids.length} פוסטים. 
                    {formData.strategy_ids.length === formData.target_group_ids.length 
                      ? ' מספר האסטרטגיות תואם!' 
                      : ` מומלץ לבחור ${formData.target_group_ids.length} אסטרטגיות.`}
                  </div>
                )}
                
                <div className="flex flex-wrap gap-2 mb-2">
                  {formData.target_group_ids.length > 0 && (
                    <button type="button" onClick={() => {
                      const count = formData.target_group_ids.length;
                      const shuffled = [...strategies].sort(() => Math.random() - 0.5);
                      const selected = shuffled.slice(0, Math.min(count, strategies.length)).map(s => s.id);
                      setFormData({ ...formData, strategy_ids: selected });
                    }} className="px-3 py-1 text-xs bg-green-100 text-green-700 rounded hover:bg-green-200 font-medium">
                      🎲 בחר {formData.target_group_ids.length} אקראיות
                    </button>
                  )}
                  <button type="button" onClick={() => setFormData({ ...formData, strategy_ids: strategies.map(s => s.id) })} className="px-2 py-1 text-xs bg-blue-100 text-blue-700 rounded hover:bg-blue-200">בחר הכל</button>
                  <button type="button" onClick={() => setFormData({ ...formData, strategy_ids: [] })} className="px-2 py-1 text-xs bg-gray-100 text-gray-700 rounded hover:bg-gray-200">נקה הכל</button>
                </div>
                <div className="grid grid-cols-2 md:grid-cols-3 gap-2 max-h-48 overflow-y-auto">
                  {strategies.map((strategy) => (
                    <label key={strategy.id} className="flex items-center gap-2 p-2 border rounded hover:bg-gray-50 cursor-pointer">
                      <input type="checkbox" checked={formData.strategy_ids.includes(strategy.id)} onChange={(e) => {
                        if (e.target.checked) setFormData({ ...formData, strategy_ids: [...formData.strategy_ids, strategy.id] });
                        else setFormData({ ...formData, strategy_ids: formData.strategy_ids.filter((id) => id !== strategy.id) });
                      }} />
                      <span className="text-lg">{strategy.icon}</span>
                      <span className="text-sm">{strategy.name}</span>
                    </label>
                  ))}
                </div>
              </div>
              
              {/* Auto-Responder */}
              <div className="border-t pt-4">
                <div className="flex items-center gap-3 mb-3">
                  <h4 className="font-bold text-md">🤖 Auto-Responder</h4>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input type="checkbox" checked={formData.auto_responder_enabled} onChange={(e) => setFormData({ ...formData, auto_responder_enabled: e.target.checked })} className="sr-only peer" />
                    <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                  </label>
                </div>
                {formData.auto_responder_enabled && (
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div>
                      <label className="block text-sm font-medium mb-1">סוג תגובה</label>
                      <select value={formData.auto_responder_type} onChange={(e) => setFormData({ ...formData, auto_responder_type: e.target.value as any })} className="w-full border rounded px-3 py-2">
                        <option value="comment">תגובה</option>
                        <option value="messenger">מסנג'ר</option>
                        <option value="ai_decide">AI מחליט</option>
                      </select>
                    </div>
                    <div>
                      <label className="block text-sm font-medium mb-1">עיכוב (דקות)</label>
                      <input type="number" min="0" max="60" value={formData.auto_responder_delay_minutes} onChange={(e) => setFormData({ ...formData, auto_responder_delay_minutes: parseInt(e.target.value) })} className="w-full border rounded px-3 py-2" />
                    </div>
                    <div>
                      <label className="block text-sm font-medium mb-1">מגבלה יומית</label>
                      <input type="number" min="1" max="200" value={formData.auto_responder_daily_limit} onChange={(e) => setFormData({ ...formData, auto_responder_daily_limit: parseInt(e.target.value) })} className="w-full border rounded px-3 py-2" />
                    </div>
                  </div>
                )}
              </div>

              <div className="flex gap-2 justify-end pt-4 border-t">
                <button type="button" onClick={() => { setShowCreateForm(false); setFormData(emptyFormData); }} className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded">ביטול</button>
                <button type="submit" className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700">✨ צור קמפיין</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Edit Campaign Modal */}
      {editingCampaign && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white p-6 rounded-lg shadow-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
            <h3 className="font-bold text-lg mb-4">✏️ עריכת קמפיין: {editingCampaign.name}</h3>
            <form onSubmit={(e) => {
              e.preventDefault();
              onUpdateCampaign(editingCampaign.id, editFormData);
              setEditingCampaign(null);
            }} className="space-y-4">
              {/* Basic Info */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-1">שם הקמפיין</label>
                  <input type="text" value={editFormData.name} onChange={(e) => setEditFormData({ ...editFormData, name: e.target.value })} className="w-full border rounded px-3 py-2" required />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">נושא</label>
                  <input type="text" value={editFormData.topic} onChange={(e) => setEditFormData({ ...editFormData, topic: e.target.value })} className="w-full border rounded px-3 py-2" required />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">קהל יעד</label>
                <input type="text" value={editFormData.target_audience} onChange={(e) => setEditFormData({ ...editFormData, target_audience: e.target.value })} className="w-full border rounded px-3 py-2" />
              </div>

              {/* Groups Selection */}
              <div className="border-t pt-4">
                <h4 className="font-bold text-md mb-3">📁 קבוצות יעד ({editFormData.target_group_ids.length} נבחרו)</h4>
                <div className="flex gap-2 mb-2">
                  <button type="button" onClick={() => setEditFormData({ ...editFormData, target_group_ids: groups.map(g => g.id) })} className="px-2 py-1 text-xs bg-blue-100 text-blue-700 rounded hover:bg-blue-200">בחר הכל</button>
                  <button type="button" onClick={() => setEditFormData({ ...editFormData, target_group_ids: [] })} className="px-2 py-1 text-xs bg-gray-100 text-gray-700 rounded hover:bg-gray-200">נקה הכל</button>
                </div>
                <div className="grid grid-cols-2 gap-2 max-h-32 overflow-y-auto">
                  {groups.map((group) => (
                    <label key={group.id} className="flex items-center gap-2 p-2 border rounded hover:bg-gray-50 cursor-pointer text-sm">
                      <input type="checkbox" checked={editFormData.target_group_ids.includes(group.id)} onChange={(e) => {
                        if (e.target.checked) setEditFormData({ ...editFormData, target_group_ids: [...editFormData.target_group_ids, group.id] });
                        else setEditFormData({ ...editFormData, target_group_ids: editFormData.target_group_ids.filter((id) => id !== group.id) });
                      }} />
                      <span className="truncate">{group.name}</span>
                    </label>
                  ))}
                </div>
              </div>

              {/* Calculator Selection */}
              <div className="border-t pt-4">
                <h4 className="font-bold text-md mb-3">🧮 מחשבון לקמפיין</h4>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium mb-1">סוג בחירה</label>
                    <select value={editFormData.calculator_mode} onChange={(e) => setEditFormData({ ...editFormData, calculator_mode: e.target.value as any, calculator_id: null, calculator_category: null })} className="w-full border rounded px-3 py-2">
                      <option value="specific">מחשבון ספציפי</option>
                      <option value="category">לפי קטגוריה</option>
                    </select>
                  </div>
                  {editFormData.calculator_mode === 'specific' && (
                    <div>
                      <label className="block text-sm font-medium mb-1">בחר מחשבון</label>
                      <select value={editFormData.calculator_id || ''} onChange={(e) => {
                        const selectedCalc = calculators.find(c => c.id === Number(e.target.value));
                        setEditFormData({ ...editFormData, calculator_id: e.target.value ? Number(e.target.value) : null,
                          ...(selectedCalc && editFormData.link_placement === 'first_comment' && selectedCalc.target_url ? { auto_responder_template: selectedCalc.target_url } : {})
                        });
                      }} className="w-full border rounded px-3 py-2">
                        <option value="">בחר...</option>
                        {calculators.map((calc) => (<option key={calc.id} value={calc.id}>{calc.name}</option>))}
                      </select>
                    </div>
                  )}
                  {editFormData.calculator_mode === 'category' && (
                    <div>
                      <label className="block text-sm font-medium mb-1">בחר קטגוריה</label>
                      <select value={editFormData.calculator_category || ''} onChange={(e) => setEditFormData({ ...editFormData, calculator_category: e.target.value || null })} className="w-full border rounded px-3 py-2">
                        <option value="">בחר...</option>
                        {calcCategories.map((cat) => (<option key={cat} value={cat}>{cat}</option>))}
                      </select>
                    </div>
                  )}
                  <div>
                    <label className="block text-sm font-medium mb-1">מיקום הקישור</label>
                    <select value={editFormData.link_placement} onChange={(e) => {
                      const newPlacement = e.target.value as 'first_comment' | 'none';
                      const selectedCalc = calculators.find(c => c.id === editFormData.calculator_id);
                      setEditFormData({ ...editFormData, link_placement: newPlacement,
                        ...(selectedCalc && newPlacement === 'first_comment' && selectedCalc.target_url ? { auto_responder_template: selectedCalc.target_url } : {})
                      });
                    }} className="w-full border rounded px-3 py-2">
                      <option value="first_comment">בתגובה ראשונה (מומלץ!)</option>
                      <option value="none">ללא קישור</option>
                    </select>
                  </div>
                </div>
              </div>
              
              {/* Strategies Selection */}
              <div className="border-t pt-4">
                <h4 className="font-bold text-md mb-2">📝 אסטרטגיות כתיבה ({editFormData.strategy_ids.length} נבחרו)</h4>
                
                {/* Hint: Match strategies to groups */}
                {editFormData.target_group_ids.length > 0 && (
                  <div className={`mb-3 p-2 rounded text-sm ${
                    editFormData.strategy_ids.length === editFormData.target_group_ids.length 
                      ? 'bg-green-50 border border-green-200 text-green-700'
                      : editFormData.strategy_ids.length === 0
                        ? 'bg-yellow-50 border border-yellow-200 text-yellow-700'
                        : 'bg-blue-50 border border-blue-200 text-blue-700'
                  }`}>
                    💡 {editFormData.target_group_ids.length} קבוצות = {editFormData.target_group_ids.length} פוסטים. 
                    {editFormData.strategy_ids.length === editFormData.target_group_ids.length 
                      ? ' מספר האסטרטגיות תואם!' 
                      : ` מומלץ לבחור ${editFormData.target_group_ids.length} אסטרטגיות.`}
                  </div>
                )}
                
                <div className="flex flex-wrap gap-2 mb-2">
                  {editFormData.target_group_ids.length > 0 && (
                    <button type="button" onClick={() => {
                      const count = editFormData.target_group_ids.length;
                      const shuffled = [...strategies].sort(() => Math.random() - 0.5);
                      const selected = shuffled.slice(0, Math.min(count, strategies.length)).map(s => s.id);
                      setEditFormData({ ...editFormData, strategy_ids: selected });
                    }} className="px-3 py-1 text-xs bg-green-100 text-green-700 rounded hover:bg-green-200 font-medium">
                      🎲 בחר {editFormData.target_group_ids.length} אקראיות
                    </button>
                  )}
                  <button type="button" onClick={() => setEditFormData({ ...editFormData, strategy_ids: strategies.map(s => s.id) })} className="px-2 py-1 text-xs bg-blue-100 text-blue-700 rounded hover:bg-blue-200">בחר הכל</button>
                  <button type="button" onClick={() => setEditFormData({ ...editFormData, strategy_ids: [] })} className="px-2 py-1 text-xs bg-gray-100 text-gray-700 rounded hover:bg-gray-200">נקה הכל</button>
                </div>
                <div className="grid grid-cols-2 md:grid-cols-3 gap-2 max-h-48 overflow-y-auto">
                  {strategies.map((strategy) => (
                    <label key={strategy.id} className="flex items-center gap-2 p-2 border rounded hover:bg-gray-50 cursor-pointer">
                      <input type="checkbox" checked={editFormData.strategy_ids.includes(strategy.id)} onChange={(e) => {
                        if (e.target.checked) setEditFormData({ ...editFormData, strategy_ids: [...editFormData.strategy_ids, strategy.id] });
                        else setEditFormData({ ...editFormData, strategy_ids: editFormData.strategy_ids.filter((id) => id !== strategy.id) });
                      }} />
                      <span className="text-lg">{strategy.icon}</span>
                      <span className="text-sm">{strategy.name}</span>
                    </label>
                  ))}
                </div>
              </div>
              
              {/* Auto-Responder */}
              <div className="border-t pt-4">
                <div className="flex items-center gap-3 mb-3">
                  <h4 className="font-bold text-md">🤖 Auto-Responder</h4>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input type="checkbox" checked={editFormData.auto_responder_enabled} onChange={(e) => setEditFormData({ ...editFormData, auto_responder_enabled: e.target.checked })} className="sr-only peer" />
                    <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                  </label>
                </div>
                {editFormData.auto_responder_enabled && (
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div>
                      <label className="block text-sm font-medium mb-1">סוג תגובה</label>
                      <select value={editFormData.auto_responder_type} onChange={(e) => setEditFormData({ ...editFormData, auto_responder_type: e.target.value as any })} className="w-full border rounded px-3 py-2">
                        <option value="comment">תגובה</option>
                        <option value="messenger">מסנג'ר</option>
                        <option value="ai_decide">AI מחליט</option>
                      </select>
                    </div>
                    <div>
                      <label className="block text-sm font-medium mb-1">עיכוב (דקות)</label>
                      <input type="number" min="0" max="60" value={editFormData.auto_responder_delay_minutes} onChange={(e) => setEditFormData({ ...editFormData, auto_responder_delay_minutes: parseInt(e.target.value) })} className="w-full border rounded px-3 py-2" />
                    </div>
                    <div>
                      <label className="block text-sm font-medium mb-1">מגבלה יומית</label>
                      <input type="number" min="1" max="200" value={editFormData.auto_responder_daily_limit} onChange={(e) => setEditFormData({ ...editFormData, auto_responder_daily_limit: parseInt(e.target.value) })} className="w-full border rounded px-3 py-2" />
                    </div>
                  </div>
                )}
              </div>

              <div className="flex gap-2 justify-end pt-4 border-t">
                <button type="button" onClick={() => setEditingCampaign(null)} className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded">ביטול</button>
                <button type="submit" className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700">💾 שמור שינויים</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Delete Campaign Confirmation Modal */}
      {campaignToDelete && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
            <h3 className="text-lg font-bold text-red-600 mb-4">🗑️ מחיקת קמפיין</h3>
            <p className="text-gray-700 mb-4">
              האם אתה בטוח שברצונך למחוק את הקמפיין <strong>&ldquo;{campaignToDelete.name}&rdquo;</strong>?
            </p>
            <p className="text-gray-500 text-sm mb-4">
              פעולה זו תמחק את הקמפיין וכל הפוסטים שנוצרו. לא ניתן לבטל פעולה זו.
            </p>
            <div className="flex gap-3 justify-end">
              <button
                type="button"
                onClick={() => setCampaignToDelete(null)}
                className="px-4 py-2 bg-gray-200 text-gray-700 rounded hover:bg-gray-300"
                disabled={deletingCampaignId !== null}
              >
                ביטול
              </button>
              <button
                type="button"
                onClick={handleDeleteCampaign}
                disabled={deletingCampaignId !== null}
                className={`px-4 py-2 text-white rounded ${
                  deletingCampaignId !== null 
                    ? 'bg-gray-400 cursor-wait' 
                    : 'bg-red-600 hover:bg-red-700'
                }`}
              >
                {deletingCampaignId !== null ? '⏳ מוחק...' : '🗑️ מחק קמפיין'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
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

      {/* Anti-Spam Stats */}
      {stats.anti_spam && (
        <div className="bg-white p-6 rounded-lg shadow border-t-4 border-red-500">
          <h3 className="text-lg font-bold mb-4">🛡️ הגנת Anti-Spam</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="text-center">
              <div className="text-2xl font-bold text-blue-600">
                {stats.anti_spam.posts_today}/{stats.anti_spam.max_posts_today}
              </div>
              <div className="text-sm text-gray-500">פוסטים היום</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-green-600">
                {stats.anti_spam.remaining_today}
              </div>
              <div className="text-sm text-gray-500">נותרו היום</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-purple-600">
                {stats.anti_spam.groups_posted_this_week}
              </div>
              <div className="text-sm text-gray-500">קבוצות השבוע</div>
            </div>
            <div className="text-center">
              <div className={`text-2xl font-bold ${stats.anti_spam.can_post_now ? 'text-green-600' : 'text-red-600'}`}>
                {stats.anti_spam.can_post_now ? '✅' : '⛔'}
              </div>
              <div className="text-sm text-gray-500">
                {stats.anti_spam.can_post_now ? 'מותר לפרסם' : 'מחוץ לשעות'}
              </div>
            </div>
          </div>
          <div className="mt-4 text-sm text-gray-500 text-center">
            🕐 שעות פרסום: {stats.anti_spam.posting_hours} | 
            ⏱️ השהייה: {Math.floor(stats.anti_spam.min_delay_seconds/60)}-{Math.floor(stats.anti_spam.max_delay_seconds/60)} דקות בין פוסטים
          </div>
        </div>
      )}
    </div>
  );
};

// ========== Groups Tab ==========
const GroupsTab: React.FC<{
  groups: Group[];
  onAdd: (data: Partial<Group>) => void;
  onSearch: (query: string) => void;
  onRemove: (groupId: number) => void;
  onUpdate: (groupId: number, data: Partial<Group>) => void;
}> = ({ groups, onAdd, onSearch, onRemove, onUpdate }) => {
  const [showAddForm, setShowAddForm] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [formData, setFormData] = useState({ fb_group_id: '', name: '', url: '', category: '' });
  const [removingId, setRemovingId] = useState<number | null>(null);
  const [editingGroup, setEditingGroup] = useState<Group | null>(null);
  const [editFormData, setEditFormData] = useState({ name: '', url: '', category: '', is_active: true, auto_reply_enabled: true });

  const extractGroupId = (url: string): string => {
    const match = url.match(/facebook\.com\/groups\/([^/?&#]+)/);
    return match ? match[1] : '';
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const groupId = extractGroupId(formData.url);
    if (!groupId) return;
    onAdd({ ...formData, fb_group_id: groupId });
    setFormData({ fb_group_id: '', name: '', url: '', category: '' });
    setShowAddForm(false);
  };

  const startEditing = (group: Group) => {
    setEditingGroup(group);
    setEditFormData({
      name: group.name,
      url: group.url || '',
      category: group.category || '',
      is_active: group.is_active,
      auto_reply_enabled: group.auto_reply_enabled ?? true,
    });
  };

  const handleEditSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (editingGroup) {
      onUpdate(editingGroup.id, editFormData);
      setEditingGroup(null);
    }
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
              type="url"
              placeholder="קישור לקבוצה (https://www.facebook.com/groups/...)"
              value={formData.url}
              onChange={(e) => setFormData({ ...formData, url: e.target.value })}
              className="border rounded px-3 py-2 col-span-2"
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
              placeholder="קטגוריה"
              value={formData.category}
              onChange={(e) => setFormData({ ...formData, category: e.target.value })}
              className="border rounded px-3 py-2"
            />
          </div>
          {formData.url && !extractGroupId(formData.url) && (
            <p className="text-xs text-red-500">לא ניתן לחלץ מזהה קבוצה מה-URL. ודא שהקישור בפורמט facebook.com/groups/...</p>
          )}
          {formData.url && extractGroupId(formData.url) && (
            <p className="text-xs text-green-600">מזהה קבוצה: {extractGroupId(formData.url)}</p>
          )}
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
              <th className="px-4 py-3 text-right text-sm font-medium text-gray-500">פעולות</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {groups.map((group) => (
              <React.Fragment key={group.id}>
                <tr className="hover:bg-gray-50">
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
                  <td className="px-4 py-3">
                    <div className="flex gap-1">
                      <button
                        onClick={() => startEditing(group)}
                        className="px-2 py-1 bg-blue-100 text-blue-600 rounded text-xs hover:bg-blue-200"
                        title="ערוך"
                      >
                        ✏️ ערוך
                      </button>
                      {removingId === group.id ? (
                        <div className="flex gap-1 items-center">
                          <span className="text-xs text-red-600">בטוח?</span>
                          <button
                            onClick={() => { onRemove(group.id); setRemovingId(null); }}
                            className="px-2 py-1 bg-red-600 text-white rounded text-xs hover:bg-red-700"
                          >
                            כן
                          </button>
                          <button
                            onClick={() => setRemovingId(null)}
                            className="px-2 py-1 bg-gray-200 rounded text-xs hover:bg-gray-300"
                          >
                            לא
                          </button>
                        </div>
                      ) : (
                        <button
                          onClick={() => setRemovingId(group.id)}
                          className="px-2 py-1 bg-red-100 text-red-600 rounded text-xs hover:bg-red-200"
                        >
                          הסר
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
                {editingGroup?.id === group.id && (
                  <tr>
                    <td colSpan={6} className="px-0 py-0">
                      <form onSubmit={handleEditSubmit} className="bg-white p-4 shadow-inner border-t border-b border-blue-100 space-y-4">
                        <h4 className="font-bold text-sm text-blue-700">✏️ עריכת קבוצה: {group.name}</h4>
                        <div className="grid grid-cols-2 gap-4">
                          <div>
                            <label className="block text-xs font-medium text-gray-600 mb-1">שם הקבוצה</label>
                            <input
                              type="text"
                              value={editFormData.name}
                              onChange={(e) => setEditFormData({ ...editFormData, name: e.target.value })}
                              className="w-full border rounded px-3 py-2 text-sm"
                              required
                            />
                          </div>
                          <div>
                            <label className="block text-xs font-medium text-gray-600 mb-1">URL</label>
                            <input
                              type="text"
                              value={editFormData.url}
                              onChange={(e) => setEditFormData({ ...editFormData, url: e.target.value })}
                              className="w-full border rounded px-3 py-2 text-sm"
                            />
                          </div>
                          <div>
                            <label className="block text-xs font-medium text-gray-600 mb-1">קטגוריה</label>
                            <input
                              type="text"
                              value={editFormData.category}
                              onChange={(e) => setEditFormData({ ...editFormData, category: e.target.value })}
                              className="w-full border rounded px-3 py-2 text-sm"
                            />
                          </div>
                          <div className="flex items-end gap-6">
                            <label className="flex items-center gap-2 cursor-pointer">
                              <input
                                type="checkbox"
                                checked={editFormData.is_active}
                                onChange={(e) => setEditFormData({ ...editFormData, is_active: e.target.checked })}
                                className="w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                              />
                              <span className="text-sm">פעילה</span>
                            </label>
                            <label className="flex items-center gap-2 cursor-pointer">
                              <input
                                type="checkbox"
                                checked={editFormData.auto_reply_enabled}
                                onChange={(e) => setEditFormData({ ...editFormData, auto_reply_enabled: e.target.checked })}
                                className="w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                              />
                              <span className="text-sm">מענה אוטומטי</span>
                            </label>
                          </div>
                        </div>
                        <div className="flex gap-2">
                          <button type="submit" className="px-4 py-2 bg-blue-600 text-white rounded text-sm hover:bg-blue-700">
                            שמור
                          </button>
                          <button type="button" onClick={() => setEditingGroup(null)} className="px-4 py-2 bg-gray-200 rounded text-sm hover:bg-gray-300">
                            ביטול
                          </button>
                        </div>
                      </form>
                    </td>
                  </tr>
                )}
              </React.Fragment>
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
  onGenerate: (id: number) => Promise<void>;
  onUpdate: (id: number, data: any) => void;
  onDelete: (id: number) => Promise<void>;
}> = ({ campaigns, groups, onCreate, onGenerate, onUpdate, onDelete }) => {
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [editingCampaign, setEditingCampaign] = useState<Campaign | null>(null);
  const [expandedCampaign, setExpandedCampaign] = useState<number | null>(null);
  const [groupSearch, setGroupSearch] = useState('');
  const [generatingCampaignId, setGeneratingCampaignId] = useState<number | null>(null);
  const [campaignToDelete, setCampaignToDelete] = useState<Campaign | null>(null);
  const [deletingCampaignId, setDeletingCampaignId] = useState<number | null>(null);
  
  // Delete campaign handler
  const handleDeleteCampaign = async () => {
    if (!campaignToDelete) return;
    setDeletingCampaignId(campaignToDelete.id);
    try {
      await onDelete(campaignToDelete.id);
    } catch (err) {
      console.error('Error deleting campaign:', err);
    }
    setDeletingCampaignId(null);
    setCampaignToDelete(null);
  };
  
  // Calculators and strategies state
  const [calculators, setCalculators] = useState<Calculator[]>([]);
  const [strategies, setStrategies] = useState<PostStrategy[]>([]);
  const [calcCategories, setCalcCategories] = useState<string[]>([]);
  
  // Extended form data with new fields
  const [formData, setFormData] = useState({
    name: '',
    topic: 'מחשבונים פיננסיים להטמעה בחינם',
    target_audience: '',
    target_group_ids: [] as number[],
    image_percentage: 50,
    // New fields
    calculator_id: null as number | null,
    calculator_mode: 'all' as 'specific' | 'all' | 'category',
    calculator_category: null as string | null,
    strategy_ids: [] as number[],
    link_placement: 'first_comment' as 'first_comment' | 'none',  // הקישור תמיד בתגובה ראשונה
    auto_responder_enabled: false,
    auto_responder_type: 'comment' as 'comment' | 'messenger' | 'ai_decide',
    auto_responder_template: '',
    auto_responder_delay_minutes: 5,
    auto_responder_daily_limit: 50,
    media_preference: 'image' as 'image' | 'video' | 'both' | 'none',
  });
  const [editFormData, setEditFormData] = useState({
    name: '',
    topic: '',
    target_audience: '',
    image_percentage: 50,
    target_group_ids: [] as number[],
    // New fields
    calculator_id: null as number | null,
    calculator_mode: 'all' as 'specific' | 'all' | 'category',
    calculator_category: null as string | null,
    strategy_ids: [] as number[],
    link_placement: 'first_comment' as 'first_comment' | 'none',  // הקישור תמיד בתגובה ראשונה
    auto_responder_enabled: false,
    auto_responder_type: 'comment' as 'comment' | 'messenger' | 'ai_decide',
    auto_responder_template: '',
    auto_responder_delay_minutes: 5,
    auto_responder_daily_limit: 50,
    media_preference: 'image' as 'image' | 'video' | 'both' | 'none',
  });
  const [editGroupSearch, setEditGroupSearch] = useState('');
  
  // Fetch calculators and strategies on mount
  useEffect(() => {
    const fetchData = async () => {
      try {
        const [calcRes, stratRes, catRes] = await Promise.all([
          fetch(`${API_BASE}/calculators`),
          fetch(`${API_BASE.replace('/facebook', '/strategies')}`),
          fetch(`${API_BASE}/calculator-categories`),
        ]);
        
        if (calcRes.ok) setCalculators(await calcRes.json());
        if (stratRes.ok) setStrategies(await stratRes.json());
        if (catRes.ok) {
          const data = await catRes.json();
          setCalcCategories(data.categories || []);
        }
      } catch (error) {
        console.error('Error fetching data:', error);
      }
    };
    fetchData();
  }, []);

  // Filter groups by search
  const filteredGroups = groups.filter(g => 
    g.name.toLowerCase().includes(groupSearch.toLowerCase()) ||
    g.fb_group_id.includes(groupSearch)
  );

  // Filter groups for edit modal
  const filteredEditGroups = groups.filter(g => 
    g.name.toLowerCase().includes(editGroupSearch.toLowerCase()) ||
    g.fb_group_id.includes(editGroupSearch)
  );

  const startEdit = (campaign: Campaign) => {
    setEditingCampaign(campaign);
    setEditFormData({
      name: campaign.name,
      topic: campaign.topic,
      target_audience: campaign.target_audience || '',
      image_percentage: campaign.image_percentage,
      target_group_ids: campaign.target_group_ids || [],
      calculator_id: campaign.calculator_id,
      calculator_mode: campaign.calculator_mode || 'all',
      calculator_category: campaign.calculator_category,
      strategy_ids: campaign.strategy_ids || [],
      link_placement: campaign.link_placement === 'none' ? 'none' : 'first_comment',  // תיקון: הקישור תמיד בתגובה
      auto_responder_enabled: campaign.auto_responder_enabled || false,
      auto_responder_type: campaign.auto_responder_type || 'comment',
      auto_responder_template: campaign.auto_responder_template || '',
      auto_responder_delay_minutes: campaign.auto_responder_delay_minutes || 5,
      auto_responder_daily_limit: campaign.auto_responder_daily_limit || 50,
      media_preference: campaign.media_preference || 'image',
    });
    setEditGroupSearch('');
  };

  const handleEditSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (editingCampaign) {
      onUpdate(editingCampaign.id, editFormData);
      setEditingCampaign(null);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onCreate(formData);
    setFormData({ 
      name: '', 
      topic: 'מחשבונים פיננסיים להטמעה בחינם', 
      target_audience: '', 
      target_group_ids: [], 
      image_percentage: 50,
      calculator_id: null,
      calculator_mode: 'all',
      calculator_category: null,
      strategy_ids: [],
      link_placement: 'first_comment',  // הקישור תמיד בתגובה ראשונה
      auto_responder_enabled: false,
      auto_responder_type: 'comment',
      auto_responder_template: '',
      auto_responder_delay_minutes: 5,
      auto_responder_daily_limit: 50,
      media_preference: 'image',
    });
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
          
          {/* Calculator Selection */}
          <div className="border-t pt-4">
            <h4 className="font-bold text-md mb-3">🧮 בחירת מחשבון</h4>
            <div className="grid grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium mb-1">מצב בחירה</label>
                <select
                  value={formData.calculator_mode}
                  onChange={(e) => setFormData({ ...formData, calculator_mode: e.target.value as any })}
                  className="w-full border rounded px-3 py-2"
                >
                  <option value="all">כל המחשבונים (רוטציה)</option>
                  <option value="specific">מחשבון ספציפי</option>
                  <option value="category">קטגוריה</option>
                </select>
              </div>
              {formData.calculator_mode === 'specific' && (
                <div>
                  <label className="block text-sm font-medium mb-1">בחר מחשבון</label>
                  <select
                    value={formData.calculator_id || ''}
                    onChange={(e) => {
                      const calcId = e.target.value ? parseInt(e.target.value) : null;
                      // מילוי אוטומטי של קישור המחשבון
                      const selectedCalc = calculators.find(c => c.id === calcId);
                      setFormData({ 
                        ...formData, 
                        calculator_id: calcId,
                        // אם הקישור בתגובה ראשונה - ממלאים אוטומטית את הקישור
                        ...(selectedCalc && formData.link_placement === 'first_comment' && selectedCalc.target_url ? {
                          auto_responder_template: selectedCalc.target_url
                        } : {})
                      });
                    }}
                    className="w-full border rounded px-3 py-2"
                  >
                    <option value="">בחר...</option>
                    {calculators.map((calc) => (
                      <option key={calc.id} value={calc.id}>{calc.name}</option>
                    ))}
                  </select>
                  {/* הצגת הקישור שיישלח בתגובה ראשונה */}
                  {formData.calculator_id && formData.link_placement === 'first_comment' && (
                    <p className="text-xs text-green-600 mt-1">
                      🔗 קישור לתגובה: {calculators.find(c => c.id === formData.calculator_id)?.target_url}
                    </p>
                  )}
                </div>
              )}
              {formData.calculator_mode === 'category' && (
                <div>
                  <label className="block text-sm font-medium mb-1">בחר קטגוריה</label>
                  <select
                    value={formData.calculator_category || ''}
                    onChange={(e) => setFormData({ ...formData, calculator_category: e.target.value || null })}
                    className="w-full border rounded px-3 py-2"
                  >
                    <option value="">בחר...</option>
                    {calcCategories.map((cat) => (
                      <option key={cat} value={cat}>{cat}</option>
                    ))}
                  </select>
                </div>
              )}
              
              {/* Media Preference Selection */}
              {formData.calculator_id && (() => {
                const selectedCalc = calculators.find(c => c.id === formData.calculator_id);
                const hasVideo = selectedCalc?.youtube_url || selectedCalc?.demo_video_url;
                return (
                  <div className="col-span-2 border rounded-lg p-3 bg-gray-50">
                    <label className="block text-sm font-medium mb-2">🎬 סוג מדיה לפוסט</label>
                    <div className="flex gap-3 flex-wrap">
                      <label className="flex items-center gap-2 cursor-pointer">
                        <input
                          type="radio"
                          name="media_preference"
                          value="image"
                          checked={formData.media_preference === 'image'}
                          onChange={(e) => setFormData({ ...formData, media_preference: 'image' })}
                        />
                        <span>🖼️ תמונה בלבד</span>
                      </label>
                      <label className={`flex items-center gap-2 ${hasVideo ? 'cursor-pointer' : 'opacity-50 cursor-not-allowed'}`}>
                        <input
                          type="radio"
                          name="media_preference"
                          value="video"
                          checked={formData.media_preference === 'video'}
                          onChange={(e) => setFormData({ ...formData, media_preference: 'video' })}
                          disabled={!hasVideo}
                        />
                        <span>🎥 וידאו בלבד</span>
                      </label>
                      <label className={`flex items-center gap-2 ${hasVideo ? 'cursor-pointer' : 'opacity-50 cursor-not-allowed'}`}>
                        <input
                          type="radio"
                          name="media_preference"
                          value="both"
                          checked={formData.media_preference === 'both'}
                          onChange={(e) => setFormData({ ...formData, media_preference: 'both' })}
                          disabled={!hasVideo}
                        />
                        <span>🖼️🎥 תמונה + וידאו</span>
                      </label>
                      <label className="flex items-center gap-2 cursor-pointer">
                        <input
                          type="radio"
                          name="media_preference"
                          value="none"
                          checked={formData.media_preference === 'none'}
                          onChange={(e) => setFormData({ ...formData, media_preference: 'none' })}
                        />
                        <span>📝 טקסט בלבד</span>
                      </label>
                    </div>
                    {!hasVideo && (
                      <p className="text-xs text-amber-600 mt-2">⚠️ למחשבון זה אין וידאו ביוטיוב - העלה קודם מעמוד המחשבונים</p>
                    )}
                    {hasVideo && (formData.media_preference === 'video' || formData.media_preference === 'both') && (
                      <div className="mt-3 p-2 bg-white rounded border">
                        <p className="text-xs text-gray-600 mb-2">📺 תצוגה מקדימה של הוידאו:</p>
                        <div className="aspect-video max-w-md">
                          <iframe
                            src={`https://www.youtube.com/embed/${selectedCalc?.youtube_url?.split('/').pop()?.split('?')[0]}`}
                            className="w-full h-full rounded"
                            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                            allowFullScreen
                          />
                        </div>
                        <a 
                          href={selectedCalc?.youtube_url || ''} 
                          target="_blank" 
                          rel="noopener noreferrer"
                          className="text-xs text-blue-600 hover:underline mt-1 block"
                        >
                          🔗 {selectedCalc?.youtube_url}
                        </a>
                      </div>
                    )}
                  </div>
                );
              })()}
              
              <div>
                <label className="block text-sm font-medium mb-1">מיקום הקישור</label>
                <select
                  value={formData.link_placement}
                  onChange={(e) => {
                    const newPlacement = e.target.value as 'first_comment' | 'none';
                    // אם עוברים לתגובה ראשונה וכבר נבחר מחשבון - ממלאים את הקישור
                    const selectedCalc = calculators.find(c => c.id === formData.calculator_id);
                    setFormData({ 
                      ...formData, 
                      link_placement: newPlacement,
                      ...(selectedCalc && newPlacement === 'first_comment' && selectedCalc.target_url ? {
                        auto_responder_template: selectedCalc.target_url
                      } : {})
                    });
                  }}
                  className="w-full border rounded px-3 py-2"
                >
                  <option value="first_comment">בתגובה ראשונה (מומלץ!)</option>
                  <option value="none">ללא קישור</option>
                </select>
                <p className="text-xs text-gray-500 mt-1">💡 הקישור נשלח בתגובה נפרדת כדי לעקוף אנטי-ספאם של פייסבוק</p>
              </div>
            </div>
          </div>
          
          {/* Strategy Selection */}
          <div className="border-t pt-4">
            <h4 className="font-bold text-md mb-2">📝 אסטרטגיות כתיבה ({formData.strategy_ids.length} נבחרו)</h4>
            
            {/* Hint: Match strategies to groups */}
            {formData.target_group_ids.length > 0 && (
              <div className={`mb-3 p-2 rounded text-sm ${
                formData.strategy_ids.length === formData.target_group_ids.length 
                  ? 'bg-green-50 border border-green-200 text-green-700'
                  : formData.strategy_ids.length === 0
                    ? 'bg-yellow-50 border border-yellow-200 text-yellow-700'
                    : 'bg-blue-50 border border-blue-200 text-blue-700'
              }`}>
                💡 בחרת {formData.target_group_ids.length} קבוצות = {formData.target_group_ids.length} פוסטים. 
                {formData.strategy_ids.length === formData.target_group_ids.length 
                  ? ' מספר האסטרטגיות תואם!' 
                  : ` מומלץ לבחור ${formData.target_group_ids.length} אסטרטגיות.`}
              </div>
            )}
            
            <div className="flex flex-wrap gap-2 mb-2">
              {/* Recommend button - select random strategies matching group count */}
              {formData.target_group_ids.length > 0 && (
                <button
                  type="button"
                  onClick={() => {
                    const count = formData.target_group_ids.length;
                    const shuffled = [...strategies].sort(() => Math.random() - 0.5);
                    const selected = shuffled.slice(0, Math.min(count, strategies.length)).map(s => s.id);
                    setFormData({ ...formData, strategy_ids: selected });
                  }}
                  className="px-3 py-1 text-xs bg-green-100 text-green-700 rounded hover:bg-green-200 font-medium"
                >
                  🎲 בחר {formData.target_group_ids.length} אקראיות
                </button>
              )}
              <button
                type="button"
                onClick={() => setFormData({ ...formData, strategy_ids: strategies.map(s => s.id) })}
                className="px-2 py-1 text-xs bg-blue-100 text-blue-700 rounded hover:bg-blue-200"
              >
                בחר הכל
              </button>
              <button
                type="button"
                onClick={() => setFormData({ ...formData, strategy_ids: [] })}
                className="px-2 py-1 text-xs bg-gray-100 text-gray-700 rounded hover:bg-gray-200"
              >
                נקה הכל
              </button>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-2 max-h-48 overflow-y-auto">
              {strategies.map((strategy) => (
                <label key={strategy.id} className="flex items-center gap-2 p-2 border rounded hover:bg-gray-50 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={formData.strategy_ids.includes(strategy.id)}
                    onChange={(e) => {
                      if (e.target.checked) {
                        setFormData({ ...formData, strategy_ids: [...formData.strategy_ids, strategy.id] });
                      } else {
                        setFormData({ ...formData, strategy_ids: formData.strategy_ids.filter((id) => id !== strategy.id) });
                      }
                    }}
                  />
                  <span className="text-lg">{strategy.icon}</span>
                  <span className="text-sm">{strategy.name}</span>
                </label>
              ))}
            </div>
          </div>
          
          {/* Auto-Responder Settings */}
          <div className="border-t pt-4">
            <div className="flex items-center gap-3 mb-3">
              <h4 className="font-bold text-md">🤖 Auto-Responder</h4>
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={formData.auto_responder_enabled}
                  onChange={(e) => setFormData({ ...formData, auto_responder_enabled: e.target.checked })}
                  className="sr-only peer"
                />
                <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
              </label>
            </div>
            {formData.auto_responder_enabled && (
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-1">סוג תגובה</label>
                  <select
                    value={formData.auto_responder_type}
                    onChange={(e) => setFormData({ ...formData, auto_responder_type: e.target.value as any })}
                    className="w-full border rounded px-3 py-2"
                  >
                    <option value="comment">תגובה</option>
                    <option value="messenger">מסנג'ר</option>
                    <option value="ai_decide">AI מחליט</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">עיכוב (דקות)</label>
                  <input
                    type="number"
                    min="0"
                    max="60"
                    value={formData.auto_responder_delay_minutes}
                    onChange={(e) => setFormData({ ...formData, auto_responder_delay_minutes: parseInt(e.target.value) })}
                    className="w-full border rounded px-3 py-2"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">מגבלה יומית</label>
                  <input
                    type="number"
                    min="1"
                    max="200"
                    value={formData.auto_responder_daily_limit}
                    onChange={(e) => setFormData({ ...formData, auto_responder_daily_limit: parseInt(e.target.value) })}
                    className="w-full border rounded px-3 py-2"
                  />
                </div>
                <div className="col-span-2 md:col-span-4">
                  <label className="block text-sm font-medium mb-1">תבנית תשובה (אופציונלי)</label>
                  <textarea
                    value={formData.auto_responder_template}
                    onChange={(e) => setFormData({ ...formData, auto_responder_template: e.target.value })}
                    className="w-full border rounded px-3 py-2"
                    rows={2}
                    placeholder="היי {user_name}, תודה על ההתעניינות! 💬"
                  />
                </div>
              </div>
            )}
          </div>
          
          <div>
            <label className="block text-sm font-medium mb-1">קבוצות יעד ({formData.target_group_ids.length} נבחרו)</label>
            <input
              type="text"
              placeholder="🔍 חפש קבוצות..."
              value={groupSearch}
              onChange={(e) => setGroupSearch(e.target.value)}
              className="w-full border rounded px-3 py-2 mb-2"
            />
            <div className="flex gap-2 mb-2">
              <button
                type="button"
                onClick={() => setFormData({ ...formData, target_group_ids: filteredGroups.map(g => g.id) })}
                className="px-2 py-1 text-xs bg-blue-100 text-blue-700 rounded hover:bg-blue-200"
              >
                בחר הכל ({filteredGroups.length})
              </button>
              <button
                type="button"
                onClick={() => setFormData({ ...formData, target_group_ids: [] })}
                className="px-2 py-1 text-xs bg-gray-100 text-gray-700 rounded hover:bg-gray-200"
              >
                נקה הכל
              </button>
            </div>
            <div className="border rounded p-2 max-h-60 overflow-y-auto">
              {filteredGroups.map((group) => (
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
              {filteredGroups.length === 0 && (
                <div className="text-center text-gray-500 py-2">לא נמצאו קבוצות</div>
              )}
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

      {/* Edit Campaign Modal */}
      {editingCampaign && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white p-6 rounded-lg shadow-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
            <h3 className="font-bold text-lg mb-4">✏️ עריכת קמפיין: {editingCampaign.name}</h3>
            <form onSubmit={handleEditSubmit} className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-1">שם הקמפיין</label>
                  <input
                    type="text"
                    value={editFormData.name}
                    onChange={(e) => setEditFormData({ ...editFormData, name: e.target.value })}
                    className="w-full border rounded px-3 py-2"
                    required
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">נושא</label>
                  <input
                    type="text"
                    value={editFormData.topic}
                    onChange={(e) => setEditFormData({ ...editFormData, topic: e.target.value })}
                    className="w-full border rounded px-3 py-2"
                    required
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">קהל יעד</label>
                  <input
                    type="text"
                    value={editFormData.target_audience}
                    onChange={(e) => setEditFormData({ ...editFormData, target_audience: e.target.value })}
                    className="w-full border rounded px-3 py-2"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">אחוז תמונות</label>
                  <input
                    type="number"
                    min="0"
                    max="100"
                    value={editFormData.image_percentage}
                    onChange={(e) => setEditFormData({ ...editFormData, image_percentage: parseInt(e.target.value) })}
                    className="w-full border rounded px-3 py-2"
                  />
                </div>
              </div>
              
              {/* Groups Selection */}
              <div>
                <label className="block text-sm font-medium mb-1">
                  📁 קבוצות יעד ({editFormData.target_group_ids.length} נבחרו מתוך {groups.length})
                </label>
                <input
                  type="text"
                  placeholder="🔍 חפש קבוצות..."
                  value={editGroupSearch}
                  onChange={(e) => setEditGroupSearch(e.target.value)}
                  className="w-full border rounded px-3 py-2 mb-2"
                />
                <div className="flex gap-2 mb-2">
                  <button
                    type="button"
                    onClick={() => setEditFormData({ ...editFormData, target_group_ids: filteredEditGroups.map(g => g.id) })}
                    className="px-2 py-1 text-xs bg-blue-100 text-blue-700 rounded hover:bg-blue-200"
                  >
                    בחר הכל ({filteredEditGroups.length})
                  </button>
                  <button
                    type="button"
                    onClick={() => setEditFormData({ ...editFormData, target_group_ids: [] })}
                    className="px-2 py-1 text-xs bg-gray-100 text-gray-700 rounded hover:bg-gray-200"
                  >
                    נקה הכל
                  </button>
                </div>
                <div className="border rounded p-2 max-h-60 overflow-y-auto bg-gray-50">
                  {filteredEditGroups.map((group) => (
                    <label key={group.id} className="flex items-center gap-2 p-1 hover:bg-white rounded cursor-pointer">
                      <input
                        type="checkbox"
                        checked={editFormData.target_group_ids.includes(group.id)}
                        onChange={(e) => {
                          if (e.target.checked) {
                            setEditFormData({ ...editFormData, target_group_ids: [...editFormData.target_group_ids, group.id] });
                          } else {
                            setEditFormData({ ...editFormData, target_group_ids: editFormData.target_group_ids.filter((id) => id !== group.id) });
                          }
                        }}
                        className="rounded"
                      />
                      <span className="text-sm flex-1">{group.name}</span>
                      <span className="text-xs text-gray-400">{group.member_count.toLocaleString()} חברים</span>
                    </label>
                  ))}
                  {filteredEditGroups.length === 0 && (
                    <div className="text-center text-gray-500 py-4">לא נמצאו קבוצות</div>
                  )}
                </div>
              </div>
              
              {/* Calculator Selection - EDIT */}
              <div className="border-t pt-4">
                <h4 className="font-bold text-md mb-3">🧮 בחירת מחשבון</h4>
                <div className="grid grid-cols-3 gap-4">
                  <div>
                    <label className="block text-sm font-medium mb-1">מצב בחירה</label>
                    <select
                      value={editFormData.calculator_mode}
                      onChange={(e) => setEditFormData({ ...editFormData, calculator_mode: e.target.value as any })}
                      className="w-full border rounded px-3 py-2"
                    >
                      <option value="all">כל המחשבונים (רוטציה)</option>
                      <option value="specific">מחשבון ספציפי</option>
                      <option value="category">קטגוריה</option>
                    </select>
                  </div>
                  {editFormData.calculator_mode === 'specific' && (
                    <div>
                      <label className="block text-sm font-medium mb-1">בחר מחשבון</label>
                      <select
                        value={editFormData.calculator_id || ''}
                        onChange={(e) => {
                          const calcId = e.target.value ? parseInt(e.target.value) : null;
                          const selectedCalc = calculators.find(c => c.id === calcId);
                          setEditFormData({ 
                            ...editFormData, 
                            calculator_id: calcId,
                            ...(selectedCalc && editFormData.link_placement === 'first_comment' && selectedCalc.target_url ? {
                              auto_responder_template: selectedCalc.target_url
                            } : {})
                          });
                        }}
                        className="w-full border rounded px-3 py-2"
                      >
                        <option value="">בחר...</option>
                        {calculators.map((calc) => (
                          <option key={calc.id} value={calc.id}>{calc.name}</option>
                        ))}
                      </select>
                      {editFormData.calculator_id && editFormData.link_placement === 'first_comment' && (
                        <p className="text-xs text-green-600 mt-1">
                          🔗 קישור לתגובה: {calculators.find(c => c.id === editFormData.calculator_id)?.target_url}
                        </p>
                      )}
                    </div>
                  )}
                  {editFormData.calculator_mode === 'category' && (
                    <div>
                      <label className="block text-sm font-medium mb-1">בחר קטגוריה</label>
                      <select
                        value={editFormData.calculator_category || ''}
                        onChange={(e) => setEditFormData({ ...editFormData, calculator_category: e.target.value || null })}
                        className="w-full border rounded px-3 py-2"
                      >
                        <option value="">בחר...</option>
                        {calcCategories.map((cat) => (
                          <option key={cat} value={cat}>{cat}</option>
                        ))}
                      </select>
                    </div>
                  )}
                  <div>
                    <label className="block text-sm font-medium mb-1">מיקום הקישור</label>
                    <select
                      value={editFormData.link_placement}
                      onChange={(e) => {
                        const newPlacement = e.target.value as 'first_comment' | 'none';
                        const selectedCalc = calculators.find(c => c.id === editFormData.calculator_id);
                        setEditFormData({ 
                          ...editFormData, 
                          link_placement: newPlacement,
                          ...(selectedCalc && newPlacement === 'first_comment' && selectedCalc.target_url ? {
                            auto_responder_template: selectedCalc.target_url
                          } : {})
                        });
                      }}
                      className="w-full border rounded px-3 py-2"
                    >
                      <option value="first_comment">בתגובה ראשונה (מומלץ!)</option>
                      <option value="none">ללא קישור</option>
                    </select>
                    <p className="text-xs text-gray-500 mt-1">💡 הקישור נשלח בתגובה נפרדת כדי לעקוף אנטי-ספאם של פייסבוק</p>
                  </div>
                </div>
              </div>
              
              {/* Strategy Selection - EDIT */}
              <div className="border-t pt-4">
                <h4 className="font-bold text-md mb-2">📝 אסטרטגיות כתיבה ({editFormData.strategy_ids.length} נבחרו)</h4>
                
                {/* Hint: Match strategies to groups */}
                {editFormData.target_group_ids.length > 0 && (
                  <div className={`mb-3 p-2 rounded text-sm ${
                    editFormData.strategy_ids.length === editFormData.target_group_ids.length 
                      ? 'bg-green-50 border border-green-200 text-green-700'
                      : editFormData.strategy_ids.length === 0
                        ? 'bg-yellow-50 border border-yellow-200 text-yellow-700'
                        : 'bg-blue-50 border border-blue-200 text-blue-700'
                  }`}>
                    💡 בחרת {editFormData.target_group_ids.length} קבוצות = {editFormData.target_group_ids.length} פוסטים. 
                    {editFormData.strategy_ids.length === editFormData.target_group_ids.length 
                      ? ' מספר האסטרטגיות תואם!' 
                      : ` מומלץ לבחור ${editFormData.target_group_ids.length} אסטרטגיות.`}
                  </div>
                )}
                
                <div className="flex flex-wrap gap-2 mb-2">
                  {/* Recommend button - select random strategies matching group count */}
                  {editFormData.target_group_ids.length > 0 && (
                    <button
                      type="button"
                      onClick={() => {
                        const count = editFormData.target_group_ids.length;
                        const shuffled = [...strategies].sort(() => Math.random() - 0.5);
                        const selected = shuffled.slice(0, Math.min(count, strategies.length)).map(s => s.id);
                        setEditFormData({ ...editFormData, strategy_ids: selected });
                      }}
                      className="px-3 py-1 text-xs bg-green-100 text-green-700 rounded hover:bg-green-200 font-medium"
                    >
                      🎲 בחר {editFormData.target_group_ids.length} אקראיות
                    </button>
                  )}
                  <button
                    type="button"
                    onClick={() => setEditFormData({ ...editFormData, strategy_ids: strategies.map(s => s.id) })}
                    className="px-2 py-1 text-xs bg-blue-100 text-blue-700 rounded hover:bg-blue-200"
                  >
                    בחר הכל
                  </button>
                  <button
                    type="button"
                    onClick={() => setEditFormData({ ...editFormData, strategy_ids: [] })}
                    className="px-2 py-1 text-xs bg-gray-100 text-gray-700 rounded hover:bg-gray-200"
                  >
                    נקה הכל
                  </button>
                </div>
                <div className="grid grid-cols-2 md:grid-cols-3 gap-2 max-h-48 overflow-y-auto">
                  {strategies.map((strategy) => (
                    <label key={strategy.id} className="flex items-center gap-2 p-2 border rounded hover:bg-gray-50 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={editFormData.strategy_ids.includes(strategy.id)}
                        onChange={(e) => {
                          if (e.target.checked) {
                            setEditFormData({ ...editFormData, strategy_ids: [...editFormData.strategy_ids, strategy.id] });
                          } else {
                            setEditFormData({ ...editFormData, strategy_ids: editFormData.strategy_ids.filter((id) => id !== strategy.id) });
                          }
                        }}
                      />
                      <span className="text-lg">{strategy.icon}</span>
                      <span className="text-sm">{strategy.name}</span>
                    </label>
                  ))}
                </div>
              </div>
              
              {/* Auto-Responder Settings - EDIT */}
              <div className="border-t pt-4">
                <div className="flex items-center gap-3 mb-3">
                  <h4 className="font-bold text-md">🤖 Auto-Responder</h4>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      checked={editFormData.auto_responder_enabled}
                      onChange={(e) => setEditFormData({ ...editFormData, auto_responder_enabled: e.target.checked })}
                      className="sr-only peer"
                    />
                    <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                  </label>
                </div>
                {editFormData.auto_responder_enabled && (
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div>
                      <label className="block text-sm font-medium mb-1">סוג תגובה</label>
                      <select
                        value={editFormData.auto_responder_type}
                        onChange={(e) => setEditFormData({ ...editFormData, auto_responder_type: e.target.value as any })}
                        className="w-full border rounded px-3 py-2"
                      >
                        <option value="comment">תגובה</option>
                        <option value="messenger">מסנג'ר</option>
                        <option value="ai_decide">AI מחליט</option>
                      </select>
                    </div>
                    <div>
                      <label className="block text-sm font-medium mb-1">עיכוב (דקות)</label>
                      <input
                        type="number"
                        min="0"
                        max="60"
                        value={editFormData.auto_responder_delay_minutes}
                        onChange={(e) => setEditFormData({ ...editFormData, auto_responder_delay_minutes: parseInt(e.target.value) })}
                        className="w-full border rounded px-3 py-2"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium mb-1">מגבלה יומית</label>
                      <input
                        type="number"
                        min="1"
                        max="200"
                        value={editFormData.auto_responder_daily_limit}
                        onChange={(e) => setEditFormData({ ...editFormData, auto_responder_daily_limit: parseInt(e.target.value) })}
                        className="w-full border rounded px-3 py-2"
                      />
                    </div>
                    <div className="col-span-2 md:col-span-4">
                      <label className="block text-sm font-medium mb-1">תבנית תשובה (אופציונלי)</label>
                      <textarea
                        value={editFormData.auto_responder_template}
                        onChange={(e) => setEditFormData({ ...editFormData, auto_responder_template: e.target.value })}
                        className="w-full border rounded px-3 py-2"
                        rows={2}
                        placeholder="היי {user_name}, תודה על ההתעניינות! 💬"
                      />
                    </div>
                  </div>
                )}
              </div>
              
              <div className="flex gap-2 pt-2 border-t">
                <button type="submit" className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700">
                  💾 שמור שינויים
                </button>
                <button type="button" onClick={() => setEditingCampaign(null)} className="px-4 py-2 bg-gray-200 rounded hover:bg-gray-300">
                  ביטול
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Delete Campaign Confirmation Modal */}
      {campaignToDelete && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
            <h3 className="text-lg font-bold text-red-600 mb-4">🗑️ מחיקת קמפיין</h3>
            <p className="text-gray-700 mb-4">
              האם אתה בטוח שברצונך למחוק את הקמפיין <strong>&ldquo;{campaignToDelete.name}&rdquo;</strong>?
            </p>
            <p className="text-gray-500 text-sm mb-4">
              פעולה זו תמחק את הקמפיין וכל הפוסטים שנוצרו עבורו. לא ניתן לבטל פעולה זו.
            </p>
            <div className="flex gap-3 justify-end">
              <button
                type="button"
                onClick={() => setCampaignToDelete(null)}
                className="px-4 py-2 bg-gray-200 text-gray-700 rounded hover:bg-gray-300"
                disabled={deletingCampaignId !== null}
              >
                ביטול
              </button>
              <button
                type="button"
                onClick={handleDeleteCampaign}
                disabled={deletingCampaignId !== null}
                className={`px-4 py-2 text-white rounded ${
                  deletingCampaignId !== null 
                    ? 'bg-gray-400 cursor-wait' 
                    : 'bg-red-600 hover:bg-red-700'
                }`}
              >
                {deletingCampaignId !== null ? '⏳ מוחק...' : '🗑️ מחק קמפיין'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Campaigns List */}
      <div className="space-y-4">
        {campaigns.map((campaign) => (
          <div key={campaign.id} className="bg-white rounded-lg shadow">
            <div className="p-4">
              <div className="flex justify-between items-start">
                <div 
                  className="flex-1 cursor-pointer"
                  onClick={() => setExpandedCampaign(expandedCampaign === campaign.id ? null : campaign.id)}
                >
                  <div className="flex items-center gap-2">
                    <span className="text-gray-400">{expandedCampaign === campaign.id ? '▼' : '▶'}</span>
                    <h3 className="font-bold text-lg">{campaign.name}</h3>
                    <span className="text-xs text-gray-400">
                      📅 {new Date(campaign.created_at).toLocaleDateString('he-IL')}
                    </span>
                  </div>
                  <p className="text-gray-600 mr-6">{campaign.topic}</p>
                  <div className="flex gap-4 mt-2 text-sm text-gray-500 mr-6">
                    <span>📝 {campaign.total_posts_generated} נוצרו</span>
                    <span>✅ {campaign.total_posts_approved} אושרו</span>
                    <span>📤 {campaign.total_posts_published} פורסמו</span>
                    <span>💬 {campaign.total_replies} תגובות</span>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <StatusBadge status={campaign.status} />
                  <button
                    onClick={() => startEdit(campaign)}
                    className="px-3 py-1 bg-gray-100 text-gray-700 text-sm rounded hover:bg-gray-200"
                  >
                    ✏️ ערוך
                  </button>
                  {/* Delete button - always available */}
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      setCampaignToDelete(campaign);
                    }}
                    className="px-3 py-1 bg-red-100 text-red-700 text-sm rounded hover:bg-red-200"
                    title="מחק קמפיין"
                  >
                    🗑️
                  </button>
                  <button
                    onClick={async () => {
                      setGeneratingCampaignId(campaign.id);
                      await onGenerate(campaign.id);
                      setGeneratingCampaignId(null);
                    }}
                    disabled={generatingCampaignId === campaign.id}
                    className={`px-3 py-1 text-white text-sm rounded ${
                      generatingCampaignId === campaign.id 
                        ? 'bg-gray-400 cursor-wait' 
                        : 'bg-green-600 hover:bg-green-700'
                    }`}
                  >
                    {generatingCampaignId === campaign.id ? (
                      <>⏳ מייצר פוסטים...</>
                    ) : (
                      <>⚡ {campaign.status === 'draft' ? 'צור פוסטים' : 'צור פוסטים נוספים'}</>
                    )}
                  </button>
                </div>
              </div>
            </div>
            
            {/* Expanded Campaign Details */}
            {expandedCampaign === campaign.id && (
              <div className="border-t p-4 bg-gray-50">
                <div className="grid grid-cols-3 gap-4 mb-4 text-sm">
                  <div>
                    <span className="text-gray-500">קהל יעד:</span>
                    <span className="mr-2 font-medium">{campaign.target_audience || 'לא הוגדר'}</span>
                  </div>
                  <div>
                    <span className="text-gray-500">אחוז תמונות:</span>
                    <span className="mr-2 font-medium">{campaign.image_percentage}%</span>
                  </div>
                  <div>
                    <span className="text-gray-500">תאריך יצירה:</span>
                    <span className="mr-2 font-medium">{new Date(campaign.created_at).toLocaleDateString('he-IL')}</span>
                  </div>
                </div>
                
                {/* Campaign Groups */}
                <div className="mt-4">
                  <h4 className="text-sm font-medium text-gray-700 mb-2">
                    📁 קבוצות בקמפיין ({campaign.target_group_ids?.length || 0})
                  </h4>
                  {campaign.target_group_ids && campaign.target_group_ids.length > 0 ? (
                    <div className="flex flex-wrap gap-2">
                      {campaign.target_group_ids.slice(0, 10).map((groupId) => {
                        const group = groups.find(g => g.id === groupId);
                        return group ? (
                          <span key={groupId} className="px-2 py-1 bg-blue-100 text-blue-700 rounded text-xs">
                            {group.name}
                          </span>
                        ) : null;
                      })}
                      {campaign.target_group_ids.length > 10 && (
                        <span className="px-2 py-1 bg-gray-200 text-gray-600 rounded text-xs">
                          +{campaign.target_group_ids.length - 10} נוספות
                        </span>
                      )}
                    </div>
                  ) : (
                    <span className="text-gray-400 text-sm">לא נבחרו קבוצות</span>
                  )}
                </div>
              </div>
            )}
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
  campaigns: Campaign[];
  onApprove: (id: number) => void;
  onReject: (id: number) => Promise<{ group_id: number; campaign_id: number | null } | null>;
  onPublish: (id: number) => Promise<void>;
  onApproveAndPublish: (id: number) => Promise<void>;
  onUpdate: (id: number, content: string) => void;
  onRegenerate: (id: number, model?: string) => Promise<void>;
  onAddImage: (id: number, style: 'eyal' | 'generic', regenerate: boolean) => Promise<void>;
  onRegenerateForGroup: (campaignId: number, groupId: number) => Promise<void>;
  availableModels: { id: string; name: string }[];
}> = ({ posts, groups, campaigns, onApprove, onReject, onPublish, onApproveAndPublish, onUpdate, onRegenerate, onAddImage, onRegenerateForGroup, availableModels }) => {
  const [filter, setFilter] = useState<string>('all');
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editContent, setEditContent] = useState('');
  const [regeneratingId, setRegeneratingId] = useState<number | null>(null);
  const [selectedModel, setSelectedModel] = useState<string>('');
  const [addingImageId, setAddingImageId] = useState<number | null>(null);
  const [deletedPost, setDeletedPost] = useState<{ groupId: number; campaignId: number; groupName: string; campaignName: string } | null>(null);
  // Loading states for AI operations
  const [loadingRegenerate, setLoadingRegenerate] = useState<number | null>(null);
  const [loadingImage, setLoadingImage] = useState<number | null>(null);
  const [loadingPublish, setLoadingPublish] = useState<number | null>(null);
  const [loadingApproveAndPublish, setLoadingApproveAndPublish] = useState<number | null>(null);
  const [loadingNewPost, setLoadingNewPost] = useState(false);
  
  // Bulk selection state
  const [selectedPosts, setSelectedPosts] = useState<Set<number>>(new Set());
  const [bulkPublishing, setBulkPublishing] = useState(false);
  
  // 🐞 Debug states
  const [debugModalPostId, setDebugModalPostId] = useState<number | null>(null);
  const [debugInfo, setDebugInfo] = useState<PostDebugInfo | null>(null);
  const [loadingDebug, setLoadingDebug] = useState(false);
  
  // API base URL (same logic as top-level API_BASE)
  const _isLocalDev = typeof window !== 'undefined' && (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1');
  const API_BASE = _isLocalDev ? 'http://localhost:8000/api/facebook' : '/api/facebook';
  
  // 🐞 DEBUG: Fetch AI prompt debug info for a post
  const fetchPostDebugInfo = async (postId: number) => {
    setLoadingDebug(true);
    setDebugModalPostId(postId);
    try {
      const res = await fetch(`${API_BASE}/posts/${postId}/debug`);
      if (res.ok) {
        const data = await res.json();
        setDebugInfo(data);
      } else {
        setDebugInfo(null);
      }
    } catch (err) {
      console.error('Failed to fetch debug info:', err);
      setDebugInfo(null);
    }
    setLoadingDebug(false);
  };

  const filteredPosts = posts.filter((p) => filter === 'all' || p.status === filter);
  const groupsMap = Object.fromEntries(groups.map((g) => [g.id, g.name]));
  const campaignsMap = Object.fromEntries(campaigns.map((c) => [c.id, c.name]));
  
  // Posts that can be published (pending or approved)
  const publishablePosts = filteredPosts.filter(p => p.status === 'pending_approval' || p.status === 'approved');
  const selectedPublishable = Array.from(selectedPosts).filter(id => publishablePosts.some(p => p.id === id));
  
  const toggleSelectPost = (postId: number) => {
    const newSelected = new Set(selectedPosts);
    if (newSelected.has(postId)) {
      newSelected.delete(postId);
    } else {
      newSelected.add(postId);
    }
    setSelectedPosts(newSelected);
  };
  
  const selectAllPublishable = () => {
    setSelectedPosts(new Set(publishablePosts.map(p => p.id)));
  };
  
  const clearSelection = () => {
    setSelectedPosts(new Set());
  };
  
  const publishSelected = async () => {
    setBulkPublishing(true);
    for (const postId of selectedPublishable) {
      const post = posts.find(p => p.id === postId);
      if (post?.status === 'pending_approval') {
        await onApproveAndPublish(postId);
      } else if (post?.status === 'approved') {
        await onPublish(postId);
      }
    }
    setSelectedPosts(new Set());
    setBulkPublishing(false);
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center flex-wrap gap-2">
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
      
      {/* Bulk Actions Toolbar */}
      {publishablePosts.length > 0 && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 flex items-center gap-3 flex-wrap">
          <span className="text-sm font-medium">
            {selectedPublishable.length > 0 
              ? `נבחרו ${selectedPublishable.length} פוסטים` 
              : `${publishablePosts.length} פוסטים ממתינים`}
          </span>
          <div className="flex gap-2">
            <button
              onClick={selectAllPublishable}
              className="px-3 py-1 text-xs bg-white border rounded hover:bg-gray-50"
            >
              בחר הכל ({publishablePosts.length})
            </button>
            {selectedPublishable.length > 0 && (
              <>
                <button
                  onClick={clearSelection}
                  className="px-3 py-1 text-xs bg-white border rounded hover:bg-gray-50"
                >
                  נקה בחירה
                </button>
                <button
                  onClick={publishSelected}
                  disabled={bulkPublishing}
                  className={`px-3 py-1 text-xs text-white rounded ${
                    bulkPublishing 
                      ? 'bg-gray-400 cursor-wait' 
                      : 'bg-blue-600 hover:bg-blue-700'
                  }`}
                >
                  {bulkPublishing ? '⏳ מפרסם...' : `🚀 פרסם ${selectedPublishable.length} נבחרים`}
                </button>
              </>
            )}
          </div>
        </div>
      )}

      <div className="space-y-4">
        {filteredPosts.map((post) => (
          <div key={post.id} className={`bg-white p-4 rounded-lg shadow ${selectedPosts.has(post.id) ? 'ring-2 ring-blue-500' : ''}`}>
            <div className="flex justify-between items-start mb-2">
              <div className="flex items-center gap-2 flex-wrap">
                {/* Checkbox for selection */}
                {(post.status === 'pending_approval' || post.status === 'approved') && (
                  <input
                    type="checkbox"
                    checked={selectedPosts.has(post.id)}
                    onChange={() => toggleSelectPost(post.id)}
                    className="w-4 h-4 text-blue-600 rounded cursor-pointer"
                  />
                )}
                <StatusBadge status={post.status} />
                {post.campaign_id && (
                  <span className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded">
                    📁 {campaignsMap[post.campaign_id] || 'קמפיין'}
                  </span>
                )}
                <span className="text-sm text-gray-500">👥 {groupsMap[post.group_id] || 'קבוצה לא ידועה'}</span>
                {post.has_image && <span className="text-sm">🖼️</span>}
                {post.youtube_url && <span className="text-sm" title="כולל וידאו">🎥</span>}
                {/* New: Calculator info */}
                {post.calculator_id && (
                  <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded">
                    🧮 מחשבון
                  </span>
                )}
                {/* New: Strategy info */}
                {post.strategy_id && (
                  <span className="text-xs bg-purple-100 text-purple-700 px-2 py-0.5 rounded">
                    📝 אסטרטגיה
                  </span>
                )}
                {/* New: First comment indicator */}
                {post.first_comment_content && (
                  <span className={`text-xs px-2 py-0.5 rounded ${
                    post.first_comment_posted 
                      ? 'bg-green-100 text-green-700' 
                      : 'bg-yellow-100 text-yellow-700'
                  }`}>
                    💬 {post.first_comment_posted ? 'תגובה ראשונה נשלחה' : 'תגובה ראשונה ממתינה'}
                  </span>
                )}
                {/* New: Auto-replies count */}
                {post.auto_replies_sent > 0 && (
                  <span className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded">
                    🤖 {post.auto_replies_sent} תשובות
                  </span>
                )}
              </div>
              {/* Publish error message */}
              {post.status === 'failed' && post.publish_error && (
                <div className="text-xs text-red-600 bg-red-50 px-3 py-1 rounded border border-red-200 mt-1">
                  ❌ {post.publish_error}
                </div>
              )}
              <div className="flex gap-2 flex-wrap">
                {post.status === 'pending_approval' && (
                  <>
                    <button
                      onClick={() => onApprove(post.id)}
                      className="px-3 py-1 bg-green-600 text-white text-sm rounded hover:bg-green-700"
                    >
                      ✓ אשר
                    </button>
                    <button
                      onClick={async () => {
                        setLoadingApproveAndPublish(post.id);
                        await onApproveAndPublish(post.id);
                        setLoadingApproveAndPublish(null);
                      }}
                      disabled={loadingApproveAndPublish === post.id}
                      className={`px-3 py-1 text-white text-sm rounded ${
                        loadingApproveAndPublish === post.id 
                          ? 'bg-gray-400 cursor-wait' 
                          : 'bg-blue-600 hover:bg-blue-700'
                      }`}
                    >
                      {loadingApproveAndPublish === post.id ? '⏳ מפרסם...' : '🚀 אשר ופרסם'}
                    </button>
                    <button
                      onClick={async () => {
                        const result = await onReject(post.id);
                        if (result && result.campaign_id) {
                          setDeletedPost({
                            groupId: result.group_id,
                            campaignId: result.campaign_id,
                            groupName: groupsMap[result.group_id] || 'קבוצה',
                            campaignName: campaignsMap[result.campaign_id] || 'קמפיין'
                          });
                        }
                      }}
                      className="px-3 py-1 bg-red-600 text-white text-sm rounded hover:bg-red-700"
                    >
                      ✗ דחה ומחק
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
                    <button
                      onClick={() => setRegeneratingId(regeneratingId === post.id ? null : post.id)}
                      className="px-3 py-1 bg-purple-600 text-white text-sm rounded hover:bg-purple-700"
                    >
                      🔄 ייצר מחדש
                    </button>
                    <button
                      onClick={() => setAddingImageId(addingImageId === post.id ? null : post.id)}
                      className="px-3 py-1 bg-orange-500 text-white text-sm rounded hover:bg-orange-600"
                    >
                      🖼️ {post.has_image ? 'החלף תמונה' : 'הוסף תמונה'}
                    </button>
                  </>
                )}
                {post.status === 'approved' && (
                  <button
                    onClick={async () => {
                      setLoadingPublish(post.id);
                      await onPublish(post.id);
                      setLoadingPublish(null);
                    }}
                    disabled={loadingPublish === post.id}
                    className={`px-3 py-1 text-white text-sm rounded ${
                      loadingPublish === post.id 
                        ? 'bg-gray-400 cursor-wait' 
                        : 'bg-blue-600 hover:bg-blue-700'
                    }`}
                  >
                    {loadingPublish === post.id ? '⏳ מפרסם...' : '📤 פרסם'}
                  </button>
                )}
                {post.status === 'failed' && (
                  <button
                    onClick={async () => {
                      setLoadingPublish(post.id);
                      await onPublish(post.id);
                      setLoadingPublish(null);
                    }}
                    disabled={loadingPublish === post.id}
                    className={`px-3 py-1 text-white text-sm rounded ${
                      loadingPublish === post.id 
                        ? 'bg-gray-400 cursor-wait' 
                        : 'bg-orange-600 hover:bg-orange-700'
                    }`}
                  >
                    {loadingPublish === post.id ? '⏳ מפרסם...' : '🔄 פרסם שוב'}
                  </button>
                )}
                {(post.status === 'rejected' || post.status === 'failed') && (
                  <button
                    onClick={async () => {
                      await onReject(post.id);
                    }}
                    className="px-3 py-1 bg-red-600 text-white text-sm rounded hover:bg-red-700"
                  >
                    🗑️ מחק
                  </button>
                )}
                {/* 🐞 Debug Button - Show AI Prompt */}
                <button
                  onClick={() => fetchPostDebugInfo(post.id)}
                  className="px-3 py-1 bg-gray-500 text-white text-sm rounded hover:bg-gray-600"
                  title="הצג את הפרומפט שנשלח ל-AI"
                >
                  🐞 דיבאג
                </button>
              </div>
              
              {/* Regenerate Modal */}
              {regeneratingId === post.id && (
                <div className="mt-2 p-3 bg-purple-50 rounded border border-purple-200">
                  <div className="flex items-center gap-2 mb-2">
                    <label className="text-sm font-medium">בחר מודל:</label>
                    <select
                      value={selectedModel}
                      onChange={(e) => setSelectedModel(e.target.value)}
                      className="border rounded px-2 py-1 text-sm"
                      disabled={loadingRegenerate === post.id}
                    >
                      <option value="">ברירת מחדל</option>
                      {availableModels.map((m) => (
                        <option key={m.id} value={m.id}>{m.name}</option>
                      ))}
                    </select>
                    <button
                      onClick={async () => {
                        setLoadingRegenerate(post.id);
                        await onRegenerate(post.id, selectedModel || undefined);
                        setLoadingRegenerate(null);
                        setRegeneratingId(null);
                        setSelectedModel('');
                      }}
                      disabled={loadingRegenerate === post.id}
                      className={`px-3 py-1 text-white text-sm rounded ${
                        loadingRegenerate === post.id 
                          ? 'bg-gray-400 cursor-wait' 
                          : 'bg-purple-600 hover:bg-purple-700'
                      }`}
                    >
                      {loadingRegenerate === post.id ? '⏳ מייצר...' : '🚀 ייצר'}
                    </button>
                    <button
                      onClick={() => setRegeneratingId(null)}
                      className="px-2 py-1 text-gray-500 text-sm hover:text-gray-700"
                      disabled={loadingRegenerate === post.id}
                    >
                      ✕
                    </button>
                  </div>
                </div>
              )}
              
              {/* Image Generation Modal */}
              {addingImageId === post.id && (
                <div className="mt-2 p-3 bg-orange-50 rounded border border-orange-200">
                  <div className="flex flex-col gap-2">
                    {loadingImage === post.id ? (
                      <div className="flex items-center gap-2 text-orange-600">
                        <span className="animate-spin">⏳</span>
                        <span className="font-medium">מייצר תמונה... (זה עלול לקחת עד 30 שניות)</span>
                      </div>
                    ) : (
                      <div className="flex items-center gap-2">
                        <label className="text-sm font-medium">סוג תמונה:</label>
                        <button
                          onClick={async () => {
                            setLoadingImage(post.id);
                            await onAddImage(post.id, 'eyal', post.has_image);
                            setLoadingImage(null);
                            setAddingImageId(null);
                          }}
                          className="px-3 py-1 bg-blue-600 text-white text-sm rounded hover:bg-blue-700"
                        >
                          👤 תמונה של אייל
                        </button>
                        <button
                          onClick={async () => {
                            setLoadingImage(post.id);
                            await onAddImage(post.id, 'generic', post.has_image);
                            setLoadingImage(null);
                            setAddingImageId(null);
                          }}
                          className="px-3 py-1 bg-green-600 text-white text-sm rounded hover:bg-green-700"
                        >
                          🎨 תמונה גנרית
                        </button>
                        <button
                          onClick={() => setAddingImageId(null)}
                          className="px-2 py-1 text-gray-500 text-sm hover:text-gray-700"
                        >
                          ✕
                        </button>
                      </div>
                    )}
                    {loadingImage !== post.id && (
                      <p className="text-xs text-gray-500">
                        {post.has_image ? '⚡ יחליף את התמונה הקיימת' : '✨ ייצר תמונה חדשה וייחודית'}
                      </p>
                    )}
                  </div>
                </div>
              )}
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

            {/* YouTube Video Preview */}
            {post.youtube_url && (
              <div className="mt-3 p-3 bg-gradient-to-r from-red-50 to-orange-50 rounded-lg border border-red-200">
                <p className="text-sm font-medium mb-2 text-red-700">🎥 וידאו מצורף:</p>
                <div className="aspect-video max-w-md">
                  <iframe 
                    src={`https://www.youtube.com/embed/${post.youtube_url.split('/').pop()?.split('?')[0]}`}
                    className="w-full h-full rounded"
                    allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                    allowFullScreen
                  />
                </div>
                <a 
                  href={post.youtube_url} 
                  target="_blank" 
                  rel="noopener noreferrer"
                  className="text-xs text-blue-600 hover:underline mt-2 block"
                >
                  🔗 {post.youtube_url}
                </a>
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

      {/* Modal לייצור פוסט חדש אחרי מחיקה */}
      {deletedPost && (
        <div 
          className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
          onClick={() => { setLoadingNewPost(false); setDeletedPost(null); }}
        >
          <div className="bg-white p-6 rounded-lg shadow-xl max-w-md" onClick={(e) => e.stopPropagation()}>
            <h3 className="text-lg font-bold mb-4">🗑️ הפוסט נמחק</h3>
            <p className="text-gray-600 mb-4">
              הפוסט לקבוצה <strong>{deletedPost.groupName}</strong> בקמפיין <strong>{deletedPost.campaignName}</strong> נמחק.
            </p>
            {loadingNewPost ? (
              <div className="flex items-center gap-2 text-blue-600 mb-4">
                <span className="animate-spin">⏳</span>
                <span className="font-medium">מייצר פוסט חדש... (זה עלול לקחת מספר שניות)</span>
              </div>
            ) : (
              <p className="text-sm text-gray-500 mb-4">האם לייצר פוסט חדש לקבוצה זו?</p>
            )}
            <div className="flex gap-2 justify-end">
              <button
                type="button"
                onClick={() => {
                  setLoadingNewPost(false);
                  setDeletedPost(null);
                }}
                className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded"
              >
                לא, תודה
              </button>
              <button
                type="button"
                onClick={async () => {
                  if (!deletedPost) return;
                  setLoadingNewPost(true);
                  try {
                    await onRegenerateForGroup(deletedPost.campaignId, deletedPost.groupId);
                  } finally {
                    setLoadingNewPost(false);
                    setDeletedPost(null);
                  }
                }}
                disabled={loadingNewPost}
                className={`px-4 py-2 text-white rounded ${
                  loadingNewPost 
                    ? 'bg-gray-400 cursor-wait' 
                    : 'bg-blue-600 hover:bg-blue-700'
                }`}
              >
                {loadingNewPost ? '⏳ מייצר...' : '✨ ייצר פוסט חדש'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 🐞 Debug Modal - Show AI Prompt */}
      {debugModalPostId && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-4xl w-full mx-4 max-h-[90vh] overflow-hidden flex flex-col">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-bold text-gray-800">
                🐞 דיבאג - הפרומפט שנשלח ל-AI (פוסט #{debugModalPostId})
              </h3>
              <button
                onClick={() => {
                  setDebugModalPostId(null);
                  setDebugInfo(null);
                }}
                className="text-gray-500 hover:text-gray-700 text-2xl"
              >
                ×
              </button>
            </div>
            
            {loadingDebug ? (
              <div className="text-center py-8">
                <div className="animate-spin inline-block w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full"></div>
                <p className="mt-2 text-gray-500">טוען מידע...</p>
              </div>
            ) : debugInfo ? (
              <div className="overflow-y-auto flex-1 space-y-4">
                {/* Meta info */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-sm">
                  <div className="bg-gray-100 p-2 rounded">
                    <span className="font-bold">קבוצה:</span> {debugInfo.group_name || 'לא ידוע'}
                  </div>
                  <div className="bg-purple-100 p-2 rounded">
                    <span className="font-bold">אסטרטגיה:</span> {debugInfo.strategy_name || 'לא ידוע'}
                  </div>
                  <div className="bg-green-100 p-2 rounded">
                    <span className="font-bold">מחשבון:</span> {debugInfo.calculator_name || 'לא ידוע'}
                  </div>
                  <div className="bg-blue-100 p-2 rounded">
                    <span className="font-bold">סטטוס:</span> {debugInfo.status}
                  </div>
                </div>

                {/* Generated content */}
                <div>
                  <h4 className="font-bold text-gray-700 mb-2">📝 התוכן שנוצר:</h4>
                  <div className="bg-yellow-50 p-3 rounded border border-yellow-200 whitespace-pre-wrap text-sm">
                    {debugInfo.generated_content}
                  </div>
                </div>

                {/* AI Prompt */}
                {debugInfo.has_debug_prompt && debugInfo.debug_ai_prompt ? (
                  <div>
                    <h4 className="font-bold text-gray-700 mb-2">🤖 הפרומפט המלא שנשלח ל-AI:</h4>
                    <div className="bg-gray-900 text-green-400 p-4 rounded font-mono text-xs whitespace-pre-wrap overflow-x-auto max-h-[50vh]" dir="rtl">
                      {debugInfo.debug_ai_prompt}
                    </div>
                  </div>
                ) : (
                  <div className="bg-red-50 p-4 rounded border border-red-200 text-red-700">
                    <strong>⚠️ אין מידע דיבאג:</strong> הפוסט הזה נוצר לפני שהוספנו את שמירת הפרומפט.
                    <br />
                    פוסטים חדשים ישמרו את הפרומפט המלא.
                  </div>
                )}
              </div>
            ) : (
              <div className="text-center py-8 text-red-500">
                שגיאה בטעינת מידע הדיבאג
              </div>
            )}

            <div className="flex justify-end mt-4 pt-4 border-t">
              <button
                onClick={() => {
                  setDebugModalPostId(null);
                  setDebugInfo(null);
                }}
                className="px-4 py-2 bg-gray-200 text-gray-700 rounded hover:bg-gray-300"
              >
                סגור
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

// ========== Replies Tab ==========
const RepliesTab: React.FC<{
  replies: Reply[];
  onGenerateResponse: (id: number) => Promise<void>;
  onSendResponse: (id: number, text?: string, channel?: string) => Promise<void>;
}> = ({ replies, onGenerateResponse, onSendResponse }) => {
  const [filter, setFilter] = useState<string>('all');
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editResponse, setEditResponse] = useState('');
  const [selectedChannel, setSelectedChannel] = useState<string>('comment');
  // Loading states
  const [loadingGenerate, setLoadingGenerate] = useState<number | null>(null);
  const [loadingSend, setLoadingSend] = useState<number | null>(null);

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
                    onClick={async () => {
                      setLoadingGenerate(reply.id);
                      await onGenerateResponse(reply.id);
                      setLoadingGenerate(null);
                    }}
                    disabled={loadingGenerate === reply.id}
                    className={`px-3 py-1 text-white text-sm rounded ${
                      loadingGenerate === reply.id 
                        ? 'bg-gray-400 cursor-wait' 
                        : 'bg-purple-600 hover:bg-purple-700'
                    }`}
                  >
                    {loadingGenerate === reply.id ? '⏳ מייצר תשובה...' : '🤖 צור תשובה'}
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
                        onClick={async () => {
                          setLoadingSend(reply.id);
                          await onSendResponse(reply.id, editResponse, selectedChannel);
                          setLoadingSend(null);
                          setEditingId(null);
                        }}
                        disabled={loadingSend === reply.id}
                        className={`px-3 py-1 text-white text-sm rounded ${
                          loadingSend === reply.id 
                            ? 'bg-gray-400 cursor-wait' 
                            : 'bg-green-600 hover:bg-green-700'
                        }`}
                      >
                        {loadingSend === reply.id ? '⏳ שולח...' : '📤 שלח'}
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
                        onClick={async () => {
                          setLoadingSend(reply.id);
                          await onSendResponse(reply.id);
                          setLoadingSend(null);
                        }}
                        disabled={loadingSend === reply.id}
                        className={`px-3 py-1 text-white text-sm rounded ${
                          loadingSend === reply.id 
                            ? 'bg-gray-400 cursor-wait' 
                            : 'bg-green-600 hover:bg-green-700'
                        }`}
                      >
                        {loadingSend === reply.id ? '⏳ שולח...' : '✓ אשר ושלח'}
                      </button>
                      <button
                        onClick={() => {
                          setEditingId(reply.id);
                          setEditResponse(reply.suggested_response || '');
                          setSelectedChannel(reply.suggested_channel || 'comment');
                        }}
                        disabled={loadingSend === reply.id}
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
  const [activeTab, setActiveTab] = useState<string>('feed');
  const [stats, setStats] = useState<Stats | null>(null);
  const [groups, setGroups] = useState<Group[]>([]);
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [posts, setPosts] = useState<Post[]>([]);
  const [replies, setReplies] = useState<Reply[]>([]);
  const [calculators, setCalculators] = useState<Calculator[]>([]);
  const [strategies, setStrategies] = useState<PostStrategy[]>([]);
  const [calcCategories, setCalcCategories] = useState<string[]>([]);
  const [availableModels, setAvailableModels] = useState<{ id: string; name: string }[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // 🍪 Cookie management states
  const [cookieStatus, setCookieStatus] = useState<{
    status: string;
    hasCookie: boolean;
    hasEssentialCookies: boolean;
    cookieCount: number;
    lastUpdated: string | null;
    profiles?: { id: number; name: string; is_active: boolean; updated_at: string | null }[];
    activeProfile?: { id: number; name: string } | null;
  } | null>(null);
  const [uploadingCookie, setUploadingCookie] = useState(false);
  const [newProfileName, setNewProfileName] = useState('');
  const [settingActiveProfileId, setSettingActiveProfileId] = useState<number | null>(null);
  const [creatingProfile, setCreatingProfile] = useState(false);
  const cookieFileRef = React.useRef<HTMLInputElement>(null);
  const [cookieLoginPending, setCookieLoginPending] = useState<number | null>(null);
  const cookieLoginPollRef = React.useRef<NodeJS.Timeout | null>(null);

  // 🐞 Debug states
  const [debugModalPostId, setDebugModalPostId] = useState<number | null>(null);
  const [debugInfo, setDebugInfo] = useState<{
    post_id: number;
    group_name: string | null;
    strategy_name: string | null;
    calculator_name: string | null;
    content: string | null;
    debug_ai_prompt: string | null;
    created_at: string | null;
  } | null>(null);
  const [loadingDebug, setLoadingDebug] = useState(false);
  const [loadingSyncPostId, setLoadingSyncPostId] = useState<number | null>(null);

  // Fetch data - resilient to individual failures
  const fetchData = async () => {
    setLoading(true);
    try {
      // Helper function to safely fetch
      const safeFetch = async (url: string) => {
        try {
          const res = await fetch(url);
          return res;
        } catch (e) {
          console.warn(`Failed to fetch ${url}:`, e);
          return null;
        }
      };

      const [statsRes, groupsRes, campaignsRes, postsRes, repliesRes, modelsRes, antiSpamRes, calcsRes, strategiesRes] = await Promise.all([
        safeFetch(`${API_BASE}/stats`),
        safeFetch(`${API_BASE}/groups`),
        safeFetch(`${API_BASE}/campaigns`),
        safeFetch(`${API_BASE}/posts`),
        safeFetch(`${API_BASE}/replies`),
        safeFetch(`${API_BASE}/ai/models`),
        safeFetch(`${API_BASE}/anti-spam/stats`),
        safeFetch(`${API_MAIN}/calculators/`),
        safeFetch(`${API_MAIN}/strategies`),
      ]);

      let statsData = null;
      if (statsRes?.ok) statsData = await statsRes.json();
      if (antiSpamRes?.ok && statsData) {
        statsData.anti_spam = await antiSpamRes.json();
      }
      if (statsData) setStats(statsData);
      
      if (groupsRes?.ok) setGroups(await groupsRes.json());
      if (campaignsRes?.ok) setCampaigns(await campaignsRes.json());
      if (postsRes?.ok) setPosts(await postsRes.json());
      if (repliesRes?.ok) setReplies(await repliesRes.json());
      if (modelsRes?.ok) {
        const modelsData = await modelsRes.json();
        setAvailableModels(modelsData.models || []);
      }
      if (calcsRes?.ok) {
        const calcsData = await calcsRes.json();
        setCalculators(calcsData);
        // Extract unique categories
        const categorySet = new Set<string>();
        calcsData.forEach((c: Calculator) => { if (c.category) categorySet.add(c.category); });
        setCalcCategories(Array.from(categorySet));
      }
      if (strategiesRes?.ok) setStrategies(await strategiesRes.json());
      
      setError(null);
    } catch (err) {
      setError('שגיאה בטעינת נתונים');
      console.error(err);
    }
    setLoading(false);
  };

  // Cookie status fetching
  const fetchCookieStatus = async () => {
    try {
      const res = await fetch(`${API_BASE}/cookies/status`);
      if (res.ok) {
        setCookieStatus(await res.json());
      }
    } catch (err) {
      console.warn('Failed to fetch cookie status:', err);
    }
  };

  const setActiveProfile = async (profileId: number) => {
    setSettingActiveProfileId(profileId);
    try {
      const res = await fetch(`${API_BASE}/profiles/${profileId}/set-active`, { method: 'PUT' });
      if (res.ok) await fetchCookieStatus();
      else setError('שגיאה בהגדרת פרופיל פעיל');
    } catch (e) {
      setError('שגיאת רשת');
    } finally {
      setSettingActiveProfileId(null);
    }
  };

  const createProfile = async () => {
    const name = newProfileName.trim() || 'פרופיל חדש';
    setCreatingProfile(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/profiles`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name }),
      });
      if (res.ok) {
        setNewProfileName('');
        await fetchCookieStatus();
      } else {
        const d = await res.json().catch(() => ({}));
        const msg = d.detail || res.statusText;
        if (res.status === 404) {
          setError('השרת לא מכיר את נתיב הפרופילים (404). וודאי שהבקאנד רץ על פורט 8000 והקוד מעודכן.');
        } else {
          setError(typeof msg === 'string' ? msg : (msg.message || 'שגיאה ביצירת פרופיל'));
        }
      }
    } catch (e) {
      setError('שגיאת רשת – וודאי שהבקאנד רץ (למשל http://localhost:8000).');
    } finally {
      setCreatingProfile(false);
    }
  };

  // Cookie upload handler
  const handleCookieUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setUploadingCookie(true);
    try {
      const text = await file.text();
      const cookies = JSON.parse(text);

      if (!Array.isArray(cookies)) {
        setError('❌ קובץ Cookie לא תקין - צריך להיות JSON array');
        return;
      }

      const res = await fetch(`${API_BASE}/cookies/upload`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ cookies }),
      });

      if (res.ok) {
        const data = await res.json();
        setError(null);
        await fetchCookieStatus();
        alert(`✅ ${data.message}`);
      } else {
        const errData = await res.json().catch(() => ({ detail: 'שגיאה' }));
        setError(`❌ שגיאה בהעלאת Cookie: ${errData.detail}`);
      }
    } catch (err) {
      setError(`❌ שגיאה בקריאת קובץ Cookie: ${err instanceof Error ? err.message : 'קובץ לא תקין'}`);
    } finally {
      setUploadingCookie(false);
      // Reset file input
      if (cookieFileRef.current) cookieFileRef.current.value = '';
    }
  };

  useEffect(() => {
    fetchData();
    fetchCookieStatus();
    // Auto-refresh cookie status every 60 seconds (to detect extension sync)
    const cookieInterval = setInterval(fetchCookieStatus, 60000);
    return () => {
      clearInterval(cookieInterval);
      // Cleanup cookie login poll if active
      if (cookieLoginPollRef.current) {
        clearInterval(cookieLoginPollRef.current);
        cookieLoginPollRef.current = null;
      }
    };
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
      } else {
        const errData = await res.json().catch(() => null);
        const msg = errData?.detail || `שגיאה בהוספת קבוצה (${res.status})`;
        alert(msg);
      }
    } catch (err) {
      console.error(err);
      alert('שגיאת רשת - לא ניתן להתחבר לשרת');
    }
  };

  const updateGroup = async (groupId: number, data: Partial<Group>) => {
    try {
      const res = await fetch(`${API_BASE}/groups/${groupId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });
      if (res.ok) {
        const updated = await res.json();
        setGroups(groups.map(g => g.id === groupId ? updated : g));
      }
    } catch (err) {
      console.error(err);
    }
  };

  const removeGroup = async (groupId: number) => {
    try {
      const res = await fetch(`${API_BASE}/groups/${groupId}`, {
        method: 'DELETE',
      });
      if (res.ok) {
        setGroups(groups.filter(g => g.id !== groupId));
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
      // Debug: log data being sent
      console.log('📤 Creating campaign with data:', data);
      console.log('📤 media_preference:', data.media_preference);
      
      const res = await fetch(`${API_BASE}/campaigns`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });
      if (res.ok) {
        const newCampaign = await res.json();
        console.log('📥 Campaign created:', newCampaign);
        setCampaigns([newCampaign, ...campaigns]);
      } else {
        console.error('❌ Campaign creation failed:', await res.text());
      }
    } catch (err) {
      console.error(err);
    }
  };

  const updateCampaign = async (campaignId: number, data: any) => {
    try {
      const res = await fetch(`${API_BASE}/campaigns/${campaignId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });
      if (res.ok) {
        const updatedCampaign = await res.json();
        setCampaigns(campaigns.map((c) => (c.id === campaignId ? updatedCampaign : c)));
      }
    } catch (err) {
      console.error(err);
    }
  };

  const deleteCampaign = async (campaignId: number) => {
    try {
      const res = await fetch(`${API_BASE}/campaigns/${campaignId}`, {
        method: 'DELETE',
      });
      if (res.ok) {
        setCampaigns(campaigns.filter((c) => c.id !== campaignId));
        // Also remove posts associated with this campaign
        setPosts(posts.filter((p) => p.campaign_id !== campaignId));
      } else {
        const error = await res.json();
        alert(error.detail || 'שגיאה במחיקת הקמפיין');
      }
    } catch (err) {
      console.error(err);
      alert('שגיאה במחיקת הקמפיין');
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

  const rejectPost = async (postId: number): Promise<{ group_id: number; campaign_id: number | null } | null> => {
    try {
      const res = await fetch(`${API_BASE}/posts/${postId}/reject`, {
        method: 'POST',
      });
      if (res.ok) {
        const data = await res.json();
        // הסר את הפוסט מהרשימה (נמחק)
        setPosts(posts.filter((p) => p.id !== postId));
        return { group_id: data.group_id, campaign_id: data.campaign_id };
      }
    } catch (err) {
      console.error(err);
    }
    return null;
  };

  // 🐞 Debug post - fetch and show AI prompt
  const debugPost = async (postId: number) => {
    setLoadingDebug(true);
    setDebugModalPostId(postId);
    try {
      const res = await fetch(`${API_BASE}/posts/${postId}/debug`);
      if (res.ok) {
        const data = await res.json();
        setDebugInfo(data);
      } else {
        setDebugInfo(null);
      }
    } catch (err) {
      console.error('Debug fetch error:', err);
      setDebugInfo(null);
    }
    setLoadingDebug(false);
  };

  const regenerateForGroup = async (campaignId: number, groupId: number) => {
    try {
      const res = await fetch(`${API_BASE}/posts/regenerate-for-group?campaign_id=${campaignId}&group_id=${groupId}`, {
        method: 'POST',
      });
      if (res.ok) {
        const newPost = await res.json();
        setPosts([newPost, ...posts]);
      }
    } catch (err) {
      console.error(err);
    }
  };

  // 🍪 Sync cookies from Chrome extension via content bridge
  // Returns true if sync succeeded (cookies are now fresh in backend)
  const syncCookiesFromExtension = (): Promise<{ synced: boolean; isLoggedIn: boolean; message: string }> => {
    return new Promise((resolve) => {
      const requestId = `sync-${Date.now()}-${Math.random().toString(36).slice(2)}`;
      const TIMEOUT_MS = 8000;

      const handler = (event: MessageEvent) => {
        if (event.source !== window) return;
        if (!event.data || event.data.type !== 'partnercalc-cookie-bridge:response') return;
        if (event.data.requestId !== requestId) return;

        window.removeEventListener('message', handler);
        clearTimeout(timeout);

        if (event.data.success && event.data.data) {
          resolve(event.data.data);
        } else {
          resolve({ synced: false, isLoggedIn: false, message: event.data.error || 'Extension error' });
        }
      };

      const timeout = setTimeout(() => {
        window.removeEventListener('message', handler);
        resolve({ synced: false, isLoggedIn: false, message: 'תוסף Cookie לא מותקן או לא מגיב' });
      }, TIMEOUT_MS);

      window.addEventListener('message', handler);

      // Send sync request to content bridge
      window.postMessage({
        type: 'partnercalc-cookie-bridge:request',
        action: 'syncAndReturn',
        requestId
      }, '*');
    });
  };

  // 🍪 Pre-publish: sync fresh cookies from extension, then verify with backend
  const ensureFreshCookies = async (): Promise<boolean> => {
    // Step 1: Ask the extension to extract & push fresh cookies to backend
    const syncResult = await syncCookiesFromExtension();
    
    if (!syncResult.isLoggedIn) {
      setError('🍪 לא מחובר לפייסבוק - יש להתחבר בדפדפן ולנסות שוב');
      // Open Facebook for login
      try {
        await fetch(`${API_BASE}/cookies/open-login`);
      } catch { /* fallback: user opens manually */ }
      return false;
    }

    if (!syncResult.synced) {
      setError(`🍪 שגיאה בסנכרון cookies: ${syncResult.message}`);
      return false;
    }

    // Step 2: Verify with backend that cookies are valid
    try {
      const statusRes = await fetch(`${API_BASE}/cookies/status`);
      if (statusRes.ok) {
        const status = await statusRes.json();
        setCookieStatus(status);
        if (status.status !== 'valid') {
          setError('🍪 Cookie פייסבוק לא תקין - יש להתחבר מחדש לפייסבוק');
          return false;
        }
      }
    } catch {
      // Backend unreachable - but cookies were synced, try anyway
    }

    return true;
  };

  // 🍪 Cookie login flow - opens Facebook, polls for cookie sync, then auto-publishes
  const startCookieLoginFlow = async (postId: number, isApproveAndPublish: boolean = false) => {
    setError('🍪 Cookie פייסבוק פג תוקף - פותח פייסבוק להתחברות...');
    setCookieLoginPending(postId);

    // Open Facebook via backend
    try {
      await fetch(`${API_BASE}/cookies/open-login`);
    } catch {
      // Fallback: user can open manually
    }

    // Start polling cookie status every 3 seconds
    let attempts = 0;
    const maxAttempts = 40; // 40 * 3s = 2 minutes

    // Clear any existing poll
    if (cookieLoginPollRef.current) {
      clearInterval(cookieLoginPollRef.current);
    }

    cookieLoginPollRef.current = setInterval(async () => {
      attempts++;
      try {
        // Try to sync from extension first
        const syncResult = await syncCookiesFromExtension();
        if (syncResult.synced && syncResult.isLoggedIn) {
          // Cookies synced! Clear poll and auto-publish
          if (cookieLoginPollRef.current) {
            clearInterval(cookieLoginPollRef.current);
            cookieLoginPollRef.current = null;
          }
          setError(null);
          setCookieLoginPending(null);
          await fetchCookieStatus();
          // Retry the publish
          if (isApproveAndPublish) {
            await approveAndPublishPost(postId);
          } else {
            await publishPost(postId);
          }
          return;
        }
      } catch {
        // Extension not available - fallback to backend poll
        try {
          const res = await fetch(`${API_BASE}/cookies/status`);
          if (res.ok) {
            const status = await res.json();
            setCookieStatus(status);
            if (status.status === 'valid') {
              if (cookieLoginPollRef.current) {
                clearInterval(cookieLoginPollRef.current);
                cookieLoginPollRef.current = null;
              }
              setError(null);
              setCookieLoginPending(null);
              if (isApproveAndPublish) {
                await approveAndPublishPost(postId);
              } else {
                await publishPost(postId);
              }
              return;
            }
          }
        } catch {
          // Network error - continue polling
        }
      }

      if (attempts >= maxAttempts) {
        if (cookieLoginPollRef.current) {
          clearInterval(cookieLoginPollRef.current);
          cookieLoginPollRef.current = null;
        }
        setError('לא הצלחנו לזהות התחברות לפייסבוק. נסה להתחבר ולחץ פרסם שוב.');
        setCookieLoginPending(null);
      }
    }, 3000);
  };

  const publishPost = async (postId: number) => {
    try {
      // 🍪 Sync fresh cookies from extension BEFORE publishing
      const cookiesReady = await ensureFreshCookies();
      if (!cookiesReady) {
        // If extension not available, fall back to login flow
        const statusRes = await fetch(`${API_BASE}/cookies/status`).catch(() => null);
        if (statusRes?.ok) {
          const status = await statusRes.json();
          setCookieStatus(status);
          if (status.status !== 'valid') {
            await startCookieLoginFlow(postId, false);
            return;
          }
          // Backend says cookies are valid even though extension sync failed - proceed
        } else {
          return; // Error already set by ensureFreshCookies
        }
      }

      // Cookies fresh - proceed to publish
      const res = await fetch(`${API_BASE}/posts/${postId}/publish`, { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        if (data.status === 'failed') {
          // Check if failure is due to expired cookie (from Apify result)
          const isExpiredCookie = data.publish_error && (
            data.publish_error.includes('Cookie') || 
            data.publish_error.includes('cookie') ||
            data.publish_error.includes('פג תוקף') ||
            data.publish_error.includes('sameSite')
          );
          if (isExpiredCookie) {
            await startCookieLoginFlow(postId, false);
            return;
          }
          setError(`❌ פרסום נכשל: ${data.publish_error || 'שגיאה לא ידועה'}`);
          setPosts(posts.map((p) => (p.id === postId ? { ...p, status: 'failed', publish_error: data.publish_error } : p)));
        } else {
          setPosts(posts.map((p) => (p.id === postId ? { ...p, status: data.status || 'published' } : p)));
        }
      } else {
        const errData = await res.json().catch(() => ({ detail: 'שגיאה לא ידועה' }));
        setError(`❌ שגיאה בפרסום: ${errData.detail || res.statusText}`);
      }
    } catch (err) {
      setError(`❌ שגיאת רשת בפרסום: ${err instanceof Error ? err.message : 'שגיאה לא ידועה'}`);
    }
  };

  const approveAndPublishPost = async (postId: number) => {
    try {
      // 🍪 Sync fresh cookies from extension BEFORE publishing
      const cookiesReady = await ensureFreshCookies();
      if (!cookiesReady) {
        const statusRes = await fetch(`${API_BASE}/cookies/status`).catch(() => null);
        if (statusRes?.ok) {
          const status = await statusRes.json();
          setCookieStatus(status);
          if (status.status !== 'valid') {
            await startCookieLoginFlow(postId, true);
            return;
          }
        } else {
          return;
        }
      }

      // First approve
      const approveRes = await fetch(`${API_BASE}/posts/${postId}/approve`, { method: 'POST' });
      if (!approveRes.ok) {
        setError('❌ אישור הפוסט נכשל');
        return;
      }
      // Then publish
      const publishRes = await fetch(`${API_BASE}/posts/${postId}/publish`, { method: 'POST' });
      if (publishRes.ok) {
        const data = await publishRes.json();
        if (data.status === 'failed') {
          const isExpiredCookie = data.publish_error && (
            data.publish_error.includes('Cookie') || 
            data.publish_error.includes('cookie') ||
            data.publish_error.includes('פג תוקף') ||
            data.publish_error.includes('sameSite')
          );
          if (isExpiredCookie) {
            await startCookieLoginFlow(postId, true);
            return;
          }
          setError(`❌ פרסום נכשל: ${data.publish_error || 'שגיאה לא ידועה'}`);
          setPosts(posts.map((p) => (p.id === postId ? { ...p, status: 'failed', publish_error: data.publish_error } : p)));
        } else {
          setPosts(posts.map((p) => (p.id === postId ? { ...p, status: data.status || 'published' } : p)));
        }
      } else {
        const errData = await publishRes.json().catch(() => ({ detail: 'שגיאה לא ידועה' }));
        setError(`❌ שגיאה בפרסום: ${errData.detail || publishRes.statusText}`);
      }
    } catch (err) {
      setError(`❌ שגיאת רשת בפרסום: ${err instanceof Error ? err.message : 'שגיאה לא ידועה'}`);
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

  const regeneratePost = async (postId: number, model?: string) => {
    try {
      const res = await fetch(`${API_BASE}/posts/${postId}/regenerate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ model }),
      });
      if (res.ok) {
        const updatedPost = await res.json();
        setPosts(posts.map((p) => (p.id === postId ? updatedPost : p)));
      }
    } catch (err) {
      console.error(err);
    }
  };

  const addImageToPost = async (postId: number, style: 'eyal' | 'generic' = 'eyal', regenerate: boolean = false) => {
    try {
      const res = await fetch(`${API_BASE}/posts/${postId}/add-image`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ style, regenerate }),
      });
      if (res.ok) {
        const updatedPost = await res.json();
        setPosts(posts.map((p) => (p.id === postId ? updatedPost : p)));
      }
    } catch (err) {
      console.error(err);
    }
  };

  const generateReplyResponse = async (replyId: number) => {
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/replies/${replyId}/generate`, { method: 'POST' });
      if (res.ok) {
        const updatedReply = await res.json();
        setReplies(replies.map((r) => (r.id === replyId ? updatedReply : r)));
        if (!updatedReply.suggested_response?.trim()) {
          setError('המערכת לא החזירה טקסט תשובה. נסה שוב או בדוק את מפתח ה-AI ב-.env');
        }
      } else {
        const errData = await res.json().catch(() => ({}));
        let msg = errData.detail;
        if (Array.isArray(msg)) msg = msg[0]?.msg ?? msg[0] ?? msg;
        if (typeof msg !== 'string') msg = res.status === 503 ? 'ה-AI לא החזיר תשובה. בדוק מפתח API (OpenAI/Anthropic) ב-.env' : 'יצירת התשובה נכשלה';
        setError(`❌ ${msg}`);
      }
    } catch (err) {
      console.error(err);
      setError('❌ שגיאת רשת – לא ניתן ליצור תשובה. בדוק שהשרת רץ ומפתח ה-AI מוגדר.');
    }
  };

  const sendReplyResponse = async (replyId: number, text?: string, channel?: string) => {
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/replies/${replyId}/respond`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ response_text: text, channel }),
      });
      if (res.ok) {
        const updatedReply = await res.json();
        setReplies(replies.map((r) => (r.id === replyId ? updatedReply : r)));
        if (updatedReply.status === 'approved_not_sent') {
          const serverReason = res.headers.get('X-Send-Error');
          const msg = serverReason
            ? `⚠️ התגובה אושרה אך לא פורסמה. סיבה: ${serverReason}`
            : '⚠️ התגובה אושרה אך לא פורסמה אוטומטית. אפשר להעתיק את הטקסט ולפרסם ידנית.';
          setError(msg);
        }
      } else {
        const errData = await res.json().catch(() => ({}));
        setError(`❌ ${errData.detail || 'שליחת התגובה נכשלה'}`);
        const refreshRes = await fetch(`${API_BASE}/replies`);
        if (refreshRes.ok) setReplies(await refreshRes.json());
      }
    } catch (err) {
      console.error(err);
      setError('❌ שגיאת רשת – לא ניתן לשלוח את התגובה.');
    }
  };

  const markReplyAsResponded = async (replyId: number) => {
    try {
      const res = await fetch(`${API_BASE}/replies/${replyId}/mark-responded`, { method: 'POST' });
      if (res.ok) {
        const updatedReply = await res.json();
        setReplies(replies.map((r) => (r.id === replyId ? updatedReply : r)));
      }
    } catch (err) {
      console.error(err);
    }
  };

  const syncPostComments = async (postId: number) => {
    setLoadingSyncPostId(postId);
    try {
      const res = await fetch(`${API_BASE}/posts/${postId}/sync-comments`, { method: 'POST' });
      if (res.ok) {
        const refreshRes = await fetch(`${API_BASE}/replies`);
        if (refreshRes.ok) setReplies(await refreshRes.json());
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoadingSyncPostId(null);
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
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold">📘 Facebook Marketing</h1>
            <p className="text-blue-100">ניהול פרסום בקבוצות פייסבוק</p>
          </div>
          {/* Cookie Status Indicator */}
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2">
              <span
                className={`w-3 h-3 rounded-full ${
                  cookieLoginPending !== null ? 'bg-orange-400 animate-pulse' :
                  cookieStatus?.status === 'valid' ? 'bg-green-400' : 'bg-red-400'
                }`}
              />
              <span className="text-sm">
                {cookieLoginPending !== null ? 'ממתין להתחברות...' :
                 cookieStatus?.status === 'valid' ? 'מחובר' : 'Cookie פג תוקף'}
              </span>
              {cookieStatus?.lastUpdated && cookieStatus?.status === 'valid' && (
                <span className="text-xs text-blue-200">
                  ({new Date(cookieStatus.lastUpdated).toLocaleTimeString('he-IL', { hour: '2-digit', minute: '2-digit' })})
                </span>
              )}
            </div>
            <button
              onClick={() => cookieFileRef.current?.click()}
              disabled={uploadingCookie}
              className="bg-blue-500 hover:bg-blue-400 text-white text-sm px-3 py-1 rounded disabled:opacity-50"
            >
              {uploadingCookie ? '⏳ מעלה...' : '🍪 העלה Cookie'}
            </button>
            <input
              ref={cookieFileRef}
              type="file"
              accept=".json"
              className="hidden"
              onChange={handleCookieUpload}
            />
          </div>
        </div>
      </div>

      {/* Cookie Login Pending Banner */}
      {cookieLoginPending !== null && (
        <div className="bg-orange-100 border border-orange-400 text-orange-800 px-4 py-3 mx-4 mt-4 rounded flex items-center justify-between animate-pulse">
          <div className="flex items-center gap-2">
            <span className="text-xl">🔄</span>
            <div>
              <span className="font-bold">ממתין להתחברות לפייסבוק...</span>
              <p className="text-sm mt-1">התחבר בטאב שנפתח - נפרסם אוטומטית כשהחיבור יזוהה</p>
            </div>
          </div>
          <button
            onClick={() => {
              if (cookieLoginPollRef.current) {
                clearInterval(cookieLoginPollRef.current);
                cookieLoginPollRef.current = null;
              }
              setCookieLoginPending(null);
              setError(null);
            }}
            className="bg-orange-600 hover:bg-orange-500 text-white px-4 py-1 rounded text-sm"
          >
            ✕ ביטול
          </button>
        </div>
      )}

      {/* Cookie Expired Alert Banner */}
      {cookieStatus && cookieStatus.status !== 'valid' && cookieLoginPending === null && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 mx-4 mt-4 rounded flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-xl">⚠️</span>
            <span className="font-bold">Cookie פייסבוק פג תוקף - יש לעדכן כדי לפרסם</span>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={async () => {
                try { await fetch(`${API_BASE}/cookies/open-login`); } catch {}
                setError('פייסבוק נפתח - התחבר והתוסף יסנכרן אוטומטית');
              }}
              className="bg-blue-600 hover:bg-blue-500 text-white px-4 py-1 rounded text-sm"
            >
              🌐 פתח פייסבוק
            </button>
            <button
              onClick={() => cookieFileRef.current?.click()}
              disabled={uploadingCookie}
              className="bg-red-600 hover:bg-red-500 text-white px-4 py-1 rounded text-sm disabled:opacity-50"
            >
              {uploadingCookie ? '⏳ מעלה...' : '📤 העלה Cookie ידנית'}
            </button>
          </div>
        </div>
      )}

      {/* 🧑 פרופיל פרסום פעיל – מעבר בין יוזרים */}
      {cookieStatus && (
        <div className="mx-4 mt-4 p-4 bg-gray-50 border border-gray-200 rounded">
          <div className="text-sm font-semibold text-gray-700 mb-2">פרופיל פרסום פעיל</div>
          <p className="text-xs text-gray-500 mb-2">
            {(cookieStatus?.profiles?.length ?? 0) === 0
              ? 'הוסף פרופיל כדי להפריד בין חשבונות (למשל שלי / אייל). הפרסום והסנכרון ישתמשו בפרופיל שנבחר.'
              : 'הפרסום והסנכרון משתמשים בפרופיל שנבחר. החלף כדי לעבוד מפייסבוק אחר (למשל שלי / אייל).'}
          </p>
          <div className="flex flex-wrap items-center gap-2">
            {(cookieStatus?.profiles ?? []).map((p) => (
              <span
                key={p.id}
                className={`inline-flex items-center gap-2 px-3 py-1.5 rounded text-sm ${
                  p.is_active ? 'bg-green-100 text-green-800 border border-green-300' : 'bg-white border border-gray-300 text-gray-700'
                }`}
              >
                <span>{p.name}</span>
                {p.is_active && <span className="text-xs">(פעיל)</span>}
                {!p.is_active && (
                  <button
                    onClick={() => setActiveProfile(p.id)}
                    disabled={settingActiveProfileId !== null}
                    className="text-blue-600 hover:underline text-xs disabled:opacity-50"
                  >
                    {settingActiveProfileId === p.id ? '...' : 'הגדר כפעיל'}
                  </button>
                )}
              </span>
            ))}
            <div className="flex items-center gap-1">
              <input
                type="text"
                value={newProfileName}
                onChange={(e) => setNewProfileName(e.target.value)}
                placeholder="שם פרופיל (למשל שלי)"
                className="border border-gray-300 rounded px-2 py-1 text-sm w-36"
              />
              <button
                onClick={createProfile}
                disabled={creatingProfile || !newProfileName.trim()}
                className="bg-gray-600 hover:bg-gray-500 text-white text-sm px-2 py-1 rounded disabled:opacity-50"
              >
                {creatingProfile ? '...' : 'הוסף פרופיל'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="bg-white border-b px-4 flex gap-2 overflow-x-auto">
        <TabButton active={activeTab === 'dashboard'} onClick={() => setActiveTab('dashboard')}>
          📊 סקירה
        </TabButton>
        <TabButton active={activeTab === 'groups'} onClick={() => setActiveTab('groups')}>
          📁 קבוצות
        </TabButton>
        <TabButton active={activeTab === 'feed'} onClick={() => setActiveTab('feed')} badge={pendingPostsCount + pendingRepliesCount}>
          📢 פיד
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
        {activeTab === 'groups' && <GroupsTab groups={groups} onAdd={addGroup} onSearch={searchGroups} onRemove={removeGroup} onUpdate={updateGroup} />}
        {activeTab === 'feed' && (
          <FeedTab
            campaigns={campaigns}
            posts={posts}
            replies={replies}
            groups={groups}
            calculators={calculators}
            strategies={strategies}
            calcCategories={calcCategories}
            onCreate={createCampaign}
            onGenerate={generatePosts}
            onUpdateCampaign={updateCampaign}
            onDeleteCampaign={deleteCampaign}
            onApprovePost={approvePost}
            onRejectPost={rejectPost}
            onPublishPost={publishPost}
            onApproveAndPublishPost={approveAndPublishPost}
            onUpdatePost={updatePost}
            onRegeneratePost={regeneratePost}
            onAddImage={addImageToPost}
            onRegenerateForGroup={regenerateForGroup}
            onGenerateResponse={generateReplyResponse}
            onSendResponse={sendReplyResponse}
            onMarkResponded={markReplyAsResponded}
            onSyncComments={syncPostComments}
            loadingSyncPostId={loadingSyncPostId}
            onDebugPost={debugPost}
            availableModels={availableModels}
          />
        )}
      </div>

      {/* 🐞 Debug Modal - Show AI Prompt */}
      {debugModalPostId && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-4xl w-full mx-4 max-h-[90vh] overflow-hidden flex flex-col">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-bold text-gray-800">
                🐞 דיבאג - הפרומפט שנשלח ל-AI (פוסט #{debugModalPostId})
              </h3>
              <button
                onClick={() => {
                  setDebugModalPostId(null);
                  setDebugInfo(null);
                }}
                className="text-gray-500 hover:text-gray-700 text-2xl"
              >
                ×
              </button>
            </div>
            
            {loadingDebug ? (
              <div className="text-center py-8">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
                <p className="mt-2 text-gray-500">טוען מידע...</p>
              </div>
            ) : debugInfo ? (
              <div className="flex-1 overflow-auto space-y-4">
                {/* Metadata */}
                <div className="grid grid-cols-2 gap-4 bg-gray-50 p-4 rounded">
                  <div>
                    <span className="font-medium text-gray-600">קבוצה:</span>{' '}
                    <span className="text-gray-800">{debugInfo.group_name || 'לא ידוע'}</span>
                  </div>
                  <div>
                    <span className="font-medium text-gray-600">אסטרטגיה:</span>{' '}
                    <span className="text-gray-800">{debugInfo.strategy_name || 'לא ידוע'}</span>
                  </div>
                  <div>
                    <span className="font-medium text-gray-600">מחשבון:</span>{' '}
                    <span className="text-gray-800">{debugInfo.calculator_name || 'לא ידוע'}</span>
                  </div>
                  <div>
                    <span className="font-medium text-gray-600">נוצר:</span>{' '}
                    <span className="text-gray-800">
                      {debugInfo.created_at ? new Date(debugInfo.created_at).toLocaleString('he-IL') : 'לא ידוע'}
                    </span>
                  </div>
                </div>
                
                {/* Generated Content */}
                <div>
                  <h4 className="font-medium text-gray-700 mb-2">📝 התוכן שנוצר:</h4>
                  <div className="bg-blue-50 p-3 rounded text-sm whitespace-pre-wrap max-h-40 overflow-auto">
                    {debugInfo.content || 'אין תוכן'}
                  </div>
                </div>
                
                {/* AI Prompt */}
                <div>
                  <h4 className="font-medium text-gray-700 mb-2">🤖 הפרומפט שנשלח ל-AI:</h4>
                  {debugInfo.debug_ai_prompt ? (
                    <pre className="bg-gray-900 text-green-400 p-4 rounded text-sm overflow-auto max-h-96 whitespace-pre-wrap" dir="ltr">
                      {debugInfo.debug_ai_prompt}
                    </pre>
                  ) : (
                    <div className="bg-yellow-50 p-4 rounded text-yellow-700">
                      ⚠️ לא נשמר פרומפט לפוסט זה. הפרומפט נשמר רק לפוסטים שנוצרו אחרי הוספת תכונה זו.
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <div className="text-center py-8 text-gray-500">
                לא נמצא מידע לפוסט זה
              </div>
            )}
            
            <div className="mt-4 flex justify-end">
              <button
                onClick={() => {
                  setDebugModalPostId(null);
                  setDebugInfo(null);
                }}
                className="px-4 py-2 bg-gray-200 text-gray-700 rounded hover:bg-gray-300"
              >
                סגור
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
