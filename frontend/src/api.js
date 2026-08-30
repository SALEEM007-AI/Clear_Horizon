const API_BASE = "https://clear-horizon-lyqj.onrender.com";

/**
 * Fetch helper — prepends the backend base URL and returns parsed JSON.
 * Throws on non-OK responses with the status text.
 */
async function apiFetch(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...options.headers },
    ...options,
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`API ${res.status}: ${body}`);
  }
  return res.json();
}

/** GET /api/health */
export function getHealth() {
  return apiFetch("/api/health");
}

/** POST /api/seed */
export function seedData() {
  return apiFetch("/api/seed", { method: "POST" });
}

/** POST /api/reset — delete all data and re-seed */
export function resetDemoData() {
  return apiFetch("/api/reset", { method: "POST" });
}

/** GET /api/customers */
export function getCustomers() {
  return apiFetch("/api/customers");
}

/** GET /api/customers/:id/history */
export function getCustomerHistory(customerId) {
  return apiFetch(`/api/customers/${customerId}/history`);
}

/** POST /api/payments/simulate */
export function simulatePayment({ customer_id, amount, failure_reason }) {
  return apiFetch("/api/payments/simulate", {
    method: "POST",
    body: JSON.stringify({ customer_id, amount, failure_reason }),
  });
}

/** GET /api/payments */
export function getPayments(status = null, limit = 50) {
  const params = new URLSearchParams();
  if (status) params.set("status", status);
  params.set("limit", String(limit));
  return apiFetch(`/api/payments?${params}`);
}

/** GET /api/payments/:id */
export function getPayment(id) {
  return apiFetch(`/api/payments/${id}`);
}

/** GET /api/metrics */
export function getMetrics() {
  return apiFetch("/api/metrics");
}

/** POST /api/payments/:id/outcome */
export function recordOutcome(paymentId, { result, recovered_amount }) {
  return apiFetch(`/api/payments/${paymentId}/outcome`, {
    method: "POST",
    body: JSON.stringify({ result, recovered_amount }),
  });
}

/** POST /api/payments/:id/retry-link — create Razorpay payment link */
export function createRetryLink(paymentId) {
  return apiFetch(`/api/payments/${paymentId}/retry-link`, {
    method: "POST",
  });
}

export default apiFetch;
