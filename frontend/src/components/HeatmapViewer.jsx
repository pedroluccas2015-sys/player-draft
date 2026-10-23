import { useEffect, useId, useState } from 'react';
import { getJSON } from '../lib';
export default function HeatmapViewer({playerId,tournamentId,seasonId,tournamentName}) {
 const [state,setState]=useState({loading:true,data:null,error:''});
 const gradient=useId().replaceAll(':','');
 useEffect(()=>{
  const controller=new AbortController();
  getJSON(`/api/heatmap/${playerId}/${tournamentId}/${seasonId}`,{signal:controller.signal}).then(data=>setState({loading:false,data,error:''})).catch(e=>{if(e.name!=='AbortError')setState({loading:false,data:null,error:e.message});});return()=>controller.abort();
 },[playerId,tournamentId,seasonId]);
 const points=(state.data?.points||[]).filter(p=>Number.isFinite(p.x)&&Number.isFinite(p.y)&&p.x>=0&&p.x<=100&&p.y>=0&&p.y<=100);
 const max=Math.max(1,...points.map(p=>p.count||1));
 return <section className="heatmap-panel"><h4>Mapa de calor · {tournamentName}</h4>{state.loading?<p className="muted small" role="status">Consultando posicionamento do atleta…</p>:state.error?<p className="data-notice">Mapa indisponível: {state.error}</p>:!points.length?<p className="data-notice">A fonte não retornou pontos de posicionamento para este recorte.</p>:<svg viewBox="0 0 100 65" role="img" aria-label={`Mapa de calor de ${tournamentName}`}><defs><radialGradient id={gradient}><stop offset="0" stopColor="#fff59d" stopOpacity=".95"/><stop offset=".3" stopColor="#ff753d" stopOpacity=".7"/><stop offset="1" stopColor="#e7f58f" stopOpacity="0"/></radialGradient></defs><rect width="100" height="65" fill="#1a6744"/>{points.map((p,i)=><circle key={i} cx={p.x} cy={(100-p.y)*.65} r={2+((p.count||1)/max)*3} fill={`url(#${gradient})`}/>)}<g fill="none" stroke="#e0fae6" strokeWidth=".35" opacity=".8"><rect x=".5" y=".5" width="99" height="64"/><path d="M50 0V65 M0 13.5H16.5V51.5H0 M100 13.5H83.5V51.5H100 M0 23.5H5.5V41.5H0 M100 23.5H94.5V41.5H100"/><circle cx="50" cy="32.5" r="9"/></g></svg>}<p className="data-note">Posicionamento agregado da competição, conforme os pontos disponíveis no Sofascore.</p></section>;
}
