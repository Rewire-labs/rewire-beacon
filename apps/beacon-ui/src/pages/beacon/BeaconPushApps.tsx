import { PageHeader, PageContainer, Card, Badge, Table, Th, Td } from "@/components/beacon/ui";
import { DemoBanner } from "@/components/beacon/DemoBanner";
import { PUSH_APPS } from "@/content/beacon-mock";
import { useBeaconPushApps } from "@/lib/hooks/useBeacon";
import { Plus, Smartphone, Apple, Globe } from "lucide-react";

const PLATFORM_ICON = { ios: Apple, android: Smartphone, web: Globe };

// BCN-238: BeaconPushApps wired to /v1/push-apps via TanStack hook.
export default function BeaconPushApps() {
  const pushQ = useBeaconPushApps();
  return (
    <PageContainer>
      {pushQ.isDemo && <DemoBanner detail="GET /v1/push-apps indisponivel" />}
      <PageHeader
        title="Push apps"
        subtitle="APNs (iOS), FCM (Android) e VAPID Web Push (RFC 8030). Connection pooling + retry exponential + cleanup automático de bad tokens."
        actions={<button className="flex items-center gap-1.5 text-sm font-semibold bg-accent text-white px-3 py-2 rounded-md hover:bg-accent/90"><Plus size={14} /> Novo app</button>}
      />

      <div className="grid md:grid-cols-3 gap-4 mb-6">
        {(["ios", "android", "web"] as const).map((p) => {
          const apps = PUSH_APPS.filter((a) => a.platform === p);
          const subs = apps.reduce((s, a) => s + a.subscribers, 0);
          const Icon = PLATFORM_ICON[p];
          return (
            <Card key={p} className="p-5">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-md bg-accent/10 flex items-center justify-center text-accent"><Icon size={16} /></div>
                <div>
                  <p className="text-[11px] uppercase tracking-wider font-semibold text-zinc-500">Push {p}</p>
                  <p className="text-xl font-bold">{subs.toLocaleString("pt-BR")}</p>
                  <p className="text-[11px] text-zinc-500">subscribers</p>
                </div>
              </div>
            </Card>
          );
        })}
      </div>

      <Table>
        <thead><tr><Th>Status</Th><Th>App</Th><Th>Plataforma</Th><Th>Bundle / Origin</Th><Th>Subscribers</Th><Th>Enviadas 30d</Th></tr></thead>
        <tbody>
          {PUSH_APPS.map((a) => (
            <tr key={a.id} className="hover:bg-zinc-50 dark:hover:bg-zinc-900/40">
              <Td>{a.configured ? <Badge tone="ok">Configurado</Badge> : <Badge tone="warn">Setup pendente</Badge>}</Td>
              <Td className="font-medium text-sm">{a.name}</Td>
              <Td><Badge tone="accent">{a.platform.toUpperCase()}</Badge></Td>
              <Td className="font-mono text-xs">{a.bundle}</Td>
              <Td className="text-xs font-mono">{a.subscribers.toLocaleString("pt-BR")}</Td>
              <Td className="text-xs font-mono">{a.sent_30d.toLocaleString("pt-BR")}</Td>
            </tr>
          ))}
        </tbody>
      </Table>

      <p className="text-[11px] text-zinc-500 mt-4">iOS: upload .p8 (token-based) ou cert APNs. Android: Service Account JSON do Firebase. Web: BEACON gera VAPID + Service Worker snippet.</p>
    </PageContainer>
  );
}
