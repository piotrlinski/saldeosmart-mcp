# Debug authentication failures

Authentication errors fall into a few well-known buckets, each with a
specific recovery path. The server logs every failure to
`SALDEO_LOG_DIR/saldeosmart.log` (default `/var/log/saldeosmart/` in
Docker, `~/.saldeosmart/logs/` for `uvx`/`pip` installs unless overridden).

## Symptom: every tool returns `HTTP_401`

The server reached Saldeo but the MD5 signature was rejected.

**Most likely causes**

1. Wrong username — Saldeo's API uses your **firm-portal login**, not the
   client-portal login. They're different on `biuro-rachunkowe` accounts.
2. Wrong token — tokens are 64-char hex; check for whitespace or
   newline characters that snuck in via copy-paste.
3. Wrong `base_url` — `saldeo.brainshare.pl` (production) vs
   `saldeo-test.brainshare.pl` (test). The token from one will not work
   against the other.

**Recovery**

1. Regenerate the token at **Konfiguracja → Konto → API → Generuj token**
   (only available to *biuro-rachunkowe* users, not their clients).
2. Test against the right environment with the smoke test:

   ```bash
   SALDEO_BASE_URL=https://saldeo-test.brainshare.pl \
   uv run python scripts/smoke_test.py
   ```

## Symptom: tools return `HTTP_403`

You authenticated, but your account doesn't have API access enabled. On
some plans this is gated behind a manual flag.

**Recovery**

Email `api@saldeosmart.pl` and ask them to enable API for your account.
Include your login. Wait ~24h for them to flip the flag.

## Symptom: `PARSE_ERROR` with HTML in the body

The 2xx body wasn't valid XML — usually an HTML error page from a proxy or
load balancer. The first 500 chars of the body land in `message`.

**Most likely causes**

- A captive-portal interstitial on a corporate network.
- Saldeo's Cloudflare WAF challenged the request (rare; happens on
  freshly-IP'd CI runners).

**Recovery**

- From a corporate network: switch to a clean network or use a forward
  proxy that doesn't rewrite responses.
- From CI: add a small backoff and retry once. The lock in `SaldeoClient`
  already serializes calls; retry isn't a thundering-herd risk.

## Symptom: server starts but Claude Desktop shows no tools

The MCP handshake failed, usually before any tool was ever called. Check
the client-side log:

| Client | Log path |
|---|---|
| Claude Desktop (macOS) | `~/Library/Logs/Claude/mcp-server-saldeosmart.log` |
| Claude Desktop (Windows) | `%LOCALAPPDATA%\Claude\Logs\mcp-server-saldeosmart.log` |
| Claude Code | `~/.claude/logs/mcp-server-saldeosmart.log` (or `claude mcp logs saldeosmart`) |
| Cursor | **Settings → MCP → View logs** |

The most common cause is a missing env var (`SALDEO_USERNAME` /
`SALDEO_API_TOKEN`) — the server fails fast in `server.main()` with a
clear error before `mcp.run()` is called.

## Read the redacted URL

Every API call is logged with the URL **redacted** to remove `req_sig` and
`api_token`:

```
[2026-05-04 09:12:33] INFO  GET https://saldeo.brainshare.pl/api/xml/2.12/company/list?username=… (req_id=…)
```

If you don't see your login in the URL, the request never went out — most
likely a config error caught before the network call.

## Last resort: enable verbose logging

```bash
SALDEO_LOG_LEVEL=DEBUG saldeosmart-mcp --username … --api-token …
```

DEBUG includes the full XML envelope (still with token redaction). Useful
for diffing against the example XML in `.temp/api-html-mirror/` when an
endpoint started returning unexpected shapes.
