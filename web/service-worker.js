const filesToCache = [
   '/',
   'index.html',
];

const dynamicCacheName = 'pages-cache-v1';

// Listen for install event, set callback
self.addEventListener('install', event => {
   console.log('Attempting to install service worker and cache static assets');
   event.waitUntil(
      caches.open(dynamicCacheName)
      .then(cache => {
         return cache.addAll(filesToCache);
      })
   );
});

// Serve files from the cache
self.addEventListener('fetch', function(event) {
   event.respondWith(
      caches.open(dynamicCacheName).then(function(cache) {
         return cache.match(event.request).then(function(response) {
            var fetchPromise = fetch(event.request).then(function(networkResponse) {
               cache.put(event.request, networkResponse.clone());
               return networkResponse;
            })
            return response || fetchPromise;
         })
      })
   );
});

// Cleanup caches
self.addEventListener('activate', function(event) {
   event.waitUntil(
      caches.keys().then(function(cacheNames) {
         return Promise.all(
            cacheNames.filter(function(cacheName) {
               // Return true if you want to remove this cache,
               // but remember that caches are shared across
               // the whole origin
            }).map(function(cacheName) {
               return caches.delete(cacheName);
            })
         );
      })
   );
});

// vim: sw=3:sts=3:expandtab
