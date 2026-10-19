import {Entity as Entity_, Column as Column_, PrimaryColumn as PrimaryColumn_, IntColumn as IntColumn_, StringColumn as StringColumn_} from "@subsquid/typeorm-store"

/**
 * The last ETH/USD price seen on the reference pool, as of (block, logIndex).
 */
@Entity_()
export class EthUsd {
    constructor(props?: Partial<EthUsd>) {
        Object.assign(this, props)
    }

    @PrimaryColumn_()
    id!: string

    @IntColumn_({nullable: false})
    block!: number

    @IntColumn_({nullable: false})
    logIndex!: number

    @StringColumn_({nullable: false})
    price!: string
}
