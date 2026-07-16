import React from "react";

function Stat({icon:Icon,label,value,sub,tone="blue"}) { return <article className={`stat ${tone}`}><div><Icon/></div><span><small>{label}</small><b>{value}</b><em>{sub}</em></span></article>; }

export default Stat;
