// BCN-230..248 — "Modo demo" banner shown when the BEACON control-plane
// is unreachable and the page falls back to mock content.
//
// Behavior intentionally inert: amber stripe, no CTA, no auto-dismiss.
// Operators sweep the cluster when they spot it.

import { AlertTriangle } from "lucide-react";

export interface DemoBannerProps {
  /**
   * Optional context fragment shown in italic after the canonical message.
   * Useful to differentiate pages that fail individually (e.g. "/v1/billing
   * indisponivel").
   */
  detail?: string;
  className?: string;
}

export function DemoBanner({ detail, className = "" }: DemoBannerProps) {
  return (
    <div
      className={
        "mb-4 flex items-center gap-2 rounded-md border border-amber-300 " +
        "bg-amber-50 dark:bg-amber-950/30 dark:border-amber-800 px-3 py-2 " +
        "text-xs text-amber-900 dark:text-amber-200 " +
        className
      }
      role="status"
      aria-live="polite"
    >
      <AlertTriangle size={14} className="flex-shrink-0" />
      <span>
        <strong>Modo demo.</strong> Backend BEACON indisponivel — exibindo
        dados de exemplo.
        {detail ? <em className="ml-1 opacity-80">{detail}</em> : null}
      </span>
    </div>
  );
}

export default DemoBanner;
