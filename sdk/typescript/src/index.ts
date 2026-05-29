// Rewire Messaging — TypeScript SDK (V0)
//
// Thin wrapper around the /v1 canonical surface. Generated against
// docs/products/messaging/API_CONTRACT.md v0.2.0.

export interface MessagingClientOptions {
  baseUrl: string;
  apiToken: string;
  tenantId: string;
  fetchImpl?: typeof fetch;
  timeoutMs?: number;
}

export interface EmailSendInput {
  sender: string;
  to: string[];
  subject: string;
  htmlBody?: string;
  plainBody?: string;
  replyTo?: string;
  templateId?: string;
  tag?: string;
  consentBasis?: string;
  metadata?: Record<string, string>;
}

export interface EmailResponse {
  message_id: string;
  status: string;
  provider: string;
}

export interface SmsSendInput {
  to: string;
  text: string;
  fromNumber?: string;
  templateId?: string;
  consentBasis?: string;
}

export interface SmsResponse {
  message_id: string;
  status: string;
  provider: string;
  cost_brl_cents: number;
}

export interface PushSendInput {
  deviceToken: string;
  platform: 'ios' | 'android' | 'web';
  title: string;
  body: string;
  data?: Record<string, string>;
  pushAppId?: string;
}

export interface PushResponse {
  message_id: string;
  status: string;
  provider: string;
  platform: string;
}

export class MessagingError extends Error {
  status: number;
  body: unknown;
  constructor(status: number, body: unknown, message?: string) {
    super(message ?? `messaging request failed: ${status}`);
    this.status = status;
    this.body = body;
  }
}

export class MessagingClient {
  private readonly opts: Required<MessagingClientOptions>;

  constructor(opts: MessagingClientOptions) {
    this.opts = {
      ...opts,
      fetchImpl: opts.fetchImpl ?? fetch.bind(globalThis),
      timeoutMs: opts.timeoutMs ?? 10000,
    };
  }

  private headers(): Record<string, string> {
    return {
      Authorization: `Bearer ${this.opts.apiToken}`,
      'X-Organization-Id': this.opts.tenantId,
      'Content-Type': 'application/json',
      'User-Agent': 'rewire-messaging-sdk-ts/0.2.0',
    };
  }

  private async post<T>(path: string, payload: unknown): Promise<T> {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), this.opts.timeoutMs);
    try {
      const resp = await this.opts.fetchImpl(`${this.opts.baseUrl}${path}`, {
        method: 'POST',
        headers: this.headers(),
        body: JSON.stringify(payload),
        signal: controller.signal,
      });
      const text = await resp.text();
      const body = text ? JSON.parse(text) : null;
      if (!resp.ok) {
        throw new MessagingError(resp.status, body);
      }
      return body as T;
    } finally {
      clearTimeout(timeout);
    }
  }

  async sendEmail(input: EmailSendInput): Promise<EmailResponse> {
    return this.post<EmailResponse>('/v1/emails', {
      sender: input.sender,
      to: input.to,
      subject: input.subject,
      html_body: input.htmlBody,
      plain_body: input.plainBody,
      reply_to: input.replyTo,
      template_id: input.templateId,
      tag: input.tag,
      consent_basis: input.consentBasis ?? 'contract',
      metadata: input.metadata ?? {},
    });
  }

  async sendSms(input: SmsSendInput): Promise<SmsResponse> {
    return this.post<SmsResponse>('/v1/sms', {
      to: input.to,
      text: input.text,
      from_number: input.fromNumber,
      template_id: input.templateId,
      consent_basis: input.consentBasis ?? 'contract',
    });
  }

  async sendPush(input: PushSendInput): Promise<PushResponse> {
    return this.post<PushResponse>('/v1/push', {
      device_token: input.deviceToken,
      platform: input.platform,
      title: input.title,
      body: input.body,
      data: input.data,
      push_app_id: input.pushAppId,
    });
  }
}

export default MessagingClient;
