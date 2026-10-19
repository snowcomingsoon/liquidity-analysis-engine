import {test} from 'node:test'
import assert from 'node:assert/strict'
import {
    ONE, applySwap, bucketStart, fromDecimal, inverse, orderOf, price0In1, sidesOf, toDecimal, type CandleState,
} from '../candles'

const WETH = '0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2'
const USDC = '0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48'
const TOKEN = '0x1111111111111111111111111111111111111111'

/** sqrtPriceX96 for a price of token0 in token1 raw units: sqrt(p) * 2^96. */
function sqrtX96(rawPrice: number): bigint {
    return BigInt(Math.round(Math.sqrt(rawPrice) * 2 ** 48)) * (1n << 48n)
}

test('UTC buckets', () => {
    const ts = Date.UTC(2026, 9, 19, 10, 7, 31) / 1000
    assert.equal(bucketStart(ts, 300), Date.UTC(2026, 9, 19, 10, 5) / 1000)
    assert.equal(bucketStart(ts, 900), Date.UTC(2026, 9, 19, 10, 0) / 1000)
    assert.equal(bucketStart(ts, 3600), Date.UTC(2026, 9, 19, 10, 0) / 1000)
    assert.equal(bucketStart(ts, 86400), Date.UTC(2026, 9, 19) / 1000)
})

test('price from sqrtPriceX96 with decimals, no float', () => {
    // USDC (6) / WETH (18) pool: token0 USDC, token1 WETH. 1 WETH = 2500 USDC means
    // 1 USDC = 1/2500 WETH = 4e-4, i.e. raw price 4e-4 * 1e18 / 1e6 = 4e8.
    const p = price0In1(sqrtX96(4e8), 6, 18)
    const usdc_in_weth = Number(toDecimal(p))
    assert.ok(Math.abs(usdc_in_weth - 4e-4) / 4e-4 < 1e-9)
    const weth_in_usdc = Number(toDecimal(inverse(p)!))
    assert.ok(Math.abs(weth_in_usdc - 2500) < 1e-6)
    // a meme price far below one, still exact enough
    const tiny = price0In1(sqrtX96(1e-12 * 1e18 / 1e18), 18, 18)
    assert.ok(Math.abs(Number(toDecimal(tiny)) - 1e-12) / 1e-12 < 1e-6)
})

test('decimal strings round-trip', () => {
    for (const s of ['0', '1', '2500.5', '0.000000000001234', '-3.25']) assert.equal(toDecimal(fromDecimal(s)), s)
})

test('open and close follow chain order, not arrival order', () => {
    const t = Date.UTC(2026, 9, 19, 10, 0, 10) / 1000
    const s = (block: number, li: number, price: number) => ({
        order: orderOf(block, li), timestamp: t, price: fromDecimal(String(price)), priceUsd: fromDecimal(String(price * 2)),
        amount: ONE,
    })
    const swaps = [s(101, 3, 2.0), s(100, 7, 1.0), s(101, 1, 3.0), s(100, 9, 0.5)]
    const fwd = swaps.reduce<CandleState | undefined>((c, x) => applySwap(c, x, 300), undefined)!
    const rev = [...swaps].reverse().reduce<CandleState | undefined>((c, x) => applySwap(c, x, 300), undefined)!
    for (const c of [fwd, rev]) {
        assert.equal(toDecimal(c.open), '1')        // block 100 log 7
        assert.equal(toDecimal(c.close), '2')       // block 101 log 3
        assert.equal(toDecimal(c.high), '3')
        assert.equal(toDecimal(c.low), '0.5')
        assert.equal(toDecimal(c.openUsd!), '2')
        assert.equal(toDecimal(c.closeUsd!), '4')
        assert.equal(c.swaps, 4)
        assert.equal(toDecimal(c.volumeToken), '4')
        assert.equal(toDecimal(c.volumeUsd), '13')  // 2 + 4 + 6 + 1
    }
})

test('a swap of another bucket is refused', () => {
    const t = Date.UTC(2026, 9, 19, 10, 0, 10) / 1000
    const c = applySwap(undefined, {order: 1n, timestamp: t, price: ONE, priceUsd: null, amount: ONE}, 300)
    assert.throws(() => applySwap(c, {order: 2n, timestamp: t + 300, price: ONE, priceUsd: null, amount: ONE}, 300))
})

test('USD from the swap time, unpriced when the quote has no USD value', () => {
    const swap = {sqrtPriceX96: sqrtX96(1e-6 * 1e18 / 1e18), amount0: -5n * 10n ** 18n, amount1: 5n * 10n ** 12n,
                  block: 10, logIndex: 2, timestamp: 1_790_000_000}
    // TOKEN/WETH pool, token0 TOKEN (18), token1 WETH (18): 1 TOKEN = 1e-6 WETH
    const pool = {token0: TOKEN, token1: WETH, decimals0: 18, decimals1: 18}
    const priced = sidesOf(pool, swap, {ethUsd: fromDecimal('2500'), weth: WETH, stables: new Set([USDC])})
    const tokenSide = priced.find((x) => x.token === TOKEN)!
    assert.equal(tokenSide.pricing, 'weth-ref')
    assert.ok(Math.abs(Number(toDecimal(tokenSide.side.priceUsd!)) - 0.0025) < 1e-9)
    assert.equal(toDecimal(tokenSide.side.amount), '5')                  // token units, absolute
    const before = sidesOf(pool, swap, {ethUsd: null, weth: WETH, stables: new Set([USDC])})
    assert.equal(before.find((x) => x.token === TOKEN)!.side.priceUsd, null)   // no ETH price yet: unpriced
    // the WETH side is priced against TOKEN, which has no USD value of its own
    assert.equal(priced.find((x) => x.token === WETH)!.side.priceUsd, null)
})

test('the inverse side: high of one is the inverse of the low of the other', () => {
    const pool = {token0: USDC, token1: WETH, decimals0: 6, decimals1: 18}
    const q = {ethUsd: null, weth: WETH, stables: new Set([USDC])}
    const t = 1_790_000_000
    let usdcSide: CandleState | undefined
    let wethSide: CandleState | undefined
    for (const [i, raw] of [4e8, 5e8, 3e8].entries()) {
        const sides = sidesOf(pool, {sqrtPriceX96: sqrtX96(raw), amount0: 1n, amount1: 1n, block: 1, logIndex: i, timestamp: t}, q)
        usdcSide = applySwap(usdcSide, sides.find((x) => x.token === USDC)!.side, 300)
        wethSide = applySwap(wethSide, sides.find((x) => x.token === WETH)!.side, 300)
    }
    const hiW = Number(toDecimal(wethSide!.high)), loU = Number(toDecimal(usdcSide!.low))
    assert.ok(Math.abs(hiW * loU - 1) < 1e-9)
    // WETH quoted in USDC is priced through the stable peg
    assert.ok(Math.abs(Number(toDecimal(wethSide!.highUsd!)) - hiW) < 1e-9)
})
