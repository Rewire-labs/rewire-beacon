import { useEffect, useState } from "react";
import { PageHeader, PageContainer, Card, Badge, Table, Th, Td, timeAgo } from "@/components/beacon/ui";
import { DemoBanner } from "@/components/beacon/DemoBanner";
import { suppression, type SuppressionEntry, ApiError } from "@/lib/api";
import { SUPPRESSIONS } from "@/content/beacon-mock";
import { useBeaconSuppression } from "@/lib/hooks/useBeacon";
import { Ban, Plus, Trash2 } from "lucide-react";

const REASON_LABEL: Record<string, string> = {
  unsubscribe: "Opt-out usuario",
  hard_bounce: "Hard bounce",
  complaint: "Reclamou (spam)",
  manual: "Adicao manual",
  dsar: "Pedido DPO (LGPD)",
  invalid: "Invalido",
  blocked: "Bloqueado",
};

// BCN-234: BeaconSuppression — keep the legacy useState/useEffect path for
// the mutation flow (add/remove) and overlay the TanStack hook to drive
// the "Modo demo" banner when /v1/suppression is unreachable.
export default function BeaconSuppression() {
  const supQ = useBeaconSuppression({ limit: 100 });
  const [entries, setEntries] = useState<SuppressionEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [adding, setAdding] = useState(false);
  const [value, setValue] = useState("");
  const [type, setType] = useState("email");
  const [error, setError] = useState<string | null>(null);

  async function refresh() {
    setLoading(true);
    try {
      const list = await suppression.list({ limit: 100 });
      setEntries(list);
      setError(null);
    } catch (e) {
      if (e instanceof ApiError) setError(`API: ${e.status}`);
      setEntries([]);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void refresh(); }, []);

  async function handleAdd() {
    if (!value.trim()) return;
    try {
      await suppression.add({
        identifier_type: type, identifier_value: value, reason: "manual",
      });
      setValue("");
      setAdding(false);
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }

  async function handleRemove(id: string) {
    if (!confirm("Remover entrada? Esse identificador voltara a receber mensagens.")) return;
    await suppression.remove(id);
    await refresh();
  }

  const rows = entries.length ? entries : SUPPRESSIONS.map((s) => ({
    id: s.id, identifier_type: s.identifier_type, identifier_value: s.identifier_value,
    reason: s.reason, source_channel: null, created_at: s.added_at,
  } as SuppressionEntry));

  return (
    <PageContainer>
      {supQ.isDemo && <DemoBanner detail="GET /v1/suppression indisponivel" />}
      <PageHeader
        title="Suppression list cross-canal"
        subtitle="Lista unica por organizacao: opt-out de email vale para SMS, WhatsApp e push. LGPD Art. 18."
        actions={
          <button
            onClick={() => setAdding(true)}
            className="flex items-center gap-1.5 text-sm font-semibold bg-accent text-white px-3 py-2 rounded-md hover:bg-accent/90"
          >
            <Plus size={14} /> Adicionar
          </button>
        }
      />

      {error && <Card className="p-3 mb-4 text-xs text-amber-700 bg-amber-50">{error}</Card>}

      <Card className="p-4 mb-6 bg-amber-50 dark:bg-amber-950/20 border-amber-200 dark:border-amber-900/40">
        <div className="flex items-start gap-3 text-xs text-amber-800 dark:text-amber-300">
          <Ban size={14} className="mt-0.5" />
          <p><strong>Como funciona:</strong> hard bounces e complaints sao adicionados automaticamente. Toda mensagem e validada contra esta lista antes do envio {"(latencia <2ms via Postgres index)"}. Cliente pode auto-gerenciar via portal <code className="font-mono">{"/v1/u/<token>"}</code>.</p>
        </div>
      </Card>

      {adding && (
        <Card className="p-4 mb-4">
          <h3 className="text-sm font-semibold mb-2">Nova entrada</h3>
          <div className="flex gap-2 mb-2">
            <select value={type} onChange={(e) => setType(e.target.value)} className="text-sm border rounded-md px-2 py-1.5">
              <option value="email">email</option>
              <option value="phone_e164">phone_e164</option>
              <option value="push_token">push_token</option>
            </select>
            <input
              type="text" value={value} onChange={(e) => setValue(e.target.value)}
              placeholder="user@example.com ou +5511..."
              className="flex-1 text-sm border rounded-md px-3 py-1.5"
            />
          </div>
          <div className="flex gap-2">
            <button onClick={handleAdd} className="text-sm bg-accent text-white px-3 py-1.5 rounded-md">Adicionar</button>
            <button onClick={() => setAdding(false)} className="text-sm border px-3 py-1.5 rounded-md">Cancelar</button>
          </div>
        </Card>
      )}

      {loading ? <Card className="p-4 text-sm">Carregando...</Card> : (
        <Table>
          <thead>
            <tr>
              <Th>Identificador</Th><Th>Tipo</Th><Th>Motivo</Th><Th>Canal origem</Th><Th>Adicionado</Th><Th></Th>
            </tr>
          </thead>
          <tbody>
            {rows.map((s) => (
              <tr key={s.id} className="hover:bg-zinc-50 dark:hover:bg-zinc-900/40">
                <Td className="font-mono text-xs">{s.identifier_value}</Td>
                <Td><Badge>{s.identifier_type}</Badge></Td>
                <Td><Badge tone={s.reason === "dsar" ? "bad" : "warn"}>{REASON_LABEL[s.reason] ?? s.reason}</Badge></Td>
                <Td className="text-xs text-zinc-500">{s.source_channel ?? "—"}</Td>
                <Td className="text-xs text-zinc-500">{timeAgo(s.created_at)}</Td>
                <Td>
                  <button onClick={() => handleRemove(s.id)} className="text-zinc-400 hover:text-red-600">
                    <Trash2 size={13} />
                  </button>
                </Td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}
    </PageContainer>
  );
}
