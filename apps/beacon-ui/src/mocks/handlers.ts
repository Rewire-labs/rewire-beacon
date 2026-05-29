// MSW handlers for rewire-messaging frontend mocks (MSG-V0 DoD #20)
// Used by beacon-ui templates editor + Storybook + Lovable integration tests.
//
// Setup: import { handlers } from './mocks/handlers';
//        import { setupWorker } from 'msw/browser';
//        const worker = setupWorker(...handlers);
//        worker.start();

import { http, HttpResponse } from 'msw';

const BASE = import.meta.env.VITE_MESSAGING_BASE_URL || 'https://messaging.rewirelabs.dev';

interface EmailSendBody {
  sender: string;
  to: string[];
  subject: string;
  html_body?: string;
  plain_body?: string;
}

interface SmsSendBody {
  to: string;
  text: string;
}

interface PushSendBody {
  device_token: string;
  platform: 'ios' | 'android' | 'web';
  title: string;
  body: string;
}

interface TemplateCreateBody {
  slug: string;
  channel: 'email' | 'sms' | 'push';
  locale?: string;
  subject?: string | null;
  body: string;
  description?: string | null;
}

export const handlers = [
  // ---- Health -----------------------------------------------------------
  http.get(`${BASE}/healthz`, () => HttpResponse.json({ status: 'ok', service: 'rewire-messaging' })),
  http.get(`${BASE}/ready`, () => HttpResponse.json({ status: 'ready', service: 'rewire-messaging' })),

  // ---- Email ------------------------------------------------------------
  http.post(`${BASE}/v1/emails`, async ({ request }) => {
    const body = (await request.json()) as EmailSendBody;
    if (!body.html_body && !body.plain_body) {
      return HttpResponse.json(
        { error: 'email_requires_html_or_plain_body' },
        { status: 422 },
      );
    }
    return HttpResponse.json(
      {
        message_id: `01HXYZ-MOCK-${Date.now()}`,
        status: 'queued',
        provider: 'postal',
      },
      { status: 202 },
    );
  }),

  http.get(`${BASE}/v1/emails/:messageId`, ({ params }) =>
    HttpResponse.json({
      message_id: params.messageId,
      status: 'delivered',
      lookup: 'mock',
    }),
  ),

  // ---- SMS --------------------------------------------------------------
  http.post(`${BASE}/v1/sms`, async ({ request }) => {
    const body = (await request.json()) as SmsSendBody;
    if (!/^\+55\d{10,11}$/.test(body.to)) {
      return HttpResponse.json(
        { error: 'invalid_recipient', message: 'phone must be E.164 BR (+55...)' },
        { status: 422 },
      );
    }
    return HttpResponse.json(
      {
        message_id: `sms_mock_${Date.now()}`,
        status: 'queued',
        provider: 'zenvia',
        cost_brl_cents: 7,
      },
      { status: 202 },
    );
  }),

  // ---- Push -------------------------------------------------------------
  http.post(`${BASE}/v1/push`, async ({ request }) => {
    const body = (await request.json()) as PushSendBody;
    if (body.platform === 'web') {
      return HttpResponse.json(
        { error: 'push_web_pending_v03', message: 'web push (VAPID) ships V0.3' },
        { status: 501 },
      );
    }
    return HttpResponse.json(
      {
        message_id: `${body.platform === 'ios' ? 'apns' : 'fcm'}-mock-${Date.now()}`,
        status: 'sent',
        provider: body.platform === 'ios' ? 'apns' : 'fcm',
        platform: body.platform,
      },
      { status: 202 },
    );
  }),

  http.post(`${BASE}/v1/push/devices`, async ({ request }) => {
    const body = (await request.json()) as { device_token: string; platform: string };
    return HttpResponse.json(
      {
        registered: true,
        tenant_id: 'mock-tenant',
        platform: body.platform,
        device_token_hint: body.device_token.slice(0, 6) + '...',
      },
      { status: 201 },
    );
  }),

  // ---- Templates --------------------------------------------------------
  http.post(`${BASE}/v1/templates`, async ({ request }) => {
    const body = (await request.json()) as TemplateCreateBody;
    return HttpResponse.json(
      {
        id: `tpl_${body.slug}`,
        slug: body.slug,
        channel: body.channel,
        locale: body.locale || 'pt-BR',
        subject: body.subject ?? null,
        body: body.body,
        version: 1,
      },
      { status: 201 },
    );
  }),

  http.get(`${BASE}/v1/templates/:id`, ({ params }) =>
    HttpResponse.json({
      id: params.id,
      slug: String(params.id).replace(/^tpl_/, ''),
      channel: 'email',
      locale: 'pt-BR',
      subject: 'Bem-vindo {{ name }}',
      body: '<p>Ola {{ name }}</p>',
      version: 1,
    }),
  ),

  http.get(`${BASE}/v1/templates`, () => HttpResponse.json([])),

  http.delete(`${BASE}/v1/templates/:id`, () => new HttpResponse(null, { status: 204 })),

  // ---- Webhooks ---------------------------------------------------------
  http.post(`${BASE}/v1/webhooks/:provider`, ({ params }) => {
    const known = new Set(['postal', 'resend', 'zenvia', 'apns', 'fcm']);
    if (!known.has(String(params.provider))) {
      return HttpResponse.json({ error: 'unknown_provider' }, { status: 404 });
    }
    return new HttpResponse(null, { status: 204 });
  }),
];

export default handlers;
