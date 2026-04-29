# Security Policy

## Supported versions

This project is in active early development. Only the latest commit on the
`master` branch (currently version `0.1.0`) receives fixes. Older commits
or tags are not patched.

| Version | Supported          |
| ------- | ------------------ |
| `master` (latest) | ✅ |
| any older commit  | ❌ |

## Reporting a vulnerability

**Please do not open a public GitHub issue for security problems.** Public
issues make the vulnerability available to attackers before a fix exists.

Instead, use one of:

1. **GitHub private vulnerability reporting** —
   https://github.com/piotrlinski/saldeosmart-mcp/security/advisories/new
   (preferred — keeps the report attached to the repo and lets us
   coordinate a fix and disclosure in private).
2. **Email** — `piotrklinski@gmail.com` with the subject line
   `[security] saldeosmart-mcp: <short description>`.

Please include:

- A description of the issue and the impact you believe it has.
- Steps to reproduce, ideally with a minimal proof of concept.
- The commit SHA / version you tested against.
- Whether the issue has been disclosed elsewhere.

You should expect an acknowledgement within **7 days**. After triage, we
will coordinate a fix and a disclosure timeline with you.

## Scope

In scope:

- The MCP server code in this repository (`src/saldeosmart_mcp/**`).
- The Docker image built from `docker/Dockerfile`.
- The request-signing, secret-handling, and URL-redaction logic
  (`http/signing.py`, `http/client.py`, `http/xml.py`).
- The published documentation at
  `https://piotrlinski.github.io/saldeosmart-mcp/`.

Out of scope:

- The upstream **SaldeoSMART REST API** itself — please report those issues
  directly to BrainShare / SaldeoSMART (`api@saldeosmart.pl`).
- Vulnerabilities in third-party dependencies that already have a public
  CVE; instead, please open a regular issue or PR bumping the dependency.
- Findings that require a malicious actor to already have your
  `SALDEO_API_TOKEN` (an attacker with the token can already act as the
  user — that is by design of the upstream API).

## Hardening notes

The project takes the following measures, which you may want to verify or
critique in a report:

- API tokens are typed as `pydantic.SecretStr` and never logged.
- Logged URLs are redacted (`req_sig`, `api_token` are scrubbed) — see
  `src/saldeosmart_mcp/http/xml.py`.
- Requests are serialized behind a `threading.Lock` to honor the
  upstream "no concurrent requests per user" rule.
- The Docker image runs as an unprivileged user (`USER mcp`) and does
  **not** bake credentials into the image — they are passed at runtime
  via `-e` / `--env-file`.
- The smoke test in `scripts/smoke_test.py` is read-only by policy;
  write tools are exercised exclusively by unit tests against fixture
  XML.

Thank you for helping keep `saldeosmart-mcp` and its users safe.
