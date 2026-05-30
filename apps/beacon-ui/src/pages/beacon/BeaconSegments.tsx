// BeaconSegments page
// FE-MESSAGING-09: authoring UI for audience segments (was list-only).

import {
  EntityAuthoring,
  type FieldDef,
} from "../../components/beacon/EntityAuthoring";

const FIELDS: FieldDef[] = [
  { name: "name", label: "Nome do segmento", required: true },
  {
    name: "filter_expr",
    label: "Filtro (expressão)",
    type: "textarea",
    required: true,
    placeholder: 'country == "BR" && plan == "pro"',
  },
  { name: "description", label: "Descrição", type: "textarea" },
];

export default function BeaconSegments() {
  return (
    <EntityAuthoring title="segmento" endpoint="/v1/segments" fields={FIELDS} />
  );
}
