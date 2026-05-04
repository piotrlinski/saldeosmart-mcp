# Explanation

Background reading for the project. These pages explain *why* the code is
shaped the way it is — useful when you're maintaining the project, doing a
security review, or onboarding a new contributor.

For task-oriented recipes, see the [how-to guides](../how-to/index.md). For
the auto-generated API surface, see the [reference](../reference/index.md).

## What's here

- [**Architecture**](architecture.md) — the layer stack, the import-direction
  rule, and how a tool call flows from the LLM to Saldeo and back.
- [**Request signing**](request-signing.md) — the MD5 algorithm Saldeo
  requires, with a sequence diagram.
- [**Concurrency**](concurrency.md) — why every request goes through a single
  `threading.Lock` (Saldeo forbids concurrent requests per user).
- [**Security & privacy**](security-and-privacy.md) — `SecretStr` tokens,
  URL redaction in logs, the read-only smoke-test policy, and the
  attack-surface assumptions.
- [**Design decisions**](design-decisions.md) — a running log of the
  non-obvious choices: why FastMCP, why MD5 (Saldeo's spec, not our pick),
  why one Pydantic model per direction, why the `_runtime`/`_builders`
  helper split, and what we explicitly chose *not* to do.
