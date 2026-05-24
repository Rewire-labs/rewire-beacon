import { PageHeader, PageContainer, Card, Badge } from "@/components/beacon/ui";
import { DemoBanner } from "@/components/beacon/DemoBanner";
import { BEACON_USER } from "@/content/beacon-mock";
import { useBeaconSettings } from "@/lib/hooks/useBeacon";
import { Settings as SettingsIcon, AlertTriangle, Bell, Globe, Clock } from "lucide-react";

// BCN-247: BeaconSettings wired to /v1/settings.
export default function BeaconSettings() {
  const settingsQ = useBeaconSettings();
  return (
    <PageContainer>
      {settingsQ.isDemo && <DemoBanner detail="GET /v1/settings indisponivel" />}
      <PageHeader title="Configurações" subtitle="Quiet hours, frequency capping, anti-bill-shock cap, regiões e BYOK." />

      <div className="grid lg:grid-cols-2 gap-4">
        <Card className="p-5">
          <h3 className="text-sm font-semibold mb-3 flex items-center gap-2"><Clock size={14} /> Quiet hours</h3>
          <p className="text-[12px] text-zinc-500 mb-3">Não enviar SMS/push entre estes horários (timezone do recipient). Configurável por organização.</p>
          <div className="flex items-center gap-3 mb-2">
            <input className="w-24 text-sm bg-zinc-50 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded px-2 py-1" defaultValue="22:00" />
            <span className="text-zinc-400">até</span>
            <input className="w-24 text-sm bg-zinc-50 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded px-2 py-1" defaultValue="07:00" />
            <Badge tone="ok">Ativo</Badge>
          </div>
        </Card>

        <Card className="p-5">
          <h3 className="text-sm font-semibold mb-3 flex items-center gap-2"><Bell size={14} /> Frequency cap</h3>
          <p className="text-[12px] text-zinc-500 mb-3">Máximo de notificações por usuário por dia, cross-canal (previne notification fatigue).</p>
          <div className="flex items-center gap-3">
            <input type="number" className="w-20 text-sm bg-zinc-50 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded px-2 py-1" defaultValue="6" />
            <span className="text-xs text-zinc-500">mensagens/usuário/dia</span>
            <Badge tone="accent">Cross-canal</Badge>
          </div>
        </Card>

        <Card className="p-5">
          <h3 className="text-sm font-semibold mb-3 flex items-center gap-2"><AlertTriangle size={14} /> Anti-bill-shock</h3>
          <p className="text-[12px] text-zinc-500 mb-3">Cap mensal global. Quando atingido, BEACON pausa envios marketing e alerta admin.</p>
          <div className="flex items-center gap-3 mb-2">
            <span className="text-xs">R$</span>
            <input type="number" className="w-32 text-sm bg-zinc-50 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded px-2 py-1" defaultValue={BEACON_USER.mtd_cap_brl} />
            <Badge tone="ok">Ativo</Badge>
          </div>
          <p className="text-[11px] text-zinc-500">Transacionais (consent/contract/legal_obligation) seguem fluindo — só marketing é pausado.</p>
        </Card>

        <Card className="p-5">
          <h3 className="text-sm font-semibold mb-3 flex items-center gap-2"><Globe size={14} /> Região</h3>
          <p className="text-[12px] text-zinc-500 mb-3">Dados sempre no Brasil (cluster Rewire SP1). DR ativo em RJ1.</p>
          <div className="flex items-center gap-2"><Badge tone="ok">br-sp1 · primário</Badge><Badge>br-rj1 · DR</Badge></div>
        </Card>

        <Card className="p-5 lg:col-span-2">
          <h3 className="text-sm font-semibold mb-3 flex items-center gap-2"><SettingsIcon size={14} /> Secrets · BYOK</h3>
          <p className="text-[12px] text-zinc-500 mb-3">Use sua própria chave KMS (OpenBao/VAULT-BR) para criptografar templates, anexos e signing secrets. Disponível Scale+.</p>
          <div className="flex items-center gap-2">{BEACON_USER.tier === "scale" || BEACON_USER.tier === "enterprise" ? <Badge tone="ok">BYOK disponível</Badge> : <Badge tone="warn">Upgrade para Scale</Badge>}</div>
        </Card>
      </div>
    </PageContainer>
  );
}
