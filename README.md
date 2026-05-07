# ComfyUI Local Server

Production-grade FastAPI backend for orchestrating ComfyUI generation workflows.

The platform currently includes:

* FastAPI REST API
* SQLAlchemy metadata persistence
* Redis integration
* Celery GPU-safe queue execution
* ComfyUI REST and websocket integration
* Socket.IO realtime job events
* Upload and output storage
* JWT and API key authentication
* Redis-backed rate limiting
* Docker Compose services for backend, worker, Redis, ComfyUI, and nginx

## Architecture

```text
client
  |
  | REST / Socket.IO
  v
nginx
  |
  v
FastAPI backend
  |-- auth and API key validation
  |-- storage API
  |-- generation API
  |-- Socket.IO server
  |
  | Redis broker/state/events
  v
Celery worker
  |
  | ComfyUI HTTP + websocket APIs
  v
ComfyUI
```

Backend modules are separated by responsibility:

* `server/app/api` - versioned route handlers
* `server/app/auth` - JWT, API keys, password hashing
* `server/app/comfy` - ComfyUI REST, websocket, output parsing, job tracking
* `server/app/core` - settings, lifecycle, logging, Redis, rate limiting
* `server/app/database` - SQLAlchemy engine/session/base
* `server/app/models` - ORM models
* `server/app/queue` - Celery app, tasks, queue service
* `server/app/schemas` - Pydantic request/response models
* `server/app/services` - business services
* `server/app/socket` - Socket.IO realtime layer
* `server/app/storage` - upload/output storage
* `server/app/workflows` - workflow loading and runtime injection

## Implemented Phases

### Phase 1: Core Backend

Implemented FastAPI app structure, environment settings, async SQLAlchemy, Redis lifecycle, structured logging, health routes, dependency injection, Docker Compose, and requirements.

### Phase 2: ComfyUI Integration

Implemented ComfyUI REST client, websocket progress listener, reusable workflow template loading, runtime parameter injection, execution service, job tracking, and output parsing.

Supported modes:

* Text-to-Image: `t2i`
* Image-to-Image: `i2i`
* Text-to-Video: `t2v`
* Image-to-Video: `i2v`

### Phase 3: Queue System

Implemented Redis + Celery queue processing with FIFO behavior, GPU-safe single-worker concurrency, retries, cancellation, timeout handling, persisted job state, and queue monitoring.

### Realtime Layer

Implemented Socket.IO job rooms and events:

* `job_queued`
* `job_started`
* `progress_update`
* `preview_image`
* `preview_video`
* `job_completed`
* `job_failed`

Clients subscribe with:

```json
{
  "job_id": "job-id"
}
```

on the `subscribe_job` event.

### Phase 4: Storage And Uploads

Implemented upload validation, async chunked writes, asset metadata persistence, output registration, download/delete/list APIs, static upload/output serving, and cleanup.

### Phase 5: Authentication And Security

Implemented user registration, JWT login, API key auth, admin-only API key creation, protected generation/storage routes, Redis-backed rate limiting, upload validation, and workflow template path whitelisting.

## Setup

Use Python 3.12.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

On Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Create a local environment file:

```bash
cp .env.example .env
```

Set at minimum:

```env
JWT_SECRET_KEY=replace-with-a-long-random-secret
ALLOW_USER_REGISTRATION=true
```

For production, set:

```env
ALLOW_USER_REGISTRATION=false
DATABASE_AUTO_CREATE_TABLES=false
```

and use migrations instead of automatic table creation.

## Run Locally

Start Redis first (required by app startup), for example:

```bash
docker run --name comfy-redis -p 6379:6379 -d redis:7.4-alpine
```

From `server`:

```bash
uvicorn app.main:socket_app --host 0.0.0.0 --port 8000
```

From repository root (Windows), you can also use:

```bat
start-server.bat
```

Run a worker:

```bash
celery -A app.queue.celery_app:celery_app worker --loglevel=INFO --concurrency=1 --queues=gpu_render_queue --prefetch-multiplier=1
```

## Docker Compose

```bash
docker compose up --build
```

Services:

* `backend` - FastAPI and Socket.IO
* `worker` - Celery GPU-safe workflow executor
* `redis` - broker, cache, job state, realtime pub/sub
* `comfyui` - independent ComfyUI service
* `nginx` - API, Socket.IO, uploads, and outputs proxy

The backend never exposes raw ComfyUI APIs publicly. It communicates with ComfyUI through internal HTTP and websocket APIs.

## API Overview

Health:

* `GET /api/v1/health`
* `GET /api/v1/health/live`

Auth:

* `POST /api/v1/auth/register`
* `POST /api/v1/auth/token`
* `GET /api/v1/auth/me`
* `POST /api/v1/auth/api-keys`

Generation:

* `POST /api/v1/generation/execute`
* `POST /api/v1/generation/queue`
* `GET /api/v1/generation/jobs/{job_id}`
* `POST /api/v1/generation/jobs/{job_id}/cancel`
* `GET /api/v1/generation/queue`

Storage:

* `POST /api/v1/storage/assets`
* `GET /api/v1/storage/assets`
* `GET /api/v1/storage/assets/{asset_id}`
* `GET /api/v1/storage/assets/{asset_id}/download`
* `DELETE /api/v1/storage/assets/{asset_id}`
* `POST /api/v1/storage/outputs/register`
* `POST /api/v1/storage/cleanup`

Protected routes accept either:

```http
Authorization: Bearer <jwt>
```

or:

```http
X-API-Key: <api-key>
```

## Workflow Templates

Workflow templates live in `server/workflows`.

Default filenames:

* `t2i.json`
* `i2i.json`
* `t2v.json`
* `i2v.json`

Templates may be plain ComfyUI API JSON exports or wrapped with explicit injection metadata:

```json
{
  "workflow": {
    "1": {
      "class_type": "CLIPTextEncode",
      "inputs": {
        "text": ""
      }
    }
  },
  "parameter_map": {
    "prompt": {
      "node_id": "1",
      "input": "text"
    }
  }
}
```

When no `parameter_map` is present, common ComfyUI node conventions are used for prompts, negative prompts, seeds, samplers, dimensions, LoRA nodes, image inputs, and video inputs.

## Configuration

Important environment variables:

* `DATABASE_URL`
* `REDIS_URL`
* `COMFYUI_BASE_URL`
* `COMFYUI_WS_URL`
* `JWT_SECRET_KEY`
* `ALLOW_USER_REGISTRATION`
* `CELERY_QUEUE_NAME`
* `CELERY_WORKER_CONCURRENCY`
* `RATE_LIMIT_REQUESTS_PER_MINUTE`
* `MAX_UPLOAD_SIZE_BYTES`
* `ALLOWED_UPLOAD_EXTENSIONS`

See `.env.example` for the full list.

## Testing

```bash
cd server
python -m pytest tests
```

Current verification coverage includes app import, auth security, health service, ComfyUI output parsing, queue configuration, Socket.IO configuration, storage validation, and workflow injection.

## Deployment Notes

* Use Python 3.12.
* Set `JWT_SECRET_KEY` before enabling login.
* Keep `CELERY_WORKER_CONCURRENCY=1` for single-GPU safety.
* Do not expose ComfyUI directly to public clients.
* Use PostgreSQL and Alembic migrations for production database management.
* Put nginx or another trusted proxy in front of the backend.
* Store uploads and outputs on persistent local SSD or an S3-compatible backend in future iterations.
* Alembic migrations are located in `server/migrations` and are intended to be the schema source of truth.
* For production-like deployments, set `DATABASE_AUTO_CREATE_TABLES=false` and run migrations before starting `backend`/`worker` (the provided `docker-compose.yml` includes a one-shot `migrations` service).
* Kubernetes scaling:
  * Run `backend` as a Deployment (horizontal scaling is safe because job state lives in Redis and Socket.IO uses a Redis-backed manager).
  * Keep `worker` replicas at `1` (or enforce strict single concurrency) to avoid overloading ComfyUI (`CELERY_WORKER_CONCURRENCY=1`).
  * Run migrations as an initContainer or pre-deploy Job before rolling out backend/worker.

## Remaining Phases

* Phase 6: Dashboard and monitoring
* Phase 7: Deployment hardening, migrations, production infrastructure, Kubernetes-ready scaling
