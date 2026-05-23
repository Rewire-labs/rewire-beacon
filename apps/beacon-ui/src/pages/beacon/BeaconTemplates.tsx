import { PageHeader, PageContainer, Card, Badge, Table, Th, Td, timeAgo } from "@/components/beacon/ui";
import { TEMPLATES, CHANNEL_LABELS } from "@/content/beacon-mock";
import { Plus, FileText } from "lucide-react";

export default function BeaconTemplates() {
  return (
    <PageContainer>
      <PageHeader
        title="Templates"
        subtitle="MJML 5.x para email, Handlebars-like para variáveis, A/B testing nativo. 50+ templates marketplace prontos para e-commerce, fintech, healthtech."
        actions={<button className="flex items-center gap-1.5 text-sm font-semibold bg-accent text-white px-3 py-2 rounded-md hover:bg-accent/90"><Plus size={14} /> Novo template</button>}
      />

      <div className="grid md:grid-cols-4 gap-3 mb-6">
        {(["transactional", "marketing", "security", "system"] as const).map((cat) => {
          const count = TEMPLATES.filter((t) => t.category === cat).length;
          return (
            <Card key={cat} className="p-4">
              <p className="text-[10px] uppercase tracking-wider text-zinc-500 font-semibold">{cat}</p>
              <p className="text-xl font-bold mt-1">{count}</p>
              <p className="text-[11px] text-zinc-500">templates</p>
            </Card>
          );
        })}
      </div>

      <Table>
        <thead>
          <tr>
            <Th>Status</Th><Th>Nome</Th><Th>Canal</Th><Th>Categoria</Th><Th>Variáveis</Th>
            <Th>Enviadas 30d</Th><Th>Open</Th><Th>Click</Th><Th>Última uso</Th>
          </tr>
        </thead>
        <tbody>
          {TEMPLATES.map((t) => (
            <tr key={t.id} className="hover:bg-zinc-50 dark:hover:bg-zinc-900/40">
              <Td>{t.enabled ? <Badge tone="ok">Ativo</Badge> : <Badge tone="warn">Pausado</Badge>}</Td>
              <Td className="font-medium text-sm flex items-center gap-2"><FileText size={13} className="text-zinc-400" />{t.name}</Td>
              <Td><Badge tone="accent">{CHANNEL_LABELS[t.channel]}</Badge></Td>
              <Td className="text-xs capitalize">{t.category}</Td>
              <Td className="text-xs"><code className="font-mono text-zinc-500">{`{${t.variables.join(", ")}}`}</code></Td>
              <Td className="text-xs font-mono">{t.sent_30d.toLocaleString("pt-BR")}</Td>
              <Td className="text-xs">{t.open_rate ? `${(t.open_rate * 100).toFixed(0)}%` : "—"}</Td>
              <Td className="text-xs">{t.click_rate ? `${(t.click_rate * 100).toFixed(0)}%` : "—"}</Td>
              <Td className="text-xs text-zinc-500">{timeAgo(t.last_used)}</Td>
            </tr>
          ))}
        </tbody>
      </Table>
    </PageContainer>
  );
}
