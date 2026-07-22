import React from "react";
import WorkerHome from "../../pages/worker/WorkerHome";
import TBM from "../../pages/worker/TBM";
import Checklist from "../../pages/worker/Checklist";
import Report from "../../pages/worker/Report";
import DigitalTwin from "../../pages/admin/DigitalTwin";
import Monitoring from "../../pages/admin/Monitoring";
import WorkerReports from "../../pages/admin/WorkerReports";
import Permits from "../../pages/admin/Permits";
import Risk from "../../pages/admin/Risk";
import Audit from "../../pages/admin/Audit";

function Page({page,role,session,notify}) {
  if (role === "worker") return page==="tbm"?<TBM notify={notify}/>:page==="checklist"?<Checklist notify={notify}/>:page==="report"?<Report session={session} notify={notify}/>:<WorkerHome session={session} notify={notify}/>;
  return page==="monitoring"?<Monitoring notify={notify}/>:page==="reports"?<WorkerReports session={session} notify={notify}/>:page==="permits"?<Permits session={session} notify={notify}/>:page==="risk"?<Risk/>:page==="audit"?<Audit/>:<DigitalTwin session={session} notify={notify}/>;
}

export default Page;
