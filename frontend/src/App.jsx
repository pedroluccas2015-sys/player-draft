import { lazy, Suspense, useCallback, useRef, useState } from 'react';
import { Bookmark, Globe2, Radar, BarChart3, GitCompareArrows, X, ArrowUpRight } from 'lucide-react';
import DiscoveryView from './views/DiscoveryView';
import RadarView from './views/RadarView';
import RankingsView from './views/RankingsView';
const PlayerDossier=lazy(()=>import('./components/PlayerDossier'));
import RecruitCard from './components/RecruitCard';
import GlobalSearch from './components/GlobalSearch';
import { getJSON, money, number } from './lib';
import WelcomeScreen from './components/WelcomeScreen';
import AthletePhoto from './components/AthletePhoto';
import './club.css';

const tabs = [['discover','Rede de Scout',Globe2],['shortlist','Lista de interesse',Bookmark],['compare','Comparar atletas',GitCompareArrows],['radar','Radar de ligas',Radar],['rankings','Destaques por liga',BarChart3]];
const identity = p => p.tm_id ? `tm:${p.tm_id}` : `sofa:${p.sofa_id || p.id}`;
function loadShortlist() { try { const v=JSON.parse(localStorage.getItem('player-draft-shortlist-v1')||'[]');return Array.isArray(v)?v.filter(p=>p&&p.id&&p.name):[]; } catch { return []; } }
export default function App() {
  const [started,setStarted]=useState(false);
  const [tab,setTab]=useState('discover');
  const [shortlist,setShortlist]=useState(loadShortlist);
  const [compared,setCompared]=useState([]);
  const [selected,setSelected]=useState(null);
  const [loading,setLoading]=useState(false);
  const [error,setError]=useState('');
  const [clubPlayers,setClubPlayers]=useState(null);
  const requestId=useRef(0);
  async function openPlayer(p) {
    const id=++requestId.current;setLoading(true);setError('');
    try {
      const profile=await getJSON('/api/search',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(p.sofa_id?{player_id:p.sofa_id,league_id:p.league_id,league_name:p.league_name}:p.tm_id?{tm_id:p.tm_id}:{player_id:p.id,player_name:p.name})});
      if(id===requestId.current)setSelected(profile);
    } catch(e){if(id===requestId.current)setError(e.message);}
    finally{if(id===requestId.current)setLoading(false);}
  }
  function save(p) {
    setShortlist(previous=>{
      const next=previous.some(s=>identity(s)===identity(p))?previous.filter(s=>identity(s)!==identity(p)):[p,...previous];
      try{localStorage.setItem('player-draft-shortlist-v1',JSON.stringify(next));}catch{setError('A lista está nesta sessão, mas o navegador não permitiu salvá-la para a próxima visita.');}
      return next;
    });
  }
  async function compare(p) {
    if(compared.some(s=>identity(s)===identity(p))){setCompared(previous=>previous.filter(s=>identity(s)!==identity(p)));return;}
    if(compared.length>=2){setError('Remova um atleta da comparação antes de selecionar outro.');return;}
    let profile=p;
    if(!p.is_full_profile){
      const id=++requestId.current;setLoading(true);setError('');
      try{profile=await getJSON('/api/search',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(p.sofa_id?{player_id:p.sofa_id,league_id:p.league_id,league_name:p.league_name}:p.tm_id?{tm_id:p.tm_id}:{player_id:p.id,player_name:p.name})});if(id!==requestId.current)return;}
      catch(e){if(id===requestId.current)setError(e.message);return;}
      finally{if(id===requestId.current)setLoading(false);}
    }
    setCompared(previous=>previous.some(s=>identity(s)===identity(profile))||previous.length>=2?previous:[...previous,profile]);
  }
  const closeDossier=useCallback(()=>setSelected(null),[]);
  async function openClub(name) {
    setLoading(true);setError('');
    try {
      const clubs=await getJSON('/api/clubs/search?q='+encodeURIComponent(typeof name==='string'?name:name.name));
      if(!clubs.length)throw new Error('Clube não identificado. Busque os jogadores pelo nome.');
      const club=clubs.find(c=>c.name.toLowerCase()===(typeof name==='string'?name:name.name).toLowerCase())||clubs[0];
      const result=await getJSON('/api/team-squad?id='+club.id);
      setClubPlayers({name:club.name,players:result.squad||[]});
    }catch(e){setError(e.message);}finally{setLoading(false);}
  }
  const card=p=><RecruitCard key={identity(p)} player={p} onOpen={openPlayer} onSave={save} saved={shortlist.some(s=>identity(s)===identity(p))} onCompare={compare} compared={compared.some(s=>identity(s)===identity(p))}/>;
  if(!started)return <WelcomeScreen onStart={()=>setStarted(true)}/>;
  return <div className="club-app">
    <aside className="club-sidebar"><a className="brand" href="#" onClick={e=>{e.preventDefault();setTab('discover');}} aria-label="Player Draft - início"><span className="brand-mark">PD<span>↗</span></span><span>PLAYER<br/><strong>DRAFT</strong></span></a><div className="club-context"><span className="status-dot"/><span>DEPARTAMENTO DE FUTEBOL</span></div><p className="nav-label">CENTRAL DE RECRUTAMENTO</p><nav aria-label="Navegação principal">{tabs.map(([id,label,Icon])=><button key={id} aria-label={label} title={label} onClick={()=>setTab(id)} className={tab===id?'active':''}><Icon size={18}/><span>{label}</span>{id==='shortlist'&&<small>{shortlist.length}</small>}{id==='compare'&&<small>{compared.length}/2</small>}</button>)}</nav><div className="sidebar-bottom"><Globe2 size={20}/><strong>O talento não tem fronteiras.</strong><p>Uma nova perspectiva para cada contratação.</p><span>PLAYER DRAFT · CLUB SCOUTING</span></div></aside>
    <main className="club-main"><header className="club-topbar"><div className="breadcrumb">Player Draft <span>/</span> <strong>{tabs.find(t=>t[0]===tab)?.[1]}</strong></div><GlobalSearch onSelect={openPlayer}/><span className="live-label"><span className="status-dot"/>FUTEBOL DE CLUBES</span></header><div className="club-content">
      <div hidden={tab!=='discover'}><DiscoveryView onOpen={openPlayer} onSave={save} shortlist={shortlist} onCompare={compare} compared={compared}/></div>
      {tab==='shortlist'&&<><div className="section-intro"><p className="eyebrow">PLANEJAMENTO DO ELENCO</p><h1>Lista de interesse<span>.</span></h1><p className="muted">{shortlist.length} atletas monitorados. A lista fica salva neste navegador.</p></div><div className="budget-strip"><span>Soma dos valores conhecidos <strong>{money(shortlist.reduce((v,p)=>v+(p.market_value_eur||0),0))}</strong></span><p>Estimativas da base Transfermarkt de 06/07/2026; não representam propostas de compra. {shortlist.filter(p=>p.market_value_eur==null).length} atleta(s) sem valor informado.</p></div>{shortlist.length?<div className="recruit-grid">{shortlist.map(card)}</div>:<div className="empty-state"><Bookmark/><h2>Seu próximo reforço começa aqui</h2><p>Use “Monitorar” em um atleta para adicioná-lo à lista.</p><button className="primary-button" onClick={()=>setTab('discover')}>Explorar mercados<ArrowUpRight size={16}/></button></div>}</>}
      {tab==='compare'&&<><div className="section-intro"><p className="eyebrow">DECISÃO COM CONTEXTO</p><h1>Comparar atletas<span>.</span></h1><p className="muted">Selecione até dois jogadores. Abra os dossiês para consultar as estatísticas atualizadas.</p></div>{compared.length?<div className="comparison-grid">{compared.map(p=><div key={identity(p)} className="comparison-player"><button className="remove-compare" onClick={()=>compare(p)} aria-label={'Remover '+p.name+' da comparação'}><X size={18}/></button><AthletePhoto player={p}/><h2>{p.name}</h2><p className="muted">{p.club}</p><dl>{[['Idade',p.age!=null?p.age+' anos':'—'],['Posição',p.position_detail||p.position],['Valor de mercado',money(p.market_value_eur)],['Nota atual no Sofascore',number(p.rating,2)],...Object.entries(p.attributes||{}).map(([k,v])=>[k,number(v,2)])].map(([label,value])=><div key={label}><dt>{label}</dt><dd>{value||'—'}</dd></div>)}</dl><button className="primary-button" onClick={()=>openPlayer(p)}>Analisar dossiê<ArrowUpRight size={16}/></button></div>)}</div>:<div className="empty-state"><GitCompareArrows/><h2>Coloque duas oportunidades lado a lado</h2><p>Selecione “Comparar” nos cartões dos atletas.</p></div>}</>}
      {tab==='radar'&&<><div className="section-intro"><p className="eyebrow">ACOMPANHAMENTO DE COMPETIÇÕES</p><h1>Radar de ligas<span>.</span></h1><p className="muted">Resultados e próximos jogos · ESPN · atualização a cada 60 segundos</p></div><RadarView onTeamClick={openClub} onPlayerClick={name=>openPlayer({name})}/></>}
      {tab==='rankings'&&<><div className="section-intro"><p className="eyebrow">DESEMPENHO NA TEMPORADA</p><h1>Destaques por liga<span>.</span></h1><p className="muted">Os cinco atletas com maior nota em cada recorte · Sofascore. Clique para analisar.</p></div><RankingsView onPlayerClick={(name,id)=>openPlayer({name,id})}/></>}
    </div><footer className="app-footer"><span>PLAYER DRAFT</span><span>Estatísticas · Sofascore &nbsp; / &nbsp; Competições · ESPN &nbsp; / &nbsp; Mercado · Transfermarkt (base de 06/07/2026)</span></footer></main>
    {loading&&<div className="loading-overlay" role="status"><div className="loading-spinner"/><strong>Preparando o dossiê</strong><p>Consultando estatísticas e confirmando o atleta nas fontes…</p><button onClick={()=>{requestId.current++;setLoading(false);}} className="text-button">Cancelar visualização</button></div>}
    {error&&<div className="error-toast" role="alert"><span>{error}</span><button onClick={()=>setError('')} aria-label="Fechar aviso"><X size={18}/></button></div>}
    {selected&&<Suspense fallback={<div className="loading-overlay" role="status">Abrindo dossiê…</div>}><PlayerDossier key={identity(selected)} player={selected} onClose={closeDossier} saved={shortlist.some(p=>identity(p)===identity(selected))} onSave={save} onCompare={p=>{compare(p);setSelected(null);setTab('compare');}}/></Suspense>}
    {clubPlayers&&<div className="modal-backdrop" onClick={()=>setClubPlayers(null)}><section className="club-roster" role="dialog" aria-modal="true" aria-label={'Elenco do '+clubPlayers.name} onClick={e=>e.stopPropagation()}><button className="close-modal" onClick={()=>setClubPlayers(null)} aria-label="Fechar elenco"><X/></button><p className="eyebrow">ELENCO DO CLUBE · SOFASCORE</p><h2>{clubPlayers.name}</h2>{clubPlayers.players.length?clubPlayers.players.map(p=><button key={p.id} className="roster-player" onClick={()=>{setClubPlayers(null);openPlayer(p);}}><AthletePhoto player={p}/><span>{p.name}</span><small>{p.position}</small><ArrowUpRight size={16}/></button>):<p className="muted">Nenhum atleta retornado pela fonte.</p>}</section></div>}
  </div>;
}
