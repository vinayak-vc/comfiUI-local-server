# API Documentation (Client Integration)

This folder contains client-facing API documentation and importable artifacts.

## Quick start

- **Swagger UI**: `GET /docs`
- **OpenAPI JSON**: `GET /openapi.json`

Default dev URLs from this repo’s settings:

- **App**: `http://localhost:8000`
- **API base**: `http://localhost:8000/api`
- **Versioned API base**: `http://localhost:8000/api/v1`

## Authentication

Most endpoints accept **either**:

- **JWT bearer**: `Authorization: Bearer <access_token>`
- **API key**: `X-API-Key: <api_key>`

Admin-only endpoints require `is_admin=true`.

## Included files

- `openapi.yaml`: OpenAPI 3.1 spec for the HTTP API (import into Swagger/Postman).
- `postman_collection.json`: Postman collection with examples and auth variables.
- `postman_environment.json`: Postman environment variables (`BASE_URL`, `JWT`, `API_KEY`).

## Import into Postman

1. Import `api_docs/openapi.yaml` (or `postman_collection.json`).
2. Import `postman_environment.json` and select it.
3. Set:
   - `BASE_URL` to `http://localhost:8000`
   - `JWT` to the access token from `POST /api/v1/auth/token` (without `Bearer ` prefix)
   - `API_KEY` to an admin-created key from `POST /api/v1/auth/api-keys`

## Notes for client dev

- `POST /api/v1/generation/execute` and `POST /api/v1/generation/queue` default to the Flux Schnell workflow (`workflow/flux_schnell.json`). Send `{}` or omit individual fields to use defaults; provide only the parameters you want to override.
- Flux Schnell defaults are `workflow_name=flux_schnell`, `mode=t2i`, `model=flux1-schnell-fp8.safetensors`, `sampler=euler`, `scheduler=simple`, `steps=4`, `cfg=1`, `denoise=1`, `width=1024`, `height=1024`, and `batch_size=1`.
- Leave `loras` empty for `flux_schnell`; that workflow does not contain `LoraLoader` nodes.
- Generation output `url` fields are returned as absolute downloadable URLs based on the API request host, for example `http://192.168.1.28:8000/outputs/ComfyUI_00007_.png`.
- Uploads and outputs are also served as static files:
  - `GET /uploads/...`
  - `GET /outputs/...`
- Socket.IO mounts at path `/socket.io` on the same origin as the API server.

