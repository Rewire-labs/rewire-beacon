// BeaconJourneys page
// FE-MESSAGING-09: authoring UI for multi-step journeys (was list-only).

import {
  EntityAuthoring,
  type FieldDef,
} from "../../components/beacon/EntityAuthoring";

const FIELDS: FieldDef[] = [
  { name: "name", label: "Nome da jornada", required: true },
  {
    name: "trigger_event",
    label: "Evento de gatilho",
    required: true,
    placeholder: "user.signed_up",
  },
  {
    name: "steps",
    label: "Passos (JSON)",
    type: "textarea",
    required: true,
    placeholder: '[{"channel":"email","delay_hours":0}]',
  },
];

export default function BeaconJourneys() {
  return (
    <EntityAuthoring title="jornada" endpoint="/v1/journeys" fields={FIELDS} />
  );
}
