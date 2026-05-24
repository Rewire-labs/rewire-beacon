import { PageHeader, PageContainer, Card, ScoreBar, Table, Th, Td, Badge } from "@/components/beacon/ui";
import { DemoBanner } from "@/components/beacon/DemoBanner";
import { DELIVERABILITY, CHANNEL_LABELS, type Channel } from "@/content/beacon-mock";
import { useBeaconDeliverability } from "@/lib/hooks/useBeacon";
import { BellRing } from "lucide-react";

// BCN-245: BeaconDeliverability wired to /v1/deliverability/reputation.
export default function BeaconDeliverability() {
  const delivQ = useBeaconDeliverability();
  return (
    <PageContainer>
      {delivQ.isDemo && <DemoBanner detail="GET /v1/deliverability/reputation indisponivel" />}
      <PageHeader
        title="Deliverability"
        subtitle="Postal IPs próprios + AWS SES BR fallback para email. APNs/FCM para push (grátis). Zenvia/TotalVoice para SMS via operadoras BR. Alvo: >98% delivered."
      />

      <Card className="p-4 mb-6 bg-emerald-50 dark:bg-emerald-950/20 border-emerald-200 dark:border-emerald-900/40">
        <div className="flex items-start gap-3 text-xs text-emerald-800 dark:text-emerald-300">
          <BellRing size={14} className="mt-0.5" />
          <p><strong>Deliverability é o killer feature.</strong> IP warming gradual em 30 dias para novos IPs, DKIM/SPF/DMARC automático, complaint loop processing (Gmail, Outlook, UOL, Locaweb, Yahoo, AOL), hard bounce → suppression cross-canal instantâneo.</p>
        </div>
      </Card>

      <Table>
        <thead><tr><Th>Provider</Th><Th>Canal</Th><Th>Delivered</Th><Th>Bounce</Th><Th>Complaints</Th><Th>Reputation</Th></tr></thead>
        <tbody>
          {DELIVERABILITY.map((d) => (
            <tr key={d.provider}>
              <Td className="font-medium text-sm">{d.provider}</Td>
              <Td><Badge tone="accent">{CHANNEL_LABELS[d.channel as Channel]}</Badge></Td>
              <Td className="text-xs font-semibold text-emerald-600 dark:text-emerald-400">{(d.delivered_rate * 100).toFixed(2)}%</Td>
              <Td className="text-xs">{(d.bounce_rate * 100).toFixed(2)}%</Td>
              <Td className="text-xs">{(d.complaint_rate * 100).toFixed(3)}%</Td>
              <Td>
                <div className="flex items-center gap-2">
                  <span className="text-xs font-semibold w-8">{d.reputation}</span>
                  <div className="w-24"><ScoreBar score={d.reputation} /></div>
                </div>
              </Td>
            </tr>
          ))}
        </tbody>
      </Table>
    </PageContainer>
  );
}
