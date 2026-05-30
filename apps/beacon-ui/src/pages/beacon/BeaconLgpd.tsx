import { useState } from "react";
import { PageHeader, PageContainer, Card, Badge, Table, Th, Td, timeAgo, fmtDate } from "@/components/beacon/ui";
import { DemoBanner } from "@/components/beacon/DemoBanner";
import { DSAR_REQUESTS } from "@/content/beacon-mock";
import { useBeaconLgpd } from "@/lib/hooks/useBeacon";
import { FileCheck, Plus, AlertCircle } from "lucide-react";
import { lgpd } from "@/lib/api";

const TYPE_LABEL = { access: "Acesso", deletion: "Exclusão", portability: "Portabilidade" };
const STATUS_TONE = { received: "warn" as const, in_progress: "warn" as const, fulfilled: "ok" as const };

// BCN-242 / FE-MESSAGING-06: render hook.data (falls back to mock when isDemo).
export default function BeaconLgpd() {
  const lgpdQ = useBeaconLgpd();
  // Use fetched data when available; lgpdQ.data.dsars is populated by the hook
  // (with mock fallback when backend unreachable).
  const dsars = lgpdQ.data.dsars as typeof DSAR_REQUESTS;
  const pending = dsars.filter((d) => d.status !== "fulfilled").length;
  const [creating, setCreating] = useState(false);
  const [email, setEmail] = useState("");
  const [result, setResult] = useState<string | null>(null);
  async function handleSubmit() {
    if (!email) return;
    try {
      const r = await lgpd.requestDsar({ subject_email: email });
      setResult(`DSAR ${r.id} aceito (ETA ${r.eta_hours}h)`);
      setEmail("");
      setCreating(false);
    } catch (e) {
      setResult(`Erro: ${e instanceof Error ? e.message : String(e)}`);
    }
  }
  return (
    <PageContainer>
      {lgpdQ.isDemo && <DemoBanner detail="GET /v1/audit/lgpd/dsar indisponivel" />}
      <PageHeader
        title="LGPD · DSAR"
        subtitle="Direito do titular de dados (Art. 18). DSAR fulfillment automático."
        actions={
          <button onClick={() => setCreating(true)} className="flex items-center gap-1.5 text-sm font-semibold bg-accent text-white px-3 py-2 rounded-md hover:bg-accent/90">
            <Plus size={14} /> Registrar DSAR
          </button>
        }
      />

      {creating && (
        <Card className="p-4 mb-4">
          <h3 className="text-sm font-semibold mb-2">Nova solicitacao DSAR</h3>
          <input value={email} onChange={(e) => setEmail(e.target.value)} placeholder="titular@example.com"
            className="w-full text-sm border rounded-md px-3 py-1.5 mb-2 font-mono" />
          <div className="flex gap-2">
            <button onClick={handleSubmit} className="text-sm bg-accent text-white px-3 py-1.5 rounded-md">Submeter</button>
            <button onClick={() => setCreating(false)} className="text-sm border px-3 py-1.5 rounded-md">Cancelar</button>
          </div>
        </Card>
      )}
      {result && <Card className="p-3 mb-4 text-xs">{result}</Card>}

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
          {dsars.map((d) => (
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
