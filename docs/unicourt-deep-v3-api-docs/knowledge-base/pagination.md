---
title: "Pagination"
source: https://dart.unicourt.com/res-deep/assets/deep-v3-api-doc/knowledge-base/pagination/
retrieved: 2026-10-01
---

# Pagination

## Learn how to paginate results from UniCourt's endpoints

List endpoints, such as case search or docket entry retrieval, can return far more results than is practical to send in a single response. To keep performance predictable, these endpoints return one page of results per request instead of the full result set.

For example, this is a request to search cases within a workspace, requesting page 1:

```bash
curl -G https://deep-api.unicourt.com/v3/workspace/{workspaceId}/caseSearch \  -H "Authorization: Bearer <YOUR_API_KEY>" \  -d 'q=(caseNumber:"ER20751557")' \  -d pageNumber=1
```

The response contains one page of results, along with paging metadata:

```json
{  "object": "CaseSearchResponse",  "pageNumber": 1,  "totalCount": 27,  "totalPages": 3,  "nextPageAPI": "/workspace/{workspaceId}/caseSearch?q=(caseNumber:\"ER20751557\")&pageNumber=2",  "previousPageAPI": null,  "data": [    { "caseId": "CASEar7a26f15e76cf", "caseTitle": "..." },    { "caseId": "CASEbf91c3a2d4e1", "caseTitle": "..." }  ]}
```

Keep in mind the following details when working with these endpoints:

- Objects are inside the `data` property.
- `pageNumber` is a **required** query parameter. Every list and search request must include it, starting at 1.
- `totalCount` is the total number of results across all pages, not the count on the current page.
- `totalPages` tells you how many pages exist in total for the current query.
- `nextPageAPI` is `null` on the last page, and otherwise gives you the exact path to call next.

Page size is fixed per endpoint and can't be changed with a `limit` or `pageSize` parameter:

| Endpoint type | Results per page |
| --- | --- |
| Case search | 10 |
| Docket entries | 100 |
| Documents | 100 |

Pagination is capped at **1,000 pages** per query. Combined with the fixed page sizes above, that means a single query can return at most:

| Endpoint type | Max results per query |
| --- | --- |
| Case search | 10,000 |
| Docket entries | 100,000 |
| Documents | 100,000 |

If a query would match more results than this cap allows, apply additional filters to narrow the result set whenever possible. When you truly need a larger set, batch the work into multiple queries by date fields (for example `filedDate` on case search, or another date filter supported by the endpoint) so each request stays within the 1,000-page limit.

## Paginating results

Because `totalCount` and `totalPages` are returned on every page, you can decide upfront how many pages to fetch, or loop until you've exhausted the results. Don't assume the first page is the full set, and don't rely on `data.length` alone to detect the end of results since the last page may be a partial page.

### Recommended: follow `nextPageAPI`

The simplest and most reliable approach is to follow `nextPageAPI` directly rather than constructing page URLs yourself. When `nextPageAPI` is `null`, you've reached the last page.

```javascript
let url = 'https://deep-api.unicourt.com/v3/workspace/{workspaceId}/caseSearch?q=(caseNumber:"ER20751557")&pageNumber=1';const allResults = [];while (url) {  const response = await fetch(url, {    headers: { Authorization: `Bearer ${API_KEY}` }  });  const page = await response.json();  allResults.push(...page.data);  url = page.nextPageAPI    ? `https://deep-api.unicourt.com/v3${page.nextPageAPI}`    : null;}
```

### Alternative: increment `pageNumber`

If you'd rather manage pagination yourself, increment `pageNumber` on each request and stop once `pageNumber` reaches `totalPages`.

```javascript
let pageNumber = 1;let totalPages = 1;const allResults = [];do {  const response = await fetch(    `https://deep-api.unicourt.com/v3/workspace/{workspaceId}/caseSearch?q=(caseNumber:"ER20751557")&pageNumber=${pageNumber}`,    { headers: { Authorization: `Bearer ${API_KEY}` } }  );  const page = await response.json();  allResults.push(...page.data);  totalPages = page.totalPages;  pageNumber++;} while (pageNumber <= totalPages);
```

## Errors

Requests to list or search endpoints without a `pageNumber`, or with an invalid one, return a `400`:

```json
{  "object": "Exception",  "code": "UN400",  "message": "INVALID_INPUT",  "details": "pageNumber parameter is mandatory."}
```

```json
{  "object": "Exception",  "code": "UN400",  "message": "INVALID_INPUT",  "details": "Requested pageNumber is invalid. pageNumber parameter needs to be digit which is greater than 0."}
```

`pageNumber` must be an integer greater than 0. Requesting a page beyond `totalPages` returns an empty `data` array rather than an error.

## Migration Notes for v2 Integrators

If your integration builds page URLs by hand, omits `pageNumber`, or assumes account-scoped list paths, update as below.

| v2 Field / Endpoint | v3 Field / Endpoint | Notes |
| --- | --- | --- |
| Optional or omitted `pageNumber` on list/search calls | **`pageNumber` required** (integer ≥ 1) | Missing or invalid `pageNumber` returns **`400` / `UN400` / `INVALID_INPUT`** |
| Account-scoped list paths (for example `/caseSearch`) | `/workspace/{workspaceId}/…` list paths | Same pagination fields; path is workspace-scoped on `deep-api.unicourt.com` |
| Constructed `?pageNumber=N` URLs | Prefer **`nextPageAPI`** from each response | Follow `nextPageAPI` until `null`; still include `pageNumber` on the first request |
| Client-chosen `limit` / `pageSize` | *(not supported)* | Page size is fixed per endpoint (for example, 10 for case search; 100 for docket entries and documents) |
