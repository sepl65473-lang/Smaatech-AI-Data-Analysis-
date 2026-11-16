import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams, Link } from 'react-router-dom'
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
    check: (
      <polyline points="20 6 9 17 4 12" />
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
    sparkles: (
      <path d="m12 3-1.9 5.8a2 2 0 0 1-1.3 1.3L3 12l5.8 1.9a2 2 0 0 1 1.3 1.3L12 21l1.9-5.8a2 2 0 0 1 1.3-1.3L21 12l-5.8-1.9a2 2 0 0 1-1.3-1.3L12 3z" />
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

export default function Activate() {
  const [searchParams] = useSearchParams()
  const token = searchParams.get('token') || ''
  const navigate = useNavigate()

  const [loading, setLoading] = useState(true)
  const [userInfo, setUserInfo] = useState(null)
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [visible, setVisible] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState(false)

  // Verify invitation token on mount
  useEffect(() => {
    if (!token) {
      setError('Activation token is missing. Please check the link from your invitation email.')
      setLoading(false)
      return
    }

    let isMounted = true
    api.get(`/auth/activate/verify?token=${encodeURIComponent(token)}`)
      .then(({ data }) => {
        if (isMounted) {
          setUserInfo(data)
          setLoading(false)
        }
      })
      .catch((err) => {
        if (isMounted) {
          setError(getErrorMessage(err) || 'This invitation link is invalid, expired, or has already been used.')
          setLoading(false)
        }
      })

    return () => { isMounted = false }
  }, [token])

  // Password criteria check
  const criteria = {
    length: password.length >= 12,
    upper: /[A-Z]/.test(password),
    lower: /[a-z]/.test(password),
    number: /[0-9]/.test(password),
    symbol: /[^A-Za-z0-9]/.test(password),
  }
  const allCriteriaMet = Object.values(criteria).every(Boolean)

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')

    if (!allCriteriaMet) {
      setError('Please ensure your password satisfies all security requirements.')
      return
    }
    if (password !== confirmPassword) {
      setError('Passwords do not match. Please re-enter.')
      return
    }

    setSubmitting(true)
    try {
      await api.get('/auth/csrf')
      await api.post('/auth/activate', { token, password })
      setSuccess(true)
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <main className="login-page">
      {/* Left Brand Showcase */}
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
              <span>Enterprise Account Activation</span>
            </div>
            <h1 className="showcase-title">
              Activate Your
              <span className="title-accent">Secure Workspace</span>
            </h1>
            <p className="showcase-desc">
              You have been invited to the SEPL AI Data Analysis Platform. Set your password to access enterprise financial analytics, automated reconciliation, and multi-format deliverables.
            </p>

            <div className="feature-grid">
              <div className="feature-pill">
                <div className="feature-icon"><Icon name="shield" size={18} /></div>
                <div className="feature-meta">
                  <strong>Role-Based Access</strong>
                  <small>Tailored team permissions</small>
                </div>
              </div>
              <div className="feature-pill">
                <div className="feature-icon"><Icon name="checkCircle" size={18} /></div>
                <div className="feature-meta">
                  <strong>End-to-End Security</strong>
                  <small>Encrypted session tokens</small>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Right Activation Card */}
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

        <div className="login-card">
          {loading ? (
            <div className="card-header text-center py-12">
              <span className="login-spinner inline-block" />
              <p className="login-subtitle mt-4">Verifying your secure invitation…</p>
            </div>
          ) : success ? (
            <div className="card-header text-center py-6">
              <div className="w-14 h-14 mx-auto mb-4 rounded-full bg-emerald-100 text-emerald-600 flex items-center justify-center">
                <Icon name="check" size={28} />
              </div>
              <h2 className="text-2xl font-bold text-slate-900">Account Activated!</h2>
              <p className="login-subtitle mt-2">
                Your password has been securely configured. You can now sign in to access your workspace.
              </p>
              <button
                type="button"
                onClick={() => navigate('/login')}
                className="login-submit mt-6 w-full"
              >
                <Icon name="user" size={18} />
                <span>Sign In to Workspace</span>
              </button>
            </div>
          ) : error && !userInfo ? (
            <div className="card-header text-center py-6">
              <div className="w-14 h-14 mx-auto mb-4 rounded-full bg-red-100 text-red-600 flex items-center justify-center">
                <Icon name="alertCircle" size={28} />
              </div>
              <h2 className="text-xl font-bold text-slate-900">Invalid Invitation Link</h2>
              <p className="login-subtitle mt-2 text-slate-600">{error}</p>
              <div className="mt-6">
                <Link to="/login" className="text-sm font-semibold text-blue-600 hover:text-blue-700">
                  ← Return to Sign In
                </Link>
              </div>
            </div>
          ) : (
            <form onSubmit={handleSubmit} noValidate>
              <div className="card-header">
                <div className="card-badge-icon">
                  <Icon name="sparkles" size={24} />
                </div>
                <h2>Welcome, {userInfo?.full_name || 'Team Member'}</h2>
                <p className="login-subtitle">
                  Activate account for <strong>{userInfo?.email}</strong>
                </p>
              </div>

              <div className="form-fields">
                <div className="input-group">
                  <label htmlFor="activate-password" className="input-label">New Password</label>
                  <div className="login-field">
                    <span className="field-icon"><Icon name="lock" size={18} /></span>
                    <input
                      id="activate-password"
                      type={visible ? 'text' : 'password'}
                      autoComplete="new-password"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      placeholder="Enter new password (12+ chars)"
                      disabled={submitting}
                      required
                    />
                    <button
                      type="button"
                      className="password-toggle"
                      aria-label={visible ? 'Hide password' : 'Show password'}
                      onClick={() => setVisible(!visible)}
                    >
                      <Icon name={visible ? 'eyeOff' : 'eye'} size={18} />
                    </button>
                  </div>
                </div>

                <div className="input-group">
                  <label htmlFor="activate-confirm" className="input-label">Confirm Password</label>
                  <div className="login-field">
                    <span className="field-icon"><Icon name="lock" size={18} /></span>
                    <input
                      id="activate-confirm"
                      type={visible ? 'text' : 'password'}
                      autoComplete="new-password"
                      value={confirmPassword}
                      onChange={(e) => setConfirmPassword(e.target.value)}
                      placeholder="Confirm your password"
                      disabled={submitting}
                      required
                    />
                  </div>
                </div>

                {/* Password Criteria Checklist */}
                <div className="p-3 bg-slate-50 rounded-xl border border-slate-200/80 text-xs space-y-1.5 text-slate-600">
                  <span className="font-semibold block text-slate-700">Password Requirements:</span>
                  <div className="grid grid-cols-2 gap-1.5 pt-1">
                    <span className={`flex items-center gap-1.5 ${criteria.length ? 'text-emerald-700 font-medium' : 'text-slate-500'}`}>
                      <Icon name={criteria.length ? 'check' : 'alertCircle'} size={13} /> 12+ characters
                    </span>
                    <span className={`flex items-center gap-1.5 ${criteria.upper ? 'text-emerald-700 font-medium' : 'text-slate-500'}`}>
                      <Icon name={criteria.upper ? 'check' : 'alertCircle'} size={13} /> Uppercase letter
                    </span>
                    <span className={`flex items-center gap-1.5 ${criteria.lower ? 'text-emerald-700 font-medium' : 'text-slate-500'}`}>
                      <Icon name={criteria.lower ? 'check' : 'alertCircle'} size={13} /> Lowercase letter
                    </span>
                    <span className={`flex items-center gap-1.5 ${criteria.number ? 'text-emerald-700 font-medium' : 'text-slate-500'}`}>
                      <Icon name={criteria.number ? 'check' : 'alertCircle'} size={13} /> Number (0-9)
                    </span>
                    <span className={`flex items-center gap-1.5 col-span-2 ${criteria.symbol ? 'text-emerald-700 font-medium' : 'text-slate-500'}`}>
                      <Icon name={criteria.symbol ? 'check' : 'alertCircle'} size={13} /> Symbol (!@#$%^&*...)
                    </span>
                  </div>
                </div>
              </div>

              {error && (
                <div className="login-error mt-4" role="alert">
                  <Icon name="alertCircle" size={18} className="alert-icon" />
                  <span>{error}</span>
                </div>
              )}

              <button
                className="login-submit mt-5"
                disabled={submitting || !allCriteriaMet || password !== confirmPassword}
                type="submit"
              >
                {submitting ? (
                  <span className="login-spinner" />
                ) : (
                  <Icon name="shield" size={18} />
                )}
                <span>{submitting ? 'Activating…' : 'Activate Account & Proceed'}</span>
              </button>

              <footer className="card-footer mt-4">
                <div className="card-divider" />
                <div className="powered-by">
                  Powered by <strong>SEPL</strong> • Enterprise Financial Intelligence
                </div>
              </footer>
            </form>
          )}
        </div>
      </section>
    </main>
  )
}

