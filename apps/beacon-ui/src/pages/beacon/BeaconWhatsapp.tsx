import { PageHeader, PageContainer, Card, Badge } from "@/components/beacon/ui";
import { DemoBanner } from "@/components/beacon/DemoBanner";
import { WA_NUMBERS } from "@/content/beacon-mock";
import { useBeaconWhatsapp } from "@/lib/hooks/useBeacon";
import { MessageSquare, Plus, ExternalLink } from "lucide-react";

const QUALITY_TONE: Record<string, "ok" | "warn" | "bad"> = { green: "ok", yellow: "warn", red: "bad" };
const TIER_LABEL: Record<string, string> = {
  tier_1k: "1k msgs/24h", tier_10k: "10k msgs/24h", tier_100k: "100k msgs/24h", tier_unlimited: "Ilimitado",
};

// BCN-237: BeaconWhatsapp wired to /v1/whatsapp via TanStack hooks.
export default function BeaconWhatsapp() {
  const wa = useBeaconWhatsapp();
  return (
    <PageContainer>
      {wa.isDemo && <DemoBanner detail="GET /v1/whatsapp indisponivel (depende CONNECT GA)" />}
      <PageHeader
        title="WhatsApp Business (via CONNECT)"
        subtitle="BEACON delega envio WhatsApp para CONNECT API interna. Templates aprovados Meta sincronizados. Janelas 24h e quality rating gerenciados pelo CONNECT."
        actions={
          <>
            <a href="/app/produtos/connect" className="flex items-center gap-1.5 text-xs font-semibold border border-zinc-200 dark:border-zinc-800 px-3 py-2 rounded-md hover:bg-zinc-50 dark:hover:bg-zinc-800"><ExternalLink size={13} /> Abrir CONNECT</a>
            <button className="flex items-center gap-1.5 text-sm font-semibold bg-accent text-white px-3 py-2 rounded-md hover:bg-accent/90"><Plus size={14} /> Vincular número</button>
          </>
        }
      />

      <Card className="p-4 mb-6 bg-accent/5 border-accent/30">
        <div className="flex items-start gap-3 text-xs text-zinc-700 dark:text-zinc-300">
          <MessageSquare size={14} className="mt-0.5 text-accent" />
          <p><strong>Como funciona:</strong> seu cliente faz <code className="font-mono">POST /v1/messages/whatsapp</code> no BEACON com o número CONNECT já vinculado. BEACON resolve template, valida suppression list, ancora chain BLAKE3 e chama <code className="font-mono">CONNECT /internal/whatsapp/send</code>. Cobrança consolida tudo via Asaas.</p>
        </div>
      </Card>

      <div className="grid md:grid-cols-2 gap-4">
        {WA_NUMBERS.map((w) => (
          <Card key={w.id} className="p-5">
            <div className="flex items-start gap-3 mb-3">
              <div className="w-9 h-9 rounded-md bg-emerald-100 dark:bg-emerald-950/40 flex items-center justify-center text-emerald-600 dark:text-emerald-400"><MessageSquare size={16} /></div>
              <div className="flex-1">
                <h3 className="text-sm font-semibold font-mono">{w.number}</h3>
                <p className="text-[11px] text-zinc-500 mt-0.5">CONNECT id <code className="font-mono">cn_wa_{w.id.slice(3)}</code></p>
              </div>
              <Badge tone={QUALITY_TONE[w.quality]}>{w.quality.toUpperCase()}</Badge>
            </div>

            <div className="grid grid-cols-3 gap-2 text-center mb-3">
              <div><p className="text-base font-bold">{w.templates_approved}</p><p className="text-[10px] text-zinc-500">templates Meta</p></div>
              <div><p className="text-base font-bold">{TIER_LABEL[w.tier]}</p><p className="text-[10px] text-zinc-500">messaging tier</p></div>
              <div><p className="text-base font-bold">{w.sent_30d.toLocaleString("pt-BR")}</p><p className="text-[10px] text-zinc-500">enviadas 30d</p></div>
            </div>

            <p className="text-[11px] text-zinc-500 border-t border-zinc-100 dark:border-zinc-800 pt-3">
              Custo: utility ≈ R$ 0,15 · marketing ≈ R$ 0,40 (pass-through Meta + markup 30%).
            </p>
          </Card>
        ))}
      </div>
    </PageContainer>
  );
}
