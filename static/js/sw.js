const CACHE_NAME = 'stockboy-pwa-v1';
const STATIC_ASSETS = [
  '/',
  '/offline',
  '/static/css/hero.css',
  '/static/css/dashboard.css',
  '/static/css/trust.css',
  '/static/css/profile.css',
  '/static/js/trust.js',
  '/static/js/pwa.js',
  '/static/favicons/android-chrome-192x192.png',
  '/static/favicons/android-chrome-512x512.png'
];

// Install Event - Cache Static Assets
self.addEventListener('install', (event) => {
  self.skipWaiting();
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      console.log('[SW] Caching Static Assets');
      return cache.addAll(STATIC_ASSETS);
    })
  );
});

// Activate Event - Clean up old caches
self.addEventListener('activate', (event) => {
  event.waitUntil(self.clients.claim());
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cacheName) => {
          if (cacheName !== CACHE_NAME) {
            console.log('[SW] Deleting old cache:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    })
  );
});

// Fetch Event - Network First for HTML, Cache First for Static Assets
self.addEventListener('fetch', (event) => {
  const request = event.request;
  const url = new URL(request.url);

  // Ignore non-GET requests (POST, PUT, etc)
  if (request.method !== 'GET') return;

  // Cache First for static assets (CSS, JS, Images)
  if (url.pathname.startsWith('/static/')) {
    event.respondWith(
      caches.match(request).then((cachedResponse) => {
        return cachedResponse || fetch(request).then(response => {
          return caches.open(CACHE_NAME).then(cache => {
            cache.put(request, response.clone());
            return response;
          });
        });
      })
    );
    return;
  }

  // Network First for everything else (HTML pages, API)
  event.respondWith(
    fetch(request)
      .then((response) => {
        // Cache the latest version
        const responseClone = response.clone();
        caches.open(CACHE_NAME).then((cache) => cache.put(request, responseClone));
        return response;
      })
      .catch(() => {
        console.log('[SW] Network failed, attempting cache fallback for:', request.url);
        return caches.match(request).then((cachedResponse) => {
          if (cachedResponse) {
            return cachedResponse;
          }
          // If it's a navigation request and we have no cache, return the offline page
          if (request.mode === 'navigate') {
            return caches.match('/offline');
          }
          return new Response('Network error happened', { status: 408, headers: { 'Content-Type': 'text/plain' } });
        });
      })
  );
});

// Background Sync Architecture placeholder
self.addEventListener('sync', (event) => {
  if (event.tag === 'sync-profile-updates') {
    console.log('[SW] Background sync triggered for profile updates');
    // Implement retry logic here
  }
});

// Push Notification Architecture placeholder
self.addEventListener('push', (event) => {
  if (event.data) {
    const data = event.data.json();
    console.log('[SW] Push Received:', data);
    const options = {
      body: data.body,
      icon: '/static/favicons/android-chrome-192x192.png',
      badge: '/static/favicons/favicon-32x32.png',
      vibrate: [100, 50, 100],
      data: {
        dateOfArrival: Date.now(),
        primaryKey: '1'
      }
    };
    event.waitUntil(self.registration.showNotification(data.title, options));
  }
});
