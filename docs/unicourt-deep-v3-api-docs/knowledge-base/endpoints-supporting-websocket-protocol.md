---
title: "Endpoints Supporting the WebSocket Protocol"
source: https://dart.unicourt.com/res-deep/assets/deep-v3-api-doc/knowledge-base/endpoints-supporting-websocket-protocol/
retrieved: 2026-10-01
---

# Endpoints Supporting the WebSocket Protocol

DEEP exposes long-running operation results over WebSocket in two modes:

- **Sync** — Open a connection, send one JSON request, receive acknowledgment and completion on the same connection, then the connection closes.
- **Async** — Open a **live** or **historical** stream to receive callbacks for operations you submitted over HTTP or sync WebSocket.

For connection rules, filters, payload limits, and migration detail, see [WebSocket Protocol](../knowledge-base/wss.md). Message schemas are in the [**Callbacks & WebSockets API spec**](#).

## Connection URL

v3 WebSocket URL pattern

```Shell
wss://deep-callbacks.unicourt.com?accessToken=<Your_JWT_accessToken>&type=<type>[&workspaceId=<workspaceId>][&filterParams...]
```

Pass your JWT as **`accessToken`**. All `workspace*` types also require **`workspaceId`**.

v2 host note

v2 used **`wss://callbacks.unicourt.com`**. v3 uses **`deep-callbacks.unicourt.com`**.

Connections stay open up to **2 hours**. A maximum of **5** simultaneous connections are allowed per `type` per account. All messages are JSON strings.

For overlapping reconnects, historical backfill, and HTTP fallbacks, see [WebSocket Best Practices](../knowledge-base/wss.md#websocket-best-practices).

## Sync endpoints

Submit one operation per connection. DEEP closes the connection after the final callback (or at the 2-hour limit).

| v3 `type` | Request message (JSON) | KB article |
| --- | --- | --- |
| `workspaceCaseUpdate` | `{ "caseId": "<caseId>" }` (+ optional fields from HTTP) | [Case Update](../knowledge-base/case-update.md) |
| `workspaceCaseDocumentOrder` | `{ "caseDocumentId": "<id>", "isPreviewOnly": false, … }` | [Document Orders](../knowledge-base/document-orders.md) |
| `workspaceCaseExport` | `{ "caseId": "<caseId>" }` | [Case Export](../knowledge-base/case-export.md) |
| `workspaceCaseImport` | Same body as HTTP **PUT** `/workspace/{workspaceId}/caseImport` | [Case Import](../knowledge-base/case-import.md) |
| `workspaceNormAttorneyUpdate` | See API spec | Entity update (API spec) |

**Example — sync case update:**

Sync case update

```Shell
wss://deep-callbacks.unicourt.com?accessToken=<Your_JWT_accessToken>&type=workspaceCaseUpdate&workspaceId={workspaceId}
```

```json
{ "caseId": "CASEne32920dcecabe" }
```

Case Track

Case Track has **no** sync WebSocket channel in v3. Use HTTP scheduling plus **`liveCallbacks`** / **`workspaceLiveCallbacks`**, or poll **GET /workspace/{workspaceId}/caseTrack/{caseId}`. See [Case Track](../knowledge-base/case-track.md).

## Async endpoints

Receive-only streams. Submit operations via HTTP or sync WebSocket; callbacks arrive on the live connection. Replay missed callbacks from historical.

| v3 `type` | Scope | Purpose |
| --- | --- | --- |
| `liveCallbacks` | Account | Real-time callback stream |
| `workspaceLiveCallbacks` | Workspace | Same payloads; requires `workspaceId` |
| `historicalCallbacks` | Account | Replay missed callbacks |
| `workspaceHistoricalCallbacks` | Workspace | Same filters; requires `workspaceId` |

Workspace live callbacks

```Shell
wss://deep-callbacks.unicourt.com?accessToken=<Your_JWT_accessToken>&type=workspaceLiveCallbacks&workspaceId={workspaceId}
```

**Live stream payload types**: `CaseImportCallback`, `CaseUpdate`, `CaseTrack`, `NormAttorneyUpdate`, `NormAttorneyTrack`.

**Historical `callbackType` filters**: `caseImport`, `caseUpdate`, `caseDocumentOrder`, `caseTrack`, `normAttorneyUpdate`, `normAttorneyTrack`.

Additional historical filters: `messages` (`unposted`, `posted`, `all`), `fromTime` / `toTime`, `last`.

Export and document order delivery

`liveCallbacks` / historical streams do not carry Case Export on live, and `caseExport` is not a historical `callbackType` filter. Use **`workspaceCaseExport`** / **`workspaceCaseDocumentOrder`** sync channels or HTTP callbacks. See [WebSocket Protocol](../knowledge-base/wss.md#async-wss).

Do not send operation requests on live or historical connections.

## Service status WebSockets

| v3 `type` | Purpose |
| --- | --- |
| `workspaceCourtSystemServiceStatusChangeSubscription` | Subscribe by court system ID |
| `workspaceCourtServiceStatusChangeSubscription` | Subscribe by court and/or court system ID |
| `workspaceCourtSourceServiceStatusChangeSubscription` | Subscribe by court source, court, and/or court system ID |
| `workspaceServiceStatusSubscription` | Court source service status subscription |
| `liveServiceStatusChanges` | Account-level live status-change stream |
| `workspaceLiveServiceStatusChanges` | Workspace-scoped live status-change stream |

Request bodies, payload objects (`CourtSystemServiceStatusChange`, `CourtServiceStatusChange`, `CourtSourceServiceStatusChange`), and examples: [WebSocket Protocol — Service status](../knowledge-base/wss.md#service-status-websockets).

## Maintenance and missed callbacks

During downtime, connections drop and HTTP requests may fail. After maintenance, backfill with **GET /workspace/{workspaceId}/caseUpdates** (and other callback list endpoints) or **`workspaceHistoricalCallbacks`** with a `fromTime`/`toTime` window. See [Handling Requests and Callbacks during maintenance](../knowledge-base/handling-requests-callbacks.md).

## Migration Notes for v2 Integrators

| v2 `type` | v3 `type` |
| --- | --- |
| `caseUpdate` | `workspaceCaseUpdate` (+ `workspaceId`) |
| `caseDocumentOrder` | `workspaceCaseDocumentOrder` (+ `workspaceId`) |
| `caseExport` | `workspaceCaseExport` (+ `workspaceId`) |
| `liveCallbacks` | `liveCallbacks` or `workspaceLiveCallbacks` |
| `historicalCallbacks` | `historicalCallbacks` or `workspaceHistoricalCallbacks` |

| v2 Field / Endpoint | v3 Field / Endpoint | Notes |
| --- | --- | --- |
| `wss://callbacks.unicourt.com` | `wss://deep-callbacks.unicourt.com` | Host change |
| Unprefixed sync `type` values | `workspace*` prefix + `workspaceId` | All sync ops workspace-scoped |
| Historical `messages`: `unposted`, `all` | Adds **`posted`** | See [WebSocket Protocol](../knowledge-base/wss.md) |
| `GET /callbacks` | *(removed)* | Use historical WSS or operation callback HTTP endpoints |
