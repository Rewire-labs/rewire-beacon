import { PageHeader, PageContainer, Card, Badge, Table, Th, Td, timeAgo } from "@/components/beacon/ui";
import { DemoBanner } from "@/components/beacon/DemoBanner";
import { CHAIN_ENTRIES } from "@/content/beacon-mock";
import { useBeaconChain } from "@/lib/hooks/useBeacon";
import { Link2, ShieldCheck, ExternalLink } from "lucide-react";

// BCN-244 / FE-MESSAGING-06: render hook.data (falls back to mock).
export default function BeaconChain() {
  const chainQ = useBeaconChain(50);
  const entries = chainQ.data.entries as unknown as typeof CHAIN_ENTRIES;
  return (
    <PageContainer>
      {chainQ.isDemo && <DemoBanner detail="GET /v1/chain indisponivel (CITADEL link)" />}
      <PageHeader
        title="Audit chain (BLAKE3)"
        subtitle="Cada mensagem enviada e cada operação privilegiada gera um nó na CITADEL chain. Hash forense imutável (conteúdo + recipient + timestamp + consent basis) — diferencial absoluto para auditoria LGPD."
        actions={<a className="flex items-center gap-1.5 text-xs font-semibold border border-zinc-200 dark:border-zinc-800 px-3 py-2 rounded-md hover:bg-zinc-50 dark:hover:bg-zinc-800" href="/app/produtos/citadel"><ExternalLink size={13} /> Abrir CITADEL</a>}
      />

      <div className="grid md:grid-cols-3 gap-3 mb-6">
        <Card className="p-5">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-md bg-emerald-100 dark:bg-emerald-950/40 flex items-center justify-center text-emerald-600 dark:text-emerald-400"><ShieldCheck size={16} /></div>
            <div>
              <p className="text-[11px] uppercase tracking-wider font-semibold text-zinc-500">Integridade</p>
              <p className="text-base font-bold text-emerald-600 dark:text-emerald-400">OK · verificada</p>
              <p className="text-[11px] text-zinc-500">há 12s</p>
            </div>
          </div>
        </Card>
        <Card className="p-5"><p className="text-[11px] uppercase tracking-wider text-zinc-500 font-semibold">Total de entradas</p><p className="text-2xl font-bold mt-1">2.881.422</p></Card>
        <Card className="p-5"><p className="text-[11px] uppercase tracking-wider text-zinc-500 font-semibold">Anchor frequency</p><p className="text-2xl font-bold mt-1">60s</p><p className="text-[11px] text-zinc-500">Postgres → CITADEL</p></Card>
      </div>

      <Table>
        <thead><tr><Th>Quando</Th><Th>Actor</Th><Th>Ação</Th><Th>Target</Th><Th>Hash</Th></tr></thead>
        <tbody>
          {entries.map((c) => (
            <tr key={c.id} className="hover:bg-zinc-50 dark:hover:bg-zinc-900/40">
              <Td className="text-xs text-zinc-500">{timeAgo(c.ts)}</Td>
              <Td className="font-mono text-xs">{c.actor}</Td>
              <Td><Badge tone="accent">{c.action}</Badge></Td>
              <Td className="font-mono text-xs">{c.target}</Td>
              <Td className="font-mono text-[11px] text-zinc-500 flex items-center gap-1"><Link2 size={11} />{c.hash}</Td>
            </tr>
          ))}
        </tbody>
      </Table>
    </PageContainer>
  );
}
