module.exports = class Data1792406000049 {
    name = 'Data1792406000049'

    async up(db) {
        await db.query(`CREATE TABLE "pool" ("id" character varying NOT NULL, "token0" text NOT NULL, "token1" text NOT NULL, "decimals0" integer NOT NULL, "decimals1" integer NOT NULL, "symbol0" text, "symbol1" text, "fee" integer NOT NULL, "from_block" integer NOT NULL, CONSTRAINT "PK_db1bfe411e1516c01120b85f8fe" PRIMARY KEY ("id"))`)
        await db.query(`CREATE TABLE "candle" ("id" character varying NOT NULL, "pool" text NOT NULL, "token" text NOT NULL, "quote" text NOT NULL, "timeframe" integer NOT NULL, "start" integer NOT NULL, "open_order" numeric NOT NULL, "close_order" numeric NOT NULL, "open" text NOT NULL, "high" text NOT NULL, "low" text NOT NULL, "close" text NOT NULL, "open_usd" text, "high_usd" text, "low_usd" text, "close_usd" text, "volume_token" text NOT NULL, "volume_usd" text NOT NULL, "swaps" integer NOT NULL, "priced_swaps" integer NOT NULL, "pricing" text NOT NULL, CONSTRAINT "PK_e4bfba00b826f30058f10eb59d0" PRIMARY KEY ("id"))`)
        await db.query(`CREATE INDEX "idx_candle_start_e13bf911" ON "candle" ("start") `)
        await db.query(`CREATE UNIQUE INDEX "idx_candle_pool_token_timeframe_start_00a30dca" ON "candle" ("pool", "token", "timeframe", "start") `)
        await db.query(`CREATE TABLE "eth_usd" ("id" character varying NOT NULL, "block" integer NOT NULL, "log_index" integer NOT NULL, "price" text NOT NULL, CONSTRAINT "PK_c62bfbf14c9e8df2a177d6baefb" PRIMARY KEY ("id"))`)
        await db.query(`CREATE TABLE "sync_status" ("id" character varying NOT NULL, "block" integer NOT NULL, "timestamp" integer NOT NULL, "finalized_block" integer NOT NULL, "updated_at" TIMESTAMP WITH TIME ZONE NOT NULL, CONSTRAINT "PK_86336482262ab8d5b548a4a71b7" PRIMARY KEY ("id"))`)
    }

    async down(db) {
        await db.query(`DROP TABLE "sync_status"`)
        await db.query(`DROP TABLE "eth_usd"`)
        await db.query(`DROP INDEX "public"."idx_candle_pool_token_timeframe_start_00a30dca"`)
        await db.query(`DROP INDEX "public"."idx_candle_start_e13bf911"`)
        await db.query(`DROP TABLE "candle"`)
        await db.query(`DROP TABLE "pool"`)
    }
}
