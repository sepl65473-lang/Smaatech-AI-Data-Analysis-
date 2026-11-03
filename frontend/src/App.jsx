import { BrowserRouter, Routes, Route, Navigate, useLocation, useNavigate } from 'react-router-dom'
import { useEffect, useState } from 'react'
import api from './api/client'
import Home from './pages/Home'
import Results from './pages/Results'
import Login from './pages/Login'

function RoutedApp() {
  const [auth, setAuth] = useState('loading')
  const [user, setUser] = useState(null)
  const [showPasswordDialog, setShowPasswordDialog] = useState(false)
  const location = useLocation()
  const navigate = useNavigate()
  useEffect(() => {
    api.get('/auth/csrf').then(() => api.get('/auth/me')).then(({ data }) => { setUser(data.user); setAuth('signed-in') }).catch(() => setAuth('signed-out'))
  }, [])
  useEffect(() => {
    const refreshAuth = () => api.get('/auth/me').then(({ data }) => { setUser(data.user); setAuth('signed-in') }).catch(() => { setUser(null); setAuth('signed-out') })
    window.addEventListener('sepl-auth-change', refreshAuth)
    return () => window.removeEventListener('sepl-auth-change', refreshAuth)
  }, [])
  async function logout() {
    try { await api.post('/auth/logout') } finally { setUser(null); setAuth('signed-out'); navigate('/login', { replace: true }) }
  }
  if (auth === 'loading') return <div className="min-h-screen grid place-items-center text-slate-600">Checking your secure session…</div>
  return <>
    {auth === 'signed-in' && <div className="fixed right-4 top-4 z-[100] flex items-center gap-2"><button type="button" onClick={()=>setShowPasswordDialog(true)} className="rounded-lg border bg-white px-3 py-2 text-sm font-semibold text-slate-700 shadow">Change password</button><button type="button" onClick={logout} className="rounded-lg border bg-white px-3 py-2 text-sm font-semibold text-slate-700 shadow">Sign out</button></div>}
    {showPasswordDialog&&<PasswordDialog onClose={()=>setShowPasswordDialog(false)}/>}
    <Routes>
      <Route path="/login" element={auth === 'signed-in' ? <Navigate to="/" replace/> : <Login/>}/>
      <Route path="/" element={auth === 'signed-in' ? <Home/> : <Navigate to="/login" replace state={{ from: location }}/>} />
      <Route path="/results" element={auth === 'signed-in' ? <Results/> : <Navigate to="/login" replace state={{ from: location }}/>} />
      <Route path="*" element={<Navigate to={auth === 'signed-in' ? '/' : '/login'} replace />} />
    </Routes>
  </>
}

function PasswordDialog({ onClose }) {
  const [current, setCurrent] = useState('')
  const [next, setNext] = useState('')
  const [confirm, setConfirm] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  async function submit(event) {
    event.preventDefault(); setError('')
    if (next !== confirm) { setError('The new passwords do not match.'); return }
    if (next.length < 12 || !/[A-Z]/.test(next) || !/[a-z]/.test(next) || !/[0-9]/.test(next) || !/[^A-Za-z0-9]/.test(next)) { setError('Use at least 12 characters with uppercase, lowercase, number and symbol characters.'); return }
    setBusy(true)
    try { await api.post('/auth/change-password', { current_password: current, new_password: next }); onClose() }
    catch (err) { setError(err?.response?.data?.detail || 'Password could not be changed. Please try again.') }
    finally { setBusy(false) }
  }
  return <div className="fixed inset-0 z-[120] grid place-items-center bg-slate-950/50 p-4" role="presentation" onMouseDown={e=>e.target===e.currentTarget&&onClose()}><form onSubmit={submit} className="w-full max-w-md space-y-4 rounded-2xl bg-white p-6 shadow-2xl" aria-labelledby="password-dialog-title"><div className="flex items-center justify-between"><h2 id="password-dialog-title" className="text-xl font-bold text-slate-800">Change password</h2><button type="button" onClick={onClose} aria-label="Close" className="rounded p-2 text-slate-500 hover:bg-slate-100">×</button></div><label className="block text-sm font-medium text-slate-700">Current password<input required type="password" autoComplete="current-password" value={current} onChange={e=>setCurrent(e.target.value)} className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2"/></label><label className="block text-sm font-medium text-slate-700">New password<input required type="password" autoComplete="new-password" value={next} onChange={e=>setNext(e.target.value)} className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2"/></label><label className="block text-sm font-medium text-slate-700">Confirm new password<input required type="password" autoComplete="new-password" value={confirm} onChange={e=>setConfirm(e.target.value)} className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2"/></label>{error&&<p role="alert" className="rounded bg-red-50 p-3 text-sm text-red-700">{error}</p>}<button disabled={busy} className="w-full rounded-lg bg-blue-700 px-4 py-3 font-semibold text-white disabled:opacity-60">{busy?'Changing…':'Change password'}</button></form></div>
}

export default function App() {
  return (
    <BrowserRouter><RoutedApp/></BrowserRouter>
  )
}
