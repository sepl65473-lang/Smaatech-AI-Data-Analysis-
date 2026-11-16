import { useState, useEffect } from 'react'
import api, { getErrorMessage } from '../api/client'

const PERMISSION_OPTIONS = [
  { id: 'platform:access', label: 'Platform Access', desc: 'Sign in and view dashboards' },
  { id: 'statements:upload', label: 'Upload Statements', desc: 'Process bank statements & datasets' },
  { id: 'reports:export', label: 'Export Deliverables', desc: 'Download Excel, PDF, CSV, ZIP' },
  { id: 'analytics:view', label: 'Advanced Analytics', desc: 'View financial intelligence & summaries' },
  { id: 'users:manage', label: 'User Management', desc: 'Create and manage user accounts (Admin only)' },
  { id: 'audit:read', label: 'Audit Log Access', desc: 'Inspect security and admin audit events (Admin only)' },
  { id: 'sessions:revoke', label: 'Session Revocation', desc: 'Revoke active sessions (Admin only)' },
]

export default function AdminUsersModal({ isOpen, onClose, currentUser }) {
  const [activeTab, setActiveTab] = useState('users') // 'users' | 'audit'
  const [users, setUsers] = useState([])
  const [auditEvents, setAuditEvents] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [notification, setNotification] = useState('')

  // Search & Filters
  const [searchQuery, setSearchQuery] = useState('')
  const [roleFilter, setRoleFilter] = useState('all')
  const [statusFilter, setStatusFilter] = useState('all')

  // Modals inside Admin
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [showEditModal, setShowEditModal] = useState(false)
  const [editingUser, setEditingUser] = useState(null)
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(null) // user object
  const [createdInvitation, setCreatedInvitation] = useState(null) // { user, invitation_url, email_sent, message }

  // Create Form State
  const [createForm, setCreateForm] = useState({
    full_name: '',
    email: '',
    role: 'standard_user',
    permissions: ['platform:access', 'statements:upload', 'reports:export', 'analytics:view'],
  })
  const [createSubmitting, setCreateSubmitting] = useState(false)
  const [copiedLink, setCopiedLink] = useState(false)

  // Load Users and Audit
  useEffect(() => {
    if (!isOpen) return
    loadUsers()
    loadAudit()
  }, [isOpen])

  async function loadUsers() {
    setLoading(true)
    setError('')
    try {
      const { data } = await api.get('/auth/admin/users')
      setUsers(data.users || [])
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  async function loadAudit() {
    try {
      const { data } = await api.get('/auth/admin/audit')
      setAuditEvents((data.events || []).reverse())
    } catch {
      // ignore audit load failure if standard user
    }
  }

  function showToast(msg) {
    setNotification(msg)
    setTimeout(() => setNotification(''), 4000)
  }

  // Create User Handler
  async function handleCreateUser(e) {
    e.preventDefault()
    setCreateSubmitting(true)
    setError('')
    try {
      const { data } = await api.post('/auth/admin/users', createForm)
      setCreatedInvitation(data)
      loadUsers()
      loadAudit()
      showToast('User created successfully.')
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setCreateSubmitting(false)
    }
  }

  // Edit User Handler
  async function handleUpdateUser(e) {
    e.preventDefault()
    if (!editingUser) return
    try {
      await api.patch(`/auth/admin/users/${editingUser.id}`, {
        full_name: editingUser.full_name,
        role: editingUser.role,
        status: editingUser.status,
        permissions: editingUser.permissions,
      })
      setShowEditModal(false)
      setEditingUser(null)
      loadUsers()
      loadAudit()
      showToast('User updated successfully.')
    } catch (err) {
      setError(getErrorMessage(err))
    }
  }

  // Suspend / Activate toggle
  async function handleToggleStatus(u) {
    const nextStatus = u.status === 'suspended' ? 'active' : 'suspended'
    try {
      await api.patch(`/auth/admin/users/${u.id}`, { status: nextStatus })
      loadUsers()
      loadAudit()
      showToast(`User account ${nextStatus === 'active' ? 'activated' : 'suspended'}.`)
    } catch (err) {
      setError(getErrorMessage(err))
    }
  }

  // Unlock user
  async function handleUnlock(u) {
    try {
      await api.post(`/auth/admin/users/${u.id}/unlock`)
      loadUsers()
      loadAudit()
      showToast('User account unlocked.')
    } catch (err) {
      setError(getErrorMessage(err))
    }
  }

  // Resend invitation
  async function handleResendInvitation(u) {
    try {
      const { data } = await api.post(`/auth/admin/users/${u.id}/resend-invitation`)
      loadUsers()
      loadAudit()
      setCreatedInvitation({
        user: u,
        invitation_url: data.invitation_url,
        email_sent: data.email_sent,
        message: data.message,
      })
      setShowCreateModal(true)
      showToast('Invitation renewed.')
    } catch (err) {
      setError(getErrorMessage(err))
    }
  }

  // Delete User
  async function handleDeleteUser(u) {
    try {
      await api.delete(`/auth/admin/users/${u.id}`)
      setShowDeleteConfirm(null)
      loadUsers()
      loadAudit()
      showToast('User account deleted.')
    } catch (err) {
      setError(getErrorMessage(err))
    }
  }

  // Filtered Users List
  const filteredUsers = users.filter((u) => {
    const query = searchQuery.toLowerCase().trim()
    const matchesSearch =
      !query ||
      u.email.toLowerCase().includes(query) ||
      (u.full_name && u.full_name.toLowerCase().includes(query))

    const matchesRole = roleFilter === 'all' || u.role === roleFilter
    const matchesStatus = statusFilter === 'all' || u.status === statusFilter

    return matchesSearch && matchesRole && matchesStatus
  })

  if (!isOpen) return null

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/60 backdrop-blur-sm p-4 overflow-y-auto"
      role="dialog"
      aria-modal="true"
      aria-labelledby="admin-modal-title"
    >
      <div className="relative w-full max-w-5xl bg-white dark:bg-slate-900 rounded-2xl shadow-2xl border border-slate-200 dark:border-slate-800 flex flex-col max-h-[92vh] overflow-hidden animate-in fade-in zoom-in-95 duration-150">
        {/* Header */}
        <div className="px-6 py-4.5 border-b border-slate-200 dark:border-slate-800 bg-slate-50/70 dark:bg-slate-800/50 flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <span className="w-10 h-10 rounded-xl bg-gradient-to-tr from-indigo-600 to-blue-500 text-white flex items-center justify-center text-lg shadow-sm">
              🛡️
            </span>
            <div>
              <div className="flex items-center gap-2">
                <h2 id="admin-modal-title" className="text-lg font-bold text-slate-900 dark:text-white">
                  Admin User Management
                </h2>
                <span className="text-[11px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-indigo-100 dark:bg-indigo-950/80 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800">
                  Super Admin
                </span>
              </div>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Create users, dispatch invitations, assign roles, and audit security events.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2.5">
            <button
              type="button"
              onClick={() => {
                setCreatedInvitation(null)
                setCreateForm({
                  full_name: '',
                  email: '',
                  role: 'standard_user',
                  permissions: ['platform:access', 'statements:upload', 'reports:export', 'analytics:view'],
                })
                setShowCreateModal(true)
              }}
              className="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold rounded-xl bg-blue-600 hover:bg-blue-700 text-white shadow-xs transition-colors"
            >
              <span>+</span>
              <span>Create User</span>
            </button>
            <button
              type="button"
              onClick={onClose}
              className="p-2 rounded-xl text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
              aria-label="Close"
            >
              ✕
            </button>
          </div>
        </div>

        {/* Notification Toast */}
        {notification && (
          <div className="bg-emerald-50 dark:bg-emerald-950/80 border-b border-emerald-200 dark:border-emerald-800 px-6 py-2.5 text-xs text-emerald-800 dark:text-emerald-200 flex items-center justify-between">
            <span>✓ {notification}</span>
            <button onClick={() => setNotification('')} className="text-emerald-600 hover:underline">Dismiss</button>
          </div>
        )}

        {/* Global Error Banner */}
        {error && (
          <div className="bg-red-50 dark:bg-red-950/80 border-b border-red-200 dark:border-red-800 px-6 py-2.5 text-xs text-red-800 dark:text-red-200 flex items-center justify-between">
            <span>⚠️ {error}</span>
            <button onClick={() => setError('')} className="text-red-600 hover:underline">Dismiss</button>
          </div>
        )}

        {/* Navigation Tabs */}
        <div className="px-6 pt-3 border-b border-slate-200 dark:border-slate-800 flex gap-4 text-xs font-semibold">
          <button
            type="button"
            onClick={() => setActiveTab('users')}
            className={`pb-2.5 border-b-2 transition-colors ${
              activeTab === 'users'
                ? 'border-blue-600 text-blue-600 dark:text-blue-400'
                : 'border-transparent text-slate-500 hover:text-slate-800 dark:hover:text-slate-200'
            }`}
          >
            Users & Roles ({users.length})
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('audit')}
            className={`pb-2.5 border-b-2 transition-colors ${
              activeTab === 'audit'
                ? 'border-blue-600 text-blue-600 dark:text-blue-400'
                : 'border-transparent text-slate-500 hover:text-slate-800 dark:hover:text-slate-200'
            }`}
          >
            Security Audit Log ({auditEvents.length})
          </button>
        </div>

        {/* Body Content */}
        <div className="p-6 overflow-y-auto flex-1 space-y-4">
          {activeTab === 'users' ? (
            <>
              {/* Filter and Search Bar */}
              <div className="flex flex-wrap items-center justify-between gap-3 bg-slate-50 dark:bg-slate-800/40 p-3 rounded-xl border border-slate-200/70 dark:border-slate-800">
                <div className="relative flex-1 min-w-[200px]">
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="Search by name or email…"
                    className="w-full text-xs bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-2 text-slate-800 dark:text-slate-100 placeholder-slate-400 focus:outline-hidden focus:border-blue-500"
                  />
                  {searchQuery && (
                    <button
                      onClick={() => setSearchQuery('')}
                      className="absolute right-2.5 top-2 text-xs text-slate-400 hover:text-slate-600"
                    >
                      ×
                    </button>
                  )}
                </div>

                <div className="flex items-center gap-2">
                  <select
                    value={roleFilter}
                    onChange={(e) => setRoleFilter(e.target.value)}
                    className="text-xs bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg px-2.5 py-2 text-slate-700 dark:text-slate-200 focus:outline-hidden"
                  >
                    <option value="all">All Roles</option>
                    <option value="administrator">Administrators</option>
                    <option value="standard_user">Standard Users</option>
                  </select>

                  <select
                    value={statusFilter}
                    onChange={(e) => setStatusFilter(e.target.value)}
                    className="text-xs bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg px-2.5 py-2 text-slate-700 dark:text-slate-200 focus:outline-hidden"
                  >
                    <option value="all">All Statuses</option>
                    <option value="active">Active</option>
                    <option value="pending_activation">Pending Activation</option>
                    <option value="suspended">Suspended</option>
                  </select>
                </div>
              </div>

              {/* Users Table */}
              <div className="border border-slate-200 dark:border-slate-800 rounded-xl overflow-hidden shadow-2xs">
                <table className="w-full text-left text-xs border-collapse">
                  <thead className="bg-slate-50/90 dark:bg-slate-800/80 text-slate-600 dark:text-slate-300 font-semibold border-b border-slate-200 dark:border-slate-800">
                    <tr>
                      <th className="py-3 px-4">User</th>
                      <th className="py-3 px-4">Role</th>
                      <th className="py-3 px-4">Status</th>
                      <th className="py-3 px-4 hidden md:table-cell">Permissions</th>
                      <th className="py-3 px-4 hidden lg:table-cell">Created / Active</th>
                      <th className="py-3 px-4 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 dark:divide-slate-800/70 text-slate-800 dark:text-slate-200">
                    {loading ? (
                      <tr>
                        <td colSpan={6} className="py-12 text-center text-slate-400">
                          Loading user accounts…
                        </td>
                      </tr>
                    ) : filteredUsers.length === 0 ? (
                      <tr>
                        <td colSpan={6} className="py-12 text-center text-slate-400">
                          No users matched your query.
                        </td>
                      </tr>
                    ) : (
                      filteredUsers.map((u) => {
                        const isSelf = currentUser?.email === u.email
                        const isPending = u.status === 'pending_activation'
                        const isSuspended = u.status === 'suspended'
                        const isLocked = u.locked_until && u.locked_until > Date.now() / 1000

                        return (
                          <tr key={u.id} className="hover:bg-slate-50/60 dark:hover:bg-slate-800/40 transition-colors">
                            {/* User details */}
                            <td className="py-3 px-4">
                              <div className="flex items-center gap-2.5">
                                <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-slate-200 to-slate-300 dark:from-slate-700 dark:to-slate-600 text-slate-700 dark:text-slate-200 font-bold flex items-center justify-center shrink-0">
                                  {u.full_name ? u.full_name.charAt(0).toUpperCase() : u.email.charAt(0).toUpperCase()}
                                </div>
                                <div className="min-w-0">
                                  <div className="font-semibold text-slate-900 dark:text-white truncate">
                                    {u.full_name || u.email.split('@')[0]}
                                    {isSelf && <span className="ml-1.5 text-[10px] text-blue-600 dark:text-blue-400 font-bold">(You)</span>}
                                  </div>
                                  <div className="text-[11px] text-slate-400 truncate">{u.email}</div>
                                </div>
                              </div>
                            </td>

                            {/* Role badge */}
                            <td className="py-3 px-4">
                              <span
                                className={`inline-block px-2 py-0.5 rounded-full text-[10.5px] font-semibold border ${
                                  u.role === 'administrator'
                                    ? 'bg-purple-50 dark:bg-purple-950/60 text-purple-700 dark:text-purple-300 border-purple-200 dark:border-purple-800'
                                    : 'bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border-slate-200 dark:border-slate-700'
                                }`}
                              >
                                {u.role === 'administrator' ? 'Administrator' : 'Standard User'}
                              </span>
                            </td>

                            {/* Status badge */}
                            <td className="py-3 px-4">
                              {isLocked ? (
                                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10.5px] font-semibold bg-orange-50 dark:bg-orange-950/60 text-orange-700 dark:text-orange-300 border border-orange-200 dark:border-orange-800">
                                  <span className="w-1.5 h-1.5 rounded-full bg-orange-500" /> Locked
                                </span>
                              ) : isPending ? (
                                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10.5px] font-semibold bg-amber-50 dark:bg-amber-950/60 text-amber-700 dark:text-amber-300 border border-amber-200 dark:border-amber-800">
                                  <span className="w-1.5 h-1.5 rounded-full bg-amber-500 animate-pulse" /> Pending Activation
                                </span>
                              ) : isSuspended ? (
                                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10.5px] font-semibold bg-red-50 dark:bg-red-950/60 text-red-700 dark:text-red-300 border border-red-200 dark:border-red-800">
                                  <span className="w-1.5 h-1.5 rounded-full bg-red-500" /> Suspended
                                </span>
                              ) : (
                                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10.5px] font-semibold bg-emerald-50 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800">
                                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" /> Active
                                </span>
                              )}
                            </td>

                            {/* Permissions chips */}
                            <td className="py-3 px-4 hidden md:table-cell">
                              <div className="flex flex-wrap gap-1 max-w-xs">
                                {(u.permissions || ['platform:access']).slice(0, 3).map((p) => (
                                  <span key={p} className="text-[10px] font-mono bg-slate-100 dark:bg-slate-800 px-1.5 py-0.5 rounded text-slate-600 dark:text-slate-400">
                                    {p.split(':')[1] || p}
                                  </span>
                                ))}
                                {(u.permissions || []).length > 3 && (
                                  <span className="text-[10px] text-slate-400">+{u.permissions.length - 3}</span>
                                )}
                              </div>
                            </td>

                            {/* Dates */}
                            <td className="py-3 px-4 hidden lg:table-cell text-slate-500 text-[11px]">
                              <div>Created: {u.created_at ? new Date(u.created_at * 1000).toLocaleDateString() : '—'}</div>
                              {u.activated_at && <div>Active: {new Date(u.activated_at * 1000).toLocaleDateString()}</div>}
                            </td>

                            {/* Actions Dropdown / Buttons */}
                            <td className="py-3 px-4 text-right">
                              <div className="inline-flex items-center gap-1">
                                {isLocked && (
                                  <button
                                    onClick={() => handleUnlock(u)}
                                    className="px-2 py-1 rounded bg-amber-50 hover:bg-amber-100 text-amber-700 text-[11px] font-medium"
                                    title="Unlock user account"
                                  >
                                    Unlock
                                  </button>
                                )}

                                {isPending && (
                                  <button
                                    onClick={() => handleResendInvitation(u)}
                                    className="px-2 py-1 rounded bg-blue-50 hover:bg-blue-100 text-blue-700 text-[11px] font-medium"
                                    title="Resend activation invitation"
                                  >
                                    Resend Invite
                                  </button>
                                )}

                                <button
                                  onClick={() => {
                                    setEditingUser({ ...u, permissions: u.permissions || [] })
                                    setShowEditModal(true)
                                  }}
                                  className="p-1.5 rounded hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-500 hover:text-slate-800 dark:hover:text-slate-200"
                                  title="Edit User"
                                >
                                  ✏️
                                </button>

                                {!isSelf && (
                                  <button
                                    onClick={() => handleToggleStatus(u)}
                                    className={`p-1.5 rounded hover:bg-slate-100 dark:hover:bg-slate-800 ${
                                      isSuspended ? 'text-emerald-600' : 'text-amber-600'
                                    }`}
                                    title={isSuspended ? 'Activate User' : 'Suspend User'}
                                  >
                                    {isSuspended ? '▶️' : '⏸️'}
                                  </button>
                                )}

                                {!isSelf && (
                                  <button
                                    onClick={() => setShowDeleteConfirm(u)}
                                    className="p-1.5 rounded hover:bg-red-50 dark:hover:bg-red-950/50 text-red-600"
                                    title="Safe Delete User"
                                  >
                                    🗑️
                                  </button>
                                )}
                              </div>
                            </td>
                          </tr>
                        )
                      })
                    )}
                  </tbody>
                </table>
              </div>
            </>
          ) : (
            /* Security Audit Log View */
            <div className="border border-slate-200 dark:border-slate-800 rounded-xl overflow-hidden shadow-2xs">
              <table className="w-full text-left text-xs border-collapse">
                <thead className="bg-slate-50/90 dark:bg-slate-800/80 text-slate-600 dark:text-slate-300 font-semibold border-b border-slate-200 dark:border-slate-800">
                  <tr>
                    <th className="py-3 px-4">Timestamp</th>
                    <th className="py-3 px-4">Event</th>
                    <th className="py-3 px-4">Actor</th>
                    <th className="py-3 px-4">Subject</th>
                    <th className="py-3 px-4">IP / Details</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800/70 text-slate-800 dark:text-slate-200 font-mono text-[11px]">
                  {auditEvents.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="py-12 text-center text-slate-400">
                        No audit events recorded yet.
                      </td>
                    </tr>
                  ) : (
                    auditEvents.slice(0, 50).map((ev, idx) => (
                      <tr key={ev.id || idx} className="hover:bg-slate-50/60 dark:hover:bg-slate-800/40">
                        <td className="py-2.5 px-4 text-slate-500 whitespace-nowrap">
                          {ev.timestamp ? new Date(ev.timestamp * 1000).toLocaleString() : 'Recent'}
                        </td>
                        <td className="py-2.5 px-4 font-semibold text-slate-900 dark:text-white">
                          <span className="px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-800">
                            {ev.event}
                          </span>
                        </td>
                        <td className="py-2.5 px-4 text-slate-600 dark:text-slate-400 truncate max-w-[120px]">
                          {ev.actor || 'System'}
                        </td>
                        <td className="py-2.5 px-4 text-slate-600 dark:text-slate-400 truncate max-w-[120px]">
                          {ev.subject || '—'}
                        </td>
                        <td className="py-2.5 px-4 text-slate-500 truncate max-w-[200px]">
                          {ev.source ? `IP: ${ev.source}` : ev.email || ev.role || '—'}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Create User Sub-Modal */}
        {showCreateModal && (
          <div className="fixed inset-0 z-60 flex items-center justify-center bg-slate-950/60 backdrop-blur-xs p-4">
            <div className="bg-white dark:bg-slate-900 rounded-2xl p-6 max-w-lg w-full border border-slate-200 dark:border-slate-800 shadow-2xl">
              {createdInvitation ? (
                <div className="space-y-4">
                  <div className="w-12 h-12 rounded-full bg-emerald-100 text-emerald-600 flex items-center justify-center text-xl mx-auto">
                    ✓
                  </div>
                  <h3 className="text-lg font-bold text-center text-slate-900 dark:text-white">
                    User Created &amp; Invitation Ready
                  </h3>
                  <p className="text-xs text-slate-600 dark:text-slate-300 text-center">
                    {createdInvitation.message}
                  </p>

                  <div className="p-3 bg-slate-50 dark:bg-slate-800/60 rounded-xl border border-slate-200 dark:border-slate-700 space-y-2">
                    <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider block">
                      Secure Activation Link (Valid 48 hours):
                    </span>
                    <input
                      readOnly
                      value={createdInvitation.invitation_url}
                      className="w-full text-xs font-mono bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg p-2 text-slate-800 dark:text-slate-200"
                    />
                    <button
                      type="button"
                      onClick={() => {
                        navigator.clipboard.writeText(createdInvitation.invitation_url)
                        setCopiedLink(true)
                        setTimeout(() => setCopiedLink(false), 2000)
                      }}
                      className="w-full py-2 bg-slate-800 hover:bg-slate-900 text-white text-xs font-semibold rounded-lg transition-colors flex items-center justify-center gap-1.5"
                    >
                      {copiedLink ? '✓ Copied to Clipboard!' : '📋 Copy Invitation Link'}
                    </button>
                  </div>

                  <div className="flex justify-end pt-2">
                    <button
                      type="button"
                      onClick={() => {
                        setShowCreateModal(false)
                        setCreatedInvitation(null)
                      }}
                      className="px-4 py-2 bg-blue-600 text-white rounded-xl text-xs font-semibold hover:bg-blue-700"
                    >
                      Done
                    </button>
                  </div>
                </div>
              ) : (
                <form onSubmit={handleCreateUser} className="space-y-4">
                  <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-3">
                    <h3 className="text-base font-bold text-slate-900 dark:text-white">
                      Create &amp; Invite New User
                    </h3>
                    <button
                      type="button"
                      onClick={() => setShowCreateModal(false)}
                      className="text-slate-400 hover:text-slate-600"
                    >
                      ✕
                    </button>
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                      Full Name *
                    </label>
                    <input
                      required
                      type="text"
                      value={createForm.full_name}
                      onChange={(e) => setCreateForm({ ...createForm, full_name: e.target.value })}
                      placeholder="e.g. Rohan Sharma"
                      className="w-full text-xs bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-2 text-slate-900 dark:text-white"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                      Email Address *
                    </label>
                    <input
                      required
                      type="email"
                      value={createForm.email}
                      onChange={(e) => setCreateForm({ ...createForm, email: e.target.value })}
                      placeholder="name@company.com"
                      className="w-full text-xs bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-2 text-slate-900 dark:text-white"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                      Role *
                    </label>
                    <select
                      value={createForm.role}
                      onChange={(e) => {
                        const newRole = e.target.value
                        const perms =
                          newRole === 'administrator'
                            ? PERMISSION_OPTIONS.map((p) => p.id)
                            : ['platform:access', 'statements:upload', 'reports:export', 'analytics:view']
                        setCreateForm({ ...createForm, role: newRole, permissions: perms })
                      }}
                      className="w-full text-xs bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-2 text-slate-900 dark:text-white"
                    >
                      <option value="standard_user">Standard User (Access according to permissions)</option>
                      <option value="administrator">Administrator (Full Control & User Management)</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                      Permissions
                    </label>
                    <div className="space-y-1.5 max-h-40 overflow-y-auto p-2 bg-slate-50 dark:bg-slate-800/40 rounded-lg border border-slate-200 dark:border-slate-700">
                      {PERMISSION_OPTIONS.map((p) => {
                        const checked = createForm.permissions.includes(p.id)
                        return (
                          <label key={p.id} className="flex items-start gap-2 text-xs text-slate-700 dark:text-slate-300 cursor-pointer">
                            <input
                              type="checkbox"
                              checked={checked}
                              onChange={(e) => {
                                const newPerms = e.target.checked
                                  ? [...createForm.permissions, p.id]
                                  : createForm.permissions.filter((x) => x !== p.id)
                                setCreateForm({ ...createForm, permissions: newPerms })
                              }}
                              className="mt-0.5 rounded text-blue-600"
                            />
                            <div>
                              <strong className="block text-[11px]">{p.label}</strong>
                              <small className="text-[10px] text-slate-400 block">{p.desc}</small>
                            </div>
                          </label>
                        )
                      })}
                    </div>
                  </div>

                  <div className="p-3 bg-blue-50/70 dark:bg-blue-950/40 rounded-xl border border-blue-200 dark:border-blue-900 text-[11px] text-blue-800 dark:text-blue-300">
                    ℹ️ A single-use, 48-hour secure activation link will be automatically generated. The invited user will choose their own password upon activation.
                  </div>

                  <div className="flex items-center justify-end gap-2.5 pt-2">
                    <button
                      type="button"
                      onClick={() => setShowCreateModal(false)}
                      className="px-3.5 py-2 text-xs font-semibold rounded-xl border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300 hover:bg-slate-100"
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      disabled={createSubmitting}
                      className="px-4 py-2 text-xs font-semibold rounded-xl bg-blue-600 hover:bg-blue-700 text-white disabled:opacity-60"
                    >
                      {createSubmitting ? 'Generating…' : 'Generate & Send Invitation'}
                    </button>
                  </div>
                </form>
              )}
            </div>
          </div>
        )}

        {/* Edit User Sub-Modal */}
        {showEditModal && editingUser && (
          <div className="fixed inset-0 z-60 flex items-center justify-center bg-slate-950/60 backdrop-blur-xs p-4">
            <form onSubmit={handleUpdateUser} className="bg-white dark:bg-slate-900 rounded-2xl p-6 max-w-lg w-full border border-slate-200 dark:border-slate-800 shadow-2xl space-y-4">
              <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-3">
                <h3 className="text-base font-bold text-slate-900 dark:text-white">
                  Edit User: {editingUser.email}
                </h3>
                <button
                  type="button"
                  onClick={() => setShowEditModal(false)}
                  className="text-slate-400 hover:text-slate-600"
                >
                  ✕
                </button>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  Full Name
                </label>
                <input
                  type="text"
                  value={editingUser.full_name || ''}
                  onChange={(e) => setEditingUser({ ...editingUser, full_name: e.target.value })}
                  className="w-full text-xs bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-2 text-slate-900 dark:text-white"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  Role
                </label>
                <select
                  value={editingUser.role}
                  onChange={(e) => setEditingUser({ ...editingUser, role: e.target.value })}
                  className="w-full text-xs bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-2 text-slate-900 dark:text-white"
                >
                  <option value="standard_user">Standard User</option>
                  <option value="administrator">Administrator</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  Account Status
                </label>
                <select
                  value={editingUser.status}
                  onChange={(e) => setEditingUser({ ...editingUser, status: e.target.value })}
                  className="w-full text-xs bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-2 text-slate-900 dark:text-white"
                >
                  <option value="active">Active</option>
                  <option value="suspended">Suspended (Revokes sessions immediately)</option>
                  <option value="pending_activation">Pending Activation</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                  Permissions
                </label>
                <div className="space-y-1.5 max-h-40 overflow-y-auto p-2 bg-slate-50 dark:bg-slate-800/40 rounded-lg border border-slate-200 dark:border-slate-700">
                  {PERMISSION_OPTIONS.map((p) => {
                    const checked = (editingUser.permissions || []).includes(p.id)
                    return (
                      <label key={p.id} className="flex items-start gap-2 text-xs text-slate-700 dark:text-slate-300 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={checked}
                          onChange={(e) => {
                            const current = editingUser.permissions || []
                            const newPerms = e.target.checked
                              ? [...current, p.id]
                              : current.filter((x) => x !== p.id)
                            setEditingUser({ ...editingUser, permissions: newPerms })
                          }}
                          className="mt-0.5 rounded text-blue-600"
                        />
                        <div>
                          <strong className="block text-[11px]">{p.label}</strong>
                          <small className="text-[10px] text-slate-400 block">{p.desc}</small>
                        </div>
                      </label>
                    )
                  })}
                </div>
              </div>

              <div className="flex items-center justify-end gap-2.5 pt-2">
                <button
                  type="button"
                  onClick={() => setShowEditModal(false)}
                  className="px-3.5 py-2 text-xs font-semibold rounded-xl border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300 hover:bg-slate-100"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 text-xs font-semibold rounded-xl bg-blue-600 hover:bg-blue-700 text-white"
                >
                  Save Changes
                </button>
              </div>
            </form>
          </div>
        )}

        {/* Delete Confirmation Modal */}
        {showDeleteConfirm && (
          <div className="fixed inset-0 z-60 flex items-center justify-center bg-slate-950/60 backdrop-blur-xs p-4">
            <div className="bg-white dark:bg-slate-900 rounded-2xl p-6 max-w-sm w-full border border-slate-200 dark:border-slate-800 shadow-2xl space-y-4">
              <div className="w-12 h-12 rounded-full bg-red-100 text-red-600 flex items-center justify-center text-xl mx-auto">
                ⚠️
              </div>
              <h3 className="text-base font-bold text-center text-slate-900 dark:text-white">
                Delete User Account?
              </h3>
              <p className="text-xs text-slate-500 text-center">
                Are you sure you want to permanently delete <strong>{showDeleteConfirm.email}</strong>? All active sessions will be terminated. This action cannot be undone.
              </p>
              <div className="flex items-center justify-center gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowDeleteConfirm(null)}
                  className="px-4 py-2 text-xs font-semibold rounded-xl border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={() => handleDeleteUser(showDeleteConfirm)}
                  className="px-4 py-2 text-xs font-semibold rounded-xl bg-red-600 hover:bg-red-700 text-white"
                >
                  Confirm Delete
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

