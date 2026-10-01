# Archive notes

This folder is an unedited copy of UniCourt's DEEP v3 "API Docs" pages, as
exported on 2026-10-01. Start at [INDEX.md](INDEX.md), which also gives the
source URL. This file is the only addition to that folder.

- **Base URL:** the pagination page shows `https://deep-api.unicourt.com/v3/...`. A check
  without credentials on 2026-10-01 found `/v3/workspace/.../caseSearch`
  answering 404, while `/workspace/.../caseSearch` answered 401 (the route
  exists, but needs a token). `unicourt_state` therefore uses
  `https://deep-api.unicourt.com` with no `/v3`, as in the OpenAPI spec.
  Set `UNICOURT_API_ROOT` to override it.
- **Pages the code relies on:**
  - [getting-started/rate-limits.md](getting-started/rate-limits.md): 30
    requests per 5 seconds; `429` / `UN429`.
  - [knowledge-base/pagination.md](knowledge-base/pagination.md): `pageNumber`
    is required, follow `nextPageAPI`, page sizes are fixed (10 for case
    search, 100 for documents), and the cap is 1,000 pages.
- **Python SDK:** the wheel that
  [knowledge-base/python-sdk.md](knowledge-base/python-sdk.md) links to
  (its "Download" links are `#` placeholders in this copy) is stored at
  [../unicourt-sdk/unicourt-1.0-py3-none-any.whl](../unicourt-sdk/unicourt-1.0-py3-none-any.whl).
  See [../unicourt-sdk/README.md](../unicourt-sdk/README.md). It is kept for
  reference only and is not used by this project. Its default host is also
  `https://deep-api.unicourt.com` with no `/v3`.
- **Plan:** see [../unicourt-retrieval.md](../unicourt-retrieval.md) for the
  retrieval plan built on these docs.
