/* Transkripsiya sahifasining service worker'i — faqat «Ulashish» (Web Share Target) uchun.
   Telefonda Telegram, Galereya va boshqa ilovalarning «Ulashish» menyusidan yuborilgan fayl yoki
   havola shu yerga POST bo'lib keladi: uni vaqtincha keshga qo'yib, sahifani ochamiz — sahifa
   o'zi oladi va keshni tozalaydi. Boshqa so'rovlarga tegilmaydi (keshlash yo'q). */
const ULASHISH = "ulashish";

self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", e => e.waitUntil(self.clients.claim()));

self.addEventListener("fetch", e => {
  const url = new URL(e.request.url);
  if (e.request.method !== "POST" || !url.searchParams.has("ulashish")) return;
  e.respondWith((async () => {
    try {
      const fd = await e.request.formData();
      const fayllar = fd.getAll("fayl").filter(f => f && typeof f === "object" && f.size > 0);
      const matn = ["title", "text", "url"].map(k => fd.get(k)).filter(x => typeof x === "string" && x.trim()).join(" ");
      await caches.delete(ULASHISH);
      const c = await caches.open(ULASHISH);
      await Promise.all(fayllar.map((f, i) => c.put(`ulashish/fayl-${i}`, new Response(f, {
        headers: { "content-type": f.type || "application/octet-stream", "x-nom": encodeURIComponent(f.name || "") },
      }))));
      await c.put("ulashish/meta", new Response(JSON.stringify({ n: fayllar.length, matn })));
    } catch (x) { /* sahifa «hech narsa kelmadi» deydi */ }
    return Response.redirect("./index.html?ulashildi", 303);
  })());
});
