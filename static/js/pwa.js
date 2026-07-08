// PWA Lifecycle and Capabilities
document.addEventListener('DOMContentLoaded', () => {
  // 1. Register Service Worker
  if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
      navigator.serviceWorker.register('/sw.js')
        .then(registration => {
          console.log('[PWA] Service Worker registered with scope:', registration.scope);
        })
        .catch(error => {
          console.error('[PWA] Service Worker registration failed:', error);
        });
    });
  }

  // 2. Custom Install Prompt Logic
  let deferredPrompt;
  const installSheet = document.getElementById('sbInstallSheet');
  const btnInstall = document.getElementById('sbBtnInstall');
  const btnLater = document.getElementById('sbBtnLater');

  window.addEventListener('beforeinstallprompt', (e) => {
    // Prevent the mini-infobar from appearing on mobile
    e.preventDefault();
    // Stash the event so it can be triggered later.
    deferredPrompt = e;
    // Show our custom premium bottom sheet
    if (installSheet) {
      setTimeout(() => {
        installSheet.classList.add('visible');
      }, 3000); // Wait 3 seconds before prompting to not overwhelm user
    }
  });

  if (btnInstall) {
    btnInstall.addEventListener('click', async () => {
      if (!deferredPrompt) return;
      installSheet.classList.remove('visible');
      // Show the native install prompt
      deferredPrompt.prompt();
      // Wait for the user to respond to the prompt
      const { outcome } = await deferredPrompt.userChoice;
      console.log(`[PWA] User response to install prompt: ${outcome}`);
      deferredPrompt = null;
    });
  }

  if (btnLater) {
    btnLater.addEventListener('click', () => {
      installSheet.classList.remove('visible');
    });
  }

  // 3. Push Notifications Architecture Preparation
  // We expose a function to request permission when appropriate (e.g. from Dashboard)
  window.StockboyPWA = {
    requestNotificationPermission: async () => {
      if (!('Notification' in window)) {
        console.log('[PWA] This browser does not support desktop notification');
        return false;
      }
      
      let permission = Notification.permission;
      if (permission === 'granted') return true;
      
      if (permission !== 'denied') {
        permission = await Notification.requestPermission();
        return permission === 'granted';
      }
      return false;
    }
  };
});
