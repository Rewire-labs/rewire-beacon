import { PageHeader, PageContainer, Card, Badge, Table, Th, Td, timeAgo } from "@/components/beacon/ui";
import { SUPPRESSIONS } from "@/content/beacon-mock";
import { Ban, Plus, Upload } from "lucide-react";

const REASON_LABEL: Record<string, string> = {
  user_unsubscribed: "Opt-out usuário",
  hard_bounce: "Hard bounce",
  complaint: "Reclamou (spam)",
  manual: "Adição manual",
  dpo_request: "Pedido DPO (LGPD)",
};

export default function BeaconSuppression() {
  return (
    <PageContainer>
      <PageHeader
        title="Suppression list cross-canal"
        subtitle="Lista única por organização: opt-out de email vale para SMS, WhatsApp e push. Compliance LGPD Art. 18 — direito ao opt-out garantido."
        actions={
          <>
            <button className="flex items-center gap-1.5 text-xs font-semibold border border-zinc-200 dark:border-zinc-800 px-3 py-2 rounded-md hover:bg-zinc-50 dark:hover:bg-zinc-800"><Upload size={13} /> Importar CSV</button>
            <button className="flex items-center gap-1.5 text-sm font-semibold bg-accent text-white px-3 py-2 rounded-md hover:bg-accent/90"><Plus size={14} /> Adicionar</button>
          </>
        }
      />

      <Card className="p-4 mb-6 bg-amber-50 dark:bg-amber-950/20 border-amber-200 dark:border-amber-900/40">
        <div className="flex items-start gap-3 text-xs text-amber-800 dark:text-amber-300">
          <Ban size={14} className="mt-0.5" />
          <p><strong>Como funciona:</strong> hard bounces e complaints são adicionados automaticamente. Toda mensagem é validada contra esta lista antes do envio {"(latência <2ms via Postgres index)"}. Cliente pode auto-gerenciar via portal <code className="font-mono">{"/u/<token>"}</code>.</p>
        </div>
      </Card>

      <Table>
        <thead>
          <tr>
            <Th>Identificador</Th><Th>Tipo</Th><Th>Canais bloqueados</Th><Th>Motivo</Th><Th>Adicionado</Th>
          </tr>
        </thead>
        <tbody>
          {SUPPRESSIONS.map((s) => (
            <tr key={s.id} className="hover:bg-zinc-50 dark:hover:bg-zinc-900/40">
              <Td className="font-mono text-xs">{s.identifier_value}</Td>
              <Td><Badge>{s.identifier_type}</Badge></Td>
              <Td className="text-xs">
                <div className="flex flex-wrap gap-1">
                  {s.channels.map((c) => <Badge key={c} tone="accent">{c}</Badge>)}
                </div>
              </Td>
              <Td><Badge tone={s.reason === "dpo_request" ? "bad" : "warn"}>{REASON_LABEL[s.reason]}</Badge></Td>
              <Td className="text-xs text-zinc-500">{timeAgo(s.added_at)}</Td>
            </tr>
          ))}
        </tbody>
      </Table>
    </PageContainer>
  );
}
