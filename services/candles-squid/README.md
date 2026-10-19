# candles-squid (pilot, OFF by default)

OHLCV candles at 5m, 15m, 1h and 1d for an **allowlist** of Ethereum
Uniswap V3 pools, built from their `Swap` events with the Squid SDK, served
over GraphQL to the app on the internal Docker network. It covers nothing
else: not Uniswap V2 or V4, not forks, not other chains. Background, scope
and provenance: `PROVENANCE.md`, `../../HANDOVER.md` (19/10),
`ISTRUZIONI_CLAUDE_SQUID.md`.

Nothing starts by default. The normal deploy (`docker compose up -d --build`)
ignores the three services; they run only with the `squid` profile, and the
app reads them only with `SQUID_MODE=compare` or `on` (default `off`).

## What a candle is

One row per (pool, token side, timeframe, UTC bucket start):

- `open/high/low/close`: price of `token` in `quote` units after each swap,
  from `sqrtPriceX96` with the tokens' decimals, exact fixed point (36
  fractional digits), stored as decimal strings.
- `openUsd/highUsd/lowUsd/closeUsd`: the same in USD *at each swap*: quote
  WETH → ETH/USD from the last swap of the reference pool (USDC/WETH 0.05%)
  before it, by block and log index; quote USDC/USDT/DAI → 1 USD
  (`pricing = stable-peg`); any other quote → null (`pricing = none`), never
  guessed. Before the first reference swap ETH/USD is read once from the
  reference pool's `slot0` at `START_BLOCK - 1`.
- `volumeToken` (token units), `volumeUsd` (USD, priced swaps only),
  `swaps`, `pricedSwaps`.
- open/close are the first/last swap by `(block, logIndex)`; the inverse side
  is computed per swap, so its high is the inverse of the other side's low.
- A bucket with no swap has no row. A missing row before `SyncStatus.block`
  means no trade; after it means not indexed yet. The app tells the two apart
  with `SyncStatus` (`timestamp`, `finalizedBlock`).

Reorgs: the store keeps the unfinalized blocks and rolls their writes back;
each batch commits atomically with its checkpoint, so a restart resumes
without counting a swap twice. `finalizedBlock` is `block - FINALITY_BLOCKS`
(64 by default), an estimate, not the chain's finality.

## Run (local or server)

Requirements: Node 22, Postgres 16, an Ethereum JSON-RPC (any provider; the
public `ethereum-rpc.publicnode.com` works but is rate limited, no SLA), the
public Portal (`portal.sqd.dev`, no key, its own limits; check them before
relying on it).

```
cp .env.example .env              # fill POOLS, START_BLOCK, RPC_ETH_HTTP, DB_*
npm ci && npm test                # unit tests of the aggregation
npx squid-typeorm-migration apply # schema
node lib/main.js                  # processor (follows the head)
npx squid-graphql-server          # API on GQL_PORT
```

Every pool in `POOLS` is checked with `factory()` against
`0x1f98431c8ad98523631ae4a59f267346ea31f984` before the first block; one that
fails stops the start.

On the server: `cp deploy/squid.env.example deploy/squid.env`, fill it, then
`docker compose --profile squid up -d squid-db squid-processor squid-api`.
Stop: `docker compose --profile squid stop squid-processor squid-api`
(the database keeps its volume `squid-db`). Remove everything:
`docker compose --profile squid down` then `docker volume rm deploy_squid-db`.

Disk: a few MB per pool-month at these four timeframes (8 rows per swap at
most, upserts); backup with `pg_dump` from `squid-db`. Adding pools: append
to `POOLS` and restart; a new pool is read from where the processor is, so a
full history for it needs a fresh database or a dedicated run.

## Not done / not measured

- No production run: neither the deploy nor the app's `SQUID_MODE` turn it on.
- Portal and RPC limits and costs at sustained use are not measured.
- `finalizedBlock` is an estimate (see above).
- The comparison with GeckoTerminal (`tools/compare_gecko.py`, run by
  `.github/workflows/candles-squid.yml` on the chat branch) is a check of
  consistency between two methods, not a proof of correctness.
