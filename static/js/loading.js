/**
 * ════════════════════════════════════════════════════════════════
 *  STOCKBOY PREMIUM — ENTERPRISE LOADING SYSTEM
 *  Manages page loaders, form button states, and Razorpay overlays
 * ════════════════════════════════════════════════════════════════
 */
(function() {
  'use strict';

  // ── 1. Page Loader Management ──
  function initPageLoader() {
    const loader = document.getElementById('sbGlobalLoader');
    const progress = document.getElementById('sbLoaderProgress');
    
    if (!loader) return;

    // Simulate progress
    let p = 0;
    const interval = setInterval(() => {
      p += Math.random() * 15;
      if (p > 90) p = 90;
      if (progress) progress.style.width = p + '%';
    }, 50);

    // Hide loader
    function hideLoader() {
      clearInterval(interval);
      if (progress) progress.style.width = '100%';
      
      setTimeout(() => {
        loader.classList.add('hidden');
        setTimeout(() => {
          if (loader.parentNode) loader.parentNode.removeChild(loader);
        }, 400); // Wait for CSS transition
      }, 150); // slight delay after 100%
    }

    // Hide on window load, or fallback after 3 seconds max
    if (document.readyState === 'complete') {
      hideLoader();
    } else {
      window.addEventListener('load', hideLoader);
      setTimeout(hideLoader, 3000); // Safety fallback
    }
  }

  // ── 2. Form Button States (Login/Signup) ──
  function initFormLoaders() {
    // Automatically bind to all standard forms
    document.querySelectorAll('form').forEach(form => {
      form.addEventListener('submit', function(e) {
        // Find the submit button
        const submitBtn = form.querySelector('button[type="submit"], input[type="submit"]');
        if (submitBtn && !submitBtn.classList.contains('btn-loading')) {
          // If the form is valid (HTML5 validation)
          if (form.checkValidity()) {
            // We don't preventDefault, we let the form submit natively
            // But we add the loading state immediately
            submitBtn.classList.add('btn-loading');
            
            // Safety: if navigation doesn't happen, re-enable after 10 seconds
            setTimeout(() => {
              submitBtn.classList.remove('btn-loading');
            }, 10000);
          }
        }
      });
    });
  }

  // ── 3. Razorpay Payment Overlay Management ──
  // We expose this globally so HTML inline scripts can call it
  window.sbShowPaymentLoader = function() {
    let overlay = document.getElementById('sbPaymentOverlay');
    
    // Create it if it doesn't exist
    if (!overlay) {
      overlay = document.createElement('div');
      overlay.id = 'sbPaymentOverlay';
      overlay.className = 'sb-payment-overlay';
      overlay.innerHTML = `
        <div class="sb-payment-card">
          <svg class="sb-payment-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
            <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
          </svg>
          <div class="sb-payment-title">Preparing Secure Payment</div>
          <div class="sb-payment-subtitle">
            <div class="sb-payment-spinner"></div>
            Connecting to Razorpay...
          </div>
        </div>
      `;
      document.body.appendChild(overlay);
    }
    
    // Show it
    // Force reflow
    void overlay.offsetWidth;
    overlay.classList.add('active');

    // Razorpay Hijack: We need to know when Razorpay's modal actually opens to hide our loader.
    // Razorpay injects an iframe or div with class 'razorpay-container'
    // We use a MutationObserver to detect it.
    const observer = new MutationObserver((mutations, obs) => {
      const rzpContainer = document.querySelector('.razorpay-container');
      if (rzpContainer && getComputedStyle(rzpContainer).display !== 'none') {
        // Razorpay is visible, hide our overlay!
        overlay.classList.remove('active');
        obs.disconnect(); // stop observing
      }
    });
    
    observer.observe(document.body, { childList: true, subtree: true });

    // Safety fallback: Hide overlay after 8 seconds in case network fails
    setTimeout(() => {
      if (overlay.classList.contains('active')) {
        overlay.classList.remove('active');
        observer.disconnect();
      }
    }, 8000);
  };

  // ── Initialization ──
  // Run immediately for the page loader
  initPageLoader();

  // Run DOM-dependent stuff when ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
      initFormLoaders();
    });
  } else {
    initFormLoaders();
  }

})();
