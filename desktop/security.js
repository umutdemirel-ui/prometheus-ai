export function sameOrigin(url, origin) { try {return new URL(url).origin===origin} catch{return false} }
export function allowMediaCheck({permission,requestingOrigin,origin,mediaType}) {
 return permission==='media' && requestingOrigin===origin && (!mediaType || mediaType==='audio');
}
export function allowAudioRequest({permission,pageUrl,requestingUrl,origin,mediaTypes}) {
 return permission==='media' && sameOrigin(pageUrl,origin) && (!requestingUrl || sameOrigin(requestingUrl,origin)) && Array.isArray(mediaTypes) && mediaTypes.includes('audio') && !mediaTypes.includes('video');
}
export function safeExternalUrl(url) {try{return new URL(url).protocol==='https:'}catch{return false}}
