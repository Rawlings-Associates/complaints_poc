---
title: "What You Can Do with DEEP"
source: https://dart.unicourt.com/res-deep/assets/deep-v3-api-doc/getting-started/what-you-can-do-with-deep/
retrieved: 2026-10-01
---

# What You Can Do with DEEP

DEEP is organized into a handful of API groups, each covering a related set of endpoints. Start with the group that matches what you are trying to build, then use the common use cases below to jump straight to a walkthrough.

## API groups

### Docket Research

Search for cases and read everything attached to them: parties, counsel, judges, hearings, documents, and docket entries.

- **[Case Search](#)**
- **[Case View](#)**
- **[Case Document View](#)**
- **[Case Update](#)**

### Docket Tracking

Put a case on a recurring refresh schedule so UniCourt keeps it current as the court publishes new activity.

- **[Case Track](#)**

### Entity Research

Resolve an attorney or law firm name to a normalized entity, then read its profile.

- **[Entity Search](#)**
- **[Entity Profile View](#)**
- **[Entity Update](#)**

### Entity Tracking

Put an attorney or law firm on a recurring refresh schedule, the same way you would a case.

- **[Entity Track](#)**

### Legal Analytics

Aggregate case counts across a dimension, such as court, case type, or opposing counsel, without pulling every case individually.

- **[Analytics View](#)**

### Platform

Everything that keeps the rest of DEEP running: authentication, workspaces, PACER credentials, usage, court coverage, and master data.

- **[Authentication & Workspace Management](#)**
- **[PACER Credentials](#)**
- **[Usage](#)**
- **[Court Service Status](#)**
- **[Court Master Data](#)**
- **[Case Master Data](#)**

### Callbacks & WebSockets

Receive results for long-running operations like case imports, exports, updates, and document orders.

- **[Callbacks & WebSockets](#)**

Callbacks

For sync and async WebSocket delivery, see [Set up callbacks](../common-use-cases/platform/set-up-callbacks.md) and [WebSocket Protocol](../knowledge-base/wss.md). For HTTP status polling without WebSockets, see [Synchronous vs asynchronous](../getting-started/working-with-unicourt-apis.md#synchronous-vs-asynchronous).

### DEEP v3 API Bundle

- **[All DEEP APIs](#)**, if you would rather work from a single combined spec.

## Common use cases

A quick map from what you are trying to do to where you start. Each links to a full walkthrough.

| I want to... | Use case |
| --- | --- |
| Find cases matching specific criteria | [Search for cases](../common-use-cases/find-and-read-cases/search-for-cases.md) |
| Pull a case's full docket, parties, and documents | [Read a full case](../common-use-cases/find-and-read-cases/read-a-full-case.md) |
| Get a case document (download or order) | [Getting documents from cases](../common-use-cases/get-case-content/get-a-case-document.md) |
| Export a full case as a ZIP | [Export a case](../common-use-cases/get-case-content/export-a-case.md) |
| Keep a case current without polling | [Track a case on a schedule](../common-use-cases/keep-cases-current/track-a-case-on-a-schedule.md) |
| Refresh a single case right now | [Update a case once](../common-use-cases/keep-cases-current/update-a-case-once.md) |
| See what changed on a case since my last check | [See what changed on a case](../common-use-cases/keep-cases-current/sync-case-history.md) |
| Pull a case in from PACER by case number | [Import a case from PACER](../common-use-cases/find-and-read-cases/import-a-case-from-pacer.md) |
| Resolve an attorney or firm name to an entity | [Search for and Match your Entity](../common-use-cases/entities-and-counsel/search-for-an-entity.md) |
| Read an attorney or law firm profile | [Read an entity profile](../common-use-cases/entities-and-counsel/read-an-entity-profile.md) |
| Keep an attorney or firm profile current | [Track an entity on a schedule](../common-use-cases/entities-and-counsel/track-an-entity-on-a-schedule.md) |
| Turn plain language into a structured filter ID | [Resolve master data](../common-use-cases/find-and-read-cases/resolve-master-data.md) |
| Analyze case counts by court, type, or area of law | [Analyze case counts](../common-use-cases/analyze/analyze-case-counts.md) |
| Analyze case counts by attorney or opposing counsel | [Analyze counsel activity](../common-use-cases/analyze/analyze-counsel-activity.md) |
| Create or organize workspaces | [Create a workspace](../common-use-cases/platform/create-a-workspace.md) |
| Check my API usage or billing activity | [Check usage](../common-use-cases/platform/check-usage.md) |
| Receive results for long-running operations | [Set up callbacks](../common-use-cases/platform/set-up-callbacks.md) |
