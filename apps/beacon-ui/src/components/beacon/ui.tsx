// BEACON UI primitives — inlined from the canonical design system (audit/ui).
// V0 standalone; avoids cross-product imports so the app builds isolated.
import { ReactNode } from "react";

export function PageHeader({
  title, subtitle, actions,
}: { title: string; subtitle?: string; actions?: ReactNode }) {
  return (
    <div className="flex items-end justify-between flex-wrap gap-4 mb-8">
      <div>
        <h1 className="text-2xl md:text-3xl font-extrabold tracking-tight">{title}</h1>
        {subtitle && <p className="text-sm text-zinc-500 mt-1.5 max-w-2xl">{subtitle}</p>}
      </div>
      {actions && <div className="flex gap-2">{actions}</div>}
    </div>
  );
}

export function Card({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <div className={`bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl ${className}`}>
      {children}
    </div>
  );
}

export function Kpi({ label, value, hint, accent }: { label: string; value: string; hint?: string; accent?: "ok" | "warn" | "bad" }) {
  const color =
    accent === "ok" ? "text-emerald-600 dark:text-emerald-400"
      : accent === "warn" ? "text-amber-600 dark:text-amber-400"
      : accent === "bad" ? "text-red-600 dark:text-red-400"
      : "text-zinc-900 dark:text-zinc-100";
  return (
    <Card className="p-5">
      <p className="text-[11px] uppercase tracking-wider font-semibold text-zinc-500">{label}</p>
      <p className={`text-2xl font-bold mt-1.5 ${color}`}>{value}</p>
      {hint && <p className="text-[11px] text-zinc-500 mt-1">{hint}</p>}
    </Card>
  );
}

export function StatusDot({ status }: { status: string }) {
  const ok = ["active", "passing", "ready", "delivered", "paid", "connected", "resolved", "confirmed"];
  const warn = ["pending", "in_progress", "investigating", "intake", "generating", "open", "warning", "not_collected"];
  const bad = ["failing", "expired", "revoked", "failed", "rejected", "error", "critical"];
  const c = ok.includes(status) ? "bg-emerald-500" : bad.includes(status) ? "bg-red-500" : warn.includes(status) ? "bg-amber-500" : "bg-zinc-400";
  return <span className={`inline-block w-1.5 h-1.5 rounded-full ${c}`} />;
}

export function Badge({ children, tone = "default" }: { children: ReactNode; tone?: "default" | "ok" | "warn" | "bad" | "accent" }) {
  const map = {
    default: "bg-zinc-100 text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300",
    ok: "bg-emerald-50 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-400",
    warn: "bg-amber-50 text-amber-700 dark:bg-amber-950/40 dark:text-amber-400",
    bad: "bg-red-50 text-red-700 dark:bg-red-950/40 dark:text-red-400",
    accent: "bg-accent/10 text-accent",
  };
  return <span className={`text-[10px] font-semibold uppercase tracking-wider px-1.5 py-0.5 rounded ${map[tone]}`}>{children}</span>;
}

export function Table({ children }: { children: ReactNode }) {
  return (
    <Card className="overflow-x-auto">
      <table className="w-full text-sm">{children}</table>
    </Card>
  );
}

export function Th({ children, className = "" }: { children?: ReactNode; className?: string }) {
  return <th className={`text-left text-[11px] uppercase tracking-wider font-semibold text-zinc-500 px-4 py-3 border-b border-zinc-200 dark:border-zinc-800 ${className}`}>{children}</th>;
}

export function Td({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <td className={`px-4 py-3 border-b border-zinc-100 dark:border-zinc-900 ${className}`}>{children}</td>;
}

export function timeAgo(iso?: string) {
  if (!iso || iso === "—") return "—";
  const diff = (Date.now() - new Date(iso).getTime()) / 60000;
  if (diff < 0) return "agora";
  if (diff < 60) return `há ${Math.round(diff)}min`;
  if (diff < 60 * 24) return `há ${Math.round(diff / 60)}h`;
  return `há ${Math.round(diff / (60 * 24))}d`;
}

export function fmtDate(iso?: string) {
  if (!iso || iso === "—") return "—";
  return new Date(iso).toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" });
}

export function PageContainer({ children }: { children: ReactNode }) {
  return <div className="max-w-7xl mx-auto px-6 py-8">{children}</div>;
}

export function ScoreBar({ score }: { score: number }) {
  const color = score >= 95 ? "bg-emerald-500" : score >= 85 ? "bg-accent" : score >= 70 ? "bg-amber-500" : "bg-red-500";
  return (
    <div className="w-full h-1.5 bg-zinc-200 dark:bg-zinc-800 rounded">
      <div className={`h-1.5 rounded ${color}`} style={{ width: `${score}%` }} />
    </div>
  );
}
