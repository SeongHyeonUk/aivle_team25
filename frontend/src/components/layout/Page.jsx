import React from "react";
import WorkerHome from "../../pages/worker/WorkerHome";
import TBM from "../../pages/worker/TBM";
import Checklist from "../../pages/worker/Checklist";
import Report from "../../pages/worker/Report";
import AdminHome from "../../pages/admin/AdminHome";
import Monitoring from "../../pages/admin/Monitoring";
import Permits from "../../pages/admin/Permits";
import Risk from "../../pages/admin/Risk";
import Standards from "../../pages/admin/Standards";
import Audit from "../../pages/admin/Audit";

<<<<<<< Updated upstream
function Page({page,role,notify}) {
  if (role === "worker") return page==="tbm"?<TBM notify={notify}/>:page==="checklist"?<Checklist notify={notify}/>:page==="report"?<Report notify={notify}/>:<WorkerHome notify={notify}/>;
  return page==="monitoring"?<Monitoring notify={notify}/>:page==="permits"?<Permits notify={notify}/>:page==="risk"?<Risk/>:page==="standards"?<Standards notify={notify}/>:page==="audit"?<Audit/>:<AdminHome/>;
=======
function Page({page,role,session,notify}) {
  if (role === "worker") return page==="tbm"?<TBM notify={notify}/>:page==="checklist"?<Checklist notify={notify}/>:page==="report"?<Report session={session} notify={notify}/>:<WorkerHome notify={notify}/>;
  return page==="monitoring"?<Monitoring notify={notify}/>:page==="permits"?<Permits session={session} notify={notify}/>:page==="risk"?<Risk/>:page==="standards"?<Standards notify={notify}/>:page==="audit"?<Audit/>:<AdminHome/>;
>>>>>>> Stashed changes
}

export default Page;
