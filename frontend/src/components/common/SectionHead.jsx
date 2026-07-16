import React from "react";

function SectionHead({eyebrow,title,desc,action}) { return <div className="section-head"><div><span className="eyebrow">{eyebrow}</span><h2>{title}</h2><p>{desc}</p></div>{action}</div>; }

export default SectionHead;
