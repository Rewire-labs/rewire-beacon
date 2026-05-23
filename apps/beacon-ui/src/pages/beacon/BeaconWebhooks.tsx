import { PageHeader, PageContainer, Card, Badge, Table, Th, Td, timeAgo } from "@/components/beacon/ui";
import { WEBHOOKS } from "@/content/beacon-mock";
import { Webhook, Plus, Copy } from "lucide-react";

export default function BeaconWebhooks() {
  return (
    <PageContainer>
      <PageHeader
        title="Webhooks"
        subtitle="Receba eventos em tempo real: message.sent, .delivered, .opened, .clicked, .bounced, .complained, .unsubscribed. Assinatura HMAC-SHA256 + retry exponencial (até 24h)."
        actions={<button className="flex items-center gap-1.5 text-sm font-semibold bg-accent text-white px-3 py-2 rounded-md hover:bg-accent/90"><Plus size={14} /> Adicionar endpoint</button>}
      />

      <div className="grid md:grid-cols-3 gap-3 mb-6">
        <Card className="p-4">
          <p className="text-[10px] uppercase tracking-wider text-zinc-500 font-semibold">Endpoints ativos</p>
          <p className="text-2xl font-bold mt-1">{WEBHOOKS.filter((w) => w.enabled).length}</p>
        </Card>
        <Card className="p-4">
          <p className="text-[10px] uppercase tracking-wider text-zinc-500 font-semibold">Entregas 30d</p>
          <p className="text-2xl font-bold mt-1">{WEBHOOKS.reduce((s, w) => s + w.deliveries_30d, 0).toLocaleString("pt-BR")}</p>
        </Card>
        <Card className="p-4">
          <p className="text-[10px] uppercase tracking-wider text-zinc-500 font-semibold">Success rate médio</p>
          <p className="text-2xl font-bold mt-1 text-emerald-600 dark:text-emerald-400">99,4%</p>
        </Card>
      </div>

      <Table>
        <thead><tr><Th>Status</Th><Th>URL</Th><Th>Eventos</Th><Th>Success 30d</Th><Th>Entregas</Th><Th>Última</Th></tr></thead>
        <tbody>
          {WEBHOOKS.map((w) => (
            <tr key={w.id} className="hover:bg-zinc-50 dark:hover:bg-zinc-900/40">
              <Td>{w.enabled ? <Badge tone="ok">Ativo</Badge> : <Badge tone="bad">Desativado</Badge>}</Td>
              <Td className="font-mono text-xs flex items-center gap-2"><Webhook size={12} className="text-zinc-400" />{w.url}</Td>
              <Td className="text-xs">
                <div className="flex flex-wrap gap-1 max-w-[280px]">
                  {w.events.slice(0, 4).map((e) => <Badge key={e}>{e}</Badge>)}
                  {w.events.length > 4 && <span className="text-[10px] text-zinc-400">+{w.events.length - 4}</span>}
                </div>
              </Td>
              <Td className="text-xs font-semibold">{(w.success_rate_30d * 100).toFixed(1)}%</Td>
              <Td className="text-xs font-mono">{w.deliveries_30d.toLocaleString("pt-BR")}</Td>
              <Td className="text-xs text-zinc-500">{timeAgo(w.last_delivery)}</Td>
            </tr>
          ))}
        </tbody>
      </Table>

      <Card className="p-5 mt-6">
        <h3 className="text-sm font-semibold mb-2">Verificação HMAC (Node.js)</h3>
        <pre className="text-[11px] font-mono bg-zinc-50 dark:bg-zinc-900 p-3 rounded-md overflow-x-auto"><code>{`import crypto from "crypto";

const signature = req.headers["x-beacon-signature"];
const expected = crypto.createHmac("sha256", SIGNING_SECRET).update(req.rawBody).digest("hex");
if (signature !== expected) return res.status(401).end();`}</code></pre>
        <button className="flex items-center gap-1.5 text-[11px] text-accent mt-2 hover:underline"><Copy size={11} /> Copiar exemplo</button>
      </Card>
    </PageContainer>
  );
}
