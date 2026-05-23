"""Template rendering: MJML compile + Handlebars-like variable interpolation.

MJML compile is delegated to a sidecar HTTP service (mjml-renderer) when
available. In dev, a minimal MJML-to-HTML stub wraps content in a basic
table layout so the rest of the pipeline can be tested.

Variable syntax:
- `{{name}}`               — simple substitution (HTML-escaped)
- `{{{name}}}`             — raw substitution (no escape)
- `{{#if cond}}...{{/if}}` — conditional block
- `{{#each items}}{{this}}{{/each}}` — loop
"""
from __future__ import annotations

import html
import logging
import re
from typing import Any

import httpx

from beacon.settings import get_settings

logger = logging.getLogger(__name__)


_VAR_RE = re.compile(r"\{\{\{?\s*([a-zA-Z_][a-zA-Z0-9_.]*)\s*\}?\}\}")
_IF_RE = re.compile(r"\{\{#if\s+([a-zA-Z_][a-zA-Z0-9_.]*)\s*\}\}(.*?)\{\{/if\}\}", re.DOTALL)
_EACH_RE = re.compile(r"\{\{#each\s+([a-zA-Z_][a-zA-Z0-9_.]*)\s*\}\}(.*?)\{\{/each\}\}", re.DOTALL)


def _resolve_dotted(data: dict[str, Any], path: str) -> Any:
    cur: Any = data
    for part in path.split("."):
        if isinstance(cur, dict):
            cur = cur.get(part)
        else:
            return None
    return cur


def render_handlebars(template: str, vars: dict[str, Any]) -> str:
    out = template

    # Loops first (so each-body can contain ifs).
    def _each_sub(m: re.Match[str]) -> str:
        key, body = m.group(1), m.group(2)
        items = _resolve_dotted(vars, key) or []
        rendered = []
        for item in items:
            ctx = {**vars, "this": item}
            if isinstance(item, dict):
                ctx.update(item)
            rendered.append(render_handlebars(body, ctx))
        return "".join(rendered)

    out = _EACH_RE.sub(_each_sub, out)

    # Conditionals.
    def _if_sub(m: re.Match[str]) -> str:
        key, body = m.group(1), m.group(2)
        return body if _resolve_dotted(vars, key) else ""

    out = _IF_RE.sub(_if_sub, out)

    # Simple substitution.
    def _var_sub(m: re.Match[str]) -> str:
        raw = m.group(0).startswith("{{{")
        value = _resolve_dotted(vars, m.group(1))
        if value is None:
            return ""
        s = str(value)
        return s if raw else html.escape(s)

    out = _VAR_RE.sub(_var_sub, out)
    return out


async def compile_mjml(mjml_source: str) -> str:
    """Compile MJML -> HTML. Uses sidecar if reachable, else dev stub."""
    s = get_settings()
    sidecar_url = f"{s.postal_api_url.rstrip('/').replace('postal', 'mjml-renderer')}/v1/render"
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.post(sidecar_url, json={"mjml": mjml_source})
            if resp.status_code == 200:
                return resp.json()["html"]
    except Exception as exc:  # noqa: BLE001
        logger.debug("mjml-renderer unavailable: %s", exc)
    # Dev stub — strip mjml tags, wrap in basic HTML so testing remains valid.
    stripped = re.sub(r"<mj-[^>]+/?>", "", mjml_source)
    stripped = re.sub(r"</?mj-[^>]+>", "", stripped)
    return f"<!doctype html><html><body>{stripped}</body></html>"


async def render_email_template(
    *,
    mjml_source: str,
    text_source: str | None,
    subject_template: str,
    vars: dict[str, Any],
) -> tuple[str, str, str | None]:
    """Returns (subject, html_body, text_body)."""
    subject = render_handlebars(subject_template, vars)
    rendered_mjml = render_handlebars(mjml_source, vars)
    html_body = await compile_mjml(rendered_mjml)
    text_body = render_handlebars(text_source, vars) if text_source else None
    return subject, html_body, text_body
