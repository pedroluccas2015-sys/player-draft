// Aggregate the same source rows used by the season totals, once per competition/season.
export function competitionTotals(stats) {
  const groups=new Map(),seen=new Set();
  for(const season of stats)for(const t of season.tournaments||[]){
    const key=`${t.tournament_id}:${t.season_id}`;
    if(t.is_national||seen.has(key))continue;
    seen.add(key);
    const row=groups.get(t.tournament_id)||{...t,season_id:null,matches:0,goals:0,assists:0,minutes:0,seasons:[],weighted:0,ratedMatches:0};
    for(const field of ['matches','goals','assists','minutes'])row[field]+=Number(t[field])||0;
    if(t.rating!=null&&t.matches>0){row.weighted+=t.rating*t.matches;row.ratedMatches+=t.matches;}
    if(!row.seasons.includes(season.season))row.seasons.push(season.season);
    groups.set(t.tournament_id,row);
  }
  return [...groups.values()].map(r=>({...r,rating:r.ratedMatches?r.weighted/r.ratedMatches:null})).sort((a,b)=>b.goals-a.goals||b.matches-a.matches||a.name.localeCompare(b.name));
}
