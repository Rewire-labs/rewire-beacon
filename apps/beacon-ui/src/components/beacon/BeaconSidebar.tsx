import { NavLink } from "react-router-dom";
import {
  LayoutDashboard, Send, FileText, Workflow, Ban, Globe, MessageSquare, Smartphone,
  BellRing, BarChart3, Webhook, AlertTriangle, KeyRound, FileCheck, Link2,
  Receipt, Users, Settings as SettingsIcon, Mail,
} from "lucide-react";
import type { ForwardRefExoticComponent, RefAttributes } from "react";
import type { LucideProps } from "lucide-react";

type NavIcon = ForwardRefExoticComponent<Omit<LucideProps, "ref"> & RefAttributes<SVGSVGElement>>;
interface NavItem { to: string; label: string; icon: NavIcon; end?: boolean; badge?: string }

const BASE = "/app/produtos/beacon";

const NAV: Array<{ group: string; items: NavItem[] }> = [
  { group: "Visão", items: [
    { to: "", label: "Overview", icon: LayoutDashboard, end: true },
  ]},
  { group: "Envios", items: [
    { to: "messages", label: "Mensagens", icon: Send },
    { to: "templates", label: "Templates", icon: FileText },
    { to: "journeys", label: "Journeys", icon: Workflow, badge: "Temporal" },
    { to: "suppression", label: "Suppression list", icon: Ban, badge: "Cross-canal" },
  ]},
  { group: "Canais", items: [
    { to: "domains", label: "Email · Domínios", icon: Globe },
    { to: "sms-numbers", label: "SMS · Números BR", icon: Mail },
    { to: "whatsapp", label: "WhatsApp", icon: MessageSquare, badge: "CONNECT" },
    { to: "push-apps", label: "Push apps", icon: Smartphone },
  ]},
  { group: "Análise & Saúde", items: [
    { to: "analytics", label: "Analytics", icon: BarChart3 },
    { to: "webhooks", label: "Webhooks", icon: Webhook },
    { to: "deliverability", label: "Deliverability", icon: BellRing },
    { to: "antispam", label: "Anti-spam ML", icon: AlertTriangle },
  ]},
  { group: "Conta", items: [
    { to: "api-keys", label: "API keys", icon: KeyRound },
    { to: "lgpd", label: "LGPD · DSAR", icon: FileCheck },
    { to: "chain", label: "Audit chain", icon: Link2, badge: "BLAKE3" },
    { to: "billing", label: "Billing & uso", icon: Receipt },
    { to: "team", label: "Time & SSO", icon: Users },
    { to: "settings", label: "Configurações", icon: SettingsIcon },
  ]},
];

export default function BeaconSidebar() {
  return (
    {/* RW-FE-MESSAGING-10: canonical tokens (no hard-coded zinc). */}
    <aside className="w-60 shrink-0 border-r border-border bg-card min-h-[calc(100vh-3.5rem)] sticky top-14 self-start">
      <nav className="py-4 px-2 space-y-4">
        {NAV.map((g) => (
          <div key={g.group}>
            <p className="px-3 mb-1.5 text-[10px] uppercase tracking-wider font-semibold text-muted-foreground">{g.group}</p>
            <div className="space-y-0.5">
              {g.items.map(({ to, label, icon: Icon, end = false, badge }) => (
                <NavLink
                  key={to}
                  to={`${BASE}/${to}`.replace(/\/$/, "")}
                  end={end}
                  className={({ isActive }) =>
                    `flex items-center gap-2.5 px-3 py-2 rounded-md text-sm transition ${
                      isActive
                        ? "bg-accent/10 text-accent font-semibold"
                        : "text-muted-foreground hover:bg-muted hover:text-foreground"
                    }`
                  }
                >
                  <Icon size={15} />
                  <span className="flex-1">{label}</span>
                  {badge && (
                    <span className="text-[9px] font-semibold uppercase tracking-wider text-accent bg-accent/10 px-1 py-0.5 rounded">{badge}</span>
                  )}
                </NavLink>
              ))}
            </div>
          </div>
        ))}
      </nav>
      <div className="mx-3 mt-4 mb-6 p-3 rounded-lg bg-gradient-to-br from-accent/10 to-primary/10 border border-accent/20">
        <p className="text-[10px] uppercase tracking-wider font-semibold text-accent mb-1">Cluster</p>
        <p className="text-xs font-bold text-foreground">br-sp1 · São Paulo</p>
        <p className="text-[10px] text-muted-foreground mt-0.5">Postal · Kafka · ClickHouse · Temporal</p>
      </div>
    </aside>
  );
}
