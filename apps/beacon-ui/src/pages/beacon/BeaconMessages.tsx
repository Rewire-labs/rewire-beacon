// BeaconMessages page
//
// FE-MESSAGING-04: compose-and-send UI for the core notification action.
// Lets an operator pick channel + recipient + category + content (or template),
// preview it, validate, and send via the canonical API (beaconApi.send).
// FE-MESSAGING-10: built on token-driven ui/ primitives (no hardcoded zinc).

import * as React from "react";
import { beaconApi, ApiError, type SendResult } from "../../lib/api";
import {
  Badge,
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Input,
  Label,
  Select,
  Textarea,
} from "../../components/beacon/ui";

const CHANNELS = ["email", "sms", "push", "whatsapp"] as const;
const CATEGORIES = ["transactional", "marketing", "digest"] as const;

type Channel = (typeof CHANNELS)[number];

interface FormState {
  channel: Channel;
  recipient: string;
  category: string;
  subject: string;
  body: string;
}

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const E164_RE = /^\+[1-9]\d{6,14}$/;

function validate(form: FormState): string | null {
  if (!form.recipient.trim()) return "Informe o destinatário.";
  if (form.channel === "email" && !EMAIL_RE.test(form.recipient)) {
    return "E-mail do destinatário inválido.";
  }
  if (
    (form.channel === "sms" || form.channel === "whatsapp") &&
    !E164_RE.test(form.recipient)
  ) {
    return "Telefone deve estar em formato E.164 (ex: +5511999998888).";
  }
  if (!form.body.trim()) return "O conteúdo da mensagem é obrigatório.";
  if (form.channel === "email" && !form.subject.trim()) {
    return "Assunto é obrigatório para e-mail.";
  }
  return null;
}

export default function BeaconMessages() {
  const [form, setForm] = React.useState<FormState>({
    channel: "email",
    recipient: "",
    category: "transactional",
    subject: "",
    body: "",
  });
  const [sending, setSending] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [result, setResult] = React.useState<SendResult | null>(null);

  const update = <K extends keyof FormState>(key: K, value: FormState[K]) => {
    setForm((f) => ({ ...f, [key]: value }));
    setError(null);
    setResult(null);
  };

  const onSend = async () => {
    const validationError = validate(form);
    if (validationError) {
      setError(validationError);
      return;
    }
    setSending(true);
    setError(null);
    setResult(null);
    try {
      const res = await beaconApi.send({
        channel: form.channel,
        recipient: form.recipient.trim(),
        category: form.category,
        subject: form.subject,
        body: form.body,
      });
      setResult(res);
      if (!res.accepted) {
        setError(`Não enviado (${res.decision}): ${res.reason}`);
      }
    } catch (e) {
      const msg = e instanceof ApiError ? e.message : "Falha ao enviar.";
      setError(msg);
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="grid gap-6 md:grid-cols-2">
      <Card>
        <CardHeader>
          <CardTitle>Compor mensagem</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="channel">Canal</Label>
            <Select
              id="channel"
              value={form.channel}
              onChange={(e) => update("channel", e.target.value as Channel)}
            >
              {CHANNELS.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </Select>
          </div>

          <div className="flex flex-col gap-1.5">
            <Label htmlFor="recipient">Destinatário</Label>
            <Input
              id="recipient"
              value={form.recipient}
              placeholder={
                form.channel === "email" ? "nome@dominio.com" : "+5511999998888"
              }
              onChange={(e) => update("recipient", e.target.value)}
            />
          </div>

          <div className="flex flex-col gap-1.5">
            <Label htmlFor="category">Categoria</Label>
            <Select
              id="category"
              value={form.category}
              onChange={(e) => update("category", e.target.value)}
            >
              {CATEGORIES.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </Select>
          </div>

          {form.channel === "email" && (
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="subject">Assunto</Label>
              <Input
                id="subject"
                value={form.subject}
                onChange={(e) => update("subject", e.target.value)}
              />
            </div>
          )}

          <div className="flex flex-col gap-1.5">
            <Label htmlFor="body">Conteúdo</Label>
            <Textarea
              id="body"
              value={form.body}
              onChange={(e) => update("body", e.target.value)}
            />
          </div>

          {error && (
            <p className="text-sm text-destructive" role="alert">
              {error}
            </p>
          )}
          {result?.accepted && (
            <p className="text-sm text-primary" role="status">
              Mensagem aceita para envio.
            </p>
          )}

          <Button onClick={onSend} disabled={sending}>
            {sending ? "Enviando…" : "Enviar"}
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Preview</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
          <div className="flex items-center gap-2">
            <Badge>{form.channel}</Badge>
            <Badge>{form.category}</Badge>
          </div>
          <p className="text-sm text-muted-foreground">
            Para: {form.recipient || "—"}
          </p>
          {form.channel === "email" && (
            <p className="text-sm font-medium">{form.subject || "(sem assunto)"}</p>
          )}
          <div className="rounded-md border border-border bg-muted p-3 text-sm whitespace-pre-wrap">
            {form.body || "(mensagem vazia)"}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
