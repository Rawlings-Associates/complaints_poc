---
title: "Working with UniCourt APIs"
source: https://dart.unicourt.com/res-deep/assets/deep-v3-api-doc/getting-started/working-with-unicourt-apis/
retrieved: 2026-10-01
---

# Working with UniCourt APIs

This page teaches the foundations of our APIs: the workspace model, authentication, your first call, and the handful of conventions that show up on almost every endpoint. For a map of what DEEP can do, see [What You Can Do with DEEP](../getting-started/what-you-can-do-with-deep.md).

## What the DEEP API is

DEEP is UniCourt's litigation data platform API. It gives you programmatic access to cases and their docket entries, documents, parties, counsel, judges, and hearings; to normalized attorney and law firm entities; to court master data; and to analytics across all of it. You can search and read this data, order and download documents, and set up tracking so UniCourt keeps your data fresh as courts publish new activity.

Every action you take (including viewing cases, case tracking, etc.) is done inside a **workspace**, helping you stay organized and collaborate effectively. Most endpoints live under `/workspace/{workspaceId}/...`, so the workspace ID is the first thing you reach for after authenticating. For concepts, token scopes, and creating workspaces, see [Account & Workspace Management](../getting-started/account-workspace-management.md).

## What you can do with DEEP

DEEP is a single API, not a bundle of separately versioned products, so there is no product picker to work through before you get started. For the full map of API groups and common use cases, with links straight to the endpoints that get you there, see [What You Can Do with DEEP](../getting-started/what-you-can-do-with-deep.md).

## The base URL

All requests go to your assigned DEEP host. Examples on this page use `https://deep-api.unicourt.com` as a stand-in; check your onboarding details for your actual host.

```text
https://deep-api.unicourt.com/...
```

## Authentication

DEEP uses bearer tokens, in two scopes:

- **Account tokens** authenticate you at the account level and cover account-wide operations, including managing workspaces. Generate one with `POST /generateNewToken`.
- **Workspace tokens** are scoped to a single workspace and are what you use for day-to-day data calls. Generate one with `POST /generateNewWorkspaceToken`.

Send the token as a bearer header on every request:

```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \  "https://deep-api.unicourt.com/workspaces"
```

Rotate tokens by generating a new one and invalidating the old. Treat tokens like passwords: never commit them, and prefer environment variables.

For more details on authentication, see [Authentication](../getting-started/authentication.md).

## Your first request

A first call has three steps: find your workspace, run a search, then read a case.

**1. List your workspaces** to get a `workspaceId`:

```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \  "https://deep-api.unicourt.com/workspaces"
```

**2. Search for cases** in that workspace:

```bash
curl -H "Authorization: Bearer YOUR_WORKSPACE_TOKEN" \  --data-urlencode 'q=caseName:(cavalry) AND CaseStatus:(caseClass:civil)' \  -G "https://deep-api.unicourt.com/workspace/WORKSPACE_ID/caseSearch"
```

**3. Fetch the full case** using a `caseId` from the results:

```bash
curl -H "Authorization: Bearer YOUR_WORKSPACE_TOKEN" \  "https://deep-api.unicourt.com/workspace/WORKSPACE_ID/case/CASE_ID"
```

## Conventions you will see everywhere

### The workspace path

Nearly every data endpoint is prefixed with `/workspace/{workspaceId}`. The few that are not (token management, `workspaceCreate`, the top-level `/workspaces`) are account-level operations. If an endpoint acts on litigation data, expect the workspace prefix.

### The query language

Search and master data endpoints accept a `q` parameter written in a keyword expression language with logical operators.

| Operator | Meaning | Example |
| --- | --- | --- |
| `AND` | All terms must match | `caseName:(cavalry) AND CaseStatus:(caseClass:civil)` |
| `OR` | Any term matches | `name:(Wage Claim) OR name:(Tax Claim)` |
| `NOT` | Exclude a term | `caseName:(cavalry) NOT Party:(name:(john))` |
| `"phrase"` | Exact phrase | `caseName:"cavalry"` |
| `~ n` | Proximity within n words | `"personal injury" ~ 5` |
| `( ... )` | Grouping and precedence | `caseName:(cavalry) AND (Party:(name:(john)) OR Attorney:(name:(john)))` |

Master data queries allow at most 15 operators in a single expression. The full list of searchable fields lives in the query language reference, which every searchable endpoint links to.

### Pagination

List endpoints page their results and return paging metadata. A case search returns 10 results per page, and a case returns up to 100 docket entries or documents per page. Iterate by requesting the next page until results are exhausted, and always read the paging metadata rather than assuming the first page is the full set. Where available, follow `nextPageAPI` directly instead of constructing page URLs yourself. For more details on pagination, see [Pagination](../knowledge-base/pagination.md).

### Sorting

List endpoints accept sort and order parameters; search endpoints use their own search-sort and search-order parameters. Combine them to control ordering, for example most recently filed first.

### Synchronous vs asynchronous

Most reads are synchronous. A few operations are long-running and asynchronous: `caseImport`, `caseExport`, `caseUpdate`, `normAttorneyUpdate`, and `caseDocumentOrder`. These acknowledge immediately, then progress through a status sequence:

- **IN_PROGRESS** while the work runs
- **DELAYED** if a source or internal slowdown occurs
- **FAILURE** if it times out or errors
- **COMPLETE** when it finishes

Receive results over WebSocket

For async operations, open a WebSocket connection and receive the result there. That is the recommended method. Polling the corresponding `callbacks` endpoint is available but slower, and we do not recommend it for production.

### Case Search vs Case Match

**Search** (`caseSearch`) when you need a list of cases that meet certain criteria, or when you already confidently know key identifying information about a single case. **Match** (`caseMatch`) when you are trying to find a case from imperfect data—it fuzzy-matches your inputs against UniCourt's holdings so you can resolve to the standardized, cleaned version of the case.

### Tracking vs updating

**Update** (`caseUpdate`) when you need a one-off refresh of a case from the court source. **Track** (`caseTrack`) when you need to schedule recurring updates (hourly, daily, weekly, or monthly) so UniCourt keeps the case current automatically. The same distinction applies to attorneys and firms.

### Cases and entity profiles are snapshots in time

A case in UniCourt is a snapshot, not a live view of the court. To get its current state, run an update or put the case on tracking. The same is true of attorney and law firm profiles.

### Master data resolution

Many workflows start with plain language ("personal injury", "California", "motion to dismiss") that must become a structured ID before you can search or filter. Resolve those terms against the relevant `masterData/{type}` endpoint first, cache the IDs, and pass them into your search. Treat resolution as its own step.

### Errors

Errors return a structured response containing an error `code`, a `message` identifying the error type, and `details` with additional context. Build your error handling around the stable `code` value rather than parsing the `message` or `details` text. For more details on errors, see [Error Management](../knowledge-base/error-codes.md) and [General Error Codes](../knowledge-base/general-error-codes.md).

### Responses

A successful response returns `200 OK` with the result in the body, even if the query itself matches nothing. Any other status code means the request could not be processed, whether from a malformed query, an authentication problem, or an unexpected server-side error. If you see non-200 responses repeatedly and unexpectedly, contact UniCourt support rather than retrying blind.

### Rate limits

Stay under **30 requests per 5 seconds**. Exceeding that returns a `429`, and you should back off to that rate. For more details on rate limits, see [Rate Limits](../getting-started/rate-limits.md).

### Usage and limits

Billable activity limits are tracked at the account-level. There is no separate, per-workspace limit. However, you are able to check your usage consumption either per-workspace or at the account-level. For more details, see [Usage, Limits, and Billable Activity](../getting-started/usage-limits-billable-activities.md).

## Examples: search, then read a case

The same search-then-read flow in three languages.

- cURL
- Python
- Node.js

```bash
# 1. Searchcurl -H "Authorization: Bearer YOUR_WORKSPACE_TOKEN" \  --data-urlencode 'q=caseName:(cavalry) AND CaseStatus:(caseClass:civil)' \  -G "https://deep-api.unicourt.com/workspace/WORKSPACE_ID/caseSearch"# 2. Read the case using a caseId from the resultscurl -H "Authorization: Bearer YOUR_WORKSPACE_TOKEN" \  "https://deep-api.unicourt.com/workspace/WORKSPACE_ID/case/CASE_ID"
```

```python
import requestsBASE = "https://deep-api.unicourt.com"TOKEN = "YOUR_WORKSPACE_TOKEN"WORKSPACE = "WORKSPACE_ID"headers = {"Authorization": f"Bearer {TOKEN}"}# Search, then read the first caser = requests.get(    f"{BASE}/workspace/{WORKSPACE}/caseSearch",    headers=headers,    params={"q": "caseName:(cavalry) AND CaseStatus:(caseClass:civil)"},)case_id = r.json()["cases"][0]["caseId"]  # adjust to the response envelopecase = requests.get(    f"{BASE}/workspace/{WORKSPACE}/case/{case_id}",    headers=headers,).json()print(case)
```

```javascript
const BASE = "https://deep-api.unicourt.com";const TOKEN = "YOUR_WORKSPACE_TOKEN";const WORKSPACE = "WORKSPACE_ID";const headers = { Authorization: `Bearer ${TOKEN}` };const q = encodeURIComponent("caseName:(cavalry) AND CaseStatus:(caseClass:civil)");const search = await fetch(  `${BASE}/workspace/${WORKSPACE}/caseSearch?q=${q}`,  { headers }).then((res) => res.json());const caseId = search.cases[0].caseId; // adjust to the response envelopeconst fullCase = await fetch(  `${BASE}/workspace/${WORKSPACE}/case/${caseId}`,  { headers }).then((res) => res.json());console.log(fullCase);
```

## Explore the live reference

The interactive API reference lets you try requests against your workspace and see real responses. This page teaches the conventions; the reference gives you the exact fields. To view a response schema, use the schema toggle next to the example value rather than scrolling to the bottom of the page.
