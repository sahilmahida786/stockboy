/**
 * ════════════════════════════════════════════════════════════════
 *  STOCKBOY PREMIUM — ENTERPRISE ANIMATION ENGINE
 *  Vanilla JS · IntersectionObserver · requestAnimationFrame
 *  Zero dependencies · GPU-friendly · Mobile-aware
 * ════════════════════════════════════════════════════════════════
 */
(function() {
  'use strict';

  // ── Feature detection ──
  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const isMobile = window.innerWidth <= 768;
  const isTouchDevice = 'ontouchstart' in window || navigator.maxTouchPoints > 0;

  // ── 1. Navbar Scroll Glassmorphism ──
  function initNavbarScroll() {
    const navbar = document.querySelector('.navbar');
    if (!navbar) return;

    let ticking = false;
    let lastScrollY = 0;

    function updateNavbar() {
      const scrollY = window.scrollY || window.pageYOffset;
      if (scrollY > 40) {
        navbar.classList.add('sb-scrolled');
      } else {
        navbar.classList.remove('sb-scrolled');
      }
      lastScrollY = scrollY;
      ticking = false;
    }

    window.addEventListener('scroll', function() {
      if (!ticking) {
        requestAnimationFrame(updateNavbar);
        ticking = true;
      }
    }, { passive: true });

    // Initial check
    updateNavbar();
  }

  // ── 2. Scroll Progress Bar ──
  function initScrollProgress() {
    const bar = document.querySelector('.sb-scroll-progress');
    if (!bar) return;

    let ticking = false;

    function updateProgress() {
      const scrollTop = window.scrollY || window.pageYOffset;
      const docHeight = document.documentElement.scrollHeight - window.innerHeight;
      const percent = docHeight > 0 ? (scrollTop / docHeight) * 100 : 0;
      bar.style.width = percent + '%';
      ticking = false;
    }

    window.addEventListener('scroll', function() {
      if (!ticking) {
        requestAnimationFrame(updateProgress);
        ticking = true;
      }
    }, { passive: true });
  }

  // ── 3. Scroll Reveal System (IntersectionObserver) ──
  function initScrollReveal() {
    if (prefersReducedMotion) {
      // Immediately show all elements
      document.querySelectorAll('.reveal, .reveal-fade, .reveal-slide-up, .reveal-slide-left, .reveal-slide-right, .reveal-scale').forEach(function(el) {
        el.classList.add('active');
      });
      return;
    }

    const revealObserver = new IntersectionObserver(function(entries) {
      entries.forEach(function(entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add('active');
          revealObserver.unobserve(entry.target); // Fire only once
        }
      });
    }, {
      threshold: 0.08,
      rootMargin: '0px 0px -40px 0px'
    });

    document.querySelectorAll('.reveal, .reveal-fade, .reveal-slide-up, .reveal-slide-left, .reveal-slide-right, .reveal-scale').forEach(function(el) {
      revealObserver.observe(el);
    });
  }

  // ── 4. Animated Number Counter (requestAnimationFrame) ──
  function initCountUp() {
    const countObserver = new IntersectionObserver(function(entries) {
      entries.forEach(function(entry) {
        if (entry.isIntersecting && !entry.target.dataset.sbAnimated) {
          entry.target.dataset.sbAnimated = '1';
          animateNumber(entry.target);
          countObserver.unobserve(entry.target);
        }
      });
    }, { threshold: 0.5 });

    document.querySelectorAll('[data-sb-count]').forEach(function(el) {
      countObserver.observe(el);
    });
  }

  function animateNumber(el) {
    var target = parseInt(el.dataset.sbCount, 10);
    var prefix = el.dataset.sbPrefix || '';
    var suffix = el.dataset.sbSuffix || '';
    var duration = isMobile ? 1200 : 1800;

    if (!target) return;

    var startTime = performance.now();

    function step(currentTime) {
      var elapsed = currentTime - startTime;
      var progress = Math.min(elapsed / duration, 1);
      // Ease-out cubic
      var ease = 1 - Math.pow(1 - progress, 3);
      var currentVal = Math.floor(ease * target);

      el.textContent = prefix + currentVal + suffix;

      if (progress < 1) {
        requestAnimationFrame(step);
      } else {
        el.textContent = prefix + target + suffix;
      }
    }

    requestAnimationFrame(step);
  }

  // ── 5. Card Mouse Glow Tracking (Desktop Only) ──
  function initCardGlow() {
    if (isMobile || isTouchDevice || prefersReducedMotion) return;

    document.querySelectorAll('.sb-card-glow').forEach(function(card) {
      card.addEventListener('mousemove', function(e) {
        var rect = card.getBoundingClientRect();
        var x = ((e.clientX - rect.left) / rect.width) * 100;
        var y = ((e.clientY - rect.top) / rect.height) * 100;
        card.style.setProperty('--mouse-x', x + '%');
        card.style.setProperty('--mouse-y', y + '%');
      });
    });
  }

  // ── 6. Button Ripple Effect ──
  function initRipple() {
    document.querySelectorAll('.sb-ripple').forEach(function(btn) {
      btn.addEventListener('click', function(e) {
        var ripple = document.createElement('span');
        var rect = btn.getBoundingClientRect();
        var size = Math.max(rect.width, rect.height);
        var x = e.clientX - rect.left - size / 2;
        var y = e.clientY - rect.top - size / 2;

        ripple.style.cssText = 'position:absolute;border-radius:50%;background:rgba(255,255,255,0.15);pointer-events:none;width:' + size + 'px;height:' + size + 'px;left:' + x + 'px;top:' + y + 'px;transform:scale(0);opacity:1;transition:transform 0.5s ease,opacity 0.4s ease;z-index:1;';
        btn.style.position = 'relative';
        btn.style.overflow = 'hidden';
        btn.appendChild(ripple);

        // Trigger reflow and animate
        ripple.offsetHeight; // force reflow
        ripple.style.transform = 'scale(2.5)';
        ripple.style.opacity = '0';

        setTimeout(function() {
          if (ripple.parentNode) ripple.parentNode.removeChild(ripple);
        }, 600);
      });
    });
  }

  // ── 7. Form Validation Shake ──
  // Exported globally so templates can call it
  window.sbShakeElement = function(el) {
    if (!el) return;
    el.classList.remove('sb-shake');
    void el.offsetWidth; // trigger reflow
    el.classList.add('sb-shake');
    el.addEventListener('animationend', function handler() {
      el.classList.remove('sb-shake');
      el.removeEventListener('animationend', handler);
    });
  };

  // ── 8. Smooth Page Transitions (internal links) ──
  function initPageTransitions() {
    if (prefersReducedMotion) return;

    document.querySelectorAll('a[href]').forEach(function(link) {
      // Only internal, non-hash, non-blank links
      var href = link.getAttribute('href');
      if (!href || href.startsWith('#') || href.startsWith('javascript') ||
          href.startsWith('http') || href.startsWith('mailto') || href.startsWith('tel') ||
          link.target === '_blank' || link.hasAttribute('download')) return;

      link.addEventListener('click', function(e) {
        e.preventDefault();
        document.body.style.opacity = '0';
        document.body.style.transition = 'opacity 0.18s ease';
        setTimeout(function() {
          window.location.href = href;
        }, 180);
      });
    });
  }

  // ── 9. Hero Parallax (Desktop Only) ──
  function initHeroParallax() {
    if (isMobile || isTouchDevice || prefersReducedMotion) return;

    var heroGlow = document.querySelector('.hero-glow');
    var heroGrid = document.querySelector('.hero-grid');
    if (!heroGlow && !heroGrid) return;

    var ticking = false;

    document.addEventListener('mousemove', function(e) {
      if (ticking) return;
      ticking = true;

      requestAnimationFrame(function() {
        var centerX = window.innerWidth / 2;
        var centerY = window.innerHeight / 2;
        var moveX = (e.clientX - centerX) / centerX;
        var moveY = (e.clientY - centerY) / centerY;

        if (heroGlow) {
          heroGlow.style.transform = 'translateX(calc(-50% + ' + (moveX * 15) + 'px)) translateY(' + (moveY * 10) + 'px)';
        }
        if (heroGrid) {
          heroGrid.style.transform = 'translate(' + (moveX * -5) + 'px, ' + (moveY * -5) + 'px)';
        }

        ticking = false;
      });
    }, { passive: true });
  }

  // ── 10. Dashboard Tab Animation ──
  function initDashboardTabs() {
    document.querySelectorAll('[data-sb-tab-trigger]').forEach(function(trigger) {
      trigger.addEventListener('click', function() {
        var targetId = trigger.dataset.sbTabTrigger;
        var target = document.getElementById(targetId);
        if (!target) return;

        // Hide all siblings
        var parent = target.parentElement;
        if (parent) {
          parent.querySelectorAll('[data-sb-tab-panel]').forEach(function(panel) {
            panel.style.display = 'none';
            panel.classList.remove('sb-tab-content');
          });
        }

        // Show target with animation
        target.style.display = '';
        void target.offsetWidth; // trigger reflow
        target.classList.add('sb-tab-content');
      });
    });
  }

  // ── 11. Auto-apply animation classes to known elements ──
  function autoApplyClasses() {
    // Sections get reveal-slide-up
    document.querySelectorAll('.sec, .sec-title, .section-title').forEach(function(el) {
      if (!el.classList.contains('reveal') && !el.classList.contains('reveal-slide-up') && !el.classList.contains('reveal-fade')) {
        el.classList.add('reveal-slide-up');
      }
    });

    // Cards get hover lift + reveal
    var cardSelectors = '.plan-card, .feature-card, .trust-card, .trust-card-v2, .testi-card, .testi-card-v2, .metric-card, .step';
    document.querySelectorAll(cardSelectors).forEach(function(el) {
      el.classList.add('sb-card-hover');
      if (!el.classList.contains('reveal') && !el.classList.contains('reveal-scale')) {
        el.classList.add('reveal-scale');
      }
    });

    // Stagger grids
    document.querySelectorAll('.plans-grid, .features-grid, .trust-grid, .trust-cards-grid, .metrics-grid, .steps-list').forEach(function(el) {
      el.classList.add('reveal-stagger');
    });

    // Buttons get ripple
    document.querySelectorAll('.cta-main, .btn-plan, .btn-gold, .btn-login, .btn-register').forEach(function(el) {
      el.classList.add('sb-ripple');
    });

    // Form inputs get focus animation
    document.querySelectorAll('input[type="text"], input[type="email"], input[type="password"], input[type="tel"], input[type="number"], textarea').forEach(function(el) {
      el.classList.add('sb-input-focus');
    });
  }

  // ── Initialize Everything ──
  function init() {
    autoApplyClasses();
    initNavbarScroll();
    initScrollProgress();
    initScrollReveal();
    initCountUp();
    initCardGlow();
    initRipple();
    initPageTransitions();
    initHeroParallax();
    initDashboardTabs();
  }

  // Run on DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
