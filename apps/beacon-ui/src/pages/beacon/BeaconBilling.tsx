import { PageHeader, PageContainer, Card, Table, Th, Td } from "@/components/beacon/ui";
import { DemoBanner } from "@/components/beacon/DemoBanner";
import { BEACON_USER, BILLING_BREAKDOWN, TIER_LABELS } from "@/content/beacon-mock";
import { useBeaconBilling } from "@/lib/hooks/useBeacon";
import { Receipt, Download, FileText, TrendingUp } from "lucide-react";

// BCN-243: BeaconBilling wired to /v1/billing/* via TanStack hook.
export default function BeaconBilling() {
  const billingQ = useBeaconBilling();
  const usage = billingQ.usage.data.counts;
  const liveEmail = usage?.email ?? BEACON_USER.mtd_email;
  const liveSms = usage?.sms ?? BEACON_USER.mtd_sms;
  const liveWa = usage?.whatsapp ?? BEACON_USER.mtd_wa;
  const total = BILLING_BREAKDOWN.reduce((s, b) => s + b.total_brl, 0);
  return (
    <PageContainer>
      {billingQ.isDemo && <DemoBanner detail="GET /v1/billing/* indisponivel" />}
      <PageHeader
        title="Billing & uso"
        subtitle={`Plano ${TIER_LABELS[BEACON_USER.tier]} · faturamento mensal via Asaas BR · NF-e emitida automaticamente. Anti-bill-shock: limite global R$ ${BEACON_USER.mtd_cap_brl.toLocaleString("pt-BR")} ativo.`}
        actions={
          <>
            <button className="flex items-center gap-1.5 text-xs font-semibold border border-zinc-200 dark:border-zinc-800 px-3 py-2 rounded-md"><FileText size={13} /> Baixar NF-e</button>
            <button className="flex items-center gap-1.5 text-sm font-semibold bg-accent text-white px-3 py-2 rounded-md"><Download size={14} /> Export CSV</button>
          </>
        }
      />

      <div className="grid md:grid-cols-4 gap-3 mb-6">
        <Card className="p-4">
          <p className="text-[10px] uppercase tracking-wider text-zinc-500 font-semibold">Total MTD</p>
          <p className="text-2xl font-bold mt-1">R$ {total.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}</p>
        </Card>
        <Card className="p-4">
          <p className="text-[10px] uppercase tracking-wider text-zinc-500 font-semibold">Email</p>
          <p className="text-2xl font-bold mt-1">{liveEmail.toLocaleString("pt-BR")}</p>
          <p className="text-[10px] text-zinc-500">de {BEACON_USER.mtd_email_quota.toLocaleString("pt-BR")}</p>
        </Card>
        <Card className="p-4">
          <p className="text-[10px] uppercase tracking-wider text-zinc-500 font-semibold">SMS BR</p>
          <p className="text-2xl font-bold mt-1">{liveSms.toLocaleString("pt-BR")}</p>
          <p className="text-[10px] text-zinc-500">de {BEACON_USER.mtd_sms_quota.toLocaleString("pt-BR")}</p>
        </Card>
        <Card className="p-4">
          <p className="text-[10px] uppercase tracking-wider text-zinc-500 font-semibold">WhatsApp</p>
          <p className="text-2xl font-bold mt-1">{liveWa.toLocaleString("pt-BR")}</p>
          <p className="text-[10px] text-zinc-500">de {BEACON_USER.mtd_wa_quota.toLocaleString("pt-BR")}</p>
        </Card>
      </div>

      <Card className="p-5 mb-6">
        <h3 className="text-sm font-semibold mb-3 flex items-center gap-2"><TrendingUp size={14} /> Detalhamento MTD</h3>
        <Table>
          <thead><tr><Th>Item</Th><Th>Qtd</Th><Th>Unitário</Th><Th>Total</Th></tr></thead>
          <tbody>
            {BILLING_BREAKDOWN.map((b) => (
              <tr key={b.item}>
                <Td className="text-sm">{b.item}</Td>
                <Td className="text-xs font-mono">{b.qty.toLocaleString("pt-BR")}</Td>
                <Td className="text-xs font-mono text-zinc-500">{b.unit}</Td>
                <Td className="text-sm font-semibold">R$ {b.total_brl.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}</Td>
              </tr>
            ))}
            <tr className="bg-zinc-50 dark:bg-zinc-900/40">
              <Td className="font-bold text-sm" >Total acumulado</Td><Td>—</Td><Td>—</Td>
              <Td className="font-bold text-base">R$ {total.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}</Td>
            </tr>
          </tbody>
        </Table>
      </Card>

      <Card className="p-5 flex items-center gap-3 bg-emerald-50 dark:bg-emerald-950/20 border-emerald-200 dark:border-emerald-900/40">
        <Receipt size={18} className="text-emerald-600 dark:text-emerald-400" />
        <p className="text-xs text-emerald-800 dark:text-emerald-300">NF-e emitida automaticamente todo dia 1 via Asaas. CNPJ <strong className="font-mono">{BEACON_USER.cnpj}</strong> · pagamento default PIX (desconto 2%) ou boleto.</p>
      </Card>
    </PageContainer>
  );
}
