// Beacon UI primitives
//
// FE-MESSAGING-10: token-driven primitives (shadcn-style API) replacing
// hardcoded zinc colors. Colors come from CSS custom properties on
// :root / .dark (e.g. --background, --foreground, --primary, --border,
// --muted, --destructive) so the palette is theme-driven, not bespoke.

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

export function Badge({
  className,
  ...props
}: React.HTMLAttributes<HTMLSpanElement>) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border border-border bg-muted px-2.5 py-0.5 text-xs font-medium text-muted-foreground",
        className,
      )}
      {...props}
    />
  );
}
