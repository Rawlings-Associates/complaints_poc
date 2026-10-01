---
title: "Getting Documents from Cases"
source: https://dart.unicourt.com/res-deep/assets/deep-v3-api-doc/common-use-cases/get-case-content/get-a-case-document/
retrieved: 2026-10-01
---

# Getting Documents from Cases

Acquire a case document and download the file. The API path depends on **`repository`**, but your integration can treat both as one flow: inspect metadata, understand cost, then either download immediately or place an order and retrieve the file when ready.

**Reference docs:** [Document Orders](../../knowledge-base/document-orders.md) (fields, limits, WebSocket details), [Read a full case](../../common-use-cases/find-and-read-cases/read-a-full-case.md) (find `caseDocumentId` values), [Set up callbacks](../../common-use-cases/platform/set-up-callbacks.md) (WebSocket alternative to polling).

## Before you start

You need:

- A **`caseDocumentId`** from a case document list or docket entry
- A **workspace token** and **`workspaceId`**
- Base URL: **`https://deep-api.unicourt.com`**

## Step 1 — Inspect document metadata

Always start here. Metadata tells you how to acquire the file and what it may cost.

Document metadata

```Shell
curl -X 'GET' \  'https://deep-api.unicourt.com/workspace/{workspaceId}/caseDocument/{caseDocumentId}' \  -H 'accept: application/json' \  -H 'Authorization: Bearer <Your JWT accessToken>'
```

| Field | Why it matters |
| --- | --- |
| **`repository`** | **`UNICOURT`** — UniCourt already has the file (download path). **`COURT_SOURCE`** — place an order first (async path). |
| **`price`** | Quoted cost for this document on your account (may be `0`). |
| **`isPreviewAvailable`** | If `true`, you can request a free preview instead of the full file. |
| **`availabilityStatusAtCourtSource`** | Court-side availability; useful when orders fail or stall. |

v3 change from v2

v2 used **`inLibrary`**. v3 uses **`repository`** to choose download vs order.

## Step 2 — Understand costs and limits

DEEP currently supports **CSL** (CrowdSourced Library) accounts. On CSL, `UNICOURT`-repository documents are typically free to download; `COURT_SOURCE` orders use the order price from **`price`** on metadata / callback. **`reOrder: true`** always charges again.

Separate **daily caps** apply to orders and downloads (HTTP **`403`** / `UN203`). Per-court order limits may surface on the callback as **`FAILURE`**. See [Document Orders — limits](../../knowledge-base/document-orders.md#limits) and [Usage, Limits, and Billable Activity](../../getting-started/usage-limits-billable-activities.md).

Check **`price`** on the metadata response before you commit.

## Step 3 — Acquire the document

### Path A: Download now (`repository: UNICOURT`)

When UniCourt already has the file, one synchronous **GET** returns a time-limited link:

Download full document

```Shell
curl -X 'GET' \  'https://deep-api.unicourt.com/workspace/{workspaceId}/caseDocumentDownload/{caseDocumentId}?isPreviewDocument=false' \  -H 'accept: application/json' \  -H 'Authorization: Bearer <Your JWT accessToken>'
```

Preview only (when **`isPreviewAvailable`** is `true`):

Download preview

```Shell
curl -X 'GET' \  'https://deep-api.unicourt.com/workspace/{workspaceId}/caseDocumentDownload/{caseDocumentId}?isPreviewDocument=true' \  -H 'accept: application/json' \  -H 'Authorization: Bearer <Your JWT accessToken>'
```

Spec: [**Case Document Download**](#).

Skip to [Step 4](#step-4--download-the-file) when **`fileUrl`** is present.

### Path B: Order first (`repository: COURT_SOURCE`)

When the file is not yet in UniCourt's repository, submit an asynchronous order with **PUT**:

Place document order

```Shell
curl -X 'PUT' \  'https://deep-api.unicourt.com/workspace/{workspaceId}/caseDocumentOrder' \  -H 'accept: application/json' \  -H 'Authorization: Bearer <Your JWT accessToken>' \  -H 'Content-Type: application/json' \  -d '{  "caseDocumentId": "CDOCboda2c3beb0491",  "isPreviewOnly": false}'
```

Spec: [**Case Document Order**](#).

The response is a **`CaseDocumentOrderCallback`** with **`status: IN_PROGRESS`** and a **`caseDocumentOrderCallbackId`**.

Poll until **`status`** is **`COMPLETE`** (or handle **`DELAYED`** / **`FAILURE`**):

Poll order callback

```Shell
curl -X 'GET' \  'https://deep-api.unicourt.com/workspace/{workspaceId}/caseDocumentOrder/callbacks/{caseDocumentOrderCallbackId}' \  -H 'accept: application/json' \  -H 'Authorization: Bearer <Your JWT accessToken>'
```

Or use WebSocket delivery instead of polling — see [Set up callbacks](../../common-use-cases/platform/set-up-callbacks.md) and [Document Orders — WebSocket](../../knowledge-base/document-orders.md#real-time-delivery-via-websocket).

When the order completes, the callback includes **`file.fileUrl`** and **`caseDocumentDownloadAPI`** for future link refresh.

Completed order (excerpt)

```json
{  "object": "CaseDocumentOrderCallback",  "status": "COMPLETE",  "file": {    "object": "ExportFile",    "fileUrl": "https://casedocs.unicourt.com/...",    "expiryDate": "2023-02-28T08:12:28+00:00"  },  "caseDocumentDownloadAPI": "/workspace/{workspaceId}/caseDocumentDownload/CDOCcrcfa6f5382361"}
```

**PACER documents:** include **`pacerOptions`** on the order request. Set credentials first — see [PACER API](../../knowledge-base/pacer-api.md).

Optional order fields (**`priorityLevel`**, **`notifyOnDelay`**, **`reOrder`**) are documented in [Document Orders](../../knowledge-base/document-orders.md#placing-a-document-order).

## Step 4 — Download the file

Whether you used Path A or Path B, retrieve bytes from **`fileUrl`**:

Save the file

```Shell
curl -L -o document.pdf '<fileUrl from response>'
```

| Source | Where `fileUrl` comes from |
| --- | --- |
| Path A (download) | **`DocumentDownload.fileUrl`** |
| Path B (order) | **`CaseDocumentOrderCallback.file.fileUrl`** when **`status: COMPLETE`** |

Links expire at **`expiryDate`**. Call **`caseDocumentDownloadAPI`** again to mint a fresh link — you do not need to re-order.

If Path A returns **`fileUrl: null`** with an **`exception`**, the document may need ordering instead (confirm **`repository`** on metadata). If the order path failed, inspect **`status`**, **`statusDetails`**, and **`exception`** on the callback.

## Decision summary

```mermaid
flowchart TD  A[GET caseDocument metadata] --> B{repository?}  B -->|UNICOURT| C[GET caseDocumentDownload]  B -->|COURT_SOURCE| D[PUT caseDocumentOrder]  D --> E[Poll callback or WebSocket]  E --> F{status COMPLETE?}  F -->|yes| G[Use file.fileUrl]  C --> H{fileUrl present?}  H -->|yes| G  H -->|no| D  G --> I[curl fileUrl to disk]
```

## v3 path reminder

| v2 | v3 |
| --- | --- |
| `GET /caseDocument/{caseDocumentId}` | `GET /workspace/{workspaceId}/caseDocument/{caseDocumentId}` |
| `GET /caseDocumentDownload/{caseDocumentId}` | `GET /workspace/{workspaceId}/caseDocumentDownload/{caseDocumentId}` |
| `PUT /caseDocumentOrder` | `PUT /workspace/{workspaceId}/caseDocumentOrder` |
| `inLibrary: true` | `repository: "UNICOURT"` |

## Related

Need the full case as a downloadable archive instead of a single filing? See [Export a case](../../common-use-cases/get-case-content/export-a-case.md).
