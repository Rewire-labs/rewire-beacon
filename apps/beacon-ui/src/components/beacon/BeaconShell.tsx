import { Outlet } from "react-router-dom";
import BeaconTopbar from "./BeaconTopbar";
import BeaconSidebar from "./BeaconSidebar";

export default function BeaconShell() {
  return (
    {/* RW-FE-MESSAGING-10: canonical bg-background/text-foreground tokens (no hard-coded zinc). */}
    <div className="min-h-screen bg-background text-foreground font-sans">
      <BeaconTopbar />
      <div className="flex">
        <BeaconSidebar />
        <main className="flex-1 min-w-0"><Outlet /></main>
      </div>
    </div>
  );
}
