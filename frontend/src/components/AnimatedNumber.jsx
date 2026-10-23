import useReducedMotion from '../hooks/useReducedMotion';
import { useEffect, useRef } from 'react';
import { number } from '../lib';

export default function AnimatedNumber({ value, digits=0, duration=1000 }) {
  const ref=useRef(null);
  const reduced=useReducedMotion();
  useEffect(()=>{
    if(reduced||value==null||!Number.isFinite(Number(value)))return;
    let frame;
    let start;
    const animate=time=>{
      if(!ref.current)return;
      start ??= time;
      const progress=Math.min(1,(time-start)/duration);
      const eased=1-Math.pow(1-progress,3);
      ref.current.textContent=number(Number(value)*eased,digits);
      if(progress<1)frame=requestAnimationFrame(animate);
    };
    frame=requestAnimationFrame(animate);
    return()=>cancelAnimationFrame(frame);
  },[value,digits,duration,reduced]);
  return <span aria-label={number(value,digits)}><span ref={ref} aria-hidden="true">{number(value,digits)}</span></span>;
}
