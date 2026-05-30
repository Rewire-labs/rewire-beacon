// Beacon UI primitives
//
// FE-MESSAGING-01 / FE-MESSAGING-10: full token-driven primitive set.
// Badge gains a `tone` prop (ok/warn/bad/accent). Added: PageHeader,
// PageContainer, Table, Th, Td, Kpi, StatusDot, ScoreBar, timeAgo, fmtDate.
// Colors come from CSS custom properties (--background, --foreground,
// --primary, --border, --muted, --destructive, --accent) so the palette
// is theme-driven, not bespoke.

import * as React from "react";

export function cn(...classes: Array<string | false | null | undefined>): string {
  return classes.filter(Boolean).join(" ");
}

type DivProps = React.HTMLAttributes<HTMLDivElement>;

export function Card({ className, ...props }: DivProps) {
  return (
    <div
      className={cn(
        "rounded-lg border border-border bg-card text-card-foreground shadow-sm",
        className,
      )}
      {...props}
    />
  );
}

export function CardHeader({ className, ...props }: DivProps) {
  return <div className={cn("flex flex-col gap-1.5 p-6", className)} {...props} />;
}

export function CardTitle({ className, ...props }: DivProps) {
  return (
    <div className={cn("text-lg font-semibold leading-none", className)} {...props} />
  );
}

export function CardContent({ className, ...props }: DivProps) {
  return <div className={cn("p-6 pt-0", className)} {...props} />;
}

type ButtonProps = React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "default" | "outline" | "ghost" | "destructive";
};

export function Button({
  className,
  variant = "default",
  ...props
}: ButtonProps) {
  const variants: Record<NonNullable<ButtonProps["variant"]>, string> = {
    default: "bg-primary text-primary-foreground hover:bg-primary/90",
    outline: "border border-border bg-background hover:bg-muted",
    ghost: "hover:bg-muted",
    destructive: "bg-destructive text-destructive-foreground hover:bg-destructive/90",
  };
  return (
    <button
      className={cn(
        "inline-flex items-center justify-center rounded-md px-4 py-2 text-sm font-medium transition-colors disabled:pointer-events-none disabled:opacity-50",
        variants[variant],
        className,
      )}
      {...props}
    />
  );
}

type InputProps = React.InputHTMLAttributes<HTMLInputElement>;
export function Input({ className, ...props }: InputProps) {
  return (
    <input
      className={cn(
        "flex h-10 w-full rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring",
        className,
      )}
      {...props}
    />
  );
}

type TextareaProps = React.TextareaHTMLAttributes<HTMLTextAreaElement>;
export function Textarea({ className, ...props }: TextareaProps) {
  return (
    <textarea
      className={cn(
        "flex min-h-[120px] w-full rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring",
        className,
      )}
      {...props}
    />
  );
}

type SelectProps = React.SelectHTMLAttributes<HTMLSelectElement>;
export function Select({ className, ...props }: SelectProps) {
  return (
    <select
      className={cn(
        "flex h-10 w-full rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring",
        className,
      )}
      {...props}
    />
  );
}

export function Label({
  className,
  ...props
}: React.LabelHTMLAttributes<HTMLLabelElement>) {
  return (
    <label
      className={cn("text-sm font-medium text-foreground", className)}
      {...props}
    />
  );
}

type BadgeTone = "ok" | "warn" | "bad" | "accent";
type BadgeProps = React.HTMLAttributes<HTMLSpanElement> & { tone?: BadgeTone };

const BADGE_TONE: Record<BadgeTone, string> = {
  ok: "border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-400",
  warn: "border-amber-200 bg-amber-50 text-amber-700 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-400",
  bad: "border-red-200 bg-red-50 text-red-700 dark:border-red-800 dark:bg-red-950/40 dark:text-red-400",
  accent: "border-violet-200 bg-violet-50 text-violet-700 dark:border-violet-800 dark:bg-violet-950/40 dark:text-violet-400",
};

export function Badge({ className, tone, ...props }: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium",
        tone ? BADGE_TONE[tone] : "border-border bg-muted text-muted-foreground",
        className,
      )}
      {...props}
    />
  );
}

// ---------------------------------------------------------------------------
// Layout primitives
// ---------------------------------------------------------------------------

type PageHeaderProps = {
  title: string;
  subtitle?: string;
  actions?: React.ReactNode;
};
export function PageHeader({ title, subtitle, actions }: PageHeaderProps) {
  return (
    <div className="flex items-start justify-between gap-4 mb-6">
      <div>
        <h1 className="text-xl font-bold text-foreground">{title}</h1>
        {subtitle && (
          <p className="mt-1 text-sm text-muted-foreground max-w-prose">{subtitle}</p>
        )}
      </div>
      {actions && <div className="flex-shrink-0">{actions}</div>}
    </div>
  );
}

export function PageContainer({ className, ...props }: DivProps) {
  return <div className={cn("p-6 space-y-4", className)} {...props} />;
}

// ---------------------------------------------------------------------------
// Table primitives
// ---------------------------------------------------------------------------

export function Table({ className, ...props }: React.HTMLAttributes<HTMLTableElement>) {
  return (
    <div className="w-full overflow-x-auto rounded-lg border border-border">
      <table
        className={cn("w-full caption-bottom text-sm", className)}
        {...props}
      />
    </div>
  );
}

export function Th({ className, ...props }: React.ThHTMLAttributes<HTMLTableCellElement>) {
  return (
    <th
      className={cn(
        "h-10 px-4 text-left align-middle text-xs font-semibold uppercase tracking-wider text-muted-foreground bg-muted/50 border-b border-border",
        className,
      )}
      {...props}
    />
  );
}

export function Td({ className, ...props }: React.TdHTMLAttributes<HTMLTableCellElement>) {
  return (
    <td
      className={cn("px-4 py-3 align-middle text-sm text-foreground border-b border-border last-of-type:border-0", className)}
      {...props}
    />
  );
}

// ---------------------------------------------------------------------------
// KPI card
// ---------------------------------------------------------------------------

type KpiProps = { label: string; value: string; hint?: string; accent?: BadgeTone };
export function Kpi({ label, value, hint, accent }: KpiProps) {
  return (
    <div className="rounded-lg border border-border bg-card p-5 shadow-sm">
      <p className="text-xs uppercase tracking-wider font-semibold text-muted-foreground">{label}</p>
      <p
        className={cn(
          "text-2xl font-bold mt-1",
          accent === "ok" && "text-emerald-600 dark:text-emerald-400",
          accent === "warn" && "text-amber-600 dark:text-amber-400",
          accent === "bad" && "text-red-600 dark:text-red-400",
          accent === "accent" && "text-violet-600 dark:text-violet-400",
          !accent && "text-foreground",
        )}
      >
        {value}
      </p>
      {hint && <p className="text-xs text-muted-foreground mt-0.5">{hint}</p>}
    </div>
  );
}

// ---------------------------------------------------------------------------
// StatusDot
// ---------------------------------------------------------------------------

type DotStatus = "delivered" | "queued" | "failed" | "pending" | string;
export function StatusDot({ status }: { status: DotStatus }) {
  const color =
    status === "delivered" ? "bg-emerald-500"
    : status === "failed" ? "bg-red-500"
    : status === "queued" || status === "pending" ? "bg-amber-400"
    : "bg-muted-foreground";
  return <span className={cn("inline-block h-2 w-2 rounded-full flex-shrink-0", color)} />;
}

// ---------------------------------------------------------------------------
// ScoreBar (0–1 or 0–100)
// ---------------------------------------------------------------------------

type ScoreBarProps = { value?: number; score?: number; max?: number; className?: string };
export function ScoreBar({ value, score, max = 1, className }: ScoreBarProps) {
  const pct = Math.min(100, Math.round(((value ?? score ?? 0) / max) * 100));
  const color =
    pct >= 80 ? "bg-emerald-500"
    : pct >= 50 ? "bg-amber-400"
    : "bg-red-500";
  return (
    <div className={cn("flex items-center gap-2", className)}>
      <div className="flex-1 h-1.5 rounded bg-muted overflow-hidden">
        <div className={cn("h-full rounded transition-all", color)} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs tabular-nums text-muted-foreground w-8 text-right">{pct}%</span>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Time helpers
// ---------------------------------------------------------------------------

export function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const s = Math.floor(diff / 1000);
  if (s < 60) return `${s}s atrás`;
  const m = Math.floor(s / 60);
  if (m < 60) return `${m}min atrás`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h atrás`;
  return `${Math.floor(h / 24)}d atrás`;
}

export function fmtDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("pt-BR");
}
