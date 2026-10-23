export const money = (value) => value == null ? 'Não informado' : new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'EUR', notation: 'compact', maximumFractionDigits: 1 }).format(value);
export const number = (value, digits = 0) => value == null ? '—' : Number(value).toLocaleString('pt-BR', { maximumFractionDigits: digits });
export const date = (value) => value ? new Date(value.slice(0, 10) + 'T12:00:00').toLocaleDateString('pt-BR') : 'Não informado';
export const fallbackPhoto = '/player-placeholder.svg';
export function photoFallback(event) { event.currentTarget.onerror = null; event.currentTarget.src = fallbackPhoto; }
export async function getJSON(url, options = {}) {
  const response = await fetch(url, options);
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || 'Não foi possível carregar os dados.');
  return data;
}
export const positionLabel = { 'Goalkeeper': 'Goleiro', 'Centre-Back': 'Zagueiro', 'Left-Back': 'Lateral esquerdo', 'Right-Back': 'Lateral direito', 'Defensive Midfield': 'Volante', 'Central Midfield': 'Meia central', 'Attacking Midfield': 'Meia ofensivo', 'Left Midfield': 'Meia esquerdo', 'Right Midfield': 'Meia direito', 'Left Winger': 'Ponta esquerda', 'Right Winger': 'Ponta direita', 'Centre-Forward': 'Centroavante', 'Second Striker': 'Segundo atacante', 'midfield': 'Meio-campo', 'defence': 'Defesa', 'attack': 'Ataque' };
