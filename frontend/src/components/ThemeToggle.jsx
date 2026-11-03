import React, { useEffect, useState } from 'react'

export default function ThemeToggle() {
  const [isDark, setIsDark] = useState(() => {
    if (typeof window !== 'undefined') {
      const stored = localStorage.getItem('theme')
      if (stored) return stored === 'dark'
      return window.matchMedia('(prefers-color-scheme: dark)').matches
    }
    return false
  })

  useEffect(() => {
    const root = document.documentElement
    if (isDark) {
      root.classList.add('dark')
      localStorage.setItem('theme', 'dark')
    } else {
      root.classList.remove('dark')
      localStorage.setItem('theme', 'light')
    }
  }, [isDark])

  return (
    <button
      type="button"
      onClick={() => setIsDark(!isDark)}
      title={isDark ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
      className="p-2 rounded-xl border border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-slate-700 transition-colors text-sm shadow-2xs flex items-center gap-1.5"
    >
      <span>{isDark ? '☀️' : '🌙'}</span>
      <span className="text-xs font-semibold hidden md:inline">{isDark ? 'Light' : 'Dark'}</span>
    </button>
  )
}
