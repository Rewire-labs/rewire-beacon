import { Outlet } from "react-router-dom";
import BeaconTopbar from "./BeaconTopbar";
import BeaconSidebar from "./BeaconSidebar";

export default function BeaconShell() {
  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-zinc-950 text-zinc-900 dark:text-zinc-100 font-sans">
      <BeaconTopbar />
      <div className="flex">
        <BeaconSidebar />
        <main className="flex-1 min-w-0"><Outlet /></main>
      </div>
    </div>
  );
}
