---
title: "Get Case Hearings"
source: https://dart.unicourt.com/res-deep/assets/deep-v3-api-doc/common-use-cases/get-case-content/get-case-hearings/
retrieved: 2026-10-01
---

# Get Case Hearings

List scheduled hearings for a case and interpret how UniCourt resolved each hearing's time from the court source.

**Reference docs:** [Hearings](../../knowledge-base/hearings.md) (fields, time-resolution rules, history endpoints), [Read a full case](../../common-use-cases/find-and-read-cases/read-a-full-case.md), [Pagination](../../knowledge-base/pagination.md).

## Before you start

You need:

- A **`caseId`** in your workspace
- A **workspace token** and **`workspaceId`**
- Base URL: **`https://deep-api.unicourt.com`**

Hearings reflect data UniCourt already holds for the case. To refresh from the court first, see [Update a case once](../../common-use-cases/keep-cases-current/update-a-case-once.md).

## Step 1 — List hearings

**GET** [**/workspace/{workspaceId}/case/{caseId}/hearings**](#):

Get hearings

```Shell
curl -X 'GET' \  'https://deep-api.unicourt.com/workspace/{workspaceId}/case/{caseId}/hearings?pageNumber=1&sortBy=oldest%20to%20latest' \  -H 'accept: application/json' \  -H 'Authorization: Bearer <Your JWT accessToken>'
```

| Query parameter | Purpose |
| --- | --- |
| **`pageNumber`** | Which page to return. Follow **`nextPageAPI`** until it is `null`. |
| **`sortBy`** | `oldest to latest` or `latest to oldest`. |

The response is a **`Hearings`** object: `hearingArray` plus paging metadata (`pageNumber`, `totalCount`, `totalPages`, `nextPageAPI`).

Sample response

```json
{  "object": "Hearings",  "pageNumber": 1,  "totalCount": 3,  "totalPages": 1,  "nextPageAPI": null,  "hearingArray": [    {      "object": "Hearing",      "hearingId": "HRNGgc513f837d8264b518516a0e230a",      "hearingDate": "2025-09-22",      "hearingTime": "09:00:00",      "hearingTimezone": "America/Los_Angeles",      "hearingTimeResolution": "SOURCE_PROVIDED",      "sourceHearingTime": "09:00:00",      "hearingLocation": "CIVIC CENTER COURTHOUSE ROOM 204",      "hearingDescription": "ADDED TO CALENDAR FOR Status Hearing...",      "hearingStructured": {        "extractedFields": null,        "rawOrderedDataArray": [          {            "lbl": "Judge Name",            "ord": 0,            "val": "ROSS C. MOODY",            "childArray": []          }        ]      }    }  ]}
```

## Step 2 — Read date, time, and location

For each item in **`hearingArray`**:

| Field | Use it for |
| --- | --- |
| **`hearingDate`** | Calendar date (`YYYY-MM-DD` only). |
| **`hearingTime`** | Normalized clock time (`HH:MM:SS`), or `null` when none was determined. |
| **`hearingTimezone`** | Timezone for that hearing. |
| **`hearingLocation`** | Venue / room text from the source (renamed from `location` in 2026-08-03). |
| **`hearingDescription`** | Full source description. |
| **`hearingId`** | Stable ID if you store or de-dupe hearings. |

Do not treat `hearingDate` as a date-time. Combine **`hearingDate` + `hearingTime` + `hearingTimezone`** when you need a scheduled instant.

## Step 3 — Check `hearingTimeResolution`

Before displaying or sorting on **`hearingTime`**, read **`hearingTimeResolution`**:

| Value | What it means for your app |
| --- | --- |
| **`SOURCE_PROVIDED`** | Time came clearly from the source (AM/PM or unambiguous 24-hour hour ≥ 13). Safe to treat **`hearingTime`** as authoritative. |
| **`INFERRED`** | UniCourt inferred AM/PM from an ambiguous source clock time. Prefer showing **`sourceHearingTime`** (when present) alongside the normalized time, or flag the value as inferred. |
| **`NOT_PROVIDED`** | No usable time. **`hearingTime`** is `null`—schedule on **`hearingDate`** only. |

Example: source text `7:00` with no AM/PM becomes **`INFERRED`** with **`hearingTime`: `19:00:00`** (treated as 7:00 PM). Source `10:00` without meridian becomes **`INFERRED`** with **`hearingTime`: `10:00:00`** (kept as-is). Full rules and examples are in [Hearings — Hearing time resolution](../../knowledge-base/hearings.md#hearing-time-resolution).

Existing data

Older hearings may have **`sourceHearingTime`: `null`** even when **`hearingTimeResolution`** is set. After court parsers capture source times, refresh the case so future hearings can populate **`sourceHearingTime`**.

## Step 4 — Optional: hearing history

To see how hearings changed across case refreshes:

1. **GET** `/workspace/{workspaceId}/caseHistory/{caseId}/hearingsHistory` — list history windows (optional `fromDate` / `toDate`, `pageNumber`).
2. **GET** `/workspace/{workspaceId}/caseHistory/{caseId}/hearingsHistory/{lastFetchDateWithUpdates}` — hearings snapshot for one fetch date.

See [See what changed on a case](../../common-use-cases/keep-cases-current/sync-case-history.md) for the Case History pattern.

## What's next

- [Hearings](../../knowledge-base/hearings.md) — complete field reference and resolution rules
- [Search for cases](../../common-use-cases/find-and-read-cases/search-for-cases.md) — filter with `(Hearing:(hearingDate:[now TO now+10d]))`
- [Update a case once](../../common-use-cases/keep-cases-current/update-a-case-once.md) — refresh hearings from the court
- [Export a case](../../common-use-cases/get-case-content/export-a-case.md) — package full case data including hearings
