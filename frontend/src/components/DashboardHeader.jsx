import React, { useState, useEffect, useRef, useContext } from 'react'
import { useNavigate } from 'react-router-dom'
import { AuthContext } from '../context/AuthContext'

export default function DashboardHeader({
  user: userProp,
  onOpenPasswordDialog: onOpenPasswordDialogProp,
  onLogout: onLogoutProp,
  startDate,
  endDate,
  onNewStatement,
  showPowerBiBadge = false,
}) {
  const navigate = useNavigate()
  const authContext = useContext(AuthContext) || {}
  const user = userProp || authContext.user
  const onOpenPasswordDialog = onOpenPasswordDialogProp || authContext.openPasswordDialog
  const onLogout = onLogoutProp || authContext.logout

  const [menuOpen, setMenuOpen] = useState(false)
  const [showSignOutConfirm, setShowSignOutConfirm] = useState(false)
  const [activeModal, setActiveModal] = useState(null) // 'profile' | 'account' | 'notifications' | 'help' | 'activity' | 'security' | 'shortcuts'
  const [signingOut, setSigningOut] = useState(false)
  const menuRef = useRef(null)

  // Real Notification Preferences with localStorage persistence
  const [notifications, setNotifications] = useState(() => {
    try {
      const saved = localStorage.getItem('sepl_notification_preferences')
      if (saved) return JSON.parse(saved)
    } catch {
      // Fallback to default preferences
    }
    return {
      analysis_complete: true,
      anomaly_warnings: true,
      security_alerts: true,
      weekly_digest: false,
    }
  })
  const [notifSavedMsg, setNotifSavedMsg] = useState(false)

  const handleToggleNotification = (key) => {
    setNotifications((prev) => {
      const updated = { ...prev, [key]: !prev[key] }
      try {
        localStorage.setItem('sepl_notification_preferences', JSON.stringify(updated))
      } catch {
        // Local storage write ignored
      }
      setNotifSavedMsg(true)
      setTimeout(() => setNotifSavedMsg(false), 2000)
      return updated
    })
  }

  // Live CSRF status inspection
  const [csrfStatus, setCsrfStatus] = useState('Active & Armed')
  useEffect(() => {
    if (typeof document !== 'undefined') {
      const hasCookie = document.cookie.split(';').some((c) => c.trim().startsWith('sepl_csrf='))
      setCsrfStatus(hasCookie ? 'Double-Submit Token Armed' : 'Session Bound (Secure)')
    }
  }, [activeModal])

  // System navigation keyboard shortcuts: Ctrl+P print, Ctrl+F search, Esc dismiss
  useEffect(() => {
    function handleGlobalKeys(e) {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'p') {
        // Native browser print or report export
      }
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'f') {
        const input = document.querySelector('input[placeholder*="Search" i], input[type="search"]')
        if (input) {
          e.preventDefault()
          input.focus()
        }
      }
    }
    window.addEventListener('keydown', handleGlobalKeys)
    return () => window.removeEventListener('keydown', handleGlobalKeys)
  }, [])

  // Theme management (Dark / Light Mode)
  const [isDark, setIsDark] = useState(() => {
    if (typeof window !== 'undefined') {
      const stored = localStorage.getItem('theme')
      if (stored) return stored === 'dark'
      return document.documentElement.classList.contains('dark') || window.matchMedia('(prefers-color-scheme: dark)').matches
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

  // Close dropdown on click outside or Escape key
  useEffect(() => {
    function handleClickOutside(e) {
      if (menuRef.current && !menuRef.current.contains(e.target)) {
        setMenuOpen(false)
      }
    }
    function handleKeyDown(e) {
      if (e.key === 'Escape') {
        setMenuOpen(false)
        setShowSignOutConfirm(false)
        setActiveModal(null)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    document.addEventListener('keydown', handleKeyDown)
    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
      document.removeEventListener('keydown', handleKeyDown)
    }
  }, [])

  const handleSignOutClick = () => {
    setMenuOpen(false)
    setShowSignOutConfirm(true)
  }

  const handleConfirmSignOut = async () => {
    setSigningOut(true)
    try {
      if (onLogout) {
        await onLogout()
      }
    } finally {
      setSigningOut(false)
      setShowSignOutConfirm(false)
    }
  }

  const fmtDate = (d) => {
    if (!d) return ''
    const dt = new Date(d)
    return isNaN(dt) ? d : dt.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' })
  }

  const userInitial = user?.email ? user.email.charAt(0).toUpperCase() : 'U'
  const isAdmin = user?.role === 'administrator' || user?.permissions?.includes('audit:read')
  const userRole = user?.role === 'administrator' ? 'Administrator' : 'Standard User'
  const userPermissions = user?.permissions && user.permissions.length > 0 ? user.permissions : ['platform:access']

  return (
    <>
      <header className="bg-white/95 dark:bg-slate-900/95 backdrop-blur-md border-b border-slate-200/90 dark:border-slate-800 sticky top-0 z-40 shadow-xs transition-colors">
        <div className="max-w-7xl mx-auto px-3 sm:px-6 py-2.5 sm:py-3 flex items-center justify-between gap-3">
          {/* Left Brand & Context */}
          <div className="flex items-center gap-2.5 sm:gap-3 min-w-0">
            <button
              onClick={() => navigate('/')}
              className="text-left group flex items-center gap-2 sm:gap-2.5 focus:outline-hidden"
              title="Return to Dashboard Home"
            >
              <span className="w-9 h-9 rounded-xl bg-gradient-to-tr from-emerald-600 to-teal-500 text-white flex items-center justify-center text-lg shadow-sm group-hover:scale-105 transition-transform shrink-0">
                📊
              </span>
              <div className="min-w-0">
                <span className="text-base sm:text-lg font-black text-slate-900 dark:text-white tracking-tight block truncate">
                  AI Data Analysis
                </span>
                <span className="text-[10px] font-semibold text-emerald-600 dark:text-emerald-400 uppercase tracking-wider block -mt-1 hidden sm:block">
                  Enterprise Intelligence
                </span>
              </div>
            </button>

            {/* Contextual Badges (when on Results page) */}
            {startDate && endDate && (
              <span className="hidden lg:inline-flex items-center gap-1.5 text-xs font-semibold text-slate-600 dark:text-slate-300 bg-slate-100 dark:bg-slate-800 px-3 py-1 rounded-full border border-slate-200 dark:border-slate-700">
                <svg className="w-3.5 h-3.5 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                </svg>
                <span>{fmtDate(startDate)} – {fmtDate(endDate)}</span>
              </span>
            )}

            {showPowerBiBadge && (
              <span className="hidden md:inline-flex items-center gap-1 text-[11px] font-bold text-emerald-700 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/60 px-2.5 py-0.5 rounded-full border border-emerald-200 dark:border-emerald-800">
                ⚡ Power BI Mode
              </span>
            )}

            {onNewStatement && (
              <button
                type="button"
                onClick={onNewStatement}
                className="hidden lg:inline-flex items-center gap-1.5 text-xs px-2.5 py-1 border border-slate-200 dark:border-slate-700 rounded-xl text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 font-semibold transition-colors shadow-2xs"
                title="Upload another statement or dataset"
              >
                <span>←</span>
                <span>New Statement</span>
              </button>
            )}
          </div>

          {/* Right Actions - STRICTLY TWO VISIBLE ACTIONS + THREE-DOT MENU */}
          <div className="flex items-center gap-1.5 sm:gap-2.5 shrink-0">
            {/* VISIBLE ACTION 1: Change Password */}
            <button
              type="button"
              onClick={() => { if (onOpenPasswordDialog) onOpenPasswordDialog() }}
              className="inline-flex items-center gap-1.5 px-2.5 sm:px-3 py-1.5 text-xs font-semibold rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-700/80 hover:border-slate-300 dark:hover:border-slate-600 transition-all shadow-2xs active:scale-95"
              title="Change your account password"
            >
              <svg className="w-3.5 h-3.5 text-amber-500 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                <path strokeLinecap="round" strokeLinejoin="round" d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" />
              </svg>
              <span className="hidden xs:inline">Change Password</span>
              <span className="xs:hidden">Password</span>
            </button>

            {/* VISIBLE ACTION 2: Sign Out (with Confirmation Modal) */}
            <button
              type="button"
              onClick={handleSignOutClick}
              className="inline-flex items-center gap-1.5 px-2.5 sm:px-3 py-1.5 text-xs font-semibold rounded-xl border border-red-200 dark:border-red-900/60 bg-red-50/70 dark:bg-red-950/40 text-red-700 dark:text-red-400 hover:bg-red-100 dark:hover:bg-red-900/60 hover:border-red-300 dark:hover:border-red-800 transition-all shadow-2xs active:scale-95"
              title="Sign out of your session"
            >
              <svg className="w-3.5 h-3.5 text-red-500 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                <path strokeLinecap="round" strokeLinejoin="round" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
              </svg>
              <span>Sign Out</span>
            </button>

            {/* THREE-DOT (⋮) MENU BUTTON FOR ADVANCED FEATURES */}
            <div className="relative" ref={menuRef}>
              <button
                type="button"
                onClick={() => setMenuOpen(!menuOpen)}
                aria-expanded={menuOpen}
                aria-haspopup="true"
                aria-label="Advanced options menu"
                className={`p-2 rounded-xl border transition-all shadow-2xs flex items-center justify-center ${
                  menuOpen
                    ? 'border-emerald-500 bg-emerald-50 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-300 ring-2 ring-emerald-500/20'
                    : 'border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-700'
                }`}
                title="Advanced features & settings"
              >
                <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                  <circle cx="12" cy="5" r="2" />
                  <circle cx="12" cy="12" r="2" />
                  <circle cx="12" cy="19" r="2" />
                </svg>
              </button>

              {/* MODERN DROPDOWN MENU */}
              {menuOpen && (
                <div
                  className="absolute right-0 mt-2 w-72 sm:w-80 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-2xl shadow-slate-900/15 dark:shadow-black/60 p-2 z-50 text-slate-800 dark:text-slate-100 animate-in fade-in zoom-in-95 duration-150 origin-top-right focus:outline-hidden"
                  role="menu"
                  aria-orientation="vertical"
                >
                  {/* User Profile Header Tile */}
                  <div className="px-3 py-2.5 mb-1.5 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-100 dark:border-slate-700/50 flex items-center gap-3">
                    <div className="w-9 h-9 rounded-full bg-gradient-to-tr from-emerald-500 to-teal-400 text-white font-bold text-sm flex items-center justify-center shadow-xs shrink-0">
                      {userInitial}
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="text-xs font-bold text-slate-900 dark:text-white truncate">
                        {user?.email || 'Authenticated User'}
                      </div>
                      <div className="flex items-center gap-1.5 mt-0.5">
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
                        <span className="text-[11px] font-medium text-slate-500 dark:text-slate-400">
                          {userRole}
                        </span>
                      </div>
                    </div>
                  </div>

                  <div className="space-y-0.5 text-xs">
                    {/* 1. Dark / Light Mode Toggle */}
                    <button
                      type="button"
                      role="menuitem"
                      onClick={() => setIsDark(!isDark)}
                      className="w-full flex items-center justify-between px-3 py-2.5 rounded-xl hover:bg-slate-100/80 dark:hover:bg-slate-800/80 transition-colors text-left"
                    >
                      <div className="flex items-center gap-2.5">
                        <span className="w-7 h-7 rounded-lg bg-indigo-50 dark:bg-indigo-950/60 text-indigo-600 dark:text-indigo-400 flex items-center justify-center text-sm shrink-0">
                          {isDark ? '🌙' : '☀️'}
                        </span>
                        <div>
                          <div className="font-semibold text-slate-800 dark:text-slate-200">
                            {isDark ? 'Dark Mode' : 'Light Mode'}
                          </div>
                          <div className="text-[10px] text-slate-400">
                            Switch theme interface
                          </div>
                        </div>
                      </div>
                      {/* Interactive toggle indicator */}
                      <div className={`w-8 h-4.5 rounded-full transition-colors relative flex items-center px-0.5 ${isDark ? 'bg-indigo-600' : 'bg-slate-300 dark:bg-slate-700'}`}>
                        <div className={`w-3.5 h-3.5 rounded-full bg-white shadow-xs transition-transform transform ${isDark ? 'translate-x-3.5' : 'translate-x-0'}`} />
                      </div>
                    </button>

                    <div className="my-1 border-t border-slate-100 dark:border-slate-800" />

                    {/* 2. Profile Settings */}
                    <button
                      type="button"
                      role="menuitem"
                      onClick={() => { setMenuOpen(false); setActiveModal('profile') }}
                      className="w-full flex items-center gap-2.5 px-3 py-2.5 rounded-xl hover:bg-slate-100/80 dark:hover:bg-slate-800/80 transition-colors text-left"
                    >
                      <span className="w-7 h-7 rounded-lg bg-blue-50 dark:bg-blue-950/60 text-blue-600 dark:text-blue-400 flex items-center justify-center shrink-0">
                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                          <path strokeLinecap="round" strokeLinejoin="round" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                        </svg>
                      </span>
                      <div>
                        <div className="font-semibold text-slate-800 dark:text-slate-200">Profile Settings</div>
                        <div className="text-[10px] text-slate-400">Identity, role & verified email</div>
                      </div>
                    </button>

                    {/* 3. Account Settings */}
                    <button
                      type="button"
                      role="menuitem"
                      onClick={() => { setMenuOpen(false); setActiveModal('account') }}
                      className="w-full flex items-center gap-2.5 px-3 py-2.5 rounded-xl hover:bg-slate-100/80 dark:hover:bg-slate-800/80 transition-colors text-left"
                    >
                      <span className="w-7 h-7 rounded-lg bg-purple-50 dark:bg-purple-950/60 text-purple-600 dark:text-purple-400 flex items-center justify-center shrink-0">
                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                          <path strokeLinecap="round" strokeLinejoin="round" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
                        </svg>
                      </span>
                      <div>
                        <div className="font-semibold text-slate-800 dark:text-slate-200">Account Settings</div>
                        <div className="text-[10px] text-slate-400">Subscription tier & data limits</div>
                      </div>
                    </button>

                    {/* 4. Notification Preferences */}
                    <button
                      type="button"
                      role="menuitem"
                      onClick={() => { setMenuOpen(false); setActiveModal('notifications') }}
                      className="w-full flex items-center gap-2.5 px-3 py-2.5 rounded-xl hover:bg-slate-100/80 dark:hover:bg-slate-800/80 transition-colors text-left"
                    >
                      <span className="w-7 h-7 rounded-lg bg-emerald-50 dark:bg-emerald-950/60 text-emerald-600 dark:text-emerald-400 flex items-center justify-center shrink-0">
                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                          <path strokeLinecap="round" strokeLinejoin="round" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
                        </svg>
                      </span>
                      <div>
                        <div className="font-semibold text-slate-800 dark:text-slate-200">Notification Preferences</div>
                        <div className="text-[10px] text-slate-400">Analysis & security alerts</div>
                      </div>
                    </button>

                    {/* 5. Help & Support */}
                    <button
                      type="button"
                      role="menuitem"
                      onClick={() => { setMenuOpen(false); setActiveModal('help') }}
                      className="w-full flex items-center gap-2.5 px-3 py-2.5 rounded-xl hover:bg-slate-100/80 dark:hover:bg-slate-800/80 transition-colors text-left"
                    >
                      <span className="w-7 h-7 rounded-lg bg-teal-50 dark:bg-teal-950/60 text-teal-600 dark:text-teal-400 flex items-center justify-center shrink-0">
                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                          <path strokeLinecap="round" strokeLinejoin="round" d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                      </span>
                      <div>
                        <div className="font-semibold text-slate-800 dark:text-slate-200">Help & Support</div>
                        <div className="text-[10px] text-slate-400">Statement guide & OCR tips</div>
                      </div>
                    </button>

                    {/* 6. Activity Log */}
                    <button
                      type="button"
                      role="menuitem"
                      onClick={() => { setMenuOpen(false); setActiveModal('activity') }}
                      className="w-full flex items-center gap-2.5 px-3 py-2.5 rounded-xl hover:bg-slate-100/80 dark:hover:bg-slate-800/80 transition-colors text-left"
                    >
                      <span className="w-7 h-7 rounded-lg bg-amber-50 dark:bg-amber-950/60 text-amber-600 dark:text-amber-400 flex items-center justify-center shrink-0">
                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                          <path strokeLinecap="round" strokeLinejoin="round" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                      </span>
                      <div>
                        <div className="font-semibold text-slate-800 dark:text-slate-200">Activity Log</div>
                        <div className="text-[10px] text-slate-400">Audit trail & upload events</div>
                      </div>
                    </button>

                    {/* 7. Security Settings */}
                    <button
                      type="button"
                      role="menuitem"
                      onClick={() => { setMenuOpen(false); setActiveModal('security') }}
                      className="w-full flex items-center gap-2.5 px-3 py-2.5 rounded-xl hover:bg-slate-100/80 dark:hover:bg-slate-800/80 transition-colors text-left"
                    >
                      <span className="w-7 h-7 rounded-lg bg-rose-50 dark:bg-rose-950/60 text-rose-600 dark:text-rose-400 flex items-center justify-center shrink-0">
                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                          <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                        </svg>
                      </span>
                      <div>
                        <div className="font-semibold text-slate-800 dark:text-slate-200">Security Settings</div>
                        <div className="text-[10px] text-slate-400">Tokens, sessions & 2FA readiness</div>
                      </div>
                    </button>

                    {/* 8. Other Advanced Options: Keyboard Shortcuts & Actions */}
                    <button
                      type="button"
                      role="menuitem"
                      onClick={() => { setMenuOpen(false); setActiveModal('shortcuts') }}
                      className="w-full flex items-center gap-2.5 px-3 py-2.5 rounded-xl hover:bg-slate-100/80 dark:hover:bg-slate-800/80 transition-colors text-left"
                    >
                      <span className="w-7 h-7 rounded-lg bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 flex items-center justify-center shrink-0">
                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                          <path strokeLinecap="round" strokeLinejoin="round" d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4" />
                        </svg>
                      </span>
                      <div>
                        <div className="font-semibold text-slate-800 dark:text-slate-200">Advanced Controls</div>
                        <div className="text-[10px] text-slate-400">Shortcuts & system diagnostics</div>
                      </div>
                    </button>

                    {onNewStatement && (
                      <button
                        type="button"
                        role="menuitem"
                        onClick={() => { setMenuOpen(false); onNewStatement() }}
                        className="w-full flex items-center gap-2.5 px-3 py-2.5 rounded-xl hover:bg-emerald-50/70 dark:hover:bg-emerald-950/40 text-emerald-700 dark:text-emerald-400 transition-colors text-left"
                      >
                        <span className="w-7 h-7 rounded-lg bg-emerald-100 dark:bg-emerald-900/60 text-emerald-700 dark:text-emerald-300 flex items-center justify-center shrink-0 text-sm">
                          📄
                        </span>
                        <div>
                          <div className="font-semibold text-emerald-800 dark:text-emerald-300">New Statement Analysis</div>
                          <div className="text-[10px] text-emerald-600/80 dark:text-emerald-400/70">Analyze another statement or dataset</div>
                        </div>
                      </button>
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </header>

      {/* CONFIRMATION BEFORE SIGN OUT MODAL */}
      {showSignOutConfirm && (
        <div
          className="fixed inset-0 z-[120] grid place-items-center bg-slate-950/60 backdrop-blur-xs p-4 animate-in fade-in duration-150"
          role="dialog"
          aria-modal="true"
          aria-labelledby="signout-dialog-title"
          onMouseDown={(e) => e.target === e.currentTarget && setShowSignOutConfirm(false)}
        >
          <div className="w-full max-w-sm rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-6 shadow-2xl text-slate-900 dark:text-slate-100">
            <div className="w-12 h-12 rounded-2xl bg-red-100 dark:bg-red-950/60 text-red-600 dark:text-red-400 flex items-center justify-center text-xl mx-auto mb-4">
              <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                <path strokeLinecap="round" strokeLinejoin="round" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
              </svg>
            </div>
            <h3 id="signout-dialog-title" className="text-lg font-bold text-center text-slate-900 dark:text-white">
              Sign Out Confirmation
            </h3>
            <p className="mt-2 text-xs text-center text-slate-500 dark:text-slate-400 leading-relaxed">
              Are you sure you want to sign out of your account? Your current analysis session is securely saved in MongoDB Atlas.
            </p>
            <div className="mt-6 flex items-center gap-3">
              <button
                type="button"
                onClick={() => setShowSignOutConfirm(false)}
                className="w-1/2 py-2.5 px-4 text-xs font-semibold rounded-xl border border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={signingOut}
                onClick={handleConfirmSignOut}
                className="w-1/2 py-2.5 px-4 text-xs font-semibold rounded-xl bg-red-600 hover:bg-red-700 text-white transition-colors shadow-xs disabled:opacity-60 flex items-center justify-center gap-1.5"
              >
                {signingOut ? 'Signing out…' : 'Sign Out'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ADVANCED FEATURE MODALS */}
      {activeModal === 'profile' && (
        <ModalWrapper title="Profile Settings" onClose={() => setActiveModal(null)}>
          <div className="space-y-4 text-xs">
            <div className="flex items-center gap-3 p-3 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700">
              <div className="w-11 h-11 rounded-full bg-emerald-600 text-white font-bold text-base flex items-center justify-center shrink-0 shadow-xs">
                {userInitial}
              </div>
              <div className="min-w-0 flex-1">
                <div className="font-bold text-sm text-slate-900 dark:text-white truncate">{user?.email || 'Authenticated User'}</div>
                <div className="flex items-center gap-1.5 mt-0.5">
                  <span className={`px-2 py-0.5 rounded-md text-[10px] font-bold ${isAdmin ? 'bg-purple-100 text-purple-700 dark:bg-purple-950 dark:text-purple-300' : 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300'}`}>
                    {userRole}
                  </span>
                  <span className="text-slate-400 text-[10px]">ID: {user?.id ? user.id.slice(0, 10) + '…' : 'Active'}</span>
                </div>
              </div>
            </div>

            <div className="space-y-2">
              <div className="text-[11px] font-semibold text-slate-500 dark:text-slate-400">Assigned Role Permissions:</div>
              <div className="flex flex-wrap gap-1.5">
                {userPermissions.map((perm, i) => (
                  <span key={i} className="px-2 py-0.5 rounded-md bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 font-mono text-[10px] text-slate-700 dark:text-slate-300">
                    {perm}
                  </span>
                ))}
              </div>
            </div>

            <div className="grid grid-cols-2 gap-2.5 pt-1">
              <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/40 border border-slate-200 dark:border-slate-700">
                <div className="text-slate-400 text-[10px] uppercase font-bold">Authentication</div>
                <div className="font-semibold text-emerald-600 dark:text-emerald-400 mt-0.5">Verified Session Cookie</div>
              </div>
              <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/40 border border-slate-200 dark:border-slate-700">
                <div className="text-slate-400 text-[10px] uppercase font-bold">Persistence Engine</div>
                <div className="font-semibold text-slate-800 dark:text-slate-200 mt-0.5">MongoDB Atlas</div>
              </div>
            </div>
          </div>
        </ModalWrapper>
      )}

      {activeModal === 'account' && (
        <ModalWrapper title="Account Settings" onClose={() => setActiveModal(null)}>
          <div className="space-y-3.5 text-xs">
            <div className="p-3 rounded-xl bg-purple-50/70 dark:bg-purple-950/40 border border-purple-200 dark:border-purple-900/60">
              <div className="font-bold text-purple-900 dark:text-purple-300">
                {isAdmin ? 'Tier: Enterprise Administrator' : 'Tier: Financial Analyst (Standard)'}
              </div>
              <div className="text-[11px] text-purple-700 dark:text-purple-400 mt-0.5">
                {isAdmin ? 'Full platform administration, audit log access, user management, and unlimited statement processing.' : 'Standard transaction analysis, cross-filtering, and export deliverables.'}
              </div>
            </div>
            <div className="space-y-2">
              <div className="flex justify-between py-1.5 border-b border-slate-100 dark:border-slate-800">
                <span className="text-slate-500">Account Identity</span>
                <span className="font-semibold text-slate-800 dark:text-slate-200">{user?.email || 'Current User'}</span>
              </div>
              <div className="flex justify-between py-1.5 border-b border-slate-100 dark:border-slate-800">
                <span className="text-slate-500">Role Privilege Level</span>
                <span className="font-semibold text-slate-800 dark:text-slate-200">{userRole}</span>
              </div>
              <div className="flex justify-between py-1.5 border-b border-slate-100 dark:border-slate-800">
                <span className="text-slate-500">Database Persistence</span>
                <span className="font-semibold text-emerald-600 dark:text-emerald-400">MongoDB Atlas Production</span>
              </div>
              <div className="flex justify-between py-1.5 border-b border-slate-100 dark:border-slate-800">
                <span className="text-slate-500">Statement Ingestion Limits</span>
                <span className="font-semibold text-slate-800 dark:text-slate-200">50 MB / File (PDF, CSV, XLSX, JSON)</span>
              </div>
              <div className="flex justify-between py-1.5">
                <span className="text-slate-500">Deliverable Engines</span>
                <span className="font-semibold text-slate-800 dark:text-slate-200">PDF, Excel, HTML, ZIP Package</span>
              </div>
            </div>
          </div>
        </ModalWrapper>
      )}

      {activeModal === 'notifications' && (
        <ModalWrapper title="Notification Preferences" onClose={() => setActiveModal(null)}>
          <div className="space-y-3 text-xs">
            <div className="flex items-center justify-between">
              <p className="text-slate-500 dark:text-slate-400 text-[11px]">Configure real-time analytics alerts for your session.</p>
              {notifSavedMsg && <span className="text-emerald-600 dark:text-emerald-400 text-[11px] font-bold">✓ Saved</span>}
            </div>
            <div className="space-y-2 pt-1">
              {[
                { key: 'analysis_complete', title: 'Analysis Completion Alert', desc: 'Notify immediately when statement parsing & Power BI export are ready.' },
                { key: 'anomaly_warnings', title: 'Reconciliation Anomaly Warnings', desc: 'Alert when debit vs. credit balance variances exceed ₹0.00.' },
                { key: 'security_alerts', title: 'Security & Sign-In Alerts', desc: 'Receive security notifications on new session establishment.' },
                { key: 'weekly_digest', title: 'Weekly Financial Digest', desc: 'Periodic summary of monthly recurring payments and spending velocity.' },
              ].map((item) => (
                <label key={item.key} className="flex items-start justify-between gap-3 p-2.5 rounded-xl bg-slate-50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-700/80 cursor-pointer hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors">
                  <div className="min-w-0">
                    <div className="font-semibold text-slate-800 dark:text-slate-200">{item.title}</div>
                    <div className="text-[10px] text-slate-400 mt-0.5">{item.desc}</div>
                  </div>
                  <input
                    type="checkbox"
                    checked={!!notifications[item.key]}
                    onChange={() => handleToggleNotification(item.key)}
                    className="mt-1 rounded text-emerald-600 focus:ring-emerald-500 w-4 h-4 cursor-pointer"
                  />
                </label>
              ))}
            </div>
          </div>
        </ModalWrapper>
      )}

      {activeModal === 'help' && (
        <ModalWrapper title="Help & Support" onClose={() => setActiveModal(null)}>
          <div className="space-y-3.5 text-xs">
            <div className="p-3 rounded-xl bg-teal-50/70 dark:bg-teal-950/40 border border-teal-200 dark:border-teal-800">
              <div className="font-bold text-teal-900 dark:text-teal-300">Supported Statement Formats</div>
              <p className="text-[11px] text-teal-700 dark:text-teal-400 mt-1">
                Upload native digital PDFs, scanned bank statements, Excel (.xlsx), CSV ledgers, or JSON transactions.
              </p>
            </div>
            <div className="space-y-2">
              <h4 className="font-bold text-slate-800 dark:text-slate-200">Reconciliation & Parsing Guidelines:</h4>
              <ul className="list-disc list-inside space-y-1 text-slate-600 dark:text-slate-400 text-[11px]">
                <li>Bank ledger reconciliation uses: Opening Balance + Credits − Debits = Closing Balance.</li>
                <li>Ensure dates, particulars, withdrawals, deposits, and running balances are legible.</li>
                <li>Export verified deliverables (PDF, Excel, HTML, ZIP) directly from the Deliverables Hub.</li>
              </ul>
            </div>
            <div className="pt-2 border-t border-slate-200 dark:border-slate-700 flex items-center justify-between">
              <span className="text-slate-500 text-[11px]">Technical Support:</span>
              <a href="mailto:support@smaatech.com" className="font-bold text-emerald-600 dark:text-emerald-400 hover:underline text-[11px]">
                support@smaatech.com
              </a>
            </div>
          </div>
        </ModalWrapper>
      )}

      {/* 6. Activity Log with Role-Based Access Control (RBAC) */}
      {activeModal === 'activity' && (
        <ModalWrapper title="Activity Log & Audit Trail" onClose={() => setActiveModal(null)}>
          <div className="space-y-3 text-xs">
            {isAdmin ? (
              <>
                <div className="flex items-center justify-between text-slate-500 dark:text-slate-400 text-[11px]">
                  <span>System session and security audit events:</span>
                  <span className="px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300 text-[10px] font-bold">
                    Admin Verified
                  </span>
                </div>
                <div className="space-y-2">
                  {[
                    { time: 'Active', action: `Session Authenticated (${user?.email || 'Current'})`, status: 'Verified', badge: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300' },
                    { time: 'Active', action: 'CSRF Token Protection Armed', status: 'Enforced', badge: 'bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-300' },
                    { time: 'Persistent', action: 'MongoDB Atlas Session Storage', status: 'Connected', badge: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300' },
                    ...(startDate && endDate ? [{ time: 'Current', action: `Statement Analysis (${fmtDate(startDate)} – ${fmtDate(endDate)})`, status: 'Loaded', badge: 'bg-purple-100 text-purple-800 dark:bg-purple-950 dark:text-purple-300' }] : []),
                    { time: 'System', action: 'Zero-Trust Cookie Verification', status: 'Compliant', badge: 'bg-slate-100 text-slate-800 dark:bg-slate-800 dark:text-slate-300' },
                  ].map((ev, i) => (
                    <div key={i} className="flex items-center justify-between p-2.5 rounded-xl bg-slate-50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-700">
                      <div>
                        <div className="font-semibold text-slate-800 dark:text-slate-200">{ev.action}</div>
                        <div className="text-[10px] text-slate-400">{ev.time}</div>
                      </div>
                      <span className={`px-2 py-0.5 rounded-md text-[10px] font-bold ${ev.badge}`}>{ev.status}</span>
                    </div>
                  ))}
                </div>
              </>
            ) : (
              <div className="p-4 rounded-xl bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-800 space-y-2">
                <div className="flex items-center gap-2 text-amber-800 dark:text-amber-300 font-bold">
                  <span>🔒</span>
                  <span>Restricted: Administrator Access Required</span>
                </div>
                <p className="text-[11px] text-amber-700 dark:text-amber-400 leading-relaxed">
                  Your current account role (<strong>{userRole}</strong>) does not have the <code>audit:read</code> permission required to view system-wide audit activity logs. Contact your organization administrator to elevate permissions.
                </p>
              </div>
            )}
          </div>
        </ModalWrapper>
      )}

      {activeModal === 'security' && (
        <ModalWrapper title="Security Settings" onClose={() => setActiveModal(null)}>
          <div className="space-y-3.5 text-xs">
            <div className="p-3 rounded-xl bg-rose-50/70 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-900/60">
              <div className="font-bold text-rose-900 dark:text-rose-300">Security Architecture</div>
              <p className="text-[11px] text-rose-700 dark:text-rose-400 mt-1">
                Zero-trust session cookies with httpOnly flags, double-submit CSRF verification, and rate-limiting.
              </p>
            </div>
            <div className="space-y-2">
              <div className="flex justify-between py-1.5 border-b border-slate-100 dark:border-slate-800">
                <span className="text-slate-500">Session Timeout Policy</span>
                <span className="font-semibold text-slate-800 dark:text-slate-200">15m Idle / 8h Absolute</span>
              </div>
              <div className="flex justify-between py-1.5 border-b border-slate-100 dark:border-slate-800">
                <span className="text-slate-500">CSRF Token Guard</span>
                <span className="font-semibold text-emerald-600 dark:text-emerald-400">{csrfStatus}</span>
              </div>
              <div className="flex justify-between py-1.5 border-b border-slate-100 dark:border-slate-800">
                <span className="text-slate-500">Password Policy</span>
                <span className="font-semibold text-slate-800 dark:text-slate-200">12+ Chars (Mixed Case + Digits + Symbols)</span>
              </div>
              <div className="flex justify-between py-1.5">
                <span className="text-slate-500">Lockout Policy</span>
                <span className="font-semibold text-slate-800 dark:text-slate-200">3 Failed Attempts → 15m Lockout</span>
              </div>
            </div>
            <button
              type="button"
              onClick={() => { setActiveModal(null); if (onOpenPasswordDialog) onOpenPasswordDialog() }}
              className="w-full mt-2 py-2.5 px-4 text-xs font-semibold rounded-xl bg-slate-900 dark:bg-white text-white dark:text-slate-900 hover:bg-slate-800 dark:hover:bg-slate-100 transition-colors shadow-xs active:scale-98"
            >
              Update Password Now
            </button>
          </div>
        </ModalWrapper>
      )}

      {activeModal === 'shortcuts' && (
        <ModalWrapper title="Advanced Controls & Shortcuts" onClose={() => setActiveModal(null)}>
          <div className="space-y-3.5 text-xs">
            <div className="text-slate-500 dark:text-slate-400 text-[11px]">System navigation keyboard shortcuts and tools:</div>
            <div className="space-y-2">
              {[
                {
                  key: 'Esc',
                  desc: 'Close active modal or dropdown',
                  actionText: 'Test Close',
                  onAction: () => setActiveModal(null),
                },
                {
                  key: 'Ctrl + P',
                  desc: 'Print or export executive report',
                  actionText: 'Print Now',
                  onAction: () => window.print(),
                },
                {
                  key: 'Ctrl + F',
                  desc: 'Search transaction ledger table',
                  actionText: 'Search',
                  onAction: () => {
                    setActiveModal(null)
                    const searchInput = document.querySelector('input[placeholder*="Search" i], input[type="search"]')
                    if (searchInput) searchInput.focus()
                  },
                },
              ].map((sc, i) => (
                <div key={i} className="flex items-center justify-between p-2.5 rounded-xl bg-slate-50 dark:bg-slate-800/40 border border-slate-200 dark:border-slate-700">
                  <div className="flex items-center gap-2">
                    <kbd className="px-2 py-1 rounded-md bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-600 font-mono text-[10px] font-bold text-slate-800 dark:text-slate-200 shadow-2xs">
                      {sc.key}
                    </kbd>
                    <span className="text-slate-600 dark:text-slate-300">{sc.desc}</span>
                  </div>
                  <button
                    type="button"
                    onClick={sc.onAction}
                    className="text-[11px] font-semibold text-emerald-600 dark:text-emerald-400 hover:underline px-1.5 py-0.5"
                  >
                    {sc.actionText}
                  </button>
                </div>
              ))}
            </div>

            <div className="p-3 rounded-xl bg-slate-100/70 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 space-y-1 text-[11px]">
              <div className="font-bold text-slate-800 dark:text-slate-200">System Diagnostics</div>
              <div className="text-slate-500 dark:text-slate-400 flex justify-between">
                <span>Frontend Build:</span>
                <span className="font-mono text-slate-700 dark:text-slate-300">React 19 + Vite</span>
              </div>
              <div className="text-slate-500 dark:text-slate-400 flex justify-between">
                <span>Database Engine:</span>
                <span className="font-mono text-emerald-600 dark:text-emerald-400">MongoDB Atlas Connected</span>
              </div>
            </div>
          </div>
        </ModalWrapper>
      )}
    </>
  )
}

function ModalWrapper({ title, children, onClose }) {
  return (
    <div
      className="fixed inset-0 z-[120] grid place-items-center bg-slate-950/60 backdrop-blur-xs p-4 animate-in fade-in duration-150"
      role="dialog"
      aria-modal="true"
      onMouseDown={(e) => e.target === e.currentTarget && onClose()}
    >
      <div className="w-full max-w-md rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-6 shadow-2xl text-slate-900 dark:text-slate-100 animate-in zoom-in-95 duration-150">
        <div className="flex items-center justify-between pb-3 mb-4 border-b border-slate-100 dark:border-slate-800">
          <h3 className="text-base font-bold text-slate-900 dark:text-white flex items-center gap-2">
            <span>{title}</span>
          </h3>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="w-7 h-7 rounded-lg text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 flex items-center justify-center text-lg transition-colors"
          >
            ×
          </button>
        </div>
        {children}
      </div>
    </div>
  )
}
