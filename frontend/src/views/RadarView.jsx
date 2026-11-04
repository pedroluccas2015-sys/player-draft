import { useCallback, useEffect, useState } from 'react';
import { ArrowUpRight, CalendarDays, Radio } from 'lucide-react';
import { getJSON } from '../lib';
import MatchCenter from '../components/MatchCenter';
const leagues=[['bra.1','Brasileirão'],['eng.1','Premier League'],['ita.1','Serie A · Itália'],['esp.1','La Liga'],['ger.1','Bundesliga'],['fra.1','Ligue 1'],['por.1','Liga Portugal'],['uefa.champions','Champions League'],['conmebol.libertadores','Libertadores'],['conmebol.sudamericana','Sul-Americana'],['usa.1','MLS']];
export default function RadarView({onTeamClick,onPlayerClick}) {
 const [selectedMatch,setSelectedMatch]=useState(null);
 const closeMatch=useCallback(()=>setSelectedMatch(null),[]);
 const [league,setLeague]=useState('bra.1');
 const [tab,setTab]=useState('recent');
 const [state,setState]=useState({loading:true,data:null,error:''});
 const [checked,setChecked]=useState(null);
 useEffect(()=>{
  const controller=new AbortController();
  let pending=false;
  setChecked(null);
  async function refresh(){
   if(pending || document.hidden)return;
   pending=true;
   try{
    const data=await getJSON('/api/scoreboard?league='+league,{signal:controller.signal,cache:'no-store'});
    if(!controller.signal.aborted){setState({loading:false,data,error:''});setChecked(new Date(data.updated_at || Date.now()));}
   }catch(e){if(!controller.signal.aborted)setState(s=>({...s,loading:false,error:e.message}));}
   finally{pending=false;}
  }
  refresh();
  const timer=setInterval(refresh,15000);
  document.addEventListener('visibilitychange',refresh);
  window.addEventListener('focus',refresh);
  return()=>{controller.abort();clearInterval(timer);document.removeEventListener('visibilitychange',refresh);window.removeEventListener('focus',refresh);};
 },[league]);
 const rows=(tab==='recent'?state.data?.matches:state.data?.upcoming)||[];
 return <div>{selectedMatch&&<MatchCenter key={`${league}:${selectedMatch.id}`} match={selectedMatch} league={league} onClose={closeMatch} onPlayerClick={onPlayerClick}/>}<div className="league-tabs">{leagues.map(([id,label])=><button key={id} className={league===id?'active':''} onClick={()=>{if(id===league)return;setLeague(id);setState({loading:true,data:null,error:''});}}>{label}</button>)}</div><div className="radar-toolbar"><div className="season-selector"><button className={tab==='recent'?'active':''} onClick={()=>setTab('recent')}><Radio size={13}/>Resultados e ao vivo</button><button className={tab==='upcoming'?'active':''} onClick={()=>setTab('upcoming')}><CalendarDays size={13}/>Próximos jogos</button></div><p className="muted small">{checked?'Consultado às '+checked.toLocaleTimeString('pt-BR'):'Consultando ESPN…'}</p></div>{state.error&&<div className="error-panel" role="alert">{state.error}</div>}{state.loading?<div className="empty-state" role="status">Carregando calendário ESPN…</div>:rows.length?<div className="match-grid">{rows.map(m=><article key={m.id} className="match-card"><div className="match-status"><span>{m.is_live?'● AO VIVO · ':''}{m.short_status}</span><small>{m.date}</small></div><div className="match-teams"><button onClick={()=>onTeamClick(m.home_team)} aria-label={'Ver elenco do '+m.home_team}>{m.home_logo&&<img src={m.home_logo} alt="" onError={e=>{e.currentTarget.style.visibility='hidden';}}/>}<strong>{m.home_team}</strong></button><div className="match-score">{tab==='upcoming'?<span>×</span>:<><strong>{m.home_score}</strong><span>:</span><strong>{m.away_score}</strong></>}</div><button onClick={()=>onTeamClick(m.away_team)} aria-label={'Ver elenco do '+m.away_team}>{m.away_logo&&<img src={m.away_logo} alt="" onError={e=>{e.currentTarget.style.visibility='hidden';}}/>}<strong>{m.away_team}</strong></button></div><div className="match-scorers">{[...(m.home_scorers||[]),...(m.away_scorers||[])].map((p,i)=><button key={i} disabled={!p.radar_context?.club} title={p.radar_context?.club?`Ver ${p.name} no elenco de ${p.radar_context.club}`:'Identidade do time indisponível'} onClick={()=>onPlayerClick(p)}>{p.time} {p.name}{p.is_own?' (contra)':''}<ArrowUpRight size={11}/></button>)}</div><button className="match-analyze-button" onClick={()=>setSelectedMatch(m)}>Analisar partida · estatísticas e campo ↗</button></article>)}</div>:<div className="empty-state"><CalendarDays/><h2>Nenhum jogo retornado neste período</h2><p>Selecione outra liga ou consulte a aba de próximos jogos.</p></div>}<p className="data-note">Calendário ESPN do mês anterior, atual e seguinte. Todos os jogos ao vivo têm prioridade. Placares consultados a cada 15 segundos enquanto esta tela estiver aberta; a atualização depende da ESPN. Os links de clubes e atletas consultam o Sofascore.</p></div>;
}
