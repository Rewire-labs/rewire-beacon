import { PageHeader, PageContainer, Card, Badge, Table, Th, Td, timeAgo } from "@/components/beacon/ui";
import { API_KEYS } from "@/content/beacon-mock";
import { Plus, KeyRound, Copy, Eye } from "lucide-react";

export default function BeaconApiKeys() {
  return (
    <PageContainer>
      <PageHeader
        title="API keys"
        subtitle="Tokens por tenant via Authentik OIDC + scopes granulares. Use Bearer auth no header `Authorization: Bearer bcn_live_...`."
        actions={<button className="flex items-center gap-1.5 text-sm font-semibold bg-accent text-white px-3 py-2 rounded-md hover:bg-accent/90"><Plus size={14} /> Nova API key</button>}
      />

      <Card className="p-5 mb-6">
        <h3 className="text-sm font-semibold mb-2">Quickstart — enviar email</h3>
        <pre className="text-[11px] font-mono bg-zinc-50 dark:bg-zinc-900 p-3 rounded-md overflow-x-auto"><code>{`curl -X POST https://api.beacon.rewirelabs.dev/v1/messages/email \\
  -H "Authorization: Bearer bcn_live_4k9..." \\
  -H "Content-Type: application/json" \\
  -d '{
    "from": "no-reply@pampapay.com.br",
    "to": "cliente@exemplo.com",
    "subject": "Pedido confirmado",
    "template_id": "tpl_order_confirmation",
    "template_variables": { "pedido_id": "28117", "total": "R$ 199,90" },
    "lawful_basis": "contract"
  }'`}</code></pre>
        <button className="flex items-center gap-1.5 text-[11px] text-accent mt-2 hover:underline"><Copy size={11} /> Copiar</button>
      </Card>

      <Table>
        <thead><tr><Th>Nome</Th><Th>Prefix</Th><Th>Scopes</Th><Th>Criada por</Th><Th>Criada</Th><Th>Último uso</Th><Th></Th></tr></thead>
        <tbody>
          {API_KEYS.map((k) => (
            <tr key={k.id} className="hover:bg-zinc-50 dark:hover:bg-zinc-900/40">
              <Td className="font-medium text-sm flex items-center gap-2"><KeyRound size={13} className="text-zinc-400" /> {k.name}</Td>
              <Td className="font-mono text-xs">{k.prefix}</Td>
              <Td className="text-xs">
                <div className="flex flex-wrap gap-1">
                  {k.scopes.map((s) => <Badge key={s} tone="accent">{s}</Badge>)}
                </div>
              </Td>
              <Td className="text-xs text-zinc-500">{k.created_by}</Td>
              <Td className="text-xs text-zinc-500">{timeAgo(k.created_at)}</Td>
              <Td className="text-xs text-zinc-500">{timeAgo(k.last_used)}</Td>
              <Td><button className="text-zinc-400 hover:text-zinc-900 dark:hover:text-white"><Eye size={13} /></button></Td>
            </tr>
          ))}
        </tbody>
      </Table>
    </PageContainer>
  );
}
