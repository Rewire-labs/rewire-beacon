import { useState } from "react";

import { PageHeader, PageContainer, Card, Badge, Table, Th, Td } from "@/components/beacon/ui";
import { DemoBanner } from "@/components/beacon/DemoBanner";
import { useMessagingAbTests, useMessagingAbResults } from "@/lib/hooks/useBeacon";
import { FlaskConical, Award, TrendingUp } from "lucide-react";

// MSG-IMPL-001 (Lote 8): página A/B tests umbrella (multi-canal).
// Lista experimentos + drill-down para resultados (chi-square ≥95%).
export default function BeaconAbTests() {
  const tests = useMessagingAbTests();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const results = useMessagingAbResults(selectedId);

  return (
    <PageContainer>
      {tests.isDemo && <DemoBanner detail="GET /v1/ab-tests indisponivel" />}
      <PageHeader
        title="A/B tests"
        subtitle="Experimentos multi-canal com winner detection automático (chi-square ≥95%)."
      />

      <div className="grid lg:grid-cols-3 gap-4">
        <Card className="p-5 lg:col-span-2">
          <h3 className="text-sm font-semibold mb-3 flex items-center gap-2">
            <FlaskConical size={14} /> Experimentos
          </h3>
          {tests.data.length === 0 ? (
            <p className="text-xs text-zinc-500 py-6 text-center">
              Nenhum experimento ativo. Crie via <code className="font-mono">POST /v1/ab-tests</code>.
            </p>
          ) : (
            <Table>
              <thead>
                <tr>
                  <Th>Nome</Th>
                  <Th>Canal</Th>
                  <Th>Variantes</Th>
                  <Th>Métrica</Th>
                  <Th>Status</Th>
                </tr>
              </thead>
              <tbody>
                {tests.data.map((t) => (
                  <tr
                    key={t.id}
                    onClick={() => setSelectedId(t.id)}
                    className={`cursor-pointer ${selectedId === t.id ? "bg-accent/5" : ""}`}
                  >
                    <Td>{t.name}</Td>
                    <Td>{t.channel}</Td>
                    <Td>{t.variants.length}</Td>
                    <Td>{t.primary_metric}</Td>
                    <Td>
                      <Badge tone={t.status === "running" ? "ok" : "warn"}>{t.status}</Badge>
                    </Td>
                  </tr>
                ))}
              </tbody>
            </Table>
          )}
        </Card>

        <Card className="p-5">
          <h3 className="text-sm font-semibold mb-3 flex items-center gap-2">
            <Award size={14} /> Resultado
          </h3>
          {!selectedId ? (
            <p className="text-xs text-zinc-500 py-6 text-center">
              Selecione um experimento para ver agregados.
            </p>
          ) : (
            <div className="space-y-3">
              <div className="text-xs">
                <span className="text-zinc-500">Confiança: </span>
                <strong>{(results.data.confidence * 100).toFixed(1)}%</strong>
                {results.data.has_significant_winner && (
                  <Badge tone="ok" className="ml-2">
                    Vencedor
                  </Badge>
                )}
              </div>
              <div className="text-xs">
                <span className="text-zinc-500">Total assignments: </span>
                <strong>{results.data.total_assignments.toLocaleString("pt-BR")}</strong>
              </div>
              <div className="border-t border-zinc-100 dark:border-zinc-800 pt-3 space-y-2">
                {results.data.variants.map((v) => (
                  <div key={v.variant_id} className="text-xs flex items-center justify-between">
                    <span className="font-medium flex items-center gap-1.5">
                      {v.is_winner && <TrendingUp size={11} className="text-emerald-600" />}
                      {v.name}
                    </span>
                    <span className="font-mono">{(v.ctr * 100).toFixed(2)}%</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </Card>
      </div>
    </PageContainer>
  );
}
