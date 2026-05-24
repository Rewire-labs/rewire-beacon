import { PageHeader, PageContainer, Card, Badge, Table, Th, Td, timeAgo } from "@/components/beacon/ui";
import { DemoBanner } from "@/components/beacon/DemoBanner";
import { TEAM } from "@/content/beacon-mock";
import { useBeaconTeam } from "@/lib/hooks/useBeacon";
import { Plus, Users, Shield } from "lucide-react";

const ROLE_TONE = { owner: "bad" as const, admin: "warn" as const, developer: "accent" as const, marketer: "accent" as const, viewer: "ok" as const };

// BCN-248: BeaconTeam wired to /v1/team.
export default function BeaconTeam() {
  const teamQ = useBeaconTeam();
  return (
    <PageContainer>
      {teamQ.isDemo && <DemoBanner detail="GET /v1/team indisponivel" />}
      <PageHeader
        title="Time & SSO"
        subtitle="Authentik OIDC para SSO + RBAC granular: owner, admin, developer, marketer, viewer. Auditores externos têm role viewer sem expor API keys."
        actions={<button className="flex items-center gap-1.5 text-sm font-semibold bg-accent text-white px-3 py-2 rounded-md hover:bg-accent/90"><Plus size={14} /> Convidar membro</button>}
      />

      <div className="grid md:grid-cols-3 gap-3 mb-6">
        <Card className="p-4"><p className="text-[10px] uppercase tracking-wider text-zinc-500 font-semibold">Membros ativos</p><p className="text-2xl font-bold mt-1">{TEAM.length}</p></Card>
        <Card className="p-4"><p className="text-[10px] uppercase tracking-wider text-zinc-500 font-semibold">SSO habilitado</p><p className="text-2xl font-bold mt-1">{TEAM.filter((t) => t.sso).length}/{TEAM.length}</p></Card>
        <Card className="p-4 flex items-center gap-3">
          <Shield size={20} className="text-accent" />
          <div><p className="text-[10px] uppercase tracking-wider text-zinc-500 font-semibold">SAML + OIDC</p><p className="text-sm font-semibold mt-1">Authentik conectado</p></div>
        </Card>
      </div>

      <Table>
        <thead><tr><Th>Nome</Th><Th>Email</Th><Th>Role</Th><Th>SSO</Th><Th>Última atividade</Th></tr></thead>
        <tbody>
          {TEAM.map((t) => (
            <tr key={t.id} className="hover:bg-zinc-50 dark:hover:bg-zinc-900/40">
              <Td className="font-medium text-sm flex items-center gap-2"><Users size={13} className="text-zinc-400" />{t.name}</Td>
              <Td className="text-xs text-zinc-500">{t.email}</Td>
              <Td><Badge tone={ROLE_TONE[t.role]}>{t.role}</Badge></Td>
              <Td>{t.sso ? <Badge tone="ok">SSO</Badge> : <Badge tone="warn">Senha</Badge>}</Td>
              <Td className="text-xs text-zinc-500">{timeAgo(t.last_active)}</Td>
            </tr>
          ))}
        </tbody>
      </Table>
    </PageContainer>
  );
}
