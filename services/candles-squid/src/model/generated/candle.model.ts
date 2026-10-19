import {Entity as Entity_, Column as Column_, PrimaryColumn as PrimaryColumn_, Index as Index_, StringColumn as StringColumn_, IntColumn as IntColumn_, BigIntColumn as BigIntColumn_} from "@subsquid/typeorm-store"

/**
 * One candle of one side of one pool. `token` is the side priced, `quote` the
 * other token of the pool. Prices are decimal strings (exact fixed point, 36
 * fractional digits before trimming): open/high/low/close in `quote` units, the
 * *Usd ones in US dollars at the time of each swap (null when no swap of the
 * bucket could be priced). Volumes: `volumeToken` in `token` units, `volumeUsd`
 * in US dollars over the priced swaps only.
 */
@Index_("idx_candle_pool_token_timeframe_start_00a30dca", ["pool", "token", "timeframe", "start"], {unique: true})
@Entity_()
export class Candle {
    constructor(props?: Partial<Candle>) {
        Object.assign(this, props)
    }

    /**
     * pool-token-timeframe-start
     */
    @PrimaryColumn_()
    id!: string

    @StringColumn_({nullable: false})
    pool!: string

    @StringColumn_({nullable: false})
    token!: string

    @StringColumn_({nullable: false})
    quote!: string

    /**
     * seconds: 300, 900, 3600, 86400
     */
    @IntColumn_({nullable: false})
    timeframe!: number

    /**
     * bucket start, unix seconds, aligned in UTC
     */
    @Index_("idx_candle_start_e13bf911")
    @IntColumn_({nullable: false})
    start!: number

    /**
     * block * 1e6 + logIndex of the first and last swap in the bucket
     */
    @BigIntColumn_({nullable: false})
    openOrder!: bigint

    @BigIntColumn_({nullable: false})
    closeOrder!: bigint

    @StringColumn_({nullable: false})
    open!: string

    @StringColumn_({nullable: false})
    high!: string

    @StringColumn_({nullable: false})
    low!: string

    @StringColumn_({nullable: false})
    close!: string

    @StringColumn_({nullable: true})
    openUsd!: string | undefined | null

    @StringColumn_({nullable: true})
    highUsd!: string | undefined | null

    @StringColumn_({nullable: true})
    lowUsd!: string | undefined | null

    @StringColumn_({nullable: true})
    closeUsd!: string | undefined | null

    @StringColumn_({nullable: false})
    volumeToken!: string

    @StringColumn_({nullable: false})
    volumeUsd!: string

    @IntColumn_({nullable: false})
    swaps!: number

    @IntColumn_({nullable: false})
    pricedSwaps!: number

    /**
     * how USD was obtained: weth-ref (ETH/USD from the reference pool), stable-peg (quote is a USD stablecoin, taken at 1), none
     */
    @StringColumn_({nullable: false})
    pricing!: string
}
