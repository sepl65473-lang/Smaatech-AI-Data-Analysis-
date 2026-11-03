import { useEffect, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import api, { getErrorMessage } from '../api/client'
import './Login.css'

function Icon({ name, size = 22 }) {
  const paths = {
    user: <><circle cx="12" cy="8" r="4"/><path d="M4 21v-2a8 8 0 0 1 16 0v2z"/></>,
    lock: <><rect x="4" y="10" width="16" height="11" rx="2"/><path d="M8 10V7a4 4 0 1 1 8 0v3m-4 5v2"/></>,
    eye: <><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12Z"/><circle cx="12" cy="12" r="3"/></>,
    eyeOff: <><path d="m3 3 18 18M10.6 10.6a2 2 0 0 0 2.8 2.8"/><path d="M9.9 5.2A10 10 0 0 1 12 5c6.5 0 10 7 10 7a14 14 0 0 1-3.1 3.8M6.2 6.2C3.5 8 2 12 2 12s3.5 7 10 7a9.8 9.8 0 0 0 3-.5"/></>,
    chart: <><path d="M4 19V9h4v10zm6 0V5h4v14zm6 0v-7h4v7z"/></>,
    chip: <><rect x="6" y="6" width="12" height="12" rx="2"/><path d="M9 2v4m6-4v4M9 18v4m6-4v4M2 9h4m-4 6h4m12-6h4m-4 6h4M10 14l2-5 2 5"/></>,
    shield: <><path d="M12 22s8-4 8-11V5l-8-3-8 3v6c0 7 8 11 8 11Z"/><path d="m9 12 2 2 4-4"/></>,
    bolt: <path d="m13 2-3 9h7L9 22l2-9H4z"/>,
    login: <><path d="M10 17l5-5-5-5m5 5H3"/><path d="M12 3h6a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-6"/></>,
  }
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{paths[name]}</svg>
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

  useEffect(() => {
    if (!countdown && !lockSeconds) return undefined
    const timer = window.setInterval(() => { setCountdown(v => Math.max(0, v - 1)); setLockSeconds(v => Math.max(0, v - 1)) }, 1000)
    return () => window.clearInterval(timer)
  }, [countdown > 0, lockSeconds > 0])

  useEffect(() => {
    setError('')
    setBusy(false)
  }, [location.key])

  async function submit(event) {
    event.preventDefault()
    setError('')
    if (!identity.trim() || !password) { setError('Enter your email and password to continue.'); return }
    setBusy(true)
    try {
      await api.get('/auth/csrf')
      await api.post('/auth/login', { identity: identity.trim(), password, remember })
      window.dispatchEvent(new Event('sepl-auth-change'))
      navigate(location.state?.from?.pathname || '/', { replace: true })
    } catch (err) {
      const message = err?.response?.status === 404
        ? 'The login endpoint returned HTTP 404. Check that the backend is running the authentication routes.'
        : getErrorMessage(err)
      const seconds = Number(message.match(/(?:in|for)\s+(\d+)\s+seconds?/i)?.[1] || 0)
      if (seconds) setLockSeconds(seconds)
      setError(message)
    }
    finally { setBusy(false) }
  }

  async function requestRecovery(event) {
    event.preventDefault(); setError(''); setBusy(true)
    try { const { data } = await api.post('/auth/recovery/request', { email: recoveryEmail }); setRecoveryStep(2); setCountdown(60); setError(data.message) }
    catch (err) { setError(getErrorMessage(err)) } finally { setBusy(false) }
  }
  async function verifyOTP(event) {
    event.preventDefault(); setError(''); setBusy(true)
    try { const { data } = await api.post('/auth/recovery/verify', { email: recoveryEmail, otp }); setResetToken(data.reset_token); setRecoveryStep(3) }
    catch (err) { setError(getErrorMessage(err)) } finally { setBusy(false) }
  }
  async function resetPassword(event) {
    event.preventDefault(); setError('')
    const confirm = event.currentTarget.elements.confirmPassword.value
    if (newPassword !== confirm) { setError('The passwords do not match.'); return }
    setBusy(true)
    try { await api.post('/auth/recovery/reset', { reset_token: resetToken, new_password: newPassword }); setRecoveryStep(0); setPassword(''); setError('Password reset. Sign in with your new password.') }
    catch (err) { setError(getErrorMessage(err)) } finally { setBusy(false) }
  }

  return <main className="login-page">
    <section className="login-showcase" aria-label="SEPL platform introduction">
      <div className="login-brand">
        <div className="brand-logo"><img src="/sepl_logo.png" alt="SEPL logo"/></div>
        <span className="brand-divider"/>
        <div><strong>SEPL</strong><small>Smart Solutions. Better Tomorrow.</small></div>
      </div>
      <div className="showcase-copy">
        <h1>AI Data Analysis<br/><span>Platform</span></h1>
        <p>Transform Your Data into<br/>Actionable Insights with AI</p>
      </div>
      <div className="feature-list">
        {[['chart','Advanced','Analytics'],['chip','AI-Powered','Insights'],['shield','Secure &','Reliable'],['bolt','Real-Time','Dashboard']].map(([icon,a,b])=><div className="feature-card" key={a}><Icon name={icon} size={31}/><b>{a}<br/>{b}</b></div>)}
      </div>
      <img className="analytics-art" src="/sepl-login-art.png" alt="" aria-hidden="true" />
    </section>
    <section className="login-side">
      {recoveryStep===0?<form className="login-card" onSubmit={submit} noValidate>
        <div className="login-avatar"><Icon name="user" size={56}/></div>
        <h2>Welcome Back</h2><p className="login-subtitle">Sign in to your account</p>
        <label className="login-field"><Icon name="user" size={22}/><span className="sr-only">User Name / Email</span><input autoComplete="username" value={identity} onChange={e=>setIdentity(e.target.value)} placeholder="User Name / Email" /></label>
        <label className="login-field"><Icon name="lock" size={22}/><span className="sr-only">Password</span><input type={visible?'text':'password'} autoComplete="current-password" value={password} onChange={e=>setPassword(e.target.value)} placeholder="Password"/><button type="button" className="password-toggle" aria-label={visible?'Hide password':'Show password'} onClick={()=>setVisible(v=>!v)}><Icon name={visible?'eyeOff':'eye'} size={21}/></button></label>
        <div className="login-options"><label className="remember-option"><input type="checkbox" checked={remember} onChange={e=>setRemember(e.target.checked)}/><span>Remember Me</span></label><button className="text-action" type="button" onClick={()=>{setError('');setRecoveryStep(1)}}>Forgot Password?</button></div>
        {error&&<div className="login-error" role="alert">{error}</div>}
        {lockSeconds>0&&<p className="login-lockout" role="status">Sign in is temporarily locked. Try again in {Math.floor(lockSeconds/60)}:{String(lockSeconds%60).padStart(2,'0')}.</p>}
        <button className="login-submit" disabled={busy||lockSeconds>0}>{busy?<span className="login-spinner"/>:<Icon name="login" size={25}/>}<span>{busy?'Signing in…':lockSeconds>0?'Please wait':'Login'}</span></button>
        <div className="login-separator"><span/><b>or</b><span/></div><div className="powered-by">Powered by <strong>SEPL</strong></div>
      </form>:<form className="login-card" onSubmit={recoveryStep===1?requestRecovery:recoveryStep===2?verifyOTP:resetPassword}>
        <div className="login-avatar"><Icon name="lock" size={50}/></div>
        <h2>{recoveryStep===1?'Reset Password':recoveryStep===2?'Verify Email':'Choose Password'}</h2>
        <p className="login-subtitle">{recoveryStep===1?'Enter your registered email address':recoveryStep===2?'Enter the six-digit code sent to your email':'Set a new password for your account'}</p>
        {recoveryStep===1&&<label className="login-field"><span className="sr-only">Email address</span><input required type="email" autoComplete="email" value={recoveryEmail} onChange={e=>setRecoveryEmail(e.target.value)} placeholder="Registered email"/></label>}
        {recoveryStep===2&&<><label className="login-field"><span className="sr-only">Email verification code</span><input required inputMode="numeric" pattern="[0-9]{6}" maxLength={6} value={otp} onChange={e=>setOtp(e.target.value)} placeholder="6-digit verification code"/></label><button type="button" className="text-action" disabled={countdown>0} onClick={requestRecovery}>{countdown>0?`Resend in ${countdown}s`:'Resend code'}</button></>}
        {recoveryStep===3&&<><label className="login-field"><Icon name="lock"/><span className="sr-only">New password</span><input required type="password" autoComplete="new-password" minLength={12} value={newPassword} onChange={e=>setNewPassword(e.target.value)} placeholder="New password (12+ characters)"/></label><label className="login-field"><Icon name="lock"/><span className="sr-only">Confirm new password</span><input required type="password" name="confirmPassword" autoComplete="new-password" placeholder="Confirm new password"/></label></>}
        {error&&<div className="login-error" role="alert">{error}</div>}
        <button className="login-submit" disabled={busy||(!countdown&&recoveryStep===2&&otp.length!==6)}>{busy?<span className="login-spinner"/>:<Icon name="login"/>}<span>{busy?'Please wait…':recoveryStep===1?'Send recovery code':recoveryStep===2?'Verify code':'Reset password'}</span></button>
        <button type="button" className="text-action recovery-back" onClick={()=>{setRecoveryStep(0);setError('')}}>Back to sign in</button>
        <div className="login-separator"><span/><b>Powered by <strong>SEPL</strong></b><span/></div>
      </form>}
    </section>
  </main>
}
