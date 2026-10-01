---
title: "Search for Cases"
source: https://dart.unicourt.com/res-deep/assets/deep-v3-api-doc/common-use-cases/find-and-read-cases/search-for-cases/
retrieved: 2026-10-01
---

# Search for Cases

Find cases in your workspace by keyword expression against **Case Search**. This walkthrough covers building a query, running the search, and paging through results.

**Reference docs:** [Case Search](../../knowledge-base/case-search.md) (endpoints, response fields, vs Match), [Query Builders](../../knowledge-base/query-builders.md) (expression syntax), [Pagination](../../knowledge-base/pagination.md) (list endpoints), [Resolve master data](../../common-use-cases/find-and-read-cases/resolve-master-data.md) (look up `courtId`, `caseClassId`, and other filter IDs).

## Before you start

You need:

- A **workspace ID** (`workspaceId`)
- A **workspace-scoped JWT** from `POST /generateNewWorkspaceToken` (see [Authentication](../../getting-started/authentication.md))

Send the token on every request:

```http
Authorization: Bearer <Your JWT accessToken>
```

Base URL for data calls: **`https://deep-api.unicourt.com`**.

## Step 1 — Build a keyword expression

Case Search takes a required **`q`** parameter: a keyword expression made of field names, values, and Boolean operators (`AND`, `OR`, `NOT`). Wrap nested filters in parentheses.

Examples:

| Goal | Example `q` |
| --- | --- |
| Cases whose caption contains "Harley-Davidson" | `caseName:(Harley-Davidson)` |
| Cases filed on or after 2021-01-01 | `filedDate:{2021-01-01T00:00:00 TO *}` |
| Caption + date combined | `caseName:(Harley-Davidson) AND filedDate:{2021-01-01T00:00:00 TO *}` |
| Plaintiff named Morris | `(Party:((name:(Morris)) AND (PartyRole:(name:(Plaintiff)))))` |
| Counsel named Connors | `(Counsel:(name:(Connors)))` |
| State courts (`type` is `State` or `Federal`) | `(Court:(type:"State"))` |
| Caption, date, party, counsel, and court combined | `(caseName:(Harley-Davidson)) AND filedDate:{2021-01-01T00:00:00 TO *} AND (Party:((name:(Morris)) AND (PartyRole:(name:(Plaintiff))))) AND (Counsel:(name:(Connors))) AND (Court:(type:"State"))` |
| Exact case number | `(caseNumber:"CA 25-00256")` |

The Case Search spec documents every supported field and nested filter. Use **Try It Out** in the [**Case Search API spec**](#) to validate expressions before you ship them.

Counsel vs Attorney in search

Participant filters in **`q`** use **`Counsel`**. On the case object itself, attorneys and law firms are also modeled as **Counsel** — see [Understanding the Counsel Object](../../knowledge-base/understanding-the-counsel-object.md).

To filter by court or case type ID instead of free text, resolve master data IDs first (see [Resolve master data](../../common-use-cases/find-and-read-cases/resolve-master-data.md)), then nest them in `q` (for example `(CaseType:(caseClassId:"CSCLNjbKTN7Yfo2wdb"))`).

## Step 2 — Run the search

Submit a **GET** to **`/workspace/{workspaceId}/caseSearch`** with **`q`**, **`pageNumber`** (required, start at `1`), and optional **`sort`** / **`order`**.

Search by case number

```Shell
curl -X 'GET' \  'https://deep-api.unicourt.com/workspace/{workspaceId}/caseSearch?q=%28caseNumber%3A%22CA%2025-00256%22%29&pageNumber=1&sort=filedDate&order=desc' \  -H 'accept: application/json' \  -H 'Authorization: Bearer <Your JWT accessToken>'
```

Search by caption, party, counsel, court, and filing date

```Shell
curl -X 'GET' \  'https://deep-api.unicourt.com/workspace/{workspaceId}/caseSearch?q=%28caseName%3A%28Harley-Davidson%29%29%20AND%20filedDate%3A%7B2021-01-01T00%3A00%3A00%20TO%20%2A%7D%20AND%20%28Party%3A%28%28name%3A%28Morris%29%29%20AND%20%28PartyRole%3A%28name%3A%28Plaintiff%29%29%29%29%29%20AND%20%28Counsel%3A%28name%3A%28Connors%29%29%29%20AND%20%28Court%3A%28type%3A%22State%22%29%29&pageNumber=1&sort=filedDate&order=desc' \  -H 'accept: application/json' \  -H 'Authorization: Bearer <Your JWT accessToken>'
```

## Step 3 — Read the response

A successful search returns **`200 OK`** with a **`CaseSearchResponse`**:

Excerpt — CaseSearchResponse

```json
{  "object": "CaseSearchResponse",  "caseSearchResultArray": [    {      "object": "CaseSearchResult",      "caseId": "CASEggd5bf749967db",      "caseName": "Harold E. Morris et al v. Harley-Davidson Motor Company Group, LLC",      "caseNumber": "CA 25-00256",      "filedDate": "2025-02-13T00:00:00+00:00",      "caseAPI": "/workspace/{workspaceId}/case/CASEggd5bf749967db",      "matchedObjectArray": [        {          "object": "MatchedObject",          "matchedObjectId": "CNSLggc233ac8ea445",          "matchedObjectName": "Counsel",          "matchedObjectAttribute": "name",          "highlightSnippet": "<b>CONNORS</b> LLP",          "matchedObjectAPI": "/workspace/{workspaceId}/counsel/CNSLggc233ac8ea445"        },        {          "object": "MatchedObject",          "matchedObjectId": "PRTYgg4121f3bc6aa8",          "matchedObjectName": "Party",          "matchedObjectAttribute": "name",          "highlightSnippet": "<b>Morris</b> , Respondent",          "matchedObjectAPI": "/workspace/{workspaceId}/party/PRTYgg4121f3bc6aa8"        },        {          "object": "MatchedObject",          "matchedObjectId": "PTYRiP8nMgPxBsPc5i",          "matchedObjectName": "Party.PartyRole",          "matchedObjectAttribute": "name",          "highlightSnippet": "<b>Plaintiff</b>",          "matchedObjectAPI": "/workspace/{workspaceId}/masterData/partyRole/PTYRiP8nMgPxBsPc5i"        }      ]    }  ],  "caseSearchId": "CSRHRywKSxXDwPkJod",  "q": "%28caseName%3A%28Harley-Davidson%29%29%20AND%20filedDate%3A%7B2021-01-01T00%3A00%3A00%20TO%20%2A%7D%20AND%20%28Party%3A%28%28name%3A%28Morris%29%29%20AND%20%28PartyRole%3A%28name%3A%28Plaintiff%29%29%29%29%29%20AND%20%28Counsel%3A%28name%3A%28Connors%29%29%29%20AND%20%28Court%3A%28type%3A%22State%22%29%29",  "pageNumber": 1,  "totalCount": 4,  "totalPages": 1,  "nextPageAPI": null,  "previousPageAPI": null}
```

Key fields:

| Field | Use it to… |
| --- | --- |
| **`caseSearchResultArray`** | Scan matches on this page (preview metadata, not the full case) |
| **`caseId`** / **`caseAPI`** | Open the full case (next walkthrough) |
| **`matchedObjectArray`** | See which field matched and highlighted snippets |
| **`caseSearchId`** | Re-fetch this exact search later (Step 5) |
| **`totalCount`** / **`totalPages`** | Know how many pages to retrieve |
| **`nextPageAPI`** | GET the next page (relative path on the same host) |

An empty **`caseSearchResultArray`** with **`200 OK`** means no cases matched — the query was valid but returned zero rows.

## Step 4 — Paginate

Every search request must include **`pageNumber`**. Increment it until **`nextPageAPI`** is `null`.

Case search returns **10 results per page** and supports up to **1,000 pages** per query — so a single search can return at most **10,000 cases**. If **`totalCount`** is higher, narrow your **`q`** with additional filters, or batch by **`filedDate`** (or another date field) and run multiple searches. See [Pagination](../../knowledge-base/pagination.md) for the full page-size table and guidance.

Page 2 using nextPageAPI

```Shell
curl -X 'GET' \  'https://deep-api.unicourt.com/workspace/{workspaceId}/caseSearch?q=%28caseName%3A%28Harley-Davidson%29%29%20AND%20filedDate%3A%7B2021-01-01T00%3A00%3A00%20TO%20%2A%7D%20AND%20%28Party%3A%28%28name%3A%28Morris%29%29%20AND%20%28PartyRole%3A%28name%3A%28Plaintiff%29%29%29%29%29%20AND%20%28Counsel%3A%28name%3A%28Connors%29%29%29%20AND%20%28Court%3A%28type%3A%22State%22%29%29&pageNumber=2&sort=filedDate&order=desc' \  -H 'accept: application/json' \  -H 'Authorization: Bearer <Your JWT accessToken>'
```

Or call the **`nextPageAPI`** path from the prior response directly (prepend `https://deep-api.unicourt.com` if the value is relative).

See [Pagination](../../knowledge-base/pagination.md) for edge cases (invalid `pageNumber`, empty last page).

## Step 5 — Re-run a previous search (optional)

To retrieve results for an earlier query without resending the full **`q`** string, use the **`caseSearchId`** from the original response:

Fetch by caseSearchId

```Shell
curl -X 'GET' \  'https://deep-api.unicourt.com/workspace/{workspaceId}/caseSearch/{caseSearchId}?pageNumber=1' \  -H 'accept: application/json' \  -H 'Authorization: Bearer <Your JWT accessToken>'
```

CASE SEARCH EXPIRATION

Keep in mind that a caseSearchId expires six months after its last use.

## Next step

Search returns case previews. To pull docket entries, parties, counsel, and documents for a **`caseId`**, continue to [Read a full case](../../common-use-cases/find-and-read-cases/read-a-full-case.md).
