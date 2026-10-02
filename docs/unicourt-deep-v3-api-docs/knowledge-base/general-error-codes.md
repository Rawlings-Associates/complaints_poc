---
title: "General Error Codes"
source: https://dart.unicourt.com/res-deep/assets/deep-v3-api-doc/knowledge-base/general-error-codes/
retrieved: 2026-10-01
---

# General Error Codes

This page lists the UniCourt error codes that apply across DEEP APIs. Use it as the sorted reference when you need to map a `code` from an `Exception` response. Endpoint-specific examples stay in each API’s documentation; this page covers the shared catalog.

For the Exception object shape and how to handle errors in code, see [Error Management](../knowledge-base/error-codes.md). For HTTP status semantics, see the [Glossary of HTTP Response Codes](../knowledge-base/glossary-of-HTTP-response-codes.md).

Same code, different HTTP status

A UniCourt `code` can appear under more than one HTTP status. For example, `UN100` / `SEALED` may be returned as HTTP `451` or inside an HTTP `200` callback body. Always read `code` and the HTTP status together. Branch on `code` (and `message`); treat `details` as display text only.

## Error codes

Sorted by UniCourt `code`.

| Code | Message | HTTP status | Meaning |
| --- | --- | --- | --- |
| `UN100` | `SEALED` | `200`, `451` | The case, document, or related resource is sealed by the court and cannot be returned. |
| `UN101` | `NO_LONGER_AVAILABLE_IN_BAR` | `200` | The normalized attorney is no longer available in the bar source used for updates or tracking. |
| `UN103` | `CURRENTLY_UNAVAILABLE_IN_COURT` | `200` | The case or document is temporarily unavailable at the court source. UniCourt may continue retrying internally; add the case to tracking to be notified when it returns. |
| `UN203` | `LIMIT_REACHED` | `200`, `403` | An account or product limit was reached (for example concurrent tracks, daily downloads, or token generation). Contact Support to raise the limit if needed. |
| `UN400` | `INVALID_INPUT` | `200`, `400` | A parameter is missing, malformed, empty, or otherwise invalid. Check the field named in `details` against the endpoint reference. |
| `UN401` | `UNAUTHORIZED` | `401` | The request is not authenticated or not authorized—for example a missing, expired, or wrong-scope access token. |
| `UN402` | `PAYMENT_REQUIRED` | `402` | Payment is required before the operation can proceed (for example a document order that exceeds an allowed cost threshold). |
| `UN404` | `RESOURCE_NOT_FOUND` | `200`, `404` | The requested resource does not exist, or the ID you supplied could not be found. |
| `UN429` | `TOO_MANY_REQUESTS` | `429` | You have exceeded the allowed request rate for this resource. Wait and retry with backoff. See [Rate Limits](../getting-started/rate-limits.md). |
| `UN500` | `INTERNAL_SERVER_ERROR` | `200`, `500` | An unexpected error occurred on UniCourt’s side while processing the request. Retry after a short delay; contact Support if it persists. |
| `UN501` | `FEATURE_NOT_SUPPORTED` | `200` | The requested operation is not supported for this resource or court source. |
| `UN502` | `ISSUE_AT_THE_COURT_SOURCE` | `200`, `424` | The court source is unavailable, under maintenance, or intermittently failing. UniCourt typically retries before returning this. |
| `UN503` | `NOT_ACCEPTING_REQUESTS` | `200` | The integration is not accepting requests for this resource—often because the upstream source changed or is offline. |
| `UN504` | `TIMEOUT` | `200` | The operation timed out while waiting on an upstream source or long-running workflow. |
| `UN505` | `BROKEN_INTEGRATION` | `200` | Integration with the court source is broken due to a change on the source side. Restoring it requires action by UniCourt. |
| `UN506` | `DELAYED_AT_THE_COURT_SOURCE` | `200` | Fulfillment is delayed at the court source. The request was accepted, but completion is waiting on the court. |

## Codes commonly returned with HTTP 200

On long-running callback and status endpoints (for example case update, case track, document order, case import, and entity update/track), an error can be delivered **inside an HTTP 200** response. Error handling that keys only off the HTTP status will miss these. Always check whether the body `object` is `Exception`.

Codes that appear with HTTP `200` in the catalog above:

`UN100`, `UN101`, `UN103`, `UN203`, `UN400`, `UN404`, `UN500`, `UN501`, `UN502`, `UN503`, `UN504`, `UN505`, `UN506`

See [Error Management — Errors returned with HTTP 200](../knowledge-base/error-codes.md#errors-returned-with-http-200) for handling guidance.

## Endpoint-specific errors

Some endpoints document additional context, example `details` strings, or workflow-specific failures in their own pages and OpenAPI examples. Prefer those pages when debugging a single API; use this page for the shared code and message values that appear across APIs.
