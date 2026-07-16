import React from "react";

function Panel({title,action,children}) { return <article className="panel"><div className="panel-head"><h3>{title}</h3><span>{action}</span></div>{children}</article>; }

export default Panel;
