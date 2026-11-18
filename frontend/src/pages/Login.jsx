import { useEffect, useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import api, { getErrorMessage } from '../api/client'
import './Login.css'

function Icon({ name, size = 18, className = '' }) {
  const paths = {
    user: (
      <>
        <path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2" />
        <circle cx="12" cy="7" r="4" />
      </>
    ),
    lock: (
      <>
        <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
        <path d="M7 11V7a5 5 0 0 1 10 0v4" />
      </>
    ),
    mail: (
      <>
        <rect width="20" height="16" x="2" y="4" rx="2" />
        <path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7" />
      </>
    ),
    eye: (
      <>
        <path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12Z" />
        <circle cx="12" cy="12" r="3" />
      </>
    ),
    eyeOff: (
      <>
        <path d="m3 3 18 18M10.6 10.6a2 2 0 0 0 2.8 2.8" />
        <path d="M9.9 5.2A10 10 0 0 1 12 5c6.5 0 10 7 10 7a14 14 0 0 1-3.1 3.8M6.2 6.2C3.5 8 2 12 2 12s3.5 7 10 7a9.8 9.8 0 0 0 3-.5" />
      </>
    ),
    shield: (
      <>
        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
        <path d="m9 12 2 2 4-4" />
      </>
    ),
    alertCircle: (
      <>
        <circle cx="12" cy="12" r="10" />
        <line x1="12" y1="8" x2="12" y2="12" />
        <line x1="12" y1="16" x2="12.01" y2="16" />
      </>
    ),
    checkCircle: (
      <>
        <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
        <polyline points="22 4 12 14.01 9 11.01" />
      </>
    ),
    arrowLeft: (
      <>
        <line x1="19" y1="12" x2="5" y2="12" />
        <polyline points="12 19 5 12 12 5" />
      </>
    ),
  }

  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden="true"
    >
      {paths[name] || null}
    </svg>
  )
}

export default function Login() {
  const [identity, setIdentity] = useState('')
  const [password, setPassword] = useState('')
  const [remember, setRemember] = useState(true)
  const [showPassword, setShowPassword] = useState(false)
  const [recoveryStep, setRecoveryStep] = useState(0) // 0: login, 1: req email, 2: verify otp, 3: reset pass
  const [recoveryEmail, setRecoveryEmail] = useState('')
  const [otp, setOtp] = useState('')
  const [resetToken, setResetToken] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [countdown, setCountdown] = useState(0)
  const [lockSeconds, setLockSeconds] = useState(0)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [activeModal, setActiveModal] = useState(null) // 'privacy' | 'support' | null
  const navigate = useNavigate()
  const location = useLocation()

  const hasActiveTimer = countdown > 0 || lockSeconds > 0
  useEffect(() => {
    if (!hasActiveTimer) return undefined
    const timer = window.setInterval(() => {
      setCountdown((v) => Math.max(0, v - 1))
      setLockSeconds((v) => Math.max(0, v - 1))
    }, 1000)
    return () => window.clearInterval(timer)
  }, [hasActiveTimer])

  useEffect(() => {
    setError('')
    setBusy(false)
  }, [location.key])

  // ESC to close modals
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape' && activeModal) {
        setActiveModal(null)
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [activeModal])

  async function submit(event) {
    event.preventDefault()
    setError('')
    const cleanIdentity = identity.trim()
    const cleanPassword = password.trim()
    if (!cleanIdentity || !cleanPassword) {
      setError('Enter your email and password to continue.')
      return
    }
    setBusy(true)
    try {
      await api.get('/auth/csrf')
      await api.post('/auth/login', { identity: cleanIdentity, password: cleanPassword, remember })
      window.dispatchEvent(new Event('sepl-auth-change'))
      navigate(location.state?.from?.pathname || '/dashboard', { replace: true })
    } catch (err) {
      const message =
        err?.response?.status === 404
          ? 'The login endpoint returned HTTP 404. Check that the backend is running the authentication routes.'
          : getErrorMessage(err)
      const seconds = Number(message.match(/(?:in|for)\s+(\d+)\s+seconds?/i)?.[1] || 0)
      if (seconds) setLockSeconds(seconds)
      setError(message)
    } finally {
      setBusy(false)
    }
  }

  async function requestRecovery(event) {
    event.preventDefault()
    setError('')
    const cleanEmail = recoveryEmail.trim()
    if (!cleanEmail) {
      setError('Enter your registered email address.')
      return
    }
    setBusy(true)
    try {
      const { data } = await api.post('/auth/recovery/request', { email: cleanEmail })
      setRecoveryStep(2)
      setCountdown(60)
      setError(data.message)
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  async function verifyOTP(event) {
    event.preventDefault()
    setError('')
    const cleanOtp = otp.trim()
    if (!cleanOtp || cleanOtp.length !== 6) {
      setError('Enter the 6-digit code received.')
      return
    }
    setBusy(true)
    try {
      const { data } = await api.post('/auth/recovery/verify', { email: recoveryEmail.trim(), otp: cleanOtp })
      setResetToken(data.reset_token)
      setRecoveryStep(3)
      setError('')
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  async function performReset(event) {
    event.preventDefault()
    setError('')
    if (newPassword.length < 8) {
      setError('New password must be at least 8 characters long.')
      return
    }
    setBusy(true)
    try {
      await api.post('/auth/recovery/reset', {
        email: recoveryEmail.trim(),
        reset_token: resetToken,
        new_password: newPassword,
      })
      setRecoveryStep(0)
      setError('Password successfully reset. You can now sign in with your new password.')
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="login-page-root min-h-screen bg-slate-50 flex flex-col justify-between selection:bg-blue-600 selection:text-white">
      {/* Top Bar with Return to Main Website Link */}
      <header className="w-full max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-5 flex items-center justify-between">
        <Link
          to="/"
          className="flex items-center gap-2 text-sm font-semibold text-slate-600 hover:text-blue-600 transition-colors group"
          title="Return to Main Website"
        >
          <Icon name="arrowLeft" size={16} className="group-hover:-translate-x-1 transition-transform" />
          <span>Back to Main Website</span>
        </Link>

        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
          <span className="text-xs font-semibold text-slate-500">Secure 256-Bit TLS</span>
        </div>
      </header>

      {/* Main Authentication Card Container */}
      <main className="flex-1 flex items-center justify-center p-4 sm:p-6 my-auto">
        <div className="w-full max-w-[440px] bg-white rounded-2xl shadow-xl shadow-slate-200/80 border border-slate-200/90 p-8 sm:p-10 transition-all">
          {/* SEPL Logo (Clickable, returns to main website) */}
          <div className="flex flex-col items-center text-center mb-7">
            <Link
              to="/"
              className="inline-block mb-3.5 group focus:outline-hidden"
              title="SEPL - Return to Main Website"
            >
              <div className="w-14 h-14 rounded-2xl bg-gradient-to-tr from-blue-700 via-blue-600 to-cyan-500 p-0.5 shadow-md shadow-blue-500/20 group-hover:scale-105 transition-transform flex items-center justify-center">
                <div className="w-full h-full rounded-[14px] bg-white flex items-center justify-center p-1.5 overflow-hidden">
                  <img
                    src="/sepl_logo.png"
                    alt="SEPL Logo"
                    className="w-full h-full object-contain"
                    onError={(e) => {
                      e.currentTarget.style.display = 'none'
                      e.currentTarget.parentElement.innerHTML = '<span class="text-blue-600 font-black text-2xl">S</span>'
                    }}
                  />
                </div>
              </div>
            </Link>

            <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
              {recoveryStep === 0 && 'Welcome Back'}
              {recoveryStep === 1 && 'Recover Password'}
              {recoveryStep === 2 && 'Enter Security Code'}
              {recoveryStep === 3 && 'Create New Password'}
            </h1>
            <p className="text-sm text-slate-500 mt-1">
              {recoveryStep === 0 && 'Sign in to your SEPL workspace.'}
              {recoveryStep === 1 && 'Enter your registered email to receive a recovery code.'}
              {recoveryStep === 2 && `Enter the 6-digit code sent to ${recoveryEmail}.`}
              {recoveryStep === 3 && 'Choose a strong new password for your account.'}
            </p>
          </div>

          {/* Inline Alert / Error Notice */}
          {error && (
            <div
              role="alert"
              className={`p-3.5 mb-5 rounded-xl text-xs font-medium flex items-start gap-2.5 ${
                error.toLowerCase().includes('success')
                  ? 'bg-emerald-50 text-emerald-800 border border-emerald-200'
                  : 'bg-rose-50 text-rose-800 border border-rose-200'
              }`}
            >
              <Icon
                name={error.toLowerCase().includes('success') ? 'checkCircle' : 'alertCircle'}
                size={16}
                className="shrink-0 mt-0.5 text-current"
              />
              <span className="leading-snug">{error}</span>
            </div>
          )}

          {/* Form Step 0: Standard Sign In */}
          {recoveryStep === 0 && (
            <form onSubmit={submit} className="space-y-4" noValidate>
              <div>
                <label htmlFor="login-identity" className="block text-xs font-semibold text-slate-700 mb-1.5">
                  Email Address or Username
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                    <Icon name="mail" size={17} />
                  </div>
                  <input
                    id="login-identity"
                    type="text"
                    required
                    autoFocus
                    autoComplete="username"
                    value={identity}
                    onChange={(e) => setIdentity(e.target.value)}
                    placeholder="name@company.com"
                    disabled={busy || lockSeconds > 0}
                    className="w-full pl-10 pr-3.5 py-2.5 rounded-xl border border-slate-300 focus:border-blue-600 focus:ring-2 focus:ring-blue-600/20 text-slate-900 text-sm outline-hidden transition-all bg-white disabled:bg-slate-50 disabled:text-slate-400"
                  />
                </div>
              </div>

              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <label htmlFor="login-password" className="block text-xs font-semibold text-slate-700">
                    Password
                  </label>
                  <button
                    type="button"
                    onClick={() => {
                      setError('')
                      setRecoveryStep(1)
                    }}
                    className="text-xs font-semibold text-blue-600 hover:text-blue-700 hover:underline transition-colors"
                  >
                    Forgot Password?
                  </button>
                </div>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                    <Icon name="lock" size={17} />
                  </div>
                  <input
                    id="login-password"
                    type={showPassword ? 'text' : 'password'}
                    required
                    autoComplete="current-password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••"
                    disabled={busy || lockSeconds > 0}
                    className="w-full pl-10 pr-11 py-2.5 rounded-xl border border-slate-300 focus:border-blue-600 focus:ring-2 focus:ring-blue-600/20 text-slate-900 text-sm outline-hidden transition-all bg-white disabled:bg-slate-50 disabled:text-slate-400"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute inset-y-0 right-0 pr-3.5 flex items-center text-slate-400 hover:text-slate-600 focus:outline-hidden"
                    title={showPassword ? 'Hide password' : 'Show password'}
                    aria-label={showPassword ? 'Hide password' : 'Show password'}
                  >
                    <Icon name={showPassword ? 'eyeOff' : 'eye'} size={17} />
                  </button>
                </div>
              </div>

              <div className="flex items-center pt-1 pb-1">
                <label className="flex items-center gap-2 cursor-pointer select-none">
                  <input
                    type="checkbox"
                    checked={remember}
                    onChange={(e) => setRemember(e.target.checked)}
                    className="w-4 h-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500 transition-colors"
                  />
                  <span className="text-xs font-medium text-slate-600">Remember this device for 30 days</span>
                </label>
              </div>

              <button
                type="submit"
                disabled={busy || lockSeconds > 0}
                className="w-full py-3 px-4 rounded-xl bg-blue-600 hover:bg-blue-700 active:bg-blue-800 text-white font-bold text-sm shadow-md shadow-blue-600/25 hover:shadow-blue-600/35 transition-all disabled:opacity-60 disabled:cursor-not-allowed flex items-center justify-center gap-2 cursor-pointer mt-2"
              >
                {busy ? (
                  <>
                    <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    <span>Signing In…</span>
                  </>
                ) : lockSeconds > 0 ? (
                  <span>Locked ({lockSeconds}s)</span>
                ) : (
                  <span>Sign In</span>
                )}
              </button>
            </form>
          )}

          {/* Form Step 1: Request Password Recovery */}
          {recoveryStep === 1 && (
            <form onSubmit={requestRecovery} className="space-y-4">
              <div>
                <label htmlFor="recovery-email" className="block text-xs font-semibold text-slate-700 mb-1.5">
                  Registered Email Address
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                    <Icon name="mail" size={17} />
                  </div>
                  <input
                    id="recovery-email"
                    type="email"
                    required
                    autoFocus
                    value={recoveryEmail}
                    onChange={(e) => setRecoveryEmail(e.target.value)}
                    placeholder="name@company.com"
                    disabled={busy}
                    className="w-full pl-10 pr-3.5 py-2.5 rounded-xl border border-slate-300 focus:border-blue-600 focus:ring-2 focus:ring-blue-600/20 text-slate-900 text-sm outline-hidden transition-all bg-white"
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={busy}
                className="w-full py-3 px-4 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-bold text-sm shadow-md transition-all disabled:opacity-60"
              >
                {busy ? 'Sending Code…' : 'Send Verification Code'}
              </button>

              <button
                type="button"
                onClick={() => {
                  setError('')
                  setRecoveryStep(0)
                }}
                className="w-full py-2 text-xs font-semibold text-slate-500 hover:text-slate-800 transition-colors"
              >
                ← Back to Sign In
              </button>
            </form>
          )}

          {/* Form Step 2: Verify Recovery OTP */}
          {recoveryStep === 2 && (
            <form onSubmit={verifyOTP} className="space-y-4">
              <div>
                <label htmlFor="recovery-otp" className="block text-xs font-semibold text-slate-700 mb-1.5">
                  6-Digit Verification Code
                </label>
                <input
                  id="recovery-otp"
                  type="text"
                  required
                  autoFocus
                  maxLength={6}
                  value={otp}
                  onChange={(e) => setOtp(e.target.value)}
                  placeholder="123456"
                  disabled={busy}
                  className="w-full px-3.5 py-2.5 rounded-xl border border-slate-300 focus:border-blue-600 focus:ring-2 focus:ring-blue-600/20 text-slate-900 text-center font-mono tracking-widest text-lg outline-hidden bg-white"
                />
              </div>

              <button
                type="submit"
                disabled={busy}
                className="w-full py-3 px-4 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-bold text-sm shadow-md transition-all disabled:opacity-60"
              >
                {busy ? 'Verifying…' : 'Verify Code'}
              </button>

              <div className="flex items-center justify-between text-xs text-slate-500 pt-1">
                <button
                  type="button"
                  onClick={() => {
                    setError('')
                    setRecoveryStep(0)
                  }}
                  className="hover:text-slate-800"
                >
                  ← Back to Sign In
                </button>
                {countdown > 0 ? (
                  <span>Resend in {countdown}s</span>
                ) : (
                  <button type="button" onClick={requestRecovery} className="text-blue-600 font-semibold hover:underline">
                    Resend Code
                  </button>
                )}
              </div>
            </form>
          )}

          {/* Form Step 3: Set New Password */}
          {recoveryStep === 3 && (
            <form onSubmit={performReset} className="space-y-4">
              <div>
                <label htmlFor="recovery-new-password" className="block text-xs font-semibold text-slate-700 mb-1.5">
                  New Strong Password
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                    <Icon name="lock" size={17} />
                  </div>
                  <input
                    id="recovery-new-password"
                    type="password"
                    required
                    autoFocus
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    placeholder="At least 8 characters"
                    disabled={busy}
                    className="w-full pl-10 pr-3.5 py-2.5 rounded-xl border border-slate-300 focus:border-blue-600 focus:ring-2 focus:ring-blue-600/20 text-slate-900 text-sm outline-hidden bg-white"
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={busy}
                className="w-full py-3 px-4 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-bold text-sm shadow-md transition-all disabled:opacity-60"
              >
                {busy ? 'Resetting…' : 'Update Password & Sign In'}
              </button>

              <button
                type="button"
                onClick={() => {
                  setError('')
                  setRecoveryStep(0)
                }}
                className="w-full py-2 text-xs font-semibold text-slate-500 hover:text-slate-800 transition-colors"
              >
                ← Back to Sign In
              </button>
            </form>
          )}

          {/* Card Footer Links */}
          <div className="mt-8 pt-6 border-t border-slate-100 flex items-center justify-center gap-4 text-xs text-slate-500">
            <button
              type="button"
              onClick={() => setActiveModal('privacy')}
              className="hover:text-blue-600 transition-colors cursor-pointer"
            >
              Privacy Policy
            </button>
            <span>•</span>
            <button
              type="button"
              onClick={() => setActiveModal('support')}
              className="hover:text-blue-600 transition-colors cursor-pointer"
            >
              Enterprise Support
            </button>
          </div>
        </div>
      </main>

      {/* Page Footer */}
      <footer className="w-full max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-5 text-center text-xs text-slate-400">
        Powered by SEPL • Smart Solutions. Better Tomorrow.
      </footer>

      {/* Interactive Compliance Modals */}
      {activeModal && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-xs p-4"
          role="dialog"
          aria-modal="true"
          onClick={() => setActiveModal(null)}
        >
          <div
            className="w-full max-w-md bg-white rounded-2xl border border-slate-200 p-6 shadow-2xl relative text-left"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between pb-3.5 border-b border-slate-100 mb-3.5">
              <h3 className="text-base font-bold text-slate-900">
                {activeModal === 'privacy' && 'Enterprise Data Privacy & Security'}
                {activeModal === 'support' && 'Enterprise Technical Support'}
              </h3>
              <button
                type="button"
                onClick={() => setActiveModal(null)}
                className="p-1 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100"
                aria-label="Close dialog"
              >
                ✕
              </button>
            </div>

            <div className="text-xs text-slate-600 space-y-2.5 leading-relaxed">
              {activeModal === 'privacy' && (
                <>
                  <p>
                    SEPL complies with institutional data security standards. Bank statement data is processed in volatile memory with zero retention upon session termination.
                  </p>
                  <p>
                    All passwords use high-cost Scrypt key derivation, and web sessions use cryptographically signed HttpOnly cookies with CSRF validation.
                  </p>
                </>
              )}

              {activeModal === 'support' && (
                <>
                  <p>
                    For institutional assistance or account activation issues:
                  </p>
                  <div className="p-3 rounded-lg bg-slate-50 border border-slate-200 space-y-1 text-xs">
                    <div><strong>Email:</strong> support@sepl.local</div>
                    <div><strong>Security Lead:</strong> security@sepl.local</div>
                    <div><strong>Response Time:</strong> Institutional SLA (&lt;15 mins)</div>
                  </div>
                </>
              )}
            </div>

            <div className="mt-5 pt-3.5 border-t border-slate-100 flex justify-end">
              <button
                type="button"
                onClick={() => setActiveModal(null)}
                className="px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-semibold text-xs"
              >
                Close Dialog
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
