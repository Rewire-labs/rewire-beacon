import { PageHeader, PageContainer, Card, Badge, Table, Th, Td, timeAgo, fmtDate } from "@/components/beacon/ui";
import { DSAR_REQUESTS } from "@/content/beacon-mock";
import { FileCheck, Plus, AlertCircle } from "lucide-react";

const TYPE_LABEL = { access: "Acesso", deletion: "Exclusão", portability: "Portabilidade" };
const STATUS_TONE = { received: "warn" as const, in_progress: "warn" as const, fulfilled: "ok" as const };

export default function BeaconLgpd() {
  const pending = DSAR_REQUESTS.filter((d) => d.status !== "fulfilled").length;
  return (
    <PageContainer>
      <PageHeader
        title="LGPD · DSAR"
        subtitle="Direito do titular de dados (Art. 18). DSAR fulfillment automático: BEACON retorna todas as mensagens com identifier_value. Breach notification 3-day automatizada."
        actions={<button className="flex items-center gap-1.5 text-sm font-semibold bg-accent text-white px-3 py-2 rounded-md hover:bg-accent/90"><Plus size={14} /> Registrar DSAR</button>}
      />

      <div className="grid md:grid-cols-4 gap-3 mb-6">
        <Card className="p-4"><p className="text-[10px] uppercase tracking-wider text-zinc-500 font-semibold">DSAR pendentes</p><p className="text-2xl font-bold mt-1">{pending}</p></Card>
        <Card className="p-4"><p className="text-[10px] uppercase tracking-wider text-zinc-500 font-semibold">SLA legal</p><p className="text-2xl font-bold mt-1">15 dias</p><p className="text-[10px] text-zinc-500">ANPD</p></Card>
        <Card className="p-4"><p className="text-[10px] uppercase tracking-wider text-zinc-500 font-semibold">Lawful basis tags</p><p className="text-2xl font-bold mt-1">4</p><p className="text-[10px] text-zinc-500">por mensagem</p></Card>
        <Card className="p-4"><p className="text-[10px] uppercase tracking-wider text-zinc-500 font-semibold">Retenção eventos</p><p className="text-2xl font-bold mt-1">13 meses</p><p className="text-[10px] text-zinc-500">ClickHouse TTL</p></Card>
      </div>

      <Card className="p-4 mb-6 bg-accent/5 border-accent/30">
        <div className="flex items-start gap-3 text-xs">
          <AlertCircle size={14} className="mt-0.5 text-accent" />
          <p><strong>Lawful basis tags obrigatórias:</strong> toda mensagem precisa de <code className="font-mono">consent</code>, <code className="font-mono">contract</code>, <code className="font-mono">legal_obligation</code> ou <code className="font-mono">legitimate_interest</code>. Tag fica imutável na audit chain BLAKE3.</p>
        </div>
      </Card>

      <h3 className="text-sm font-semibold mb-3">Solicitações DSAR</h3>
      <Table>
        <thead><tr><Th>Status</Th><Th>Titular</Th><Th>Tipo</Th><Th>Mensagens encontradas</Th><Th>Recebido</Th><Th>Deadline ANPD</Th></tr></thead>
        <tbody>
          {DSAR_REQUESTS.map((d) => (
            <tr key={d.id} className="hover:bg-zinc-50 dark:hover:bg-zinc-900/40">
              <Td><Badge tone={STATUS_TONE[d.status]}>{d.status}</Badge></Td>
              <Td className="font-mono text-xs flex items-center gap-2"><FileCheck size={12} className="text-zinc-400" />{d.identifier}</Td>
              <Td><Badge tone="accent">{TYPE_LABEL[d.type]}</Badge></Td>
              <Td className="text-xs font-mono">{d.messages_found?.toLocaleString("pt-BR") ?? "—"}</Td>
              <Td className="text-xs text-zinc-500">{timeAgo(d.received_at)}</Td>
              <Td className="text-xs">{fmtDate(d.deadline_at)}</Td>
            </tr>
          ))}
        </tbody>
      </Table>
    </PageContainer>
  );
}
