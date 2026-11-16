import { useEffect, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import api, { getErrorMessage } from '../api/client'
import './Login.css'

function Icon({ name, size = 20, className = '' }) {
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
    chart: (
      <>
        <path d="M3 3v18h18" />
        <path d="m19 9-5 5-4-4-3 3" />
      </>
    ),
    chip: (
      <>
        <rect width="18" height="18" x="3" y="3" rx="2" />
        <path d="M9 9h6v6H9zM9 1v2m6-2v2M9 21v2m6-2v2M1 9h2m-2 6h2m18-6h2m-2 6h2" />
      </>
    ),
    shield: (
      <>
        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
        <path d="m9 12 2 2 4-4" />
      </>
    ),
    bolt: (
      <path d="M13 2 3 14h9l-1 8 10-12h-9l1-8z" />
    ),
    login: (
      <>
        <path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4" />
        <polyline points="10 17 15 12 10 7" />
        <line x1="15" y1="12" x2="3" y2="12" />
      </>
    ),
    alertCircle: (
      <>
        <circle cx="12" cy="12" r="10" />
        <line x1="12" y1="8" x2="12" y2="12" />
        <line x1="12" y1="16" x2="12.01" y2="16" />
      </>
    ),
    key: (
      <>
        <path d="m21 2-2 2m-1.5 1.5L14 9l-1.5-1.5-2 2L12 11l-2 2-1.5-1.5-2 2L8 15l-4 4a2.83 2.83 0 0 1-4-4l4-4 1.5 1.5 2-2L6 9l2-2 1.5 1.5 2-2L10 5l1.5-1.5z" />
        <circle cx="15.5" cy="8.5" r=".5" fill="currentColor" />
      </>
    ),
    checkCircle: (
      <>
        <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
        <polyline points="22 4 12 14.01 9 11.01" />
      </>
    ),
    trendingUp: (
      <>
        <polyline points="23 6 13.5 15.5 8.5 10.5 1 18" />
        <polyline points="17 6 23 6 23 12" />
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
  const [visible, setVisible] = useState(false)
  const [remember, setRemember] = useState(false)
  const [recoveryStep, setRecoveryStep] = useState(0)
  const [recoveryEmail, setRecoveryEmail] = useState('')
  const [otp, setOtp] = useState('')
  const [resetToken, setResetToken] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [countdown, setCountdown] = useState(0)
  const [lockSeconds, setLockSeconds] = useState(0)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const navigate = useNavigate()
  const location = useLocation()

  const hasActiveTimer = countdown > 0 || lockSeconds > 0
  useEffect(() => {
    if (!hasActiveTimer) return undefined
    const timer = window.setInterval(() => {
      setCountdown(v => Math.max(0, v - 1))
      setLockSeconds(v => Math.max(0, v - 1))
    }, 1000)
    return () => window.clearInterval(timer)
  }, [hasActiveTimer])

  useEffect(() => {
    setError('')
    setBusy(false)
  }, [location.key])

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
      navigate(location.state?.from?.pathname || '/', { replace: true })
    } catch (err) {
      const message = err?.response?.status === 404
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
    setBusy(true)
    try {
      const { data } = await api.post('/auth/recovery/request', { email: recoveryEmail })
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
    setBusy(true)
    try {
      const { data } = await api.post('/auth/recovery/verify', { email: recoveryEmail, otp })
      setResetToken(data.reset_token)
      setRecoveryStep(3)
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  async function resetPassword(event) {
    event.preventDefault()
    setError('')
    const confirm = event.currentTarget.elements.confirmPassword.value
    if (newPassword !== confirm) {
      setError('The passwords do not match.')
      return
    }
    setBusy(true)
    try {
      await api.post('/auth/recovery/reset', { reset_token: resetToken, new_password: newPassword })
      setRecoveryStep(0)
      setPassword('')
      setError('Password reset. Sign in with your new password.')
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <main className="login-page">
      {/* Left Brand Showcase Section */}
      <section className="login-showcase" aria-label="SEPL platform introduction">
        <div className="showcase-inner">
          <header className="login-brand">
            <div className="brand-logo-frame">
              <img src="/sepl_logo.webp" alt="SEPL logo" />
            </div>
            <div className="brand-divider" aria-hidden="true" />
            <div className="brand-meta">
              <strong className="brand-name">SEPL</strong>
              <small className="brand-tagline">Smart Solutions. Better Tomorrow.</small>
            </div>
          </header>

          <div className="showcase-content">
            <div className="showcase-badge">
              <span className="badge-pulse" />
              <span>Enterprise Financial Intelligence</span>
            </div>
            <h1 className="showcase-title">
              Financial Audit &
              <span className="title-accent">Intelligence Platform</span>
            </h1>
            <p className="showcase-desc">
              Transform complex bank statements into verified audit deliverables with automated zero-delta reconciliation and intelligent classification.
            </p>

            <div className="feature-grid">
              <div className="feature-pill">
                <div className="feature-icon"><Icon name="chart" size={18} /></div>
                <div className="feature-meta">
                  <strong>Zero-Delta Audit</strong>
                  <small>Automated mathematical proof</small>
                </div>
              </div>
              <div className="feature-pill">
                <div className="feature-icon"><Icon name="chip" size={18} /></div>
                <div className="feature-meta">
                  <strong>Smart Classification</strong>
                  <small>Rule-based & AI classification</small>
                </div>
              </div>
              <div className="feature-pill">
                <div className="feature-icon"><Icon name="shield" size={18} /></div>
                <div className="feature-meta">
                  <strong>Enterprise Security</strong>
                  <small>Signed sessions & CSRF tokens</small>
                </div>
              </div>
              <div className="feature-pill">
                <div className="feature-icon"><Icon name="bolt" size={18} /></div>
                <div className="feature-meta">
                  <strong>Instant Deliverables</strong>
                  <small>Excel, PDF, CSV, HTML & ZIP</small>
                </div>
              </div>
            </div>
          </div>

          {/* Integrated Financial Analytics Visual — Vector & Benchmark Dashboard */}
          <div className="financial-visual-board" aria-label="Financial analytics benchmark preview">
            <div className="visual-board-glass">
              <div className="board-top-row">
                <div className="board-status-badge">
                  <span className="board-live-dot" />
                  <span>Verified Audit Benchmark</span>
                </div>
                <span className="board-period-tag">Axis Bank • June 2023</span>
              </div>

              <div className="board-metrics-row">
                <div className="board-metric-card">
                  <span className="metric-label">Total Inflow</span>
                  <div className="metric-value-wrap">
                    <strong className="metric-val inflow">₹45,48,780</strong>
                    <span className="trend-badge inflow"><Icon name="trendingUp" size={11} /> 9 Credits</span>
                  </div>
                </div>
                <div className="board-metric-card">
                  <span className="metric-label">Total Outflow</span>
                  <div className="metric-value-wrap">
                    <strong className="metric-val outflow">₹46,26,410</strong>
                    <span className="trend-badge outflow">153 Debits</span>
                  </div>
                </div>
                <div className="board-metric-card highlight">
                  <span className="metric-label">Reconciliation Delta</span>
                  <div className="metric-value-wrap">
                    <strong className="metric-val reconciled">Δ = ₹0.00</strong>
                    <span className="reconciled-badge">BALANCED</span>
                  </div>
                </div>
              </div>

              <div className="board-chart-container" aria-hidden="true">
                <svg className="board-chart-svg" viewBox="0 0 420 85" preserveAspectRatio="none">
                  <defs>
                    <linearGradient id="chartGradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#2563eb" stopOpacity="0.22" />
                      <stop offset="100%" stopColor="#2563eb" stopOpacity="0.0" />
                    </linearGradient>
                    <linearGradient id="lineGradient" x1="0" y1="0" x2="1" y2="0">
                      <stop offset="0%" stopColor="#3b82f6" />
                      <stop offset="55%" stopColor="#2563eb" />
                      <stop offset="100%" stopColor="#0284c7" />
                    </linearGradient>
                  </defs>
                  {/* Subtle Grid Guidelines */}
                  <line x1="0" y1="18" x2="420" y2="18" stroke="rgba(203, 213, 225, 0.45)" strokeDasharray="3 3" />
                  <line x1="0" y1="46" x2="420" y2="46" stroke="rgba(203, 213, 225, 0.45)" strokeDasharray="3 3" />
                  <line x1="0" y1="74" x2="420" y2="74" stroke="rgba(203, 213, 225, 0.45)" strokeDasharray="3 3" />

                  {/* Shaded Area Fill */}
                  <path
                    d="M 0 68 Q 65 52, 115 58 T 215 32 T 315 42 T 420 18 L 420 85 L 0 85 Z"
                    fill="url(#chartGradient)"
                  />
                  {/* Smooth Trend Curve */}
                  <path
                    d="M 0 68 Q 65 52, 115 58 T 215 32 T 315 42 T 420 18"
                    fill="none"
                    stroke="url(#lineGradient)"
                    strokeWidth="2.5"
                    strokeLinecap="round"
                  />
                  {/* Visual Data Points */}
                  <circle cx="115" cy="58" r="3.5" fill="#ffffff" stroke="#2563eb" strokeWidth="2" />
                  <circle cx="215" cy="32" r="3.5" fill="#ffffff" stroke="#2563eb" strokeWidth="2" />
                  <circle cx="315" cy="42" r="3.5" fill="#ffffff" stroke="#2563eb" strokeWidth="2" />
                  <circle cx="420" cy="18" r="4" fill="#2563eb" stroke="#ffffff" strokeWidth="2" />
                </svg>
              </div>

              <div className="board-bottom-row">
                <div className="board-stat">
                  <Icon name="checkCircle" size={13} className="stat-icon-green" />
                  <span>162 Transactions Audited</span>
                </div>
                <div className="board-stat">
                  <Icon name="shield" size={13} className="stat-icon-blue" />
                  <span>CSRF & Session Protected</span>
                </div>
                <div className="board-stat">
                  <Icon name="chart" size={13} className="stat-icon-cyan" />
                  <span>Zero-Delta Reconciled</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Right Authentication Card Section */}
      <section className="login-side">
        <div className="mobile-brand-bar">
          <div className="mobile-logo-frame">
            <img src="/sepl_logo.webp" alt="SEPL logo" />
          </div>
          <div className="mobile-brand-meta">
            <strong>SEPL</strong>
            <small>AI Data Analysis Platform</small>
          </div>
        </div>

        {recoveryStep === 0 ? (
          <form className="login-card" onSubmit={submit} noValidate>
            <div className="card-header">
              <div className="card-badge-icon">
                <Icon name="shield" size={24} />
              </div>
              <h2>Welcome Back</h2>
              <p className="login-subtitle">Sign in to your enterprise workspace</p>
            </div>

            <div className="form-fields">
              <div className="input-group">
                <label htmlFor="login-identity" className="input-label">User Name / Email</label>
                <div className="login-field">
                  <span className="field-icon"><Icon name="user" size={18} /></span>
                  <input
                    id="login-identity"
                    autoComplete="username"
                    value={identity}
                    onChange={e => setIdentity(e.target.value)}
                    placeholder="name@company.com"
                    spellCheck={false}
                    disabled={busy || lockSeconds > 0}
                  />
                </div>
              </div>

              <div className="input-group">
                <div className="label-row">
                  <label htmlFor="login-password" className="input-label">Password</label>
                  <button
                    type="button"
                    className="text-action forgot-link"
                    onClick={() => { setError(''); setRecoveryStep(1) }}
                    disabled={busy}
                  >
                    Forgot Password?
                  </button>
                </div>
                <div className="login-field">
                  <span className="field-icon"><Icon name="lock" size={18} /></span>
                  <input
                    id="login-password"
                    type={visible ? 'text' : 'password'}
                    autoComplete="current-password"
                    value={password}
                    onChange={e => setPassword(e.target.value)}
                    placeholder="Enter password"
                    disabled={busy || lockSeconds > 0}
                  />
                  <button
                    type="button"
                    className="password-toggle"
                    aria-label={visible ? 'Hide password' : 'Show password'}
                    onClick={() => setVisible(v => !v)}
                    disabled={busy || lockSeconds > 0}
                  >
                    <Icon name={visible ? 'eyeOff' : 'eye'} size={18} />
                  </button>
                </div>
              </div>

              <div className="login-options">
                <label className="remember-option">
                  <input
                    type="checkbox"
                    checked={remember}
                    onChange={e => setRemember(e.target.checked)}
                    disabled={busy || lockSeconds > 0}
                  />
                  <span>Remember Me</span>
                </label>
              </div>
            </div>

            {error && (
              <div className="login-error" role="alert">
                <Icon name="alertCircle" size={18} className="alert-icon" />
                <span>{error}</span>
              </div>
            )}

            {lockSeconds > 0 && (
              <div className="login-lockout" role="status">
                <Icon name="lock" size={18} className="alert-icon" />
                <span>Sign in is temporarily locked. Try again in {Math.floor(lockSeconds / 60)}:{String(lockSeconds % 60).padStart(2, '0')}.</span>
              </div>
            )}

            <button
              className="login-submit"
              disabled={busy || lockSeconds > 0}
              type="submit"
              aria-label="Login"
            >
              {busy ? (
                <span className="login-spinner" />
              ) : (
                <Icon name="login" size={20} />
              )}
              <span>{busy ? 'Signing in…' : lockSeconds > 0 ? 'Please wait' : 'Sign In'}</span>
            </button>

            <footer className="card-footer">
              <div className="card-divider" />
              <div className="powered-by">
                Powered by <strong>SEPL</strong> • Enterprise Financial Intelligence
              </div>
            </footer>
          </form>
        ) : (
          <form className="login-card" onSubmit={recoveryStep === 1 ? requestRecovery : recoveryStep === 2 ? verifyOTP : resetPassword}>
            <div className="card-header">
              <div className="card-badge-icon recovery">
                <Icon name={recoveryStep === 1 ? 'mail' : recoveryStep === 2 ? 'shield' : 'key'} size={24} />
              </div>
              <h2>{recoveryStep === 1 ? 'Reset Password' : recoveryStep === 2 ? 'Verify Email' : 'Choose Password'}</h2>
              <p className="login-subtitle">
                {recoveryStep === 1
                  ? 'Enter your registered email address'
                  : recoveryStep === 2
                  ? 'Enter the six-digit code sent to your email'
                  : 'Set a new password for your account'}
              </p>
            </div>

            <div className="form-fields">
              {recoveryStep === 1 && (
                <div className="input-group">
                  <label htmlFor="recovery-email" className="input-label">Registered Email</label>
                  <div className="login-field">
                    <span className="field-icon"><Icon name="mail" size={18} /></span>
                    <input
                      id="recovery-email"
                      required
                      type="email"
                      autoComplete="email"
                      value={recoveryEmail}
                      onChange={e => setRecoveryEmail(e.target.value)}
                      placeholder="Registered email"
                      disabled={busy}
                    />
                  </div>
                </div>
              )}

              {recoveryStep === 2 && (
                <div className="input-group">
                  <div className="label-row">
                    <label htmlFor="otp-code" className="input-label">Verification Code</label>
                    <button
                      type="button"
                      className="text-action"
                      disabled={countdown > 0 || busy}
                      onClick={requestRecovery}
                    >
                      {countdown > 0 ? `Resend in ${countdown}s` : 'Resend code'}
                    </button>
                  </div>
                  <div className="login-field otp-field">
                    <input
                      id="otp-code"
                      required
                      inputMode="numeric"
                      pattern="[0-9]{6}"
                      maxLength={6}
                      value={otp}
                      onChange={e => setOtp(e.target.value)}
                      placeholder="6-digit verification code"
                      className="otp-input"
                      disabled={busy}
                    />
                  </div>
                </div>
              )}

              {recoveryStep === 3 && (
                <>
                  <div className="input-group">
                    <label htmlFor="new-pass" className="input-label">New Password</label>
                    <div className="login-field">
                      <span className="field-icon"><Icon name="lock" size={18} /></span>
                      <input
                        id="new-pass"
                        required
                        type="password"
                        autoComplete="new-password"
                        minLength={12}
                        value={newPassword}
                        onChange={e => setNewPassword(e.target.value)}
                        placeholder="New password (12+ characters)"
                        disabled={busy}
                      />
                    </div>
                  </div>
                  <div className="input-group">
                    <label htmlFor="confirm-pass" className="input-label">Confirm New Password</label>
                    <div className="login-field">
                      <span className="field-icon"><Icon name="lock" size={18} /></span>
                      <input
                        id="confirm-pass"
                        required
                        type="password"
                        name="confirmPassword"
                        autoComplete="new-password"
                        placeholder="Confirm new password"
                        disabled={busy}
                      />
                    </div>
                  </div>
                </>
              )}
            </div>

            {error && (
              <div className="login-error" role="alert">
                <Icon name="alertCircle" size={18} className="alert-icon" />
                <span>{error}</span>
              </div>
            )}

            <button
              className="login-submit"
              disabled={busy || (!countdown && recoveryStep === 2 && otp.length !== 6)}
              type="submit"
              aria-label={recoveryStep === 1 ? 'Send recovery code' : recoveryStep === 2 ? 'Verify code' : 'Reset password'}
            >
              {busy ? (
                <span className="login-spinner" />
              ) : (
                <Icon name="login" size={20} />
              )}
              <span>
                {busy
                  ? 'Please wait…'
                  : recoveryStep === 1
                  ? 'Send recovery code'
                  : recoveryStep === 2
                  ? 'Verify code'
                  : 'Reset password'}
              </span>
            </button>

            <button
              type="button"
              className="text-action recovery-back"
              onClick={() => { setRecoveryStep(0); setError('') }}
              disabled={busy}
              aria-label="Back to sign in"
            >
              ← Back to sign in
            </button>

            <footer className="card-footer">
              <div className="card-divider" />
              <div className="powered-by">
                Powered by <strong>SEPL</strong> • Enterprise Financial Intelligence
              </div>
            </footer>
          </form>
        )}
      </section>
    </main>
  )
}
