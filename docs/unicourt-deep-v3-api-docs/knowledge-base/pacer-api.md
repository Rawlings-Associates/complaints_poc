---
title: "PACER API"
source: https://dart.unicourt.com/res-deep/assets/deep-v3-api-doc/knowledge-base/pacer-api/
retrieved: 2026-10-01
---

# PACER API

PACER (Public Access to Court Electronic Records) is the U.S. federal courts' paid access system. DEEP minimizes PACER charges by reusing cases UniCourt has already extracted, and exposes PACER-specific endpoints when you need to import or search cases not yet in the database.

See [Import a case from PACER](../common-use-cases/find-and-read-cases/import-a-case-from-pacer.md) for a full PACER import walkthrough.

## When to use which API

| Goal | Prefer | Notes |
| --- | --- | --- |
| Find a federal case UniCourt may already have | [Case Search](../getting-started/what-you-can-do-with-deep.md) — **GET /workspace/{workspaceId}/caseSearch** | Normalized data; no direct PACER login per search |
| Import a case by PACER case number + court | **GET /workspace/{workspaceId}/pacer/importCaseByCourtUsingCaseNumber** | Hits the court site; may incur PACER fees |
| Search PACER Case Locator (PCL) by party or case | **GET /workspace/{workspaceId}/pacerCaseLocator/…** | Cross-court PCL search; requires PACER credentials |
| Refresh a federal case | [Case Update](../knowledge-base/case-update.md) — **PUT /workspace/{workspaceId}/caseUpdate** | Requires `pacerOptions.pacerUserId` |
| Order PACER documents | [Document Orders](../knowledge-base/document-orders.md) | Requires PACER credentials on chargeable orders |
| Export an existing case | [Case Export](../knowledge-base/case-export.md) | No PACER credentials required |

For cases already in UniCourt, read **GET /workspace/{workspaceId}/case/{caseId}** first before triggering a paid PACER update.

### UniCourt federal coverage (summary)

UniCourt continuously extracts new federal cases and schedules refresh updates. If your case falls within this coverage, **caseSearch** is usually cheaper and returns normalized fields.

| Court system | Data since (approx.) | Extraction |
| --- | --- | --- |
| U.S. District Courts | 2018 | Daily + 60-day refresh |
| U.S. Courts of Appeals | 2019 | Daily + 60-day refresh |
| U.S. Bankruptcy Courts | 2019 | Daily + 60-day refresh |
| U.S. Court of International Trade | 2022 | Daily + 60-day refresh |
| U.S. Court of Federal Claims | 2022 | Daily + 60-day refresh |
| JPML | 2022 | Daily + 60-day refresh |

Resolve **`courtId`** values via [**Data Standards**](#) or master data APIs.

## Multi-Factor Authentication (MFA)

From mid-2025, the Administrative Office of the U.S. Courts is rolling out MFA on CM/ECF and PACER. CM/ECF-level accounts will require MFA; PACER-only viewing accounts may keep MFA optional.

To use chargeable PACER features through DEEP when MFA is enabled:

1. Log in to PACER → **Manage My Account** → enroll in **Multifactor Authentication**.
2. Under **Authentication Apps**, add an app and obtain the **secret key** from email.
3. Register the app (for example, "UniCourt MFA Application") and copy the generated **MFA Secret Key**.
4. Store that key in UniCourt via the [PACER Credentials API](#pacer-credentials-api) as **`pacerMFASecretKey`**.

Use Google Authenticator, Authy, or a compatible TOTP app to complete PACER enrollment.

## PACER credentials

Register credentials on your account before PACER import, PCL search, case update, or document order calls that bill against your PACER account.

**Web app:** Settings → PACER Credentials → validate User ID, password, client code (if required), and MFA secret key when applicable.

### PACER Credentials API

| Method | Path | Description |
| --- | --- | --- |
| PUT | `/pacerCredential` | Add or update credentials (`addPacerCredential`) |
| GET | `/pacerCredential` | List credentials (`getPacerCredential`) |
| GET | `/pacerCredential/{pacerUserId}` | Get one credential (`getPacerCredentialById`) |
| DELETE | `/pacerCredential/{pacerUserId}` | Remove credentials (`removePacerCredentialById`) |

| Request field | Required | Description |
| --- | --- | --- |
| `pacerUserId` | Yes | PACER login ID |
| `password` | Yes | PACER password (8–45 characters) |
| `defaultPacerClientCode` | Conditional | Required when PACER billing preferences mandate a client code |
| `pacerMFASecretKey` | Conditional | 32-character MFA secret when MFA is enabled |

Add PACER credentials

```Shell
curl -X 'PUT' \  'https://deep-api.unicourt.com/pacerCredential' \  -H 'accept: application/json' \  -H 'Authorization: Bearer <Your JWT accessToken>' \  -H 'Content-Type: application/json' \  -d '{  "pacerUserId": "<your pacerUserId>",  "defaultPacerClientCode": "<your PacerClientCode>",  "password": "<your password>",  "pacerMFASecretKey": "<your MFA secret key>"}'
```

Success response

```json
{  "object": "Success",  "message": "Added Successfully."}
```

**Client code rules:** No spaces; up to 32 characters from `A–Z`, `a–z`, `0–9`, `.`, `_`, `-`, `/`. Mandatory when PACER's **Require Client Code?** billing preference is **Yes**.

**Password rotation:** PACER passwords expire every **180 days**. After changing your PACER password, **DELETE** then **PUT** credentials in DEEP (or update via the web app) so imports and updates continue to authenticate.

Pass **`pacerUserId`** (and **`pacerClientCode`** when required) on each PACER import or PCL search request. You may register multiple PACER accounts per workspace.

## PACER import by court and case number

Use [**GET /workspace/{workspaceId}/pacer/importCaseByCourtUsingCaseNumber**](#) when you know the **`caseNumber`** and **`courtId`**.

Required query parameters: **`pacerUserId`**, **`caseNumber`**, **`courtId`**. Optional: **`pacerClientCode`**.

PACER import request

```Shell
curl -X 'GET' \  'https://deep-api.unicourt.com/workspace/{workspaceId}/pacer/importCaseByCourtUsingCaseNumber?pacerUserId=<your pacerUserId>&pacerClientCode=<your pacerClientCode>&caseNumber=2:10-cv-00001&courtId=CORTjF63b8Z4d2i9UB' \  -H 'accept: application/json' \  -H 'Authorization: Bearer <Your JWT accessToken>'
```

PACER import response (excerpt)

```json
{  "object": "PACERImportCase",  "courtFee": 0.1,  "pacerImportCaseResultsArray": [    {      "object": "PACERImportCaseResults",      "hasOnlyMetaInfo": false,      "uniCourtContent": {        "object": "CaseSearchResult",        "caseId": "CASEgtaa7e66390d69",        "caseNumber": "2:10-cv-00001",        "caseName": "Rob J. Simmons v. California State Parole",        "caseAPI": "/workspace/{workspaceId}/case/CASEgtaa7e66390d69"      }    }  ]}
```

**Workflow:**

1. Import returns find-case metadata (and **`courtFee`** when the court charges for the lookup).
2. Call [Case Update](../knowledge-base/case-update.md) with the returned **`caseId`** and `pacerOptions` to pull the full docket.

Find-case in district, bankruptcy, and national courts is typically free; appeal-court find-case may incur a minimum charge (see **`courtFee`** in the response).

## PACER Case Locator (PCL)

PCL endpoints search across PACER by party name or case attributes. Paths follow:

- **Case search:** `/workspace/{workspaceId}/pacerCaseLocator/caseSearch/{courtGroup}`
- **Party search:** `/workspace/{workspaceId}/pacerCaseLocator/partySearch/{courtGroup}`

**`courtGroup`** values: `allCourts`, `appealCourts`, `bankruptcyCourts`, `civilCourts`, `criminalCourts`, `multiDistrictCourts`.

All PCL calls require **`pacerUserId`** (and **`pacerClientCode`** when your PACER account requires it). See the [**Case Search API spec**](#) for full query parameters (`lastName`, `caseNumber`, `caseTypeArray`, `courtRegionIdArray`, `caseFiledStartDate`, etc.).

PCL civil party search (excerpt)

```Shell
curl -X 'GET' \  'https://deep-api.unicourt.com/workspace/{workspaceId}/pacerCaseLocator/partySearch/civilCourts?pacerUserId=<your pacerUserId>&pacerClientCode=<your pacerClientCode>&lastName=Smith&firstName=John&pageNumber=1' \  -H 'accept: application/json' \  -H 'Authorization: Bearer <Your JWT accessToken>'
```

Responses include **`pacerSearchResultsArray`**, billing metadata in **`pacerReceipt`**, pagination in **`pacerPageInfo`**, and normalized **`uniCourtContent`** when UniCourt already holds the case. Use **`nextPageAPI`** for additional pages.

## Case update and PACER options

When updating federal cases, pass **`pacerOptions.pacerUserId`** on [Case Update](../knowledge-base/case-update.md) and [Case Track](../knowledge-base/case-track.md) requests. Use root-level **`fetchParticipantsIfOlderThanDays`** and **`fetchType`** (not nested under `pacerOptions` in v3) to control participant refresh cost.

## Migration Notes for v2 Integrators

PACER import and Case Locator endpoints are workspace-scoped in v3. PACER **credential** endpoints remain account-scoped (same path shape as v2, on `deep-api.unicourt.com`).

| v2 Endpoint | v3 Endpoint |
| --- | --- |
| `PUT /pacerCredential` | `PUT /pacerCredential` |
| `GET /pacerCredential` | `GET /pacerCredential` |
| `GET /pacerCredential/{pacerUserId}` | `GET /pacerCredential/{pacerUserId}` |
| `DELETE /pacerCredential/{pacerUserId}` | `DELETE /pacerCredential/{pacerUserId}` |
| `GET /pacer/importCaseByCourtUsingCaseNumber` | `GET /workspace/{workspaceId}/pacer/importCaseByCourtUsingCaseNumber` |
| `GET /pacerCaseLocator/caseSearch/{courtGroup}` | `GET /workspace/{workspaceId}/pacerCaseLocator/caseSearch/{courtGroup}` |
| `GET /pacerCaseLocator/partySearch/{courtGroup}` | `GET /workspace/{workspaceId}/pacerCaseLocator/partySearch/{courtGroup}` |

| v2 Field / Endpoint | v3 Field / Endpoint | Notes |
| --- | --- | --- |
| `https://enterpriseapi.unicourt.com/…` | `https://deep-api.unicourt.com/…` | Base URL change; workspace prefix on import/PCL (not on credential paths) |
| `caseAPI` paths without workspace | `/workspace/{workspaceId}/case/{caseId}` | Follow workspace-scoped case view paths |
| `pacerOptions.refreshType` on update/track | Root `fetchType` (`INCREMENTAL` / `FULL`) | See [Case Update](../knowledge-base/case-update.md#migration-notes-for-v2-integrators) |

PACER credential field names (`pacerUserId`, `defaultPacerClientCode`, `password`, `pacerMFASecretKey`) are unchanged in v3.
