// BeaconWebhooks page
// FE-MESSAGING-09: authoring UI for outbound webhooks (was list-only).

import {
  EntityAuthoring,
  type FieldDef,
} from "../../components/beacon/EntityAuthoring";

const FIELDS: FieldDef[] = [
  { name: "name", label: "Nome", required: true },
  {
    name: "url",
    label: "URL de destino",
    type: "url",
    required: true,
    placeholder: "https://example.com/webhooks/beacon",
  },
  {
    name: "events",
    label: "Eventos (separados por vírgula)",
    placeholder: "delivered,bounced,complained",
  },
  { name: "secret", label: "Secret de assinatura (HMAC)" },
];

export default function BeaconWebhooks() {
  return (
    <EntityAuthoring title="webhook" endpoint="/v1/webhooks" fields={FIELDS} />
  );
}
