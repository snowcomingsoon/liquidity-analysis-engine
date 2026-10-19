import {Entity as Entity_, Column as Column_, PrimaryColumn as PrimaryColumn_, StringColumn as StringColumn_, IntColumn as IntColumn_} from "@subsquid/typeorm-store"

/**
 * An allowlisted Uniswap V3 pool, verified against the factory before indexing.
 */
@Entity_()
export class Pool {
    constructor(props?: Partial<Pool>) {
        Object.assign(this, props)
    }

    /**
     * pool address, lower case
     */
    @PrimaryColumn_()
    id!: string

    @StringColumn_({nullable: false})
    token0!: string

    @StringColumn_({nullable: false})
    token1!: string

    @IntColumn_({nullable: false})
    decimals0!: number

    @IntColumn_({nullable: false})
    decimals1!: number

    @StringColumn_({nullable: true})
    symbol0!: string | undefined | null

    @StringColumn_({nullable: true})
    symbol1!: string | undefined | null

    @IntColumn_({nullable: false})
    fee!: number

    /**
     * first block this indexer reads for the pool (START_BLOCK or later)
     */
    @IntColumn_({nullable: false})
    fromBlock!: number
}
