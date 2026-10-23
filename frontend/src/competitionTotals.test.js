import { test } from 'node:test';
import assert from 'node:assert/strict';
import { competitionTotals } from './competitionTotals.js';

test('goals stay split by competition and reconcile across seasons',()=>{
  const rows=[{season:'2026',tournaments:[{tournament_id:1,season_id:26,name:'Liga',matches:10,goals:6,assists:2,rating:8,logo:'/liga'},{tournament_id:2,season_id:26,name:'Copa',matches:2,goals:3,assists:1,rating:null}]},{season:'2025',tournaments:[{tournament_id:1,season_id:25,name:'Liga',matches:20,goals:7,assists:3,rating:7}]}];
  const totals=competitionTotals(rows);
  assert.equal(totals.length,2);
  assert.equal(totals[0].goals,13);
  assert.equal(totals[0].logo,'/liga');
  assert.equal(totals[0].matches,30);
  assert.equal(totals[0].rating,220/30);
  assert.equal(totals.reduce((n,t)=>n+t.goals,0),16);
  assert.equal(totals[1].rating,null);
});
test('duplicate source rows and national teams cannot double-count club goals',()=>{
  const t={tournament_id:1,season_id:26,name:'Liga',matches:2,goals:1};
  assert.equal(competitionTotals([{season:'2026',tournaments:[t,t,{...t,tournament_id:2,is_national:true,goals:8}]}])[0].goals,1);
});
