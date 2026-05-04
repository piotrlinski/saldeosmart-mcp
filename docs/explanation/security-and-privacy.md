# Security & privacy

This page describes the project's security posture: what we protect, how
we protect it, what's explicitly out of scope, and the assumptions an
operator or auditor needs to know.

For the disclosure path and supported versions, see the [security
policy](../security.md).

## Threat model in one paragraph

The server is a credentialed bridge between an MCP client (typically
running on an end-user's desktop) and SaldeoSMART. The high-value asset is
the API token, which can read and modify accounting data for an entire
client portfolio. The realistic adversary is **a malicious or compromised
LLM client process** that can read the server's logs, environment, or
filesystem; **a network observer** between the server and Saldeo; and
**a careless user** who pastes credentials into the wrong place.

## Hardening measures

### Token handling

- `SaldeoConfig.api_token` is a `pydantic.SecretStr` — `repr()` of the
  config redacts it (`SecretStr('**********')`). Logging the config
  object will not leak the token.
- The token is read **once**, in `RequestSigner`, to compute the per-
  request signature. It is never serialized to disk and never sent to
  Saldeo as a plaintext field — only as the input to an MD5 hash.
- The token is not echoed in error messages even when authentication
  fails — `SaldeoError` carries the Saldeo error code and the request's
  `req_id`, never the signing material.

### URL redaction in logs

Every log line that contains a URL is filtered through
`http/xml.py:redact_url`, which strips the `req_sig` and `api_token`
query params:

```text
[2026-05-04 09:12:33] INFO  GET https://saldeo.brainshare.pl/api/xml/2.12/company/list?username=…&req_id=…&req_sig=… HTTP/1.1 200
```

If you ever see a non-redacted token in a log line, it's a bug — please
file it via [SECURITY.md](../security.md).

### Request lock

The `threading.Lock` in `SaldeoClient` ([Concurrency](concurrency.md))
also serves a security purpose: it ensures that no in-flight request can
be observed mid-flight by a parallel thread inside the same process,
which simplifies reasoning about sensitive material in memory.

### Container isolation

The Docker image (`docker/Dockerfile`) runs as an unprivileged user
`mcp:mcp` inside `python:3.12-slim-bookworm`. The image has no shell
utilities beyond what the runtime needs and no network listener — MCP is
spoken over stdio.

### Smoke-test policy

`scripts/smoke_test.py` invokes **only** read endpoints against the live
account. Write tools (`merge_*`, `update_*`, `delete_*`, `recognize_*`,
`sync_*`) are covered exclusively by unit tests against fixture XML.
Credentials in `.env` cannot accidentally mutate the production account
from this script. This is a hard policy and any extension to the smoke
test must preserve it.

## Known limitations

??? warning "MD5 in the signature"
    Saldeo's spec mandates MD5 for `req_sig`. We implement what the spec
    requires. The token itself is high-entropy and the signature is
    over per-request material, so the realistic attack is replay — not
    collision — and Saldeo's `req_id` (timestamp + UUID) defends against
    that. Out of our control.

??? warning "Token in the MCP client config"
    Most MCP clients expect the token in `claude_desktop_config.json`
    or equivalent, in plaintext. The `--env-file` pattern documented in
    [Configure Claude Desktop](../how-to/configure-claude-desktop.md)
    moves it to a `chmod 600` file outside the client config. Beyond
    that, OS keychain integration would require client-side support
    that doesn't yet exist in the MCP ecosystem.

??? warning "No mTLS to Saldeo"
    Saldeo doesn't offer client-cert auth — the API authenticates with
    the username/token signature only. We rely on standard TLS
    certificate verification (httpx default).

## Out of scope

- **DoS resistance.** The server is a single-process subprocess of an MCP
  client. It is not a service. If a malicious tool input causes
  infinite work, the client process crashes — which is a recovery path,
  not a vulnerability.
- **Multi-tenancy.** One server process serves one set of credentials.
  Running multiple clients with different tokens means running multiple
  server processes.
- **Audit logging.** The server logs every request to a local file. It
  does not ship logs anywhere or correlate them with end-user actions.
  That's the MCP client's job.

## Reporting

See [SECURITY.md](../security.md) for the private disclosure path.
