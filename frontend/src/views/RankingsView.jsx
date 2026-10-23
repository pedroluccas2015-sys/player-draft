import AthletePhoto from '../components/AthletePhoto';
import { useEffect, useState } from 'react';
import { ArrowUpRight, Trophy } from 'lucide-react';
import { getJSON, number } from '../lib';
const leagues=[['325','Brasileirão'],['17','Premier League'],['8','La Liga'],['23','Serie A · Itália'],['35','Bundesliga'],['34','Ligue 1'],['7','Champions League']];
export default function RankingsView({onPlayerClick}) {
  const [league,setLeague]=useState('325');
  const [position,setPosition]=useState('all');
  const [query,setQuery]=useState('');
  const [state,setState]=useState({loading:true,data:null,error:''});
  useEffect(()=>{
    const controller=new AbortController();
    getJSON(`/api/rankings?league_id=${league}&position=${position}`,{signal:controller.signal}).then(data=>setState({loading:false,data,error:''})).catch(e=>{if(e.name!=='AbortError')setState({loading:false,data:null,error:e.message});});
    return()=>controller.abort();
  },[league,position]);
  const rows=(state.data?.players||[]).filter(p=>(p.name+' '+p.team).toLowerCase().includes(query.toLowerCase()));
  function change(setter,value,current){if(current===value)return;setter(value);setState({loading:true,data:null,error:''});}
  return <div><div className="league-tabs">{leagues.map(([id,label])=><button key={id} onClick={()=>change(setLeague,id,league)} className={id===league?'active':''}>{label}</button>)}</div><div className="ranking-filters"><label>Posição<select value={position} onChange={e=>change(setPosition,e.target.value,position)}>{[['all','Todas as posições'],['G','Goleiros'],['D','Defensores'],['M','Meio-campistas'],['F','Atacantes']].map(([id,label])=><option key={id} value={id}>{label}</option>)}</select></label><label>Nome ou clube<input type="search" value={query} onChange={e=>setQuery(e.target.value)} placeholder="Filtrar resultados"/></label><p className="muted small">Top 5 por nota<br/>Temporada: {state.data?.season||'—'}<br/>Mínimo de partidas: {state.data?.minimum_matches||'—'}</p></div>{state.loading?<div className="empty-state" role="status">Consultando o ranking Sofascore…</div>:state.error?<div className="error-panel" role="alert">{state.error}</div>:rows.length?<><div className="ranking-list">{rows.map((p,i)=><button className="ranking-row" key={p.id} onClick={()=>onPlayerClick(p.name,p.id)}><span className="ranking-number">{i<3?<Trophy size={19}/>:String(i+1).padStart(2,'0')}</span><AthletePhoto player={p} alt={p.name}/><span className="ranking-name"><strong>{p.name}</strong><small>{p.team}</small></span><span className="ranking-stat">{number(p.matches)}<small>jogos</small></span><span className="ranking-stat">{number(p.goals)}<small>gols</small></span><span className="ranking-stat">{number(p.assists)}<small>assist.</small></span><span className="rating-badge">{number(p.rating,2)}</span><ArrowUpRight size={18}/></button>)}</div><p className="data-note">{state.data?.notice}</p></>:<div className="empty-state"><Trophy/><h2>Nenhum atleta neste recorte</h2><p>A fonte não retornou notas disponíveis para esta posição nas temporadas consultadas.</p></div>}</div>;
}
