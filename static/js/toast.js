/**
 * ════════════════════════════════════════════════════════════════
 *  STOCKBOY PREMIUM — TOAST NOTIFICATION ENGINE
 *  Handles rendering, queuing, and auto-dismissal of Toasts
 * ════════════════════════════════════════════════════════════════
 */

window.StockboyToast = (function() {
  'use strict';

  let container = null;

  // Icon mapping using Lucide SVGs
  const ICONS = {
    info: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/></svg>`,
    success: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>`,
    warning: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/><path d="M12 9v4"/><path d="M12 17h.01"/></svg>`,
    error: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>`,
    'signal-buy': `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>`,
    'signal-sell': `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 15l9 7 9-7"/><path d="M12 2v20"/></svg>`
  };

  function initContainer() {
    if (!container) {
      container = document.createElement('div');
      container.className = 'sb-toast-container';
      document.body.appendChild(container);
    }
  }

  /**
   * Show a toast notification
   * @param {Object} opts { title, message, type, duration }
   */
  function show(opts) {
    initContainer();

    const title = opts.title || '';
    const message = opts.message || '';
    const type = opts.type || 'info'; // info, success, warning, error, signal-buy, signal-sell
    const duration = opts.duration || 6000;

    const toast = document.createElement('div');
    toast.className = `sb-toast ${type}`;
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', 'polite');

    const iconHtml = ICONS[type] || ICONS['info'];

    toast.innerHTML = `
      <div class="sb-toast-icon">${iconHtml}</div>
      <div class="sb-toast-body">
        ${title ? `<div class="sb-toast-title">${title}</div>` : ''}
        <div class="sb-toast-message">${message}</div>
        <div class="sb-toast-time">Just now</div>
      </div>
      <button class="sb-toast-close" aria-label="Close notification">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
      </button>
      <div class="sb-toast-progress" style="animation: sbToastProgress ${duration}ms linear forwards;"></div>
    `;

    // Add progress animation dynamically
    const styleId = 'sbToastAnimStyle';
    if (!document.getElementById(styleId)) {
      const style = document.createElement('style');
      style.id = styleId;
      style.innerHTML = `@keyframes sbToastProgress { from { width: 100%; } to { width: 0%; } }`;
      document.head.appendChild(style);
    }

    container.appendChild(toast);

    // Play Sound if enabled (Will rely on notification-sound.js if loaded)
    if (window.StockboySound) {
      window.StockboySound.playNotification();
    }

    // Dismissal logic
    let dismissTimeout;
    
    const dismiss = () => {
      if (toast.classList.contains('closing')) return;
      toast.classList.add('closing');
      setTimeout(() => {
        if (toast.parentNode) toast.parentNode.removeChild(toast);
      }, 300); // Matches CSS slide out duration
    };

    const startTimer = () => {
      if (duration > 0) {
        dismissTimeout = setTimeout(dismiss, duration);
      }
    };

    const clearTimer = () => {
      if (dismissTimeout) clearTimeout(dismissTimeout);
    };

    // Close button
    toast.querySelector('.sb-toast-close').addEventListener('click', dismiss);

    // Pause on hover
    toast.addEventListener('mouseenter', clearTimer);
    toast.addEventListener('mouseleave', startTimer);

    startTimer();
  }

  return {
    show
  };

})();
