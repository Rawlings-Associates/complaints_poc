---
title: "Normalization"
source: https://dart.unicourt.com/res-deep/assets/deep-v3-api-doc/knowledge-base/normalization-docs/
retrieved: 2026-10-01
---

# Normalization

## Introduction

The UniCourt database is derived from several hundred disparate data sources. To maximize the utility we can offer to our clients, we have normalized a host of data fields across the database so that like-for-like comparisons and searches can be performed over all of our data sets.

### What is Normalization?

Within our database, the purpose of our normalization is to take disparate nomenclature between hundreds of different data sources, and when those data sources are using different wording to describe the same concept, we give that set of terms one unique term and immutable identifier across the entire dataset. Those identifiers use fixed object ID prefixes—see [Object ID Prefixes](../knowledge-base/object-id-prefixes.md).

An example would be case type - one court portal could assign the case type **"Civil - Contract"** while another would use **"Business - Contract"**. To alleviate the difficulties this could present in finding the information our customers require, we normalize many of these features. With case types, we have a four-tiered classification structure, each layer of which has a unique and immutable identifier. In the **“Civil - Contract”/”Business - Contract”** example, we have normalized such cases as follows:

- Case Class - **"Civil"**
- Area of Law - **"Commercial and Trade"**
- Case Type Group - **"Contract"**
- Case Type - **"Contract"**

We normalize a host of features from court portals, which can be viewed in our [**UniCourt Data Standards UI**](#). As well as the normalization of these "case features", we also normalize what we refer to as "entities" across jurisdictions.

## Entity Normalization

### Introduction

A particularly challenging aspect of normalization across our database involves the legal entities or individuals, each of which we call **"entities"**. At a high level, the goal of this **"entity normalization"** is to understand when an attorney, law firm, judge, or party involved in one case, or included in another database is in fact the exact same as one involved elsewhere in our data set.

This functionality is of utmost importance when one uses legal data to make conclusions about the behavior or performance of a participant in litigation. For example, if I am an attorney who knows that the opposing counsel is **"John J Smith"**, I may want to view all the other litigation this attorney has been involved in and study his behavior. The inclusion of every other **"John Smith"** practicing in a given state would cloud the judgments I could make which may lead to misleading conclusions.

In practice, this process involves two processes: (1) creating a reliable source of truth, and (2) linking the contents of case data to that reliable source of truth. For attorneys, for example, we have collected data from 49 out of 50 state bar associations. To create a reliable source of truth, we first use our statistical techniques to decide which attorneys are barred in more than one state and, therefore, should be aggregated into a single cluster in our bar database.

As our case data comes from several hundred individual sources, the naming convention for attorneys and the data fields available can vary hugely. We extract as many data features as possible from each of these so-called **"case entities"** and then perform another round of analysis to allocate them to our source of truth.

### Norm Entities

As we are using sophisticated analytical techniques, the output of our process is a probability that two or more individuals or legal entities are the same. Where we have absolute certainty that they are, in fact, the same, we introduce the concept of a **"norm entity"** (short for a normalized entity). Each "norm entity" has a unique and immutable ID and is composed of one or more non-normalized entities clustered together.

There are instances, however, where we believe that two norm entity clusters could be the same individual but the probability thereof is less than 100%. In these circumstances, we describe these norm entities as being "similar norm entities" and provide a confidence score that allows one to assess how certain we are that the entities are the same.

### Example: Looking at a Norm Attorney Profile

There are a variety of ways you locate a normalized entity in UniCourt's data, including obtaining those details from a case object response, or matching your internal data on that entity to that of UniCourt's. In this example, we have obtained a `normAttorneyId` for a normalized attorney. In order to get details for that normalized attorney, we must use the [**/workspace/{workspaceId}/normAttorney/{normAttorneyId}**](#) endpoint.

**Request Parameters You Need**

- `normAttorneyId`: Pass the targeted normAttorneyId you're looking for. For instance, **QATTM0VnRF4w4MBLEQ**
- `accessToken`: Use the JWT accessToken as the Bearer token in your request header.

**Here's the request**

- cURL-Bash
- cURL-Powershell
- cURL-CMD

Norm Attorneys Request

```Shell
curl -X 'GET' \  'https://deep-api.unicourt.com/workspace/{workspaceId}/normAttorney/QATTM0VnRF4w4MBLEQ' \  -H 'accept: application/json' \  -H 'Authorization: Bearer <your JWT accessToken>'
```

Norm Attorneys Request

```Shell
ccurl.exe -X 'GET' `  'https://deep-api.unicourt.com/workspace/{workspaceId}/normAttorney/QATTM0VnRF4w4MBLEQ' `  -H 'accept: application/json' `  -H 'Authorization: Bearer <your JWT accessToken>'
```

Norm Attorney Request

```Shell
curl -X "GET" ^  "https://deep-api.unicourt.com/workspace/{workspaceId}/normAttorney/QATTM0VnRF4w4MBLEQ" ^  -H "accept: application/json" ^  -H "Authorization: Bearer <your JWT accessToken>"
```

**Response to the above query**

Norm Attorney Response

```json
{  "object": "NormAttorney",  "normAttorneyId": "QATTM0VnRF4w4MBLEQ",  "name": "Warren Carpenter Osgood",  "contact": {    "object": "NormAttorneyContact",    "contactLocationArray": [      {        "object": "Contact",        "addressArray": [          {            "object": "Address",            "streetAddress1": "PO BOX 691477",            "streetAddress2": null,            "city": "STOCKTON",            "stateName": "CALIFORNIA",            "stateCode": "CA",            "countryName": "UNITED STATES OF AMERICA",            "countryCode": "US",            "zip": "95269",            "zip4": null,            "isVisible": false,            "firstFetchDate": "2018-03-03T00:00:00+00:00",            "lastFetchDate": "2019-05-13T00:00:00+00:00",            "latitude": null,            "longitude": null          },          {            "object": "Address",            "streetAddress1": "10608 HIDDEN GROVE CIR",            "streetAddress2": "WARREN OSGOOD",            "city": "STOCKTON",            "stateName": "CALIFORNIA",            "stateCode": "CA",            "countryName": "UNITED STATES OF AMERICA",            "countryCode": "US",            "zip": "95209",            "zip4": "4222",            "isVisible": false,            "firstFetchDate": "2019-05-17T00:00:00+00:00",            "lastFetchDate": "2023-08-20T14:22:38+00:00",            "latitude": null,            "longitude": null          }        ],        "phoneNumberArray": [          {            "object": "Phone",            "phoneNumber": "209-477-4040",            "phoneType": "FAX",            "isVisible": false,            "firstFetchDate": "2022-08-04T12:21:18+00:00",            "lastFetchDate": "2023-08-20T14:22:38+00:00"          },          {            "object": "Phone",            "phoneNumber": "(209) 518-1272",            "phoneType": "PHONE",            "isVisible": false,            "firstFetchDate": "2020-06-28T06:35:53+00:00",            "lastFetchDate": "2020-06-28T06:35:53+00:00"          }        ],        "emailArray": [          {            "object": "Email",            "emailId": "osgoodwarren@gmail.com",            "isVisible": true,            "firstFetchDate": "2019-05-13T00:00:00+00:00",            "lastFetchDate": "2026-03-06T11:32:29+00:00"          }        ]      }    ],    "otherNamesArray": [],    "currentName": {      "prefix": null,      "name": "Warren Carpenter Osgood",      "firstName": "Warren",      "middleName": "Carpenter",      "lastName": "Osgood",      "suffix": null    },    "websiteArray": [],    "bio": null  },  "barMembershipAndStatusArray": [    {      "stateCode": "CA",      "barNumber": "141169",      "admittedDate": "1989-06-06T00:00:00+00:00",      "barMembershipStatus": {        "status": "Inactive",        "asOnDate": null      },      "firstFetchDate": "2018-03-03T00:00:00+00:00",      "lastFetchDate": "2026-03-06T11:32:29+00:00"    }  ],  "disciplinaryHistoryArray": [],  "lawSchoolArray": [    {      "lawSchool": "Santa Clara Univ SOL; Santa Clara CA",      "lawSchoolGraduatedDate": null,      "lawSchoolGraduatedYear": null,      "lawSchoolGraduatedMonth": null    }  ],  "employmentRecordArray": [],  "barRecordArray": [    {      "object": "BarRecord",      "barNumber": "141169",      "barSourceType": "state_bar",      "admittedDate": "1989-06-06T00:00:00+00:00",      "stateCode": "CA",      "status": "Inactive",      "inactivationDate": "2018-11-29T00:00:00+00:00",      "barSourceData": {        "object": "BarSourceData",        "administrativeActionsArray": [],        "admissionType": null,        "appellateCourtDistrict": null,        "appellateDivisionDepartment": null,        "attorneyGroup": null,        "authorized": null,        "barServiceClass": null,        "bio": null,        "boardCertificationsArray": [],        "boardDistrict": null,        "circuit": null,        "comments": null,        "committeesArray": [],        "courtHistoryArray": [],        "courtOfAdmissions": null,        "courtServiceEmail": null,        "disciplinaryHistoryArray": [],        "disciplineSummariesArray": [],        "dismissalsArray": [],        "district": null,        "employmentHistoryArray": [],        "expirationDate": null,        "feesOptionsArray": [],        "firmSize": null,        "firmWebsite": null,        "firstAdmittedDate": null,        "firstAdmittedYear": null,        "homeCounty": null,        "inGoodStanding": null,        "insurance": null,        "involvementsArray": [],        "judicialDistrict": null,        "jurisType": null,        "languagesArray": [],        "lastRenewalDate": null,        "lawSchoolArray": [          {            "lawSchool": "Santa Clara Univ SOL; Santa Clara CA",            "lawSchoolGraduatedDate": null,            "lawSchoolGraduatedYear": null,            "lawSchoolGraduatedMonth": null          }        ],        "legalSpecialityArray": [],        "licenseType": null,        "name": {          "name": "Warren Carpenter Osgood",          "firstName": "Warren",          "middleName": "Carpenter",          "lastName": "Osgood",          "prefix": null,          "suffix": null        },        "nextRegistration": null,        "nextRenewalDate": null,        "openActionStatusArray": [],        "otherJurisdictionArray": [],        "otherNameArray": [],        "parish": null,        "pendingProceedingArray": [],        "position": null,        "practiceAreaArray": [],        "practiceLocationArray": [],        "privateLawPractice": null,        "profileLastCertified": null,        "publicHearingArray": [],        "reasonForInactivation": null,        "sectionsArray": [],        "servicesArray": [],        "sourceInfo": {          "url": "https://apps.calbar.ca.gov/attorney/Licensee/Detail/141169"        },        "statewideGrievanceCommitteeHistoryArray": [],        "status": "Inactive",        "statusDate": null,        "statusHistoryArray": [          {            "statusChange": "Inactive",            "effectiveDate": null          },          {            "statusChange": "Inactive",            "effectiveDate": "2018-11-29T00:00:00+00:00"          },          {            "statusChange": "Admitted to the State Bar of California",            "effectiveDate": "1989-06-06T00:00:00+00:00"          }        ],        "tenYearDisciplineArray": [],        "undergraduateSchool": null,        "barLawFirm": null,        "yearsOfPractice": null,        "clientsRepresentedArray": [],        "statusHint": null,        "advancedDegreeArray": [],        "barStatusArray": [],        "relatedCasesArray": []      },      "contact": {        "object": "Contact",        "addressArray": [          {            "object": "Address",            "streetAddress1": "PO BOX 691477",            "streetAddress2": null,            "city": "STOCKTON",            "stateName": "CALIFORNIA",            "stateCode": "CA",            "countryName": "UNITED STATES OF AMERICA",            "countryCode": "US",            "zip": "95269",            "zip4": null,            "isVisible": false,            "firstFetchDate": "2018-03-03T00:00:00+00:00",            "lastFetchDate": "2019-05-13T00:00:00+00:00",            "latitude": null,            "longitude": null          },          {            "object": "Address",            "streetAddress1": "10608 HIDDEN GROVE CIR",            "streetAddress2": "WARREN OSGOOD",            "city": "STOCKTON",            "stateName": "CALIFORNIA",            "stateCode": "CA",            "countryName": "UNITED STATES OF AMERICA",            "countryCode": "US",            "zip": "95209",            "zip4": "4222",            "isVisible": false,            "firstFetchDate": "2019-05-17T00:00:00+00:00",            "lastFetchDate": "2023-08-20T14:22:38+00:00",            "latitude": null,            "longitude": null          }        ],        "phoneNumberArray": [          {            "object": "Phone",            "phoneNumber": "(209) 477-4040",            "phoneType": "FAX",            "isVisible": false,            "firstFetchDate": "2019-05-13T00:00:00+00:00",            "lastFetchDate": "2020-06-28T06:35:53+00:00"          },          {            "object": "Phone",            "phoneNumber": "(209) 518-1272",            "phoneType": "PHONE",            "isVisible": false,            "firstFetchDate": "2020-06-28T06:35:53+00:00",            "lastFetchDate": "2020-06-28T06:35:53+00:00"          },          {            "object": "Phone",            "phoneNumber": "209-477-4040",            "phoneType": "FAX",            "isVisible": false,            "firstFetchDate": "2022-08-04T12:21:18+00:00",            "lastFetchDate": "2023-08-20T14:22:38+00:00"          }        ],        "emailArray": [          {            "object": "Email",            "emailId": "osgoodwarren@gmail.com",            "isVisible": true,            "firstFetchDate": "2019-05-13T00:00:00+00:00",            "lastFetchDate": "2026-03-06T11:32:29+00:00"          }        ]      },      "firstFetchDate": "2018-03-03T00:00:00+00:00",      "lastFetchDate": "2026-03-06T11:32:29+00:00",      "lastFetchDateWithUpdates": "2024-03-07T03:05:11+00:00"    }  ],  "idEvolutionAPI": null,  "lastIdEvolutionDate": null,  "lastFetchDate": "2026-03-06T11:32:29+00:00",  "lastFetchDateWithUpdates": "2024-03-07T03:05:11+00:00"}
```

In the response above, we obtain the **`normAttorney`** details for a specifically requested **`normAttorneyId`**, such as their bar information and last date their UniCourt profile was updated. To find all the cases that this norm attorney has been involved in, the resulting normAttorneyId can be used as an input field for the [**/workspace/{workspaceId}/searchCases**](#) endpoint.
