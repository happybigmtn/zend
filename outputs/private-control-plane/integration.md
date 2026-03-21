# Private Control Plane Integration

Status: integrated on 2026-03-21

## Runtime Contract

The private control plane now exposes a reviewed event-spine read contract
without introducing a second receipt store:

- `GET /spine/events`
- Query params:
  - `client=<device-name>` for observe-scoped reads
  - `surface=<home|inbox|agent|device_pairing|device_permissions>`
  - `kind=<event-kind>`
  - `limit=<positive-int>`

The response shape is:

```json
{
  "events": [
    {
      "id": "uuid",
      "principal_id": "uuid",
      "kind": "control_receipt",
      "payload": {},
      "created_at": "2026-03-21T14:00:27.631774+00:00"
    }
  ]
}
```

## Shared Surfaces

- `spine.py` is now the single place that knows how event kinds route onto
  inbox-adjacent surfaces.
- `daemon.py` delegates event-spine reads through the shared routing logic.
- `cli.py events --surface <surface>` uses the same projection rules as HTTP.

## Expected Consumers

- Existing reviewed proof flows can read raw events from `/spine/events`.
- Client or script consumers that want the operations inbox view should request
  `surface=inbox` instead of re-implementing routing rules elsewhere.
