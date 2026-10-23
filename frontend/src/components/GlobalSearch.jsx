import AthletePhoto from './AthletePhoto';
import { useEffect, useRef, useState } from 'react';
import { Search, LoaderCircle } from 'lucide-react';
import { getJSON } from '../lib';
export default function GlobalSearch({ onSelect }) {
  const [query,setQuery]=useState('');
  const [results,setResults]=useState([]);
  const [error,setError]=useState('');
  const [busy,setBusy]=useState(false);
  const [open,setOpen]=useState(false);
  const [active,setActive]=useState(0);
  const container=useRef(null);
  useEffect(()=>{const handle=e=>{if(!container.current?.contains(e.target))setOpen(false);};document.addEventListener('pointerdown',handle);return()=>document.removeEventListener('pointerdown',handle);},[]);
  useEffect(()=>{
    const controller=new AbortController();
    const timer=setTimeout(async()=>{
      setActive(0);setResults([]);setError('');
      if(query.trim().length<3){setBusy(false);setOpen(false);return;}
      setBusy(true);setOpen(true);
      try{setResults(await getJSON('/api/search/suggestions?q='+encodeURIComponent(query),{signal:controller.signal}));}
      catch(e){if(e.name!=='AbortError')setError(e.message);}
      finally{if(!controller.signal.aborted)setBusy(false);}
    },350);
    return()=>{clearTimeout(timer);controller.abort();};
  },[query]);
  function select(p){setOpen(false);setQuery('');onSelect(p);}
  return <div className="global-search" ref={container}><Search size={17}/><input role="combobox" aria-expanded={open} aria-controls="global-results" aria-activedescendant={open&&results[active]?`global-result-${active}`:undefined} aria-label="Buscar jogador no Sofascore" placeholder="Busque um jogador no mundo…" value={query} onChange={e=>setQuery(e.target.value)} onFocus={()=>{if(query.length>=3)setOpen(true);}} onKeyDown={e=>{if(e.key==='Escape')setOpen(false);if(e.key==='ArrowDown'){e.preventDefault();setActive(i=>Math.min(i+1,results.length-1));}if(e.key==='ArrowUp'){e.preventDefault();setActive(i=>Math.max(i-1,0));}if(e.key==='Enter'&&results[active]){e.preventDefault();select(results[active]);}}}/>{busy&&<LoaderCircle className="spin" size={16}/>}
    {open&&<div id="global-results" role="listbox" className="global-results">{error?<p role="alert">{error}</p>:busy?<p>Consultando Sofascore…</p>:!results.length?<p>Nenhum jogador encontrado.</p>:results.map((p,i)=><button role="option" aria-selected={i===active} id={`global-result-${i}`} key={p.id} onClick={()=>select(p)} className={i===active?'active':''}><AthletePhoto player={p} alt=""/><span><strong>{p.name}</strong><small>{p.team}</small></span></button>)}</div>}
  </div>;
}
