/**
 * ── Learnova Billing (billing.js) ──
 *
 * Shared billing/payment utilities used across billing.html, payment.html,
 * and confirm.html.
 *
 * Responsibilities:
 *   - Fetch the current user's billing status from the backend
 *   - Submit payment confirmation (with card_last4 only — NEVER the full PAN)
 *   - Show a success notification with fallback when showToast() is unavailable
 *
 * Dependencies:
 *   - app.js (showToast(), used if available for success feedback)
 *   - config.js (tier values)
 *   - Backend endpoints under /api/billing
 */

// ── API Constants ──

// Base path for all billing-related API routes.
const BILLING_API = '/api/billing';

// ── Billing API Calls ──

/**
 * Fetch the current billing status for the logged-in user.
 *
 * Used by billing.html and confirm.html to display plan details,
 * payment history, and subscription state on page load.
 *
 * @returns {Promise<object|null>} Billing status object, or null if not
 *                                 authenticated or if the request fails.
 *                                 Null is returned deliberately on network/
 *                                 auth errors so callers can show safe fallbacks.
 */
async function getBillingStatus() {
  const token = localStorage.getItem('token');
  if (!token) return null; // No auth token — treat as unauthenticated.
  try {
    const res = await fetch(`${BILLING_API}/status`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    if (!res.ok) return null;
    return await res.json();
  } catch (_error) {
    // On network/auth errors we intentionally return null so page code can use safe fallbacks.
    return null;
  }
}

/**
 * Submit payment details to confirm the transaction.
 *
 * Called from confirm.html when the user clicks the final confirmation button.
 *
 * SECURITY: NEVER sends the full card number — only `card_last4` (last 4 digits).
 *           The full PAN is tokenised client-side before this point.
 *
 * @param {object} paymentData - Payment payload (includes card_last4, expiry, etc.)
 * @returns {Promise<object>} Parsed JSON response from the backend
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

// ── Payment Success Feedback ──

/**
 * Inject the fallback CSS keyframe animation for the billing toast once.
 *
 * The guard (checking for #billing-toast-style) prevents duplicate <style>
 * blocks from accumulating when users navigate back and forth between pages.
 */
function ensureBillingToastStyles() {
  if (document.getElementById('billing-toast-style')) return;

  const style = document.createElement('style');
  style.id = 'billing-toast-style';
  style.textContent = '@keyframes billing-toast-pop {'
    + '0% { transform: translateY(-8px); opacity: 0; }'
    + '100% { transform: translateY(0); opacity: 1; }'
    + '}';

  document.head.appendChild(style);
}

/**
 * Display a payment-success toast and then redirect the user to pro.html.
 *
 * Uses app.js's showToast() when available; otherwise falls back to a
 * self-contained animated notification element.
 *
 * Called from: confirm.html after a successful payment confirmation response.
 *
 * Flow:
 *   1. Show success toast (either via showToast() or a custom fallback).
 *   2. After a short delay, redirect to /pro.html (the Pro features page).
 */
function showSuccessNotification() {
  // Use the global toast system if present (defined in app.js).
  if (typeof showToast === 'function') {
    showToast('Payment completed successfully.', 'success', 2200);
  } else {
    // Fallback: inject a self-contained notification element with custom styles.
    ensureBillingToastStyles();

    const notification = document.createElement('div');
    notification.textContent = 'Payment completed successfully.';

    // Layout: fixed floating message at top-right.
    // Appearance: green success color, readable text, and shadow depth.
    // Animation: subtle pop-in motion for immediate feedback.
    notification.style.cssText = 'position:fixed;top:20px;right:20px;z-index:9999;'
      + 'padding:12px 16px;border-radius:10px;background:#1f8f4c;color:#ffffff;'
      + 'font-size:14px;font-weight:600;box-shadow:0 10px 28px rgba(0,0,0,0.2);'
      + 'animation:billing-toast-pop 220ms ease-out;';

    document.body.appendChild(notification);
    setTimeout(function () {
      notification.remove();
    }, 1600);
  }

  // Redirect after a brief pause so the user sees the confirmation.
  setTimeout(function() {
    window.location.href = 'pro.html';
  }, 1800);
}