'use client'

import { Bell, User, Search } from 'lucide-react'

export default function Header() {
  return (
    <header className="h-16 bg-white border-b border-gray-200 flex items-center justify-between px-6">
      {/* חיפוש */}
      <div className="flex-1 max-w-md">
        <div className="relative">
          <Search className="absolute right-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
          <input
            type="text"
            placeholder="חיפוש..."
            className="w-full pr-10 pl-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none"
          />
        </div>
      </div>

      {/* פעולות */}
      <div className="flex items-center gap-4">
        {/* התראות */}
        <button className="relative p-2 text-gray-600 hover:bg-gray-100 rounded-lg">
          <Bell className="w-5 h-5" />
          <span className="absolute top-1 left-1 w-2 h-2 bg-danger-500 rounded-full"></span>
        </button>

        {/* משתמש */}
        <button className="flex items-center gap-2 p-2 text-gray-600 hover:bg-gray-100 rounded-lg">
          <User className="w-5 h-5" />
          <span className="text-sm font-medium">Admin</span>
        </button>
      </div>
    </header>
  )
}
