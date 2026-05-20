# Security Architecture

## Identity & Access
- OAuth2 + JWT + refresh rotation
- RBAC roles: `owner`, `family_admin`, `family_member`, `clinician_viewer`
- ABAC rules for family resource sharing

## Data Protection
- TLS 1.2+ all traffic
- S3 SSE encryption
- Postgres encrypted volumes
- PII field-level encryption

## API Security
- API Gateway JWT verification
- WAF + rate limiting + IP reputation
- Request schema validation
- Response data masking in logs

## File Security
- MIME whitelist
- max size policy
- antivirus scanning queue
- blocked executable/document macro policies

## AI Safety
- Prompt injection filter
- Evidence grounding guardrail
- Banned medical diagnosis language filter
- Human escalation for high-risk outputs

## Monitoring
- Audit trails immutable storage
- SIEM alerts for suspicious behavior
- periodic key rotation and secret scanning
