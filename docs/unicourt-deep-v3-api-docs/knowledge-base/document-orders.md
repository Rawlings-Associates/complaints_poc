---
title: "Document Orders"
source: https://dart.unicourt.com/res-deep/assets/deep-v3-api-doc/knowledge-base/document-orders/
retrieved: 2026-10-01
---

# Document Orders

Every case document lives in one of two places, indicated by its `repository` field: the **court's** own site (`COURT_SOURCE`), or **UniCourt's** repository (`UNICOURT`). This field determines which endpoint you use:

- **`repository: COURT_SOURCE`** → use the [Case Document Order](#placing-a-document-order) endpoint. UniCourt retrieves the document from the court on your behalf. This is asynchronous, since it's a real retrieval operation that can take anywhere from a few minutes to longer depending on the court.
- **`repository: UNICOURT`** → use the [Case Document Download](#downloading-a-document) endpoint. UniCourt already has a copy. This is synchronous: you get a link back immediately.

DEEP currently supports **CrowdSourced Library (CSL)** accounts: every `UNICOURT`-repository document is free to download.

Some court documents also offer a free preview, typically the first few pages. Use `isPreviewOnly` on an order, or `isPreviewDocument` on a download, to request just the preview.

This page covers both acquisition paths: the asynchronous **Case Document Order** endpoint, and the synchronous **Case Document Download** endpoint.

See [Getting documents from cases](../common-use-cases/get-case-content/get-a-case-document.md) for a full walkthrough. Document and callback IDs use fixed prefixes (`CDOC`, `CBDO`)—see [Object ID Prefixes](../knowledge-base/object-id-prefixes.md).

## Retrieving Document Metadata

Before ordering or downloading, inspect a document with [**GET /workspace/{workspaceId}/caseDocument/{caseDocumentId}**](#). The response includes `repository` (`COURT_SOURCE` or `UNICOURT`), `price`, `isPreviewAvailable`, and `availabilityStatusAtCourtSource`, which tell you whether to order, download, or wait.

In v3, use `repository` to decide the acquisition path. The v2 `inLibrary` boolean is removed.

## Placing a Document Order

Order a document asynchronously through the [**/workspace/{workspaceId}/caseDocumentOrder**](#) endpoint. The flow has three steps:

1. Send a request containing the `caseDocumentId` value of the document you want. Please note that document orders cannot be cancelled once they are placed.
2. Receive an acknowledgment containing a `caseDocumentOrderCallbackId`, which identifies your request.
3. Retrieve the completed order, either by polling the callback endpoint or by listening for a WebSocket callback.

### Request fields

| Field | Required | Description |
| --- | --- | --- |
| `caseDocumentId` | Yes | The document you want to order. |
| `isPreviewOnly` | Yes | If `true`, orders only the free preview (where available) instead of the full document. |
| `priorityLevel` | No | `level1` (Critical, 5 minute timeout), `level2` (High, 30 minutes), or `level5` (Normal, 24 hours, default). Higher priority orders are processed first. |
| `notifyOnDelay` | No | If `true`, you'll be notified if the order moves into a `DELAYED` state. Defaults to `false`. |
| `reOrder` | No | If `true`, forces UniCourt to re-fetch the document from the court even if it's already in your library. This always charges your account again, even if the original acquisition was free. Defaults to `false`. |
| `pacerOptions` | Conditional | Required for PACER documents. See [PACER Documents](#pacer-documents) below. |

Submit the request with **PUT**:

Case Document Order request

```Shell
curl -X 'PUT' \  'https://deep-api.unicourt.com/workspace/{workspaceId}/caseDocumentOrder' \  -H 'accept: application/json' \  -H 'Authorization: Bearer <Your JWT accessToken>' \  -H 'Content-Type: application/json' \  -d '{  "caseDocumentId": "CDOCboda2c3beb0491",  "isPreviewOnly": false}'
```

Poll a single callback with [**GET /workspace/{workspaceId}/caseDocumentOrder/callbacks/{caseDocumentOrderCallbackId}**](#).

### Response: the order callback

The immediate response is a `CaseDocumentOrderCallback` object, echoing your request fields alongside processing metadata:

- `caseDocumentOrderCallbackId`, the ID you'll use to retrieve the result
- `status`, one of `IN_PROGRESS`, `DELAYED`, `COMPLETE`, `FAILURE`, or `MANUAL`
- `statusDetails`, populated once there's something to report: `issueSource` (`INTERNAL`, `COURT`, or `CLIENT`) and `issueType` (`INTERMITTENT`, `MAINTENANCE`, `REPRODUCIBLE`, or `VOR`), so you know not just that something went wrong but where and why
- `caseDocumentOrderCallbackAPI`, a link to poll for the result
- `caseDocumentDownloadAPI`, a link you can use once the document is ready
- `caseDocument`, populated with the full document object once the order completes; `null` until then
- `file`, populated with a download link once the order completes; `null` until then

Order acknowledgment

```json
{  "object": "CaseDocumentOrderCallback",  "workspaceId": "proj123",  "caseDocumentId": "CDOCdl27f64f1df850",  "caseDocumentOrderCallbackId": "CBDOim76295e4280R3",  "isPreviewOnly": false,  "priorityLevel": "level5",  "notifyOnDelay": false,  "reOrder": null,  "pacerOptions": null,  "currentTime": "2023-03-13T09:46:15+00:00",  "startDate": "2023-03-13T09:45:10+00:00",  "status": "IN_PROGRESS",  "statusDetails": null,  "exception": null,  "callbackGeneratedDate": null,  "file": null,  "caseDocumentOrderCallbackAPI": "/workspace/{workspaceId}/caseDocumentOrder/callbacks/CBDOim76295e4280R3",  "caseDocumentDownloadAPI": "/workspace/{workspaceId}/caseDocumentDownload/CDOCdl27f64f1df850",  "caseDocument": null}
```

Once the order completes, retrieve it from `caseDocumentOrderCallbackAPI` (or wait for the WebSocket callback, see below):

Completed order

```json
{  "object": "CaseDocumentOrderCallback",  "workspaceId": "proj123",  "caseDocumentId": "CDOCcrcfa6f5382361",  "caseDocumentOrderCallbackId": "CBDOp2o7L63f47ce15",  "isPreviewOnly": false,  "priorityLevel": "level5",  "notifyOnDelay": false,  "reOrder": false,  "pacerOptions": null,  "currentTime": "2023-02-21T08:13:45+00:00",  "startDate": "2023-02-21T08:08:25+00:00",  "status": "COMPLETE",  "statusDetails": null,  "exception": null,  "callbackGeneratedDate": "2023-02-21T08:12:28+00:00",  "file": {    "object": "ExportFile",    "name": "CDOCag3e5eba43b870",    "expiryDate": "2023-02-28T08:12:28+00:00",    "fileUrl": "https://casedocs.unicourt.com/ca/sm/CDOCag3e5eba43b870_1677603474.pdf?Expires=...&Key-Pair-Id=...&Signature=..."  },  "caseDocumentOrderCallbackAPI": "/workspace/{workspaceId}/caseDocumentOrder/callbacks/CBDOp2o7L63f47ce15",  "caseDocumentDownloadAPI": "/workspace/{workspaceId}/caseDocumentDownload/CDOCcrcfa6f5382361",  "caseDocument": {    "object": "CaseDocument",    "caseDocumentId": "CDOCag3e5eba43b870",    "name": "Reply - Reply",    "description": "7/1/2022: Reply - Reply",    "documentFiledDate": "2022-07-01T00:00:00+00:00",    "tags": {      "object": "Tags",      "motionTypeIdArray": [],      "motionOutcomeIdArray": [],      "caseEventIdArray": [],      "proceduralActivityIdArray": [],      "caseDispositionIdArray": []    },    "parentDocumentId": null,    "childDocumentIdArray": [],    "pages": 14,    "isPreviewAvailable": false,    "previewDocument": null,    "price": 10.75,    "repository": "COURT_SOURCE",    "lastAddedDateToUniCourtRepository": "2022-07-10T10:10:24+00:00",    "availabilityStatusAtCourtSource": "NO_KNOWN_ISSUE",  }}
```

`file.fileUrl` is the raw link to the document. It expires at `file.expiryDate`; after that, use `caseDocumentDownloadAPI` to get a fresh link rather than re-ordering.

Note

`reOrder: true` always charges your account, even for a document you already have. It exists specifically for cases where you need a fresh copy from the court rather than what's on file with UniCourt.

In the acknowledgment response, `reOrder` may be `null` when omitted from the request; in completed callbacks it is a boolean.

### When an order is delayed

If the court source is temporarily unavailable, an order can move to `DELAYED` before eventually resolving. `statusDetails` tells you why, and `nextRetry` tells you when UniCourt will try again:

Delayed order — court under scheduled maintenance

```json
{  "object": "CaseDocumentOrderCallback",  "workspaceId": "proj123",  "caseDocumentId": "CDOCcca48451a0a47b",  "caseDocumentOrderCallbackId": "CBDO63f481489xjSE0",  "isPreviewOnly": false,  "priorityLevel": "level5",  "notifyOnDelay": true,  "reOrder": false,  "pacerOptions": null,  "status": "DELAYED",  "statusDetails": {    "object": "StatusDetails",    "issueSource": "COURT",    "issueType": "MAINTENANCE",    "statusAsOn": "2025-06-24T08:15:00+00:00",    "nextRetry": "2025-06-24T08:25:00+00:00",    "details": "Request is delayed as the court source is either under Scheduled Maintenance or Unplanned Maintenance."  },  "exception": null,  "startDate": "2023-02-21T08:25:00+00:00",  "currentTime": "2023-02-21T08:32:45+00:00",  "callbackGeneratedDate": "2025-06-24T08:31:04+00:00",  "file": null,  "caseDocumentOrderCallbackAPI": "/workspace/{workspaceId}/caseDocumentOrder/callbacks/CBDO63f481489xjSE0",  "caseDocumentDownloadAPI": "/workspace/{workspaceId}/caseDocumentDownload/CDOCcca48451a0a47b",  "caseDocument": null}
```

## Downloading a Document

If a document's `repository` is already `UNICOURT`, skip the order flow entirely and call the [**/workspace/{workspaceId}/caseDocumentDownload/{caseDocumentId}**](#) endpoint directly. It's a synchronous GET; there's no callback to poll.

Case Document Download Request

```Shell
curl -X 'GET' \  'https://deep-api.unicourt.com/workspace/{workspaceId}/caseDocumentDownload/CDOCaqe42a86394f63?isPreviewDocument=false' \  -H 'accept: application/json' \  -H 'Authorization: Bearer <Your JWT accessToken>'
```

Case Document Download Response

```json
{  "object": "DocumentDownload",  "caseDocumentId": "CDOCaqe42a86394f63",  "expiryDate": "2023-02-28T16:57:54+00:00",  "fileUrl": "https://casedocs.unicourt.com/ca/sm/CDOCaqe42a86394f63_1648691795.pdf?Expires=1677603474&Key-Pair-Id=K1K4HTY1FAWDYU&Signature=TtwJcIUIwc~Sr-egZEnDjO8HbBU3EKDQ~0AZoesSRucPSTf-IkxFtKXxK-~iwdzIFVkeppleK-VA75p89bWDZvuYLxjXJkXFhdIlh9PfaRzCklU7nggIGyRTSzX7jaka2Xndl2s01P3~irtjpDdIJyF8DZZU1kwovgc3306N1AX~k29xFDh-YG2GHXY8uwU6kIo7GmeDRsnkcmjhhDBTT0EshwqFsRVbO~B8LHvseTznRaVa7a5JXmCamKqRQJAfghMCYrryaUw5hky3oHNDQFik9pDJMbgGf22Wg90sjaBgpP3eWvX~bn8qkWdsu2Uxub7j7yrQhJ8ntXNaH6Ugxg__",  "caseDocumentDownloadAPI": "/workspace/{workspaceId}/caseDocumentDownload/CDOCaqe42a86394f63",  "exception": null}
```

If the document isn't actually available to download this way, `fileUrl` and `caseDocumentDownloadAPI` come back `null` and `exception` is populated instead, for example:

Document not currently available

```json
{  "object": "DocumentDownload",  "caseDocumentId": "CDOCaqe42a86394f63",  "expiryDate": null,  "fileUrl": null,  "caseDocumentDownloadAPI": null,  "exception": {    "object": "Exception",    "code": "UN103",    "message": "CURRENTLY_UNAVAILABLE_IN_COURT",    "details": "The Document is currently unavailable in the Court."  }}
```

Use the `isPreviewDocument` query parameter the same way you'd use `isPreviewOnly` on an order, to fetch just the free preview instead of the full document.

## PACER Documents

Ordering a PACER document works the same way as any other order, with two differences: you must have PACER credentials on file, and you pass them along with the order.

note

Set your PACER credentials once via [**PUT /pacerCredential**](#) before ordering PACER documents.

Include `pacerOptions` in your order request:

pacerOptions on a PACER order

```json
{  "caseDocumentId": "CDOCdgd2e087b53a6b",  "isPreviewOnly": false,  "notifyOnDelay": false,  "pacerOptions": {    "pacerUserId": "<Your pacerUserId>",    "pacerClientCode": "<Your-pacerClientCode>"  }}
```

`pacerUserId` is always required for a PACER order. `pacerClientCode` is required only if your PACER account has "Require Client Code?" enabled under PACER's billing preferences. Everything else about the order and callback flow, including `priorityLevel`, `reOrder`, and the response shape, works exactly as described above.

## Limits

Two kinds of limits can stop an order: a per-court-source volume cap, and account-level cost controls. They surface differently.

### Per-court-source order limit

Individual courts can only sustain so much order volume, and UniCourt enforces a cap per court source. Unlike cost rejections below, this one isn't rejected upfront: your order is accepted, and the limit shows up later on the callback itself, with `status: FAILURE`:

Per-court-source order limit reached

```json
{  "object": "CaseDocumentOrderCallback",  "workspaceId": "proj123",  "caseDocumentId": "CDOCcr01adcbc19558",  "caseDocumentOrderCallbackId": "CBDOim76295e4280R5",  "isPreviewOnly": false,  "priorityLevel": "level5",  "notifyOnDelay": false,  "reOrder": false,  "pacerOptions": null,  "currentTime": "2023-02-21T08:33:45+00:00",  "startDate": "2023-02-21T08:25:00+00:00",  "status": "FAILURE",  "statusDetails": null,  "exception": {    "object": "Exception",    "code": "UN203",    "message": "LIMIT_REACHED",    "details": "You have reached the daily limit of caseDocumentOrder for court source CTSS2282c2e7475a43."  },  "callbackGeneratedDate": "2023-02-21T14:47:05+00:00",  "caseDocumentOrderCallbackAPI": "/workspace/{workspaceId}/caseDocumentOrder/callbacks/CBDOim76295e4280R5",  "file": null,  "caseDocumentDownloadAPI": "/workspace/{workspaceId}/caseDocumentDownload/CDOCcr01adcbc19558",  "caseDocument": null}
```

Since a court-source limit failure only appears after the order is accepted, check `status` and `exception` on the callback (or the WebSocket message) rather than assuming acceptance means success.

### Order cost limits

Accounts can be configured with two separate cost controls. Both reject the request before an order is accepted.

**Maximum cost per order (`maxOrderCost`).** If this document's price exceeds the per-order ceiling configured for your account, the request fails with HTTP `400`:

Order exceeds maxOrderCost

```json
{  "object": "Exception",  "code": "UN400",  "message": "INVALID_INPUT",  "details": "Cannot place this order because the total price 7.25 is more than the maxOrderCost 0 allowed"}
```

**Invoice / unbilled-amount block.** Separately, some accounts are blocked from placing further paid orders when outstanding charges hit an account threshold or an invoice is past due. That returns HTTP `402`:

Payment required

```json
{  "object": "Exception",  "code": "UN402",  "message": "PAYMENT_REQUIRED",  "details": "You have been blocked due to invoice failure. Please contact support."}
```

A `maxOrderCost` rejection means this specific document's price is too high for a single order. `PAYMENT_REQUIRED` means ordering is blocked at the account level until billing is resolved—contact Support.

## Real-Time Delivery via WebSocket

Instead of polling the callback endpoint, you can receive order results over a WebSocket connection as soon as they're ready. The request and response payloads are the same shape as the HTTP flow above; the only difference is delivery.

Connect with your access token and `type=workspaceCaseDocumentOrder` in the query string, along with your `workspaceId`:

WebSocket connection

```Shell
wss://deep-callbacks.unicourt.com?accessToken=<Your_JWT_accessToken>&type=workspaceCaseDocumentOrder&workspaceId={workspaceId}
```

Once connected, send the same request body you'd send to the HTTP order endpoint:

WebSocket order request

```json
{  "caseDocumentId": "CDOCcre989d654fa05",  "isPreviewOnly": false,  "notifyOnDelay": false}
```

You'll receive the acknowledgment and, later, the completed callback as separate messages on the same connection, in the same shape shown in the HTTP examples above.

tip

Only one `caseDocumentId` can be submitted per message. A connection stays open for a maximum of 2 hours.

## Order Status and Delays

An order moves through up to four states: `IN_PROGRESS`, `DELAYED`, `COMPLETE`, or `FAILURE`. A `MANUAL` status can also appear, when UniCourt falls back to manual retrieval for a document automation can't reach on its own.

An order starts `IN_PROGRESS`. If it isn't resolved within the timeout for its `priorityLevel` (5 minutes for `level1`, 30 minutes for `level2`, 24 hours for `level5`), it moves to `DELAYED`. From there it can still resolve to `COMPLETE` or `FAILURE`, which can take up to 72 hours from when it entered `DELAYED`.

When an order is delayed or fails, `statusDetails` tells you more about why: whether the issue originated internally, at the court, or with your request (`issueSource`), and whether it's a one-off, scheduled maintenance, a reproducible problem, or a document that requires the court's manual sign-off (`issueType`).

Note

In v2 documentation, `IN_PROGRESS` was described as moving to `DELAYED` after a fixed four-hour window. In v3, the timeout before `DELAYED` depends on `priorityLevel` (5 minutes, 30 minutes, or 24 hours).

## Listing Recent Orders

To review multiple orders at once rather than looking them up one at a time, use [**GET /workspace/{workspaceId}/caseDocumentOrder/callbacks**](#). You can filter by `status`, by `callbackGeneratedDate` or `startDate` (both limited to the last 30 days), and page through results with `pageNumber`.

## Errors

Order and download requests can fail outright (an HTTP error status) or complete with `status: FAILURE` and an `exception` describing what went wrong. See [General Error Codes](../knowledge-base/general-error-codes.md) for the shared code catalog and [Error Management](../knowledge-base/error-codes.md) for how to handle `Exception` responses. The [Limits](#limits) section above covers per-court-source volume caps and the cost-related `maxOrderCost` / `PAYMENT_REQUIRED` responses.

## Migration Notes for v2 Integrators

If your integration currently reads `inLibrary`, `downloadAPI`, `documentId`, or nested `CaseDocument` fields from v2 order/download responses, these have been replaced in v3. See the field mapping table below.

### `orderCaseDocument` / `CaseDocumentOrderCallback` — request fields added in v3

- `notifyOnDelay`
- `priorityLevel`
- `reOrder`

### `orderCaseDocument` / `getCaseDocumentOrderCallbackById` — response fields added in v3

Applies to both the immediate `orderCaseDocument` response and `getCaseDocumentOrderCallbackById`.

- `workspaceId`
- `currentTime`
- `startDate`
- `isPreviewOnly`
- `notifyOnDelay`
- `priorityLevel`
- `reOrder`
- `pacerOptions`
- `pacerOptions.object`
- `pacerOptions.pacerClientCode`
- `pacerOptions.pacerUserId`
- `caseDocumentDownloadAPI`
- `statusDetails`
- `statusDetails.object`
- `statusDetails.issueSource`
- `statusDetails.issueType`
- `statusDetails.statusAsOn`
- `statusDetails.nextRetry`
- `statusDetails.details`
- `caseDocument.repository`
- `caseDocument.availabilityStatusAtCourtSource`
- `caseDocument.lastAddedDateToUniCourtRepository`
- `caseDocument.tags`
- `caseDocument.tags.object`
- `caseDocument.tags.motionTypeIdArray`
- `caseDocument.tags.motionOutcomeIdArray`
- `caseDocument.tags.caseEventIdArray`
- `caseDocument.tags.proceduralActivityIdArray`
- `caseDocument.tags.caseDispositionIdArray`
- `caseDocument.previewDocument.repository`
- `caseDocument.previewDocument.lastAddedDateToUniCourtRepository`

### `orderCaseDocument` / `getCaseDocumentOrderCallbackById` — `caseDocument` fields removed in v3

- `caseDocument.addedToLibraryDate`
- `caseDocument.downloadAPI`
- `caseDocument.estimatedOrderDuration`
- `caseDocument.inLibrary`
- `caseDocument.sortOrder`
- `caseDocument.sourceDataStatus`
- `caseDocument.previewDocument.addedToLibraryDate`
- `caseDocument.previewDocument.downloadAPI`
- `caseDocument.previewDocument.inLibrary`

### `getDocumentById` — response fields added in v3

- `repository`
- `availabilityStatusAtCourtSource`
- `lastAddedDateToUniCourtRepository`
- `tags`
- `tags.object`
- `tags.motionTypeIdArray`
- `tags.motionOutcomeIdArray`
- `tags.caseEventIdArray`
- `tags.proceduralActivityIdArray`
- `tags.caseDispositionIdArray`
- `previewDocument.repository`
- `previewDocument.lastAddedDateToUniCourtRepository`

### `getDocumentById` — response fields removed in v3

- `addedToLibraryDate`
- `downloadAPI`
- `estimatedOrderDuration`
- `inLibrary`
- `sortOrder`
- `sourceDataStatus`
- `previewDocument.addedToLibraryDate`
- `previewDocument.downloadAPI`
- `previewDocument.inLibrary`

| v2 Field / Endpoint | v3 Field / Endpoint | Notes |
| --- | --- | --- |
| `PUT /caseDocumentOrder` | `PUT /workspace/{workspaceId}/caseDocumentOrder` | Workspace-scoped on `deep-api.unicourt.com` |
| `GET /caseDocumentOrder/callbacks` | `GET /workspace/{workspaceId}/caseDocumentOrder/callbacks` | Workspace-scoped |
| `GET /caseDocumentOrder/callbacks/{caseDocumentOrderCallbackId}` | `GET /workspace/{workspaceId}/caseDocumentOrder/callbacks/{caseDocumentOrderCallbackId}` | Workspace-scoped |
| `GET /caseDocumentDownload/{caseDocumentId}` | `GET /workspace/{workspaceId}/caseDocumentDownload/{caseDocumentId}` | Workspace-scoped |
| `GET /caseDocument/{caseDocumentId}` | `GET /workspace/{workspaceId}/caseDocument/{caseDocumentId}` | Workspace-scoped |
| `documentId` (request) | `caseDocumentId` | Renamed in v3 |
| `inLibrary` (`CaseDocument`) | `repository` | Removed; use `COURT_SOURCE` vs `UNICOURT` to choose order vs download |
| `downloadAPI` (`CaseDocument`) | `caseDocumentDownloadAPI` (`CaseDocumentOrderCallback`) | Moved to callback object; not on nested `caseDocument` |
| `addedToLibraryDate` | *(removed)* | No v3 equivalent on `CaseDocument` |
| `estimatedOrderDuration` | *(removed)* | No v3 equivalent on `CaseDocument` |
| `sortOrder` | *(removed)* | No v3 equivalent on `CaseDocument` |
| `sourceDataStatus` | *(removed)* | Replaced by `availabilityStatusAtCourtSource` |
| *(none)* | `repository` | New on `CaseDocument`; drives order vs download path |
| *(none)* | `availabilityStatusAtCourtSource` | New on `CaseDocument` |
| *(none)* | `lastAddedDateToUniCourtRepository` | New on `CaseDocument` (replaces earlier library/fetch-date fields) |
| *(none)* | `tags` | New object on `CaseDocument` (see subfields below) |
| *(none)* | `tags.motionTypeIdArray` | New |
| *(none)* | `tags.motionOutcomeIdArray` | New |
| *(none)* | `tags.caseEventIdArray` | New |
| *(none)* | `tags.proceduralActivityIdArray` | New |
| *(none)* | `tags.caseDispositionIdArray` | New |
| `previewDocument.inLibrary` | `previewDocument.repository` | Type change: boolean removed; repository string added |
| `previewDocument.downloadAPI` | *(removed)* | Use top-level `caseDocumentDownloadAPI` on callback |
| `previewDocument.addedToLibraryDate` | `previewDocument.lastAddedDateToUniCourtRepository` | Renamed/replaced |
| *(none)* | `notifyOnDelay` | New request/response field on order |
| *(none)* | `priorityLevel` | New request/response field on order |
| *(none)* | `reOrder` | New request/response field on order; nullable in acknowledgment |
| *(none)* | `currentTime` | New on `CaseDocumentOrderCallback` |
| *(none)* | `startDate` | New on `CaseDocumentOrderCallback` |
| *(none)* | `workspaceId` | New on `CaseDocumentOrderCallback` |
| *(none)* | `statusDetails` | New on `CaseDocumentOrderCallback` |
| *(none)* | `statusDetails.issueSource` | New |
| *(none)* | `statusDetails.issueType` | New |
| *(none)* | `statusDetails.statusAsOn` | New |
| *(none)* | `statusDetails.nextRetry` | New; nullable |
| *(none)* | `statusDetails.details` | New |
| `wss://callbacks.unicourt.com?...&type=caseDocumentOrder` | `wss://deep-callbacks.unicourt.com?...&type=workspaceCaseDocumentOrder&workspaceId={workspaceId}` | Host, type, and workspace query param changed |
