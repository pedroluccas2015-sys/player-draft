import AthletePhoto from './AthletePhoto';
import { ArrowUpRight, Bookmark, Check, GitCompareArrows } from 'lucide-react';
import { money, positionLabel } from '../lib';
export default function RecruitCard({ player, onOpen, onSave, saved, onCompare, compared }) {
  return <article className="recruit-card">
    <button className="player-portrait" onClick={() => onOpen(player)} aria-label={`Abrir dossiê de ${player.name}`}>
      <AthletePhoto player={player} />
      <span className="position-badge">{positionLabel[player.position_detail] || player.position || 'Atleta'}</span>
      <span className="portrait-arrow"><ArrowUpRight size={18} /></span>
    </button>
    <div className="recruit-body"><p className="eyebrow">{player.club || 'Clube não informado'}</p><button className="player-name" onClick={() => onOpen(player)}>{player.name}</button><p className="player-meta">{player.age != null ? `${player.age} anos` : 'Idade não informada'} · {player.nationality || 'Nacionalidade não informada'}</p>
      <div className="value-row"><span>Valor de mercado</span><strong>{money(player.market_value_eur)}</strong></div>
      <p className="data-note">{player.market_value_source||(player.source==='Sofascore'?'Sofascore':'Transfermarkt')}{player.snapshot_date?' · 06/07/2026':player.market_value_eur!=null?' · estimativa na consulta':' · valor não informado'}</p><div className="card-actions"><button className={saved ? 'saved' : ''} onClick={() => onSave(player)}><Bookmark size={15} fill={saved ? 'currentColor' : 'none'} />{saved ? 'Na lista' : 'Monitorar'}</button><button className={compared ? 'saved' : ''} onClick={() => onCompare(player)} aria-label={`Comparar ${player.name}`}>{compared ? <Check size={15}/> : <GitCompareArrows size={15}/>}Comparar</button></div>
    </div>
  </article>;
}
