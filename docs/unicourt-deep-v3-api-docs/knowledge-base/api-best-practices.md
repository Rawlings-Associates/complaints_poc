---
title: "API Best Practices"
source: https://dart.unicourt.com/res-deep/assets/deep-v3-api-doc/knowledge-base/api-best-practices/
retrieved: 2026-10-01
---

# API Best Practices

Practices below help you use DEEP efficiently and avoid unnecessary cost. For authentication details see [Authentication](../getting-started/authentication.md). For what counts as billable activity see [Usage, Limits, and Billable Activity](../getting-started/usage-limits-billable-activities.md).

## Save and scope your tokens

DEEP issues JWT access tokens in two scopes:

| Scope | Generate with | Use for |
| --- | --- | --- |
| **Account** | `POST /generateNewToken` | Workspace management, account administration |
| **Workspace** | `POST /generateNewWorkspaceToken` | Case search, view, track, update, import, document orders, PACER |

Store tokens securely after generation. The token string is returned only once from [**POST /generateNewToken**](#) or [**POST /generateNewWorkspaceToken**](#). Listing endpoints such as **PUT /listAllTokenIds** and **PUT /listAllWorkspaceTokenIds** return token IDs only, not the secret string.

Use environment variables for **Client ID** and **Client Secret** in application code. Rotate the client secret from your API Security page if you suspect exposure.

For day-to-day integrations, prefer a **workspace token** scoped to the workspace you operate in. Pass **`Authorization: Bearer <token>`** on every REST call and as **`accessToken`** on WebSocket connections.

## Workspace-scoped requests

Nearly all data endpoints live under **`/workspace/{workspaceId}/…`** on **`deep-api.unicourt.com`**. Keep `workspaceId` in configuration alongside your workspace token.

When generating an account token, the v3 **`generateNewToken`** response may include a default **`deepWorkspace`** object with the workspace ID and name—useful for bootstrapping, but workspace tokens remain required for data APIs.

## HTTP billing behavior

Billing for HTTP calls depends on the response status:

| Status | Typically billed? |
| --- | --- |
| **429** Too Many Requests | No (rate limit; see [Rate Limits](../getting-started/rate-limits.md)) |
| **5xx** server errors | No |
| Other **4xx** (including **403**, **404**) | Yes |
| **2xx** success | Yes (when the operation is billable—see usage article) |

Treat unexpected **4xx** responses as billable and fix the request promptly to avoid wasting quota.

Product-level rules (what constitutes a successful billable run vs a preview) are documented in [Usage, Limits, and Billable Activity](../getting-started/usage-limits-billable-activities.md).

## WebSocket billing

DEEP WebSocket workflows on **`deep-callbacks.unicourt.com`** generally bill as follows:

| Step | Billed? |
| --- | --- |
| Opening the WebSocket connection | No |
| Sending a sync operation request (for example on **`workspaceCaseUpdate`**) | Yes, when the operation is billable |
| Receiving callback messages on **`liveCallbacks`** / **`historicalCallbacks`** | No |

The same pattern applies to live and historical async streams: you are not charged for listening on the socket; billable work is tied to the underlying operation.

Sync channels include **`workspaceCaseUpdate`**, **`workspaceCaseDocumentOrder`**, **`workspaceCaseExport`**, **`workspaceCaseImport`**, and **`workspaceNormAttorneyUpdate`**. See [WebSocket Protocol](../knowledge-base/wss.md).

v2 WebSocket note

v2 used **`type=caseUpdate`** and **`type=caseDocumentOrder`** on **`callbacks.unicourt.com`**. v3 uses workspace-prefixed types and **`deep-callbacks.unicourt.com`**.

## Operational tips

- **Poll vs WebSocket:** Use sync WebSocket or HTTP callbacks for one-off operations; use **`liveCallbacks`** when monitoring many cases. Backfill gaps with **`historicalCallbacks`** (see [WebSocket Protocol](../knowledge-base/wss.md#websocket-best-practices)).
- **PACER cost control:** Search UniCourt first; use **`fetchParticipantsIfOlderThanDays`** on federal updates and tracks when you only need docket changes. See [PACER API](../knowledge-base/pacer-api.md).
- **Usage monitoring:** Query **`GET /monthlyUsage/{month}`**, **`GET /dailyUsage/{date}`**, and workspace-scoped usage endpoints instead of inferring consumption from call logs alone.

## Migration Notes for v2 Integrators

| v2 practice | v3 practice |
| --- | --- |
| Single account token for all APIs | **Workspace tokens** for data APIs; account token for workspace admin |
| `https://enterpriseapi.unicourt.com/…` | `https://deep-api.unicourt.com/workspace/{workspaceId}/…` |
| `wss://callbacks.unicourt.com?type=caseUpdate` | `wss://deep-callbacks.unicourt.com?type=workspaceCaseUpdate&workspaceId={id}` |
| `GET /billingCycles`, `GET /billingCycleUsage/{billingCycle}` | Removed; use **`GET /monthlyUsage/{month}`** and workspace usage endpoints |
| `listAllTokenIds` → `AccessTokenIdArray` | **`accessTokenIdArray`** (casing change) |
| Account token response | May include **`deepWorkspace`** with default workspace metadata |

| v2 Field / Endpoint | v3 Field / Endpoint | Notes |
| --- | --- | --- |
| `POST /generateNewToken` | `POST /generateNewToken` | Same path on `deep-api.unicourt.com`; response adds `deepWorkspace` |
| *(none)* | `POST /generateNewWorkspaceToken` | New; preferred for data API calls |
| Unscoped `/caseSearch`, `/caseUpdate`, … | `/workspace/{workspaceId}/…` | All major data endpoints workspace-scoped |
