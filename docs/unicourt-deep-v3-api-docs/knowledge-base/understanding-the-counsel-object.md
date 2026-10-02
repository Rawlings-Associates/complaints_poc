---
title: "Understanding the Counsel Object"
source: https://dart.unicourt.com/res-deep/assets/deep-v3-api-doc/knowledge-base/understanding-the-counsel-object/
retrieved: 2026-10-01
---

# Understanding the Counsel Object

## What Changed

In prior versions of the UniCourt API, a case's legal representation was split across two separate concepts: an `Attorney` object, and a `attorneyLawFirmArray` nested inside each attorney to capture the firm(s) that attorney was associated with on the case. There was no standalone, case-level law firm entity. This design had some drawbacks, such as awkwardness representing a law firm without a named attorney.

In DEEP v3, attorneys and law firms are both represented by a single object type called **Counsel**. A Counsel object represents either an attorney or a law firm involved in a case, distinguished by its `counselType`. The Counsel object treats attorneys and law firms as peers of the same type, connected through explicit association objects rather than one being nested inside the other. This section explains what the Counsel object contains, how attorneys and law firms relate to each other and to parties, and how to work with it in your integration.

## The Counsel Object

Every Counsel object appears in a case's `counselList` and carries a `counselType` of `ATTORNEY`, `LAW_FIRM`, or `UNABLE_TO_DETERMINE`. A single Counsel object has exactly one `counselType`—never more than one. When a court record lists something like "John Smith at ACME Law Group" as a single unparsed string, UniCourt extracts both an attorney Counsel object and a law firm Counsel object, then links them through an association, described below.

Occasionally an `UNABLE_TO_DETERMINE` counsel string may in fact describe more than one entity (for example, an attorney and a firm that UniCourt could not confidently split). In those cases UniCourt may still emit a single Counsel object of type `UNABLE_TO_DETERMINE` rather than separate attorney and firm records.

Selected fields on the Counsel object (not exhaustive—see the [**Case View API spec**](#) for the full schema):

| Field | Description |
| --- | --- |
| `counselId` | Unique identifier for this counsel within the case. Prefixed `CNSL`—see [Object ID Prefixes](../knowledge-base/object-id-prefixes.md). |
| `name` | Name of the counsel as provided by the court. |
| `counselType` | `ATTORNEY`, `LAW_FIRM`, or `UNABLE_TO_DETERMINE`. |
| `counselRole` | The counsel's role in the case (for example, attorney of record). |
| `partyRoleGroupIdArray` | Party role group IDs for the representation this counsel is associated with (the party-side role group, not the counsel's own role). |
| `partyRoleIdArray` | Party role IDs for the representation this counsel is associated with (for example, plaintiff or defendant). |
| `barNumber` | Bar enrollment number, when available. Applicable to attorneys. |
| `dataSource` | Where this counsel record originated: `CASE_METADATA`, `DOCUMENT`, `DOCKET_ENTRY`, or `INFERRED`. |
| `normAttorney` | Normalized attorney reference, when this counsel is an attorney. At most one of `normAttorney` or `normLawFirm` is populated on a given Counsel object; the other is `null`. |
| `normLawFirm` | Normalized law firm reference, when this counsel is a law firm. At most one of `normAttorney` or `normLawFirm` is populated on a given Counsel object; the other is `null`. |
| `counselAssociations` | Links from this counsel to other counsel in the case (for example, an attorney linked to their firm). |
| `partyCounselAssociations` | Links from this counsel to the parties they represent. |
| `isVisible` | Whether this counsel is currently active/shown for the case. |

## How Counsel Relates to Parties and to Other Counsel

The Counsel object does not stand alone. It connects to other entities in the case through two association types:

**Party-Counsel Associations** link a counsel (attorney or law firm) to the party they represent. These live in `partyCounselAssociations` on the Counsel object, and the reverse reference lives in `partyCounselAssociations` on the Party object.

**Counsel Associations** link one counsel to another, most commonly an attorney to the law firm they practice at. These live in `counselAssociations` on the Counsel object.

Both association types carry a `dataSource` field, so you can tell whether a given relationship came directly from case metadata, was extracted from a document or docket entry, or was inferred by UniCourt.

`partyRoleIdArray` and `partyRoleGroupIdArray` describe the **party-side** of that representation: which party role(s) and role group(s) the counsel is tied to on the case. They are distinct from `counselRole`, which describes the counsel's own role (for example, lead counsel). A counsel who represents parties on more than one side of a case may have multiple IDs in these arrays.

### Counsel Object Creation Example

Consider a case where attorney Jane Doe represents Plaintiff Corp, and Jane Doe is affiliated with Smith & Associates.

1. UniCourt creates a Counsel object for Jane Doe, with `counselType: ATTORNEY`.
2. UniCourt creates a separate Counsel object for Smith & Associates, with `counselType: LAW_FIRM`.
3. A Counsel Association links Jane Doe's counsel record to Smith & Associates' counsel record.
4. A Party-Counsel Association links Jane Doe's counsel record to the Plaintiff Corp party record.

#### One Attorney, Multiple Firms

If Jane Doe changes firms partway through the case, UniCourt creates a second law firm Counsel object for her new firm and a second Counsel Association, rather than overwriting the first. Assuming the first firm, Smith & Associates, is no longer listed by the court, UniCourt will change its `isVisible` property to be `false` to reflect that. This way, you can see the full representation history.

## Retrieving Counsel Data

| Endpoint | Description |
| --- | --- |
| `GET /workspace/{workspaceId}/case/{caseId}/counsel` | List all counsel for a case. |
| `GET /workspace/{workspaceId}/counsel/{counselId}` | Retrieve a single counsel record. |
| `GET /workspace/{workspaceId}/counsel/{counselId}/associatedCounsel` | Retrieve counsel associated with a given counsel (for example, an attorney's firm). |
| `GET /workspace/{workspaceId}/counsel/{counselId}/associatedParties` | Retrieve parties associated with a given counsel. |
| `GET /workspace/{workspaceId}/party/{partyId}/associatedCounsel` | Retrieve counsel representing a given party. |

## Searching for Counsel Entities

Normalized attorneys and law firms each have their own dedicated search endpoints, separate from case-level counsel data:

| Endpoint | Description |
| --- | --- |
| `/workspace/{workspaceId}/normAttorneySearch` | Search normalized attorneys. |
| `/workspace/{workspaceId}/normLawFirmSearch` | Search normalized law firms. |

## Searching for Counsel’s Cases

To find cases involving counsel, use nested keyword expressions against the [**`caseSearch`**](#) endpoint. See [Query Builders](../knowledge-base/query-builders.md) for the general rules on nested property searching.

**By counsel name (attorneys and law firms).** A name-only filter matches any counsel whose `name` contains the term, including attorneys and firms:

```text
Counsel:(name:(Smith))
```

**By counsel name, excluding law firms.** To search as if for an attorney while still including ambiguous `UNABLE_TO_DETERMINE` records, exclude `LAW_FIRM` rather than requiring `ATTORNEY` alone:

```text
Counsel:(name:(Smith) NOT counselType:(LAW_FIRM))
```

**By normalized attorney or law firm.** Once you have a `normAttorneyId` or `normLawFirmId`, you can also filter `caseSearch` by that normalized entity:

```text
Counsel:(normAttorneyId:"QATTM0VnRF4w4MBLEQ")Counsel:(normLawFirmId:"QLAWkGfH3h68KV41hY")
```

## Migration Notes for v2 Integrators

If your integration currently reads `Case.attorneys`, the `attorneyId`, `attorneyType`, `possibleNormAttorneyArray`, and `possibleNormLawFirmArray` fields, or the `partyAttorneyAssociations` and `attorneyLawFirmArray` structures, these have all been replaced as part of the Counsel object. See the field mapping table below.

| v2 Field | v3 Field | Notes |
| --- | --- | --- |
| `Case.attorneys` | `Case.counselList` | Now contains both attorneys and law firms. |
| `attorneyId` | `counselId` |  |
| `attorneyType` | `counselRole` |  |
| `possibleNormAttorneyArray` | `normAttorney` | Now a single normalized object, not an array. |
| `possibleNormLawFirmArray` | `normLawFirm` | Now a single normalized object, not an array. |
| `partyAttorneyAssociations` | `partyCounselAssociations` |  |
| `attorneyLawFirmArray` | `counselAssociations` | Now a peer-to-peer counsel association, not a nested array on the attorney. |
| `namePrefix`, `firstName`, `middleName`, `lastName`, `nameSuffix` | *(removed)* | Counsel exposes the full court-sourced `name` string only; the old name-segregation fields on `Attorney` are not present. |
| `GET /case/{caseId}/attorneys` | `GET /workspace/{workspaceId}/case/{caseId}/counsel` | Also now workspace-scoped, on the new v3 base URL `deep-api.unicourt.com`. |
| `GET /party/{partyId}/associatedAttorneys` | `GET /workspace/{workspaceId}/party/{partyId}/associatedCounsel` | Also now workspace-scoped. |
