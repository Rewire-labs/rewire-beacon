// RW-FE-MESSAGING-10: canonical tokens (no hard-coded zinc/emerald).
import { Link } from "react-router-dom";
import { Radio, ChevronDown, Bell, Plus } from "lucide-react";
import { BEACON_USER, TIER_LABELS } from "@/content/beacon-mock";

export default function BeaconTopbar() {
  const emailPct = Math.round((BEACON_USER.mtd_email / BEACON_USER.mtd_email_quota) * 100);
  const spendPct = Math.round((BEACON_USER.mtd_spend_brl / BEACON_USER.mtd_cap_brl) * 100);

  return (
    <header className="h-14 border-b border-border bg-card flex items-center px-4 sticky top-0 z-40">
      <Link to="/app/produtos/beacon" className="flex items-center gap-2 mr-6">
        <div className="w-7 h-7 rounded-md bg-gradient-to-br from-primary to-accent flex items-center justify-center">
          <Radio size={16} className="text-white" />
        </div>
        <span className="font-bold text-sm tracking-wide">BEACON</span>
        <span className="text-[10px] font-semibold uppercase tracking-wider text-success bg-success/10 px-1.5 py-0.5 rounded">
          Multi-canal BR
        </span>
      </Link>

      <button className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground px-2 py-1 rounded hover:bg-muted transition">
        <span className="font-medium">{BEACON_USER.org}</span>
        <span className="text-[10px] uppercase font-semibold text-accent">{TIER_LABELS[BEACON_USER.tier]}</span>
        <ChevronDown size={12} />
      </button>

      <div className="flex-1 flex items-center justify-center gap-3 text-xs">
        <span className="text-muted-foreground">
          email <span className="font-semibold text-foreground">{emailPct}%</span> da quota
        </span>
        <span className="text-muted-foreground">·</span>
        <span className="text-muted-foreground">
          SMS <span className="font-semibold text-foreground">{BEACON_USER.mtd_sms.toLocaleString("pt-BR")}</span>
        </span>
        <span className="text-muted-foreground">·</span>
        <span className="text-muted-foreground">
          spend MTD <span className="font-semibold text-foreground">R$ {BEACON_USER.mtd_spend_brl.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}</span> ({spendPct}%)
        </span>
      </div>

      <Link
        to="/app/produtos/beacon/messages"
        className="hidden md:flex items-center gap-1.5 text-xs font-semibold bg-accent hover:bg-accent/90 text-white px-3 py-1.5 rounded-md mr-3 transition"
      >
        <Plus size={13} /> Enviar mensagem
      </Link>

      <button className="p-2 text-muted-foreground hover:text-foreground relative">
        <Bell size={16} />
      </button>
      <Link to="/plataforma/beacon" className="text-xs text-muted-foreground hover:text-foreground mr-3 ml-2">← Sair</Link>
      <div className="w-8 h-8 rounded-full bg-gradient-to-br from-primary to-accent flex items-center justify-center text-xs font-bold text-white">
        {BEACON_USER.initial}
      </div>
    </header>
  );
}
