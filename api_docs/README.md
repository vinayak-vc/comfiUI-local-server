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

- Uploads and outputs are also served as static files:
  - `GET /uploads/...`
  - `GET /outputs/...`
- Socket.IO mounts at path `/socket.io` on the same origin as the API server.

