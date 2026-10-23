import { useEffect, useRef, useState } from 'react';
import { ArrowRight, ChevronLeft, ChevronRight, Globe2, Search, SlidersHorizontal, RotateCcw } from 'lucide-react';
import ScoutingMap from '../components/ScoutingMap';
import RecruitCard from '../components/RecruitCard';
import { getJSON, positionLabel } from '../lib';

const regions = [['south-america','América do Sul'],['europe','Europa'],['north-america','América do Norte'],['asia','Ásia'],['africa','África'],['oceania','Oceania']];
const names = { Chile:'Chile', Uruguay:'Uruguai', Ecuador:'Equador', Paraguay:'Paraguai', Peru:'Peru', Bolivia:'Bolívia', Venezuela:'Venezuela', Guyana:'Guiana', Suriname:'Suriname', Egypt:'Egito', Morocco:'Marrocos', Algeria:'Argélia', 'South Africa':'África do Sul', Brazil:'Brasil', Argentina:'Argentina', Colombia:'Colômbia', England:'Inglaterra', Scotland:'Escócia', Spain:'Espanha', France:'França', Germany:'Alemanha', Portugal:'Portugal', Italy:'Itália', Netherlands:'Holanda', Belgium:'Bélgica', Austria:'Áustria', Switzerland:'Suíça', Denmark:'Dinamarca', Norway:'Noruega', Sweden:'Suécia', Poland:'Polônia', Romania:'Romênia', Serbia:'Sérvia', Croatia:'Croácia', 'Czech Republic':'Tchéquia', Russia:'Rússia', Ukraine:'Ucrânia', Greece:'Grécia', 'United States':'Estados Unidos', Mexico:'México', Australia:'Austrália', Japan:'Japão', 'Korea, South':'Coreia do Sul', 'Saudi Arabia':'Arábia Saudita', Türkiye:'Turquia' };
const defaults = { region:'south-america',country:'Brazil',position:'',min_value:'',max_value:'',min_age:'',max_age:'',contract:'',foot:'',min_height:'',max_height:'',q:'',sort:'value_desc' };
export default function DiscoveryView({ onOpen, onSave, shortlist, onCompare, compared }) {
  const [filters,setFilters]=useState(defaults);
  const [options,setOptions]=useState(null);
  const [result,setResult]=useState(null);
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState('');
  const [dirty,setDirty]=useState(false);
  const abort=useRef(null);
  const resultsRef=useRef(null);
  useEffect(()=>{ const c=new AbortController();getJSON('/api/scouting/options',{signal:c.signal}).then(setOptions).catch(e=>{if(e.name!=='AbortError')setError(e.message);});return()=>{c.abort();abort.current?.abort();}; },[]);
  function change(key,value) { setFilters(f=>({...f,[key]:value,...(key==='region'?{country:''}:{})}));setDirty(true); }
  async function search(page=1) {
    abort.current?.abort();const c=new AbortController();abort.current=c;
    setBusy(true);setError('');
    try { const data=await getJSON('/api/scouting/search?'+new URLSearchParams({...filters,page}),{signal:c.signal});setResult(data);setDirty(false);resultsRef.current?.scrollIntoView({behavior:'smooth',block:'start'}); }
    catch(e){if(e.name!=='AbortError')setError(e.message);}
    finally{if(!c.signal.aborted)setBusy(false);}
  }
  const countries=options?.metadata.countries.filter(c=>!filters.region||c.region===filters.region)||[];
  const selectedCountry=countries.find(c=>c.country===filters.country);
  const selectionHasData=filters.country?selectedCountry?.has_data:countries.some(c=>c.has_data);
  return <div className="discovery">
    <div className="page-intro"><div><p className="eyebrow">REDE GLOBAL DE SCOUTING</p><h1>O próximo talento.<br/><em>Na sua área de visão.</em></h1></div><p>Defina o mercado. Refine o perfil.<br/>Encontre o próximo reforço do seu clube.</p></div>
    <div className="mission-tabs" role="group" aria-label="Região de observação">{regions.map(([id,label])=><button key={id} className={filters.region===id?'active':''} onClick={()=>change('region',id)}>{label}</button>)}</div>
    <section className="mission-board" aria-label="Missão do olheiro">
      <div className="country-panel"><div className="panel-heading"><Globe2 size={17}/><span>Selecionar país</span><small>{countries.length} mercados</small></div><p className="muted small">País em que o clube atua</p><div className="country-list"><button onClick={()=>change('country','')} className={!filters.country?'active':''}><span>Todos da região</span><ArrowRight size={14}/></button>{countries.map(c=><button key={c.country} onClick={()=>change('country',c.country)} className={filters.country===c.country?'active':''} title={c.league||names[c.country]||c.country}><span>{names[c.country]||c.country}</span><small>{c.has_data?c.count.toLocaleString('pt-BR'):'Sem cobertura'}</small></button>)}{options&&countries.length===0&&<p className="muted">Esta base ainda não cobre clubes desta região.</p>}</div></div>
      <div className="map-panel"><div className="map-heading"><span className="eyebrow">ÁREA DE OBSERVAÇÃO</span><h2>{names[filters.country]||filters.country||regions.find(r=>r[0]===filters.region)?.[1]}</h2>{selectedCountry?.league&&<p className="map-league-name">{selectedCountry.league}</p>}</div><ScoutingMap region={filters.region} country={filters.country}/><div className="map-footer"><span><i/> Rede de Scout · Player Draft</span><span>Mercado de clubes</span></div></div>
      <div className="mission-summary"><div className="scan-icon"><Search size={28}/></div><p className="eyebrow">SUA PRÓXIMA CONTRATAÇÃO</p><h2>Uma missão.<br/>Novas possibilidades.</h2><p className="muted">Combine critérios para encontrar jogadores dentro da estratégia e do orçamento do clube.</p><div className="summary-stat"><strong>{options?.metadata.total.toLocaleString('pt-BR')||'—'}</strong><span>registros recentes de mercado; elencos ampliados por liga</span></div><div className="source-tag">Sofascore + Transfermarkt <span>Elencos por liga · valores com fonte</span></div></div>
    </section>
    {options&&!selectionHasData&&<p className="data-notice" role="status">{selectedCountry?.league?`${selectedCountry.league}: `:''}Os elencos deste país serão consultados na busca. A cobertura financeira depende dos dados publicados pelas fontes.</p>}
    <form className="filter-panel" onSubmit={e=>{e.preventDefault();search();}}><div className="filter-title"><h2><SlidersHorizontal size={18}/> Perfil da contratação</h2><button type="button" className="text-button" onClick={()=>{setFilters(defaults);setDirty(true);}}><RotateCcw size={13}/>Redefinir</button></div>
      <div className="filters-grid">
        <label>Posição<select value={filters.position} onChange={e=>change('position',e.target.value)}><option value="">Todas as posições</option>{options?.positions.map(p=><option key={p} value={p}>{positionLabel[p]||p}</option>)}</select></label>
        <label>Valor mínimo (€)<input type="number" min="0" step="1" placeholder="Sem mínimo" value={filters.min_value} onChange={e=>change('min_value',e.target.value)}/></label>
        <label>Valor máximo (€)<input type="number" min="0" step="1" placeholder="Sem máximo" value={filters.max_value} onChange={e=>change('max_value',e.target.value)}/></label>
        <label>Idade mínima<input type="number" min="0" max="100" placeholder="Qualquer" value={filters.min_age} onChange={e=>change('min_age',e.target.value)}/></label>
        <label>Idade máxima<input type="number" min="0" max="100" placeholder="Qualquer" value={filters.max_age} onChange={e=>change('max_age',e.target.value)}/></label>
        <label>Situação do contrato<select value={filters.contract} onChange={e=>change('contract',e.target.value)}><option value="">Qualquer situação</option><option value="expiring">Vencia até jan/2027 na base</option><option value="long">Válido além de jul/2027 na base</option><option value="free">Registrado sem clube na base</option><option value="unknown">Sem data informada</option></select></label>
        <label>Pé preferido<select value={filters.foot} onChange={e=>change('foot',e.target.value)}><option value="">Ambos os perfis</option><option value="left">Esquerdo</option><option value="right">Direito</option><option value="both">Ambidestro</option></select></label>
        <label>Altura mínima (cm)<input type="number" min="0" placeholder="Qualquer" value={filters.min_height} onChange={e=>change('min_height',e.target.value)}/></label>
        <label>Altura máxima (cm)<input type="number" min="0" placeholder="Qualquer" value={filters.max_height} onChange={e=>change('max_height',e.target.value)}/></label>
        <label>Nome ou clube<input type="search" placeholder="Ex.: Santos" value={filters.q} onChange={e=>change('q',e.target.value)}/></label>
        <label>Ordenar por<select value={filters.sort} onChange={e=>change('sort',e.target.value)}><option value="value_desc">Maior valor de mercado</option><option value="value_asc">Menor valor de mercado</option><option value="age_asc">Mais jovens</option><option value="name">Nome do atleta</option></select></label>
        <button className="primary-button search-mission" disabled={busy||!options}><Search size={17}/>{busy?'Buscando atletas…':'Buscar destaques'}<ArrowRight size={17}/></button>
      </div><p className="data-note">Elencos das ligas consultados no Sofascore, com atualização a cada 6 horas. Valores Transfermarkt de 06/07/2026 quando confirmados; demais estimativas identificadas como Sofascore. Campos desconhecidos não atendem filtros específicos. Idades calculadas hoje.</p>
    </form>
    <section className="search-results" ref={resultsRef} aria-live="polite" aria-busy={busy}>
      {error&&<div role="alert" className="error-panel">{error}</div>}
      {result&&<><div className="results-heading"><div><p className="eyebrow">RELATÓRIO DA MISSÃO</p><h2>{result.coverage_status==='not_covered'?'Mercado ainda sem cobertura':`${result.total.toLocaleString('pt-BR')} atletas encontrados`}</h2></div>{dirty&&<span className="muted">Filtros alterados. Busque novamente para atualizar.</span>}<span className="small muted">Elencos · Sofascore / Mercado · fonte por atleta</span></div>
        <p className="data-note">{result.coverage_notice}</p>{result.leagues?.some(l=>l.failures||l.stale||l.status==='not_covered')&&<p className="data-notice">Consulta parcial em algumas ligas. Apenas os elencos disponíveis foram incluídos.</p>}{result.players.length?<div className="recruit-grid">{result.players.map(p=><RecruitCard key={p.id} player={p} onOpen={onOpen} onSave={onSave} saved={shortlist.some(s=>s.id===p.id||(p.tm_id&&s.tm_id===p.tm_id))} onCompare={onCompare} compared={compared.some(c=>c.id===p.id||(p.tm_id&&c.tm_id===p.tm_id))}/>)}</div>:<div className="empty-state"><Search/><h3>{result.coverage_status==='not_covered'?'Dados deste mercado ainda não disponíveis':'Nenhum atleta com esse perfil na base'}</h3><p>{result.coverage_notice||'Amplie os critérios ou selecione outro país. O catálogo tem cobertura parcial e não representa todos os jogadores do mundo.'}</p></div>}
        {result.total>24&&<div className="pagination"><button disabled={result.page===1||busy||dirty} onClick={()=>search(result.page-1)}><ChevronLeft size={16}/>Anterior</button><span>{result.page} / {Math.ceil(result.total/24)}</span><button disabled={result.page*24>=result.total||busy||dirty} onClick={()=>search(result.page+1)}>Próxima<ChevronRight size={16}/></button></div>}</>}
      {!result&&!error&&<div className="mission-ready"><span className="status-dot"/> Missão pronta. Defina os critérios e busque seus próximos reforços.</div>}
    </section>
  </div>;
}
