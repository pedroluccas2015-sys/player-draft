import { useEffect, useState } from 'react';
export default function useReducedMotion() {
  const [reduced,setReduced]=useState(()=>window.matchMedia('(prefers-reduced-motion: reduce)').matches);
  useEffect(()=>{
    const media=window.matchMedia('(prefers-reduced-motion: reduce)');
    const change=event=>setReduced(event.matches);
    media.addEventListener('change',change);
    return()=>media.removeEventListener('change',change);
  },[]);
  return reduced;
}

