---
title: "Python SDK"
source: https://dart.unicourt.com/res-deep/assets/deep-v3-api-doc/knowledge-base/python-sdk/
retrieved: 2026-10-01
---

# UniCourt Python SDK

Coming soon

The Python library and sample code documentation has been updated for DEEP v3. Guidance from earlier platform versions no longer applies.

The UniCourt SDK reduces the work required to use the DEEP v3 API from a Python application. Instead of building and authenticating raw HTTP requests yourself, the SDK gives you typed classes and methods, one per API resource, that handle the request and return a Python object you can work with directly.

At a high level, using the SDK looks like this:

1. Set your `CLIENT_ID` and `CLIENT_SECRET`, then call `Authentication.generate_new_token()` to authenticate. This also stores your `WORKSPACE_ID`, which every workspace-scoped call uses automatically.
2. Call a method on the class for the resource you need (for example, `CaseSearch.search_cases()` or `AttorneySearch.search_normalized_attorneys()`), passing any required parameters.
3. Each method returns a tuple: a response object with the data, and an HTTP status code.
4. When you're done, call `Authentication.invalidate_token()` to invalidate the access token.

The sections below cover installation, authentication, a full reference of available classes and methods, and troubleshooting.

## Requirements

- Python 3.11 or later

Python Version

The SDK requires Python 3.11+. Earlier versions of Python, which may be sufficient for other UniCourt tooling, will not work with this SDK. See [Troubleshooting](#troubleshooting) below if you need to upgrade.

## Installation

**Step 1:** Download the `.whl` file [here](#).

**Step 2:** Open your terminal or command prompt and install the downloaded file:

```bash
pip install path/to/downloaded_file.whl
```

Example:

```bash
pip install home/Downloads/unicourt-1.0-py3-none-any.whl
```

## Prerequisites and Configuration

You will find your `clientId` and `secret` on the [API Security](https://dart.unicourt.com/default/deep-v3/api-credentials) page.

## Getting Started

Copy the code below into a file (for example, `sample.py`) and run it from your terminal:

```bash
python sample.py
```

```python
import unicourtfrom unicourt import CaseMasterData, AttorneySearch, Authentication# Get CLIENT_ID and CLIENT_SECRET from your accountunicourt.CLIENT_ID = "your_client_id"unicourt.CLIENT_SECRET = "your_client_secret"# Authenticate to generate an access token. The line below returns# a tuple consisting of an authentication object and an HTTP status code.# You can generate up to 10 authentication tokens, so be sure to use# invalidate_token() once you are done, or store the token securely# and reuse it for subsequent requests.auth_obj, http_status_code = Authentication.generate_new_token()# Stores unicourt.WORKSPACE_ID; all workspace APIs use it automatically.# Get Area Of Law details.court_standards_obj, http_status_code = CaseMasterData.get_areas_of_law(        q='name:"Personal Injury"',        page_number=1,        sort="name",        order="asc",    )for court_standard_obj in court_standards_obj.area_of_law_array:    print("Area Of Law Id : ", court_standard_obj.area_of_law_id)# Get Attorney details.attorney_obj, http_status_code = AttorneySearch.search_normalized_attorneys(    q="name:(PURDY STUART JAMES)",    page_number=1,)for attorney in attorney_obj.norm_attorney_search_result_array:    print("Attorney Name :", attorney.name)    print("Norm Attorney Id :", attorney.norm_attorney_id)# Invalidate the generated access tokenAuthentication.invalidate_token()
```

## SDK and API Version Compatibility

SDK versions and DEEP API versions are versioned independently and do not map 1:1. A single SDK release may support one or more API versions, and a new API version does not always require a new SDK release. Check the table below to confirm which API version(s) your installed SDK version supports before upgrading either one.

| SDK Version | Supported API Version(s) | Download | Notes |
| --- | --- | --- | --- |
| 1.0 | `2026-07-15`, `2026-08-03` | [Download](#) | Initial private access release |

## UniCourt API Documentation for Python Library

Below is a list of all classes and methods available in the Python library. These correspond to DEEP v3 API endpoints. Methods are grouped by class for easier scanning. `workspace_id` is omitted from required parameters since the SDK injects `unicourt.WORKSPACE_ID` automatically after authentication.

### `Authentication`

| Method | Required Parameters | HTTP | Description |
| --- | --- | --- | --- |
| `generate_new_token` | — (optional: `client_id`, `client_secret`; falls back to `unicourt.CLIENT_ID` / `CLIENT_SECRET`) | POST | Generates a new token to access the API. |
| `invalidate_all_tokens` | — (optional: `client_id`, `client_secret`) | PUT | Invalidates all access tokens. |
| `invalidate_token` | `token_id` (optional: `client_id`, `client_secret`) | PUT | Invalidates a specific access token. |
| `list_all_token_ids` | — (optional: `client_id`, `client_secret`) | GET | Lists all access token IDs. |

### `AccountTokenManagement`

| Method | Required Parameters | HTTP | Description |
| --- | --- | --- | --- |
| `generate_new_token` | — | POST | Generates a new token to access the API. |
| `invalidate_all_tokens` | — | PUT | Invalidates all access tokens. |
| `invalidate_token` | — | PUT | Invalidates the access token. |
| `list_all_token_ids` | — | PUT | Lists all the access token IDs. |

### `AttorneyMatch`

| Method | Required Parameters | HTTP | Description |
| --- | --- | --- | --- |
| `get_norm_attorney_match` | — | GET | Returns normalized attorney results for a given attorney name. |

### `AttorneyProfile`

| Method | Required Parameters | HTTP | Description |
| --- | --- | --- | --- |
| `get_norm_attorney_by_id` | `norm_attorney_id` | GET | Returns the attorney profile. |
| `get_norm_law_firms_associated_with_norm_attorney` | `norm_attorney_id` | GET | Returns the law firms the attorney has worked for. |
| `get_norm_attorney_id_evolution_by_id` | `norm_attorney_id` | GET | Returns the ID evolution of a normalized attorney. |
| `get_norm_attorney_history_by_id` | `norm_attorney_id` | GET | Returns the history of a normalized attorney. |

### `AttorneySearch`

| Method | Required Parameters | HTTP | Description |
| --- | --- | --- | --- |
| `search_normalized_attorneys` | `q` | GET | Searches for attorneys. |
| `search_normalized_attorneys_by_id` | `norm_attorney_search_id` | GET | Returns normalized attorney search results for a provided search ID. |

### `AttorneyTrack`

| Method | Required Parameters | HTTP | Description |
| --- | --- | --- | --- |
| `get_attorney_tracks_root` | — | GET | Returns the attorney track list. |
| `track_attorney` | — | PUT | Adds an attorney track for the requested attorney ID with a refresh window set. |
| `get_attorney_tracks` | — | GET | Returns the attorney track list. |
| `get_attorney_track_by_id` | `norm_attorney_id` | GET | Returns the attorney track for a requested attorney ID. |
| `remove_attorney_track_by_id` | `norm_attorney_id` | DELETE | Removes the attorney track for a specific attorney ID. |

### `AttorneyUpdate`

| Method | Required Parameters | HTTP | Description |
| --- | --- | --- | --- |
| `put_norm_attorney_update` | — | PUT | Adds an attorney update for the requested attorney ID. |
| `get_norm_attorney_updates` | — | GET | Returns the attorney update list for a requested time range. |
| `get_norm_attorney_update_by_norm_attorney_id` | `norm_attorney_id` | GET | Returns attorney updates for a requested attorney ID. |

### `CaseAnalytics`

| Method | Required Parameters | HTTP | Description |
| --- | --- | --- | --- |
| `get_case_count_analytics_by_case_type` | — | GET | Case count analytics by case type. |
| `get_case_count_analytics_by_area_of_law` | — | GET | Case count analytics by area of law. |
| `get_case_count_analytics_by_case_type_group` | — | GET | Case count analytics by case type group. |
| `get_case_count_analytics_by_case_class` | — | GET | Case count analytics by case class. |
| `get_case_count_analytics_by_case_filed_date` | `group_by` | GET | Case count analytics by case filed date. |
| `get_case_count_analytics_by_court` | — | GET | Case count analytics by court. |
| `get_case_count_analytics_by_court_type` | — | GET | Case count analytics by court type. |
| `get_case_count_analytics_by_court_system` | — | GET | Case count analytics by court system. |
| `get_case_count_analytics_by_court_location` | — | GET | Case count analytics by court location. |

### `CaseDecisionDocument`

| Method | Required Parameters | HTTP | Description |
| --- | --- | --- | --- |
| `get_tentative_ruling_by_id` | `tentative_ruling_id` | GET | Returns details for a requested tentative ruling ID. |
| `get_tentative_ruling_download_by_id` | `tentative_ruling_id` | GET | Returns a downloadable URL for a requested tentative ruling ID. |

### `CaseDocumentOrder`

| Method | Required Parameters | HTTP | Description |
| --- | --- | --- | --- |
| `order_case_document` | — | PUT | Adds a case document order for requested document IDs. |
| `get_case_document_order_callbacks` | — | GET | Returns the case document order callback list for a callback generated date. |
| `get_case_document_order_callback_by_id` | `case_document_order_callback_id` | GET | Returns the case document order callback for a requested callback ID. |

### `CaseDocumentView`

| Method | Required Parameters | HTTP | Description |
| --- | --- | --- | --- |
| `get_document_by_id` | `case_document_id` | GET | Returns details for a requested document ID. |
| `get_case_document_download_by_id` | `case_document_id` | GET | Returns a downloadable URL for a requested document ID. |

### `CaseExport`

| Method | Required Parameters | HTTP | Description |
| --- | --- | --- | --- |
| `export_case` | `case_id` | GET | Exports a case for a requested case ID. |
| `get_case_export_callbacks` | — | GET | Returns the case export callback list for a requested date. |
| `get_case_export_callback_by_id` | `case_export_callback_id` | GET | Returns the case export callback for a requested callback ID. |

### `CaseHistory`

| Method | Required Parameters | HTTP | Description |
| --- | --- | --- | --- |
| `get_case_history_by_id` | `case_id` | GET | History of case parameters. |
| `get_parties_history_for_case` | `case_id` | GET | History of parties. |
| `get_parties_history_for_case_bylast_fetch_date_with_updates` | `case_id`, `last_fetch_date_with_updates` | GET | History of parties by date. |
| `get_counsel_history_for_case` | `case_id` | GET | History of counsel. |
| `get_counsel_history_for_case_bylast_fetch_date_with_updates` | `case_id`, `last_fetch_date_with_updates` | GET | History of counsel by date. |
| `get_counsel_associations_history_for_case` | `case_id` | GET | History of counsel associations. |
| `get_counsel_associations_history_for_case_bylast_fetch_date_with_updates` | `case_id`, `last_fetch_date_with_updates` | GET | History of counsel associations by date. |
| `get_judges_history_for_case` | `case_id` | GET | History of judges. |
| `get_judges_history_for_case_bylast_fetch_date_with_updates` | `case_id`, `last_fetch_date_with_updates` | GET | History of judges by date. |
| `get_party_counsel_associations_history_for_case` | `case_id` | GET | History of party/counsel associations. |
| `get_party_counsel_associations_history_for_case_bylast_fetch_date_with_updates` | `case_id`, `last_fetch_date_with_updates` | GET | History of party/counsel associations by date. |
| `get_docket_entries_history_for_case` | `case_id` | GET | History of docket entries. |
| `get_docket_entries_history_for_case_bylast_fetch_date_with_updates` | `case_id`, `last_fetch_date_with_updates` | GET | History of docket entries by date. |
| `get_hearing_history_for_case` | `case_id` | GET | History of hearings. |
| `get_hearing_history_for_case_bylast_fetch_date_with_updates` | `case_id`, `last_fetch_date_with_updates` | GET | History of hearings by date. |
| `get_case_documents_history_for_case` | `case_id` | GET | History of case documents. |
| `get_case_documents_history_for_case_bylast_fetch_date_with_updates` | `case_id`, `last_fetch_date_with_updates` | GET | History of case documents by date. |
| `get_related_case_history_for_case` | `case_id` | GET | History of related cases. |
| `get_related_case_history_for_case_bylast_fetch_date_with_updates` | `case_id`, `last_fetch_date_with_updates` | GET | History of related cases by date. |
| `get_tentative_rulings_history_for_case` | `case_id` | GET | History of tentative rulings. |
| `get_tentative_rulings_history_for_case_bylast_fetch_date_with_updates` | `case_id`, `last_fetch_date_with_updates` | GET | History of tentative rulings by date. |

### `CaseImport`

| Method | Required Parameters | HTTP | Description |
| --- | --- | --- | --- |
| `import_case` | — | PUT | Adds a case import for the requested case ID. |
| `get_case_import_callbacks` | — | GET | Returns case import callbacks for a requested date. |
| `get_case_import_callback_by_id` | `case_import_callback_id` | GET | Returns the case import callback for a requested callback ID. |

### `CaseMasterData`

| Method | Required Parameters | HTTP | Description |
| --- | --- | --- | --- |
| `get_motion_type_categories` | — | GET | Motion type category objects. |
| `get_motion_type_category` | `motion_type_category_id` | GET | Motion type category details. |
| `get_motion_type_groups` | — | GET | Motion type group objects. |
| `get_motion_type_group` | `motion_type_group_id` | GET | Motion type group details. |
| `get_motion_types` | — | GET | Motion type objects. |
| `get_motion_type` | `motion_type_id` | GET | Motion type details. |
| `get_motion_outcome_groups` | — | GET | Motion outcome group objects. |
| `get_motion_outcome_group` | `motion_outcome_group_id` | GET | Motion outcome group details. |
| `get_motion_outcomes` | — | GET | Motion outcome objects. |
| `get_motion_outcome` | `motion_outcome_id` | GET | Motion outcome details. |
| `get_procedural_activity_groups` | — | GET | Procedural activity group objects. |
| `get_procedural_activity_group` | `procedural_activity_group_id` | GET | Procedural activity group details. |
| `get_procedural_activities` | — | GET | Procedural activity objects. |
| `get_procedural_activity` | `procedural_activity_id` | GET | Procedural activity details. |
| `get_case_event_groups` | — | GET | Case event group objects. |
| `get_case_event_group` | `case_event_group_id` | GET | Case event group details. |
| `get_case_events` | — | GET | Case event objects. |
| `get_case_event` | `case_event_id` | GET | Case event details. |
| `get_case_disposition_groups` | — | GET | Case disposition group objects. |
| `get_case_disposition_group` | `case_disposition_group_id` | GET | Case disposition group details. |
| `get_case_dispositions` | — | GET | Case disposition objects. |
| `get_case_disposition` | `case_disposition_id` | GET | Case disposition details. |
| `get_cases_class` | — | GET | Case class objects. |
| `get_case_class` | `case_class_id` | GET | Case class details. |
| `get_areas_of_law` | — | GET | Area of law objects. |
| `get_area_of_law` | `area_of_law_id` | GET | Area of law details. |
| `get_case_type_groups` | — | GET | Case type group objects. |
| `get_case_type_group` | `case_type_group_id` | GET | Case type group details. |
| `get_case_types` | — | GET | Case type objects. |
| `get_case_type` | `case_type_id` | GET | Case type details. |
| `get_case_status_groups` | — | GET | Case status group objects. |
| `get_case_status_group` | `case_status_group_id` | GET | Case status group details. |
| `get_cases_status` | — | GET | Case status objects. |
| `get_case_status` | `case_status_id` | GET | Case status details. |
| `get_party_role_groups` | — | GET | Party role group objects. |
| `get_party_role_group` | `party_role_group_id` | GET | Party role group details. |
| `get_party_roles` | — | GET | Party role objects. |
| `get_party_role` | `party_role_id` | GET | Party role details. |
| `get_counsel_roles` | — | GET | Counsel role objects. |
| `get_counsel_role` | `counsel_role_id` | GET | Counsel role details for the given counsel role ID. |
| `get_case_relationship_types` | — | GET | Case relationship type objects. |
| `get_case_relationship_type` | `case_relationship_type_id` | GET | Case relationship type details. |
| `get_judge_roles` | — | GET | Judge role objects. |
| `get_judge_role` | `judge_role_id` | GET | Judge role details. |

### `CaseMatch`

| Method | Required Parameters | HTTP | Description |
| --- | --- | --- | --- |
| `match_case` | — | POST | Locates a case in UniCourt based on the given input. |

### `CaseSearch`

| Method | Required Parameters | HTTP | Description |
| --- | --- | --- | --- |
| `search_cases` | `q` | GET | Searches for cases. |
| `search_cases_by_id` | `case_search_id` | GET | Returns case search results for a provided search ID. |

### `CaseTrack`

| Method | Required Parameters | HTTP | Description |
| --- | --- | --- | --- |
| `get_case_tracks_root` | — | GET | Returns the case track list with date-based filtering on updates. |
| `track_case` | — | PUT | Adds a case track for the requested case ID with a refresh window set for automated updates. |
| `get_case_tracks` | — | GET | Returns the case track list with date-based filtering on updates. |
| `get_case_track_by_id` | `case_id` | GET | Returns the case object for a specific case with tracking information. |
| `remove_case_track_by_id` | `case_id` | DELETE | Removes the case track for a specific case ID. |

### `CaseUpdate`

| Method | Required Parameters | HTTP | Description |
| --- | --- | --- | --- |
| `update_case` | — | PUT | Submits a case update request to refresh case data from the court source. |
| `get_case_updates` | — | GET | Returns case update response details for requests submitted within a specified time period. |
| `get_case_update_by_case_id` | `case_id` | GET | Returns the case update object for the specified case ID with status information. |

### `CaseView`

| Method | Required Parameters | HTTP | Description |
| --- | --- | --- | --- |
| `get_case` | `case_id` | GET | Returns case information for a requested case ID. |
| `get_case_parties` | `case_id` | GET | Returns parties for a requested case ID. |
| `get_case_counsel` | `case_id` | GET | Returns counsel for a requested case ID. |
| `get_case_judges` | `case_id` | GET | Returns judges for a requested case ID. |
| `get_case_docket_entries` | `case_id` | GET | Returns docket entries for a requested case ID. |
| `get_primary_documents_for_docket_entries` | `case_id`, `docket_entry_id` | GET | Returns primary documents for docket entries. |
| `get_secondary_documents_for_docket_entries` | `case_id`, `docket_entry_id` | GET | Returns secondary documents for docket entries. |
| `get_case_documents` | `case_id` | GET | Returns documents for a requested case ID. |
| `get_case_hearings` | `case_id` | GET | Returns hearings for a requested case ID. |
| `get_case_related_cases` | `case_id` | GET | Returns related cases for a requested case ID. |
| `get_party_by_id` | `party_id` | GET | Returns details for a requested party ID. |
| `get_party_associated_counsel` | `party_id` | GET | Returns associated counsel details for a requested party ID. |
| `get_counsel_by_id` | `counsel_id` | GET | Returns details for a requested counsel ID. |
| `get_counsel_associated_parties` | `counsel_id` | GET | Returns associated party details for a requested counsel ID. |
| `get_counsel_associated_counsel` | `counsel_id` | GET | Returns associated counsel details for a requested counsel ID. |
| `get_judge_by_id` | `judge_id` | GET | Returns details for a requested judge ID. |
| `get_tentative_rulings` | `case_id` | GET | Returns tentative rulings for a requested case ID. |

### `CourtMasterData`

| Method | Required Parameters | HTTP | Description |
| --- | --- | --- | --- |
| `get_court_types` | — | GET | Court type objects. |
| `get_court_type` | `court_type_id` | GET | Court type details for the provided court type ID. |
| `get_court_systems` | — | GET | Court system objects. |
| `get_court_system` | `court_system_id` | GET | Court system details for the provided court system ID. |
| `get_courts` | — | GET | Court objects. |
| `get_court` | `court_id` | GET | Court details for the provided court ID. |
| `get_court_locations_for_court` | `court_id` | GET | Associated court location for the provided court ID. |
| `get_jurisdiction_geo_for_court` | `court_id` | GET | Jurisdiction geo for the provided court ID. |
| `get_appeal_courts_for_court` | `court_id` | GET | Appeal courts for the provided court ID. |
| `get_court_locations` | — | GET | Court location objects. |
| `get_court_location` | `court_location_id` | GET | Court location details for the provided court location ID. |
| `get_courts_for_court_location` | `court_location_id` | GET | Associated courts for the provided court location. |
| `get_jurisdictions_geo` | — | GET | Jurisdiction geo objects. |
| `get_jurisdiction_geo` | `jurisdiction_geo_id` | GET | Jurisdiction geo details for the provided jurisdiction geo ID. |
| `get_courts_for_jurisdiction_geo` | `jurisdiction_geo_id` | GET | Associated courts for a given jurisdiction geo. |
| `get_court_source` | — | GET | Court source objects. |
| `get_court_source_by_id` | `court_source_id` | GET | Court source details for the provided court source ID. |

### `CourtServiceStatus`

| Method | Required Parameters | HTTP | Description |
| --- | --- | --- | --- |
| `gettentative_ruling_source` | — | GET | Tentative ruling service status object. |
| `get_tentative_ruling_source_by_id` | `tentative_ruling_source_id` | GET | Tentative ruling source details for the provided tentative ruling source ID. |
| `get_tentative_ruling_source_service_status` | — | GET | Tentative ruling service status object. |
| `get_court_source_service_status` | — | GET | Court source service status objects. |
| `get_court_system_service_status` | — | GET | Court system service status objects. |
| `get_courts_service_status` | — | GET | Court service status objects. |

### `EntityAnalytics`

| Method | Required Parameters | HTTP | Description |
| --- | --- | --- | --- |
| `get_case_count_analytics_by_norm_attorney` | — | GET | Case count analytics by attorney. |
| `get_case_count_analytics_by_opposing_norm_attorney_for_a_norm_attorney` | `norm_attorney_id` | GET | Case count analytics by opposing attorney for a given attorney. |
| `get_case_count_analytics_by_norm_law_firm` | — | GET | Case count analytics by law firm. |
| `get_case_count_analytics_by_opposing_norm_law_firm_for_a_norm_law_firm` | `norm_law_firm_id` | GET | Case count analytics by opposing law firm for a given law firm. |

### `LawFirmMatch`

| Method | Required Parameters | HTTP | Description |
| --- | --- | --- | --- |
| `get_norm_law_firm_match` | `name` | GET | Returns normalized law firm results for a given law firm name. |

### `LawFirmProfile`

| Method | Required Parameters | HTTP | Description |
| --- | --- | --- | --- |
| `get_norm_law_firm_by_id` | `norm_law_firm_id` | GET | Returns the normalized law firm profile. |
| `get_norm_attorneys_associated_with_norm_law_firm` | `norm_law_firm_id` | GET | Returns attorneys working for the law firm. |
| `get_norm_law_firm_id_evolution_by_id` | `norm_law_firm_id` | GET | Returns the ID evolution of a normalized law firm. |

### `LawFirmSearch`

| Method | Required Parameters | HTTP | Description |
| --- | --- | --- | --- |
| `search_normalized_law_firms` | `q` | GET | Searches for law firms. |
| `search_normalized_law_firms_by_id` | `norm_law_firm_search_id` | GET | Returns normalized law firm search results for a provided search ID. |

### `LawFirmTrack`

| Method | Required Parameters | HTTP | Description |
| --- | --- | --- | --- |
| `get_law_firm_tracks_root` | — | GET | Returns the law firm track list. |
| `track_law_firm` | — | PUT | Adds a law firm track for the requested law firm ID with a refresh window set. |
| `get_law_firm_tracks` | — | GET | Returns the law firm track list. |
| `get_law_firm_track_by_id` | `norm_law_firm_id` | GET | Returns the law firm track for a requested law firm ID. |
| `remove_law_firm_track_by_id` | `norm_law_firm_id` | DELETE | Removes the law firm track for a specific law firm ID. |

### `LawFirmUpdate`

| Method | Required Parameters | HTTP | Description |
| --- | --- | --- | --- |
| `put_norm_law_firm_update` | — | PUT | Adds a law firm update for the requested law firm ID. |
| `get_norm_law_firm_updates` | — | GET | Returns the law firm update list for the last N days. |
| `get_norm_law_firm_update_by_norm_law_firm_id` | `norm_law_firm_id` | GET | Returns law firm updates for a requested law firm ID. |

### `PACERCaseImport`

| Method | Required Parameters | HTTP | Description |
| --- | --- | --- | --- |
| `import_pacer_case_by_court_using_case_number` | `pacer_user_id`, `case_number`, `court_id` | GET | Finds a PACER case for a requested case number and court. |

### `PACERCaseSearch`

| Method | Required Parameters | HTTP | Description |
| --- | --- | --- | --- |
| `all_courts_pacer_case_locator_case_search` | `pacer_user_id` | GET | PACER Case Locator search for all courts. |
| `appeal_courts_pacer_case_locator_case_search` | `pacer_user_id` | GET | PACER Case Locator search for appeal courts. |
| `bankruptcy_courts_pacer_case_locator_case_search` | `pacer_user_id` | GET | PACER Case Locator search for bankruptcy courts. |
| `civil_courts_pacer_case_locator_case_search` | `pacer_user_id` | GET | PACER Case Locator search for civil courts. |
| `criminal_courts_pacer_case_locator_case_search` | `pacer_user_id` | GET | PACER Case Locator search for criminal courts. |
| `multi_district_courts_pacer_case_locator_case_search` | `pacer_user_id` | GET | PACER Case Locator search for multi-district courts. |

### `PACERCredentials`

| Method | Required Parameters | HTTP | Description |
| --- | --- | --- | --- |
| `add_pacer_credential` | — | PUT | Adds a PACER credential. |
| `get_pacer_credential` | — | GET | Returns the PACER credential list. |
| `get_pacer_credential_by_id` | `pacer_user_id` | GET | Returns the PACER credential for a requested PACER user ID. |
| `remove_pacer_credential_by_id` | `pacer_user_id` | DELETE | Removes the PACER credential for a specific PACER user ID. |

### `PACERPartySearch`

| Method | Required Parameters | HTTP | Description |
| --- | --- | --- | --- |
| `all_courts_pacer_case_locator_party_search` | `pacer_user_id` | GET | PACER Case Locator party search for all courts. |
| `appeal_courts_pacer_case_locator_party_search` | `pacer_user_id` | GET | PACER Case Locator party search for appeal courts. |
| `bankruptcy_courts_pacer_case_locator_party_search` | `pacer_user_id` | GET | PACER Case Locator party search for bankruptcy courts. |
| `civil_courts_pacer_case_locator_party_search` | `pacer_user_id` | GET | PACER Case Locator party search for civil courts. |
| `criminal_courts_pacer_case_locator_party_search` | `pacer_user_id` | GET | PACER Case Locator party search for criminal courts. |
| `multi_district_courts_pacer_case_locator_party_search` | `pacer_user_id` | GET | PACER Case Locator party search for multi-district courts. |

### `Usage`

| Method | Required Parameters | HTTP | Description |
| --- | --- | --- | --- |
| `get_account_monthly_usage` | `month` | GET | Returns billing activity usage for the account for a specified month. |
| `get_account_daily_usage_by_date` | `date` | GET | Returns billing activity usage for the account for a requested date. |
| `get_workspace_monthly_usage` | `month` | GET | Returns billing activity usage for a workspace for a specified month. |
| `get_workspace_daily_usage_by_date` | `date` | GET | Returns billing activity usage for a workspace for a requested date. |

### `WorkspaceManagement`

| Method | Required Parameters | HTTP | Description |
| --- | --- | --- | --- |
| `workspace_templates_request` | — | GET | Returns the list of workspace templates. |
| `workspace_template_detail_request` | `workspace_template_id` | GET | Returns details of a specific workspace template. |
| `create_workspace_request` | — | PUT | Creates a new workspace. |
| `workspace_detail_list_request` | — | GET | Returns the list of workspaces. |
| `search_workspaces_request` | `q` | GET | Searches for workspaces with advanced filters. |
| `workspace_detail_request` | — | GET | Returns details of a specific workspace. |
| `update_workspace_request` | — | PUT | Updates an existing workspace. |
| `archive_workspace_request` | — | PUT | Archives an existing workspace. |

### `WorkspaceTokenManagement`

| Method | Required Parameters | HTTP | Description |
| --- | --- | --- | --- |
| `generate_new_workspace_token` | — | POST | Generates a new workspace token to access the API. |
| `list_all_workspace_token_ids` | — | PUT | Lists all workspace access token IDs. |
| `invalidate_workspace_token` | — | PUT | Invalidates the workspace access token. |
| `invalidate_all_workspace_tokens` | — | PUT | Invalidates all workspace access tokens for a workspace. |

## Troubleshooting

### I'm getting an error that my Python version is not supported

The SDK requires Python 3.11 or later. Check your installed version with:

```bash
python3 --version
```

If you need to upgrade your python vesrion, follow official Python installation instructions for your OS: [Python Downloads](https://www.python.org/downloads/).

After upgrading, confirm `pip` is pointing at the new version before reinstalling the SDK:

```bash
python3 -m pip install path/to/downloaded_file.whl
```
