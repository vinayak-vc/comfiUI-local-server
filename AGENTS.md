# AGENTS.md

## Project Overview

This repository contains a production-grade AI generation orchestration platform built around ComfyUI.

The platform supports:

* Text-to-Image (T2I)
* Image-to-Image (I2I)
* Text-to-Video (T2V)
* Image-to-Video (I2V)

The backend acts as a centralized AI render farm with:

* REST APIs
* Socket.IO realtime updates
* workflow orchestration
* distributed queue processing
* asset storage
* authentication
* scalable infrastructure

Primary technologies:

* Python 3.12
* FastAPI
* Redis
* Celery
* Socket.IO
* SQLAlchemy
* Docker
* ComfyUI

---

# Engineering Principles

Agents must follow these rules strictly.

## Architecture Rules

* Use clean architecture principles.
* Follow SOLID principles.
* Keep modules loosely coupled.
* Use dependency injection when appropriate.
* Separate:

  * API layer
  * business logic
  * infrastructure
  * storage
  * workflow execution
  * websocket communication
* Never place business logic inside route handlers.
* Avoid circular dependencies.
* Avoid giant utility files.

---

# Coding Standards

## Python Standards

* Python version: 3.12
* Use type hints everywhere.
* Use async/await correctly.
* Use Pydantic models for request/response validation.
* Use SQLAlchemy ORM.
* Use dataclasses only where appropriate.
* Use pathlib instead of raw string paths.
* Use enums for status constants.

## Forbidden

Do NOT:

* generate placeholder code
* generate TODO comments
* create mock implementations
* use hardcoded secrets
* duplicate logic
* create monolithic files
* silently swallow exceptions
* use global mutable state

---

# Repository Structure

Expected structure:

server/
│
├── app/
│   ├── api/
│   ├── auth/
│   ├── comfy/
│   ├── core/
│   ├── database/
│   ├── models/
│   ├── queue/
│   ├── schemas/
│   ├── services/
│   ├── socket/
│   ├── storage/
│   ├── utils/
│   ├── workflows/
│   └── main.py
│
├── workflows/
├── uploads/
├── outputs/
├── logs/
├── tests/
├── docker/
├── nginx/
└── scripts/

Agents should preserve modularity.

---

# Workflow System Rules

ComfyUI workflows are JSON templates.

Rules:

* Never hardcode prompts into workflows.
* Runtime values must be injected dynamically.
* Workflow templates must remain reusable.
* Workflows must support:

  * prompt injection
  * negative prompt injection
  * seed injection
  * LoRA injection
  * model switching
  * sampler switching
  * image/video input injection

Workflow logic belongs inside:

* WorkflowLoader
* WorkflowBuilder
* WorkflowExecutor

---

# Queue System Rules

Queue system uses:

* Redis
* Celery

Requirements:

* FIFO safe execution
* GPU-safe concurrency
* retry handling
* cancellation support
* execution timeout handling

Agents must avoid:

* VRAM overload risks
* uncontrolled parallelism
* blocking execution paths

---

# WebSocket Rules

Realtime communication uses:

* Socket.IO

Required events:

* job_queued
* job_started
* progress_update
* preview_image
* preview_video
* job_completed
* job_failed

WebSocket code must:

* support reconnects
* avoid memory leaks
* avoid blocking operations

---

# API Rules

REST API requirements:

* versioned routes
* request validation
* response schemas
* structured error handling
* JWT authentication
* API key support

Route handlers must remain thin.

Business logic belongs in service layers.

---

# Database Rules

Use:

* SQLAlchemy ORM
* Alembic migrations

Track:

* jobs
* assets
* users
* workflows
* logs

Database code must:

* avoid raw SQL where unnecessary
* use relationships correctly
* support future PostgreSQL migration

---

# Storage Rules

Storage layer responsibilities:

* upload handling
* output handling
* cleanup jobs
* metadata tracking
* future S3 compatibility

Never directly manipulate storage paths outside storage services.

---

# Logging Rules

Logging must include:

* request logs
* queue logs
* workflow execution logs
* websocket logs
* exception traces

Use structured logging.

Do not use print statements.

---

# Security Rules

Required:

* JWT authentication
* API keys
* upload validation
* rate limiting
* file extension validation
* workflow whitelisting

Never expose raw ComfyUI endpoints publicly.

Never trust client-side validation.

---

# Docker Rules

Docker setup must:

* support GPU runtime
* use Docker Compose
* separate services cleanly
* support environment variables
* support persistent volumes

Expected services:

* backend
* redis
* comfyui
* nginx

---

# Performance Rules

Agents should optimize for:

* low memory overhead
* async I/O
* queue stability
* GPU utilization
* minimal workflow overhead

Avoid:

* repeated model reloads
* unnecessary JSON parsing
* blocking filesystem operations

---

# Testing Rules

Create tests for:

* API routes
* workflow execution
* queue behavior
* websocket events
* auth system

Use:

* pytest

---

# Documentation Rules

Every major module should contain:

* docstrings
* architecture explanation
* usage examples where necessary

README should contain:

* setup
* configuration
* deployment
* troubleshooting
* architecture overview

---

# Implementation Strategy

Agents must work in phases.

## Phase 1

Core backend:

* FastAPI
* config system
* database
* Redis
* health routes

## Phase 2

ComfyUI integration:

* workflow loading
* execution
* websocket tracking

## Phase 3

Queue system:

* Celery
* job lifecycle
* retries

## Phase 4

Storage and uploads:

* asset management
* cleanup
* serving

## Phase 5

Authentication and security

## Phase 6

Dashboard and monitoring

## Phase 7

Docker and deployment

---

# Important Runtime Assumptions

Assume:

* Ubuntu server
* NVIDIA GPU
* CUDA installed
* ComfyUI runs independently
* backend communicates through APIs
* local SSD storage initially

---

# Agent Behavioral Instructions

Agents should:

* make autonomous engineering decisions
* prefer scalable designs
* explain architecture choices
* verify imports
* verify runtime consistency
* maintain production quality

Agents should NOT:

* ask repetitive questions
* create incomplete implementations
* generate pseudo-code
* produce temporary hacks

If uncertainty exists:

* choose scalable architecture
* prioritize maintainability
* preserve modularity

---

# Final Goal

The final platform should resemble a private AI inference cloud similar to:

* RunPod infrastructure
* Stability AI internal systems
* enterprise ComfyUI orchestration platforms

The system must be capable of future scaling:

* multi-GPU
* distributed rendering
* cloud deployment
* Kubernetes orchestration
* multi-node workers


<claude-mem-context>
# Memory Context

# claude-mem status

This project has no memory yet. The current session will seed it; subsequent sessions will receive auto-injected context for relevant past work.

Memory injection starts on your second session in a project.

`/learn-codebase` is available if the user wants to front-load the entire repo into memory in a single pass (~5 minutes on a typical repo, optional). Otherwise memory builds passively as work happens.

Live activity: http://localhost:37777
How it works: `/how-it-works`

This message disappears once the first observation lands.
</claude-mem-context>