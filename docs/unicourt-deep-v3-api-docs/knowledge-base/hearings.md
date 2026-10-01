---
title: "Hearings"
source: https://dart.unicourt.com/res-deep/assets/deep-v3-api-doc/knowledge-base/hearings/
retrieved: 2026-10-01
---

# Hearings

The Hearings APIs return scheduled hearing data for a case—date, normalized time, timezone, location, and source description—plus how UniCourt resolved the hearing time when the court source was ambiguous or incomplete.

See [Get case hearings](../common-use-cases/get-case-content/get-case-hearings.md) for a full walkthrough. Hearing IDs are prefixed `HRNG`—see [Object ID Prefixes](../knowledge-base/object-id-prefixes.md).

## Endpoints

| Method | Path | Description |
| --- | --- | --- |
| GET | `/workspace/{workspaceId}/case/{caseId}/hearings` | List hearings for a case (`getCaseHearings`) |
| GET | `/workspace/{workspaceId}/caseHistory/{caseId}/hearingsHistory` | Hearing change history for a case (`getHearingHistoryForCase`) |
| GET | `/workspace/{workspaceId}/caseHistory/{caseId}/hearingsHistory/{lastFetchDateWithUpdates}` | Hearing history snapshot for one fetch date (`getHearingHistoryForCaseBylastFetchDateWithUpdates`) |

Current hearings are a Case View sub-resource. History endpoints are part of [Case History](../common-use-cases/keep-cases-current/sync-case-history.md)—use them when you need to see how hearings changed across refreshes.

## Getting hearings for a case

Submit a **GET** to [**/workspace/{workspaceId}/case/{caseId}/hearings**](#).

Query parameters:

| Parameter | Required | Description |
| --- | --- | --- |
| `pageNumber` | No | Page of results to retrieve. Follow `nextPageAPI` when present. See [Pagination](../knowledge-base/pagination.md). |
| `sortBy` | No | `latest to oldest` or `oldest to latest`. |

List hearings for a case

```Shell
curl -X 'GET' \  'https://deep-api.unicourt.com/workspace/{workspaceId}/case/{caseId}/hearings?pageNumber=1&sortBy=oldest%20to%20latest' \  -H 'accept: application/json' \  -H 'Authorization: Bearer <Your JWT accessToken>'
```

### Response: Hearings

Hearings response (excerpt)

```json
{  "object": "Hearings",  "pageNumber": 1,  "totalCount": 3,  "totalPages": 1,  "nextPageAPI": null,  "hearingArray": [    {      "object": "Hearing",      "hearingId": "HRNGgc513f837d8264b518516a0e230a",      "hearingDate": "2025-09-22",      "hearingTime": "09:00:00",      "hearingTimezone": "America/Los_Angeles",      "hearingTimeResolution": "SOURCE_PROVIDED",      "sourceHearingTime": "09:00:00",      "hearingLocation": "CIVIC CENTER COURTHOUSE ROOM 204",      "hearingDescription": "ADDED TO CALENDAR FOR Status Hearing...",      "hearingStructured": {        "extractedFields": null,        "rawOrderedDataArray": [          {            "lbl": "Judge Name",            "ord": 0,            "val": "ROSS C. MOODY",            "childArray": []          }        ]      }    }  ]}
```

## Hearing object fields

| Field | Type | Description |
| --- | --- | --- |
| `hearingId` | string | Unique hearing ID. Prefixed with `HRNG`. |
| `hearingDate` | date (`YYYY-MM-DD`) | Hearing date from the source. Date-only—no time component. |
| `hearingTime` | string or `null` | Normalized hearing time as `HH:MM:SS` when a time is available; otherwise `null`. |
| `hearingTimezone` | string | Timezone associated with the hearing (for example `US/Central` or `America/Los_Angeles`). |
| `hearingTimeResolution` | enum | How the time was determined. See [Hearing time resolution](#hearing-time-resolution). |
| `sourceHearingTime` | string or `null` | Hearing time in the same form the court source provided. `null` when the source gave no time, or when historical data was resolved without a captured source string. |
| `hearingLocation` | string or `null` | Where the hearing takes place. |
| `hearingDescription` | string or `null` | Source hearing description text. |
| `hearingStructured` | object or `null` | Structured source fields when available (`SourceStructuredData`). |

Use **`hearingDate`**, **`hearingTime`**, and **`hearingTimezone`** together when you need a calendar schedule. Prefer **`hearingTimeResolution`** (and **`sourceHearingTime`** when present) before treating an early-morning `hearingTime` as literal clock time.

## Hearing time resolution

Court sources do not always publish hearing times clearly. Some include AM/PM or unambiguous 24-hour times; others omit the meridian or provide only a date. **`hearingTimeResolution`** tells you how UniCourt interpreted that source text into **`hearingTime`**.

| `hearingTimeResolution` | Meaning |
| --- | --- |
| **`SOURCE_PROVIDED`** | The source gave a clear time: either with AM/PM, or in 24-hour form with hour **≥ 13**. Examples: `10:00 AM`, `14:00`. |
| **`INFERRED`** | The source gave a clock time without AM/PM and not as clear 24-hour (≥ 13). UniCourt applies inference rules (below). |
| **`NOT_PROVIDED`** | The court provided only a date (or an equivalent with no usable time, such as `00:00`). **`hearingTime`** and **`sourceHearingTime`** are `null`. |

### Inference rules (`INFERRED`)

When the source time lacks AM/PM and is not unambiguous 24-hour:

| Source clock time | How UniCourt normalizes `hearingTime` |
| --- | --- |
| **0:00–7:59** | Treated as PM (add 12 hours). Example: source `7:00` → `19:00:00`. |
| **8:00–12:59** | Used as-is. Example: source `10:00` → `10:00:00`. |

### Examples

**SOURCE_PROVIDED (AM/PM)** — court site: `10-10-2026 10:00 AM`

```json
{  "hearingDate": "2026-10-10",  "hearingTime": "10:00:00",  "hearingTimezone": "US/Central",  "hearingTimeResolution": "SOURCE_PROVIDED",  "sourceHearingTime": "10:00 AM"}
```

**SOURCE_PROVIDED (24-hour, hour ≥ 13)** — court site: `10-10-2026 14:00`

```json
{  "hearingDate": "2026-10-10",  "hearingTime": "14:00:00",  "hearingTimezone": "US/Central",  "hearingTimeResolution": "SOURCE_PROVIDED",  "sourceHearingTime": "14:00"}
```

**INFERRED (0:00–7:59 → PM)** — court site: `10-10-2026 7:00`

```json
{  "hearingDate": "2026-10-10",  "hearingTime": "19:00:00",  "hearingTimezone": "US/Central",  "hearingTimeResolution": "INFERRED",  "sourceHearingTime": "7:00"}
```

**INFERRED (8:00–12:59 as-is)** — court site: `10-10-2026 10:00`

```json
{  "hearingDate": "2026-10-10",  "hearingTime": "10:00:00",  "hearingTimezone": "US/Central",  "hearingTimeResolution": "INFERRED",  "sourceHearingTime": "10:00"}
```

**NOT_PROVIDED** — court site: `10-10-2026`

```json
{  "hearingDate": "2026-10-10",  "hearingTime": null,  "hearingTimezone": "US/Central",  "hearingTimeResolution": "NOT_PROVIDED",  "sourceHearingTime": null}
```

### Existing hearings and `sourceHearingTime`

For hearings that already existed before source-time capture was available, UniCourt may still set **`hearingTimeResolution`** from the stored time component, but **`sourceHearingTime`** can remain **`null`** until the case is refreshed from a parser that captures the original source string.

| Situation | Typical result |
| --- | --- |
| Stored time was `00:00:00` (no real time) | `NOT_PROVIDED`; `hearingTime` and `sourceHearingTime` are `null` |
| Stored hour ≥ 13 | `SOURCE_PROVIDED`; `sourceHearingTime` may be `null` |
| Stored hour < 13 and not `00:00:00` | `INFERRED` (same 0:00–7:59 / 8:00–12:59 rules); `sourceHearingTime` may be `null` |

If you need a populated **`sourceHearingTime`** for older future hearings, refresh the case with [Case Update](../knowledge-base/case-update.md) or [Case Track](../knowledge-base/case-track.md) after the court source supports the new parsing.

## Finding cases by hearing date

Case Search supports hearing-date filters—for example, cases with a hearing in the next 10 days:

```text
(Hearing:(hearingDate:[now TO now+10d]))
```

See [Case Search](../knowledge-base/case-search.md) and [Query builders](../knowledge-base/query-builders.md) for query syntax.

## Migration Notes for v2 Integrators

If your integration reads `location`, date-time `hearingDate`, or fetch-date fields on Hearing objects, map to the v3 shape below. Hearings history was on the v2 Alpha Case History API; in v3 it is workspace-scoped on the same host as Case View.

| v2 | v3 | Notes |
| --- | --- | --- |
| `GET /case/{caseId}/hearings` | `GET /workspace/{workspaceId}/case/{caseId}/hearings` | Workspace-scoped on `deep-api.unicourt.com` |
| `GET /caseHistory/{caseId}/hearingsHistory` (Alpha) | `GET /workspace/{workspaceId}/caseHistory/{caseId}/hearingsHistory` | Workspace-scoped; same `fromDate` / `toDate` / `pageNumber` pattern |
| `GET /caseHistory/{caseId}/hearingsHistory/{lastFetchDateWithUpdates}` (Alpha) | `GET /workspace/{workspaceId}/caseHistory/{caseId}/hearingsHistory/{lastFetchDateWithUpdates}` | Workspace-scoped |
| `location` | `hearingLocation` | Renamed on `Hearing` |
| `hearingDate` (`date-time`) | `hearingDate` (`YYYY-MM-DD`) | Date-only; combine with `hearingTime` and `hearingTimezone` for a full schedule |
| *(none)* | `hearingId` | Prefixed `HRNG` |
| *(none)* | `hearingTime` | Normalized `HH:MM:SS`, or `null` when no time |
| *(none)* | `hearingTimezone` | Timezone for the hearing |
| *(none)* | `hearingTimeResolution` | `SOURCE_PROVIDED`, `INFERRED`, or `NOT_PROVIDED` — see [Hearing time resolution](#hearing-time-resolution) |
| *(none)* | `sourceHearingTime` | Source-form time string when captured; may be `null` on older hearings |
| `firstFetchDate`, `lastFetchDate` | *(removed)* | No longer returned on `Hearing` |
| `https://enterpriseapi.unicourt.com/…` | `https://deep-api.unicourt.com/workspace/{workspaceId}/…` | Base URL and workspace prefix |

## Related docs

- [Get case hearings](../common-use-cases/get-case-content/get-case-hearings.md) — step-by-step walkthrough
- [Read a full case](../common-use-cases/find-and-read-cases/read-a-full-case.md) — case shell and other Case View sub-resources
- [See what changed on a case](../common-use-cases/keep-cases-current/sync-case-history.md) — hearings history and other case history endpoints
- [Update a case once](../common-use-cases/keep-cases-current/update-a-case-once.md) / [Track a case on a schedule](../common-use-cases/keep-cases-current/track-a-case-on-a-schedule.md) — refresh hearing data from the court
