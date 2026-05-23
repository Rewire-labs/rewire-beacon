import { useEffect, useState } from "react";
import { PageHeader, PageContainer, Card, Badge, Table, Th, Td, timeAgo } from "@/components/beacon/ui";
import { apiTokens, type ApiToken, ApiError } from "@/lib/api";
import { API_KEYS } from "@/content/beacon-mock";
import { Plus, KeyRound, Copy, Eye, Trash2 } from "lucide-react";

export default function BeaconApiKeys() {
  const [tokens, setTokens] = useState<ApiToken[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [newName, setNewName] = useState("");
  const [revealedToken, setRevealedToken] = useState<string | null>(null);

  async function refresh() {
    setLoading(true);
    try {
      const list = await apiTokens.list();
      setTokens(list);
      setError(null);
    } catch (e) {
      // Fall back to mock when API unreachable in dev.
      if (e instanceof ApiError && e.status === 0) {
        setTokens([]);
        setError("API offline — showing mock data");
      } else if (e instanceof Error) {
        setError(e.message);
      }
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void refresh();
  }, []);

  async function handleCreate() {
    if (!newName.trim()) return;
    try {
      const created = await apiTokens.create({ name: newName });
      setRevealedToken(created.token);
      setNewName("");
      setCreating(false);
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }

  async function handleRevoke(id: string) {
    if (!confirm("Revogar este token? Aplicacoes que o usam vao falhar.")) return;
    try {
      await apiTokens.revoke(id);
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }

  const rows = tokens.length ? tokens : API_KEYS.map((k) => ({
    id: k.id, name: k.name, token_prefix: k.prefix, scopes: k.scopes,
    last_used_at: k.last_used, expires_at: null, revoked_at: null, created_at: k.created_at,
  } as ApiToken));

  return (
    <PageContainer>
      <PageHeader
        title="API keys"
        subtitle="Tokens por tenant via Authentik OIDC + scopes granulares. Use Bearer auth no header `Authorization: Bearer bcn_live_...`."
        actions={
          <button
            onClick={() => setCreating(true)}
            className="flex items-center gap-1.5 text-sm font-semibold bg-accent text-white px-3 py-2 rounded-md hover:bg-accent/90"
          >
            <Plus size={14} /> Nova API key
          </button>
        }
      />

      {error && <Card className="p-3 mb-4 text-xs text-amber-700 bg-amber-50 dark:bg-amber-950/30">{error}</Card>}

      {revealedToken && (
        <Card className="p-4 mb-4 border-2 border-accent">
          <p className="text-xs font-semibold mb-1">Copie o token agora — nao podera ser exibido novamente:</p>
          <pre className="text-[11px] font-mono bg-zinc-50 dark:bg-zinc-900 p-3 rounded-md overflow-x-auto"><code>{revealedToken}</code></pre>
          <button
            onClick={() => { navigator.clipboard.writeText(revealedToken); setRevealedToken(null); }}
            className="flex items-center gap-1.5 text-[11px] text-accent mt-2 hover:underline"
          >
            <Copy size={11} /> Copiar e fechar
          </button>
        </Card>
      )}

      {creating && (
        <Card className="p-4 mb-4">
          <h3 className="text-sm font-semibold mb-2">Nova API key</h3>
          <input
            type="text"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            placeholder="Nome (ex: production-app)"
            className="w-full text-sm border rounded-md px-3 py-2 mb-2"
          />
          <div className="flex gap-2">
            <button onClick={handleCreate} className="text-sm bg-accent text-white px-3 py-1.5 rounded-md">Criar</button>
            <button onClick={() => setCreating(false)} className="text-sm border px-3 py-1.5 rounded-md">Cancelar</button>
          </div>
        </Card>
      )}

      <Card className="p-5 mb-6">
        <h3 className="text-sm font-semibold mb-2">Quickstart — enviar email</h3>
        <pre className="text-[11px] font-mono bg-zinc-50 dark:bg-zinc-900 p-3 rounded-md overflow-x-auto"><code>{`curl -X POST https://api.beacon.rewirelabs.dev/v1/messages/email \\
  -H "Authorization: Bearer bcn_live_4k9..." \\
  -H "Content-Type: application/json" \\
  -d '{
    "sender": "no-reply@pampapay.com.br",
    "to": ["cliente@exemplo.com"],
    "subject": "Pedido confirmado",
    "template_slug": "tpl_order_confirmation",
    "consent_basis": "contract"
  }'`}</code></pre>
      </Card>

      {loading ? <Card className="p-4 text-sm">Carregando...</Card> : (
        <Table>
          <thead><tr><Th>Nome</Th><Th>Prefix</Th><Th>Scopes</Th><Th>Criada</Th><Th>Ultimo uso</Th><Th></Th></tr></thead>
          <tbody>
            {rows.map((k) => (
              <tr key={k.id} className="hover:bg-zinc-50 dark:hover:bg-zinc-900/40">
                <Td className="font-medium text-sm flex items-center gap-2"><KeyRound size={13} className="text-zinc-400" /> {k.name}</Td>
                <Td className="font-mono text-xs">{k.token_prefix}</Td>
                <Td className="text-xs">
                  <div className="flex flex-wrap gap-1">
                    {k.scopes.map((s) => <Badge key={s} tone="accent">{s}</Badge>)}
                  </div>
                </Td>
                <Td className="text-xs text-zinc-500">{timeAgo(k.created_at)}</Td>
                <Td className="text-xs text-zinc-500">{k.last_used_at ? timeAgo(k.last_used_at) : "nunca"}</Td>
                <Td>
                  <button
                    onClick={() => handleRevoke(k.id)}
                    className="text-zinc-400 hover:text-red-600"
                    title="Revogar"
                  >
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
