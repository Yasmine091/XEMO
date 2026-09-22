# Growbot ↔ local Qwen integration notes

Recorded 2026-09-11.

## Working architecture

```text
Growbot GUI (HTTPS)
  → https://llm.malaxit.eu/v1
  → Cloudflare Tunnel: xemo-brain
  → JSON compatibility shim: http://127.0.0.1:1235
  → http://127.0.0.1:1234
  → LM Studio OpenAI-compatible API
  → Qwen3-VL 8B
```

- Cloudflare public hostname: `llm.malaxit.eu`
- Tunnel ID: `399cd750-43c1-4b97-a7fd-a8945adfaa67`
- Tunnel service: `http://127.0.0.1:1235` (the shim)
- LM Studio server: running on port `1234`
- Growbot server URL must include `/v1`: `https://llm.malaxit.eu/v1`
- Exact working model ID: `qwen/qwen3-vl-8b`
- LM Studio CORS: enabled
- Growbot vision option: enabled when camera frames should be sent to Qwen3-VL
- Growbot strict JSON mode: enabled during connection testing

Do not add `/chat/completions` to the Growbot URL. Growbot appends that path itself.

## JSON compatibility shim

LM Studio rejects the legacy request `response_format.type=json_object` and
accepts `json_schema` or `text`. Start `XEMO/bot/llm_compat_proxy.py` on port
1235. It rewrites only `json_object` requests to a permissive JSON schema and
passes streaming responses through unchanged. Point the named Cloudflare
Tunnel service at `http://127.0.0.1:1235`, not directly at port 1234. The
Growbot URL remains `https://llm.malaxit.eu/v1`.

## Confirmed working checks

```bash
curl -4 https://llm.malaxit.eu/v1/models
```

Returns the LM Studio model list, including:

- `qwen/qwen3-vl-8b`
- `qwen/qwen3-vl-4b`
- `qwen/qwen3-4b-thinking-2507`
- `qwen/qwen3-4b-2507`
- `zai-org/glm-4.7-flash`
- `text-embedding-nomic-embed-text-v1.5`

LM Studio logs confirmed successful requests to:

```text
POST /v1/chat/completions
```

Both streaming and non-streaming completions work through the tunnel. The connection test reached Qwen3-VL 8B and returned successfully.

## Important failure diagnosis

Using this URL was wrong:

```text
https://llm.malaxit.eu
```

That caused Growbot to call:

```text
POST /chat/completions
```

LM Studio reported `Unexpected endpoint or method` because the OpenAI-compatible endpoint is under `/v1`.

The correct URL is:

```text
https://llm.malaxit.eu/v1
```

The earlier TLS/CORS symptoms were misleading during setup. Once the certificate/tunnel became available and the `/v1` path was supplied, the request reached LM Studio normally.

## Nginx Proxy Manager note

Nginx Proxy Manager hosts other `malaxit.eu` services, but it is not part of this working route. The exact `llm.malaxit.eu` record is a proxied Cloudflare Tunnel record, so no NPM proxy host or NPM certificate is required for this hostname.

Do not expose LM Studio's raw port through NPM unless intentionally switching away from the tunnel architecture.

## Security follow-up

LM Studio authentication was not enabled during initial testing. Before leaving this endpoint available publicly, enable LM Studio authentication, create an API key, and place that key in Growbot's optional server API key field. Keep the tunnel pointed at LM Studio's local HTTP service; HTTPS is terminated by Cloudflare.
