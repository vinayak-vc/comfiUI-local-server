# API Documentation (Client Integration)

This folder contains client-facing API documentation and importable artifacts.

## Quick Start

- Swagger UI: `GET /docs`
- OpenAPI JSON: `GET /openapi.json`
- API base: `http://localhost:8000/api/v1`

Default dev URLs from this repo's settings:

- App: `http://localhost:8000`
- API base: `http://localhost:8000/api`
- Versioned API base: `http://localhost:8000/api/v1`

## Included Files

- `openapi.yaml`: OpenAPI 3.1 spec for Swagger/Postman import.
- `postman_collection.json`: Postman collection with ready-to-run examples.
- `postman_environment.json`: Postman environment variables: `BASE_URL`, `JWT`, `API_KEY`.

## Application Flow

The normal client flow is:

1. Register a user with `POST /api/v1/auth/register`.
2. Login with `POST /api/v1/auth/token`.
3. Send the returned JWT as `Authorization: Bearer <token>`.
4. Run generation with either immediate execution or queued execution.
5. Read the generated output URL from the response.
6. Download the image/video from the returned `url`.

For production clients, prefer queued generation because it returns quickly and lets the Celery worker process GPU jobs safely.

## Authentication

Most protected endpoints accept either:

```http
Authorization: Bearer <access_token>
```

or:

```http
X-API-Key: <api_key>
```

Admin-only endpoints require an admin user. The first registered user becomes admin.

## Step 1: Register User

Endpoint:

```http
POST /api/v1/auth/register
Content-Type: application/json
```

Request:

```json
{
  "email": "user@example.com",
  "password": "a-very-strong-password"
}
```

Response:

```json
{
  "id": "user-id",
  "email": "user@example.com",
  "is_active": true,
  "is_admin": true,
  "created_at": "2026-05-07T12:00:00Z"
}
```

## Step 2: Login

Endpoint:

```http
POST /api/v1/auth/token
Content-Type: application/x-www-form-urlencoded
```

Form fields:

```text
username=user@example.com
password=a-very-strong-password
```

Response:

```json
{
  "access_token": "jwt-token",
  "token_type": "bearer",
  "expires_in": 3600
}
```

Use the token in later requests:

```http
Authorization: Bearer jwt-token
```

## Step 3: Check Current User

Endpoint:

```http
GET /api/v1/auth/me
Authorization: Bearer <jwt-token>
```

Use this to verify the token and current user privileges.

## Step 4A: Immediate Generation

Endpoint:

```http
POST /api/v1/generation/execute
Authorization: Bearer <jwt-token>
Content-Type: application/json
```

This executes the workflow immediately and keeps the HTTP request open until ComfyUI finishes.

Minimal request using Flux Schnell defaults:

```json
{}
```

Override only selected parameters:

```json
{
  "parameters": {
    "prompt": "a cinematic robot chef in a neon kitchen, high detail, soft studio lighting",
    "seed": 12345
  }
}
```

Full default request:

```json
{
  "mode": "t2i",
  "workflow_name": "flux_schnell",
  "parameters": {
    "prompt": "a cinematic robot chef in a neon kitchen, high detail, soft studio lighting",
    "negative_prompt": "",
    "seed": 173805153958730,
    "model": "flux1-schnell-fp8.safetensors",
    "sampler": "euler",
    "scheduler": "simple",
    "steps": 4,
    "cfg": 1,
    "denoise": 1,
    "width": 1024,
    "height": 1024,
    "batch_size": 1,
    "loras": [],
    "extra_parameters": {}
  }
}
```

Response:

```json
{
  "job_id": "job-id",
  "prompt_id": "comfyui-prompt-id",
  "status": "completed",
  "outputs": [
    {
      "filename": "ComfyUI_00007_.png",
      "subfolder": "",
      "type": "output",
      "url": "http://192.168.1.28:8000/outputs/ComfyUI_00007_.png",
      "media_type": "image"
    }
  ],
  "events": [],
  "started_at": "2026-05-07T12:00:00Z",
  "completed_at": "2026-05-07T12:00:30Z",
  "error": null
}
```

## Step 4B: Queued Generation

Endpoint:

```http
POST /api/v1/generation/queue
Authorization: Bearer <jwt-token>
Content-Type: application/json
```

This submits a job to Redis/Celery and returns immediately. The Celery worker must be running.

Request:

```json
{
  "parameters": {
    "prompt": "a cinematic robot chef in a neon kitchen, high detail, soft studio lighting",
    "seed": 12345
  }
}
```

Response:

```json
{
  "job": {
    "job_id": "job-id",
    "task_id": "celery-task-id",
    "prompt_id": null,
    "mode": "t2i",
    "status": "queued",
    "retry_count": 0,
    "outputs": [],
    "error": null
  }
}
```

## Step 5: Poll Job Status

Endpoint:

```http
GET /api/v1/generation/jobs/{job_id}
Authorization: Bearer <jwt-token>
```

When the job finishes, `status` becomes `completed` and `outputs` contains downloadable URLs.

Example completed output:

```json
{
  "job_id": "job-id",
  "prompt_id": "comfyui-prompt-id",
  "mode": "t2i",
  "status": "completed",
  "outputs": [
    {
      "filename": "ComfyUI_00007_.png",
      "subfolder": "",
      "type": "output",
      "url": "http://192.168.1.28:8000/outputs/ComfyUI_00007_.png",
      "media_type": "image"
    }
  ],
  "error": null
}
```

## Step 6: Download Output

Use the `outputs[].url` value directly:

```http
GET http://192.168.1.28:8000/outputs/ComfyUI_00007_.png
```

The backend serves local output files first. If the file is not in `server/outputs`, it proxies the file from ComfyUI's `/view` endpoint.

## Queue And Monitoring APIs

Queue snapshot:

```http
GET /api/v1/generation/queue
Authorization: Bearer <jwt-token>
```

Dashboard job list:

```http
GET /api/v1/monitoring/jobs?limit=20&offset=0
Authorization: Bearer <jwt-token>
```

Job counts by status:

```http
GET /api/v1/monitoring/jobs/counts
Authorization: Bearer <jwt-token>
```

Admin log tail:

```http
GET /api/v1/monitoring/logs/tail?lines=200
Authorization: Bearer <admin-jwt-token>
```

## API Key Flow

Admin users can create API keys:

```http
POST /api/v1/auth/api-keys
Authorization: Bearer <admin-jwt-token>
Content-Type: application/json
```

Request:

```json
{
  "name": "client-dev"
}
```

Use the returned key on later requests:

```http
X-API-Key: cui_example_key
```

Do not place API keys in browser frontend code. Treat them like passwords.

## Storage APIs

Upload asset:

```http
POST /api/v1/storage/assets
Authorization: Bearer <jwt-token>
Content-Type: multipart/form-data
```

List assets:

```http
GET /api/v1/storage/assets?limit=50&offset=0
Authorization: Bearer <jwt-token>
```

Get asset metadata:

```http
GET /api/v1/storage/assets/{asset_id}
Authorization: Bearer <jwt-token>
```

Download uploaded asset:

```http
GET /api/v1/storage/assets/{asset_id}/download
Authorization: Bearer <jwt-token>
```

## Flux Schnell Defaults

`POST /api/v1/generation/execute` and `POST /api/v1/generation/queue` default to the Flux Schnell workflow at `workflow/flux_schnell.json`.

Defaults:

```json
{
  "workflow_name": "flux_schnell",
  "mode": "t2i",
  "model": "flux1-schnell-fp8.safetensors",
  "sampler": "euler",
  "scheduler": "simple",
  "steps": 4,
  "cfg": 1,
  "denoise": 1,
  "width": 1024,
  "height": 1024,
  "batch_size": 1
}
```

Leave `loras` empty for `flux_schnell`; that workflow does not contain `LoraLoader` nodes.

Use `extra_parameters` only for advanced node-level overrides:

```json
{
  "parameters": {
    "extra_parameters": {
      "31.steps": 6,
      "27.width": 768,
      "27.height": 1344
    }
  }
}
```

## Postman Import

1. Import `api_docs/openapi.yaml` or `api_docs/postman_collection.json`.
2. Import `api_docs/postman_environment.json` and select it.
3. Set `BASE_URL` to your server, for example `http://192.168.1.28:8000`.
4. Register/login and let the token request save `JWT`, or paste the token manually.
5. Run generation requests from the `Generation` folder.

## Notes

- Socket.IO mounts at `/socket.io` on the same origin as the API server.
- Static uploads are available under `/uploads/...`.
- Generated outputs are available under `/outputs/...`.
- Queued generation requires Redis and the Celery worker from `start-worker.bat`.
