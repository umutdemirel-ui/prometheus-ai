export function validateMessages(messages) {
  if (!Array.isArray(messages) || !messages.length || messages.length > 40) throw new Error('Geçersiz sohbet bağlamı.');
  return messages.map(m => {
    if (!['user', 'assistant'].includes(m.role) || typeof m.content !== 'string' || !m.content.trim() || m.content.length > 12000) throw new Error('Geçersiz mesaj.');
    return { role: m.role, content: m.content };
  });
}
export function validateModel(model) {
  if (typeof model !== 'string' || !/^[a-zA-Z0-9._:/-]{1,150}$/.test(model)) throw new Error('Geçersiz model adı.');
  return model;
}
export function safeError(status) {
  if (status === 401 || status === 403) return 'Sağlayıcı kimlik doğrulaması başarısız. Sunucu yapılandırmasını kontrol edin.';
  if (status === 404) return 'Model veya sağlayıcı uç noktası bulunamadı.';
  if (status === 429) return 'Sağlayıcı kotası veya istek sınırı aşıldı.';
  return 'Sağlayıcıya ulaşılamadı veya sağlayıcı hata döndürdü.';
}
export function wikiUrl(query) {
  const url = new URL('https://tr.wikipedia.org/w/api.php');
  url.search = new URLSearchParams({action:'query',generator:'search',gsrsearch:query,gsrlimit:'5',prop:'extracts|info',exintro:'1',explaintext:'1',inprop:'url',format:'json',formatversion:'2'}).toString();
  return url;
}
