import { fallbackPhoto } from '../lib';

// List portraits use the same provider fallback as dossiers, eagerly on mount.
export default function AthletePhoto({ player, src, alt, ...props }) {
  let url = src || player?.photo || fallbackPhoto;
  const sofaId = player?.sofa_id || (player?.tm_id ? null : player?.id);
  if (sofaId && !String(sofaId).startsWith('tm:')) url = `/proxy-image/${sofaId}?v=portrait-v3`;
  else if (url.startsWith('/proxy-image/')) url = url.split('?')[0] + '?v=portrait-v3';
  return <img {...props} src={url} alt={alt ?? player?.name ?? ''} loading="eager" decoding="async" referrerPolicy="no-referrer" onError={event => {
    const image = event.currentTarget;
    if (player?.photo_fallback && image.getAttribute('src') !== player.photo_fallback && image.dataset.fallback !== 'used') {
      image.dataset.fallback = 'used';
      image.src = player.photo_fallback;
    } else {
      image.onerror = null;
      image.src = fallbackPhoto;
    }
  }} />;
}
