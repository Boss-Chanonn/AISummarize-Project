/* ── Learnova billing.js ── */
/* Shared billing utilities for billing.html, payment.html, confirm.html */

/* -- Group: API Constants -- */
const BILLING_API = '/api/billing';

/* -- Group: Billing API Calls -- */

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
  } catch (_error) {
    // On network/auth errors we intentionally return null so page code can use safe fallbacks.
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

/* -- Group: Payment Success Feedback -- */

/**
 * Inject fallback toast animation styles once.
 * This check prevents duplicate <style> blocks when users revisit the page.
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
 * Show payment success toast, then redirect to dashboard.
 */
function showSuccessNotification() {
  if (typeof showToast === 'function') {
    showToast('Payment completed successfully.', 'success', 2200);
  } else {
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

  setTimeout(function() {
    window.location.href = 'dashboard.html';
  }, 1800);
}
