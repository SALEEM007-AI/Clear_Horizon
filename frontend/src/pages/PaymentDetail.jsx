import { useState, useEffect } from "react";
import { useParams, Link } from "react-router-dom";
import { getPayment, createRetryLink } from "../api";

export default function PaymentDetail() {
  const { id } = useParams();
  const [payment, setPayment] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [creatingLink, setCreatingLink] = useState(false);
  const [linkError, setLinkError] = useState(null);

  useEffect(() => {
    getPayment(id)
      .then(setPayment)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [id]);

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

  const handleCreateLink = async () => {
    setCreatingLink(true);
    setLinkError(null);
    try {
      await createRetryLink(id);
      const updated = await getPayment(id);
      setPayment(updated);
    } catch (e) {
      setLinkError(e.message);
    }
    setCreatingLink(false);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4"></div>
          <p className="text-slate-400 font-medium">Loading details...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-xl mx-auto px-4 py-12 text-center">
        <Link to="/" className="inline-flex items-center text-sm text-primary hover:text-indigo-400 mb-6">
          <span className="material-symbols-outlined text-sm mr-1">arrow_back</span>
          Back to Dashboard
        </Link>
        <div className="glass-panel rounded-xl p-8 border-rose-500/30">
          <span className="material-symbols-outlined text-rose-400 text-5xl mb-2">error</span>
          <p className="text-slate-300">Failed to load payment details: {error}</p>
        </div>
      </div>
    );
  }

  const action = payment?.recovery_actions?.[0];
  const outcome = action?.outcome;

  return (
    <div className="space-y-6">
      
      <Link to="/" className="inline-flex items-center text-sm font-semibold text-primary hover:text-indigo-600 transition-colors">
        <span className="material-symbols-outlined text-sm mr-1">arrow_back</span>
        Back to Dashboard
      </Link>

      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 border-b border-slate-200 pb-6">
        <div>
          <h1 className="text-3xl font-extrabold tracking-tight text-slate-900">Payment Details</h1>
          <p className="text-slate-500 mt-1">Transaction audit log and recovery pipeline analytics</p>
        </div>
        <div className="font-mono text-sm bg-slate-50 border border-slate-200 px-4 py-2 rounded-xl text-slate-700 shadow-sm">
          Reference: #{payment.id}
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        
        {/* Payment Info */}
        <div className="glass-panel rounded-xl p-6 space-y-6 shadow-sm">
          <h3 className="text-base font-bold text-slate-900 flex items-center gap-2 border-b border-slate-200 pb-4">
            <span className="material-symbols-outlined text-primary">receipt_long</span>
            Audit Details
          </h3>

          <div className="divide-y divide-slate-100 text-sm">
            <div className="flex justify-between py-3">
              <span className="text-slate-500">Total Value</span>
              <span className="font-bold text-slate-900">₹{payment.amount?.toLocaleString("en-IN")}</span>
            </div>
            
            <div className="flex justify-between py-3 items-center">
              <span className="text-slate-500">Status</span>
              <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold ${
                payment.status === 'SUCCESS' 
                  ? 'bg-emerald-500/10 text-emerald-600 border border-emerald-500/20' 
                  : 'bg-rose-500/10 text-rose-600 border border-rose-500/20'
              }`}>
                {payment.status}
              </span>
            </div>
            
            <div className="flex justify-between py-3">
              <span className="text-slate-500">Failure Trigger</span>
              <span className="text-slate-800 font-semibold">{payment.failure_reason?.replace(/_/g, " ") || "—"}</span>
            </div>
            
            <div className="flex justify-between py-3">
              <span className="text-slate-500">Customer Name</span>
              <span className="text-slate-800 font-semibold">{payment.customer?.name || `ID #${payment.customer_id}`}</span>
            </div>
            
            <div className="flex justify-between py-3">
              <span className="text-slate-500">Email Address</span>
              <span className="text-slate-700">{payment.customer?.email || "—"}</span>
            </div>

            <div className="flex justify-between py-3">
              <span className="text-slate-500">Initial Method</span>
              <span className="text-slate-800 font-semibold">
                {payment.method ? `${payment.method.type}${payment.method.last4 ? ` (••${payment.method.last4})` : ""}` : "—"}
              </span>
            </div>
            
            <div className="flex justify-between py-3">
              <span className="text-slate-500">Created Time</span>
              <span className="text-slate-700">
                {payment.created_at ? new Date(payment.created_at).toLocaleString("en-IN") : "—"}
              </span>
            </div>
          </div>
        </div>

        {/* Recovery Action / Agent Decision */}
        <div className="glass-panel rounded-xl p-6 space-y-6 shadow-sm">
          <h3 className="text-base font-bold text-slate-900 flex items-center gap-2 border-b border-slate-200 pb-4">
            <span className="material-symbols-outlined text-primary">smart_toy</span>
            Recovery Decision
          </h3>

          {action ? (
            <div className="space-y-6">
              <div className="flex justify-between items-center text-sm">
                <span className="text-slate-500">Agent Recommendation</span>
                <span className={`px-2.5 py-0.5 rounded-full font-label-caps text-xs ${getActionBadgeClass(action.action_type)}`}>
                  {action.action_type.replace(/_/g, " ")}
                </span>
              </div>

              {/* Confidence Meter */}
              <div className="space-y-2">
                <div className="flex justify-between text-xs font-semibold text-slate-500">
                  <span>Recommendation Confidence</span>
                  <span className={getConfidenceColor(action.confidence)}>
                    {Math.round(action.confidence * 100)}%
                  </span>
                </div>
                <div className="h-2 w-full bg-slate-100 rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all duration-500 ${getConfidenceProgressBg(action.confidence)}`}
                    style={{ width: `${action.confidence * 100}%` }}
                  ></div>
                </div>
              </div>

              {action.recommended_method && (
                <div className="flex justify-between text-sm pt-2">
                  <span className="text-slate-500">Target Method</span>
                  <span className="text-slate-800 font-bold">{action.recommended_method}</span>
                </div>
              )}

              {action.reasoning && (
                <div className="bg-primary-fixed/30 border border-primary/10 rounded-xl p-4 text-xs text-slate-800 space-y-1">
                  <div className="font-bold text-primary flex items-center gap-1">
                    <span className="material-symbols-outlined text-sm">psychology</span>
                    AI Reasoning
                  </div>
                  <p className="leading-relaxed">{action.reasoning}</p>
                </div>
              )}

              {action.nudge_text && (
                <div className="bg-amber-500/5 border border-amber-500/20 rounded-xl p-4 text-xs text-slate-800 space-y-1">
                  <div className="font-bold text-amber-500 flex items-center gap-1">
                    <span className="material-symbols-outlined text-sm">chat_bubble</span>
                    Nudge Message
                  </div>
                  <p className="leading-relaxed">{action.nudge_text}</p>
                </div>
              )}

              {action.payment_link_url && (
                <a
                  href={action.payment_link_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="w-full inline-flex items-center justify-center gap-2 bg-cyan-500 hover:bg-cyan-600 hover:shadow-[0_0_15px_rgba(6,182,212,0.4)] text-white font-bold py-3 rounded-xl text-sm transition shadow-sm"
                >
                  <span className="material-symbols-outlined">credit_card</span>
                  Open Razorpay Checkout
                </a>
              )}

              {action.action_type === "CUSTOMER_NUDGE" && !action.payment_link_url && (
                <div className="space-y-3">
                  <button
                    className="w-full bg-slate-50 hover:bg-slate-100 border border-slate-200 text-slate-700 font-bold py-2.5 rounded-xl text-sm transition shadow-sm"
                    onClick={handleCreateLink}
                    disabled={creatingLink}
                  >
                    {creatingLink ? "Generating checkout link..." : "🔗 Generate Razorpay Link"}
                  </button>
                  {linkError && (
                    <p className="text-xs text-amber-500 text-center">{linkError}</p>
                  )}
                </div>
              )}

              {/* Outcome info */}
              {outcome && (
                <div className="pt-4 border-t border-slate-200 space-y-3">
                  <div className="flex justify-between items-center text-sm">
                    <span className="text-slate-550">Execution Outcome</span>
                    <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold ${
                      outcome.result === "RECOVERED" 
                        ? 'bg-emerald-500/10 text-emerald-600 border border-emerald-500/20' 
                        : 'bg-rose-500/10 text-rose-600 border border-rose-500/20'
                    }`}>
                      {outcome.result.replace(/_/g, " ")}
                    </span>
                  </div>
                  {outcome.recovered_amount > 0 && (
                    <div className="flex justify-between items-center text-sm">
                      <span className="text-slate-500">Amount Recovered</span>
                      <span className="font-black text-emerald-500">₹{outcome.recovered_amount.toLocaleString("en-IN")}</span>
                    </div>
                  )}
                </div>
              )}
            </div>
          ) : (
            <div className="text-center py-12 text-slate-400">
              No recovery recommendation logged for this transaction.
            </div>
          )}
        </div>

      </div>

    </div>
  );
}
