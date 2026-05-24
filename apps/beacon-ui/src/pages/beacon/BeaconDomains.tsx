import { useEffect, useState } from "react";
import { PageHeader, PageContainer, Card, Badge, ScoreBar } from "@/components/beacon/ui";
import { DemoBanner } from "@/components/beacon/DemoBanner";
import { domains, type EmailDomain, ApiError } from "@/lib/api";
import { DOMAINS } from "@/content/beacon-mock";
import { useBeaconDomains } from "@/lib/hooks/useBeacon";
import { Plus, Globe, Check, X, Copy } from "lucide-react";

interface DomainRow extends EmailDomain {
  daily_limit?: number;
  sent_30d?: number;
}

// BCN-235: BeaconDomains — wire TanStack hook for the demo-banner signal
// while keeping the existing useState/useEffect mutation path.
export default function BeaconDomains() {
  const domainsQ = useBeaconDomains();
  const [rows, setRows] = useState<EmailDomain[]>([]);
  const [loading, setLoading] = useState(true);
  const [adding, setAdding] = useState(false);
  const [newDomain, setNewDomain] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function refresh() {
    setLoading(true);
    try {
      const list = await domains.list();
      setRows(list);
      setError(null);
    } catch (e) {
      if (e instanceof ApiError) setError(`API ${e.status}`);
      setRows([]);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void refresh(); }, []);

  async function handleCreate() {
    if (!newDomain.match(/^[a-z0-9.-]+\.[a-z]{2,}$/i)) {
      setError("dominio invalido");
      return;
    }
    try {
      await domains.create(newDomain.toLowerCase());
      setNewDomain("");
      setAdding(false);
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }

  async function handleVerify(id: string) {
    try {
      await domains.verify(id);
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }

  const displayRows: DomainRow[] = rows.length ? rows : DOMAINS.map((d) => ({
    id: d.id, domain: d.domain, verified: d.verified,
    spf_status: d.spf_verified ? "pass" : "pending",
    dmarc_status: d.dmarc_verified ? "pass" : "pending",
    reputation_score: d.reputation, created_at: new Date().toISOString(),
    verified_at: d.verified ? new Date().toISOString() : null,
    daily_limit: d.daily_limit, sent_30d: d.sent_30d,
  }));

  return (
    <PageContainer>
      {domainsQ.isDemo && <DemoBanner detail="GET /v1/domains indisponivel" />}
      <PageHeader
        title="Email - Dominios"
        subtitle="DKIM 2048-bit gerado automaticamente pelo Postal. SPF assistido + DMARC reporting agregado."
        actions={
          <button
            onClick={() => setAdding(true)}
            className="flex items-center gap-1.5 text-sm font-semibold bg-accent text-white px-3 py-2 rounded-md hover:bg-accent/90"
          >
            <Plus size={14} /> Adicionar dominio
          </button>
        }
      />

      {error && <Card className="p-3 mb-4 text-xs text-amber-700 bg-amber-50">{error}</Card>}

      {adding && (
        <Card className="p-4 mb-4">
          <h3 className="text-sm font-semibold mb-2">Adicionar dominio</h3>
          <div className="flex gap-2 mb-2">
            <input
              value={newDomain} onChange={(e) => setNewDomain(e.target.value)}
              placeholder="empresa.com.br"
              className="flex-1 text-sm border rounded-md px-3 py-1.5 font-mono"
            />
            <button onClick={handleCreate} className="text-sm bg-accent text-white px-3 py-1.5 rounded-md">Criar</button>
            <button onClick={() => setAdding(false)} className="text-sm border px-3 py-1.5 rounded-md">Cancelar</button>
          </div>
          <p className="text-[11px] text-zinc-500">Apos criar, configure os DNS records exibidos e clique em "Verificar".</p>
        </Card>
      )}

      {loading ? <Card className="p-4 text-sm">Carregando...</Card> : (
        <div className="grid md:grid-cols-2 gap-4 mb-6">
          {displayRows.map((d) => (
            <Card key={d.id} className="p-5">
              <div className="flex items-start gap-3 mb-3">
                <div className="w-9 h-9 rounded-md bg-accent/10 flex items-center justify-center text-accent">
                  <Globe size={16} />
                </div>
                <div className="flex-1">
                  <h3 className="text-sm font-semibold font-mono">{d.domain}</h3>
                  <p className="text-[11px] text-zinc-500 mt-0.5">
                    {d.daily_limit ? `Limite ${d.daily_limit.toLocaleString("pt-BR")}/dia` : "Pool Postal compartilhado"}
                  </p>
                </div>
                {d.verified ? <Badge tone="ok">Verificado</Badge> : <Badge tone="warn">Pendente</Badge>}
              </div>

              <div className="grid grid-cols-3 gap-2 text-xs mb-3">
                <div className={`flex items-center gap-1 ${d.verified ? "text-emerald-600" : "text-amber-600"}`}>
                  {d.verified ? <Check size={12} /> : <X size={12} />} DKIM
                </div>
                <div className={`flex items-center gap-1 ${d.spf_status === "pass" ? "text-emerald-600" : "text-amber-600"}`}>
                  {d.spf_status === "pass" ? <Check size={12} /> : <X size={12} />} SPF
                </div>
                <div className={`flex items-center gap-1 ${d.dmarc_status === "pass" ? "text-emerald-600" : "text-amber-600"}`}>
                  {d.dmarc_status === "pass" ? <Check size={12} /> : <X size={12} />} DMARC
                </div>
              </div>

              <div className="mb-3">
                <div className="flex items-center justify-between text-[11px] mb-1">
                  <span className="text-zinc-500">Reputation Postal</span>
                  <span className="font-semibold">{d.reputation_score}/100</span>
                </div>
                <ScoreBar score={d.reputation_score} />
              </div>

              <div className="text-xs text-zinc-500 flex items-center justify-between border-t border-zinc-100 dark:border-zinc-800 pt-3">
                <span>{d.sent_30d ? `${d.sent_30d.toLocaleString("pt-BR")} envios em 30d` : "—"}</span>
                {!d.verified ? (
                  <button onClick={() => handleVerify(d.id)} className="text-accent hover:underline font-semibold">Verificar</button>
                ) : (
                  <button className="flex items-center gap-1 hover:text-zinc-900 dark:hover:text-white"><Copy size={11} /> DNS</button>
                )}
              </div>
            </Card>
          ))}
        </div>
      )}
    </PageContainer>
  );
}
