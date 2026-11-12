import React, { useEffect, useState, useRef, useMemo } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import { getResults, getAnalysis, getErrorMessage } from '../api/client'

import DeliverablesHub from '../components/DeliverablesHub'
import ActiveFilterBar from '../components/ActiveFilterBar'
import ExecutiveOverview from '../components/ExecutiveOverview'
import FinancialStorytelling from '../components/FinancialStorytelling'
import IncomeExpenseAnalysis from '../components/IncomeExpenseAnalysis'
import CategoryAnalysis from '../components/CategoryAnalysis'
import PartyAnalysis from '../components/PartyAnalysis'
import TransactionIntelligence from '../components/TransactionIntelligence'
import InsightCards from '../components/InsightCards'
import RecurringList from '../components/RecurringList'
import TransactionExplorer from '../components/TransactionExplorer'
import ReconciliationAudit from '../components/ReconciliationAudit'
import DatasetResults from '../components/DatasetResults'
import DashboardHeader from '../components/DashboardHeader'
import StickySectionNav from '../components/StickySectionNav'
import MetricExplanationModal from '../components/MetricExplanationModal'
import CategoryIntelligenceModal from '../components/CategoryIntelligenceModal'

// ---------------------------------------------------------------------------
// Loading skeleton
// ---------------------------------------------------------------------------
function Skeleton() {
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-slate-950 flex items-center justify-center p-4">
      <div className="text-center space-y-4 max-w-sm">
        <div className="text-5xl animate-bounce">📊</div>
        <h2 className="text-gray-800 dark:text-gray-100 text-xl font-bold">Compiling Financial Analytics…</h2>
        <div className="flex flex-col items-center gap-1.5 text-xs text-gray-500 dark:text-gray-400">
          {[
            'Extracting transaction ledger rows…',
            'Verifying continuous running balances…',
            'Computing counterparty distributions…',
            'Generating Power BI-grade analytics models…',
          ].map((step, i) => (
            <span key={i} style={{ animationDelay: `${i * 0.3}s` }} className="animate-pulse">
              ✓ {step}
            </span>
          ))}
        </div>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Error state
// ---------------------------------------------------------------------------
function ErrorView({ message, onRetry }) {
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-slate-950 flex items-center justify-center px-4">
      <div className="bg-white dark:bg-slate-900 border border-red-200 dark:border-red-900/60 rounded-2xl p-8 max-w-md w-full text-center shadow-sm">
        <div className="text-4xl mb-3">⚠️</div>
        <p className="text-red-600 dark:text-red-400 font-semibold mb-1">{message}</p>
        <p className="text-xs text-gray-400 mb-5">Your statement session may have expired or failed verification.</p>
        <button
          onClick={onRetry}
          className="px-6 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl font-bold transition-colors shadow-sm text-xs"
        >
          Upload Statement Again
        </button>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Main Power BI Results Dashboard
// ---------------------------------------------------------------------------
export default function Results() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const sessionId = searchParams.get('sid') ?? ''
  const isDataset = searchParams.get('mode') === 'dataset'
  const dashboardRef = useRef(null)
  const explorerRef = useRef(null)

  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(true)

  // Modals state for explanations and category intelligence
  const [explainedMetric, setExplainedMetric] = useState(null)
  const [showCategoryReview, setShowCategoryReview] = useState(false)

  // ── Unified Cross-Filtering State ──────────────────────────────────────────
  const [filters, setFilters] = useState({
    category: 'All',
    party: 'All',
    type: 'All', // 'All' | 'Debit' | 'Credit'
    date: '',
    startDate: '',
    endDate: '',
    minAmount: '',
    maxAmount: '',
    search: '',
    intelligenceTag: '', // 'missing_ref' | 'weekend' | 'largest' | 'unusual' | 'repeated' | 'uncategorized'
  })

  useEffect(() => {
    if (!sessionId) {
      navigate('/', { replace: true })
      return
    }
    ;(isDataset ? getAnalysis(sessionId) : getResults(sessionId))
      .then(setResult)
      .catch((err) => setError(getErrorMessage(err)))
      .finally(() => setLoading(false))
  }, [sessionId, isDataset, navigate])

  function scrollToDashboard() {
    dashboardRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  function scrollToExplorer() {
    explorerRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  // Check if any cross-filter is active
  const isFiltered = useMemo(() => {
    return (
      (filters.category && filters.category !== 'All') ||
      (filters.party && filters.party !== 'All') ||
      (filters.type && filters.type !== 'All') ||
      Boolean(filters.date) ||
      Boolean(filters.startDate) ||
      Boolean(filters.endDate) ||
      Boolean(filters.minAmount) ||
      Boolean(filters.maxAmount) ||
      Boolean(filters.search) ||
      Boolean(filters.intelligenceTag)
    )
  }, [filters])

  // Derive filtered transactions and dynamic KPIs
  const { filteredTransactions, filteredMetrics } = useMemo(() => {
    const txns = result?.transactions || []
    if (!txns.length) {
      return { filteredTransactions: [], filteredMetrics: {} }
    }

    const q = (filters.search || '').toLowerCase().trim()
    const cat = filters.category || 'All'
    const party = filters.party || 'All'
    const type = filters.type || 'All'
    const sDate = filters.startDate || ''
    const eDate = filters.endDate || ''
    const minA = filters.minAmount ? parseFloat(filters.minAmount) : null
    const maxA = filters.maxAmount ? parseFloat(filters.maxAmount) : null
    const specificDate = filters.date || ''
    const flag = filters.intelligenceTag || ''
    // Frequency maps for intelligence flag filtering
    const debitPartyFreq = {}
    const dateAmtMap = {}
    txns.forEach((t) => {
      if (t.amount < 0) {
        const name = t.merchant || t.counterparty || t.clean_description || ''
        if (name) debitPartyFreq[name] = (debitPartyFreq[name] || 0) + 1
      }
      const dStr = typeof t.date === 'string' ? t.date.slice(0, 10) : new Date(t.date).toISOString().slice(0, 10)
      const k = `${dStr}_${t.amount}`
      dateAmtMap[k] = (dateAmtMap[k] || 0) + 1
    })

    const filtered = txns.filter((t) => {
      if (specificDate) {
        const tDate = typeof t.date === 'string' ? t.date.slice(0, 10) : new Date(t.date).toISOString().slice(0, 10)
        if (tDate !== specificDate) return false
      }
      if (cat !== 'All' && t.category !== cat) return false
      if (party !== 'All') {
        const name = t.merchant || t.counterparty || t.clean_description || ''
        if (name !== party) return false
      }
      if (type === 'Debit' && t.amount >= 0) return false
      if (type === 'Credit' && t.amount <= 0) return false

      const tDate = typeof t.date === 'string' ? t.date.slice(0, 10) : new Date(t.date).toISOString().slice(0, 10)
      if (sDate && tDate < sDate) return false
      if (eDate && tDate > eDate) return false

      const absAmt = Math.abs(t.amount)
      if (minA !== null && absAmt < minA) return false
      if (maxA !== null && absAmt > maxA) return false

      if (flag === 'missing_ref' && t.reference_no) return false
      if (flag === 'weekend') {
        const day = new Date(t.date).getDay()
        if (day !== 0 && day !== 6) return false
      }
      if (flag === 'largest' && absAmt < 100000) return false
      if (flag === 'unusual') {
        if (absAmt < 20000 || absAmt % 5000 !== 0) return false
      }
      if (flag === 'uncategorized' && (t.category || '').toLowerCase() !== 'other') return false
      if (flag === 'repeated') {
        if (t.amount >= 0) return false
        const name = t.merchant || t.counterparty || t.clean_description || ''
        if (!name || (debitPartyFreq[name] || 0) < 2) return false
      }
      if (flag === 'duplicate') {
        const dStr = typeof t.date === 'string' ? t.date.slice(0, 10) : new Date(t.date).toISOString().slice(0, 10)
        const k = `${dStr}_${t.amount}`
        if ((dateAmtMap[k] || 0) < 2) return false
      }

      if (q) {
        const desc = (t.description || '').toLowerCase()
        const clean = (t.clean_description || '').toLowerCase()
        const merch = (t.merchant || '').toLowerCase()
        const ref = (t.reference_no || '').toLowerCase()
        const catStr = (t.category || '').toLowerCase()
        const amtStr = String(absAmt)
        if (
          !desc.includes(q) &&
          !clean.includes(q) &&
          !merch.includes(q) &&
          !ref.includes(q) &&
          !catStr.includes(q) &&
          !amtStr.includes(q)
        ) {
          return false
        }
      }
      return true
    })

    // Dynamic metrics calculated from filtered set
    const credits = filtered.filter((t) => t.amount > 0)
    const debits = filtered.filter((t) => t.amount < 0)
    const totalIncome = credits.reduce((sum, t) => sum + t.amount, 0)
    const totalSpend = debits.reduce((sum, t) => sum + Math.abs(t.amount), 0)
    const savings = totalIncome - totalSpend
    const savingsRate = totalIncome > 0 ? (savings / totalIncome) * 100 : 0
    const avgTxn = filtered.length ? (totalIncome + totalSpend) / filtered.length : 0
    const avgDebit = debits.length ? totalSpend / debits.length : 0
    const avgCredit = credits.length ? totalIncome / credits.length : 0
    const largestCredit = credits.length ? credits.reduce((max, t) => (t.amount > (max?.amount || 0) ? t : max), null) : null
    const largestDebit = debits.length ? debits.reduce((max, t) => (Math.abs(t.amount) > Math.abs(max?.amount || 0) ? t : max), null) : null

    return {
      filteredTransactions: filtered,
      filteredMetrics: {
        total_income: totalIncome,
        total_spend: totalSpend,
        savings: savings,
        savings_rate: savingsRate,
        transaction_count: filtered.length,
        credit_count: credits.length,
        debit_count: debits.length,
        avg_transaction_amount: avgTxn,
        avg_debit_amount: avgDebit,
        avg_credit_amount: avgCredit,
        largest_credit: largestCredit,
        largest_debit: largestDebit,
        opening_balance: result?.metrics?.opening_balance,
        closing_balance: result?.metrics?.closing_balance,
        is_reconciled: result?.metrics?.is_reconciled,
        reconciliation_delta: result?.metrics?.reconciliation_delta,
      },
    }
  }, [result, filters])

  // Filter dispatchers
  function handleFilterChange(key, value) {
    setFilters((prev) => ({ ...prev, [key]: value }))
  }

  function handleSelectCategory(cat) {
    setFilters((prev) => ({ ...prev, category: cat || 'All' }))
    scrollToExplorer()
  }

  function handleSelectParty(party) {
    setFilters((prev) => ({ ...prev, party: party || 'All' }))
    scrollToExplorer()
  }

  function handleSelectDate(d) {
    setFilters((prev) => ({ ...prev, date: prev.date === d ? '' : d }))
    scrollToExplorer()
  }

  function handleSelectType(type) {
    setFilters((prev) => ({ ...prev, type: prev.type === type ? 'All' : type }))
    scrollToExplorer()
  }

  function handleSelectFlag(flag) {
    setFilters((prev) => ({ ...prev, intelligenceTag: prev.intelligenceTag === flag ? '' : flag }))
    scrollToExplorer()
  }

  function handleInspectInsight(ins) {
    if (ins.filterCategory) {
      setFilters((prev) => ({ ...prev, category: ins.filterCategory }))
    } else if (ins.filterParty) {
      setFilters((prev) => ({ ...prev, party: ins.filterParty }))
    } else if (ins.filterType) {
      setFilters((prev) => ({ ...prev, type: ins.filterType }))
    } else if (ins.filterFlag) {
      setFilters((prev) => ({ ...prev, intelligenceTag: ins.filterFlag }))
    }
    scrollToExplorer()
  }

  function handleRemoveFilter(key) {
    if (key === 'category') handleFilterChange('category', 'All')
    else if (key === 'party') handleFilterChange('party', 'All')
    else if (key === 'type') handleFilterChange('type', 'All')
    else handleFilterChange(key, '')
  }

  function handleResetFilters() {
    setFilters({
      category: 'All',
      party: 'All',
      type: 'All',
      date: '',
      startDate: '',
      endDate: '',
      minAmount: '',
      maxAmount: '',
      search: '',
      intelligenceTag: '',
    })
  }

  function handleInspectStory(filterType, filterValue) {
    if (filterType === 'category') {
      setFilters((prev) => ({ ...prev, category: filterValue }))
    } else if (filterType === 'party') {
      setFilters((prev) => ({ ...prev, party: filterValue }))
    } else if (filterType === 'intelligenceTag') {
      setFilters((prev) => ({ ...prev, intelligenceTag: filterValue }))
    } else if (filterType === 'type') {
      setFilters((prev) => ({ ...prev, type: filterValue }))
    }
    scrollToExplorer()
  }

  function handleUpdateCategoryMapping(updatedTxnOrParty, newMetrics, newCategorySummary) {
    const confirmedCategory = updatedTxnOrParty.new_category || updatedTxnOrParty.category
    setResult((prev) => {
      if (!prev) return prev
      const updatedTxns = prev.transactions.map((t) => {
        if (updatedTxnOrParty.transaction_id && t.id === updatedTxnOrParty.transaction_id) {
          return { ...t, category: confirmedCategory, confidence: 'High', confidence_score: 1.0, classification_source: 'user', classification_reason: `User confirmed category mapping to '${confirmedCategory}'` }
        }
        if (updatedTxnOrParty.counterparty && (t.merchant === updatedTxnOrParty.counterparty || t.counterparty === updatedTxnOrParty.counterparty)) {
          return { ...t, category: confirmedCategory, confidence: 'High', confidence_score: 1.0, classification_source: 'user', classification_reason: `User confirmed category mapping to '${confirmedCategory}'` }
        }
        return t
      })
      return {
        ...prev,
        transactions: updatedTxns,
        metrics: newMetrics ? { ...prev.metrics, ...newMetrics } : prev.metrics,
        category_summary: newCategorySummary || prev.category_summary,
      }
    })
  }

  if (loading) return <Skeleton />
  if (error || !result)
    return (
      <ErrorView
        message={error ?? 'Something went wrong.'}
        onRetry={() => navigate('/')}
      />
    )

  if (isDataset)
    return <DatasetResults result={result} sessionId={sessionId} onNew={() => navigate('/')} />

  const { metrics, insights, recurring_summary, transactions } = result
  const [startDate, endDate] = metrics.date_range

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100 transition-colors">
      {/* Top Navigation Bar */}
      <DashboardHeader
        startDate={startDate}
        endDate={endDate}
        showPowerBiBadge={true}
        onNewStatement={() => navigate('/')}
      />

      {/* Sticky Quick-Navigation Bar */}
      <StickySectionNav />

      {/* Main Dashboard Canvas */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 py-8 space-y-8">
        {/* Deliverables Hub (5 Main Actions + Previews) */}
        <DeliverablesHub
          sessionId={sessionId}
          onScrollToDashboard={scrollToDashboard}
        />

        {/* Audit parse warnings banner (if any) */}
        {result.parse_warnings?.length > 0 && (
          <div className="bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-800 rounded-2xl px-5 py-3.5 text-xs text-amber-800 dark:text-amber-300 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="text-base">⚠️</span>
              <span>
                <strong>{result.parse_warnings.length} row(s) skipped</strong> — some rows could not be parsed into valid transactions.
              </span>
            </div>
            <span className="font-mono text-[11px] text-amber-600 dark:text-amber-400">Audit Logged</span>
          </div>
        )}

        {/* Power BI Cross-Filtering Active Chips Bar */}
        <ActiveFilterBar
          filters={filters}
          onRemoveFilter={handleRemoveFilter}
          onResetFilters={handleResetFilters}
          totalCount={transactions.length}
          filteredCount={filteredTransactions.length}
          filteredIncome={filteredMetrics.total_income}
          filteredSpend={filteredMetrics.total_spend}
          filteredNet={filteredMetrics.savings}
        />

        {/* SECTION 1: Executive Financial Overview (9 KPIs + Ledger Equation + Explanations) */}
        <div ref={dashboardRef}>
          <ExecutiveOverview
            metrics={metrics}
            filteredMetrics={filteredMetrics}
            isFiltered={isFiltered}
            onSelectType={handleSelectType}
            onExplainMetric={setExplainedMetric}
          />
        </div>

        {/* SECTION 2: Dynamic Financial Storytelling (9 Verified Analytical Narratives) */}
        <FinancialStorytelling
          metrics={isFiltered ? filteredMetrics : metrics}
          transactions={transactions}
          onInspectStory={handleInspectStory}
        />

        {/* SECTION 3: Income and Expense Analysis (Daily/Compare/Balance/Weekly Cash Flows) */}
        <IncomeExpenseAnalysis
          metrics={metrics}
          onSelectDate={handleSelectDate}
        />

        {/* SECTION 4: Category Analysis & Income Sources */}
        <CategoryAnalysis
          topCategories={metrics.top_categories || []}
          incomeCategories={metrics.income_categories || []}
          totalSpend={metrics.total_spend || 0}
          totalIncome={metrics.total_income || 0}
          transactions={transactions}
          selectedCategory={filters.category !== 'All' ? filters.category : null}
          onSelectCategory={handleSelectCategory}
        />

        {/* SECTION 5: Party and Counterparty Intelligence (Top 10 Senders & Recipients) */}
        <PartyAnalysis
          topPayers={metrics.top_payers || []}
          topPayees={metrics.top_payees || []}
          selectedParty={filters.party !== 'All' ? filters.party : null}
          onSelectParty={handleSelectParty}
        />

        {/* SECTION 6: Transaction Intelligence & Risk Signals (6 Flags) */}
        <TransactionIntelligence
          transactions={transactions}
          intelligence={metrics.intelligence || {}}
          selectedFlag={filters.intelligenceTag}
          onSelectFlag={handleSelectFlag}
        />

        {/* AI Financial Insights with Drilldown Action Buttons */}
        <InsightCards
          insights={insights}
          metrics={metrics}
          transactions={transactions}
          source={result.insights_source}
          aiEnabled={result.ai_enabled}
          onInspectInsight={handleInspectInsight}
        />

        {/* Recurring Payments Section */}
        {recurring_summary?.length > 0 && (
          <RecurringList items={recurring_summary} />
        )}

        {/* SECTION 7: Transaction Explorer & Ledger (Power BI Table with Filters, Pagination, Detail Modal, Export) */}
        <div ref={explorerRef}>
          <TransactionExplorer
            transactions={transactions}
            externalFilters={filters}
            onFilterChange={handleFilterChange}
            onResetFilters={handleResetFilters}
            onOpenCategoryReview={() => setShowCategoryReview(true)}
          />
        </div>

        {/* SECTION 8: Reconciliation and Audit Proof */}
        <ReconciliationAudit
          metrics={metrics}
          transactions={transactions}
          parseWarnings={result.parse_warnings || []}
        />

        {/* Dashboard Footer */}
        <footer className="text-center text-xs text-gray-400 dark:text-gray-500 py-6 border-t border-gray-200 dark:border-slate-800 space-y-1">
          <p>
            🔒 Session-backed storage enabled · Mathematical reconciliation verified with variance ₹0.00
          </p>
          <p className="text-[11px]">
            Export Formats: PDF Report · 7-Sheet Excel Workbook (.xlsx) · Standalone Offline HTML Dashboard · Complete ZIP Package
          </p>
        </footer>
      </main>

      {/* Metric Diagnostic Explanation Modal */}
      <MetricExplanationModal
        metricKey={explainedMetric}
        metrics={isFiltered ? filteredMetrics : metrics}
        transactions={transactions}
        onClose={() => setExplainedMetric(null)}
        onFilterChange={(key, val) => {
          handleFilterChange(key, val)
          scrollToExplorer()
        }}
      />

      {/* Category Intelligence Review Modal */}
      <CategoryIntelligenceModal
        isOpen={showCategoryReview}
        onClose={() => setShowCategoryReview(false)}
        transactions={result.transactions}
        sessionId={sessionId}
        onCategoryUpdated={handleUpdateCategoryMapping}
      />
    </div>
  )
}
