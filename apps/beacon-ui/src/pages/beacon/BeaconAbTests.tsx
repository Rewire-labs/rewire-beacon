// BeaconAbTests page
// FE-MESSAGING-09: authoring UI for A/B tests (was list-only).

import {
  EntityAuthoring,
  type FieldDef,
} from "../../components/beacon/EntityAuthoring";

const FIELDS: FieldDef[] = [
  { name: "name", label: "Nome do teste", required: true },
  { name: "variant_a", label: "Variante A (template)", required: true },
  { name: "variant_b", label: "Variante B (template)", required: true },
  {
    name: "split_pct",
    label: "Divisão A (%)",
    type: "number",
    required: true,
    placeholder: "50",
  },
  { name: "goal_metric", label: "Métrica de sucesso", placeholder: "open_rate" },
];

export default function BeaconAbTests() {
  return (
    <EntityAuthoring title="teste A/B" endpoint="/v1/ab-tests" fields={FIELDS} />
  );
}
