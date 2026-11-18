import React, { useContext, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { AuthContext } from '../context/AuthContext'
import ThreeVisualizer from '../components/ThreeVisualizer'
import './Landing.css'

export default function Landing() {
  const navigate = useNavigate()
  const { auth, user, logout } = useContext(AuthContext) || {}
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const [activeModal, setActiveModal] = useState(null) // 'privacy' | 'support' | 'security' | null

  const isAuthenticated = auth === 'signed-in'

  return (
    <div className="landing-root bg-slate-950 text-slate-100 min-h-screen flex flex-col selection:bg-blue-600 selection:text-white">
      {/* Background Ambient Glows */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden z-0">
        <div className="ambient-blob ambient-blob-1" />
        <div className="ambient-blob ambient-blob-2" />
        <div className="ambient-blob ambient-blob-3" />
        <div className="ambient-grid-overlay" />
      </div>

      {/* Top Navigation Bar */}
      <header className="sticky top-0 z-50 backdrop-blur-xl bg-slate-950/80 border-b border-slate-800/80 transition-all">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-20 flex items-center justify-between gap-4">
          {/* Brand Logo & Name */}
          <Link to="/" className="flex items-center gap-3.5 group focus:outline-hidden" title="SEPL AI Data Analysis Platform">
            <div className="w-11 h-11 rounded-xl bg-gradient-to-tr from-blue-700 via-blue-600 to-cyan-400 p-0.5 shadow-lg shadow-blue-500/20 group-hover:scale-105 transition-transform shrink-0">
              <div className="w-full h-full rounded-[10px] bg-slate-950 flex items-center justify-center overflow-hidden p-1">
                <img
                  src="/sepl_logo.png"
                  alt="SEPL"
                  className="w-full h-full object-contain"
                  onError={(e) => {
                    e.currentTarget.style.display = 'none'
                    e.currentTarget.parentElement.innerHTML = '<span class="text-blue-400 font-black text-xl">S</span>'
                  }}
                />
              </div>
            </div>
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <span className="text-lg font-black tracking-tight text-white group-hover:text-cyan-400 transition-colors">
                  SEPL
                </span>
                <span className="hidden sm:inline-block px-2 py-0.5 text-[10px] font-bold tracking-wider uppercase bg-blue-500/10 text-cyan-400 border border-blue-500/20 rounded-full">
                  Enterprise 2.0
                </span>
              </div>
              <span className="text-xs font-semibold text-slate-400 tracking-wide block truncate">
                AI DATA ANALYSIS PLATFORM
              </span>
            </div>
          </Link>

          {/* Desktop Navigation Links */}
          <nav className="hidden md:flex items-center gap-8 text-sm font-medium text-slate-300">
            <a href="#features" className="hover:text-cyan-400 transition-colors">Features</a>
            <a href="#intelligence" className="hover:text-cyan-400 transition-colors">Statement Intelligence</a>
            <a href="#classification" className="hover:text-cyan-400 transition-colors">Classification</a>
            <a href="#deliverables" className="hover:text-cyan-400 transition-colors">Reporting</a>
            <a href="#security" className="hover:text-cyan-400 transition-colors">Security</a>
          </nav>

          {/* Action Area */}
          <div className="hidden sm:flex items-center gap-4">
            {isAuthenticated ? (
              <div className="flex items-center gap-3">
                <div className="text-right hidden lg:block">
                  <div className="text-xs font-bold text-slate-200 truncate max-w-[140px]">
                    {user?.full_name || user?.email || 'Authenticated'}
                  </div>
                  <div className="text-[10px] text-emerald-400 font-semibold uppercase">
                    Active Session
                  </div>
                </div>
                <button
                  onClick={() => navigate('/dashboard')}
                  className="px-5 py-2.5 rounded-xl bg-gradient-to-r from-blue-600 to-cyan-500 text-white font-bold text-sm shadow-lg shadow-blue-500/25 hover:shadow-cyan-500/30 hover:scale-[1.02] active:scale-[0.98] transition-all cursor-pointer"
                >
                  Go to Dashboard →
                </button>
                <button
                  onClick={logout}
                  className="px-3.5 py-2 rounded-xl text-slate-400 hover:text-white hover:bg-slate-800 text-xs font-semibold transition-colors cursor-pointer"
                  title="Sign out of your session"
                >
                  Sign Out
                </button>
              </div>
            ) : (
              <div className="flex items-center gap-3">
                <Link
                  to="/login"
                  className="px-4 py-2.5 rounded-xl text-slate-300 hover:text-white hover:bg-slate-800/80 text-sm font-semibold transition-colors"
                >
                  Sign In
                </Link>
                <Link
                  to="/login"
                  className="px-5 py-2.5 rounded-xl bg-gradient-to-r from-blue-600 via-blue-500 to-cyan-500 text-white font-bold text-sm shadow-lg shadow-blue-600/30 hover:shadow-cyan-500/40 hover:scale-[1.02] active:scale-[0.98] transition-all"
                >
                  Get Started
                </Link>
              </div>
            )}
          </div>

          {/* Mobile Menu Toggle */}
          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="md:hidden p-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800"
            aria-label="Toggle navigation menu"
          >
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              {mobileMenuOpen ? (
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
              ) : (
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 6h16M4 12h16M4 18h16" />
              )}
            </svg>
          </button>
        </div>

        {/* Mobile Dropdown Menu */}
        {mobileMenuOpen && (
          <div className="md:hidden border-b border-slate-800 bg-slate-950/95 backdrop-blur-2xl px-6 py-5 space-y-4">
            <div className="flex flex-col space-y-3 text-sm font-medium text-slate-300">
              <a href="#features" onClick={() => setMobileMenuOpen(false)} className="hover:text-cyan-400 py-1">Features</a>
              <a href="#intelligence" onClick={() => setMobileMenuOpen(false)} className="hover:text-cyan-400 py-1">Statement Intelligence</a>
              <a href="#classification" onClick={() => setMobileMenuOpen(false)} className="hover:text-cyan-400 py-1">Classification</a>
              <a href="#deliverables" onClick={() => setMobileMenuOpen(false)} className="hover:text-cyan-400 py-1">Reporting</a>
              <a href="#security" onClick={() => setMobileMenuOpen(false)} className="hover:text-cyan-400 py-1">Security</a>
            </div>
            <div className="pt-4 border-t border-slate-800 flex flex-col gap-2.5">
              {isAuthenticated ? (
                <>
                  <button
                    onClick={() => { setMobileMenuOpen(false); navigate('/dashboard') }}
                    className="w-full py-3 rounded-xl bg-blue-600 text-white font-bold text-center shadow-md text-sm"
                  >
                    Open Analysis Dashboard
                  </button>
                  <button
                    onClick={() => { setMobileMenuOpen(false); logout() }}
                    className="w-full py-2.5 rounded-xl text-slate-400 hover:bg-slate-800 text-center text-xs font-semibold"
                  >
                    Sign Out
                  </button>
                </>
              ) : (
                <>
                  <Link
                    to="/login"
                    onClick={() => setMobileMenuOpen(false)}
                    className="w-full py-3 rounded-xl bg-blue-600 text-white font-bold text-center shadow-md text-sm"
                  >
                    Get Started / Sign In
                  </Link>
                </>
              )}
            </div>
          </div>
        )}
      </header>

      {/* Main Content Area */}
      <main className="relative z-10 flex-1">
        {/* HERO SECTION */}
        <section className="relative pt-12 sm:pt-16 lg:pt-20 pb-20 overflow-hidden">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="text-center max-w-3xl mx-auto mb-10 sm:mb-12">
              {/* Badge */}
              <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-blue-900/30 border border-blue-500/30 text-cyan-300 text-xs font-bold tracking-wide mb-6 backdrop-blur-md">
                <span className="w-2 h-2 rounded-full bg-cyan-400 animate-ping" />
                <span>Next-Generation Financial Intelligence</span>
              </div>

              {/* Main Headline */}
              <h1 className="text-4xl sm:text-5xl lg:text-6xl font-black tracking-tight text-white leading-[1.12] mb-6">
                Smarter Analytics.{' '}
                <span className="bg-gradient-to-r from-blue-400 via-cyan-300 to-indigo-300 bg-clip-text text-transparent">
                  Stronger Decisions.
                </span>
              </h1>

              {/* Supporting Text */}
              <p className="text-lg sm:text-xl text-slate-300 leading-relaxed max-w-2xl mx-auto mb-8 font-normal">
                Transform your financial data into powerful insights with AI. Reconcile complex multi-bank statements with zero-delta mathematical proof and executive-ready reporting.
              </p>

              {/* Primary Action Buttons */}
              <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
                <Link
                  to={isAuthenticated ? '/dashboard' : '/login'}
                  className="w-full sm:w-auto px-8 py-4 rounded-xl bg-gradient-to-r from-blue-600 via-blue-500 to-cyan-500 hover:from-blue-500 hover:to-cyan-400 text-white font-bold text-base shadow-xl shadow-blue-600/30 hover:shadow-cyan-500/40 hover:-translate-y-0.5 active:translate-y-0 transition-all flex items-center justify-center gap-2 group cursor-pointer"
                >
                  <span>{isAuthenticated ? 'Open Analysis Dashboard' : 'Get Started Now'}</span>
                  <svg className="w-5 h-5 group-hover:translate-x-1 transition-transform" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M14 5l7 7m0 0l-7 7m7-7H3" />
                  </svg>
                </Link>

                <Link
                  to="/login"
                  className="w-full sm:w-auto px-7 py-4 rounded-xl bg-slate-900/80 hover:bg-slate-800/90 text-slate-200 hover:text-white border border-slate-700/80 hover:border-slate-600 font-semibold text-base backdrop-blur-md transition-all flex items-center justify-center gap-2"
                >
                  <svg className="w-5 h-5 text-cyan-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                  </svg>
                  <span>Secure Workspace Sign In</span>
                </Link>
              </div>

              {/* Verified Ledger Proof Metrics */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-12 pt-8 border-t border-slate-800/80 text-left">
                <div className="p-3.5 rounded-xl bg-slate-900/60 border border-slate-800">
                  <div className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Total Inflow Verified</div>
                  <div className="text-lg sm:text-xl font-black text-emerald-400 mt-1">₹45,48,780</div>
                  <div className="text-[11px] text-slate-500 font-medium">Synthetic Benchmark Ledger</div>
                </div>
                <div className="p-3.5 rounded-xl bg-slate-900/60 border border-slate-800">
                  <div className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Total Outflow Classified</div>
                  <div className="text-lg sm:text-xl font-black text-rose-400 mt-1">₹46,26,410</div>
                  <div className="text-[11px] text-slate-500 font-medium">99.98% Accuracy</div>
                </div>
                <div className="p-3.5 rounded-xl bg-slate-900/60 border border-slate-800">
                  <div className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Variance Guarantee</div>
                  <div className="text-lg sm:text-xl font-black text-cyan-400 mt-1">Δ = ₹0.00</div>
                  <div className="text-[11px] text-slate-500 font-medium">Zero-Delta Reconciled</div>
                </div>
                <div className="p-3.5 rounded-xl bg-slate-900/60 border border-slate-800">
                  <div className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Audit Deliverables</div>
                  <div className="text-lg sm:text-xl font-black text-blue-400 mt-1">5 Formats</div>
                  <div className="text-[11px] text-slate-500 font-medium">PDF, XLSX, CSV, HTML, ZIP</div>
                </div>
              </div>
            </div>

            {/* 3D ANIMATION VISUALIZATION CONTAINER */}
            <div className="relative mt-4 sm:mt-8 max-w-5xl mx-auto rounded-3xl p-1 bg-gradient-to-b from-blue-500/20 via-slate-800/40 to-cyan-500/10 shadow-2xl shadow-blue-950/80">
              <div className="w-full rounded-[22px] bg-slate-950/90 backdrop-blur-2xl overflow-hidden border border-slate-800/90 relative">
                <ThreeVisualizer />

                {/* Overlay Hint Pill */}
                <div className="absolute top-4 right-4 pointer-events-none hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-full bg-slate-900/70 border border-slate-700/60 text-[11px] text-slate-400 backdrop-blur-md">
                  <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse" />
                  <span>Interactive 3D Stage • Move mouse to tilt</span>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* SECTION 1: AI-POWERED FINANCIAL ANALYSIS */}
        <section id="features" className="py-20 border-t border-slate-800/80 bg-slate-950/60 relative">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="max-w-2xl mb-14">
              <span className="text-cyan-400 text-xs font-bold uppercase tracking-widest block mb-2">Core Capability 01</span>
              <h2 className="text-3xl sm:text-4xl font-extrabold text-white tracking-tight">
                AI-Powered Financial Analysis
              </h2>
              <p className="mt-4 text-base sm:text-lg text-slate-300 leading-relaxed">
                Autonomous ledger intelligence that uncovers patterns, flags anomalies, and proves mathematical precision in seconds.
              </p>
            </div>

            <div className="grid md:grid-cols-3 gap-8">
              <div className="feature-card p-8 rounded-2xl bg-slate-900/60 border border-slate-800 hover:border-blue-500/50 transition-all">
                <div className="w-12 h-12 rounded-xl bg-blue-500/10 text-cyan-400 flex items-center justify-center text-2xl mb-6 border border-blue-500/20">
                  ⚡
                </div>
                <h3 className="text-xl font-bold text-white mb-3">Multi-Model Reconciliation</h3>
                <p className="text-slate-400 text-sm leading-relaxed">
                  Dual validation architecture combining algorithmic arithmetic audits with deep LLM intelligence for zero-variance ledger proofs.
                </p>
              </div>

              <div className="feature-card p-8 rounded-2xl bg-slate-900/60 border border-slate-800 hover:border-blue-500/50 transition-all">
                <div className="w-12 h-12 rounded-xl bg-emerald-500/10 text-emerald-400 flex items-center justify-center text-2xl mb-6 border border-emerald-500/20">
                  🛡️
                </div>
                <h3 className="text-xl font-bold text-white mb-3">Predictive Anomaly Detection</h3>
                <p className="text-slate-400 text-sm leading-relaxed">
                  Real-time pattern scanning identifies unusual duplicate debits, weekend transactions, missing reference IDs, and outlier spikes.
                </p>
              </div>

              <div className="feature-card p-8 rounded-2xl bg-slate-900/60 border border-slate-800 hover:border-blue-500/50 transition-all">
                <div className="w-12 h-12 rounded-xl bg-indigo-500/10 text-indigo-400 flex items-center justify-center text-2xl mb-6 border border-indigo-500/20">
                  📈
                </div>
                <h3 className="text-xl font-bold text-white mb-3">Cash-Flow Trajectory</h3>
                <p className="text-slate-400 text-sm leading-relaxed">
                  Continuous day-by-day running balance calculation and cash runway projections based on historical inflow/outflow seasonality.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* SECTION 2: BANK STATEMENT INTELLIGENCE */}
        <section id="intelligence" className="py-20 border-t border-slate-800/80 bg-slate-900/20 relative">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="grid lg:grid-cols-2 gap-12 items-center">
              <div>
                <span className="text-cyan-400 text-xs font-bold uppercase tracking-widest block mb-2">Core Capability 02</span>
                <h2 className="text-3xl sm:text-4xl font-extrabold text-white tracking-tight mb-6">
                  Bank Statement Intelligence
                </h2>
                <p className="text-slate-300 text-base sm:text-lg leading-relaxed mb-6">
                  Universal document ingestion tailored for institutional formats. Upload statements in PDF, Excel (XLSX), CSV, or raw JSON formats with zero configuration.
                </p>
                <div className="space-y-4 text-sm text-slate-300">
                  <div className="flex items-start gap-3">
                    <span className="text-emerald-400 font-bold text-lg leading-none">✓</span>
                    <span><strong>Auto-Format Detection:</strong> Automatically parses Axis Bank, HDFC, SBI, ICICI, Kotak, and international banking schemas.</span>
                  </div>
                  <div className="flex items-start gap-3">
                    <span className="text-emerald-400 font-bold text-lg leading-none">✓</span>
                    <span><strong>Multi-Page PDF Parsing:</strong> High-fidelity table extraction that seamlessly stitches transactions across complex multi-page statements.</span>
                  </div>
                  <div className="flex items-start gap-3">
                    <span className="text-emerald-400 font-bold text-lg leading-none">✓</span>
                    <span><strong>Mathematical Ledger Audit:</strong> Verifies opening balance, all credits and debits, and proves exact match against closing balance.</span>
                  </div>
                </div>
              </div>

              <div className="p-6 rounded-2xl bg-slate-900/80 border border-slate-800 shadow-xl">
                <div className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-4 pb-3 border-b border-slate-800 flex justify-between items-center">
                  <span>Supported Document Formats</span>
                  <span className="text-cyan-400">Institutional Tier</span>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800/80">
                    <div className="text-rose-400 font-bold text-base mb-1">PDF Statements</div>
                    <p className="text-xs text-slate-400">Native digital & tabular bank exports with multi-page parsing.</p>
                  </div>
                  <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800/80">
                    <div className="text-emerald-400 font-bold text-base mb-1">Excel (XLSX)</div>
                    <p className="text-xs text-slate-400">Multi-sheet accounting workbooks with formula reconciliation.</p>
                  </div>
                  <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800/80">
                    <div className="text-blue-400 font-bold text-base mb-1">CSV Ledgers</div>
                    <p className="text-xs text-slate-400">Delimited raw bank transaction feeds with smart delimiter detection.</p>
                  </div>
                  <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800/80">
                    <div className="text-purple-400 font-bold text-base mb-1">Universal Datasets</div>
                    <p className="text-xs text-slate-400">Generalized financial datasets with automatic column remapping.</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* SECTION 3: TRANSACTION CLASSIFICATION */}
        <section id="classification" className="py-20 border-t border-slate-800/80 bg-slate-950/60 relative">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="max-w-2xl mb-14">
              <span className="text-cyan-400 text-xs font-bold uppercase tracking-widest block mb-2">Core Capability 03</span>
              <h2 className="text-3xl sm:text-4xl font-extrabold text-white tracking-tight">
                Transaction Classification
              </h2>
              <p className="mt-4 text-base sm:text-lg text-slate-300 leading-relaxed">
                Transform messy raw bank narration strings into clean, audited accounting categories with deep merchant identification.
              </p>
            </div>

            <div className="grid md:grid-cols-3 gap-8">
              <div className="p-8 rounded-2xl bg-slate-900/60 border border-slate-800">
                <div className="text-blue-400 text-2xl mb-4">🏷️</div>
                <h3 className="text-xl font-bold text-white mb-2">Vendor Normalization</h3>
                <p className="text-slate-400 text-sm leading-relaxed">
                  Cleans up obfuscated UPI, NEFT, and RTGS narrations into recognizable corporate vendor profiles and counterparties.
                </p>
              </div>

              <div className="p-8 rounded-2xl bg-slate-900/60 border border-slate-800">
                <div className="text-cyan-400 text-2xl mb-4">🔄</div>
                <h3 className="text-xl font-bold text-white mb-2">Recurring Expense Tracking</h3>
                <p className="text-slate-400 text-sm leading-relaxed">
                  Identifies regular operational overheads, subscription debits, utility bills, and salary disbursements automatically.
                </p>
              </div>

              <div className="p-8 rounded-2xl bg-slate-900/60 border border-slate-800">
                <div className="text-emerald-400 text-2xl mb-4">⚖️</div>
                <h3 className="text-xl font-bold text-white mb-2">Tax & Compliance Mapping</h3>
                <p className="text-slate-400 text-sm leading-relaxed">
                  Separates GST, TDS, duty charges, and corporate tax payments from standard operating expenditures.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* SECTION 4: FINANCIAL INSIGHTS AND REPORTING */}
        <section id="deliverables" className="py-20 border-t border-slate-800/80 bg-slate-900/20 relative">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="text-center max-w-3xl mx-auto mb-16">
              <span className="text-cyan-400 text-xs font-bold uppercase tracking-widest block mb-2">Core Capability 04</span>
              <h2 className="text-3xl sm:text-4xl font-extrabold text-white tracking-tight mb-4">
                Financial Insights & 5 Deliverables Hub
              </h2>
              <p className="text-slate-300 text-base sm:text-lg">
                Every analysis run immediately generates a complete, multi-format institutional audit package ready for board presentations or CFO sign-off.
              </p>
            </div>

            <div className="grid sm:grid-cols-2 lg:grid-cols-5 gap-4">
              <div className="p-6 rounded-2xl bg-slate-900/80 border border-slate-800 text-center hover:scale-[1.02] transition-transform">
                <div className="text-3xl mb-3">📄</div>
                <h4 className="text-base font-bold text-white mb-1">Executive PDF</h4>
                <p className="text-xs text-slate-400">Formal audit report with executive charts, summary KPIs, and reconciliation tables.</p>
              </div>

              <div className="p-6 rounded-2xl bg-slate-900/80 border border-slate-800 text-center hover:scale-[1.02] transition-transform">
                <div className="text-3xl mb-3">📊</div>
                <h4 className="text-base font-bold text-white mb-1">Excel (XLSX)</h4>
                <p className="text-xs text-slate-400">Formatted workbook featuring categorized tabs, pivot structures, and formulas.</p>
              </div>

              <div className="p-6 rounded-2xl bg-slate-900/80 border border-slate-800 text-center hover:scale-[1.02] transition-transform">
                <div className="text-3xl mb-3">📑</div>
                <h4 className="text-base font-bold text-white mb-1">CSV Ledger</h4>
                <p className="text-xs text-slate-400">Clean standardized raw ledger rows ready for ERP and database ingest.</p>
              </div>

              <div className="p-6 rounded-2xl bg-slate-900/80 border border-slate-800 text-center hover:scale-[1.02] transition-transform">
                <div className="text-3xl mb-3">🌐</div>
                <h4 className="text-base font-bold text-white mb-1">HTML Dashboard</h4>
                <p className="text-xs text-slate-400">Self-contained offline interactive visualization dashboard with filtering.</p>
              </div>

              <div className="p-6 rounded-2xl bg-slate-900/80 border border-slate-800 text-center hover:scale-[1.02] transition-transform">
                <div className="text-3xl mb-3">📦</div>
                <h4 className="text-base font-bold text-white mb-1">ZIP Package</h4>
                <p className="text-xs text-slate-400">Bundled archive containing all four deliverable formats plus audit metadata.</p>
              </div>
            </div>
          </div>
        </section>

        {/* SECTION 5: ENTERPRISE-GRADE DATA SECURITY */}
        <section id="security" className="py-20 border-t border-slate-800/80 bg-slate-950/60 relative">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="max-w-2xl mb-14">
              <span className="text-cyan-400 text-xs font-bold uppercase tracking-widest block mb-2">Core Capability 05</span>
              <h2 className="text-3xl sm:text-4xl font-extrabold text-white tracking-tight">
                Enterprise-Grade Data Security
              </h2>
              <p className="mt-4 text-base sm:text-lg text-slate-300 leading-relaxed">
                Engineered with strict zero-trust defenses to guarantee institutional data privacy, role-based isolation, and compliance.
              </p>
            </div>

            <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
              <div className="p-6 rounded-2xl bg-slate-900/60 border border-slate-800">
                <div className="w-10 h-10 rounded-lg bg-blue-500/10 text-cyan-400 flex items-center justify-center text-xl mb-4 border border-blue-500/20">
                  🔒
                </div>
                <h4 className="text-base font-bold text-white mb-2">256-Bit TLS & Scrypt</h4>
                <p className="text-xs text-slate-400 leading-relaxed">
                  End-to-end encrypted transport with high-cost Scrypt key derivation for all user credential storage.
                </p>
              </div>

              <div className="p-6 rounded-2xl bg-slate-900/60 border border-slate-800">
                <div className="w-10 h-10 rounded-lg bg-emerald-500/10 text-emerald-400 flex items-center justify-center text-xl mb-4 border border-emerald-500/20">
                  🛡️
                </div>
                <h4 className="text-base font-bold text-white mb-2">Signed HttpOnly Cookies</h4>
                <p className="text-xs text-slate-400 leading-relaxed">
                  Strictly scoped sessions with SameSite protection and cryptographically armed anti-CSRF token defense.
                </p>
              </div>

              <div className="p-6 rounded-2xl bg-slate-900/60 border border-slate-800">
                <div className="w-10 h-10 rounded-lg bg-purple-500/10 text-purple-400 flex items-center justify-center text-xl mb-4 border border-purple-500/20">
                  🚫
                </div>
                <h4 className="text-base font-bold text-white mb-2">Zero AI Data Retention</h4>
                <p className="text-xs text-slate-400 leading-relaxed">
                  Customer financial records are never retained or utilized for public model training or external telemetry.
                </p>
              </div>

              <div className="p-6 rounded-2xl bg-slate-900/60 border border-slate-800">
                <div className="w-10 h-10 rounded-lg bg-cyan-500/10 text-cyan-400 flex items-center justify-center text-xl mb-4 border border-cyan-500/20">
                  📋
                </div>
                <h4 className="text-base font-bold text-white mb-2">Immutable Audit Trails</h4>
                <p className="text-xs text-slate-400 leading-relaxed">
                  SHA-256 fingerprint verified audit trails in MongoDB Atlas tracking all admin and user activity.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* BOTTOM CTA BANNER */}
        <section className="py-20 border-t border-slate-800/80 bg-gradient-to-b from-slate-950 to-blue-950/40 relative">
          <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
            <h2 className="text-3xl sm:text-4xl font-extrabold text-white tracking-tight mb-4">
              Ready to Upgrade Your Financial Intelligence?
            </h2>
            <p className="text-slate-300 text-base sm:text-lg max-w-2xl mx-auto mb-8">
              Access the SEPL workspace to begin instant reconciliation, anomaly scanning, and audited financial report generation.
            </p>
            <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
              <Link
                to={isAuthenticated ? '/dashboard' : '/login'}
                className="w-full sm:w-auto px-8 py-4 rounded-xl bg-gradient-to-r from-blue-600 to-cyan-500 hover:from-blue-500 hover:to-cyan-400 text-white font-bold text-base shadow-xl shadow-blue-500/30 hover:shadow-cyan-500/40 transition-all cursor-pointer"
              >
                {isAuthenticated ? 'Go to Analysis Dashboard →' : 'Sign In to SEPL Workspace →'}
              </Link>
            </div>
          </div>
        </section>
      </main>

      {/* FOOTER */}
      <footer className="border-t border-slate-800 bg-slate-950 text-slate-400 text-xs py-12 relative z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col md:flex-row items-center justify-between gap-6">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center text-white font-black text-sm">
              S
            </div>
            <div>
              <div className="font-bold text-white text-sm">SEPL AI DATA ANALYSIS PLATFORM</div>
              <div className="text-[11px] text-slate-400">Smart Solutions Pvt Ltd • Financial Intelligence Division</div>
            </div>
          </div>

          <div className="flex flex-wrap items-center justify-center gap-6 text-xs text-slate-400">
            <button
              onClick={() => setActiveModal('privacy')}
              className="hover:text-cyan-400 transition-colors cursor-pointer"
            >
              Privacy Policy
            </button>
            <button
              onClick={() => setActiveModal('support')}
              className="hover:text-cyan-400 transition-colors cursor-pointer"
            >
              Enterprise Support
            </button>
            <button
              onClick={() => setActiveModal('security')}
              className="hover:text-cyan-400 transition-colors cursor-pointer"
            >
              Security Architecture
            </button>
            <Link to="/login" className="hover:text-cyan-400 transition-colors">
              Workspace Login
            </Link>
          </div>

          <div className="text-slate-400 text-center md:text-right text-[11px]">
            © {new Date().getFullYear()} SEPL. All rights reserved.
          </div>
        </div>
      </footer>

      {/* INTERACTIVE MODALS */}
      {activeModal && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-md p-4"
          role="dialog"
          aria-modal="true"
          onClick={() => setActiveModal(null)}
        >
          <div
            className="w-full max-w-lg rounded-2xl bg-slate-900 border border-slate-800 p-6 shadow-2xl relative text-left"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between pb-4 border-b border-slate-800 mb-4">
              <h3 className="text-lg font-bold text-white">
                {activeModal === 'privacy' && 'SEPL Enterprise Data Privacy'}
                {activeModal === 'support' && 'Enterprise Technical Support'}
                {activeModal === 'security' && 'Zero-Trust Security Architecture'}
              </h3>
              <button
                onClick={() => setActiveModal(null)}
                className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800"
                aria-label="Close modal"
              >
                ✕
              </button>
            </div>

            <div className="text-sm text-slate-300 space-y-3 leading-relaxed">
              {activeModal === 'privacy' && (
                <>
                  <p>
                    SEPL operates on a strict <strong>Zero Data Retention</strong> policy. Bank statement documents and extracted financial transaction rows are held exclusively in volatile memory during the active analysis session.
                  </p>
                  <p>
                    Customer financial data is never stored on persistent storage outside the explicitly authorized MongoDB Atlas session stores, nor is it ever utilized for foundational model retraining.
                  </p>
                </>
              )}

              {activeModal === 'support' && (
                <>
                  <p>
                    Enterprise customers have access to 24/7 priority support with a dedicated SLA.
                  </p>
                  <div className="p-3 rounded-lg bg-slate-950 border border-slate-800 space-y-1 text-xs">
                    <div><strong>Priority Desk:</strong> support@sepl.local</div>
                    <div><strong>Emergency SLA:</strong> Under 15 minutes response time</div>
                    <div><strong>Dedicated Account Lead:</strong> Enterprise Success Team</div>
                  </div>
                </>
              )}

              {activeModal === 'security' && (
                <>
                  <p>
                    All transmissions are secured with 256-Bit Transport Layer Security (TLS 1.3). Credentials are encrypted with Scrypt key derivation, and sessions utilize cryptographically signed HttpOnly cookies with CSRF defense.
                  </p>
                </>
              )}
            </div>

            <div className="mt-6 pt-4 border-t border-slate-800 flex justify-end">
              <button
                onClick={() => setActiveModal(null)}
                className="px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-semibold text-xs"
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
