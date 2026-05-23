"""External provider HTTP clients (Postal, AWS SES, Zenvia, etc).

Each module exposes a thin async client + result dataclasses. No business
logic — services orchestrate which client to use.
"""
