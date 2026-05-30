// BeaconPushApps page
// FE-MESSAGING-09: authoring UI for push apps / credentials (was list-only).

import {
  EntityAuthoring,
  type FieldDef,
} from "../../components/beacon/EntityAuthoring";

const FIELDS: FieldDef[] = [
  { name: "name", label: "Nome do app", required: true },
  {
    name: "platform",
    label: "Plataforma",
    required: true,
    placeholder: "fcm | apns | webpush",
  },
  { name: "bundle_id", label: "Bundle / Package ID", required: true },
  {
    name: "credentials",
    label: "Credenciais (JSON)",
    type: "textarea",
    placeholder: '{"server_key":"..."}',
  },
];

export default function BeaconPushApps() {
  return (
    <EntityAuthoring title="push app" endpoint="/v1/push-apps" fields={FIELDS} />
  );
}
