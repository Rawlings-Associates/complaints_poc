---
title: "Error Management"
source: https://dart.unicourt.com/res-deep/assets/deep-v3-api-doc/knowledge-base/error-codes/
retrieved: 2026-10-01
---

# Error Management

When a request cannot be processed, the UniCourt DEEP API returns a structured error. This page describes the shape of that error and how to handle it in code. For the sorted catalog of shared UniCourt error codes, see [General Error Codes](../knowledge-base/general-error-codes.md).

## The error object

Every error response shares the same JSON shape. It is the `Exception` object defined in the API specification:

Error object

```json
{  "object": "Exception",  "code": "UN404",  "message": "RESOURCE_NOT_FOUND",  "details": "caseSearchQueryId resource you were looking for doesn't exist."}
```

| Field | Type | Description | Safe to branch on? |
| --- | --- | --- | --- |
| `object` | string | Always the literal value `Exception`. Lets you detect an error payload regardless of HTTP status. | Yes |
| `code` | string | A UniCourt-assigned code such as `UN404`. Disambiguates errors that share an HTTP status. This is the primary value to switch on. | Yes |
| `message` | string | A stable, machine-readable enum such as `RESOURCE_NOT_FOUND` or `INVALID_INPUT`. | Yes |
| `details` | string | A human-readable description of what went wrong. Intended for logs and display, **not** for parsing. The exact wording may change without notice. | No |

All four fields are always present. Branch your error handling on `code` and `message`. Treat `details` as display text only.

## How to handle errors

UniCourt uses standard HTTP status codes to signal the broad outcome of a request:

| HTTP series | Meaning |
| --- | --- |
| 2xx | The request succeeded and the response contains the expected payload. |
| 4xx | A problem with your request: malformed input, a missing parameter or value, an invalid resource, or a rate limit. These are correctable on your end. |
| 5xx | An error on UniCourt's side while processing an otherwise valid request. |

A robust integration should:

1. Check the HTTP status code first to decide success versus failure.
2. On failure, read `code` to determine the specific error and `message` for a stable category.
3. Log `details` for troubleshooting, but never parse it programmatically.

Some errors are returned with HTTP 200

A subset of source-related and validation errors on callback and long-running status endpoints are delivered **inside a 200 response** rather than a 4xx or 5xx. Because the HTTP status reads as success, these will not be caught by error handling that keys off the status code alone. For these endpoints, always inspect `object` (and `code`) in the response body even when the status is 200. See [Errors returned with HTTP 200](#errors-returned-with-http-200) and the [General Error Codes](../knowledge-base/general-error-codes.md#codes-commonly-returned-with-http-200) list.

## Error code reference

The shared catalog of UniCourt `code` values—sorted by code, with `message` and HTTP status mappings—lives on [General Error Codes](../knowledge-base/general-error-codes.md).

Quick orientation for the codes you will see most often:

| Code | Message | Typical HTTP | What to do |
| --- | --- | --- | --- |
| `UN400` | `INVALID_INPUT` | `400` (also `200` on some callbacks) | Fix the parameter named in `details`. See [Common `UN400` cases](#common-un400-cases). |
| `UN401` | `UNAUTHORIZED` | `401` | Verify the access token (complete, unexpired, correct scope) and re-run Login if needed. |
| `UN203` | `LIMIT_REACHED` | `403` (also `200` on some callbacks) | An account limit was hit. Contact Support to raise it. See [Account limits](#account-limits). |
| `UN404` | `RESOURCE_NOT_FOUND` | `404` (also `200` on some callbacks) | Verify the ID named in `details`. |
| `UN429` | `TOO_MANY_REQUESTS` | `429` | Back off and retry. See [Rate Limits](../getting-started/rate-limits.md). |
| `UN500` | `INTERNAL_SERVER_ERROR` | `500` (also `200` on some callbacks) | Retry after a short wait; contact Support if it persists. |

Court-source and workflow codes such as `UN100`, `UN103`, `UN502`, and `UN505` are listed with full HTTP mappings on [General Error Codes](../knowledge-base/general-error-codes.md).

### Common `UN400` cases

`UN400` is the most frequent error and covers many distinct validation failures. The `details` field tells you which one. Grouped by the API area where they occur:

**Court Data APIs** (`caseTrack`, `caseExport`, PACER-related)

- `Requested caseId is invalid.`
- `Please send the pacerOptions field with pacerUserId.`
- `Please set your PACER credentials in UniCourt Account settings.`
- `Number of documents should not be more than 50.`
- `Invalid caseDocumentId`
- `Cannot place this order because the total price {totalPrice} is more than the maxOrderCost {maxOrderCost} allowed`
- `caseId parameter is mandatory.`
- `unicourtAccountId parameter is mandatory.`
- `callback parameter is mandatory.`

**Document order** (`/workspace/{workspaceId}/caseDocumentOrder`)

- `Invalid request. Please check the pacerUserId.`
- `Invalid request. Please check the pacerClientCode.`
- `Invalid request. Please check the empty key.`
- `You have reached your document order limit. Please contact Support.`

**Legal Analytics APIs**

- `Norm ID is missing`
- `pageNumber is required.`
- `groupBy method should not be specified.`
- `Invalid groupBy condition specified.`
- `Invalid query parameters received.`
- `Invalid caseDocumentId.`
- `Invalid caseTrackId.`
- `Invalid caseUpdateCallbackId.`
- `caseFiledDate is not in the required format.`
- `from date should be earlier than to date.`

**Search APIs** (`caseSearch`, `normAttorneySearch`, `normJudgeSearch`, `normLawFirmSearch`, and similar)

- `pageNumber value passed {pageNumber} is not valid.`
- `order value passed {sortOrder} is not valid.`
- `sort value passed {sortBy} is not valid.`
- `Please verify the query passed.`

**All Enterprise APIs**

- `Invalid request. Please check the empty key.` (a required parameter was sent with an empty value)

### Account limits

| Endpoint | Default limit | Error returned |
| --- | --- | --- |
| `/workspace/{workspaceId}/caseTrack` | 20 concurrent tracked cases | `UN203` / `LIMIT_REACHED` |
| `/workspace/{workspaceId}/caseDocumentDownload/{caseDocumentId}` | 300 downloads per day | `UN203` / `LIMIT_REACHED` |

To raise a limit, contact UniCourt Support.

## Errors returned with HTTP 200

Status code reads as success

The errors below are returned **inside a 200 response**. Error handling that branches only on the HTTP status code will treat these as successful. On callback and long-running status endpoints, always check whether the response body's `object` is `Exception` before treating the payload as a result.

These occur on long-running workflows (for example `caseUpdate`, `caseTrack`, `caseDocumentOrder`, `caseImport`, and entity update/track callbacks), where the request is accepted but the court or bar source ultimately cannot fulfill it.

| Code | Message | Meaning |
| --- | --- | --- |
| `UN100` | `SEALED` | The case or document is sealed by the court. |
| `UN101` | `NO_LONGER_AVAILABLE_IN_BAR` | The normalized attorney is no longer available in the bar source. |
| `UN103` | `CURRENTLY_UNAVAILABLE_IN_COURT` | The case or document is temporarily unavailable on the court site. UniCourt may retry internally; add the case to tracking to be notified when it returns. |
| `UN203` | `LIMIT_REACHED` | An account or product limit was reached during the workflow. |
| `UN400` | `INVALID_INPUT` | A required field is missing or invalid (for example `pacerOptions` with `pacerUserId` when ordering a PACER document). |
| `UN404` | `RESOURCE_NOT_FOUND` | An invalid resource ID was supplied for the workflow. |
| `UN500` | `INTERNAL_SERVER_ERROR` | An unexpected error occurred while fulfilling the workflow. |
| `UN501` | `FEATURE_NOT_SUPPORTED` | The requested operation is not supported for this case or court. |
| `UN502` | `ISSUE_AT_THE_COURT_SOURCE` | The court source is under maintenance or intermittently unresponsive. |
| `UN503` | `NOT_ACCEPTING_REQUESTS` | The integration is not accepting requests for this resource. |
| `UN504` | `TIMEOUT` | The workflow timed out waiting on an upstream source. |
| `UN505` | `BROKEN_INTEGRATION` | Integration with the court source is broken due to a change on the source side. Contact Support. |
| `UN506` | `DELAYED_AT_THE_COURT_SOURCE` | Fulfillment is delayed at the court source. |

For the full sorted catalog (including non-200 HTTP mappings), see [General Error Codes](../knowledge-base/general-error-codes.md).

## WebSocket errors

When a request made over the WebSocket protocol cannot be fulfilled, the API delivers an error as a WebSocket message. WebSocket errors carry no HTTP status code, so the `code` field is the only signal; branch on it directly.

| Code | Message | Endpoints | Meaning |
| --- | --- | --- | --- |
| `UN203` | `LIMIT_REACHED` | `caseUpdate`, `caseDocumentOrder`, `allCallbacks` | You have reached the maximum number of WebSocket connections allowed for your account for this connection type. |
| `UN400` | `INVALID_INPUT` | `caseUpdate`, `caseDocumentOrder` | A request is already in progress, or a parameter (for example `caseId`, `caseDocumentId`, `pacerUserId`, `pacerClientCode`, `fetchIfOlderThanDays`, `additionalPageArray`, `fetchParticipantsIfOlderThanDays`, or `refreshType`) is invalid. Check the value named in the message. |
| `UN400` | `INVALID_INPUT` | `liveCallbacks`, `historicCallbacks` | This endpoint accepts no request parameters. Send only the parameters the endpoint defines. |
| `UN401` | (unexpected server response: 401) | All WebSocket APIs | The access token is missing, invalid, or expired. Verify it, or use the Login API to mint a new one. |
| `UN500` | `INTERNAL_SERVER_ERROR` | All WebSocket APIs | An error on UniCourt's side. Review your request and resend after a short wait. |
