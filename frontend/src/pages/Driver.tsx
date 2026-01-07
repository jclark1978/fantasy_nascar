import React from 'react'
import { useParams } from 'react-router-dom'

export default function Driver(){
  const { id } = useParams()
  return (
    <div>
      <h2>Driver {id}</h2>
      <p>Driver page prototype — fetch `/athlete-info` in full implementation.</p>
    </div>
  )
}
