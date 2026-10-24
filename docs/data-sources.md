# Data sources and responsible use

`GET /api/v1/data/world-bank/{indicator}` is deliberately an **offline mock adapter** in this starter. It gives the frontend a stable interface before the team chooses an indicator or configures network access.

To connect it to the World Bank API, validate the returned JSON shape, record the indicator, country, last-updated date, and source in every response. Cache external responses; network failure must be visible as an unavailable source, never silently relabelled as live data.

World Bank indicators provide context such as inflation or GDP history. They do not predict an individual's investment return, a research outcome, or a causal future. TimeFork must display this distinction wherever external data is used.
