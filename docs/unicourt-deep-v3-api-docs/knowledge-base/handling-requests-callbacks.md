---
title: "Handling Requests and Callbacks during maintenance"
source: https://dart.unicourt.com/res-deep/assets/deep-v3-api-doc/knowledge-base/handling-requests-callbacks/
retrieved: 2026-10-01
---

# Handling Requests and Callbacks during maintenance

This article describes how to manage API requests and WebSocket callbacks during scheduled maintenance windows.

## Downtime behavior

During scheduled maintenance, REST API requests and WebSocket connections are temporarily unavailable. Requests sent during downtime may return errors such as HTTP **503 Service Unavailable**. Open WebSocket connections are terminated.

Operations already in progress may move to **DELAYED** status (with `statusDetails`) when court or internal systems are affected. UniCourt retries until the operation timeout; see [Case Update](../knowledge-base/case-update.md#when-an-update-is-delayed) for an example.

## Retrieving missed updates

After maintenance ends, backfill results using HTTP list endpoints, operation-specific callback endpoints, or historical WebSocket replay.

### REST API

**Case updates.** Use [**GET /workspace/{workspaceId}/caseUpdates**](#) to list update requests submitted during the outage window:

| Query parameter | Description |
| --- | --- |
| `lastNDays` | Look-back window (1–30 days; default `1`). Returns the **most recent** status per case in that period. |
| `status` | Optional: `IN_PROGRESS`, `DELAYED`, `COMPLETE`, or `FAILURE`. |
| `caseId` | Optional: filter to one case. |
| `pageNumber` | Pagination. |

List completed case updates after maintenance

```Shell
curl -X 'GET' \  'https://deep-api.unicourt.com/workspace/{workspaceId}/caseUpdates?lastNDays=2&status=COMPLETE&pageNumber=1' \  -H 'accept: application/json' \  -H 'Authorization: Bearer <Your JWT accessToken>'
```

For a single case, poll [**GET /workspace/{workspaceId}/caseUpdate/{caseId}**](#).

**Other operations.** Use the callback list endpoints for each operation type (for example, **GET /workspace/{workspaceId}/caseImport/callbacks**, **GET /workspace/{workspaceId}/caseDocumentOrder/callbacks**, **GET /workspace/{workspaceId}/caseExport/callbacks**) with the `date` and `status` filters documented in the respective KB articles.

### WebSocket (historical replay)

Replay callbacks missed while live connections were down using **`historicalCallbacks`** or **`workspaceHistoricalCallbacks`**:

Historical replay for a maintenance window

```Shell
wss://deep-callbacks.unicourt.com?accessToken=<Your_JWT_accessToken>&type=workspaceHistoricalCallbacks&workspaceId={workspaceId}&fromTime=2024-07-27T06:00:00+00:00&toTime=2024-07-27T14:00:00+00:00
```

Set **`fromTime`** to roughly four hours before maintenance start (UTC) and **`toTime`** to when service was restored. Add **`callbackType`** to limit to one operation (for example, `caseUpdate`, `caseImport`, `caseDocumentOrder`, `caseTrack`).

See [WebSocket Protocol](../knowledge-base/wss.md#historicalcallbacks) for all filters (`messages`, `last`, workspace vs account scope).

v2 WebSocket note

v2 used **`wss://callbacks.unicourt.com?…&type=historicalCallbacks`**. v3 uses **`deep-callbacks.unicourt.com`**; workspace-scoped streams require **`workspaceId`**.

## Migration Notes for v2 Integrators

If your maintenance runbook queries v2 **`/caseUpdates?requestedDate=…`**, update paths and query parameters as below.

| v2 Field / Endpoint | v3 Field / Endpoint | Notes |
| --- | --- | --- |
| `GET /caseUpdates?requestedDate=…` | `GET /workspace/{workspaceId}/caseUpdates?lastNDays=…` | v3 uses day-based look-back (`lastNDays`, max 30), not `requestedDate` |
| `wss://callbacks.unicourt.com?…&type=historicalCallbacks` | `wss://deep-callbacks.unicourt.com?…&type=historicalCallbacks` or `…&type=workspaceHistoricalCallbacks&workspaceId={id}` | Host changed; workspace variant added |
| `callbackType=caseExport` on historical | *(not a v3 historical filter)* | Replay exports via HTTP **GET /workspace/{workspaceId}/caseExport/callbacks** or sync **`workspaceCaseExport`** WSS |
