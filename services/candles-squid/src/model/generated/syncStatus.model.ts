import {Entity as Entity_, Column as Column_, PrimaryColumn as PrimaryColumn_, IntColumn as IntColumn_, DateTimeColumn as DateTimeColumn_} from "@subsquid/typeorm-store"

/**
 * Where indexing stands: the last block processed and an estimate of the finalized one.
 */
@Entity_()
export class SyncStatus {
    constructor(props?: Partial<SyncStatus>) {
        Object.assign(this, props)
    }

    @PrimaryColumn_()
    id!: string

    @IntColumn_({nullable: false})
    block!: number

    @IntColumn_({nullable: false})
    timestamp!: number

    @IntColumn_({nullable: false})
    finalizedBlock!: number

    @DateTimeColumn_({nullable: false})
    updatedAt!: Date
}
