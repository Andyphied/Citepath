# Deployment Process

## Standard Release Flow

1. Merge feature branch to `main` after CI passes.
2. Tag release candidate and deploy to staging.
3. Run smoke tests including billing-api charge flow.
4. Promote to production during the approved change window.
5. Monitor error rates for 30 minutes post-deploy.

## Post-Deploy Verification

After every production deployment, verify:

- API gateway upstream health for critical services
- billing-api `/health/ready` and sample invoice query
- auth-service token issuance smoke test

## Rollback

If error rates exceed SLO within 15 minutes, rollback the deployment and notify #incidents.

## Documentation Requirements

Each deployment must include notes in the change ticket describing config changes that affect gateway timeouts or database pools.
