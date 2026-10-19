# Provenance

Reference: https://github.com/subsquid-labs/uniswapv3-squid, commit
`53b8aa4de1f8d444a0567171a86ed9d3a9aac44b` (28/08/2026), MIT License,
Copyright (c) 2023 Subsquid Labs. The full text is in `LICENSE.upstream` and
applies to the copied files below.

Copied unchanged from that commit:

- `abi/pool.json`, `abi/ERC20.json`
- `src/abi/pool/*`, `src/abi/ERC20/*`, `src/abi/abi.support.ts` (typegen output)

Taken as pattern, rewritten here: the Portal + RPC fallback data source
(`src/processor.ts` upstream), the TypeORM store with hot blocks, the use of
`(blockNumber, logIndex)` to order open/close (upstream `openOrder`/
`closeOrder` on token buckets).

Not taken, and why: the upstream indexes every pool of the factory and
rebuilds the Uniswap V3 subgraph (ticks, positions, TVL, factory totals) in
several address-filtered passes over the full history (~120 GB of Postgres);
its rollups are hourly and daily, priced through mutable `derivedETH` and
`Bundle.ethPriceUSD` kept as JS floats. A pilot on an allowlist of pools
needs candles only, at 5m/15m/1h/1d, so `src/candles.ts` aggregates them
directly from Swap events with exact fixed-point prices; restricting the
upstream to an allowlist would have meant rewriting its pass/manifest
machinery and its pricing anyway.

Not copied: the upstream `.env` (it carries a project RPC URL), its
`docker-compose.yml` (default password, published port), `assets/pools.json`.
`@subsquid/big-decimal` (GPL-3.0-or-later) is not used: prices are bigint
fixed point.
