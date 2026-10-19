/**
 * Candles for an allowlist of Ethereum Uniswap V3 pools, from their Swap
 * events (ISTRUZIONI_CLAUDE_SQUID.md, phases 3-4).
 *
 * Why not run subsquid-labs/uniswapv3-squid as is (see PROVENANCE.md): it
 * indexes every pool of the factory and rebuilds the whole subgraph (ticks,
 * positions, TVL, multi-pass history), ~120 GB of Postgres, and its rollups
 * are hourly and daily only. A pilot of a few pools needs none of that, and a
 * Swap event already carries the pool price after the swap (sqrtPriceX96),
 * so a candle needs no pool state from before START_BLOCK. What is kept from
 * upstream: the pool and ERC20 ABIs, the Portal + RPC fallback data source,
 * the TypeORM store with hot blocks.
 *
 * Environment:
 *   POOLS          comma-separated pool addresses (required). Each is checked
 *                  against the factory before indexing: a pool whose factory()
 *                  is not FACTORY_ADDRESS stops the start, it is never guessed.
 *   START_BLOCK    first block read (required: no full-history sync by default)
 *   RPC_ETH_HTTP   Ethereum JSON-RPC (required: factory/token reads, slot0 of the
 *                  reference pool at START_BLOCK - 1, and the fallback source)
 *   PORTAL_URL     Portal dataset (default: the public mainnet dataset)
 *   PORTAL_API_KEY only for a private portal
 *   ETH_USD_POOL   USDC/WETH reference pool for ETH/USD (default the 0.05% one)
 *   FINALITY_BLOCKS blocks under the head counted as finalized (default 64)
 *   DB_*           Postgres, see .env.example
 *
 * USD: a side quoted in WETH is priced with ETH/USD from the reference pool's
 * last swap before it (by block and log index), a side quoted in a listed USD
 * stablecoin at 1 USD (pricing "stable-peg"), any other side is left unpriced.
 * Reorgs: the store keeps the hot blocks and rolls their writes back, and
 * each batch commits with its checkpoint, so a replay never counts twice.
 */
import {run} from '@subsquid/batch-processor'
import {augmentBlock} from '@subsquid/evm-objects'
import {EvmFallbackDataSourceBuilder} from '@subsquid/squid-sdk/evm/fallback'
import {RpcClient} from '@subsquid/rpc-client'
import {TypeormDatabase, type Store} from '@subsquid/typeorm-store'
import assert from 'assert'
import {In} from 'typeorm'
import * as poolAbi from './abi/pool'
import * as erc20 from './abi/ERC20'
import {
    TIMEFRAMES, applySwap, fromDecimal, inverse, price0In1, sidesOf, toDecimal, type CandleState, type QuotePrices,
} from './candles'
import {Candle, EthUsd, Pool, SyncStatus} from './model'

export const FACTORY_ADDRESS = '0x1f98431c8ad98523631ae4a59f267346ea31f984'
export const WETH = '0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2'
export const STABLES = new Set([
    '0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48', // USDC
    '0xdac17f958d2ee523a2206206994597c13d831ec7', // USDT
    '0x6b175474e89094c44da98b954eedeac495271d0f', // DAI
])
const DEFAULT_ETH_USD_POOL = '0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640' // USDC/WETH 0.05%
const DEFAULT_PORTAL_URL = 'https://portal.sqd.dev/datasets/ethereum-mainnet'

function env(name: string, required = true): string {
    const v = (process.env[name] || '').trim()
    assert(!required || v, `${name} is required (see services/candles-squid/README.md)`)
    return v
}

const POOLS = env('POOLS').split(',').map((s) => s.trim().toLowerCase()).filter(Boolean)
const START_BLOCK = Number(env('START_BLOCK'))
const ETH_USD_POOL = (process.env.ETH_USD_POOL || DEFAULT_ETH_USD_POOL).toLowerCase()
const FINALITY_BLOCKS = Number(process.env.FINALITY_BLOCKS || 64)
assert(POOLS.length > 0 && POOLS.length <= 1000, 'POOLS: between 1 and 1000 addresses')
assert(Number.isInteger(START_BLOCK) && START_BLOCK > 0, 'START_BLOCK: a block number')

const rpc = new RpcClient({url: env('RPC_ETH_HTTP'), capacity: 5, rateLimit: 5, retryAttempts: 3,
    headers: {'user-agent': 'candles-squid'}})   // some public RPCs refuse an empty agent

async function call<T>(fn: {encode(a: {}): string; decodeResult(o: string): T}, to: string, block: number | 'latest'): Promise<T> {
    const tag = block === 'latest' ? 'latest' : '0x' + block.toString(16)
    const out: string = await rpc.call('eth_call', [{to, data: fn.encode({})}, tag])
    return fn.decodeResult(out)
}

/** Reads and checks every pool before the first block: factory, tokens, decimals. */
async function describePools(): Promise<Pool[]> {
    const out: Pool[] = []
    const startBlock: {timestamp: string} | null = await rpc.call('eth_getBlockByNumber', ['0x' + START_BLOCK.toString(16), false])
    assert(startBlock != null, `START_BLOCK ${START_BLOCK} not found on the RPC`)
    const fromTimestamp = Number(BigInt(startBlock.timestamp))
    const refused: string[] = []
    for (const address of new Set([...POOLS, ETH_USD_POOL])) {
        const factory = String(await call(poolAbi.functions.factory, address, 'latest')).toLowerCase()
        if (factory !== FACTORY_ADDRESS) {
            refused.push(`${address} (factory ${factory})`)
            continue
        }
        const token0 = String(await call(poolAbi.functions.token0, address, 'latest')).toLowerCase()
        const token1 = String(await call(poolAbi.functions.token1, address, 'latest')).toLowerCase()
        const symbol = async (t: string) => {
            try {
                return String(await call(erc20.functions.symbol, t, 'latest'))
            } catch {
                return null       // bytes32 symbols (MKR...) are not needed for candles
            }
        }
        out.push(new Pool({
            id: address, token0, token1,
            decimals0: Number(await call(erc20.functions.decimals, token0, 'latest')),
            decimals1: Number(await call(erc20.functions.decimals, token1, 'latest')),
            symbol0: await symbol(token0), symbol1: await symbol(token1),
            fee: Number(await call(poolAbi.functions.fee, address, 'latest')),
            fromBlock: START_BLOCK, fromTimestamp,
        }))
    }
    assert(refused.length === 0, `not Uniswap V3 pools of ${FACTORY_ADDRESS}: ${refused.join(', ')}`)
    return out
}

/** ETH/USD at the end of `block`, from the reference pool's slot0. */
async function ethUsdAt(ref: Pool, block: number): Promise<bigint | null> {
    const slot = await call(poolAbi.functions.slot0, ref.id, block) as {sqrtPriceX96: bigint}
    const p0 = price0In1(slot.sqrtPriceX96, ref.decimals0, ref.decimals1)
    return ref.token1 === WETH ? inverse(p0) : ref.token0 === WETH ? p0 : null
}

function candleId(pool: string, token: string, tf: number, start: number): string {
    return `${pool}-${token}-${tf}-${start}`
}

function toState(c: Candle): CandleState {
    const n = (s: string | null | undefined) => (s == null ? null : fromDecimal(s))
    return {
        start: c.start, timeframe: c.timeframe, openOrder: c.openOrder, closeOrder: c.closeOrder,
        open: fromDecimal(c.open), high: fromDecimal(c.high), low: fromDecimal(c.low), close: fromDecimal(c.close),
        openUsd: n(c.openUsd), highUsd: n(c.highUsd), lowUsd: n(c.lowUsd), closeUsd: n(c.closeUsd),
        // the USD open/close are set by the first/last priced swap, whose order is not stored:
        // within a stored candle they are taken as already final for the swaps before it
        openUsdOrder: c.openUsd == null ? null : c.openOrder,
        closeUsdOrder: c.closeUsd == null ? null : c.closeOrder,
        volumeToken: fromDecimal(c.volumeToken), volumeUsd: fromDecimal(c.volumeUsd),
        swaps: c.swaps, pricedSwaps: c.pricedSwaps,
    }
}

function fromState(id: string, pool: string, token: string, quote: string, pricing: string, s: CandleState): Candle {
    const d = (x: bigint | null) => (x == null ? null : toDecimal(x))
    return new Candle({
        id, pool, token, quote, timeframe: s.timeframe, start: s.start,
        openOrder: s.openOrder, closeOrder: s.closeOrder,
        open: toDecimal(s.open), high: toDecimal(s.high), low: toDecimal(s.low), close: toDecimal(s.close),
        openUsd: d(s.openUsd), highUsd: d(s.highUsd), lowUsd: d(s.lowUsd), closeUsd: d(s.closeUsd),
        volumeToken: toDecimal(s.volumeToken), volumeUsd: toDecimal(s.volumeUsd),
        swaps: s.swaps, pricedSwaps: s.pricedSwaps, pricing,
    })
}

async function main() {
    const pools = await describePools()
    const byId = new Map(pools.map((p) => [p.id, p]))
    const ref = byId.get(ETH_USD_POOL)!
    assert(ref.token0 === WETH || ref.token1 === WETH, 'ETH_USD_POOL must pair WETH')
    assert(STABLES.has(ref.token0) || STABLES.has(ref.token1), 'ETH_USD_POOL must pair a USD stablecoin')
    const indexed = new Set(POOLS)

    const source = new EvmFallbackDataSourceBuilder()
        .setDownstreamSources([
            {type: 'portal' as const, url: process.env.PORTAL_URL || DEFAULT_PORTAL_URL,
             ...(process.env.PORTAL_API_KEY ? {headers: {'x-api-key': process.env.PORTAL_API_KEY}} : {})},
            {type: 'rpc' as const, url: env('RPC_ETH_HTTP'), network: 'ethereum-mainnet'},
        ])
        .setFields({block: {timestamp: true}, log: {address: true, topics: true, data: true}})
        .addLog({where: {address: [...byId.keys()], topic0: [poolAbi.events.Swap.topic]}, range: {from: START_BLOCK}})
        .build()

    const db = new TypeormDatabase({stateSchema: 'candles_squid', supportHotBlocks: true})

    run(source, db, async (ctx) => {
        const store: Store = ctx.store
        const blocks = ctx.blocks.map(augmentBlock)
        if (blocks.length === 0) return

        // Pools are written once, in the first batch (and again if POOLS grew).
        const known = new Set((await store.findBy(Pool, {id: In([...byId.keys()])})).map((p) => p.id))
        const fresh = pools.filter((p) => !known.has(p.id))
        if (fresh.length) await store.insert(fresh)

        let eth = await store.get(EthUsd, 'last')
        if (eth == null) {
            // slot0 at START_BLOCK - 1 needs an archive node (public RPCs refuse
            // it): without one, ETH/USD starts at the reference pool's first
            // swap, and WETH-quoted swaps before it stay unpriced.
            const seed = await ethUsdAt(ref, START_BLOCK - 1).catch((err) => {
                console.warn(`no ETH/USD seed at ${START_BLOCK - 1}: ${err?.message ?? err}`)
                return null
            })
            if (seed != null) eth = new EthUsd({id: 'last', block: START_BLOCK - 1, logIndex: 0, price: toDecimal(seed)})
        }
        const q: QuotePrices = {ethUsd: eth == null ? null : fromDecimal(eth.price), weth: WETH, stables: STABLES}

        const touched = new Map<string, Candle>()
        const getCandle = async (id: string) => touched.get(id) ?? (await store.get(Candle, id))

        for (const block of blocks) {
            const ts = Math.floor(block.header.timestamp / 1000)
            for (const log of block.logs) {
                const address = log.address.toLowerCase()
                if (log.topics[0] !== poolAbi.events.Swap.topic) continue
                const pool = byId.get(address)
                if (pool == null) continue
                const ev = poolAbi.events.Swap.decode(log)
                const swap = {sqrtPriceX96: ev.sqrtPriceX96, amount0: ev.amount0, amount1: ev.amount1,
                              block: block.header.number, logIndex: log.logIndex, timestamp: ts}
                if (indexed.has(address)) {
                    for (const {token, quote, side, pricing} of sidesOf(pool, swap, q)) {
                        for (const tf of TIMEFRAMES) {
                            const start = Math.floor(ts / tf) * tf
                            const id = candleId(address, token, tf, start)
                            const prev = await getCandle(id)
                            const next = applySwap(prev ? toState(prev) : undefined, side, tf)
                            const how = side.priceUsd != null ? pricing : (prev?.pricing ?? 'none')
                            touched.set(id, fromState(id, address, token, quote, how, next))
                        }
                    }
                }
                // The reference pool moves ETH/USD after the swaps above in the same log order.
                if (address === ETH_USD_POOL) {
                    const p0 = price0In1(ev.sqrtPriceX96, ref.decimals0, ref.decimals1)
                    const usd = ref.token1 === WETH ? inverse(p0) : p0
                    if (usd != null) {
                        q.ethUsd = usd
                        eth = new EthUsd({id: 'last', block: block.header.number, logIndex: log.logIndex,
                                          price: toDecimal(usd)})
                    }
                }
            }
        }
        await store.upsert([...touched.values()])
        if (eth != null) await store.upsert(eth)
        const last = blocks[blocks.length - 1].header
        await store.upsert(new SyncStatus({
            id: 'head', block: last.number, timestamp: Math.floor(last.timestamp / 1000),
            finalizedBlock: Math.max(0, last.number - FINALITY_BLOCKS), updatedAt: new Date(),
        }))
    })
}

main().catch((err) => {
    console.error(err)
    process.exit(1)
})
