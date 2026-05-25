import { type ReactElement } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';

import BeaconShell from '@/components/beacon/BeaconShell';
import BeaconOverview from '@/pages/beacon/BeaconOverview';
import BeaconMessages from '@/pages/beacon/BeaconMessages';
import BeaconTemplates from '@/pages/beacon/BeaconTemplates';
import BeaconJourneys from '@/pages/beacon/BeaconJourneys';
import BeaconSuppression from '@/pages/beacon/BeaconSuppression';
import BeaconDomains from '@/pages/beacon/BeaconDomains';
import BeaconSmsNumbers from '@/pages/beacon/BeaconSmsNumbers';
import BeaconWhatsapp from '@/pages/beacon/BeaconWhatsapp';
import BeaconPushApps from '@/pages/beacon/BeaconPushApps';
import BeaconAnalytics from '@/pages/beacon/BeaconAnalytics';
import BeaconWebhooks from '@/pages/beacon/BeaconWebhooks';
import BeaconDeliverability from '@/pages/beacon/BeaconDeliverability';
import BeaconAntispam from '@/pages/beacon/BeaconAntispam';
import BeaconApiKeys from '@/pages/beacon/BeaconApiKeys';
import BeaconLgpd from '@/pages/beacon/BeaconLgpd';
import BeaconChain from '@/pages/beacon/BeaconChain';
import BeaconBilling from '@/pages/beacon/BeaconBilling';
import BeaconTeam from '@/pages/beacon/BeaconTeam';
import BeaconSettings from '@/pages/beacon/BeaconSettings';
// MSG-IMPL-001 (Lote 8 umbrella): A/B tests + Segments (cross-canal).
import BeaconAbTests from '@/pages/beacon/BeaconAbTests';
import BeaconSegments from '@/pages/beacon/BeaconSegments';

// BEACON — Notification Platform multi-canal BR.
// Routes are mounted under /app/produtos/beacon/* so the Sidebar/Topbar
// NavLinks (which use that BASE) resolve correctly. Root path redirects
// to overview.
export default function App(): ReactElement {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/app/produtos/beacon" replace />} />
      <Route path="/app/produtos/beacon" element={<BeaconShell />}>
        <Route index element={<BeaconOverview />} />
        <Route path="messages" element={<BeaconMessages />} />
        <Route path="templates" element={<BeaconTemplates />} />
        <Route path="journeys" element={<BeaconJourneys />} />
        <Route path="suppression" element={<BeaconSuppression />} />
        <Route path="domains" element={<BeaconDomains />} />
        <Route path="sms-numbers" element={<BeaconSmsNumbers />} />
        <Route path="whatsapp" element={<BeaconWhatsapp />} />
        <Route path="push-apps" element={<BeaconPushApps />} />
        <Route path="analytics" element={<BeaconAnalytics />} />
        <Route path="webhooks" element={<BeaconWebhooks />} />
        <Route path="deliverability" element={<BeaconDeliverability />} />
        <Route path="antispam" element={<BeaconAntispam />} />
        <Route path="api-keys" element={<BeaconApiKeys />} />
        <Route path="lgpd" element={<BeaconLgpd />} />
        <Route path="chain" element={<BeaconChain />} />
        <Route path="billing" element={<BeaconBilling />} />
        <Route path="team" element={<BeaconTeam />} />
        <Route path="settings" element={<BeaconSettings />} />
        <Route path="ab-tests" element={<BeaconAbTests />} />
        <Route path="segments" element={<BeaconSegments />} />
      </Route>
      <Route path="*" element={<Navigate to="/app/produtos/beacon" replace />} />
    </Routes>
  );
}
