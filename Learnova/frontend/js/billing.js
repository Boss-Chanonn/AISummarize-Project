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
 * Show a gold-bordered success notification in the top-right corner,
 * then redirect to dashboard.html after 4 seconds.
 */
function showSuccessNotification() {
  const notification = document.createElement('div');
  notification.style.cssText = `
    position: fixed;
    top: 24px;
    right: 24px;
    background: #1a1a1a;
    border: 1px solid #c9a84c;
    border-radius: 12px;
    padding: 20px 24px;
    z-index: 9999;
    min-width: 280px;
    max-width: 340px;
    box-shadow: 0 8px 32px rgba(201,168,76,0.2);
    animation: slideIn 0.3s ease;
  `;
  notification.innerHTML = `
    <div style="display:flex;align-items:center;gap:12px;margin-bottom:8px;">
      <span style="font-size:24px;">✅</span>
      <strong style="color:#c9a84c;font-size:16px;">Payment Successful!</strong>
    </div>
    <p style="color:#e0e0e0;margin:0;font-size:14px;line-height:1.5;">
      Welcome to Learnova Pro ✨
    </p>
    <p style="color:#999;margin:6px 0 0;font-size:12px;">
      Redirecting to your dashboard…
    </p>
  `;

  // Inject slideIn keyframe if not already present
  if (!document.getElementById('billing-anim-style')) {
    const style = document.createElement('style');
    style.id = 'billing-anim-style';
    style.textContent = `
      @keyframes slideIn {
        from { opacity: 0; transform: translateX(32px); }
        to   { opacity: 1; transform: translateX(0); }
      }
    `;
    document.head.appendChild(style);
  }

  document.body.appendChild(notification);

  setTimeout(() => {
    notification.remove();
    window.location.href = 'dashboard.html';
  }, 4000);
}
