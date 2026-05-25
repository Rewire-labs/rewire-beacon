import { PageHeader, PageContainer, Card, Badge, Table, Th, Td } from "@/components/beacon/ui";
import { DemoBanner } from "@/components/beacon/DemoBanner";
import { useMessagingSegments } from "@/lib/hooks/useBeacon";
import { Users, Filter } from "lucide-react";

// MSG-IMPL-001 (Lote 8): página segmentação umbrella.
// Lista audiences reutilizáveis com estimated_size + filtros.
export default function BeaconSegments() {
  const segments = useMessagingSegments();

  return (
    <PageContainer>
      {segments.isDemo && <DemoBanner detail="GET /v1/segments indisponivel" />}
      <PageHeader
        title="Segmentação"
        subtitle="Audiências reutilizáveis cross-canal: atributos + tags include/exclude + consent basis LGPD."
      />

      <Card className="p-5">
        <h3 className="text-sm font-semibold mb-3 flex items-center gap-2">
          <Users size={14} /> Segmentos definidos
        </h3>
        {segments.data.length === 0 ? (
          <p className="text-xs text-zinc-500 py-6 text-center">
            Nenhum segmento ainda. Crie via <code className="font-mono">POST /v1/segments</code>.
          </p>
        ) : (
          <Table>
            <thead>
              <tr>
                <Th>Nome</Th>
                <Th>Canal</Th>
                <Th>
                  <Filter size={11} className="inline mr-1" />
                  Filtros
                </Th>
                <Th>Tamanho est.</Th>
                <Th>Base legal</Th>
              </tr>
            </thead>
            <tbody>
              {segments.data.map((s) => (
                <tr key={s.id}>
                  <Td>
                    <div className="font-medium">{s.name}</div>
                    {s.description && (
                      <div className="text-[11px] text-zinc-500">{s.description}</div>
                    )}
                  </Td>
                  <Td>{s.channel}</Td>
                  <Td>
                    <div className="flex flex-wrap gap-1">
                      {s.include_tags.map((t) => (
                        <Badge key={`in-${t}`} tone="ok">
                          +{t}
                        </Badge>
                      ))}
                      {s.exclude_tags.map((t) => (
                        <Badge key={`ex-${t}`} tone="warn">
                          -{t}
                        </Badge>
                      ))}
                    </div>
                  </Td>
                  <Td>{s.estimated_size.toLocaleString("pt-BR")}</Td>
                  <Td>
                    <code className="text-[11px] font-mono">{s.consent_basis}</code>
                  </Td>
                </tr>
              ))}
            </tbody>
          </Table>
        )}
      </Card>
    </PageContainer>
  );
}
