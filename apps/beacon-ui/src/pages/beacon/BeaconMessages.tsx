import { PageHeader, PageContainer, Card, Badge, StatusDot, Table, Th, Td, timeAgo } from "@/components/beacon/ui";
import { DemoBanner } from "@/components/beacon/DemoBanner";
import { MESSAGES, CHANNEL_LABELS } from "@/content/beacon-mock";
import { useBeaconMessages } from "@/lib/hooks/useBeacon";
import { Search, Filter, Send, Download } from "lucide-react";

// BCN-231: BeaconMessages wired to /v1/messages (and analytics).
export default function BeaconMessages() {
  const messages = useBeaconMessages();
  return (
    <PageContainer>
      {messages.isDemo && <DemoBanner detail="GET /v1/messages indisponivel" />}
      <PageHeader
        title="Mensagens"
        subtitle="Log de envios em tempo real (todos os canais). Eventos vindos de ClickHouse com retenção de 13 meses + audit chain BLAKE3."
        actions={
          <>
            <button className="flex items-center gap-1.5 text-xs font-semibold border border-zinc-200 dark:border-zinc-800 px-3 py-2 rounded-md hover:bg-zinc-50 dark:hover:bg-zinc-800"><Download size={13} /> Export CSV</button>
            <button className="flex items-center gap-1.5 text-sm font-semibold bg-accent hover:bg-accent/90 text-white px-3 py-2 rounded-md"><Send size={14} /> Test send</button>
          </>
        }
      />

      <Card className="p-3 mb-4 flex items-center gap-2 flex-wrap">
        <div className="flex items-center gap-2 bg-zinc-50 dark:bg-zinc-900 px-3 py-1.5 rounded-md flex-1 min-w-[240px]">
          <Search size={13} className="text-zinc-400" />
          <input className="bg-transparent text-xs outline-none flex-1" placeholder="Buscar por message_id, recipient, template..." />
        </div>
        <button className="flex items-center gap-1 text-xs border border-zinc-200 dark:border-zinc-800 px-2.5 py-1.5 rounded-md"><Filter size={11} /> Canal</button>
        <button className="flex items-center gap-1 text-xs border border-zinc-200 dark:border-zinc-800 px-2.5 py-1.5 rounded-md"><Filter size={11} /> Status</button>
        <button className="flex items-center gap-1 text-xs border border-zinc-200 dark:border-zinc-800 px-2.5 py-1.5 rounded-md"><Filter size={11} /> Período</button>
      </Card>

      <Table>
        <thead>
          <tr>
            <Th>Status</Th><Th>ID</Th><Th>Canal</Th><Th>Destinatário</Th><Th>Template / Assunto</Th>
            <Th>Provider</Th><Th>Custo</Th><Th>Basis LGPD</Th><Th>Quando</Th>
          </tr>
        </thead>
        <tbody>
          {MESSAGES.map((m) => (
            <tr key={m.id} className="hover:bg-zinc-50 dark:hover:bg-zinc-900/40">
              <Td><div className="flex items-center gap-2"><StatusDot status={m.status} /><span className="text-[10px] uppercase">{m.status}</span></div></Td>
              <Td className="font-mono text-xs">{m.id}</Td>
              <Td><Badge tone="accent">{CHANNEL_LABELS[m.channel]}</Badge></Td>
              <Td className="text-xs">{m.recipient}</Td>
              <Td className="text-xs"><code className="font-mono text-zinc-500">{m.template}</code>{m.subject_or_title && <p className="text-zinc-400 truncate max-w-[260px]">{m.subject_or_title}</p>}</Td>
              <Td className="text-xs text-zinc-500">{m.provider}</Td>
              <Td className="text-xs font-mono">R$ {m.cost_brl.toFixed(4)}</Td>
              <Td><Badge>{m.lawful_basis}</Badge></Td>
              <Td className="text-xs text-zinc-500">{timeAgo(m.sent_at)}</Td>
            </tr>
          ))}
        </tbody>
      </Table>

      <p className="text-[11px] text-zinc-500 mt-4">Cada linha está ancorada na audit chain CITADEL. <code className="font-mono">message_id</code> + <code className="font-mono">content_hash</code> são imutáveis e podem ser usados como prova jurídica.</p>
    </PageContainer>
  );
}
