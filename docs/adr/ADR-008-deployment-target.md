# ADR-008: Deployment Target

## Status

Accepted

## Context

MVP requires local development (Docker Compose), CI (GitHub Actions), and a credible cloud deployment path (Terraform scaffold). INFRA stories assume containerized deployment to AWS ECS Fargate or GCP Cloud Run with managed PostgreSQL, object storage, and Redis.

## Decision

**Primary cloud deployment: AWS ECS Fargate**

Stack:
- **ECS Fargate** — separate services for `api` and `worker` (same container image, different command)
- **RDS PostgreSQL 16** — pgvector enabled
- **ElastiCache Redis** — Celery broker
- **S3** — document object storage
- **ALB** — HTTPS termination
- **Secrets Manager** — JWT secret, DB URL, API keys
- **ECR** — container registry
- **Terraform** — scaffold modules under `terraform/environments/dev`

**Local:** Docker Compose with pgvector postgres, redis, api, worker.

**CI:** GitHub Actions — lint, pytest, Docker build.

## Consequences

**Positive:**
- No Kubernetes complexity; Fargate fits MVP team size
- Native S3 integration for document storage
- RDS pgvector is well documented
- Same Docker image local and cloud — high parity
- Strong signal for AWS infrastructure skills

**Negative:**
- AWS cost ~$60–80/mo minimum while running
- ECS/Terraform learning curve vs simpler PaaS
- Cloud Run would be simpler for API-only; worker + Redis fits AWS better

## Alternatives Considered

| Alternative | Why not selected |
|-------------|------------------|
| **GCP Cloud Run** | Excellent for stateless API; worker + Redis + pgvector slightly more fragmented on GCP for this layout; either cloud acceptable — AWS chosen for S3/RDS cohesion |
| **Heroku / Render PaaS** | Less Terraform depth; weaker IaC story |
| **Kubernetes (EKS/GKE)** | Over-engineered for MVP per architecture principles |
| **Single EC2 instance** | Poor operational habit; manual scaling |

## Implementation Notes

- One Dockerfile; multi-stage build for smaller image
- ECS task definitions: api exposes port 8000; worker no load balancer
- Run migrations as one-off ECS task before deploy
- Terraform outputs: ALB DNS, S3 bucket name (document in README)
- IAM task role for S3 — no static AWS keys in containers
- `.env.example` documents all variables for local parity
- Optional: deploy frontend as S3 static site + CloudFront (not blocking MVP)
