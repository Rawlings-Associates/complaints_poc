---
title: "WebSocket Protocol"
source: https://dart.unicourt.com/res-deep/assets/deep-v3-api-doc/knowledge-base/wss/
retrieved: 2026-10-01
---

# WebSocket Protocol

DEEP delivers long-running operation results over WebSocket as well as HTTP. Use **sync** channels when you submit one request and wait for the result on the same connection. Use **async** channels when you want a persistent stream of callbacks across many operations (or replay missed callbacks from history).

Full message schemas and examples are in the [**Callbacks & WebSockets API spec**](#).

## Connection URL

All v3 WebSocket connections use this pattern:

WebSocket URL pattern

```Shell
wss://deep-callbacks.unicourt.com?accessToken=<Your_JWT_accessToken>&type=<type>[&workspaceId=<workspaceId>][&filterParams...]
```

| Query parameter | Required | Description |
| --- | --- | --- |
| `accessToken` | Yes | JWT from the Authentication API |
| `type` | Yes | Channel name (see tables below) |
| `workspaceId` | For workspace-prefixed `type` values | Workspace scope (required for all `workspace*` types, including `workspaceLiveCallbacks` and `workspaceHistoricalCallbacks`) |

v2 host note

v2 used **`wss://callbacks.unicourt.com`**. v3 uses **`deep-callbacks.unicourt.com`**.

All messages are JSON-encoded strings.

### Connection limits

| Limit | Value |
| --- | --- |
| Maximum connections per subscription / `type` | **5** simultaneous connections per account |
| Maximum connection lifetime | **2 hours** (server closes the connection) |

Plan for reconnection before the 2-hour limit. See [WebSocket Best Practices](#websocket-best-practices) for overlapping live connections so you do not miss callbacks during handover.

## Channel overview

| Mode | v3 `type` values | Purpose |
| --- | --- | --- |
| **Sync (workspace)** | `workspaceCaseImport`, `workspaceCaseUpdate`, `workspaceCaseDocumentOrder`, `workspaceCaseExport`, `workspaceNormAttorneyUpdate` | Submit one request per message; receive result on the same connection |
| **Async live** | `liveCallbacks`, `workspaceLiveCallbacks` | Stream callbacks as operations complete (receive-only; do not send operation requests on this connection) |
| **Async historical** | `historicalCallbacks`, `workspaceHistoricalCallbacks` | Replay callbacks missed while live connections were down |
| **Service status (live)** | `liveServiceStatusChanges`, `workspaceLiveServiceStatusChanges` | Court system / service / source status change notifications |
| **Service status (subscribe)** | `workspaceCourtSystemServiceStatusChangeSubscription`, `workspaceCourtServiceStatusChangeSubscription`, `workspaceCourtSourceServiceStatusChangeSubscription`, `workspaceServiceStatusSubscription` | Subscribe to status-change feeds for a workspace |

## Sync WSS

Sync channels accept **one operation request per connection**. DEEP responds with acknowledgment and final callback objects, then closes the connection (or after the 2-hour maximum).

| v3 `type` | v2 `type` | KB reference |
| --- | --- | --- |
| `workspaceCaseUpdate` | `caseUpdate` | [Case Update](../knowledge-base/case-update.md) |
| `workspaceCaseDocumentOrder` | `caseDocumentOrder` | [Document Orders](../knowledge-base/document-orders.md) |
| `workspaceCaseExport` | `caseExport` | [Case Export](../knowledge-base/case-export.md) |
| `workspaceCaseImport` | *(not in v2 WSS docs)* | [Case Import](../knowledge-base/case-import.md) |
| `workspaceNormAttorneyUpdate` | *(not in v2 WSS docs)* | Entity update docs (see API spec) |

Case Track

There is **no** sync WebSocket channel for Case Track in v3. Schedule tracks over HTTP and monitor runs on **`liveCallbacks`** / **`workspaceLiveCallbacks`**, or poll **GET /workspace/{workspaceId}/caseTrack/{caseId}**. See [Case Track](../knowledge-base/case-track.md).

### Example: sync case update

Sync case update connection

```Shell
wss://deep-callbacks.unicourt.com?accessToken=<Your_JWT_accessToken>&type=workspaceCaseUpdate&workspaceId={workspaceId}
```

After the connection opens, send:

Sync update request

```json
{  "caseId": "CASEne32920dcecabe"}
```

Responses use the same `CaseUpdate` object shape as HTTP. See [Case Update](../knowledge-base/case-update.md#real-time-delivery-via-websocket) for field details.

### Example: sync document order

Sync document order connection

```Shell
wss://deep-callbacks.unicourt.com?accessToken=<Your_JWT_accessToken>&type=workspaceCaseDocumentOrder&workspaceId={workspaceId}
```

Sync document order request

```json
{  "caseDocumentId": "CDOCabc123def45678",  "isPreviewOnly": false}
```

See [Document Orders](../knowledge-base/document-orders.md) for `priorityLevel`, `notifyOnDelay`, PACER options, and response shapes.

## Async WSS

Async channels are **receive-only**. Submit operations over HTTP or a **sync** workspace channel; callbacks arrive on the live stream. If the live connection drops, replay from historical.

### LiveCallbacks

Account-level live callbacks

```Shell
wss://deep-callbacks.unicourt.com?accessToken=<Your_JWT_accessToken>&type=liveCallbacks
```

Workspace-scoped live callbacks

```Shell
wss://deep-callbacks.unicourt.com?accessToken=<Your_JWT_accessToken>&type=workspaceLiveCallbacks&workspaceId={workspaceId}
```

**Payload types on live streams**:

| Operation | Live object | Notes |
| --- | --- | --- |
| Case import | `CaseImportCallback` | **New in v3** live stream |
| Case update | `CaseUpdate` |  |
| Case track | `CaseTrack` | Per scheduled track run |
| Norm attorney update | `NormAttorneyUpdate` | **New in v3** |
| Norm attorney track | `NormAttorneyTrack` | **New in v3** |

Payload size

When an inline `case` (or similar nested object) would exceed **127 KB**, the stream may emit `"case": null` (or an empty object). Follow **`caseAPI`** on the callback to fetch the full object.

Export and document order delivery

`liveCallbacks` does **not** include Case Export or Document Order message types. Use the **`workspaceCaseExport`** / **`workspaceCaseDocumentOrder`** sync channels or HTTP instead, and use **historical** replay for document orders.

You cannot send operation requests on a live callbacks connection.

### HistoricalCallbacks

Account-level historical callbacks

```Shell
wss://deep-callbacks.unicourt.com?accessToken=<Your_JWT_accessToken>&type=historicalCallbacks
```

Workspace-scoped historical callbacks

```Shell
wss://deep-callbacks.unicourt.com?accessToken=<Your_JWT_accessToken>&type=workspaceHistoricalCallbacks&workspaceId={workspaceId}
```

**Payload types on historical streams**:

| Operation | Historical object | `callbackType` filter value |
| --- | --- | --- |
| Case import | `CaseImportCallback` | `caseImport` |
| Case update | `CaseUpdatePreview` | `caseUpdate` |
| Document order | `CaseDocumentOrderCallback` | `caseDocumentOrder` |
| Case track | `CaseTrackPreview` | `caseTrack` |
| Norm attorney update | `NormAttorneyUpdate` preview | `normAttorneyUpdate` |
| Norm attorney track | `NormAttorneyTrack` preview | `normAttorneyTrack` |

Historical streams return **preview** objects for update and track (not full inline cases). Use **`caseAPI`** on the preview to fetch the latest case when needed.

#### Historical filters

| Filter | Values | Description |
| --- | --- | --- |
| `callbackType` | `caseImport`, `caseUpdate`, `caseDocumentOrder`, `caseTrack`, `normAttorneyUpdate`, `normAttorneyTrack` | Limit to one operation type |
| `messages` | `unposted`, `posted`, `all` | Use `messages=all` to include all delivery states; use `unposted` to focus on callbacks not yet delivered on a live connection |
| `fromTime` / `toTime` | `YYYY-MM-DDTHH:MM:SS+ZZ:zz` | Time-range replay based on request completion time |
| `last` | Integer (default `100`) | Most recent N callbacks |

Examples:

Historical case updates only

```Shell
wss://deep-callbacks.unicourt.com?accessToken=<Your_JWT_accessToken>&type=workspaceHistoricalCallbacks&workspaceId={workspaceId}&callbackType=caseUpdate
```

Historical time range

```Shell
wss://deep-callbacks.unicourt.com?accessToken=<Your_JWT_accessToken>&type=historicalCallbacks&fromTime=2025-08-01T00:00:00+00:00&toTime=2025-08-01T23:59:59+00:00
```

Last 100 historical messages

```Shell
wss://deep-callbacks.unicourt.com?accessToken=<Your_JWT_accessToken>&type=historicalCallbacks&last=100
```

All historical messages (posted and unposted)

```Shell
wss://deep-callbacks.unicourt.com?accessToken=<Your_JWT_accessToken>&type=historicalCallbacks&messages=all
```

Export on historical

v3 **`callbackType`** values do **not** include `caseExport`. Use the **`workspaceCaseExport`** sync WebSocket or HTTP callback polling for exports.

When all matching historical callbacks are delivered, the connection closes automatically. Do not manually disconnect a historical session early if you intend to receive the full set—the server closes it when delivery is complete.

## Service status WebSockets

v3 provides subscription channels (send subscribe/unsubscribe/view requests) and live streams (receive status-change notifications) for court service availability.

### Subscription channels

Open a workspace-scoped connection, then send a JSON message with an **`action`** of `subscribe`, `unsubscribe`, or `viewSubscription`.

| v3 `type` | Subscribe by | Notes |
| --- | --- | --- |
| `workspaceCourtSystemServiceStatusChangeSubscription` | `courtSystemIdArray` | Court system–level status changes |
| `workspaceCourtServiceStatusChangeSubscription` | `courtSystemIdArray` and/or `courtIdArray` | Court-level status changes |
| `workspaceCourtSourceServiceStatusChangeSubscription` | `courtSystemIdArray`, `courtIdArray`, and/or `courtSourceIdArray` | Court source–level status changes |
| `workspaceServiceStatusSubscription` | Court source service status | Distinct accepted `type` for court source status subscriptions. See the [**Callbacks & WebSockets API spec**](#) for the request and response schemas for this type |

All subscription types require **`workspaceId`** (with **`accessToken`** and **`type`**).

Court system status subscription

```Shell
wss://deep-callbacks.unicourt.com?accessToken=<Your_JWT_accessToken>&type=workspaceCourtSystemServiceStatusChangeSubscription&workspaceId={workspaceId}
```

Example request after connect (`workspaceCourtSystemServiceStatusChangeSubscription`):

Subscribe to court system status changes

```json
{  "action": "subscribe",  "courtSystemIdArray": [    { "courtSystemId": "COSYmiJJ6VFfuGDf2t" }  ]}
```

View current subscriptions

```json
{  "action": "viewSubscription"}
```

Court service status subscription

```Shell
wss://deep-callbacks.unicourt.com?accessToken=<Your_JWT_accessToken>&type=workspaceCourtServiceStatusChangeSubscription&workspaceId={workspaceId}
```

Subscribe by court and court system

```json
{  "action": "subscribe",  "courtIdArray": [    { "courtId": "CORTV4vCEaKrhystBz" }  ],  "courtSystemIdArray": [    { "courtSystemId": "COSYmiJJ6VFfuGDf2t" }  ]}
```

Court source status subscription

```Shell
wss://deep-callbacks.unicourt.com?accessToken=<Your_JWT_accessToken>&type=workspaceCourtSourceServiceStatusChangeSubscription&workspaceId={workspaceId}
```

Subscribe by court source, court, and court system

```json
{  "action": "subscribe",  "courtSourceIdArray": [    { "courtSourceId": "CTSSf45fd1bd792e97" }  ],  "courtIdArray": [    { "courtId": "CORTV4vCEaKrhystBz" }  ],  "courtSystemIdArray": [    { "courtSystemId": "COSYmiJJ6VFfuGDf2t" }  ]}
```

workspaceServiceStatusSubscription

```Shell
wss://deep-callbacks.unicourt.com?accessToken=<Your_JWT_accessToken>&type=workspaceServiceStatusSubscription&workspaceId={workspaceId}
```

Use **`workspaceServiceStatusSubscription`** for court source service status subscription requests. Message schemas for this type are in the API spec.

### Live service status streams

After you subscribe, receive change notifications on the live service status channels (receive-only):

Account-level live service status changes

```Shell
wss://deep-callbacks.unicourt.com?accessToken=<Your_JWT_accessToken>&type=liveServiceStatusChanges
```

Workspace-scoped live service status changes

```Shell
wss://deep-callbacks.unicourt.com?accessToken=<Your_JWT_accessToken>&type=workspaceLiveServiceStatusChanges&workspaceId={workspaceId}
```

**Payload types** on these streams:

| Object | When you receive it |
| --- | --- |
| `CourtSystemServiceStatusChange` | Court system service status changed |
| `CourtServiceStatusChange` | Court service status changed |
| `CourtSourceServiceStatusChange` | Court source service status changed |

`workspaceLiveServiceStatusChanges` uses the same message payloads as `liveServiceStatusChanges` and requires **`workspaceId`**.

## WebSocket Best Practices

Callback messages can be missed if a client disconnects, reconnects frequently, or drops mid-delivery. DEEP may already have attempted delivery on the previous live connection, so that callback is not retransmitted on a new live connection. Combine **overlapping live connections**, **historical replay**, and **HTTP status polling** for reliable delivery.

These practices apply to all callback types (case update, export, tracking, document orders, and other callback-enabled APIs)—not only case update.

### 1. Maintain overlapping live connections

Each connection closes after a **maximum of 2 hours**. Before closing (or before the server closes) an active live connection, open a second live connection so the streams overlap briefly. That overlap prevents gaps during handover.

**Example:**

1. Keep **Live Connection 1** open.
2. About **10 minutes** before the 2-hour limit, open **Live Connection 2**.
3. After the overlap window, let Connection 1 close (or close it yourself once Connection 2 is receiving).
4. Repeat for the next cycle.

![Connection timeline showing overlapping live WebSocket connections and historical backfill across 2-hour cycles](/res-deep/assets/deep-v3-api-doc/assets/images/wss-connection-timeline-baf9433104c17f795c82380c840ab994.png)

Stay within the **5 connections per `type`** limit. During a normal handover you typically need only two live connections of the same type.

### 2. Restore missed messages with historical callbacks

Historical channels are not real-time. Use them after disconnects, downtime, or at the end of a batch window to reconcile anything the live stream may have missed.

Account-level historical recovery

```Shell
wss://deep-callbacks.unicourt.com?accessToken=<Your_JWT_accessToken>&type=historicalCallbacks
```

Workspace-scoped historical recovery

```Shell
wss://deep-callbacks.unicourt.com?accessToken=<Your_JWT_accessToken>&type=workspaceHistoricalCallbacks&workspaceId={workspaceId}
```

Useful patterns:

- `messages=all` — retrieve all matching callbacks that reached a final state (posted and unposted)
- `callbackType=caseUpdate` (or another type) — narrow recovery to one operation
- `fromTime` / `toTime` — bound recovery to a maintenance or outage window
- `last=100` — pull the most recent N callbacks

Do not manually disconnect a historical session early if you need the full result set; the server closes the connection after delivery.

### 3. Use a status API as a fallback

When WebSockets are unavailable or impractical (for example, low-frequency batch checks), poll the resource-specific status endpoint for the operation type.

Example for case update:

Poll case update status

```Shell
GET /workspace/{workspaceId}/caseUpdate/{caseId}
```

After submitting a batch, wait for expected processing time, then poll. See the individual KB articles ([Case Update](../knowledge-base/case-update.md), [Case Import](../knowledge-base/case-import.md), [Document Orders](../knowledge-base/document-orders.md), and others) for the correct status and callback list endpoints.

### Recommended practices checklist

- **Connection management:** Overlap live connections before expiry; keep live sockets open long enough to receive callbacks; stay within **5** connections per `type`.
- **Live + historical:** Use live for real-time delivery; use historical after reconnects or on a periodic schedule for completeness.
- **Targeted recovery:** Filter historical streams with `callbackType`, `fromTime`, `toTime`, `messages`, and `last`.
- **HTTP fallback:** Poll status / callback list endpoints when sockets fail.
- **Logging:** Record connect and disconnect timestamps for debugging. Validate HTTP status responses before treating them as authoritative.

### Prefer sync channels for single operations

When you only need one import, update, export, or document order, **`workspaceCase*`** sync types avoid managing a separate live listener.

### Testing WebSocket connections

A browser **WebSocket Test Client** (or similar tool) is useful for constructing URLs and inspecting JSON messages during integration:

1. Enter the `wss://deep-callbacks.unicourt.com?…` URL (including `accessToken`, `type`, and `workspaceId` when required).
2. Open the connection.
3. For sync or subscription channels, send the JSON request body, then inspect the response log.

Remember the **5 connections per `type`** account limit when testing from multiple tools or tabs.

## Migration Notes for v2 Integrators

If your integration connects to v2 `callbacks.unicourt.com` with unprefixed `type` values, update hosts, types, and query parameters as below.

### Host and URL

| v2 | v3 |
| --- | --- |
| `wss://callbacks.unicourt.com` | `wss://deep-callbacks.unicourt.com` |
| `?accessToken=…&type=…` | Same, plus `&workspaceId=…` for all `workspace*` types |

### Sync `type` mapping

| v2 `type` | v3 `type` | Notes |
| --- | --- | --- |
| `caseUpdate` | `workspaceCaseUpdate` | Requires `workspaceId` |
| `caseDocumentOrder` | `workspaceCaseDocumentOrder` | Requires `workspaceId` |
| `caseExport` | `workspaceCaseExport` | Requires `workspaceId` |
| *(none)* | `workspaceCaseImport` | New sync channel |
| *(none)* | `workspaceNormAttorneyUpdate` | New sync channel |

### Async `type` mapping

| v2 `type` | v3 `type` | Notes |
| --- | --- | --- |
| `liveCallbacks` | `liveCallbacks` + `workspaceLiveCallbacks` | Workspace variant requires `workspaceId` |
| `historicalCallbacks` | `historicalCallbacks` + `workspaceHistoricalCallbacks` | Workspace variant requires `workspaceId` |

### Historical `callbackType` values

| v2 | v3 |
| --- | --- |
| `caseUpdate`, `caseExport`, `caseDocumentOrder`, `caseTrack` | Same set **plus** `caseImport`, `normAttorneyUpdate`, `normAttorneyTrack`; **`caseExport` is not a v3 historical filter** — use the sync export channel |

### Historical `messages` filter

| v2 | v3 |
| --- | --- |
| `unposted`, `all` | `unposted`, `posted`, `all` |

### Removed in v3

- **`GET /callbacks`** (`getCallbacks`) — v2 REST helper for listing callbacks by date; not available in v3

| v2 Field / Endpoint | v3 Field / Endpoint | Notes |
| --- | --- | --- |
| `wss://callbacks.unicourt.com?…&type=caseUpdate` | `wss://deep-callbacks.unicourt.com?…&type=workspaceCaseUpdate&workspaceId={id}` | Host, type prefix, workspace param |
| `wss://callbacks.unicourt.com?…&type=liveCallbacks` | `wss://deep-callbacks.unicourt.com?…&type=liveCallbacks` or `…&type=workspaceLiveCallbacks&workspaceId={id}` | Workspace-scoped variant added |
| `GET /callbacks` | *(removed)* | Use `historicalCallbacks` WSS or operation-specific HTTP callback endpoints |
