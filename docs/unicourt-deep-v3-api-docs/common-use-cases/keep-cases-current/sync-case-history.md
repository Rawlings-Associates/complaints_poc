---
title: "See What Changed on a Case"
source: https://dart.unicourt.com/res-deep/assets/deep-v3-api-doc/common-use-cases/keep-cases-current/sync-case-history/
retrieved: 2026-10-01
---

# See What Changed on a Case

You already have a case in your system. A user opens it tomorrow—or your nightly job runs—and you need to know **what is new since the last time you looked**, without re-fetching every party, docket entry, and document from scratch.

That is what **Case History** is for. UniCourt records each batch of court updates under a **`lastFetchDateWithUpdates`** timestamp. You compare that to the date you stored on your last check, read the summary counts, then pull only the added or changed records you care about.

**Common reasons to use this:**

- **Case management or litigation tools** — show a "what's new" panel when someone reopens a matter
- **Incremental ETL** — append new docket entries and documents to your warehouse instead of full reloads
- **Targeted alerts** — after [tracking](../../common-use-cases/keep-cases-current/track-a-case-on-a-schedule.md) or [updating](../../common-use-cases/keep-cases-current/update-a-case-once.md), inspect only the dimensions that matter (e.g. new filings, counsel changes)
- **Lower API cost** — history endpoints return deltas; [reading the full case](../../common-use-cases/find-and-read-cases/read-a-full-case.md) is for when you need the complete current snapshot

**Reference docs:** [**Case View API — Case History**](#), [Understanding the Counsel Object](../../knowledge-base/understanding-the-counsel-object.md) (v3 counsel model).

## Before you start

You need:

- A **`caseId`** in your workspace
- A **workspace token** and **`workspaceId`**
- The **`lastFetchDateWithUpdates`** from **your last check** — usually from the **`Case`** object you already stored, or from a completed [Case Update](../../common-use-cases/keep-cases-current/update-a-case-once.md)

Case History reflects changes UniCourt has **already recorded**. If the case might be stale on the court side, run an [update](../../common-use-cases/keep-cases-current/update-a-case-once.md) or rely on [track](../../common-use-cases/keep-cases-current/track-a-case-on-a-schedule.md) first, then ask what changed.

## How it works

Each time UniCourt ingests new activity on a case, it creates a history bucket keyed by **`lastFetchDateWithUpdates`**. Your workflow:

1. **Compare dates** — find buckets newer than your stored "last checked" timestamp.
2. **Read the summary** — see how many parties, docket entries, documents, etc. were added or changed on each date.
3. **Pull the details** — fetch only the added/changed rows for the dimensions you need.

## Step 1 — See if anything changed

Case history overview

```Shell
curl -X 'GET' \  'https://deep-api.unicourt.com/workspace/{workspaceId}/caseHistory/{caseId}?pageNumber=1' \  -H 'accept: application/json' \  -H 'Authorization: Bearer <Your JWT accessToken>'
```

Optional filters: **`fromDate`**, **`toDate`** (ISO date-times), **`pageNumber`**.

The response lists **`caseHistoryByDateArray`**. Each entry has **`lastFetchDateWithUpdates`** and a **`caseHistorySummary`** with counts like **`docketEntriesAddedCount`** and **`counselChangedCount`**.

Excerpt — CaseHistories

```json
{  "object": "CaseHistories",  "pageNumber": 1,  "caseHistoryByDateArray": [    {      "object": "CaseHistoryByDate",      "lastFetchDateWithUpdates": "2022-06-03T00:00:00+00:00",      "caseHistory": {        "object": "CaseHistory",        "caseHistorySummary": {          "docketEntriesAddedCount": 1,          "docketEntriesChangedCount": 1,          "counselAddedCount": 1,          "partiesAddedCount": 1        }      }    }  ],  "totalCount": 25,  "totalPages": 4,  "nextPageAPI": "..."}
```

If every **`lastFetchDateWithUpdates`** is **on or before** your stored last-check date, nothing new has been recorded—you are done. Otherwise, note which dates and counts need a closer look.

## Step 2 — Browse changes by dimension

When you need to scan a date range (for example, "everything in the last 30 days"), use dimension-specific list endpoints:

| What changed | List endpoint |
| --- | --- |
| Case metadata | `GET .../caseHistory/{caseId}` |
| Parties | `GET .../caseHistory/{caseId}/partiesHistory` |
| Counsel | `GET .../caseHistory/{caseId}/counselHistory` |
| Counsel associations | `GET .../caseHistory/{caseId}/counselAssociationsHistory` |
| Party–counsel links | `GET .../caseHistory/{caseId}/partyCounselAssociationsHistory` |
| Judges | `GET .../caseHistory/{caseId}/judgesHistory` |
| Docket entries | `GET .../caseHistory/{caseId}/docketEntriesHistory` |
| Hearings | `GET .../caseHistory/{caseId}/hearingsHistory` |
| Case documents | `GET .../caseHistory/{caseId}/caseDocumentsHistory` |
| Related cases | `GET .../caseHistory/{caseId}/relatedCasesHistory` |
| Tentative rulings | `GET .../caseHistory/{caseId}/tentativeRulingsHistory` |

Docket entry changes in a date range

```Shell
curl -X 'GET' \  'https://deep-api.unicourt.com/workspace/{workspaceId}/caseHistory/{caseId}/docketEntriesHistory?fromDate=2024-01-01T00:00:00%2B00:00&toDate=2024-12-31T00:00:00%2B00:00&pageNumber=1' \  -H 'accept: application/json' \  -H 'Authorization: Bearer <Your JWT accessToken>'
```

## Step 3 — Get the actual added or changed records

Pick the **`lastFetchDateWithUpdates`** from Step 1 and call the dimension endpoint with that date in the **path**. Use **`historyClass`** to separate new records from edits:

| `historyClass` | Returns |
| --- | --- |
| **`all`** | Everything for that date (default) |
| **`added`** | New records |
| **`changed`** | Modified records |

New docket entries on one update date

```Shell
curl -X 'GET' \  'https://deep-api.unicourt.com/workspace/{workspaceId}/caseHistory/{caseId}/docketEntriesHistory/2024-06-15T14:30:00%2B00:00?historyClass=added&pageNumber=1' \  -H 'accept: application/json' \  -H 'Authorization: Bearer <Your JWT accessToken>'
```

Paginate with **`pageNumber`** and **`nextPageAPI`**. Repeat for other dimensions based on the summary counts from Step 1.

## Step 4 — Record when you last checked

After you process the new buckets, save the latest **`lastFetchDateWithUpdates`** (from the **`Case`** object or your most recent [Case Update](../../common-use-cases/keep-cases-current/update-a-case-once.md)). That becomes your baseline the next time someone asks, "what changed since we last looked?"

## Typical check-in loop

```mermaid
flowchart TD  A[Remember lastFetchDateWithUpdates from last check] --> B[Optional: PUT caseUpdate or wait for track]  B --> C[GET caseHistory summary]  C --> D{Any dates after last check?}  D -->|no| E[Nothing new — done]  D -->|yes| F[GET added/changed for each dimension]  F --> G[Update your app or datastore]  G --> H[Save new last-check date]  H --> E
```

## v3 vs v2

| v2 | v3 |
| --- | --- |
| `/caseHistory/{caseId}/attorneysHistory` | `/workspace/{workspaceId}/caseHistory/{caseId}/counselHistory` |
| `/caseHistory/{caseId}/partyAttorneyAssociationsHistory` | `.../partyCounselAssociationsHistory` |
| `caseDecisionDocumentsHistory` | *(removed)* |
| — | `counselAssociationsHistory`, `tentativeRulingsHistory` *(new)* |

All paths are workspace-scoped under **`deep-api.unicourt.com`**.

## When to use which approach

| Goal | Use |
| --- | --- |
| **What changed since my last check?** | **Case History** (this walkthrough) |
| **Give me the full case as it stands today** | [Read a full case](../../common-use-cases/find-and-read-cases/read-a-full-case.md) |
| **Pull fresh data from the court now** | [Update a case once](../../common-use-cases/keep-cases-current/update-a-case-once.md) |
| **Keep the case current automatically** | [Track a case on a schedule](../../common-use-cases/keep-cases-current/track-a-case-on-a-schedule.md) |
