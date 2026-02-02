'use client'

import { useState, useEffect } from 'react'
import { MessageSquare, Mail, Phone, Send, Bot, User } from 'lucide-react'

interface Message {
  id: number
  lead_id: number
  channel: string
  direction: string
  message_body: string
  subject: string
  status: string
  is_auto_reply: boolean
  sent_at: string
}

interface Conversation {
  lead_id: number
  domain: string
  site_name: string
  messages: Message[]
  total_messages: number
}

export default function InboxPage() {
  const [conversations, setConversations] = useState<any[]>([])
  const [selectedLeadId, setSelectedLeadId] = useState<number | null>(null)
  const [conversation, setConversation] = useState<Conversation | null>(null)
  const [loading, setLoading] = useState(true)
  const [newMessage, setNewMessage] = useState('')

  useEffect(() => {
    fetchConversations()
  }, [])

  useEffect(() => {
    if (selectedLeadId) {
      fetchConversation(selectedLeadId)
    }
  }, [selectedLeadId])

  const fetchConversations = async () => {
    try {
      const response = await fetch('/api/communication/inbox')
      if (response.ok) {
        const data = await response.json()
        // קבוצות לפי lead_id
        const grouped = data.reduce((acc: any, msg: any) => {
          if (!acc[msg.lead_id]) {
            acc[msg.lead_id] = { lead_id: msg.lead_id, last_message: msg }
          }
          return acc
        }, {})
        setConversations(Object.values(grouped))
      }
    } catch (error) {
      console.error('Failed to fetch conversations:', error)
    } finally {
      setLoading(false)
    }
  }

  const fetchConversation = async (leadId: number) => {
    try {
      const response = await fetch(`/api/communication/conversation/${leadId}`)
      if (response.ok) {
        const data = await response.json()
        setConversation(data)
      }
    } catch (error) {
      console.error('Failed to fetch conversation:', error)
    }
  }

  const sendMessage = async () => {
    if (!newMessage.trim() || !selectedLeadId) return

    try {
      await fetch('/api/communication/send/whatsapp', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          lead_id: selectedLeadId,
          channel: 'whatsapp',
          message_body: newMessage
        })
      })

      setNewMessage('')
      fetchConversation(selectedLeadId)
    } catch (error) {
      console.error('Failed to send message:', error)
    }
  }

  const channelIcon = (channel: string) => {
    switch (channel) {
      case 'whatsapp': return <MessageSquare className="w-4 h-4 text-green-600" />
      case 'email': return <Mail className="w-4 h-4 text-blue-600" />
      case 'sms': return <Phone className="w-4 h-4 text-purple-600" />
      default: return null
    }
  }

  return (
    <div className="h-full flex">
      {/* רשימת שיחות */}
      <div className="w-80 border-l border-gray-200 bg-white overflow-hidden flex flex-col">
        <div className="p-4 border-b border-gray-200">
          <h2 className="font-semibold">הודעות</h2>
        </div>
        
        <div className="flex-1 overflow-auto">
          {loading ? (
            <div className="p-4 text-center text-gray-500">טוען...</div>
          ) : conversations.length === 0 ? (
            <div className="p-4 text-center text-gray-500">
              <MessageSquare className="w-12 h-12 mx-auto mb-2 opacity-50" />
              <p>אין הודעות</p>
            </div>
          ) : (
            conversations.map((conv) => (
              <button
                key={conv.lead_id}
                onClick={() => setSelectedLeadId(conv.lead_id)}
                className={`w-full p-4 text-right border-b border-gray-100 hover:bg-gray-50 ${
                  selectedLeadId === conv.lead_id ? 'bg-primary-50' : ''
                }`}
              >
                <div className="flex items-center gap-2 mb-1">
                  {channelIcon(conv.last_message.channel)}
                  <span className="font-medium text-sm">ליד #{conv.lead_id}</span>
                </div>
                <p className="text-sm text-gray-600 truncate">
                  {conv.last_message.message_body}
                </p>
                <span className="text-xs text-gray-400">
                  {new Date(conv.last_message.sent_at).toLocaleDateString('he-IL')}
                </span>
              </button>
            ))
          )}
        </div>
      </div>

      {/* חלון שיחה */}
      <div className="flex-1 flex flex-col bg-gray-50">
        {!selectedLeadId ? (
          <div className="flex-1 flex items-center justify-center text-gray-500">
            <div className="text-center">
              <MessageSquare className="w-16 h-16 mx-auto mb-4 opacity-50" />
              <p>בחר שיחה לצפייה</p>
            </div>
          </div>
        ) : !conversation ? (
          <div className="flex-1 flex items-center justify-center text-gray-500">
            טוען שיחה...
          </div>
        ) : (
          <>
            {/* כותרת */}
            <div className="bg-white border-b border-gray-200 p-4">
              <div className="font-semibold">{conversation.site_name || conversation.domain}</div>
              <div className="text-sm text-gray-500">{conversation.domain}</div>
            </div>

            {/* הודעות */}
            <div className="flex-1 overflow-auto p-4 space-y-4">
              {conversation.messages.map((msg) => (
                <div
                  key={msg.id}
                  className={`flex ${msg.direction === 'outbound' ? 'justify-start' : 'justify-end'}`}
                >
                  <div
                    className={`max-w-md p-3 rounded-lg ${
                      msg.direction === 'outbound'
                        ? 'bg-primary-600 text-white'
                        : 'bg-white border border-gray-200'
                    }`}
                  >
                    <div className="flex items-center gap-2 mb-1">
                      {msg.is_auto_reply && <Bot className="w-3 h-3" />}
                      {channelIcon(msg.channel)}
                      <span className="text-xs opacity-70">
                        {new Date(msg.sent_at).toLocaleTimeString('he-IL', { hour: '2-digit', minute: '2-digit' })}
                      </span>
                    </div>
                    <p className="text-sm whitespace-pre-wrap">{msg.message_body}</p>
                  </div>
                </div>
              ))}
            </div>

            {/* כתיבת הודעה */}
            <div className="bg-white border-t border-gray-200 p-4">
              <div className="flex gap-2">
                <input
                  type="text"
                  className="input flex-1"
                  placeholder="כתוב הודעה..."
                  value={newMessage}
                  onChange={(e) => setNewMessage(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && sendMessage()}
                />
                <button
                  onClick={sendMessage}
                  className="btn btn-primary"
                  disabled={!newMessage.trim()}
                >
                  <Send className="w-5 h-5" />
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
