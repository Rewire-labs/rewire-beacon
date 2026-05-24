import { PageHeader, PageContainer, Card, Badge, Table, Th, Td } from "@/components/beacon/ui";
import { DemoBanner } from "@/components/beacon/DemoBanner";
import { SMS_NUMBERS } from "@/content/beacon-mock";
import { useBeaconSmsNumbers } from "@/lib/hooks/useBeacon";
import { Plus, Phone } from "lucide-react";

// BCN-236: BeaconSmsNumbers wired to /v1/sms-numbers.
export default function BeaconSmsNumbers() {
  const smsQ = useBeaconSmsNumbers();
  return (
    <PageContainer>
      {smsQ.isDemo && <DemoBanner detail="GET /v1/sms-numbers indisponivel" />}
      <PageHeader
        title="SMS · Números BR"
        subtitle="Short codes (5 dígitos) para alto volume e long codes (DDD +55) via Zenvia (primário) + TotalVoice (fallback). Cobertura nacional Vivo/TIM/Claro/Oi."
        actions={<button className="flex items-center gap-1.5 text-sm font-semibold bg-accent text-white px-3 py-2 rounded-md hover:bg-accent/90"><Plus size={14} /> Provisionar número</button>}
      />

      <div className="grid md:grid-cols-3 gap-4 mb-6">
        <Card className="p-5">
          <p className="text-[11px] uppercase tracking-wider font-semibold text-zinc-500">Short codes (alto volume)</p>
          <p className="text-2xl font-bold mt-1">{SMS_NUMBERS.filter((n) => n.type === "short_code").length}</p>
          <p className="text-[11px] text-zinc-500 mt-1">Disponível Scale+ · throughput 1.000 msg/s</p>
        </Card>
        <Card className="p-5">
          <p className="text-[11px] uppercase tracking-wider font-semibold text-zinc-500">Long codes</p>
          <p className="text-2xl font-bold mt-1">{SMS_NUMBERS.filter((n) => n.type === "long_code").length}</p>
          <p className="text-[11px] text-zinc-500 mt-1">Two-way habilitado · webhook de respostas</p>
        </Card>
        <Card className="p-5">
          <p className="text-[11px] uppercase tracking-wider font-semibold text-zinc-500">Custo médio</p>
          <p className="text-2xl font-bold mt-1">R$ 0,085</p>
          <p className="text-[11px] text-zinc-500 mt-1">por SMS BR · markup 30% sobre BSP</p>
        </Card>
      </div>

      <Table>
        <thead><tr><Th>Número</Th><Th>Tipo</Th><Th>Provider</Th><Th>Two-way</Th><Th>Enviadas 30d</Th></tr></thead>
        <tbody>
          {SMS_NUMBERS.map((n) => (
            <tr key={n.id} className="hover:bg-zinc-50 dark:hover:bg-zinc-900/40">
              <Td className="font-mono text-sm flex items-center gap-2"><Phone size={13} className="text-zinc-400" /> {n.number}</Td>
              <Td><Badge tone="accent">{n.type === "short_code" ? "Short code" : "Long code"}</Badge></Td>
              <Td className="text-xs capitalize">{n.provider}</Td>
              <Td>{n.two_way ? <Badge tone="ok">Sim</Badge> : <Badge>Não</Badge>}</Td>
              <Td className="text-xs font-mono">{n.sent_30d.toLocaleString("pt-BR")}</Td>
            </tr>
          ))}
        </tbody>
      </Table>
    </PageContainer>
  );
}
