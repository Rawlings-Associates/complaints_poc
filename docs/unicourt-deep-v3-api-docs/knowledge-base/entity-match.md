---
title: "Entity Match"
source: https://dart.unicourt.com/res-deep/assets/deep-v3-api-doc/knowledge-base/entity-match/
retrieved: 2026-10-01
---

# Entity Match

The Entity Match APIs fuzzy-match imperfect attorney and law firm records—inconsistent spellings, partial names, missing bar details—to UniCourt’s **normalized** entities. Unlike [Entity Search](../common-use-cases/entities-and-counsel/search-for-an-entity.md#when-to-use-entity-search-instead) (`normAttorneySearch` / `normLawFirmSearch`), which keyword-queries UniCourt’s entity index, Entity Match takes *your* identifying fields, scores candidates, and returns ranked results with **`confidenceScore`**, **`bestMatch`**, and **`scoreConstituents`** so you can decide which norm ID to accept.

Use Entity Match when you need to map CRM contacts, opposing counsel lists, panel counsel, or claims data to UniCourt’s clean, standardized, structured attorney and firm profiles—especially when your source data is incomplete or inconsistently formatted.

See [Search for and Match your Entity](../common-use-cases/entities-and-counsel/search-for-an-entity.md) for a walkthrough (match → profile, or search).

For how normalization works end to end, see [Normalization](../knowledge-base/normalization-docs.md). For counsel structure on cases, see [Understanding the Counsel Object](../knowledge-base/understanding-the-counsel-object.md). Normalized entity IDs use fixed prefixes (`QATT`, `QLAW`)—see [Object ID Prefixes](../knowledge-base/object-id-prefixes.md).

## Endpoints

| Method | Path | Description |
| --- | --- | --- |
| GET | `/workspace/{workspaceId}/normAttorneyMatch` | Match an attorney record to possible `normAttorneyId` values |
| GET | `/workspace/{workspaceId}/normLawFirmMatch` | Match a law firm record to possible `normLawFirmId` values |

Spec reference: [**Entity Search API**](#).

## Matching an attorney

**GET** [**/workspace/{workspaceId}/normAttorneyMatch**](#).

Provide either **`fullName`** or **`firstName`** + **`lastName`** (`middleName` optional). Pass every reliable identifier you have—extra context improves disambiguation.

### Request parameters

| Parameter | Required | Description |
| --- | --- | --- |
| `fullName` | One of name options | Full attorney name (for example `MICHAEL SCOTT HUNT`). |
| `firstName` + `lastName` | One of name options | Split name fields; optional `middleName`. |
| `barredState` | When sending `barNumber` | Two-letter state where the attorney is barred (for example `CA`). |
| `barNumber` | No | Bar number in that state. **`barredState` is required when you send `barNumber`**. |
| `lawFirmList` | No | One or more firm names associated with the attorney. |
| `emailList` | No | One or more email addresses. |
| `phoneList` | No | One or more phone numbers. |
| `addressList` | No | One or more street addresses. |

Match an attorney

```Shell
curl -X 'GET' \  'https://deep-api.unicourt.com/workspace/{workspaceId}/normAttorneyMatch?fullName=MICHAEL%20SCOTT%20HUNT&barredState=CA&barNumber=99804' \  -H 'accept: application/json' \  -H 'Authorization: Bearer <Your JWT accessToken>'
```

### Response: NormAttorneyMatchResponse

Excerpt — NormAttorneyMatchResponse

```json
{  "object": "NormAttorneyMatchResponse",  "name": "MICHAEL SCOTT HUNT",  "possibleNormAttorneyArray": [    {      "object": "PossibleNormAttorneyMatch",      "normAttorneyId": "QATTSJ709tX66v8KJ2",      "normAttorneyName": "MICHAEL SCOTT HUNT",      "bestMatch": true,      "confidenceScore": 1,      "scoreConstituents": {        "nameSimilarityScore": 1,        "barId": "Not_Provided_By_Data_Source",        "address": "Matched",        "email": "Matched",        "phone": "Matched",        "lawFirm": "Matched"      },      "normAttorneyAPI": "/workspace/{workspaceId}/normAttorney/QATTSJ709tX66v8KJ2"    }  ]}
```

| Field | Description |
| --- | --- |
| `name` | Echo of the name used for matching. |
| `possibleNormAttorneyArray` | Ranked candidate matches (`PossibleNormAttorneyMatch`). |

#### `PossibleNormAttorneyMatch`

| Field | Description |
| --- | --- |
| `normAttorneyId` / `normAttorneyName` | Normalized attorney identity. |
| `bestMatch` | `true` on UniCourt’s preferred candidate when multiple results exist. |
| `confidenceScore` | Match confidence (0.0–1.0). See [Confidence scores](#confidence-scores). |
| `scoreConstituents` | Breakdown of what drove the score. |
| `normAttorneyAPI` | Relative path to the normalized attorney profile. |

## Matching a law firm

**GET** [**/workspace/{workspaceId}/normLawFirmMatch**](#).

**`name`** is required. Optionally pass **`state`**, **`emailList`**, **`phoneList`**, or **`addressList`**. Scoring and selection practices are the same as for attorneys—results appear in **`possibleNormLawFirmArray`**.

Match a law firm

```Shell
curl -X 'GET' \  'https://deep-api.unicourt.com/workspace/{workspaceId}/normLawFirmMatch?name=GORDON%20REES&state=CA' \  -H 'accept: application/json' \  -H 'Authorization: Bearer <Your JWT accessToken>'
```

#### `PossibleNormLawFirmMatch` score constituents

Law firm candidates expose **`nameSimilarityScore`**, **`address`**, **`email`**, and **`phone`** (Matched / Mismatched / Not_Provided_By_Data_Source). There is no `barId` or `lawFirm` constituent on firm matches.

## Confidence scores

On Entity Match (attorneys and law firms), **`confidenceScore`** combines data quality with uniqueness:

```text
confidenceScore = similarityScore / n
```

where **`n`** is the total number of candidates returned. A high similarity against a unique candidate scores higher than the same similarity split across several candidates.

### Similarity score tiers

Before dividing by `n`, the API assigns each candidate a baseline **similarity score**:

| Similarity score | Meaning |
| --- | --- |
| **1.0** | **Attribute match** — an explicit profile attribute matched (for example email, phone, bar ID, or law firm) |
| **0.8** | **Identical name match** — perfect textual name match, but no secondary identifying attributes matched |
| **0.5** | **Name match only** — standard or partial name match with no secondary attribute validation |

### How to read common confidence scores

Because the final score is diluted by `n`, common values map to predictable scenarios:

| Confidence score | Matches (`n`) | Typical scenario |
| --- | --- | --- |
| **1.0** | 1 | Unique attribute match — one entity, validated by a strong attribute |
| **0.8** | 1 | Unique exact name match — one entity with an identical name, no secondary attributes |
| **0.5** | 2 | Attribute split — a strong attribute matched, but it is shared by two profiles |
| **0.5** | 1 | Unique partial name match — one entity, name-only similarity |
| **0.4** | 2 | Identical name split — two entities share the exact same name, no tie-breaker attributes |

### scoreConstituents

Use **`scoreConstituents`** alongside **`confidenceScore`** to see *why* a candidate scored as it did.

**Attorneys (`PossibleNormAttorneyMatch`):**

| Field | Meaning |
| --- | --- |
| **`nameSimilarityScore`** | Composite syntactic name similarity (higher is better) |
| **`barId`** | `Matched`, `Mismatched`, or `Not_Provided_By_Data_Source` |
| **`lawFirm`**, **`phone`**, **`email`**, **`address`** | Same matched / mismatched / not-provided values |

**Law firms (`PossibleNormLawFirmMatch`):** `nameSimilarityScore`, `address`, `email`, and `phone` only.

bestMatch

The API sets **`bestMatch: true`** on UniCourt’s preferred candidate. Treat that as a hint—confirm with **`confidenceScore`**, **`scoreConstituents`**, and profile review when more than one row is present.

**Trade-off:** Accepting lower confidence scores can reduce false negatives (missing the right entity) but may increase false positives. Tune thresholds on your own labeled sample.

## Entity Match vs Entity Search

| Use… | When… |
| --- | --- |
| **Entity Match** (`normAttorneyMatch` / `normLawFirmMatch`) | You are resolving *one* internal attorney or firm record to a UniCourt `normAttorneyId` / `normLawFirmId`, and inputs may be incomplete, mistyped, or inconsistently formatted. Typical next step: read the [entity profile](../common-use-cases/entities-and-counsel/read-an-entity-profile.md). |
| **Entity Search** (`normAttorneySearch` / `normLawFirmSearch`) | You have clean keyword filters and need to browse or query UniCourt’s entity directory (result sets with `q` expressions)—not link a stored CRM/claims record. |

v3 Entity Search covers **attorneys and law firms only** (v2 judge/party search endpoints are removed).

## After you accept a match

Store **`normAttorneyId`** or **`normLawFirmId`** on your internal record, then:

- Load the profile via **`normAttorneyAPI`** / **`normLawFirmAPI`** — [Read an entity profile](../common-use-cases/entities-and-counsel/read-an-entity-profile.md)
- Find associated cases with Case Search `q` filters on those IDs — [Search for cases](../common-use-cases/find-and-read-cases/search-for-cases.md) and [Query Builders](../knowledge-base/query-builders.md)
- Aggregate activity with Analytics View — [Analyze counsel activity](../common-use-cases/analyze/analyze-counsel-activity.md)

**On case counsel:** Each counsel record includes at most one **`normAttorney`** or **`normLawFirm`** link—the best match UniCourt selected for that court-provided name. Those links do not expose confidence fields. Use Entity Match when you need candidate lists and scores for *your* data.

## Migration Notes for v2 Integrators

Conceptual behavior is unchanged: match your attorney/firm attributes to normalized entities and inspect confidence fields on the candidate array.

| v2 | v3 | Notes |
| --- | --- | --- |
| `/normAttorneyMatch` | `GET /workspace/{workspaceId}/normAttorneyMatch` | Workspace-scoped on `deep-api.unicourt.com` |
| `/normLawFirmMatch` | `GET /workspace/{workspaceId}/normLawFirmMatch` | Same pattern for firms |
| `normEntityId` (generic) | `normAttorneyId`, `normLawFirmId` | Use entity-specific IDs in search and analytics `q` expressions |
| `Attorney.possibleNormAttorneyArray` on a case | `Counsel.normAttorney` (single object) | v3 counsel carries one best-match link; full candidate lists with scores are on Entity Match responses |
| `Attorney.possibleNormLawFirmArray` on a case | `Counsel.normLawFirm` (single object) | Same pattern as attorneys |
| `/normJudgeSearch`, `/normPartySearch` | *(removed)* | v3 entity search/match covers attorneys and law firms only |
| `https://enterpriseapi.unicourt.com/…` | `https://deep-api.unicourt.com/workspace/{workspaceId}/…` | Base URL and workspace prefix |
