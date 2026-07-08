/**
 * ════════════════════════════════════════════════════════════════
 *  STOCKBOY PREMIUM — NOTIFICATION CENTER UI
 *  Handles the Bell Dropdown and History List
 * ════════════════════════════════════════════════════════════════
 */

window.StockboyNotificationCenter = (function() {
  'use strict';

  let _history = [];
  let _unreadCount = 0;

  // DOM Elements (will be set on init)
  let _bellBtn = null;
  let _badge = null;
  let _dropdown = null;
  let _list = null;
  let _soundBtn = null;

  function init() {
    // Inject Bell UI into Navbar if not exists
    const navLinks = document.querySelector('.nav-links');
    if (navLinks && !document.getElementById('sbNotifBell')) {
      const bellHtml = `
        <div style="position: relative; margin-right: 0.5rem;" id="sbNotifContainer">
          <button id="sbNotifBell" class="sb-nav-bell" aria-label="Notifications">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"></path><path d="M13.73 21a2 2 0 0 1-3.46 0"></path></svg>
            <span id="sbNotifBadge" class="sb-bell-badge hidden">0</span>
          </button>
          
          <div id="sbNotifDropdown" class="sb-notif-dropdown">
            <div class="sb-notif-header">
              <h3>Notifications</h3>
              <div class="sb-notif-actions">
                <button id="sbNotifSoundBtn" class="sb-sound-toggle" title="Toggle Sound">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon>
                    <path d="M19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07"></path>
                  </svg>
                </button>
                <button id="sbNotifMarkRead" class="sb-notif-btn">Mark all read</button>
              </div>
            </div>
            <ul id="sbNotifList" class="sb-notif-list">
              <div class="sb-notif-empty">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"></path><path d="M13.73 21a2 2 0 0 1-3.46 0"></path></svg>
                <span>No new notifications</span>
              </div>
            </ul>
          </div>
        </div>
      `;
      // Insert before user-info or auth buttons
      navLinks.insertAdjacentHTML('afterbegin', bellHtml);
    }

    _bellBtn = document.getElementById('sbNotifBell');
    _badge = document.getElementById('sbNotifBadge');
    _dropdown = document.getElementById('sbNotifDropdown');
    _list = document.getElementById('sbNotifList');
    _soundBtn = document.getElementById('sbNotifSoundBtn');

    if (!_bellBtn) return;

    // Toggle Dropdown
    _bellBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      _dropdown.classList.toggle('open');
      _bellBtn.classList.toggle('active');
    });

    // Close dropdown on outside click
    document.addEventListener('click', (e) => {
      if (_dropdown.classList.contains('open') && !e.target.closest('#sbNotifContainer')) {
        _dropdown.classList.remove('open');
        _bellBtn.classList.remove('active');
      }
    });

    // Sound Toggle
    if (_soundBtn && window.StockboySound) {
      updateSoundIcon();
      _soundBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        window.StockboySound.toggleMute();
        updateSoundIcon();
      });
    }

    // Mark all read (Local only for now, can be hooked to DB later)
    document.getElementById('sbNotifMarkRead')?.addEventListener('click', (e) => {
      e.stopPropagation();
      _history.forEach(n => n.read = true);
      _unreadCount = 0;
      updateUI();
    });
  }

  function updateSoundIcon() {
    if (!window.StockboySound) return;
    const isMuted = window.StockboySound.getIsMuted();
    if (isMuted) {
      _soundBtn.classList.add('muted');
      _soundBtn.innerHTML = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon><line x1="23" y1="9" x2="17" y2="15"></line><line x1="17" y1="9" x2="23" y2="15"></line></svg>`;
    } else {
      _soundBtn.classList.remove('muted');
      _soundBtn.innerHTML = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon><path d="M19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07"></path></svg>`;
    }
  }

  /**
   * Syncs the internal state with the provided list of notifications
   * @param {Array} notifications Array of notification objects
   */
  function sync(notifications) {
    _history = notifications;
    _unreadCount = _history.filter(n => !n.read).length;
    updateUI();
  }

  /**
   * Adds a new notification to the history (if it's a real-time event)
   */
  function add(notif) {
    _history.unshift(notif);
    if (!notif.read) _unreadCount++;
    updateUI();
  }

  function updateUI() {
    if (!_badge || !_list) return;

    // Update Badge
    if (_unreadCount > 0) {
      _badge.textContent = _unreadCount > 99 ? '99+' : _unreadCount;
      _badge.classList.remove('hidden');
    } else {
      _badge.classList.add('hidden');
    }

    // Update List
    if (_history.length === 0) {
      _list.innerHTML = `
        <div class="sb-notif-empty">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"></path><path d="M13.73 21a2 2 0 0 1-3.46 0"></path></svg>
          <span>No new notifications</span>
        </div>
      `;
      return;
    }

    let html = '';
    _history.slice(0, 50).forEach(n => {
      html += `
        <li class="sb-notif-item ${n.read ? '' : 'unread'}" data-id="${n.id}">
          <div class="sb-notif-item-body">
            <div class="sb-notif-item-title">${n.title || ''}</div>
            <div class="sb-notif-item-desc">${n.message || ''}</div>
            <div class="sb-notif-item-time">${formatTime(n.timestamp)}</div>
          </div>
        </li>
      `;
    });
    _list.innerHTML = html;

    // Attach click handlers to mark as read
    _list.querySelectorAll('.sb-notif-item').forEach(item => {
      item.addEventListener('click', () => {
        const id = item.dataset.id;
        const notif = _history.find(n => n.id === id);
        if (notif && !notif.read) {
          notif.read = true;
          _unreadCount = Math.max(0, _unreadCount - 1);
          updateUI();
          // Here we would ideally sync the read state back to Firestore if we wanted to
        }
      });
    });
  }

  function formatTime(timestamp) {
    if (!timestamp) return 'Just now';
    const date = new Date(timestamp);
    const now = new Date();
    const diff = now - date;
    
    if (diff < 60000) return 'Just now';
    if (diff < 3600000) return Math.floor(diff / 60000) + 'm ago';
    if (diff < 86400000) return Math.floor(diff / 3600000) + 'h ago';
    if (diff < 172800000) return 'Yesterday';
    return date.toLocaleDateString();
  }

  // Auto-init on load
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  return {
    sync,
    add
  };

})();
