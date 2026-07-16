import React from "react";
import { Check, ChevronDown } from "lucide-react";

function Task({done,text,time,onClick}) { return <button className={`task ${done?"done":""}`} onClick={onClick}><span>{done?<Check/>:""}</span><div><b>{text}</b><small>{time}</small></div><ChevronDown/></button>; }

export default Task;
