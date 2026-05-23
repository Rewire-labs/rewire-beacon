import { PageHeader, PageContainer, Card, Badge, ScoreBar, Table, Th, Td } from "@/components/beacon/ui";
import { DOMAINS } from "@/content/beacon-mock";
import { Plus, Globe, Check, X, Copy } from "lucide-react";

export default function BeaconDomains() {
  return (
    <PageContainer>
      <PageHeader
        title="Email · Domínios"
        subtitle="DKIM 2048-bit gerado automaticamente pelo Postal. SPF assistido + DMARC reporting agregado. Reputation score 0–100 atualizado em tempo real."
        actions={<button className="flex items-center gap-1.5 text-sm font-semibold bg-accent text-white px-3 py-2 rounded-md hover:bg-accent/90"><Plus size={14} /> Adicionar domínio</button>}
      />

      <div className="grid md:grid-cols-2 gap-4 mb-6">
        {DOMAINS.map((d) => (
          <Card key={d.id} className="p-5">
            <div className="flex items-start gap-3 mb-3">
              <div className="w-9 h-9 rounded-md bg-accent/10 flex items-center justify-center text-accent"><Globe size={16} /></div>
              <div className="flex-1">
                <h3 className="text-sm font-semibold font-mono">{d.domain}</h3>
                <p className="text-[11px] text-zinc-500 mt-0.5">{d.dedicated_ip ? `IP dedicado ${d.dedicated_ip}` : "IP compartilhado pool Postal"} · limite {d.daily_limit.toLocaleString("pt-BR")}/dia</p>
              </div>
              {d.verified ? <Badge tone="ok">Verificado</Badge> : <Badge tone="warn">Pendente</Badge>}
            </div>

            <div className="grid grid-cols-3 gap-2 text-xs mb-3">
              <div className={`flex items-center gap-1 ${d.dkim_verified ? "text-emerald-600 dark:text-emerald-400" : "text-amber-600 dark:text-amber-400"}`}>
                {d.dkim_verified ? <Check size={12} /> : <X size={12} />} DKIM
              </div>
              <div className={`flex items-center gap-1 ${d.spf_verified ? "text-emerald-600 dark:text-emerald-400" : "text-amber-600 dark:text-amber-400"}`}>
                {d.spf_verified ? <Check size={12} /> : <X size={12} />} SPF
              </div>
              <div className={`flex items-center gap-1 ${d.dmarc_verified ? "text-emerald-600 dark:text-emerald-400" : "text-amber-600 dark:text-amber-400"}`}>
                {d.dmarc_verified ? <Check size={12} /> : <X size={12} />} DMARC
              </div>
            </div>

            <div className="mb-3">
              <div className="flex items-center justify-between text-[11px] mb-1">
                <span className="text-zinc-500">Reputation Postal</span>
                <span className="font-semibold">{d.reputation}/100</span>
              </div>
              <ScoreBar score={d.reputation} />
            </div>

            <div className="text-xs text-zinc-500 flex items-center justify-between border-t border-zinc-100 dark:border-zinc-800 pt-3">
              <span>{d.sent_30d.toLocaleString("pt-BR")} envios em 30d</span>
              <button className="flex items-center gap-1 hover:text-zinc-900 dark:hover:text-white"><Copy size={11} /> Copiar DNS records</button>
            </div>
          </Card>
        ))}
      </div>

      <Card className="p-5">
        <h3 className="text-sm font-semibold mb-3">DNS records sugeridos</h3>
        <Table>
          <thead><tr><Th>Tipo</Th><Th>Host</Th><Th>Valor</Th></tr></thead>
          <tbody>
            <tr><Td><Badge>TXT</Badge></Td><Td className="font-mono text-xs">beacon._domainkey.pampapay.com.br</Td><Td className="font-mono text-xs truncate max-w-[400px]">v=DKIM1; k=rsa; p=MIIBIjANBgkqhkiG9w0BAQEF...</Td></tr>
            <tr><Td><Badge>TXT</Badge></Td><Td className="font-mono text-xs">pampapay.com.br</Td><Td className="font-mono text-xs">v=spf1 include:_spf.beacon.rewirelabs.dev ~all</Td></tr>
            <tr><Td><Badge>TXT</Badge></Td><Td className="font-mono text-xs">_dmarc.pampapay.com.br</Td><Td className="font-mono text-xs">v=DMARC1; p=quarantine; rua=mailto:dmarc@pampapay.com.br</Td></tr>
          </tbody>
        </Table>
      </Card>
    </PageContainer>
  );
}
