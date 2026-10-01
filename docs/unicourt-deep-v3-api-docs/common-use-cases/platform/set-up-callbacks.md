---
title: "Set up Callbacks"
source: https://dart.unicourt.com/res-deep/assets/deep-v3-api-doc/common-use-cases/platform/set-up-callbacks/
retrieved: 2026-10-01
---

# Set up Callbacks

Imports, updates, document orders, tracks, and exports finish **asynchronously**. You need a reliable way to learn when each run hits **`COMPLETE`**, **`FAILURE`**, or **`DELAYED`**—without blocking your HTTP client on a long poll loop for every job.

DEEP offers three complementary patterns:

1. **Sync WebSocket** — submit one request and wait for the result on the same connection
2. **Live + historical WebSocket** — stream callbacks for many HTTP (or sync) jobs; backfill what you missed
3. **HTTP polling** — operation-specific callback endpoints when you prefer REST only

**Reference docs:** [WebSocket Protocol](../../knowledge-base/wss.md) (hosts, filters, payload types), [Endpoints Supporting the WebSocket Protocol](../../knowledge-base/endpoints-supporting-websocket-protocol.md), [Handling Requests and Callbacks during maintenance](../../knowledge-base/handling-requests-callbacks.md).

Spec: [**Callbacks & WebSockets API**](#).

## Before you start

You need:

- A **JWT** (`accessToken` query param on the WebSocket URL)
- A **`workspaceId`** for every `workspace*` channel
- Clarity on whether you are doing **one-shot** jobs or a **high-volume** pipeline

Host: **`wss://deep-callbacks.unicourt.com`** (not the v2 `callbacks.unicourt.com` host).

WebSocket URL pattern

```Shell
wss://deep-callbacks.unicourt.com?accessToken=<Your_JWT_accessToken>&type=<type>&workspaceId={workspaceId}
```

Connections close after a sync job finishes, or after a **maximum of 2 hours**. You may open up to **5** simultaneous connections per `type` per account. Before a live connection hits the 2-hour limit, open a second overlapping live connection so you do not miss callbacks—see [WebSocket Best Practices](../../knowledge-base/wss.md#websocket-best-practices). All messages are JSON.

## Pick a delivery pattern

| Situation | Prefer |
| --- | --- |
| One import / update / document order / export and you can hold a socket open | **Sync WebSocket** (`workspaceCaseUpdate`, etc.) |
| Many concurrent jobs; you already submit over HTTP | **`workspaceLiveCallbacks`** + **`workspaceHistoricalCallbacks`** |
| You cannot use WebSockets | **HTTP poll** the operation’s callback or status endpoints |
| Case Track schedule runs | HTTP schedule + **live/historical** (no sync track channel) |

Product walkthroughs that submit work: [Update a case once](../../common-use-cases/keep-cases-current/update-a-case-once.md), [Getting documents from cases](../../common-use-cases/get-case-content/get-a-case-document.md), [Export a case](../../common-use-cases/get-case-content/export-a-case.md), [Track a case on a schedule](../../common-use-cases/keep-cases-current/track-a-case-on-a-schedule.md), [Import a case from PACER](../../common-use-cases/find-and-read-cases/import-a-case-from-pacer.md) (PACER import is sync HTTP; court-source import uses Case Import + callbacks).

## Pattern A — Sync WebSocket (one job, one connection)

Open a channel whose **`type`** matches the operation, send the same JSON body you would use on HTTP, and read acknowledgment + final callback on that connection.

| `type` | Typical body |
| --- | --- |
| `workspaceCaseUpdate` | `{ "caseId": "…" }` (+ optional fields) |
| `workspaceCaseDocumentOrder` | `{ "caseDocumentId": "…", "isPreviewOnly": false, … }` |
| `workspaceCaseExport` | `{ "caseId": "…" }` |
| `workspaceCaseImport` | Same as HTTP **PUT** Case Import |
| `workspaceNormAttorneyUpdate` | See Entity Update in the AsyncAPI / REST spec |

Sync case update

```Shell
wss://deep-callbacks.unicourt.com?accessToken=<Your_JWT_accessToken>&type=workspaceCaseUpdate&workspaceId={workspaceId}
```

Send after connect

```json
{  "caseId": "CASEne32920dcecabe"}
```

Response objects match the HTTP shapes (`CaseUpdate`, `CaseImportCallback`, and so on). Field detail: product KB articles linked from [WebSocket Protocol — Sync WSS](../../knowledge-base/wss.md#sync-wss).

Case Track

There is **no** `workspaceCaseTrack` sync channel. Create schedules with **PUT /workspace/{workspaceId}/caseTrack**; receive run status on live/historical or by polling **GET /workspace/{workspaceId}/caseTrack/{caseId}**.

## Pattern B — Live stream + historical backfill

### 1. Keep a live listener open

Workspace live callbacks

```Shell
wss://deep-callbacks.unicourt.com?accessToken=<Your_JWT_accessToken>&type=workspaceLiveCallbacks&workspaceId={workspaceId}
```

Account-wide: **`type=liveCallbacks`** (omit `workspaceId`).

This connection is **receive-only**. Submit jobs over HTTP (or Pattern A). Live payloads include types such as **`CaseImportCallback`**, **`CaseUpdate`**, **`CaseTrack`**, **`NormAttorneyUpdate`**, and **`NormAttorneyTrack`**.

Do **not** send import/update request JSON on the live socket.

Large payloads

If an inline `case` would exceed ~127 KB, the callback may set **`case`: null**. Follow **`caseAPI`** (or the equivalent API link) to fetch the full object.

### 2. Replay what you missed

When the live socket drops, clients restart, or you come back from maintenance, open historical:

Replay case updates for this workspace

```Shell
wss://deep-callbacks.unicourt.com?accessToken=<Your_JWT_accessToken>&type=workspaceHistoricalCallbacks&workspaceId={workspaceId}&callbackType=caseUpdate&messages=unposted
```

Useful query filters:

| Filter | Purpose |
| --- | --- |
| **`callbackType`** | `caseImport`, `caseUpdate`, `caseDocumentOrder`, `caseTrack`, `normAttorneyUpdate`, `normAttorneyTrack` |
| **`messages`** | `unposted`, `posted`, or `all` |
| **`fromTime`** / **`toTime`** | Time-range backfill |
| **`last`** | Most recent N callbacks |

Historical rows for update/track are often **preview** objects—use **`caseAPI`** when you need the full case.

The historical connection closes when matching messages are delivered.

### Recommended combo

```mermaid
flowchart TD  A[Submit jobs over HTTP or sync WSS] --> B[workspaceLiveCallbacks]  B --> C{Socket drop or restart?}  C -->|yes| D[workspaceHistoricalCallbacks backfill]  D --> B  C -->|no| B
```

Many teams also run a periodic historical poll (`last=100` or a `fromTime` window) as a safety net.

## Pattern C — HTTP polling only

Every async product exposes REST status / callback list endpoints. Examples:

| Operation | Poll |
| --- | --- |
| Case update | `GET /workspace/{workspaceId}/caseUpdate/{caseId}` or `.../caseUpdates` |
| Case import | `GET /workspace/{workspaceId}/caseImport/callbacks/{caseImportCallbackId}` |
| Document order | `GET /workspace/{workspaceId}/caseDocumentOrder/callbacks/...` |
| Case track | `GET /workspace/{workspaceId}/caseTrack/{caseId}` |
| Case export | `GET /workspace/{workspaceId}/caseExport/callbacks/...` |

After maintenance, combine those list endpoints with historical WSS—see [Handling Requests and Callbacks during maintenance](../../knowledge-base/handling-requests-callbacks.md).

## After you receive a callback

1. Branch on **`status`**: continue waiting on **`IN_PROGRESS`** / **`DELAYED`**; process **`COMPLETE`**; log/retry **`FAILURE`**.
2. Prefer **`caseAPI`**, **`normAttorneyAPI`**, or document **`fileUrl`** links over assuming inline payloads are complete.
3. Continue with the matching use case: [Read a full case](../../common-use-cases/find-and-read-cases/read-a-full-case.md), [Getting documents from cases](../../common-use-cases/get-case-content/get-a-case-document.md), [See what changed on a case](../../common-use-cases/keep-cases-current/sync-case-history.md).

## v3 vs v2

| v2 | v3 |
| --- | --- |
| `wss://callbacks.unicourt.com` | `wss://deep-callbacks.unicourt.com` |
| `type=caseUpdate` (etc.) | `type=workspaceCaseUpdate` + **`workspaceId`** |
| `liveCallbacks` / `historicalCallbacks` only | Plus **`workspaceLiveCallbacks`** / **`workspaceHistoricalCallbacks`** |
| Historical `messages`: `unposted`, `all` | Adds **`posted`** |
| `GET /callbacks` | Removed — use historical WSS or HTTP callback lists |
| `callbackType=caseExport` on historical | Not in v3 filter enum — use sync **`workspaceCaseExport`** or HTTP export callbacks |

## Next steps

- Full channel tables and payload matrices: [WebSocket Protocol](../../knowledge-base/wss.md)
- Per-operation request bodies: product walkthroughs (update, documents, track, import)
- Outage backfill: [Handling Requests and Callbacks during maintenance](../../knowledge-base/handling-requests-callbacks.md)
