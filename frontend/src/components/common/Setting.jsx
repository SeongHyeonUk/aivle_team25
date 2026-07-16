import React from "react";
import { ChevronDown } from "lucide-react";

function Setting({icon:Icon,title,text,value}) { return <article className="setting-card"><div><Icon/></div><span><b>{title}</b><p>{text}</p><small>{value}</small></span><ChevronDown/></article>; }

export default Setting;
