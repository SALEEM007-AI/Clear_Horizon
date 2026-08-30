import { useState, useEffect, useRef } from "react";
import { simulatePayment, getCustomers, getMetrics, seedData } from "../api";

const FAILURE_TYPES = [
  {
    key: "INSUFFICIENT_FUNDS",
    label: "Insufficient Funds",
    icon: "account_balance_wallet",
    desc: "Card or wallet lacks funds — agent will nudge customer to use alternative method",
    color: "rgba(239, 68, 68, 0.1)",
    textColor: "#f87171",
  },
  {
    key: "BANK_DOWN",
    label: "Bank Down",
    icon: "account_balance",
    desc: "Issuing bank is down — agent will auto-retry using best historical alternative",
    color: "rgba(245, 158, 11, 0.1)",
    textColor: "#fbbf24",
  },
  {
    key: "OTP_TIMEOUT",
    label: "OTP Timeout",
    icon: "timer",
    desc: "Customer missed OTP entry — agent will nudge customer or bypass with UPI",
    color: "rgba(59, 130, 246, 0.1)",
    textColor: "#60a5fa",
  },
  {
    key: "CARD_DECLINED",
    label: "Card Declined",
    icon: "credit_card_off",
    desc: "Card blocked or invalid — low confidence, agent escalates to merchant",
    color: "rgba(249, 115, 22, 0.1)",
    textColor: "#fb923c",
  },
  {
    key: "NETWORK_ERROR",
    label: "Network Error",
    icon: "cell_wifi",
    desc: "Transient connectivity loss — agent will auto-retry same method immediately",
    color: "rgba(168, 85, 247, 0.1)",
    textColor: "#c084fc",
  },
];

export default function Simulator() {
  const [customers, setCustomers] = useState([]);
  const [selectedCustomer, setSelectedCustomer] = useState("");
  const [amount, setAmount] = useState("1499.00");
  const [failureReason, setFailureReason] = useState("INSUFFICIENT_FUNDS");
  const [simulating, setSimulating] = useState(false);
  const [decisions, setDecisions] = useState([]);
  const [expandedId, setExpandedId] = useState(null);
  const [metrics, setMetrics] = useState(null);
  const [seeding, setSeeding] = useState(false);
  const feedRef = useRef(null);

  // Load customers on mount
  useEffect(() => {
    getCustomers()
      .then((data) => {
        setCustomers(data);
        if (data.length > 0) setSelectedCustomer(String(data[0].id));
      })
      .catch(() => {});
  }, []);

  // Poll metrics every 2s
  useEffect(() => {
    const poll = () => getMetrics().then(setMetrics).catch(() => {});
    poll();
    const interval = setInterval(poll, 2000);
    return () => clearInterval(interval);
  }, []);

  const handleSeed = async () => {
    setSeeding(true);
    try {
      await seedData();
      const data = await getCustomers();
      setCustomers(data);
      if (data.length > 0) setSelectedCustomer(String(data[0].id));
    } catch (e) {
      console.error(e);
    }
    setSeeding(false);
  };

  const handleSimulate = async () => {
    if (!selectedCustomer) return;
    setSimulating(true);
    try {
      const result = await simulatePayment({
        customer_id: parseInt(selectedCustomer),
        amount: parseFloat(amount),
        failure_reason: failureReason,
      });
      setDecisions((prev) => [result, ...prev].slice(0, 50));
      setExpandedId(result.id);
      getMetrics().then(setMetrics).catch(() => {});
    } catch (e) {
      console.error(e);
    }
    setSimulating(false);
  };

  const getConfidenceLevel = (c) => {
    if (c >= 0.75) return "high";
    if (c >= 0.4) return "medium";
    return "low";
  };

  const getConfidenceColor = (c) => {
    if (c >= 0.75) return "text-emerald-400";
    if (c >= 0.4) return "text-amber-400";
    return "text-rose-400";
  };

  const getConfidenceProgressBg = (c) => {
    if (c >= 0.75) return "bg-emerald-500";
    if (c >= 0.4) return "bg-amber-500";
    return "bg-rose-500";
  };

  const getActionBadgeClass = (type) => {
    switch (type) {
      case "AUTO_RETRY":
        return "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30";
      case "CUSTOMER_NUDGE":
        return "bg-violet-500/20 text-violet-300 border border-violet-500/30";
      case "MERCHANT_ESCALATION":
        return "bg-rose-500/20 text-rose-300 border border-rose-500/30";
      default:
        return "bg-slate-500/20 text-slate-300 border border-slate-500/30";
    }
  };

  const getActionBadgeIcon = (type) => {
    switch (type) {
      case "AUTO_RETRY": return "autorenew";
      case "CUSTOMER_NUDGE": return "notifications_active";
      case "MERCHANT_ESCALATION": return "warning";
      default: return "help";
    }
  };

  return (
    <div className="space-y-6">
      
      {/* Header section */}
      <div className="border-b border-slate-200 pb-6">
        <h1 className="text-3xl font-extrabold tracking-tight text-slate-900 flex items-center gap-2">
          <span className="material-symbols-outlined text-primary" style={{ fontSize: "2rem" }}>science</span>
          Smart Simulator
        </h1>
        <p className="text-slate-500 mt-1">
          Trigger simulated payment failures and watch the AI agent recover payments dynamically.
        </p>
      </div>

      {customers.length === 0 && (
        <div className="glass-panel rounded-xl p-8 text-center space-y-4 max-w-lg mx-auto">
          <p className="text-slate-500">No customer profiles found. Seed the database to load parameters.</p>
          <button
            className="w-full bg-primary hover:bg-primary/90 text-white font-bold py-2.5 px-4 rounded-xl transition shadow-sm"
            onClick={handleSeed}
            disabled={seeding}
          >
            {seeding ? "Seeding parameters..." : "🌱 Seed Demo Parameters"}
          </button>
        </div>
      )}

      {/* Metrics comparison banner */}
      {metrics && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="glass-panel rounded-xl p-6 flex justify-between items-center border-l-4 border-l-primary shadow-sm">
            <div>
              <span className="text-xs font-bold uppercase tracking-wider text-slate-500">🤖 Agent Recovered</span>
              <div className="text-2xl font-black text-slate-900 mt-1">₹{metrics.total_recovered_amount.toLocaleString("en-IN")}</div>
            </div>
            <div className="text-right">
              <span className="text-emerald-500 text-lg font-black">{metrics.agent_recovery_rate}%</span>
              <p className="text-[10px] text-slate-400">recovery rate</p>
            </div>
          </div>
          
          <div className="glass-panel rounded-xl p-6 flex justify-between items-center border-l-4 border-l-slate-400 shadow-sm">
            <div>
              <span className="text-xs font-bold uppercase tracking-wider text-slate-500">📊 Baseline (Generic Retry)</span>
              <div className="text-2xl font-black text-slate-500 mt-1">
                ₹{Math.round(metrics.total_failed * 1499 * 0.4).toLocaleString("en-IN")}
              </div>
            </div>
            <div className="text-right">
              <span className="text-slate-500 text-lg font-black">{metrics.baseline_recovery_rate}%</span>
              <p className="text-[10px] text-slate-400">recovery rate</p>
            </div>
          </div>
        </div>
      )}

      {customers.length > 0 && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          
          {/* Simulation panel (2/3 width) */}
          <div className="lg:col-span-2 space-y-6">
            <div className="glass-panel rounded-xl p-6 space-y-6 shadow-sm">
              <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
                <span className="material-symbols-outlined text-primary">tune</span>
                Configure Scenario
              </h2>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-1">
                  <label className="text-xs font-bold uppercase tracking-wider text-slate-500">Target Profile</label>
                  <select
                    value={selectedCustomer}
                    onChange={(e) => setSelectedCustomer(e.target.value)}
                    className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-2.5 text-sm text-slate-700 focus:outline-none focus:border-primary transition"
                  >
                    {customers.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.name} (#{c.id})
                      </option>
                    ))}
                  </select>
                </div>
                
                <div className="space-y-1">
                  <label className="text-xs font-bold uppercase tracking-wider text-slate-500">Amount (INR)</label>
                  <input
                    type="number"
                    value={amount}
                    onChange={(e) => setAmount(e.target.value)}
                    min="1"
                    step="0.01"
                    className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-2.5 text-sm text-slate-700 focus:outline-none focus:border-primary transition"
                  />
                </div>
              </div>

              {/* Scenarios Grid */}
              <div className="space-y-2">
                <label className="text-xs font-bold uppercase tracking-wider text-slate-500 block">Failure Scenarios</label>
                <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
                  {FAILURE_TYPES.map((ft) => (
                    <button
                      key={ft.key}
                      onClick={() => setFailureReason(ft.key)}
                      className={`glass-panel rounded-xl p-4 text-left flex flex-col items-start gap-2.5 transition-all duration-300 relative overflow-hidden group shadow-sm ${
                        failureReason === ft.key 
                          ? 'border-primary bg-primary-fixed/30 shadow-[0_0_15px_rgba(0,74,198,0.08)]' 
                          : 'hover:border-slate-300'
                      }`}
                    >
                      <div 
                        className="w-10 h-10 rounded-full flex items-center justify-center transition-colors"
                        style={{ backgroundColor: ft.color, color: ft.textColor }}
                      >
                        <span className="material-symbols-outlined" style={{ fontVariationSettings: "'FILL' 1" }}>
                          {ft.icon}
                        </span>
                      </div>
                      <div>
                        <h3 className="text-sm font-bold text-slate-900 group-hover:text-primary transition-colors">{ft.label}</h3>
                        <p className="text-[10px] text-slate-500 leading-normal mt-1">{ft.desc}</p>
                      </div>
                    </button>
                  ))}
                </div>
              </div>

              <button
                className="w-full bg-primary hover:bg-primary/95 text-white font-bold py-3 px-6 rounded-xl transition shadow-md flex items-center justify-center gap-2"
                onClick={handleSimulate}
                disabled={simulating || !selectedCustomer}
              >
                <span className="material-symbols-outlined">bolt</span>
                {simulating ? "Analysing failure context..." : "Trigger Simulation Pipeline"}
              </button>
            </div>
          </div>

          {/* Live Feed (1/3 width) */}
          <div className="lg:col-span-1">
            <div className="glass-panel rounded-xl p-6 space-y-6 flex flex-col max-h-[640px] shadow-sm">
              <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
                <span className="material-symbols-outlined text-primary">memory</span>
                Recovery Feed
              </h2>

              {decisions.length === 0 ? (
                <div className="flex-1 flex flex-col items-center justify-center text-slate-400 py-12">
                  <span className="material-symbols-outlined text-5xl opacity-40 mb-2">smart_toy</span>
                  <p className="text-sm">Feed is active. Trigger a scenario to monitor decisions.</p>
                </div>
              ) : (
                <div className="flex-1 overflow-y-auto space-y-4 pr-1">
                  {decisions.map((d) => {
                    const action = d.recovery_actions?.[0];
                    const outcome = action?.outcome;
                    if (!action) return null;

                    return (
                      <div
                        key={d.id}
                        onClick={() => setExpandedId(expandedId === d.id ? null : d.id)}
                        className="bg-slate-50 border border-slate-100 hover:border-primary/20 rounded-xl p-4 cursor-pointer transition-all space-y-3 shadow-sm"
                      >
                        <div className="flex justify-between items-start gap-2">
                          <div>
                            <div className="font-bold text-slate-900 text-sm">
                              {d.customer?.name || `Customer #${d.customer_id}`}
                            </div>
                            <div className="text-xs text-slate-500 mt-0.5">
                              ₹{d.amount.toLocaleString("en-IN")} · {d.failure_reason?.replace(/_/g, " ")}
                            </div>
                          </div>
                          
                          <div className={`px-2 py-0.5 rounded-full font-label-caps text-[9px] flex items-center gap-1 shrink-0 ${getActionBadgeClass(action.action_type)}`}>
                            <span className="material-symbols-outlined text-[10px]">
                              {getActionBadgeIcon(action.action_type)}
                            </span>
                            {action.action_type.replace(/_/g, " ")}
                          </div>
                        </div>

                        {/* Progress confidence */}
                        <div className="space-y-1">
                          <div className="flex justify-between text-[10px] text-slate-500 font-semibold">
                            <span>Confidence</span>
                            <span className={getConfidenceColor(action.confidence)}>
                              {Math.round(action.confidence * 100)}%
                            </span>
                          </div>
                          <div className="h-1.5 w-full bg-slate-200 rounded-full overflow-hidden">
                            <div 
                              className={`h-full rounded-full ${getConfidenceProgressBg(action.confidence)}`}
                              style={{ width: `${action.confidence * 100}%` }}
                            ></div>
                          </div>
                        </div>

                        {/* Expanded details */}
                        {expandedId === d.id && (
                          <div className="pt-2 border-t border-slate-200 space-y-3">
                            <div className="bg-primary-fixed/30 border border-primary/10 rounded-xl p-3 text-xs text-slate-800">
                              <div className="font-bold text-primary flex items-center gap-1 mb-1">
                                <span className="material-symbols-outlined text-sm">psychology</span>
                                AI Reasoning
                              </div>
                              {action.reasoning}
                            </div>

                            {action.nudge_text && (
                              <div className="bg-amber-500/5 border border-amber-500/20 rounded-xl p-3 text-xs text-slate-800">
                                <div className="font-bold text-amber-500 flex items-center gap-1 mb-1">
                                  <span className="material-symbols-outlined text-sm">chat_bubble</span>
                                  Nudge Message
                                </div>
                                {action.nudge_text}
                              </div>
                            )}

                            {action.payment_link_url && (
                              <a
                                href={action.payment_link_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                onClick={(e) => e.stopPropagation()}
                                className="w-full inline-flex items-center justify-center gap-1 bg-cyan-500 hover:bg-cyan-600 text-white font-bold py-2 rounded-xl text-xs transition shadow-sm"
                              >
                                <span className="material-symbols-outlined text-sm">credit_card</span>
                                Open Checkout Link
                              </a>
                            )}
                          </div>
                        )}
                        
                        {outcome && (
                          <div className="flex justify-between items-center text-[10px] pt-1">
                            <span className="text-slate-500">Outcome</span>
                            <span className={`font-bold flex items-center gap-0.5 ${
                              outcome.result === "RECOVERED" ? "text-emerald-500" : "text-rose-500"
                            }`}>
                              <span className="material-symbols-outlined text-xs">
                                {outcome.result === "RECOVERED" ? "check_circle" : "cancel"}
                              </span>
                              {outcome.result.replace(/_/g, " ")}
                            </span>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
          
        </div>
      )}

    </div>
  );
}
