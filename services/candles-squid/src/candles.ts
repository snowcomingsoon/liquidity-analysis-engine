/**
 * Candles from Uniswap V3 Swap events: pure functions, no I/O, so the
 * aggregation is tested without a chain (test/candles.test.ts).
 *
 * Prices never go through a float. A Swap carries sqrtPriceX96, the pool's
 * price after the swap as sqrt(token1/token0) in raw units times 2^96; the
 * price of token0 in token1 units is sqrtP^2 / 2^192 * 10^(dec0 - dec1). It is
 * kept as a fixed-point bigint with SCALE fractional digits, and so are the
 * USD conversions, until it is written as a decimal string.
 *
 * A candle is one side of one pool (the token priced, the other token as
 * quote) over one UTC-aligned bucket. open/close are the first and last swap
 * by (block, logIndex), whatever order the swaps arrive in; high/low are the
 * extremes of the per-swap prices of that side. The inverse side is computed
 * per swap rather than by inverting the aggregated candle, so its high is the
 * inverse of the other side's low by construction, not by a formula on the
 * aggregate. Buckets without swaps are not written: no swap is not a candle.
 */

export const SCALE = 36n
export const ONE = 10n ** SCALE
export const Q192 = 1n << 192n
export const TIMEFRAMES = [300, 900, 3600, 86400] as const

/** Position of a log on the chain: comparable across blocks. */
export function orderOf(block: number, logIndex: number): bigint {
    return BigInt(block) * 1_000_000n + BigInt(logIndex)
}

export function bucketStart(timestampS: number, timeframe: number): number {
    return Math.floor(timestampS / timeframe) * timeframe
}

/** Price of token0 in token1 units, fixed point (SCALE digits). */
export function price0In1(sqrtPriceX96: bigint, decimals0: number, decimals1: number): bigint {
    let num = sqrtPriceX96 * sqrtPriceX96 * ONE
    let den = Q192
    const d = decimals0 - decimals1
    if (d >= 0) num *= 10n ** BigInt(d)
    else den *= 10n ** BigInt(-d)
    return num / den
}

/** 1 / x in fixed point; null for a zero price (an empty pool side). */
export function inverse(x: bigint): bigint | null {
    return x > 0n ? (ONE * ONE) / x : null
}

export function mul(a: bigint, b: bigint): bigint {
    return (a * b) / ONE
}

/** A raw token amount (wei-like) in token units, fixed point, absolute. */
export function amountOf(raw: bigint, decimals: number): bigint {
    const abs = raw < 0n ? -raw : raw
    return (abs * ONE) / 10n ** BigInt(decimals)
}

export function toDecimal(x: bigint): string {
    const neg = x < 0n
    const abs = neg ? -x : x
    const whole = abs / ONE
    let frac = (abs % ONE).toString().padStart(Number(SCALE), '0').replace(/0+$/, '')
    return `${neg ? '-' : ''}${whole}${frac ? '.' + frac : ''}`
}

export function fromDecimal(s: string): bigint {
    const neg = s.startsWith('-')
    const [w, f = ''] = (neg ? s.slice(1) : s).split('.')
    const v = BigInt(w || '0') * ONE + BigInt((f + '0'.repeat(Number(SCALE))).slice(0, Number(SCALE)) || '0')
    return neg ? -v : v
}

export interface SwapSide {
    order: bigint
    timestamp: number
    /** price of the side in quote units */
    price: bigint
    /** price in USD, null when it could not be priced at that swap */
    priceUsd: bigint | null
    /** absolute amount of the side, in its own units */
    amount: bigint
}

export interface CandleState {
    start: number
    timeframe: number
    openOrder: bigint
    closeOrder: bigint
    open: bigint
    high: bigint
    low: bigint
    close: bigint
    openUsd: bigint | null
    highUsd: bigint | null
    lowUsd: bigint | null
    closeUsd: bigint | null
    /** order of the swaps that set openUsd / closeUsd */
    openUsdOrder: bigint | null
    closeUsdOrder: bigint | null
    volumeToken: bigint
    volumeUsd: bigint
    swaps: number
    pricedSwaps: number
}

/**
 * The candle with one more swap. Idempotence is the store's job (a batch is
 * applied once, atomically with its checkpoint, and rolled back on a reorg);
 * this only guarantees that the result does not depend on arrival order.
 */
export function applySwap(c: CandleState | undefined, s: SwapSide, timeframe: number): CandleState {
    const start = bucketStart(s.timestamp, timeframe)
    if (c == null) {
        return {
            start, timeframe,
            openOrder: s.order, closeOrder: s.order,
            open: s.price, high: s.price, low: s.price, close: s.price,
            openUsd: s.priceUsd, highUsd: s.priceUsd, lowUsd: s.priceUsd, closeUsd: s.priceUsd,
            openUsdOrder: s.priceUsd == null ? null : s.order,
            closeUsdOrder: s.priceUsd == null ? null : s.order,
            volumeToken: s.amount,
            volumeUsd: s.priceUsd == null ? 0n : mul(s.amount, s.priceUsd),
            swaps: 1,
            pricedSwaps: s.priceUsd == null ? 0 : 1,
        }
    }
    if (c.start !== start || c.timeframe !== timeframe) throw new Error('swap outside the candle')
    const n: CandleState = {...c}
    if (s.order < n.openOrder) {
        n.openOrder = s.order
        n.open = s.price
    }
    if (s.order > n.closeOrder) {
        n.closeOrder = s.order
        n.close = s.price
    }
    if (s.price > n.high) n.high = s.price
    if (s.price < n.low) n.low = s.price
    n.volumeToken += s.amount
    n.swaps += 1
    if (s.priceUsd != null) {
        n.pricedSwaps += 1
        n.volumeUsd += mul(s.amount, s.priceUsd)
        if (n.highUsd == null || s.priceUsd > n.highUsd) n.highUsd = s.priceUsd
        if (n.lowUsd == null || s.priceUsd < n.lowUsd) n.lowUsd = s.priceUsd
        if (n.openUsdOrder == null || s.order < n.openUsdOrder) {
            n.openUsdOrder = s.order
            n.openUsd = s.priceUsd
        }
        if (n.closeUsdOrder == null || s.order > n.closeUsdOrder) {
            n.closeUsdOrder = s.order
            n.closeUsd = s.priceUsd
        }
    }
    return n
}

export interface PoolInfo {
    token0: string
    token1: string
    decimals0: number
    decimals1: number
}

export interface QuotePrices {
    /** ETH in USD, fixed point, as of the swap; null before the first reference swap */
    ethUsd: bigint | null
    weth: string
    stables: ReadonlySet<string>
}

/** USD value of one unit of `token`, as of the swap, or null. */
export function usdOf(token: string, q: QuotePrices): {usd: bigint | null; how: 'weth-ref' | 'stable-peg' | 'none'} {
    const t = token.toLowerCase()
    if (t === q.weth) return {usd: q.ethUsd, how: q.ethUsd == null ? 'none' : 'weth-ref'}
    if (q.stables.has(t)) return {usd: ONE, how: 'stable-peg'}
    return {usd: null, how: 'none'}
}

/**
 * Both sides of one swap. The USD price of a side is its price in the other
 * token times that token's USD value at the same swap; a side whose quote has
 * no USD value (neither WETH nor a listed stablecoin) stays unpriced, never
 * priced with a later or a guessed value.
 */
export function sidesOf(
    pool: PoolInfo,
    swap: {sqrtPriceX96: bigint; amount0: bigint; amount1: bigint; block: number; logIndex: number; timestamp: number},
    q: QuotePrices,
): {token: string; quote: string; side: SwapSide; pricing: string}[] {
    const p0 = price0In1(swap.sqrtPriceX96, pool.decimals0, pool.decimals1)
    const p1 = inverse(p0)
    const order = orderOf(swap.block, swap.logIndex)
    const out = []
    const sides: [string, string, bigint | null, bigint, number][] = [
        [pool.token0, pool.token1, p0, swap.amount0, pool.decimals0],
        [pool.token1, pool.token0, p1, swap.amount1, pool.decimals1],
    ]
    for (const [token, quote, price, raw, dec] of sides) {
        if (price == null || price === 0n) continue
        const qu = usdOf(quote, q)
        out.push({
            token, quote,
            side: {order, timestamp: swap.timestamp, price, priceUsd: qu.usd == null ? null : mul(price, qu.usd), amount: amountOf(raw, dec)},
            pricing: qu.how,
        })
    }
    return out
}
