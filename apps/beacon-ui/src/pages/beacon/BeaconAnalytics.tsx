import { useEffect, useState } from "react";
import { PageHeader, PageContainer, Card, Table, Th, Td } from "@/components/beacon/ui";
import { ANALYTICS_30D, CHANNEL_LABELS, type Channel } from "@/content/beacon-mock";
import { Calendar, Download } from "lucide-react";
import { analytics } from "@/lib/api";

export default function BeaconAnalytics() {
  const [live, setLive] = useState<Array<Record<string, unknown>>>([]);
  useEffect(() => {
    analytics.summary({}).then((r) => setLive(r.rows)).catch(() => setLive([]));
  }, []);
  const totals = ANALYTICS_30D.by_channel.reduce(
    (a, c) => ({
      sent: a.sent + c.sent, delivered: a.delivered + c.delivered, opened: a.opened + c.opened,
      clicked: a.clicked + c.clicked, bounced: a.bounced + c.bounced, complained: a.complained + c.complained,
    }),
    { sent: 0, delivered: 0, opened: 0, clicked: 0, bounced: 0, complained: 0 }
  );

  const max = Math.max(...ANALYTICS_30D.sparkline);

  return (
    <PageContainer>
      <PageHeader
        title="Analytics"
        subtitle="Eventos vindos do ClickHouse com retenção de 13 meses. Materialized views por org × dia × canal para dashboards <100ms."
        actions={
          <>
            <button className="flex items-center gap-1.5 text-xs font-semibold border border-zinc-200 dark:border-zinc-800 px-3 py-2 rounded-md"><Calendar size={13} /> Últimos 30d</button>
            <button className="flex items-center gap-1.5 text-xs font-semibold border border-zinc-200 dark:border-zinc-800 px-3 py-2 rounded-md"><Download size={13} /> Export</button>
          </>
        }
      />

      <div className="grid md:grid-cols-6 gap-3 mb-6">
        {[
          { label: "Enviadas", v: totals.sent },
          { label: "Delivered", v: totals.delivered },
          { label: "Opened", v: totals.opened },
          { label: "Clicked", v: totals.clicked },
          { label: "Bounced", v: totals.bounced },
          { label: "Complaints", v: totals.complained },
        ].map((k) => (
          <Card key={k.label} className="p-4">
            <p className="text-[10px] uppercase tracking-wider text-zinc-500 font-semibold">{k.label}</p>
            <p className="text-lg font-bold mt-1">{k.v.toLocaleString("pt-BR")}</p>
          </Card>
        ))}
      </div>

      <Card className="p-5 mb-6">
        <h3 className="text-sm font-semibold mb-3">Volume diário (últimos 14 dias)</h3>
        <div className="flex items-end gap-1 h-32">
          {ANALYTICS_30D.sparkline.map((v, i) => (
            <div key={i} className="flex-1 bg-accent/30 hover:bg-accent rounded-t" style={{ height: `${(v / max) * 100}%` }} title={`${v}k mensagens`} />
          ))}
        </div>
        <p className="text-[11px] text-zinc-500 mt-2">Valores em milhares · pico {max}k em D-2</p>
      </Card>

      <Table>
        <thead><tr><Th>Canal</Th><Th>Enviadas</Th><Th>Delivered</Th><Th>%</Th><Th>Opened</Th><Th>Clicked</Th><Th>Bounced</Th><Th>Complaints</Th></tr></thead>
        <tbody>
          {ANALYTICS_30D.by_channel.map((c) => (
            <tr key={c.channel}>
              <Td className="font-medium text-sm">{CHANNEL_LABELS[c.channel as Channel]}</Td>
              <Td className="text-xs font-mono">{c.sent.toLocaleString("pt-BR")}</Td>
              <Td className="text-xs font-mono">{c.delivered.toLocaleString("pt-BR")}</Td>
              <Td className="text-xs font-semibold text-emerald-600 dark:text-emerald-400">{((c.delivered / c.sent) * 100).toFixed(1)}%</Td>
              <Td className="text-xs font-mono">{c.opened.toLocaleString("pt-BR")}</Td>
              <Td className="text-xs font-mono">{c.clicked.toLocaleString("pt-BR")}</Td>
              <Td className="text-xs font-mono">{c.bounced.toLocaleString("pt-BR")}</Td>
              <Td className="text-xs font-mono">{c.complained.toLocaleString("pt-BR")}</Td>
            </tr>
          ))}
        </tbody>
      </Table>
    </PageContainer>
  );
}
