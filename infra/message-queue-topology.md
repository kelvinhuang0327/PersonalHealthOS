# Message Queue Topology

## Broker
- RabbitMQ (HA mode)

## Exchanges
- `health.events` (topic)
- `notification.events` (topic)
- `report.events` (topic)

## Routing Keys
- `health.metric.recorded`
- `health.symptom.logged`
- `health.lab_report.parsed`
- `health.risk_alert.created`
- `device.data.ingested`
- `notification.reminder.triggered`
- `report.pdf.requested`
- `report.pdf.generated`

## Queues
- `ai-risk-prediction.q`
- `notification-dispatch.q`
- `timeline-projection.q`
- `device-normalization.q`
- `pdf-generation.q`

## Dead Letter Queues
- `ai-risk-prediction.dlq`
- `notification-dispatch.dlq`
- `timeline-projection.dlq`
- `device-normalization.dlq`
- `pdf-generation.dlq`

## Consumer Contracts
- At-least-once delivery
- Idempotency key required
- Retry with exponential backoff
- Poison message -> DLQ + alert
