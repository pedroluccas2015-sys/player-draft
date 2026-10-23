import { ArrowRight, Activity, Globe2, ShieldCheck } from 'lucide-react';

export default function WelcomeScreen({ onStart }) {
  return <main className="welcome-screen">
    <div className="welcome-grid" aria-hidden="true" />
    <div className="welcome-orbit welcome-orbit-one" aria-hidden="true" />
    <div className="welcome-orbit welcome-orbit-two" aria-hidden="true" />
    <header className="welcome-top"><span>PLAYER DRAFT</span><span>INTELIGÊNCIA PARA O FUTEBOL DE CLUBES</span></header>
    <section className="welcome-content">
      <div className="welcome-logo-wrap"><img src="/player-draft-logo.svg" alt="Logo Player Draft" className="welcome-logo" /></div>
      <p className="eyebrow">O FUTURO DO SEU ELENCO COMEÇA AQUI</p>
      <h1>PLAYER <span>DRAFT</span></h1>
      <p className="welcome-description">Uma nova visão sobre o jogo.<br/>Encontre talentos. Entenda o desempenho. Decida com confiança.</p>
      <button className="welcome-start" onClick={onStart}>Iniciar<ArrowRight size={21}/></button>
      <div className="welcome-features"><span><Globe2 size={15}/>Rede de Scout</span><span><Activity size={15}/>Análise de desempenho</span><span><ShieldCheck size={15}/>Planejamento de elenco</span></div>
    </section>
    <footer className="welcome-footer"><span>OBSERVAR. ANALISAR. CONTRATAR.</span><span>PLAYER DRAFT · CLUB SCOUTING</span></footer>
  </main>;
}
