import React, { useState, useEffect } from 'react'

export default function StickySectionNav({ activeSection, onSelectSection }) {
  const [scrolled, setScrolled] = useState(false)

  useEffect(() => {
    const handleScroll = () => {
      setScrolled(window.scrollY > 120)
    }
    window.addEventListener('scroll', handleScroll)
    return () => window.removeEventListener('scroll', handleScroll)
  }, [])

  const sections = [
    { id: 'executive-overview', label: 'Overview', icon: '📈' },
    { id: 'financial-storytelling', label: 'Storytelling', icon: '💡' },
    { id: 'income-expense-analysis', label: 'Cash Flow', icon: '⚖️' },
    { id: 'category-analysis', label: 'Categories', icon: '🏷️' },
    { id: 'party-analysis', label: 'Parties', icon: '👥' },
    { id: 'transaction-intelligence', label: 'Risk Intelligence', icon: '🛡️' },
    { id: 'transactions-section', label: 'Explorer', icon: '📑' },
    { id: 'reconciliation-audit', label: 'Reconciliation', icon: '🔍' },
  ]

  function scrollTo(id) {
    if (onSelectSection) onSelectSection(id)
    const el = document.getElementById(id)
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }
  }

  return (
    <div
      className={`sticky top-0 z-30 transition-all py-2.5 backdrop-blur-md border-b ${
        scrolled
          ? 'bg-white/95 dark:bg-slate-900/95 border-gray-200 dark:border-slate-800 shadow-xs'
          : 'bg-white/80 dark:bg-slate-900/80 border-transparent'
      }`}
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex items-center justify-between gap-2 overflow-x-auto no-scrollbar">
        <div className="flex items-center gap-1 sm:gap-2">
          {sections.map((s) => {
            const isActive = activeSection === s.id
            return (
              <button
                key={s.id}
                type="button"
                onClick={() => scrollTo(s.id)}
                className={`text-xs px-2.5 py-1.5 rounded-xl font-bold whitespace-nowrap transition-all flex items-center gap-1.5 ${
                  isActive
                    ? 'bg-emerald-600 text-white shadow-2xs'
                    : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-slate-800/60'
                }`}
              >
                <span className="text-sm">{s.icon}</span>
                <span>{s.label}</span>
              </button>
            )
          })}
        </div>
      </div>
    </div>
  )
}
