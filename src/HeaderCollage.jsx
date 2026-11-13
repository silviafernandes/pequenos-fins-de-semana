import React, {useEffect,useState} from 'react'
import {collages,nextCollage} from './collages.js'

export default function HeaderCollage(){
  const [selected]=useState(()=>{
    let previous=-1
    try {const stored=sessionStorage.getItem('pfds-header-collage');if(stored!==null)previous=Number(stored)} catch {}
    return nextCollage(previous)
  })
  useEffect(()=>{try{sessionStorage.setItem('pfds-header-collage',String(selected))}catch{}},[selected])
  const collage=collages[selected]
  return <div className="hero-collage" aria-hidden="true">
    <div className="hero-collage-art"><img src={`${import.meta.env.BASE_URL}illustrations/${collage.file}?v=${collage.version||'flat-paper-1'}`} alt="" width="640" height="640" decoding="async"/></div>
  </div>
}
