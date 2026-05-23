import { Link } from "react-router-dom";
import { PageHeader, PageContainer, Card, Kpi, Badge, StatusDot, timeAgo } from "@/components/beacon/ui";
import { BEACON_USER, MESSAGES, ANALYTICS_30D, JOURNEYS, DOMAINS, CROSS_SELL, CHANNEL_LABELS, type Channel } from "@/content/beacon-mock";
import { Send, Plus, Mail, MessageSquare, Smartphone, BarChart3, Globe, Workflow } from "lucide-react";

export default function BeaconOverview() {
  const totalSent = ANALYTICS_30D.by_channel.reduce((s, c) => s + c.sent, 0);
  const totalDelivered = ANALYTICS_30D.by_channel.reduce((s, c) => s + c.delivered, 0);
  const deliveredRate = ((totalDelivered / totalSent) * 100).toFixed(2);
  const verifiedDomains = DOMAINS.filter((d) => d.verified).length;

  return (
    <PageContainer>
      <PageHeader
        title={`Olá, ${BEACON_USER.name.split(" ")[0]}`}
        subtitle={`${BEACON_USER.org} · ${BEACON_USER.mtd_email.toLocaleString("pt-BR")} emails, ${BEACON_USER.mtd_sms.toLocaleString("pt-BR")} SMS e ${BEACON_USER.mtd_push.toLocaleString("pt-BR")} push enviados em ${new Date().toLocaleString("pt-BR", { month: "long" })}. Spend MTD R$ ${BEACON_USER.mtd_spend_brl.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}.`}
        actions={
          <Link to="/app/produtos/beacon/messages" className="flex items-center gap-1.5 text-sm font-semibold bg-accent hover:bg-accent/90 text-white px-3 py-2 rounded-md">
            <Plus size={14} /> Enviar mensagem
          </Link>
        }
      />

      <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <Kpi label="Mensagens MTD" value={totalSent.toLocaleString("pt-BR")} hint={`${verifiedDomains}/${DOMAINS.length} domínios verificados`} />
        <Kpi label="Delivered rate" value={`${deliveredRate}%`} hint="P95 < 2s · alvo > 98%" accent="ok" />
        <Kpi label="Open rate (email)" value={`${((ANALYTICS_30D.by_channel[0].opened / ANALYTICS_30D.by_channel[0].delivered) * 100).toFixed(1)}%`} hint="Pixel tracking opt-in" />
        <Kpi label="Custo médio / mensagem" value={`R$ ${(BEACON_USER.mtd_spend_brl / (totalSent / 1000)).toFixed(2)} / 1k`} hint="Pricing em real · NF-e auto" accent="ok" />
      </div>

      <div className="grid lg:grid-cols-3 gap-6 mb-8">
        <Card className="p-5 lg:col-span-2">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold flex items-center gap-2"><BarChart3 size={14} /> Envios por canal (30d)</h3>
            <Link to="/app/produtos/beacon/analytics" className="text-xs text-accent hover:underline">Analytics →</Link>
          </div>
          <div className="space-y-2.5">
            {ANALYTICS_30D.by_channel.map((c) => {
              const pct = (c.sent / totalSent) * 100;
              return (
                <div key={c.channel} className="text-xs">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="font-medium flex-1">{CHANNEL_LABELS[c.channel as Channel]}</span>
                    <span className="text-zinc-500">{c.sent.toLocaleString("pt-BR")} enviados</span>
                    <span className="text-emerald-600 dark:text-emerald-400 w-16 text-right">{((c.delivered / c.sent) * 100).toFixed(1)}%</span>
                  </div>
                  <div className="w-full h-1.5 bg-zinc-100 dark:bg-zinc-800 rounded">
                    <div className="h-1.5 rounded bg-accent" style={{ width: `${pct}%` }} />
                  </div>
                </div>
              );
            })}
          </div>
        </Card>

        <Card className="p-5">
          <h3 className="text-sm font-semibold mb-4 flex items-center gap-2"><Workflow size={14} /> Ecosystem Rewire</h3>
          <div className="space-y-2">
            {CROSS_SELL.map((c) => (
              <div key={c.product} className="flex items-center gap-2 text-xs">
                <span className="font-semibold flex-1">{c.product}</span>
                {c.status === "active" ? <Badge tone="ok">Ativo</Badge> : c.status === "trial" ? <Badge tone="warn">Trial</Badge> : <Badge>{c.from}</Badge>}
              </div>
            ))}
          </div>
          <p className="text-[11px] text-zinc-500 mt-4 leading-relaxed">CONNECT entrega o canal WhatsApp; CITADEL ancora a chain BLAKE3; AUDIT TRAIL recebe evidências LGPD por mensagem.</p>
        </Card>
      </div>

      <div className="grid lg:grid-cols-2 gap-6">
        <Card className="p-5">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold flex items-center gap-2"><Send size={14} /> Últimas mensagens</h3>
            <Link to="/app/produtos/beacon/messages" className="text-xs text-accent hover:underline">Ver todas →</Link>
          </div>
          <div className="space-y-2">
            {MESSAGES.slice(0, 6).map((m) => (
              <div key={m.id} className="flex items-center gap-3 p-2 rounded-md hover:bg-zinc-50 dark:hover:bg-zinc-800/50">
                <StatusDot status={m.status} />
                <span className="text-xs font-mono text-zinc-500 w-20 truncate">{m.id}</span>
                <Badge>{CHANNEL_LABELS[m.channel]}</Badge>
                <span className="text-xs flex-1 truncate">{m.recipient}</span>
                <span className="text-[10px] text-zinc-500 uppercase">{m.status}</span>
                <span className="text-[10px] text-zinc-400 w-16 text-right">{timeAgo(m.sent_at)}</span>
              </div>
            ))}
          </div>
        </Card>

        <Card className="p-5">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold flex items-center gap-2"><Workflow size={14} /> Journeys ativos</h3>
            <Link to="/app/produtos/beacon/journeys" className="text-xs text-accent hover:underline">Ver todos →</Link>
          </div>
          <div className="space-y-3">
            {JOURNEYS.filter((j) => j.enabled).map((j) => (
              <div key={j.id} className="text-xs">
                <div className="flex items-center gap-2">
                  <span className="font-semibold flex-1">{j.name}</span>
                  <Badge tone="accent">{j.steps} steps</Badge>
                </div>
                <p className="text-[11px] text-zinc-500 mt-0.5">trigger: <code className="font-mono">{j.trigger}</code> · {j.active_runs} em execução · conv {(j.conversion_rate * 100).toFixed(0)}%</p>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </PageContainer>
  );
}
