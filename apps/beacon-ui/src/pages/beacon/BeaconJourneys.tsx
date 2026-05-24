import { PageHeader, PageContainer, Card, Badge } from "@/components/beacon/ui";
import { DemoBanner } from "@/components/beacon/DemoBanner";
import { JOURNEYS } from "@/content/beacon-mock";
import { useBeaconJourneys } from "@/lib/hooks/useBeacon";
import { Plus, Workflow, GitBranch, Play, Pause } from "lucide-react";

// BCN-233: BeaconJourneys wired to /v1/journeys via TanStack Query.
export default function BeaconJourneys() {
  const journeysQ = useBeaconJourneys();
  return (
    <PageContainer>
      {journeysQ.isDemo && <DemoBanner detail="GET /v1/journeys indisponivel" />}
      <PageHeader
        title="Journeys multi-canal"
        subtitle="Workflows duráveis Temporal: 'Envia email; se não abrir em 24h, SMS; se não responder em 48h, WhatsApp'. Visual flow builder + signals + conditional branching."
        actions={<button className="flex items-center gap-1.5 text-sm font-semibold bg-accent text-white px-3 py-2 rounded-md hover:bg-accent/90"><Plus size={14} /> Novo journey</button>}
      />

      <div className="grid md:grid-cols-2 gap-4">
        {JOURNEYS.map((j) => (
          <Card key={j.id} className="p-5">
            <div className="flex items-start gap-3 mb-3">
              <div className="w-9 h-9 rounded-md bg-accent/10 flex items-center justify-center text-accent"><Workflow size={16} /></div>
              <div className="flex-1">
                <h3 className="text-sm font-semibold flex items-center gap-2">
                  {j.name}
                  {j.enabled ? <Badge tone="ok">Ativo</Badge> : <Badge tone="warn">Pausado</Badge>}
                </h3>
                <p className="text-[11px] text-zinc-500 mt-0.5">trigger: <code className="font-mono">{j.trigger}</code></p>
              </div>
              <button className="text-zinc-400 hover:text-zinc-900 dark:hover:text-white p-1.5 rounded hover:bg-zinc-100 dark:hover:bg-zinc-800">
                {j.enabled ? <Pause size={13} /> : <Play size={13} />}
              </button>
            </div>

            <div className="grid grid-cols-4 gap-2 text-center mb-3">
              <div><p className="text-base font-bold">{j.steps}</p><p className="text-[10px] text-zinc-500">steps</p></div>
              <div><p className="text-base font-bold">{j.active_runs.toLocaleString("pt-BR")}</p><p className="text-[10px] text-zinc-500">em execução</p></div>
              <div><p className="text-base font-bold">{j.completed_30d.toLocaleString("pt-BR")}</p><p className="text-[10px] text-zinc-500">completas 30d</p></div>
              <div><p className="text-base font-bold text-emerald-600 dark:text-emerald-400">{(j.conversion_rate * 100).toFixed(0)}%</p><p className="text-[10px] text-zinc-500">conversão</p></div>
            </div>

            <div className="flex items-center gap-2 text-[10px] text-zinc-500 border-t border-zinc-100 dark:border-zinc-800 pt-3">
              <GitBranch size={11} /> Powered by Temporal · workflow durável + retry exponential + DLQ
            </div>
          </Card>
        ))}
      </div>
    </PageContainer>
  );
}
