const CACHE = "bobify-v2"; // Поменяли версию, чтобы сбросить старый кэш

self.addEventListener("install", e => {
  self.skipWaiting();
});

self.addEventListener("activate", e => {
  e.waitUntil(
    caches.keys().then(keys => {
      return Promise.all(keys.filter(key => key !== CACHE).map(key => caches.delete(key)));
    }).then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", e => {
  const url = new URL(e.request.url);

  // ГЛАВНОЕ ИСПРАВЛЕНИЕ: Не кэшируем запросы к серверу (поиск, музыка, скачивание)
  if (url.pathname.startsWith('/search') || 
      url.pathname.startsWith('/stream_url') || 
      url.pathname.startsWith('/download') || 
      url.pathname.startsWith('/play')) {
    return; // Пропускаем запрос напрямую в интернет
  }

  // Кэшируем только оболочку сайта (кнопки, дизайн)
  if (e.request.method !== "GET") return;
  e.respondWith(
    caches.match(e.request).then(r => r || fetch(e.request))
  );
});
