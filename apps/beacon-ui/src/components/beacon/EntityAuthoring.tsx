// EntityAuthoring — shared create/edit form scaffold (FE-MESSAGING-09).
//
// Authoring UIs for AbTests / Segments / Journeys / PushApps / Webhooks were
// list-only. This component provides a reusable, validated create/edit form
// wired to the API client, so each entity page just declares its fields.

import * as React from "react";
import { api, ApiError } from "../../lib/api";
import {
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Input,
  Label,
  Textarea,
} from "./ui";

export interface FieldDef {
  name: string;
  label: string;
  type?: "text" | "textarea" | "number" | "url";
  required?: boolean;
  placeholder?: string;
}

export type EntityValues = Record<string, string | number>;

export interface EntityAuthoringProps {
  title: string;
  endpoint: string; // e.g. "/v1/ab-tests"
  fields: FieldDef[];
  initial?: EntityValues;
  entityId?: string; // present => edit (PUT), absent => create (POST)
  onSaved?: (saved: unknown) => void;
}

function validate(fields: FieldDef[], values: EntityValues): string | null {
  for (const f of fields) {
    const v = values[f.name];
    if (f.required && (v === undefined || String(v).trim() === "")) {
      return `${f.label} é obrigatório.`;
    }
    if (f.type === "url" && v && !/^https?:\/\/.+/.test(String(v))) {
      return `${f.label} deve ser uma URL http(s) válida.`;
    }
    if (f.type === "number" && v !== undefined && v !== "" && isNaN(Number(v))) {
      return `${f.label} deve ser numérico.`;
    }
  }
  return null;
}

export function EntityAuthoring({
  title,
  endpoint,
  fields,
  initial,
  entityId,
  onSaved,
}: EntityAuthoringProps) {
  const [values, setValues] = React.useState<EntityValues>(initial ?? {});
  const [saving, setSaving] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [saved, setSaved] = React.useState(false);

  const update = (name: string, value: string) => {
    setValues((v) => ({ ...v, [name]: value }));
    setError(null);
    setSaved(false);
  };

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const validationError = validate(fields, values);
    if (validationError) {
      setError(validationError);
      return;
    }
    setSaving(true);
    setError(null);
    try {
      const body: EntityValues = {};
      for (const f of fields) {
        const raw = values[f.name];
        body[f.name] = f.type === "number" ? Number(raw) : (raw ?? "");
      }
      const result = entityId
        ? await api.put(`${endpoint}/${entityId}`, body)
        : await api.post(endpoint, body);
      setSaved(true);
      onSaved?.(result);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Falha ao salvar.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>
          {entityId ? `Editar ${title}` : `Novo ${title}`}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <form className="flex flex-col gap-4" onSubmit={onSubmit}>
          {fields.map((f) => (
            <div className="flex flex-col gap-1.5" key={f.name}>
              <Label htmlFor={f.name}>
                {f.label}
                {f.required ? " *" : ""}
              </Label>
              {f.type === "textarea" ? (
                <Textarea
                  id={f.name}
                  value={String(values[f.name] ?? "")}
                  placeholder={f.placeholder}
                  onChange={(e) => update(f.name, e.target.value)}
                />
              ) : (
                <Input
                  id={f.name}
                  type={f.type === "number" ? "number" : "text"}
                  value={String(values[f.name] ?? "")}
                  placeholder={f.placeholder}
                  onChange={(e) => update(f.name, e.target.value)}
                />
              )}
            </div>
          ))}

          {error && (
            <p className="text-sm text-destructive" role="alert">
              {error}
            </p>
          )}
          {saved && (
            <p className="text-sm text-primary" role="status">
              Salvo com sucesso.
            </p>
          )}

          <Button type="submit" disabled={saving}>
            {saving ? "Salvando…" : "Salvar"}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
