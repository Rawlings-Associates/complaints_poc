---
title: "Glossary of HTTP Response Codes"
source: https://dart.unicourt.com/res-deep/assets/deep-v3-api-doc/knowledge-base/glossary-of-HTTP-response-codes/
retrieved: 2026-10-01
---

# Glossary of HTTP Response Codes

When your software sends a request to **`deep-api.unicourt.com`**, the DEEP API returns a standard HTTP status code. Most responses use **`200 OK`**, **`400 Bad Request`**, or **`500 Internal Server Error`**. Some endpoints also return more specific codes in the 2xx, 4xx, or 5xx families—for example **`404 Not Found`** or **`429 Too Many Requests`**.

Failed responses include a structured **`Exception`** object with UniCourt **`code`** values such as `UN400` or `UN404`. For how to handle errors, see [Error Management](../knowledge-base/error-codes.md). For the sorted catalog of shared codes, see [General Error Codes](../knowledge-base/general-error-codes.md).

## `200 OK` and other `2xx` status codes

These codes mean the request was processed without a transport- or parsing-level failure. **Success here does not guarantee substantive results.** A valid keyword search against [**GET /workspace/{workspaceId}/caseSearch**](#) can return **`200 OK`** with an empty result set when no cases match your `q` expression.

Callback endpoints

Some **`caseUpdate`**, **`caseTrack`**, and **`caseDocumentOrder`** callback responses return error payloads **inside HTTP 200**. Always inspect the response body `object` field on those endpoints, not only the status code. See [Error Management — Errors returned with HTTP 200](../knowledge-base/error-codes.md#errors-returned-with-http-200).

## `400 Bad Request` and other `4xx` status codes

These codes mean the problem is with the request your software sent. Common causes:

- Wrong path (for example, `/casSearch` instead of `/workspace/{workspaceId}/caseSearch`)
- Malformed **`q`** keyword expression (unbalanced parentheses, unsupported fields)
- Missing or invalid **`workspaceId`**
- Missing, expired, or wrong-scope access token (**`401 Unauthorized`**)
- Unknown resource ID (**`404 Not Found`**)
- Rate limiting (**`429 Too Many Requests`**)

The response body is usually an **`Exception`** object with `code`, `message`, and `details`. Branch on **`code`**, not on the wording of **`details`**.

## `500 Internal Server Error` and other `5xx` status codes

These codes mean UniCourt encountered an error while processing an otherwise valid request. Retry after a short delay. If **`5xx`** responses persist for the same call, contact UniCourt Support.

**5xx** responses are generally **not billable**; most **4xx** responses **are** billable. See [API Best Practices — HTTP billing behavior](../knowledge-base/api-best-practices.md#http-billing-behavior).

## Migration Notes for v2 Integrators

HTTP status semantics are unchanged in v3. Update paths and spec links when reading examples:

| v2 | v3 | Notes |
| --- | --- | --- |
| `https://enterpriseapi.unicourt.com/caseSearch` | `https://deep-api.unicourt.com/workspace/{workspaceId}/caseSearch` | Workspace-scoped base URL |
| Account token on all endpoints | Account vs workspace tokens | Data APIs require a workspace token; **`401`** if the wrong scope is used |
| Unstructured error text (varies) | `Exception` object with `code`, `message`, `details` | See [Error Management](../knowledge-base/error-codes.md) |
| `UniCourt-Enterprise-Court-Data-API-Spec` | `UniCourt-DEEP-*-API-Spec` bundles | Per-domain DEEP specs replace Enterprise bundles |
