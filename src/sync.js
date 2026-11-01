// Only explicitly selected, non-secret UI preferences may cross devices.
const safeSettings = {
  theme: v => ['dark','light'].includes(v),
  accent: v => typeof v === 'string' && /^#[a-f0-9]{6}$/i.test(v),
  fontSize: v => Number.isInteger(v) && v >= 12 && v <= 18,
  animations: v => typeof v === 'boolean',
  voice: v => typeof v === 'boolean',
  rate: v => typeof v === 'number' && Number.isFinite(v) && v >= .5 && v <= 2,
  language: v => v === 'tr-TR',
  showActivity: v => typeof v === 'boolean'
};
export function pickSyncSettings(settings) {
  const result = {};
  for (const [key, valid] of Object.entries(safeSettings)) if (valid(settings?.[key])) result[key] = settings[key];
  return result;
}
export function toSnapshot(conversation) {
  if (!conversation || typeof conversation.title !== 'string' || !conversation.title.trim() || conversation.title.length > 200 || !Array.isArray(conversation.messages) || !conversation.messages.length || conversation.messages.length > 200) throw new Error('Sohbet buluta kaydedilemeyecek kadar uzun veya geçersiz.');
  return conversation.messages.map(m => {
    if (!['user','assistant'].includes(m.role) || typeof m.content !== 'string' || !m.content.trim() || m.content.length > 100000) throw new Error('Sohbette geçersiz veya çok uzun bir mesaj var.');
    return {role:m.role,content:m.content};
  });
}
export function importSnapshot(row) {
  const messages = (row.messages || []).slice().sort((a,b) => (a.position ?? 0) - (b.position ?? 0)).map(({role,content})=>({role,content}));
  toSnapshot({title:row.title,messages});
  return {id:`cloud-${row.id}`,cloudId:row.id,synced:true,title:row.title,date:row.created_at,messages};
}
export async function uploadSnapshot(client, cloudId, conversation) {
  const snapshot_messages = toSnapshot(conversation);
  const {error} = await client.rpc('save_conversation_snapshot',{snapshot_id:cloudId,snapshot_title:conversation.title,snapshot_messages});
  if (error) throw new Error('Sohbet buluta kaydedilemedi. Migration ve bağlantıyı kontrol edin.');
}
export async function loadSnapshots(client) {
  const {data,error} = await client.from('conversations').select('id,title,created_at,messages!messages_owner_parent_fk(role,content,position)').order('created_at',{ascending:false}).limit(100);
  if (error) throw new Error('Bulut sohbetleri yüklenemedi. Migration ve bağlantıyı kontrol edin.');
  return data || [];
}
export async function uploadPreferences(client, userId, settings) {
  const {error} = await client.from('user_preferences').upsert({user_id:userId,settings:pickSyncSettings(settings),updated_at:new Date().toISOString()});
  if (error) throw new Error('Tercihler buluta kaydedilemedi.');
}
export async function loadPreferences(client,userId) {
  const {data,error} = await client.from('user_preferences').select('settings').eq('user_id',userId).maybeSingle();
  if (error) throw new Error('Bulut tercihleri yüklenemedi.');
  return data ? pickSyncSettings(data.settings) : null;
}
