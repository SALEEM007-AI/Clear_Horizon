import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import {
  getHealth,
  getMetrics,
  getPayments,
  getCustomers,
  getCustomerHistory,
} from "../api";

export default function Dashboard() {
  const [health, setHealth] = useState(null);
  const [metrics, setMetrics] = useState(null);
  const [payments, setPayments] = useState([]);
  const [customers, setCustomers] = useState([]);
  const [selectedCustomerId, setSelectedCustomerId] = useState("");
  const [customerHistory, setCustomerHistory] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Initial load
  useEffect(() => {
    Promise.allSettled([
      getHealth(),
      getMetrics(),
      getPayments(null, 15),
      getCustomers(),
    ]).then(([h, m, p, c]) => {
      if (h.status === "fulfilled") setHealth(h.value);
      else setError("Backend unreachable");
      if (m.status === "fulfilled") setMetrics(m.value);
      if (p.status === "fulfilled") setPayments(p.value);
      if (c.status === "fulfilled") {
        setCustomers(c.value);
        if (c.value.length > 0) setSelectedCustomerId(String(c.value[0].id));
      }
      setLoading(false);
    });
  }, []);

  // Poll metrics every 3s
  useEffect(() => {
    const interval = setInterval(() => {
      getMetrics().then(setMetrics).catch(() => {});
      getPayments(null, 15).then(setPayments).catch(() => {});
    }, 3000);
    return () => clearInterval(interval);
  }, []);

  // Load customer history when selection changes
  useEffect(() => {
    if (!selectedCustomerId) return;
    getCustomerHistory(selectedCustomerId)
      .then(setCustomerHistory)
      .catch(() => setCustomerHistory(null));
  }, [selectedCustomerId]);

  const getSuccessRate = (hist) => {
    if (!hist || hist.attempts === 0) return 0;
    return Math.round((hist.successes / hist.attempts) * 100);
  };

  const getMethodIcon = (type) => {
    switch (type) {
      case "CARD": return "credit_card";
      case "UPI": return "qr_code_scanner";
      case "NET_BANKING": return "account_balance";
      case "WALLET": return "account_balance_wallet";
      default: return "payment";
    }
  };

  const getActionBadgeClass = (type) => {
    switch (type) {
      case "AUTO_RETRY":
        return "bg-[#4edea3]/10 text-[#4edea3] border border-[#4edea3]/20";
      case "CUSTOMER_NUDGE":
        return "bg-secondary/10 text-secondary border border-secondary/20";
      case "MERCHANT_ESCALATION":
        return "bg-rose-500/10 text-rose-400 border border-rose-500/20";
      default:
        return "bg-slate-500/10 text-slate-400 border border-slate-500/20";
    }
  };

  const getConfidenceProgressBg = (c) => {
    if (c >= 0.75) return "bg-[#4edea3]";
    if (c >= 0.4) return "bg-amber-500";
    return "bg-rose-500";
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4"></div>
          <p className="text-slate-400 font-medium">Loading Recovery Dashboard...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      
      {/* Header Section */}
      <div className="flex justify-between items-end mb-4 border-b border-slate-200 pb-6">
        <div>
          <h2 className="text-2xl font-black tracking-tight text-slate-900 mb-1">Dashboard</h2>
          <p className="text-sm text-slate-500">Real-time recovery performance and agent decisions.</p>
        </div>
      </div>

      {/* Hero Metrics */}
      {metrics && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          
          {/* Primary Metric */}
          <div className="fintech-card p-6 flex flex-col justify-center relative overflow-hidden h-40">
            <div className="absolute top-0 right-0 p-4 opacity-5">
              <span className="material-symbols-outlined text-7xl text-primary">trending_up</span>
            </div>
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">Agent Recovery Rate</h3>
            <div className="text-5xl font-black text-primary tracking-tight mb-2">
              {metrics.agent_recovery_rate}%
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xs text-slate-500">Baseline: {metrics.baseline_recovery_rate}%</span>
              <span className="bg-primary/10 text-primary text-[10px] font-bold px-2 py-0.5 rounded flex items-center gap-0.5">
                <span className="material-symbols-outlined text-xs">arrow_upward</span>
                +{Math.round((metrics.agent_recovery_rate - metrics.baseline_recovery_rate) * 10) / 10}%
              </span>
            </div>
          </div>

          {/* Secondary Metrics */}
          <div className="grid grid-cols-2 gap-6 md:col-span-2">
            
            <div className="fintech-card p-6 flex flex-col justify-between h-40">
              <div className="flex justify-between items-start">
                <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500">Total Recovered</h3>
                <span className="material-symbols-outlined text-slate-400">account_balance_wallet</span>
              </div>
              <div className="text-2xl font-black text-slate-900 mt-2">
                ₹{metrics.total_recovered_amount.toLocaleString("en-IN")}
              </div>
              <div className="mt-4 h-1.5 w-full progress-bar-bg rounded-full overflow-hidden">
                <div 
                  className="h-full bg-primary rounded-full transition-all duration-500" 
                  style={{ width: `${Math.min(100, (metrics.total_recovered / Math.max(1, metrics.total_failed)) * 100)}%` }}
                ></div>
              </div>
            </div>

            <div className="fintech-card p-6 flex flex-col justify-between h-40">
              <div className="flex justify-between items-start">
                <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500">Fees Saved</h3>
                <span className="material-symbols-outlined text-slate-400">savings</span>
              </div>
              <div className="text-2xl font-black text-slate-900 mt-2">
                ₹{metrics.fees_saved.toLocaleString("en-IN")}
              </div>
              <div className="mt-4 h-1.5 w-full progress-bar-bg rounded-full overflow-hidden">
                <div 
                  className="h-full bg-secondary rounded-full transition-all duration-500" 
                  style={{ width: `${Math.min(100, (metrics.fees_saved / Math.max(1, metrics.total_failed * 2)) * 100)}%` }}
                ></div>
              </div>
            </div>

          </div>
        </div>
      )}

      {/* Two Column Layout for Scenarios & Sidebar */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Main Content Area */}
        <div className="lg:col-span-2 flex flex-col gap-6">
          <div className="fintech-card p-6">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500 border-b border-slate-200 pb-4 mb-6">
              Live Decision Feed
            </h3>
            
            {payments.length === 0 ? (
              <div className="text-center py-12 text-slate-400">
                <span className="material-symbols-outlined text-5xl opacity-40 mb-2">smart_toy</span>
                <p>No recovery events logged yet. Go to Simulator to trigger payments.</p>
              </div>
            ) : (
              <div className="flex flex-col gap-6">
                {payments.map((p) => {
                  const action = p.recovery_actions?.[0];
                  if (!action) return null;

                  return (
                    <div key={p.id} className="space-y-4">
                      <div className="grid grid-cols-12 gap-4 items-center">
                        <div className="col-span-12 md:col-span-4 flex items-center gap-3">
                          <div className="w-8 h-8 rounded-full bg-slate-100 border border-slate-200 flex items-center justify-center text-primary font-bold text-xs">
                            {p.customer?.name ? p.customer.name.split(" ").map(n => n[0]).join("") : "C"}
                          </div>
                          <div>
                            <div className="text-sm font-semibold text-slate-900">{p.customer?.name || "Customer"}</div>
                            <div className="text-[10px] font-mono text-slate-500">#TXN-{p.id}</div>
                          </div>
                        </div>
                        
                        <div className="col-span-12 sm:col-span-4 md:col-span-3">
                          <span className={`inline-flex px-3 py-1 rounded-full font-bold text-[9px] uppercase tracking-wider ${getActionBadgeClass(action.action_type)}`}>
                            {action.action_type.replace(/_/g, " ")}
                          </span>
                        </div>
                        
                        <div className="col-span-12 sm:col-span-8 md:col-span-5 flex items-center gap-4">
                          <div className="flex-1">
                            <div className="flex justify-between mb-1">
                              <span className="text-[10px] text-slate-500 uppercase tracking-wider">Confidence</span>
                              <span className="text-[10px] text-slate-900 font-bold">{Math.round(action.confidence * 100)}%</span>
                            </div>
                            <div className="h-1.5 w-full progress-bar-bg rounded-full overflow-hidden">
                              <div 
                                className={`h-full rounded-full ${getConfidenceProgressBg(action.confidence)}`} 
                                style={{ width: `${action.confidence * 100}%` }}
                              ></div>
                            </div>
                          </div>
                          <div className="text-sm font-bold text-slate-900 text-right w-20 shrink-0">
                            ₹{p.amount.toLocaleString("en-IN")}
                          </div>
                        </div>
                      </div>
                      <hr className="border-slate-200" />
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>

        {/* Sidebar */}
        <div className="flex flex-col gap-6">
          
          {/* Recovery by Method */}
          <div className="fintech-card p-6">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500 border-b border-slate-200 pb-4 mb-6">
              Recovery by Method
            </h3>
            
            <div className="space-y-4">
              <select
                value={selectedCustomerId}
                onChange={(e) => setSelectedCustomerId(e.target.value)}
                className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-2.5 text-xs text-slate-700 focus:outline-none focus:border-primary transition"
              >
                {customers.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name} (#{c.id})
                  </option>
                ))}
              </select>

              {customerHistory && customerHistory.method_history.length > 0 ? (
                <div className="flex flex-col gap-5 pt-2">
                  {customerHistory.method_history.map((mh) => {
                    const rate = getSuccessRate(mh);
                    return (
                      <div key={mh.id}>
                        <div className="flex justify-between mb-2">
                          <span className="text-xs text-slate-900 flex items-center gap-1.5">
                            <span className="material-symbols-outlined text-sm text-slate-400">
                              {getMethodIcon(mh.method_type)}
                            </span>
                            {mh.method_type}
                          </span>
                          <span className="text-xs font-bold text-primary">{rate}%</span>
                        </div>
                        <div className="h-1.5 w-full progress-bar-bg rounded-full overflow-hidden">
                          <div 
                            className="h-full bg-primary rounded-full transition-all duration-500" 
                            style={{ width: `${rate}%` }}
                          ></div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div className="text-center py-6 text-slate-400 text-xs">
                  No method success history available.
                </div>
              )}
            </div>
          </div>

        </div>

      </div>

    </div>
  );
}
