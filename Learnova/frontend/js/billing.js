/* ── Learnova billing.js ── */
/* Shared billing utilities for billing.html, payment.html, confirm.html */

const BILLING_API = '/api/billing';

/**
 * Fetch current billing status for the logged-in user.
 * Returns null on error or if not authenticated.
 */
async function getBillingStatus() {
  const token = localStorage.getItem('token');
  if (!token) return null;
  try {
    const res = await fetch(`${BILLING_API}/status`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    if (!res.ok) return null;
    return await res.json();
  } catch (e) {
    return null;
  }
}

/**
 * POST /api/billing/confirm with payment details.
 * Returns the API response object.
 * NEVER sends the full card number — only card_last4.
 */
async function confirmPayment(paymentData) {
  const token = localStorage.getItem('token');
  const res = await fetch(`${BILLING_API}/confirm`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(paymentData),
  });
  return await res.json();
}

/**
 * Show payment success toast, then redirect to dashboard.
 */
function showSuccessNotification() {
  if (typeof showToast === 'function') {
    showToast('Payment completed successfully.', 'success', 2200);
  }
  setTimeout(function() {
    window.location.href = 'dashboard.html';
  }, 1800);
}
