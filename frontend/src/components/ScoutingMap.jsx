import { feature } from 'topojson-client';
import world from 'world-atlas/countries-110m.json';

const countries = feature(world, world.objects.countries).features;
const ids = { Chile:'152', Uruguay:'858', Ecuador:'218', Paraguay:'600', Peru:'604', Bolivia:'068', Venezuela:'862', Guyana:'328', Suriname:'740', Egypt:'818', Morocco:'504', Algeria:'012', 'South Africa':'710', Brazil: '076', Argentina: '032', Colombia: '170', England: '826', Scotland: '826', Spain: '724', France: '250', Germany: '276', Portugal: '620', Italy: '380', Netherlands: '528', Belgium: '056', Austria: '040', Switzerland: '756', Denmark: '208', Norway: '578', Sweden: '752', Poland: '616', Romania: '642', Serbia: '688', Croatia: '191', 'Czech Republic': '203', Russia: '643', Ukraine: '804', Greece: '300', Türkiye: '792', Turkey: '792', Japan: '392', 'Korea, South': '410', 'Saudi Arabia': '682', 'United States': '840', Mexico: '484', Australia: '036' };
const viewports = { 'south-america': '90 72 72 81', europe: '155 13 70 49', 'north-america': '6 4 134 91', asia: '205 9 134 91', africa: '155 46 90 86', oceania: '282 93 78 58', '': '0 0 360 180' };
const coordinates = (ring) => {
  let previous = ring[0][0];
  return ring.map(([longitude, latitude], index) => {
    let x = longitude;
    while(x - previous > 180) x -= 360;
    while(x - previous < -180) x += 360;
    previous = x;
    return `${index ? 'L' : 'M'}${(x + 180).toFixed(2)},${(90-latitude).toFixed(2)}`;
  }).join(' ') + 'Z';
};
const path = (geometry) => (geometry.type === 'Polygon' ? [geometry.coordinates] : geometry.coordinates).map(polygon => polygon.map(coordinates).join(' ')).join(' ');
export default function ScoutingMap({ region, country }) {
  return <svg className="scouting-map" viewBox={viewports[region] || viewports['']} role="img" aria-label={`Mapa da missão de scouting: ${country || region || 'Mundo'}`}>
    <defs><pattern id="map-grid" width="8" height="8" patternUnits="userSpaceOnUse"><path d="M8 0H0V8" fill="none" stroke="#386450" strokeWidth=".16" /></pattern></defs>
    <rect x="0" y="0" width="360" height="180" fill="#0a241b" />
    <rect x="0" y="0" width="360" height="180" fill="url(#map-grid)" />
    {countries.map(c => <path key={c.id} d={path(c.geometry)} fill={c.id === ids[country] ? '#39df9a' : '#214636'} stroke={c.id === ids[country] ? '#caffdf' : '#50725e'} strokeWidth=".25"><title>{c.properties.name}</title></path>)}
  </svg>;
}
