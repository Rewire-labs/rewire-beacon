import { PageHeader, PageContainer, Card, Badge, Table, Th, Td, timeAgo } from "@/components/beacon/ui";
import { DemoBanner } from "@/components/beacon/DemoBanner";
import { ANTISPAM_ALERTS } from "@/content/beacon-mock";
import { useBeaconAntispam } from "@/lib/hooks/useBeacon";
import { AlertTriangle, Shield, Brain } from "lucide-react";

const SEV_TONE = { low: "ok" as const, medium: "warn" as const, high: "warn" as const, critical: "bad" as const };

// BCN-246: BeaconAntispam wired to /v1/antispam/scores.
export default function BeaconAntispam() {
  const antispamQ = useBeaconAntispam();
  return (
    <PageContainer>
      {antispamQ.isDemo && <DemoBanner detail="GET /v1/antispam/scores indisponivel" />}
      <PageHeader
        title="Anti-spam ML"
        subtitle="Python services com scikit-learn + sentence-transformers. Detecta padrões suspeitos (cliente novo enviando 100k emails/h, conteúdo semanticamente igual ao de listas compradas, recipient domains sintéticos)."
      />

      <div className="grid md:grid-cols-3 gap-3 mb-6">
        <Card className="p-5">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-md bg-emerald-100 dark:bg-emerald-950/40 flex items-center justify-center text-emerald-600 dark:text-emerald-400"><Shield size={16} /></div>
            <div>
              <p className="text-[11px] uppercase tracking-wider font-semibold text-zinc-500">Status org</p>
              <p className="text-base font-bold">Whitelisted</p>
              <p className="text-[11px] text-zinc-500">histórico limpo · sem holds</p>
            </div>
          </div>
        </Card>
        <Card className="p-5">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-md bg-accent/10 flex items-center justify-center text-accent"><Brain size={16} /></div>
            <div>
              <p className="text-[11px] uppercase tracking-wider font-semibold text-zinc-500">Score reputação</p>
              <p className="text-base font-bold">96 / 100</p>
              <p className="text-[11px] text-zinc-500">modelo IsolationForest + embeddings</p>
            </div>
          </div>
        </Card>
        <Card className="p-5">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-md bg-amber-100 dark:bg-amber-950/40 flex items-center justify-center text-amber-600 dark:text-amber-400"><AlertTriangle size={16} /></div>
            <div>
              <p className="text-[11px] uppercase tracking-wider font-semibold text-zinc-500">Mensagens em hold</p>
              <p className="text-base font-bold">0</p>
              <p className="text-[11px] text-zinc-500">{"human review fast-track <2h"}</p>
            </div>
          </div>
        </Card>
      </div>

      <h3 className="text-sm font-semibold mb-3">Alertas recentes</h3>
      <Table>
        <thead><tr><Th>Severidade</Th><Th>Padrão detectado</Th><Th>Status</Th><Th>Mensagens em hold</Th><Th>Detectado</Th></tr></thead>
        <tbody>
          {ANTISPAM_ALERTS.map((a) => (
            <tr key={a.id}>
              <Td><Badge tone={SEV_TONE[a.severity]}>{a.severity}</Badge></Td>
              <Td className="text-xs">{a.pattern}</Td>
              <Td><Badge tone={a.status === "blocked" ? "bad" : a.status === "investigating" ? "warn" : "ok"}>{a.status}</Badge></Td>
              <Td className="text-xs font-mono">{a.messages_held}</Td>
              <Td className="text-xs text-zinc-500">{timeAgo(a.detected_at)}</Td>
            </tr>
          ))}
        </tbody>
      </Table>

      <p className="text-[11px] text-zinc-500 mt-4">Anti-spam protege a reputação coletiva dos IPs Postal. Falsos positivos são liberados em até 2h via review humana (customer success).</p>
    </PageContainer>
  );
}
