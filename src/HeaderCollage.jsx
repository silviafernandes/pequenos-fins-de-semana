import React, {useEffect,useState} from 'react'
import {RefreshCw} from 'lucide-react'
import {collages,nextCollage} from './collages.js'

export default function HeaderCollage(){
  const [selected,setSelected]=useState(()=>{
    let previous=-1
    try {const stored=sessionStorage.getItem('pfds-header-collage');if(stored!==null)previous=Number(stored)} catch {}
    return nextCollage(previous)
  })
  useEffect(()=>{try{sessionStorage.setItem('pfds-header-collage',String(selected))}catch{}},[selected])
  const collage=collages[selected]
  return <div className="hero-collage">
    <div className="hero-collage-art"><img src={`${import.meta.env.BASE_URL}illustrations/${collage.file}`} alt="" width="640" height="640" decoding="async"/></div>
    <button className="collage-shuffle" type="button" aria-label="Mudar colagem do cabeçalho" onClick={()=>setSelected(current=>nextCollage(current))}><RefreshCw size={14} aria-hidden="true"/> Mudar colagem</button>
    <span className="collage-announcement" role="status" aria-live="polite">Colagem: {collage.name}</span>
  </div>
}
