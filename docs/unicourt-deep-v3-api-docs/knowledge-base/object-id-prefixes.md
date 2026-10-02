---
title: "Object ID Prefixes"
source: https://dart.unicourt.com/res-deep/assets/deep-v3-api-doc/knowledge-base/object-id-prefixes/
retrieved: 2026-10-01
---

# Object ID Prefixes

Every UniCourt object ID starts with a fixed four-character prefix that identifies the object type. Use this page to look up what an ID refers to when you encounter one in a response or need to validate an ID before calling an endpoint.

For example, `CASEar7a26f15e76cf` is a case (`CASE`), and `CDOCbf91c3a2d4e1` is a case document (`CDOC`).

## How to read an object ID

| Part | Example | Description |
| --- | --- | --- |
| Prefix | `CASE` | Fixed four-character type identifier |
| Suffix | `ar7a26f15e76cf` | Opaque unique identifier for the instance |

Prefixes are stable. Branch on the prefix when you need to detect object type; do not parse the suffix.

## Prefix reference

### Court and master data

| Prefix | Field | Object |
| --- | --- | --- |
| `CORT` | `courtId` | Court |
| `CTSS` | `courtSourceId` | CourtSource |
| `TRSC` | `tentativeRulingSourceId` | TentativeRulingSource |
| `COTP` | `courtTypeId` | CourtType |
| `COSY` | `courtSystemId` | CourtSystem |
| `COLO` | `courtLocationId` | CourtLocation |
| `JUGO` | `jurisdictionGeoId` | JurisdictionGeo |
| `CSCL` | `caseClassId` | CaseClass |
| `AOFL` | `areaOfLawId` | AreaOfLaw |
| `CTYG` | `caseTypeGroupId` | CaseTypeGroup |
| `CTYP` | `caseTypeId` | CaseType |
| `CSSG` | `caseStatusGroupId` | CaseStatusGroup |
| `CSST` | `caseStatusId` | CaseStatus |
| `PTYG` | `partyRoleGroupId` | PartyRoleGroup |
| `PTYR` | `partyRoleId` | PartyRole |
| `CNRL` | `counselRoleId` | CounselRole |
| `JDRL` | `judgeRoleId` | JudgeRole |
| `CRTP` | `caseRelationshipTypeId` | CaseRelationshipType |
| `MTNC` | `motionTypeCategoryId` | MotionTypeCategory |
| `MTNG` | `motionTypeGroupId` | MotionTypeGroup |
| `MTNS` | `motionTypeId` | MotionType |
| `MOCG` | `motionOutcomeGroupId` | MotionOutcomeGroup |
| `MOCN` | `motionOutcomeId` | MotionOutcome |
| `PACG` | `proceduralActivityGroupId` | ProceduralActivityGroup |
| `PACT` | `proceduralActivityId` | ProceduralActivity |
| `CAEG` | `caseEventGroupId` | CaseEventGroup |
| `CAET` | `caseEventId` | CaseEvent |
| `CDSG` | `caseDispositionGroupId` | CaseDispositionGroup |
| `CDSN` | `caseDispositionId` | CaseDisposition |

### Case data

| Prefix | Field | Object |
| --- | --- | --- |
| `CASE` | `caseId` | Case |
| `PRTY` | `partyId` | Party |
| `CNSL` | `counselId`, `associatedCounselId` | Counsel |
| `DKTE` | `docketEntryId` | DocketEntry |
| `JUDG` | `judgeId` | Judge |
| `CDOC` | `caseDocumentId` | CaseDocument |
| `HRNG` | `hearingId` | Hearing |
| `TNTR` | `tentativeRulingId` | TentativeRulings |

### Analytics and normalized entities

| Prefix | Field | Object |
| --- | --- | --- |
| `QPTY` | `normPartyId` | NormParty |
| `QATT` | `normAttorneyId` | NormAttorney |
| `QJUD` | `normJudgeId` | NormJudge |
| `QLAW` | `normLawFirmId` | NormLawFirm |

### Account, workspace, and callbacks

| Prefix | Field | Object |
| --- | --- | --- |
| `CBDO` | `caseDocumentOrderCallbackId` | CaseDocumentOrderCallback |
| `CBCE` | `caseExportCallbackId` | CaseExportCallback |
| `CBCI` | `caseImportCallbackId` | CaseImportCallback |
| `TKID` | `tokenId` | AccessToken / AccessTokenIdResponse |
| `WTID` | `workspaceTemplateId` | WorkspaceTemplate |
| `WFID` | `workspaceTemplateFieldId` | WorkspaceTemplateField |
| `WKID` | `workspaceTokenId` | WorkspaceAccessToken |

### Search

| Prefix | Field | Object |
| --- | --- | --- |
| `CSRH` | `caseSearchId` | CaseSearch |
| `ASRH` | `normAttorneySearchId` | NormAttorneySearch |
| `LSRH` | `normLawFirmSearchId` | NormLawFirmSearch |
