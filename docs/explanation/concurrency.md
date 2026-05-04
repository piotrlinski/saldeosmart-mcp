# Concurrency

Saldeo's spec forbids concurrent requests per user — a second request
that arrives before the first has fully responded is rejected. FastMCP's
thread executor would otherwise issue tool calls in parallel as soon as
the LLM batched them, so the `SaldeoClient` enforces single-flight
behavior with a `threading.Lock`.

## The contract

From the SaldeoSMART spec:

> Klient nie może wysyłać kolejnych zapytań przed otrzymaniem odpowiedzi
> na poprzednie. Limit: 20 zapytań na minutę na użytkownika.
>
> *(The client must not send subsequent requests before receiving the
> response to the previous one. Limit: 20 requests per minute per user.)*

## How we enforce it

`SaldeoClient.__init__` allocates a `threading.Lock` and every request
method (`get`, `post_command`) wraps the network call in
`with self._lock:`. The lock is per-`SaldeoClient` instance, but the
server holds a single shared client (initialized in `tools/_runtime.py`
via `init_client(config)` and torn down in `close_client()`), so all
tool calls go through the same lock.

```python
def get(self, endpoint: str, query: dict[str, str] | None = None) -> Element:
    with self._lock:                       # serialize per-user
        params = self._signer.sign({...})
        response = self._http.get(endpoint, params=params)
        return self._parse_response(response)
```

## What this means in practice

- **The server is throughput-bound by Saldeo, not by Python.** With a
  20-req/min ceiling, three sequential calls per minute is plenty for
  interactive LLM use; bulk operations (think: importing 1000
  documents) need server-side batching, which is why `merge_*` tools
  accept lists with `max_length` caps.
- **Tool calls from a single LLM session block each other.** If an
  agent fires `list_documents` and `list_invoices` in parallel,
  FastMCP dispatches both to the executor but only one runs at a time
  inside the client. The other waits.
- **Two MCP clients with the same credentials would step on each
  other.** Each spawns its own `SaldeoClient` instance with its own
  lock — they don't share state. If you need to run two clients (say,
  Claude Desktop + Claude Code) against the same SaldeoSMART account,
  expect occasional `HTTP_429`s.

## Why not async?

`httpx.AsyncClient` would let us avoid the GIL contention, but FastMCP's
default tool dispatcher is sync (each `@mcp.tool` is a `def`, not
`async def`) and the lock would still be required. Switching to async
would only matter if a single request had multiple network hops, which
none currently do.

## Rate-limit visibility

`SaldeoClient` doesn't track 20-req/min itself — Saldeo enforces the
ceiling server-side and returns `HTTP_429` if exceeded. Treat it as a
cooperative limit: stay well under by serializing calls (which we do)
and adding a small delay if you're batching from a script.
