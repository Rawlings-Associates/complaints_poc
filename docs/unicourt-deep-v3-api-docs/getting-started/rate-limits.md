---
title: "Rate Limits"
source: https://dart.unicourt.com/res-deep/assets/deep-v3-api-doc/getting-started/rate-limits/
retrieved: 2026-10-01
---

# Rate Limits

## Understanding API rate limits

### Rate limits vs billable activity limits

These two concepts are separate:

- **Rate limits** govern how fast you may call an endpoint. Exceeding them returns `429` and does not count against your account's billable activity limit. This article is about rate limits.
- **Billable activity limits** govern how much billable activity your account may perform. When a monthly allotment is exhausted, additional usage may draw from a bulk reserve if your agreement includes one; otherwise the billable operation is blocked. For more details, see [Usage, Limits, and Billable Activity](../getting-started/usage-limits-billable-activities.md).

### Our rate limits and why we have them

Rate limits are the restriction of the count of requests or calls that can be made to the UniCourt APIs within a period of time, per account. They are imposed on our APIs to maximize API stability and prevent abuse.

Stay under **30 requests per 5 seconds**. Exceeding the limit, returns a response with a status code `429` or the `message` "Too Many Requests”, as seen below.

1. Rate Limit

```json
{ "object": "Exception", "code": "UN429", "message": "TOO_MANY_REQUESTS", "details": "Too Many Requests."}
```

2. Rate Limit

```json
{"message": "Too Many Requests"}
```

### Concurrency

For each endpoint, we only permit a specific number of requests. Having stated that, you can send queries to various endpoints simultaneously. Let's say that you want to make requests to [**/workspace/{workspaceId}/case/{caseId}**](#) and [**/workspace/{workspaceId}/case/{caseId}/attorneys**](#). You may do so concurrently provided you do not exceed the maximum number of hits for each endpoint.
