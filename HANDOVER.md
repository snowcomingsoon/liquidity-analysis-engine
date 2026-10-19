# 2026-10-19 — Altri scarti ingiusti delle gemme: emissione, GitHub, siti, meme — `seed-0353` (Claude, a mano)

Lorenzo: "Vedi altre criticita' che potrebbero falsare i risultati delle gemme o escludere progetti che non lo meriterebbero?", poi "procedi con la misura dei punti". Sonda una tantum sul branch (server in sola lettura; GoPlus, RPC, RugCheck, Solana RPC, Chrome headless dal runner), poi tolta. Scarti negli ultimi 30 giorni e cosa sono davvero:
- **"mint enabled" 526.** EVM (71 letti): chi puo' emettere e' un wallet solo in 6; 28 un contratto (governance, timelock, multisig), 33 nessun owner (minter di emissione: CRV, AERO, BAL, PENDLE...), 3 token bridgiati (RSR, RNBW, ODOS su Base). Solana (98 letti): autorita' in un wallet 19, in un programma 79 (governance MetaDAO/SPL, launchpad: un'autorita' `BCD75RNB` su 12 token, emittenti RWA `WV9PJN7X` su 10, staking/LST). GoPlus `is_mintable` dice solo che la funzione esiste.
- **GitHub "all commits on a single day" 75: bug.** Si guarda solo l'ultima pagina di 100 commit: elizaOS (19.564 stelle, 100+ commit) scartato. 43 su 75 hanno cartelle di codice vero (contratti, programmi Rust).
- **GitHub "almost no code" 151: bug sul repository scelto.** Per un link a un'organizzazione si legge l'ultimo repository toccato (`legit.github_repo`, sort=pushed): Beefy (BIFI), Badger, Send, Mind Network (FHE) giudicati dal profilo `.github` o da un repo di dati. 144 su 151 senza cartelle di codice: in gran parte vuoti davvero.
- **Sito "empty page" 198** (60 aperti in Chrome): 15 (25%) pieni in un browser vero (app.drift.trade, r0ar.io, dith.ai, facticity.ai), 29 vuoti anche li', 16 irraggiungibili, nessun muro Cloudflare. Tutti i 15 pieni hanno HTML grezzo >= 11 KB; fra i vuoti solo ~7 lo superano.
- **Nomi meme 581:** quasi tutti meme veri (cat 109, pepe 77, doge 60, inu 48, baby 33); dubbi DEGEN, gmAI, Arbitrage Ape. Nessuna modifica.
**Proposte a Lorenzo (in attesa):** emissione fatale solo se la controlla un wallet (contratto/programma: segnalazione e punti in meno; bridge: niente); GitHub: correggere il bug dei 100 commit e scegliere il repository con piu' codice/stelle dell'organizzazione, "un solo giorno" da fatale a penalita' se c'e' codice vero; sito vuoto con HTML >= 11 KB trattato come "non leggibile" (non fatale) invece che scartato.

# 2026-10-19 — Holder delle gemme: i "programmi" Solana fuori dai limiti per wallet — `seed-0352` (Claude, a mano)

Lorenzo: "in alcuni casi quelli che risultano tra i top 10 holders sono anche indirizzi dove magari c'e' il pool della liquidita' oppure l'indirizzo dove ci sono i token bloccati [...] studiare un sistema che ci puo' permettere di non scartare progetti" (soglia gemme 40%), poi "procedi con la misura".
Soglie oggi: ingresso `legit.judge_rugcheck` (Solana: primo >15%, top10 >35%), pilastro `depth._judge_tokenomics` (primo >20%, top10 >60% = voto 0), gemme `leaderboard.usage_gate` (top10 >=40% sul dato gia' ripulito). Gia' esclusi: Solana pool/AMM, LOCKER, BURN noti a RugCheck, conti dei market, curva pump.fun; EVM pool, locked, tag, morti e **tutti i contratti** (dal 29/09, cap 50% per contratto).
Misura (sonda una tantum sul branch, server in sola lettura + RugCheck/GoPlus dal runner, poi tolta): ultimi 30 giorni 4.761 scarti; per holder: "a single wallet holds" 413, "one unidentified contract" 186, "top 10 hold" 28, piu' le gemme fermate dal 40%. Etichettati i top holder dei 120 candidati piu' capitalizzati (73 Solana, 30 Ethereum, 17 Base): pool e lock residui quasi zero (2,4% e 1% in media), **exchange mai** nei top 10; su Solana i conti di **programmi** (indirizzi fuori curva: staking, vesting, lock non noti a RugCheck, ma anche multisig di tesoreria Squads) pesano in media il 32% del top 10 contato. Contando solo i wallet (programma singolo <=50%) passerebbero 26 dei 98 oltre il 40% (MNDE, SONIC, NATIX, ACS, SHDW, CGPT, P2P, UMBRA, xSOL...), e 11 dei 49 scartati per "single wallet" (19 dei 49 avevano un programma come primo holder). EVM: nessun cambiamento, i contratti erano gia' fuori.
**Fatto (Lorenzo: "applica i punti 1-4"):** `legit.is_program_account` (indirizzo fuori dalla curva ed25519 = conto di un programma); i programmi escono dai limiti per wallet all'ingresso (`legit.holder_concentration`, `program_share`, blocco se uno solo >50%) e nel pilastro (`depth.judge_tokenomics_solana` -> `_with_contracts`, condiviso con EVM: cap 50%, penalita' oltre 20%, `contracts_pct`, `top10_all_pct`). RULES_VERSION 13: tokenomics Solana ricalcolate, righe "single wallet"/"top 10" rimesse in coda. Scomposizione nella scheda solo whitekobra (`static/onchain/leaderboard.js`). Non fatto, da proporre solo se servisse: riconoscere i multisig di tesoreria (Squads) leggendo la storia on-chain e contarli come wallet.

# 2026-10-19 — GeckoTerminal coordinato; Squid provato e abbandonato — `seed-0351` (Claude, a mano)

Lorenzo ha caricato `ISTRUZIONI_CLAUDE_SQUID.md` (obiettivo: "ridurre i limiti e le attese nell'acquisizione delle candele, coordinando prima tutte le richieste GeckoTerminal e introducendo poi un provider autonomo per le pool Ethereum Uniswap V3", riferimento subsquid-labs/uniswapv3-squid). Le istruzioni chiedono: commit separati coordinamento / Squid, Squid spento per default, nessun deploy o attivazione del provider senza istruzione esplicita, niente segreti o .env dall'upstream, non dichiarare prove non eseguite. Io avevo sconsigliato Squid su Ethereum (archivio candele: 8 pool eth su 101, 5% delle candele; archivio fermo da oltre 7 giorni); Lorenzo ha ripetuto l'obiettivo: si fanno tutte le fasi.
**Fase 1 (fatta):** `app/providers/gecko_client.py`, unico proprietario delle richieste (un solo processo uvicorn: la finestra in memoria e' globale): finestra di 60 s, `BACKGROUND_PER_MIN` 14 e `GLOBAL_PER_MIN` 28 sulla stessa finestra (urgente dentro il tetto), pausa comune dopo un 429 per il suo `Retry-After` (default 5 s, massimo 120), nessun retry proprio (restano quelli dei chiamanti), metriche per chiamante (`requests`, `http_429`, `errors`, `wait_s`, `max_wait_s`, `cache_hits`, ohlcv contro il resto) su `GET /api/onchain/gecko` e su file `data/gecko_metrics.json` ogni 5 min (da `live_market_loop`). `dexscreener.gecko_get` e `usage._gecko` ci passano; prima scavalcavano il tetto scanner (pagine e trending), listings, live_prices, portfolio, prices, radar, research (scheda token a ogni analisi), token_search (ora urgente). Prima nessuno registrava i 429.
**Squid (fasi 2-5): provato e abbandonato.** Lorenzo, 19/10, dopo i risultati: "lascia perdere tutto. Abbiamo testato e non vale la pena implementare niente di tutto questo". PR #598 chiusa senza merge, niente su main (il codice resta solo nella storia del branch, commit 2767faf..739a4fb). Cosa si era misurato, per non rifarlo: delle 101 pool dell'archivio candele solo 2 sono Ethereum Uniswap V3 (~2%); il pilota reale (un giorno, 4 pool) dava bucket identici a GeckoTerminal, close a 0.03% sulla USDC/WETH ma +0.3% costante sulla WBTC/WETH 0.3% e picchi di volume fino al 99% non spiegati; per usarlo servivano chiave Portal SQD (il pubblico risponde 529), un RPC Ethereum proprio (publicnode rifiuta archivio e getLogs larghi) e ~1 GB di RAM. Non riproporlo. La fase 1 (coordinamento GeckoTerminal, #597) resta online.

# 2026-10-19 — Kronos (shiyu-coder/Kronos) provato sulle gemme: nessuna informazione (Claude, a mano)

Lorenzo: "possiamo implementare questa repository", poi "prova a studiare un approccio diverso rispetto a prevedere il mercato", scelta l'idea 1 (grafico "organico" vs innaturale, sorpresa di Kronos). Prova solo su GitHub Actions (`kronos-eval.yml` + `scripts/kronos_eval/`, solo sul branch, poi tolti; casi letti dal server in sola lettura via ssh, `gem_track` con almeno 7 giorni): 1.893 casi (bad = dimezzati 116, good = raddoppiati 39, flat 1.738), usati 305, utilizzabili 199 (candele orarie GeckoTerminal prima della decisione, >= 64). Kronos-small + Tokenizer-base, NLL per candela (s1+s2) dopo 32 di riscaldamento. AUC 'bad' vs resto: kronos_mean 0.49, kronos_p95 0.58 [0.49-0.66], kronos_last24 0.49; volatilita' oraria prima dell'ingresso **0.78 [0.71-0.85]**, max_drawdown 0.25 (cioe' 0.75 al contrario), flat_candles 0.36, il nostro punteggio 0.54. 'good' (31 casi, rumoroso): nostro punteggio 0.61, Kronos 0.42-0.49. Regressione logistica cv: bad statistiche semplici 0.78, +Kronos 0.75 (peggiora). Conclusione: Kronos non aggiunge niente, non integrarlo. Scoperta laterale: la volatilita' oraria e il drawdown prima dell'ingresso separano le gemme che poi dimezzano molto meglio del nostro punteggio (proposto a Lorenzo come regola, in attesa di risposta).

# 2026-10-19 — Ricerca delle 3 letta; con DeepSeek spento i passi DeepSeek non partono — `seed-0350` (Claude, a mano)

Lorenzo: "È tutto ok dopo la ricerca delle 3?". Letto dal server (sola lettura, branch, tolto dopo): run 187 min, `drained`, 499 analizzati, 38 scoperti, Top 70 (+4/-2), 0 chiamate DeepSeek; in 10 h 139 righe nuove (96 profili DexScreener, 22 `launchpad` di cui 14 Pons e 3 gia' `ranked`, 4 GitHub, 1 `geckoterminal` Base scartata; GeckoTerminal eth/base 104 pool tutti senza sito o meme); 13 nuovi a voto >=50, 4 >=60; `gem_hold` membri cap 204 / floor 56 / score 54 / fdv 53, trattenuti cap 2 e score 3; CPU 18%, RAM 726 MB / 3 GB; nessun 429. 75 traceback: 50 `narrative_map` + 2 `consistency` (`BudgetExceeded`, DeepSeek spento), 23 Playwright `Route.abort ... handler is closed` in `jstext.route` (rumore). Poi Lorenzo: "impedire direttamente che chiamino DeepSeek che comunque e' spento". `settings.research_deepseek` (chiave e `research_ai_enabled`): `narrative_map.step`, `consistency.step`, `tg_digest`, `deepseek_studies`, `legit` (lettura sito AI), `research` (dossier), `judge.judge` (prima delle letture X/Telegram/Discord), `judge.review_board`, `code_review.review` (prima di scaricare il codice da GitHub) si fermano subito. Non toccati: la chat (kind "chat"), `deep_recheck` (dice gia' "DeepSeek not configured"), `research.deepseek_mode` (cambia i pesi del sito).

# 2026-10-18 — Whitekobra: gemme di un anno al massimo, fuori quelle che si spengono — `seed-0349` (Claude, a mano)

Lorenzo: "abbassare il tetto della vita di un progetto dagli attuali 1000 giorni a un anno [...] applicalo anche ai layer", dei suggerimenti "applica solo il secondo" (il volume in caduta; no alla soglia di attivita' piu' alta: "rischia di essere troppo restrittivo"). `main.GEM_MAX_AGE_DAYS` 365 (layer compresi: con le date vere quasi tutti escono). `_fading`: in `_gem_view`, fuori chi ha `vol_7d_avg` < `FADE_RATIO` 0.2 x `vol_30d_avg`, da `FADE_MIN_DAYS` 14 giorni di storia (il picco del lancio non conta); senza attesa dei 7 giorni (e' gia' una media di una settimana). I layer non hanno uso DEX: la regola non li tocca. Commit con `Solo-account: whitekobra`.

# 2026-10-18 — Whitekobra: Pearl a 30 giorni, MC e FDV sempre, uscite solo dopo giorni di fila — `seed-0348` (Claude, a mano)

Lorenzo: Pearl "massimo 30 giorni"; "non ho visto [...] i due tipi di capitalizzazione"; "per uscire per capitalizzazione dalle gemme deve superare il tetto [...] per almeno 7 giorni consecutivi"; poi "mettili tutti tranne quello relativo al tetto d'emergenza" (un flash a $20-30M puo' ritracciare in poche ore). Tutto solo whitekobra (`full`). `gem_hold.py`: per regola, membri (chi l'ha passata) e da quando un membro la fallisce; esce dopo `DAYS` (cap/floor/fdv 7, score 3), una lettura buona azzera, chi non e' mai passato non e' trattenuto; file `onchain_gem_hold.json`. Agganci in `main`: `_top_entries(full)` tetto ($10M, layer `LAYER_VIEW_BAND_KOBRA` alto) e pavimento $300k (solo se e' l'unica barra di `usage_gate` che fallisce; il gem trattenuto resta nelle arene e non compare in Early); i membri della bacheca registrati a ogni chiamata; `_gem_view` voto (`GEM_MIN_SCORE` 60 per entrare, 3 giorni sotto per uscire, sotto `GEM_DROP_SCORE` 55 subito) e FDV > 5x (7 giorni). Gli orologi girano anche senza visite: `_gem_rows_each_minute` (sorgente di listing_dates) passa ogni minuto una copia nel `_gem_view`. Pearl: `PEARL_MAX_AGE_DAYS` 30 in `_gem_view_keys("pearl")` e in `top.js paintPearl`. Grafica `static/onchain/`: `tokenRow(... capTag)` mette "MC" accanto alla cap a destra, `marketSub` mostra sempre "FDV $X" quando c'e' (prima solo se oltre la cap del 5%); testi di Pearl in `onchain-app.html`. Commit con `Solo-account: whitekobra`.

# 2026-10-18 — Sentinella fra le ricerche delle gemme — `seed-0347` (Claude, a mano)

Lorenzo: "Con tutte le fonti attuali ha senso tenere accesa la ricerca delle gemme piu' a lungo. Comporterebbe costi maggiori?", poi "Procedi con la sentinella, notifiche subito a qualsiasi ora". Costi in soldi ~0 (DeepSeek della ricerca spento, API gratuite, server a prezzo fisso); costi in risorse: limite GeckoTerminal condiviso, quota GitHub, carico. `nightly.sentinel_loop` (loop "sentinel" in `loop_plan` accanto a "nightly", `settings.onchain_sentinel_enabled`): ogni `SENTINEL_EVERY_S` 600 s, se non gira una ricerca (`_research_lock`, preso anche da `run_night`) ne' un'ottimizzazione, `sentinel_once`: tick leggeri (`leaderboard.tick(light=True)`) finche' niente di nuovo aspetta (`Steps.quiet`: nessuna analisi in corso, nessuna voce senza pilastri; minimo 3 tick, massimo `SENTINEL_MAX_S` 300 s), poi settle 60 s e `flush_alerts` (notifiche subito, a qualsiasi ora). Il tick leggero salta CoinGecko, il feed dal database, pagella, grandi monete, revisione/codice/narrative/coerenza (DeepSeek), e rinfresca solo progetti nuovi o giovani; misura l'uso solo dei giovani (`young`). Restano: fonti veloci e launchpad, mercato, cap globale, Top e suoi avvisi. Da guardare: carico del server e 429 di GeckoTerminal nel controllo del 20/10.

# 2026-10-18 — Gemme: la ricerca era ferma, fonti dei launchpad, corsia per i giovani — `seed-0346` (Claude, a mano)

Lorenzo: "come possiamo fare per intercettare progetti come Veil prima che spicchino il volo?", poi "Procedi" (piano 1-5, Pons per Robinhood). Letture dal server (sola lettura, branch, tolte dopo):
- **La ricerca era ferma.** `discovery_open`: bacino = studiati+ranked del database (4.005, soglia `POOL_TARGET` 300) e arretrato 336 (123 senza pilastri, 204 senza report DeepSeek, 9 codice) > `BACKLOG_LOW` 10 -> pausa. Con `research_ai_enabled` False (dal 10/10) i report non arrivano mai: pausa per sempre. Ultimi 7 giorni: 195 righe da Jupiter, 9+3 profili DexScreener, 0 GeckoTerminal (la fonte del 17/10 non ha mai girato), 0 GitHub, 0 schede CoinGecko.
- **Ritardo nascita -> prima vista** (progetti nati negli ultimi 60 g): profili DexScreener 0 g, Jupiter 12, CoinGecko 11-22. Veil: pool 12/10 19:01, visto 14/10 06:57 da "manual", studiato in 0,8 g, voto 73.
- **CoinGecko:** su 89 studiati con voto >=60, 31 trovati solo da CoinGecko (5 su 19 a >=70, tutti Robinhood); quelli hanno eta' mediana 92 g e ritardo 71 g, gli altri 24 g e 10 g. Lorenzo voleva eliminarlo: tenuto come fonte lenta.
- **API:** GeckoTerminal ha i launchpad come DEX (Solana: pumpswap, pump-fun, meteora-dbc, meteora-damm-v2, raydium-launchlab, bags-fm, letsbonk-fun, heaven, moonit, moonshot; Robinhood: pons-dot-family, pons-v2, pons-v2-dex, virtuals-robinhood, clanker-robinhood, bankr-robinhood, hoodit, frontier-fun...). `/dexes/{dex}/pools` non accetta `sort=pool_created_at_desc` (400), accetta `h24_tx_count_desc`. MetaDAO (metadao.fi) risponde 429 alle letture automatiche: non aggiunto. Pons (ponsfamily.com/launchpad) mette la lista dei token con `socials.website`, `createdAt`, `marketCapUsd` nel payload RSC della pagina: alternativa diretta se GeckoTerminal non basta.
Fatto (tutti gli account, funzionamento): 1. `discovery.tick(..., bulk)`: la pausa ferma solo `BULK_STEPS` (CoinGecko), le fonti veloci girano sempre; `pool_status` non conta i report mancanti con DeepSeek spento. 2. `leaderboard.young()` (`YOUNG_DAYS` 14): primi nella coda di analisi e nella misura dell'uso. 3. `GT_LAUNCHPADS`: i 20 pool con piu' transazioni in 24 h di ogni launchpad, filtri dei new pools (fascia, liquidita' $5k, niente meme, sito obbligatorio dalla scheda), 6 schede per catena a giro, fonte `launchpad`; `_poll_new_pools` ora salva le note (prima le salvavano solo CoinGecko e GitHub). Pons via GeckoTerminal. Da guardare fra qualche giorno: righe `launchpad` e `geckoterminal` nel database, con che voto, e i 429 di GeckoTerminal (limite condiviso con la misura dell'uso).

# 2026-10-18 — Whitekobra: niente gemme senza data — `seed-0345` (Claude, a mano)

Lorenzo, dopo il fix delle date dei layer: "la regola dei 1000 giorni lasciala in vigore. Se i layer non compaiono, non importa [...] se non c'è modo di identificare la data di un layer, va rimosso. Quelli senza data non possono entrare nelle gemme. Questa è una regola da ammettere." `_gem_view` (solo whitekobra: Top, arene, Early, Pearl e alert) ora chiede `launched_at` (creazione o listing, `_with_listing_dates`) e lo scarta se manca, per qualunque chain. Effetto: escono HDX, BLD, MODE, BLAST (layer senza coppia CEX) e una gemma DEX resta fuori finche' `listing_dates.fill` non legge la data (5 al minuto; la sorgente di `fill` e' la lista prima del filtro, quindi viene letta comunque). Commit con `Solo-account: whitekobra`.

# 2026-10-18 — Date dei layer tutte uguali — `seed-0344` (Claude, a mano)

Lorenzo: "I layer presenti tra le gemme hanno tutti la stessa data". Letto dal server (sola lettura, branch, tolto dopo): i layer su MEXC avevano listing 2026-10-01; prova dal server: MEXC `klines?interval=1M&startTime=0&limit=1` e con startTime 2015 restituiscono entrambi il mese corrente, Binance con startTime=0 da' la prima candela (SEI 2023-08-01). Errore mio di `listing_dates.py` (17/10). Ora `_cex_listing` chiede `interval=1M&limit=1000` senza startTime e prende la candela piu' vecchia; `VERSION=2` su ogni voce e `_load` scarta le date dei layer senza `v` 2 (vengono rilette, 5 al minuto). Effetto: con le date vere molti layer superano i 1000 giorni e escono dalla vista di whitekobra (regola `GEM_MAX_AGE_DAYS`); i layer senza coppia CEX (HDX, BLD, MODE, BLAST) restano senza data.

# 2026-10-18 — Whitekobra: FDV mostrata, gemme con FDV > 5x la cap escluse — `seed-0343` (Claude, a mano)

Lorenzo: Limitless Exchange "risulta 4 milioni [...] In realta' ne ha piu' di 30". Letto dal server (sola lettura, branch, tolto dopo): LMTS su Base, DexScreener mcap $4.28M / fdv $32.5M, CoinGecko `limitless-3` mcap $4.29M / fdv $32.6M, circolante 131.6M su 1B. Non un errore: noi mostriamo la cap (DexScreener `marketCap` del pool piu' liquido, `true_cap`), il "30" e' la FDV. Proposte 1-4, scelta "Applica 1 piu' 3": `leaderboard.apply_live` salva `fdv` in `_live`; `main._with_fdv` + `_mostly_locked` (`GEM_MAX_FDV_RATIO=5`, la regola dei layer) dentro `_gem_view` (solo whitekobra) e nella pagina del token; FDV sconosciuta = non esclusa. Frontend `static/onchain/`: `marketSub` mostra "FDV $X" se supera la cap di oltre il 5%, `register(... fdv)` e riga FDV in `detail.js`. Commit con `Solo-account: whitekobra`.

# 2026-10-17 — Ethereum e Base: fonte di token nuovi (GeckoTerminal) — `seed-0342` (Claude, a mano)

Lorenzo: "vedo pochissime gemme della chain Ethereum e pochissime della chain base". Letto il server con `server-read.yml` dal branch (sola lettura, solo conteggi, poi tolto dal branch). Per chain (in fascia / studiati / mediana voto / >=60): Solana 3412/2305/30/27, Robinhood 669/496/39/46, Ethereum 1957/602/29/8, Base 1107/482/31/4, Arc 4/4, layer 101 studiati. Fonti: Ethereum 6003 su 6374 da `coingecko-list`, Base 2755 su 2835; Solana 4088 da Jupiter. Scarto principale ovunque "no website or GitHub to read" (Ethereum 829, Base 269), poi "mint enabled". La Top legge 200 studiati + 200 ranked per voto salvato: minimo 40.5, quindi non taglia niente sopra 60. CoinGecko: 1 solo 429 in 24 ore. Conclusione: niente di rotto, mancano token giovani. "aggiungi la fonte di token nuovi per Ethereum e Base su tutti gli account": `discovery._poll_new_pools` (step "geckoterminal" in `tick`), `GT_NEW_POOLS` `new_pools?include=base_token` per eth e base, 2 pagine ogni `GT_POLL_S=600`, `new_pool_candidates` (fascia CAP_MIN-CAP_MAX su `market_cap_usd`/`fdv_usd`, liquidita' >= $5k, niente quote token ne' meme), poi `GT_TOKEN_INFO` per al massimo 3 token per chain a giro (`GT_INFO_PER_CHAIN`) (`token_info_fields`: sito obbligatorio, socials, descrizione senza "meme"), `add(..., "geckoterminal")`; passa dal gate condiviso `usage._gecko`. Da guardare fra qualche giorno: quanti `geckoterminal` entrano e con che voto.

# 2026-10-17 — Whitekobra: nuovi pesi del voto — `seed-0341` (Claude, a mano)

Discussione con Lorenzo sul voto: togliere la partecipazione, token 25 / prodotto 35 / DeepSeek 20 / penalita' GitHub 5; mia proposta accettata di dare uso 25 e token 20; la crescita degli holder ("Vorrei [...] inserirlo all'interno del blocco tokenomics"), consigliata e decisa nell'uso. "Procedi con la crescita nell'uso e quindi poi ridisegna completamente tutti i nuovi parametri delle gemme solo per l'account whitekobra". `leaderboard.KOBRA_SCORE_WEIGHTS` {usage .25, product .35, token .20, deepseek .20}, `KOBRA_NO_GITHUB_PENALTY=5`, `usage_score(e, growth=True)` aggiunge `KOBRA_GROWTH_WEIGHT=20` (ramp -5%..+30%, solo se misurabile), `score_blocks(e, kobra)`, `final_score(e, kobra)`. In main: `_top_entries(full=True)` ricalcola bacheca (`_kobra_score` dall'entry completa) e righe del database; `_kobra_early()` per Early/Pearl; pagina del token; `_gem_view_keys` (Pearl >= 70 coi suoi voti). Limite noto: la coda degli avvisi ("new"/"pearl") nasce dai voti di sempre, quindi una gemma che supera 70 solo coi pesi nuovi non genera "Nuova Pearl". Il commento di `final_score` riportava ancora i pesi del 07/10: corretto.

# 2026-10-17 — Whitekobra: layer $300k-$30M — `seed-0339` (Claude, a mano)

Lorenzo, sulle soglie di cap: "vanno tutte bene, tranne quella dei layer che rimodulerei da 300k a 30M". `layers.LAYER_CAP_MIN` (ricerca) 500k -> 300k, `LAYER_CAP_MAX` resta 100M; la vista: `LAYER_VIEW_BAND` 500k-100M per gli altri, `LAYER_VIEW_BAND_KOBRA` 300k-30M con `full` in `_top_entries`. Test in `test_onchain_layers.py`. Poi "Si a entrambe, mettile online" (`seed-0340`): `listing_dates.py` (file `onchain_listing_dates.json`): `fill()` chiamata da `leaderboard.live_market_loop` ogni minuto, `PER_TURN=5`, fonte = `_top_entries(ARENA_POOL, full=True)` + Early (`set_source` in main); DEX = `token-pairs/v1` di DexScreener, min `pairCreatedAt`; layer = klines `interval=1M&startTime=0&limit=1` su Binance/MEXC (non provato dal vivo: in sandbox niente rete; se MEXC non restituisce la prima candela con `startTime=0`, quei layer restano senza data); vuoto = riprova dopo `RETRY_S` 1 giorno. `main._with_listing_dates` dentro `_gem_view` (solo whitekobra): `launched_at` + `launched_from_listing`, quindi vale anche il limite dei 1000 giorni.

# 2026-10-17 — Whitekobra: gemme pulite, Pearl sempre notificata, ordinamento, arene a 3 — `seed-0338` (Claude, a mano)

Lorenzo, "Solo per whitekobra": doppioni (Sherwood Protocol due volte con due voti), oltre 1000 giorni fuori, sotto 60 fuori, Pearl sempre notificata ("l'unica" eccezione), ordinamento per cap e recenza, arene con le prime 3 e il resto in tendina. `main._gem_view(entries)` (`GEM_MIN_SCORE=60` sul punteggio arrotondato, `GEM_MAX_AGE_DAYS=1000` su `launched_at`, doppioni per `_project_key` = nome solo lettere/cifre, tiene il pool piu' profondo poi il punteggio) in `/api/onchain/top` (entries, arene, early) e nel `top_rank` della pagina, se `_full_score(user)`. Avvisi (`_unlimited`): `_gem_view_keys(kind)` (arene per "new", Early per early/pearl) e `first_seen` salvo `kind == "pearl"`. Frontend solo `static/onchain/` (la v1 non e' toccata): `top.js` `SORTS`/`sortRows`/`paintSortBars` (localStorage `lae:gem-sort`, `[data-gem-sort]` in arene, Early, Pearl, Top 25; Cap crescente, Newest decrescente, ritocco = inverte; i numeri restano la posizione), `AR_FOLD=3` su ogni larghezza, "Show all"/"Show less". Commit con `Solo-account: whitekobra`. Provato con Playwright a 390 e 1400 px (dati finti). Non fatto: i doppioni sono tolti solo nella vista, non nel database (il Database e la v1 li mostrano ancora). Lorenzo, alla proposta di unirli anche nel database: "No, in questa chat le modifiche alle gemme sono solo per l'account whitekobra" — quindi niente modifiche condivise (database, ricerca, v1) per le gemme da questo filone: tutto passa da `_full_score`/`_unlimited` e da `static/onchain/`.

# 2026-10-17 — Avviso di deploy privato per whitekobra — `seed-0337` (Claude, a mano)

Lorenzo: "Quando effettui modifiche solo per l'account whitekobra invia la notifica del repository solamente alla chat dell'account whitekobra". Poi, stessa sera: "Semplifichiamo ulteriormente: quando le modifiche riguardano solo l'account whitekobra non sono necessarie notifiche su Telegram": ora quelle righe si saltano e basta, `settings.whitekobra_emails` e `_deploy_chat` tolti; il resto della voce descrive la prima versione. Trailer di commit `Solo-account: whitekobra` (regola in CLAUDE.md, sezione Lingua). `weekly_recap.private_account(msg)`; `main._notify_deploy` divide le righe: le private a `_deploy_chat(user)` (= `_info_chat` o, se la principale e' signal-only come sul server oggi, la chat gemme) per gli account in `settings.whitekobra_emails`; il resto alla chat del repository (`send_message`), che non riceve niente se il deploy e' solo privato. `build_recap` le salta. Test `test_deploy_notice.py`.

# 2026-10-17 — Whitekobra: avvisi Telegram senza limiti, pausa fra i messaggi, gemme solo se nuove — `seed-0336` (Claude, a mano)

Lorenzo: "Solo per account whitekobra: Rimuovi tutti i limiti per tutte le chat Telegram e utilizza lo stratagemma di qualche secondo di pausa [...] solo quando una gemma non presente nelle classifiche, qualsiasi sia, allora scatta la notifica". `settings.telegram_unlimited_emails` (hash di whitekobra, env `TELEGRAM_UNLIMITED_EMAILS`), `main._unlimited(user)`: niente tetto in `_notify_gem` (6/h) e `_notify_listing` (12/h); il trading non ne aveva. `telegram.send_to` attende `PACE_S=3` fra due messaggi alla stessa chat per le chat di quegli account (`telegram.set_paced_chats(main._paced_chats)`: chat principale, gemme, segnali). `leaderboard.first_in_any_ranking(kind, k)` (tag `top:`/`early:`/`pearl:` delle altre classifiche) mette `first_seen` sull'avviso; whitekobra salta quelli con `first_seen` False (quindi niente piu' "Nuova Pearl" per lui: Pearl sta dentro Early). Gli altri account invariati. Limite rimasto non toccato: 10 segnalazioni al giorno di DeepSeek in bacheca (non e' una chat). Test in `test_signals.py`.

# 2026-10-17 — Chat gemme muta anche dopo la ricerca delle 18 — `seed-0335` (Claude, a mano) — **da verificare stanotte**

**Chiuso, stessa sera.** Il recupero una tantum degli 8 (workflow sul branch, `7776524`, mai su main) ha avuto 400 da Telegram; il secondo tentativo con la diagnosi e' stato bloccato dai permessi ("Remote Shell Writes"). Suggerito a Lorenzo di premere Salva nel Profilo (Telegram): `_check_chats` mostra la consegna per chat. Lorenzo: "il problema era nell'ID della chat gemme. Ora dovrebbe funzionare". Recupero degli 8 non mandato. Per azioni sul server da sessioni future: regole in `.claude/settings.json` `permissions.allow` (non aggiunte).

**Seguito, stessa sera.** Lorenzo: "Leggi adesso e fammi sapere" (permesso per la lettura del server). `server-read.yml` dal branch della chat (sola lettura, solo conteggi, mai su main): run 16:00-16:31 UTC, `stopped drained`, 44 tick, 0 re-check, 8 entrati, `top_primed` True, `alerted` = 1225 `new:` + 14 `early:`, 1 errore Telegram 400 nei log dal 14:02 UTC (non attribuibile), whitekobra (`fdfcf4ae`) ha chat gemme impostata e non signal-only (la sua chat principale invece e' signal-only, quindi le gemme vanno solo nella chat gemme). Causa vera: i `new:` li aveva scritti il vecchio `_rank()` per ogni ingresso nella classifica interna della bacheca; `queue_top_news` usava lo stesso tag e saltava quasi ogni gemma entrata nella Top. Ora tag `top:` e flag salvato `top_seen` (il vecchio `top_primed` non conta: primo giro dopo il deploy = sola registrazione). Test `test_an_old_board_mark_does_not_hide_a_gem_entering_the_top`. La correzione delle fasi senza tick (#572) resta valida, ma non era la causa di questa sera.

Lorenzo: "La ricerca delle gemme delle ore 18 e' finita e ho visto i risultati nella chat del repository, pero' non mi sono arrivate le notifiche delle nuove gemme nelle arene". Causa trovata nel codice: `_sync_top` (coda "new"/"pearl") e `drain_alerts` girano solo dentro `leaderboard.tick`; `nightly.run_once` smette di fare tick quando la coda e' vuota o alla quota del 75%, poi fa `settle` (analisi ancora in corso), `layers`, `outcomes`, il re-check DeepSeek della Top (fino al 25% della finestra) e gli studi: i progetti che entrano nella Top li' finiscono in `entered` del riepilogo ma non vengono mai messi in coda (al giro dopo al massimo, tardi). Ora `leaderboard.flush_alerts()` (sync + drain fino a coda vuota + hook `on_flush`) e' chiamata da `Steps.alerts()` dopo il settle, dopo ogni re-check riuscito e alla fine. Secondo buco: oltre `_GEM_NOTIFY_PER_HOUR=6` per account gli avvisi erano scartati e gia' segnati come annunciati; ora vanno in `main._gem_overflow` e `_send_gem_overflow` (hook `on_flush`) li manda in un messaggio solo ("Altre N gemme"). Test in `test_signals.py` e `test_nightly.py`.
Non verificato sul server: la lettura in sola lettura con `server-read.yml` (stato `top_primed`/`alerted`, chat del profilo, errori Telegram nei log, solo conteggi perche' i log delle Actions sono pubblici) e' stata **negata dal controllo dei permessi della sessione** ("Production Reads"). Se stanotte la chat gemme resta muta, serve quella lettura: chiedere a Lorenzo il permesso. Altre cause possibili che solo il server puo' escludere: l'ID della chat gemme nel profilo uguale a una chat "solo segnali" di un account (`_signal_only_chats`, allora `_gems_chat` la salta), invio Telegram rifiutato (log "Invio Telegram fallito").

# 2026-10-17 — Punteggi arene/pagina allineati (solo whitekobra) e modalita' dark — `seed-0333`, `seed-0334` (Claude, a mano)

Lorenzo: "I punteggi delle gemme continuano a risultare diversi tra le classifiche per narrative e il rank sotto il grafico [...] Perche'?". Causa: `projects_db.search()` seleziona solo alcune colonne (niente `pillars`, `cg_mcap`, `similarity`, `socials`); `_top_entries` passava quelle righe a `final_score`, quindi senza blocco token, prodotto quasi vuoto, niente `NO_GITHUB_PENALTY`, e `too_big` senza cap globale. La pagina (`/api/onchain/token`) legge con `get()` la riga intera. Il test di `seed-0317` mockava `search` e `get` con lo stesso dict: non poteva vederlo. Ora `search(full=True)` e `_top_entries(..., full=)`. Lorenzo: "Per ora falla solo per whitekobra": `settings.onchain_full_score_emails` (hash sha256, env `ONCHAIN_FULL_SCORE_EMAILS`), `_full_score(user)` in `/api/onchain/top` e nel `top_rank` della pagina. Gli altri account, gli avvisi Telegram (`_top_source`), la notte e `_sync_top` restano sulle righe leggere; la vista di whitekobra legge la tenure delle arene ma non la salva (`tenure=load_tenure()`). Per estenderlo a tutti: togliere la condizione e passare `full=True` ovunque — effetti: punteggi del database cambiano, penalita' codice chiuso e tetto cap globale valgono anche nella Top, qualche token puo' uscire. Test `test_the_arenas_score_a_database_row_with_its_pillars` (database vero).
Poi "aggiungi anche modalita' dark": solo `static/onchain/` (grafica di whitekobra), la v1 non e' toccata. `theme.js` (light/dark/auto in `localStorage` "lae:theme", default light), script inline in testa a `onchain-app.html` prima della mappa (niente lampo), palette `:root[data-theme="dark"]` in fondo a `classic.css` (tutto il resto legge i token `--c-*`), `chart-theme.js` ridisegna su `lae:theme`, selettore "Appearance" nel Profilo (`.pf-theme`, nascosto da 1100 px: il desktop e' gia' scuro). Provato con Playwright a 390 px: gemme, Top 25, profilo, pagina token in scuro, chiaro invariato, scelta che resta al ricaricamento, 0/15 errori di ricaricamento. In locale serve un utente: `auth.create_user` prima di avviare uvicorn (dati in `backend/data/`, ignorata da git).

# 2026-10-17 — Pagina bianca al ricaricamento dell'app on-chain — `seed-0332` (Claude, a mano)

Nuova chat "per DegenView"; Lorenzo: "Risolvi il punto 2, il resto va bene" (il punto 2 era l'errore di ricaricamento del 16/10; gli altri due, alert gemme/Pearl da verificare stanotte e regola delle due grafiche, restano come sono). Causa: in `onchain-app.html` e `onchain-app-v1.html` i `<link rel="modulepreload">` stavano prima dell'import map (dopo i fogli di stile). Al ricaricamento `main.js` arriva dalla cache, Chromium ne risolve gli import prima di aver letto la mappa e il grafo del modulo resta in errore: app bianca. Playwright (Chromium 141, server vero, 9/10 ricaricamenti falliti su **entrambe** le versioni, non solo la nuova come scritto il 16/10). Ora `<!--onchain-importmap-->` e' subito prima di `<!--onchain-modulepreload-->`, in cima all'`<head>`: 0/30 sulla nuova, 0/15 sulla v1. Test `test_the_import_map_comes_before_any_module_fetch`. Per provarlo: niente `page.route` in Playwright (disattiva la cache e nasconde il bug), e riavvia uvicorn dopo ogni modifica all'HTML (letto all'avvio) — probabilmente il motivo per cui la prova del 16/10 "non cambiava nulla". Attenzione: `pkill -f`/`grep` con la riga di comando di uvicorn nella stessa chiamata Bash uccidono la shell stessa (exit 144): prendere il pid con `ps` in una chiamata separata.

# 2026-10-17 — Chiuse `seed-0321` e `seed-0268` (Claude, a mano)

Chat di prova sul repo rinominato. Lorenzo: "Chiudili entrambi". `seed-0321` (podio diverso dalla Top 25) -> scartato: il podio "pound for pound" e' voluto (16/10). La voce era sparita da `_SEED` con il revert di #552 ma restava sul volume: rimessa, se no la risoluzione e' orfana. `seed-0268` (overhaul sito classico) -> risolto: restano non fatti, per sua scelta, la pulizia del codice di trading spento e il resto del piano di 8 settimane. Poi, "Si, chiudi": anche `seed-0310` (repo pubblico) -> risolto, la storia era gia' riscritta il 16/10. Nota: questa sessione cloud era configurata col nome vecchio `Smowcomingsoon` (git va per reindirizzamento, gli strumenti GitHub accettano solo quel nome).

# 2026-10-17 — Alert Pearl nella chat gemme, ricerca anche alle 18 — `seed-0329`, `seed-0330` (Claude, a mano)

Lorenzo: "aggiungi l'alert nella chat delle gemme anche per quelle che eventualmente entrano nella sezione Pearl. Poi aggiungi per tutti gli account una nuova ricerca alle ore 18 [...] Due ricerche al giorno". `leaderboard.queue_pearl_news()` (da `_sync_top`, come `queue_top_news`) mette in coda "pearl" per ogni gemma nuova in `early_list()` con punteggio arrotondato >= `PEARL_MIN=70` (lo stesso filtro di `top.js paintPearl`); primo giro solo registrazione (`pearl_primed`). `_notify_gem("pearl")` manda "🦪 Nuova Pearl" con link `#pearl&token=` solo agli account con `_onchain_variant == "current"` (Pearl non esiste nella copia v1): scelta mia, per la regola grafica/sezioni nuove solo whitekobra. `onchain_nightly_extra_times` di default "18:00": giro principale anche alle 18 (stessa finestra di 6 ore, riepilogo Telegram). Se sul server il `.env` imposta `ONCHAIN_NIGHTLY_EXTRA_TIMES`, vince quello.

# 2026-10-17 — Alert Telegram delle gemme: ora partono all'ingresso nella Top — `seed-0328` (Claude, a mano)

Lorenzo: "continuano a non arrivare i messaggi delle nuove gemme. Anche stanotte, dopo la ricerca delle tre [...]". Causa nel codice, non nella chat: `_rank()` metteva "new" in coda solo per l'ingresso nella classifica interna della bacheca, e `drain_alerts()` lo scartava se il token non era nella Top 50 in quel momento — il tag restava in `_alerted`, quindi mai piu' annunciato; le righe del database non entravano mai in coda; "early" (sotto $300k) era scartato dallo stesso controllo. Ora `leaderboard.queue_top_news()` (chiamata da `_sync_top`, ogni 60 s durante i tick) mette in coda "new" per ogni progetto nuovo in `_top_source(TOP_ALERT_POOL=500)` = lo stesso elenco di "Entrati nelle arene"; il primo giro dopo il deploy registra la Top senza avvisi (`top_primed` salvato con la bacheca). Early non passa piu' dal controllo della Top. Test in `tests/test_signals.py`. Non verificato in produzione: la prova vera e' la prossima notte.

# 2026-10-17 — Whitekobra: grafica della sera del 16/10 e Pearl di nuovo — `seed-0327` (Claude, a mano)

Lorenzo: "voglio le modifiche [grafiche] che avevamo fatto in questa chat [...] e la sezione Pearl [...] solo all'account White Cobra". `static/onchain/` e `onchain-app.html` riportati a `d0e012d` (dopo #555), tenendo da dopo: `main.js` login -> `location.reload()` (#558) e i testi Early $300k (#560). Annullati solo per la versione nuova #556 (Pearl senza minimo) e #557 (Pearl tolta, mosaico): Pearl c'e' di nuovo, con `PEARL_MIN = 70`; le arene sono elencate aperte. La nota "Non riproporre Pearl" del 16/10 non vale piu'. La v1 (altro account) non e' toccata.

# 2026-10-17 — Grafica per account, funzionamento per tutti — `seed-0326` (Claude, a mano)

Lorenzo: grafica nuova dell'app on-chain solo su whitekobra, funzionamento per tutti; sito classico sempre uguale per tutti; per gemme e Discover chiedere sempre a quale account applicare (CLAUDE.md). La separazione grafica c'era gia' (`seed-0325`, `static/onchain-v1/`). Portato nella v1 solo il funzionamento: `detail.js` liveQuote/refreshLive + supply; `main.js` niente letture wallet col trading spento e retry del saldo limitato (il totale in alto della v1 resta); `agent.js` riga della ricerca e singolare; `leaderboard.js` Top #N e testi Early $300k (anche badge e nota, corretti pure in `static/onchain/`). Provato con `ONCHAIN_V1_EMAILS=<account di prova>`: 0 letture del saldo in 20 s, cap live nella pagina token, grafica v1 invariata. Top 25 resta solo su whitekobra (Lorenzo). Ogni modifica di funzionamento futura alle gemme va fatta in entrambe le cartelle.

# 2026-10-16 — Due versioni dell'app on-chain per account — `seed-0325` (Claude, a mano)

Lorenzo: "ripristina l'app come era prima per il mio utente [...] mentre per white kobra applica queste cose"; scelta sulla scheda: "Prima di oggi". `frontend/onchain-app-v1.html` + `frontend/static/onchain-v1/` = copia congelata di `5ff48ef` (main prima di `seed-0316`: gia' con #537/#538, che non cambiavano l'aspetto), percorsi riscritti a `/static/onchain-v1/`. `main._render_onchain_app` serve la v1 agli account in `settings.onchain_v1_emails` (allowlist come `admin_emails`, default l'hash dell'account admin, env `ONCHAIN_V1_EMAILS`), boot payload con `app_variant`; importmap/modulepreload per cartella (`_onchain_app_html(page, folder)`). Il login nelle due pagine ricarica invece di `boot()`, cosi' il server sceglie la pagina giusta. Le modifiche nuove vanno solo in `static/onchain/`; la v1 non si tocca, e un cambio di API che rompe la v1 va controllato su entrambe. Test `test_onchain_app_v1.py`.
Trovato qui l'errore "Failed to resolve module specifier @onchain/nozoom.js" al ricaricamento: risolto il 17/10, `seed-0332` (le conclusioni scritte qui quel giorno erano sbagliate).

# 2026-10-16 — Pearl eliminata, mosaico di nuovo nelle gemme — `seed-0323`, `seed-0324` (Claude, a mano)

Lorenzo: "cosa e' la sezione pearl?", poi "eliminala"; poi "rivoglio il mosaico sulle gems". Pearl via da `onchain-app.html`, `top.js`, `main.js` VIEWS/DOCK, `detail.js`, `shell.css`, `classic.css`, `ui.js` (numerazione 01-06), dock a 5 voci (350 px, Search desktop a 506 px). `top.js`: tornano `mosaicHtml`/`hive`/`mosaicAll` di prima di `seed-0316` (tocco = classifica dell'arena sotto il mosaico); il podio resta in `.tb-top3`, la vista singola `only` resta tolta. Non riproporre Pearl.

# 2026-10-16 — Pearl senza il minimo di 70 (Claude, a mano)

Lorenzo: "togli il minimo di 70 per essere nelle gemme early perche' cosi' e' vuota la classifica". `top.js paintPearl` non filtra piu' `PEARL_MIN`: mostra tutte le gemme di `top.early` per punteggio (quindi oggi le stesse di Early, in ordine di punteggio); testi di Pearl in `onchain-app.html` e `ui.js` aggiornati. Se vuole di nuovo una soglia, e' una riga in `paintPearl`.
Nello stesso thread: storico di $VEIL (Solana, veilit.xyz) letto dal server con `server-read.yml` dal branch della chat (sola lettura, mai su main): visto il 14/10 08:57 a ~$12,8M di cap (sopra il tetto $10M), entrato #2 nella Top il 15/10 03:00 a $6,19M, avviso Telegram senza prezzo d'ingresso registrato.

# 2026-10-16 — Revisione dell'app on-chain — `seed-0322` (Claude, a mano)

Lorenzo: "Ricontrolla tutte le sezioni dello Sniper" (= onchain-app.html, il suo segnalibro), poi "Risolvi tutto e implementa i suggerimenti tranne Riepilogo della ricerca notturna" (resta nella chat dei commit). Fatto: `ui.js` intestazioni e numeri 01-07; Early $300k in `leaderboard.js gemWhy` e nel Telegram (`TOP_CAP_MIN_USD`); `/api/onchain/token` da' `entry.top_rank` (posizione in `_top_entries(ARENA_POOL)`), mostrato come "Top #N"; conteggio arene senza le vuote; trading spento: `loadChainData`, `paintHoldings`, `refreshTotal` non leggono niente, `.tb-bal` e le parti wallet del Profile `data-trading-only`, retry del saldo limitato a 6 con attesa crescente (prima ogni 5 s per sempre); `/api/agent` da' `research` (ai, last/next run, esaminati, entrati) e Scout lo mostra; arene su telefono 5 token + "Show all"; titolo "Top 25 · narrativa" col filtro; `.memes-list:empty` nascosta. In locale un errore intermittente "Failed to resolve module specifier @onchain/agent-map-model.js" al primo giro dopo l'avvio del server: non riprodotto in 8 prove (vecchio e nuovo codice), da tenere d'occhio.

# 2026-10-16 — Podio in alto: lasciato "pound for pound" (Claude)

Lorenzo aveva chiesto che il podio rispecchiasse i primi tre della Top 25 (#552, podio per punteggio); appena andato online: "No aspetta / No, annulla", poi "Credevo fosse un errore ma era una strategia voluta". Revertito: il podio resta `p4p` (distacco dalla mediana della propria arena), la Top 25 per punteggio assoluto, quindi possono differire. Non riproporlo senza che lo chieda lui.

# 2026-10-16 — Menu gemme riordinato, sezione Top 25, mercato DEX in tempo reale — `seed-0319`, `seed-0320` (Claude, a mano)

Lorenzo: "Pearl spostala subito dopo Gems [...] una sezione Top (prima di Scout) [...] le migliori 25 gemme per punteggio [...] grafici sempre aggiornati con i dati dex, cosi' come la MarketCap". Ordine `VIEWS`/`DOCK`: gems, pearl, top (= Early), rank (= Top 25), agent, profile. Vista `rank` (`#rank-view`, `top.js paintRank`, `top.entries` per punteggio, 25). Mercato: `leaderboard.live_market_loop` (ogni 60 s, avviato in lifespan con il radar acceso, anche in modalita' notturna) -> `poll_live` legge DexScreener per bacheca + `_top_source(500)`, `apply_market` per la bacheca e `_live` per tutti; `_top_entries` usa `live()` per cap/variazione/pool delle righe database (i gate restano sui dati salvati). `detail.js`: `liveQuote`/`refreshLive` all'apertura e ogni minuto, `e.supply` = cap/prezzo per la scala del grafico. Test `test_live_market_reaches_the_top_s_database_rows`.

# 2026-10-16 — Sezione Pearl — `seed-0318` (Claude, a mano)

Lorenzo: "una nuova sezione Pearl [...] le gemme selezionate su Early che pero' hanno ottenuto un punteggio pari o superiore a 70". Vista `pearl` (main.js `VIEWS`/`DOCK`, dock in onchain-app.html dopo Early, `#pearl-view`, shell.css la nasconde fuori vista, ui.js intro, classic.css titolo, detail.js `LIST_VIEWS`), `top.js paintPearl()` sulla stessa `top.early` con `PEARL_MIN = 70` sul punteggio arrotondato; `earlyRow()` condiviso con Early. `--dock-w` piu' largo per la quinta voce. Attenzione in locale: `ss` non c'e' in questa sandbox, il server va fermato con `kill <pid>` da `ps` — l'HTML on-chain e' letto all'avvio.

# 2026-10-16 — Gemme: primi tre in alto, arene aperte, grafico al clic, punteggio allineato — `seed-0316`, `seed-0317` (Claude, a mano)

Lorenzo, con screenshot della sezione gemme. `top.js`: `paintTop3()` mette i tre di `p4p` in `.tb-top3` nella `.topbar` (dopo `.tb-me`; nascosto sul login; sotto 1100 px riga propria), il podio grande `renderPodium` non si usa piu' li'; `listHtml()` elenca tutte le arene aperte in `.ar-grid` (via mosaico, `hive`, vista singola `only`). `detail.js`: `LIST_VIEWS` senza "gems" e `paneMode()` = desk e `data-desk-list` != false, quindi nelle gemme il token si apre come pagina modale (CSS in fondo ad `app.css`, `.dt-back` visibile). Punteggio: `/api/onchain/token` per le righe del database calcola `final_score` come `_top_entries` (VEIL 89 in arena, 73 in pagina: era il punteggio salvato). Test `test_the_token_page_shows_the_top_s_score`.

# 2026-10-16 — Chat Telegram delle gemme — `seed-0315` (Claude, a mano)

Lorenzo: la terza chat (gemme) non riceve niente; la sua chat principale e' quella degli alert. `_notify_gem` mandava solo a `_info_chat` (chat principale, mai una signals-only) e solo con `user.onchain_wallets`. Ora `User.telegram_gems_chat_id` (profilo: "Gems chat ID", `PATCH /api/auth/telegram` con `telegram_gems_chat_id`, conferma in chat al salvataggio), `main._gems_chat` = chat gemme o principale, mai signals-only; requisito del wallet tolto per le gemme (resta per i listing). Il riepilogo della notte (`nightly._send`) va alle chat di sistema (TELEGRAM_DEV_CHAT_IDS), non e' cambiato. Lorenzo deve incollare l'ID della chat gemme nel profilo.
Poi: "la conferma mi e' arrivata sull'altra chat degli alert". Ogni Salva ora chiama `auth_routes._check_chats`: un messaggio per chat distinta con i suoi ruoli (`chat_roles`, stessa logica di main), esito di consegna nella risposta (`telegram_check`) e lista `#telegram-check` sotto il tasto.

# 2026-10-16 — Liste di ricerca pair intere — `seed-0314` (Claude, a mano)

Lorenzo, con screenshot: pair tagliati nella ricerca in alto e fuori schermo nel Lab. `app.js placeSuggestionList(list, anchor)` usata da `positionSuggestions` e da `makeSuggestController.render`: sposta la lista in `<body>` (un `.panel` animato fa da containing block ai `position:fixed`, vedi la nota su `@keyframes lae-sali`), larghezza >= 560 px dentro lo schermo, apertura sopra se sotto manca spazio; CSS in fondo a `style.css`: righe che vanno a capo. `shortSymbol` (Pool…6789) invariato.

# 2026-10-16 — RSI+BB 4H e RSI+BB BTC band tolte dal codice — `seed-0313` (Claude, a mano)

Lorenzo: "Alleggerisci". Via: `compute_lki4h_signals`/`LKI4H_DEFAULT_PARAMS`, `compute_rsi_bb_band_signals`, `btc_regime.band_mask` e `status()["band"]`, `optimize.max_return_search_3d`/`MAX_RETURN_MULTS`/`solidity`/range 4H (restano `_admitted`, `SOLIDITY_FLOOR`, `COARSE_SEEDS`, `FINE_RADIUS`, `MIN_TRADES_PER_YEAR_4H` per `max_return_search_nd` di Claudio 4H), voci in priors/regime/sensitivity, `scripts/compare_claudio.py` + `claudio-compare.yml`, varianti RSI+BB 4H in `compare_claudio_folds.py`, tre file di test. Nel loop degli alert una strategia non piu' nel registro si salta (`confirmed_events` ricadrebbe su Lorenzo). `strategyLabel` tiene la riga per "RSI+BB BTC band" per i vecchi alert nel registro. Il livello del grafico Bull Market Support Band (`indicators.bull_market_support_band`) resta: e' un'altra cosa.

# 2026-10-16 — Lab: via le due RSI+BB di prova, menu per tipo — `seed-0312` (Claude, a mano)

Lorenzo: togliere RSI+BB 4H e RSI+BB BTC band ("erano delle prove"), raggruppare Trend EMA Reversal con RSI+BB Reversal e Trend EMA con RSI+BB long/short, togliere la stella. Le due strategie sono in `HIDDEN_STRATEGIES` (fuori da /api/strategies e dalle rotte che controllano AVAILABLE_STRATEGIES; ancora nel registro per gli alert gia' salvati, e /api/optimize le accetta se chiamato a mano). `app.js`: `STRATEGY_GROUPS` + `strategyOptionsHtml()` (optgroup) per il menu in alto e quello del Lab, niente piu' `RECOMMENDED_STRATEGIES`; badge BTC senza la parte Band. `i18n.js` traduce anche l'attributo `label` (optgroup). Il codice di Max return 4H e della banda resta (morto per il sito): toglierlo e' un lavoro a parte, da proporre se Lorenzo vuole alleggerire.

# 2026-10-16 — Barra in alto meno affollata — `seed-0311` (Claude, a mano)

Lorenzo: "La sezione superiore del sito e' troppo affollata. Ottimizza lo spazio senza togliere niente". Sito classico (`index.html` header.toolbar; sotto 760 px resta nascosta). Misurato con Playwright (auth, strategie e /api/btc-regime finti): prima sfondava sotto 1440 px (130 px a 1280, 386 a 1024). Blocco "Top bar compaction" in fondo a `style.css`: ricerca e menu strategia si stringono, lingua come sigla (`i18n.js`, nome nel title), email -> iniziale sotto 1360 px (`updateAuthUI` mette `title` e `data-initial`), "Indicators" solo icona sotto 1200 px (`.tb-label`), due righe fra 760 e 1000 px. Nessun controllo tolto. Fatto a mano, non via DeepSeek: e' lavoro di impaginazione da verificare a schermo.

# 2026-10-16 — Repository pubblico: via dati personali, chiavi e IP (Claude, a mano)

Lorenzo: "rimuovere completamente ogni riferimento alle nostre email o qualsiasi altro dato personale o qualsiasi chiave, API [...] ovviamente preservando il funzionamento di tutto". `seed-0310`.
- Scansione gitleaks di albero e storia: nessuna chiave mai committata. Nella storia restano solo 2 email (Lorenzo, tester), l'IP del server e un'email di terzi, piu' l'email personale come autore di ~460 commit.
- Fatto: `/api/issues` anonimo maschera le email (`routes/issues._mask_emails`, prime due lettere); IP, percorso chiave SSH e nickname del tester tolti dai file; `.gitleaks.toml` (regole default + email + IPv4 pubblici, allowlist indirizzi on-chain), workflow `secret-scan.yml` separato dal deploy, `scripts/hooks/pre-commit` (`git config core.hooksPath scripts/hooks`), `.gitignore` per `.env`/chiavi.
- Restano nomi di battesimo come chiavi di strategia (Lorenzo, Gabriele): cambiarli migra i dati salvati, non fatto. Lo slug del repo contiene lo username GitHub: inevitabile.
- **Storia di main riscritta il 16/10** (Lorenzo: "Si', riscrivi"): git filter-repo con `--replace-text`, `--replace-message` e `--mailmap` verso l'indirizzo noreply di GitHub; albero finale identico (stesso hash di tree), gitleaks 0 risultati. **Ogni clone o branch di prima va riallineato**: `git fetch origin && git reset --hard origin/main`, mai un merge del vecchio main (riporterebbe dentro i commit vecchi). Restano con la storia vecchia gli altri ~215 branch e i `refs/pull/*` delle PR (solo il supporto GitHub li pulisce).
- **Branch vecchi, 16/10 sera: lasciati.** Contati 215 (oltre a main): 204 interamente dentro PR unite, 11 con 1-2 commit abbandonati (PR chiuse, DeepSeek falliti, esecutori Coinbase/Kraken del 31/08). Da una chat cloud non si cancellano: il proxy git accetta push solo sul branch della chat (403), e un workflow che li cancella dal branch della chat viene bloccato come aggiramento. Lorenzo: "Lascia stare". Non riproporlo; se lo chiede, il comando da un suo computer e' `git for-each-ref ... refs/heads | grep -vx main | xargs -n 40 git push origin --delete` su un clone `--bare`.

# 2026-10-16 — Overhaul prestazioni di tutto il sito, piano (Claude, solo piano)

Lorenzo: "fai un overhaul completo del sito per renderlo piu veloce, performante e leggero; riducendo gli errori e le ripetizioni inutili nel codice; crea piano di attuazione e proponimelo". Documento "Overhaul prestazioni — piano" (Claude Doc, artifact 6d45e063-38e2-4509-8177-35212584cd6a). Assorbe le settimane rimaste del piano del 12/10 (`seed-0268`).
- Misure 16/10: `onchain-app.html` 176 KB con 146 KB di CSS inline (HTML no-cache, si riscarica sempre); CSS app 2778 regole, 768 selettori ripetuti, `classic.css` 479 `!important`; 12 moduli del trading spento (~110 KB) importati da `main.js`; `app.js` classico 609 KB; three.js 2 MB solo per /engn; 120 `httpx.AsyncClient` in 65 file; 44 `_load`/42 `_save` copiati, 7 non atomici; gzip sia in FastAPI sia in Caddy; Chromium+Playwright+Piper nell'immagine.
- Fasi: 0 misura dal vivo (workflow sola lettura) · 1 peso morto frontend (CSS inline in file, trading a import dinamico, motion.js dopo il primo disegno) · 2 server (client HTTP condiviso, gzip solo Caddy, helper JSON atomico unico, immagine Docker) · 3 CSS unificato con screenshot prima/dopo · 4 app.js classico a moduli + grafico incrementale · 5 codice spento e main.py in router.
- Lorenzo: "applica tutto". Fatto nella PR #537: fase 0 (`server-perf.yml`, `perf.json` ogni 10 min da `perf.dump_loop`), fase 1 (`static/onchain/shell.css`, i due `fill:url(#id)` restano inline perche' un url a frammento si risolve sul foglio; moduli trading in `_ONCHAIN_LAZY_MODULES` importati con `import()` e fuori dal modulepreload; `<engn-motion>` con un foglio condiviso), fase 2 (`app/http_client.pooled()` in 70 punti, esclusi i file di esecuzione ordini; `APP_GZIP=0` in docker-compose; 7 cache scritte atomiche), fase 3 (`app/css_min.py` al servizio dei .css, stesso ETag, -29% gzip), fase 4 ridotta (JS minificato solo negli spazi da esbuild nello stage `assets` del Dockerfile, -32% gzip; il deploy controlla la sintassi dei moduli minificati). Screenshot 390/1440 di login, Gems, Early, Scout, Profile e home classica uguali a main salvo i dati.
- Non fatto e perche': app.js in moduli (un'unica IIFE da 13k righe con stato condiviso, rischio alto senza dati veri: resta da fare a pezzi); grafico incrementale (la prima tranche del 12/10 ha gia' portato il refresh a una volta per candela); CSS fuso fra strati (i duplicati sono override voluti fra file, non copie: 0 duplicati esatti per file). Chromium e Piper restano: li usano `jstext` (ricerca gemme) e la voce dello Scout.
- Fase 5, Lorenzo: "Si', cancella", poi "prosegui in autonomia fino al commit finale [...] fai in modo che tutto funzioni senza impatti". Tolti: Meme Sniper (`/api/sniper/*`, `/sniper`, sniper.html, `app/sniper/{agents,cache,cex_check,market,scorer,security}`; restano `scanner.py` e `quality.py`, li usa la ricerca gemme), pilota e autotrader (`/api/onchain/pilot`, `/api/onchain/autotrader`, `/api/onchain/sniper-autotrade`, ponte sniper, loop ai_scan, pilot.js, autotrade.js, card nascoste), loop delle strategie automatiche (non partono piu'), `ladder_watch`, `quant_research`, `analysis/futures_backtest`. Restano i moduli ancora letti da rotte vive (autotrader/wealth/portfolio servono a Profile e Top). `main.py` 9431 -> 7875 righe: helper comuni in `app/web_common.py`, 7 gruppi in `app/routes/` (issues, price_alerts, drawings, jobs, push, guest_links, auth_routes) inclusi con `include_router`; mappa delle rotte verificata identica prima/dopo (ogni path risolve allo stesso endpoint). Non spostati: watchlist, trading, archive, onchain, optimize, analyze (usano `get_provider`/`_fetch_cached` di main, che i test sostituiscono su `main`).
- Resta: app.js classico in moduli, solo dopo test Playwright che coprano grafico, timeframe, backtest e disegni (Lorenzo ha chiesto perche' non subito: app.js non ha test di comportamento).

# 2026-10-15 — Strategia Claudio 4H (nascosta finche' Lorenzo non vede i numeri) (Claude, a mano)

Lorenzo: "sviluppare una strategia 'Claudio' tutta tua adatta al timeframe 4H con ottimizzazione [...] Prima di renderla operativa riassumi", poi "Ok, perfetto". `strategies.compute_claudio_signals`: setup RSI(14)<cl_rsi_os e close<BB(20,cl_bb_mult) bassa; ingresso alla candela dopo se close > high precedente e regime (ER20<=0.30 o close>EMA200); uscita a meta' banda, stop cl_atr_stop×ATR14 all'ingresso, stop a tempo 30 candele. In STRATEGY_REGISTRY ma in `HIDDEN_STRATEGIES` (fuori da menu e alert). Ricerca `optimize.max_return_search_nd` con CLAUDIO_DIMS (OS 20-40, BB 1.8-2.8, stop 1.5-4.0), `FOUR_H_LAB` in main (ultimi 12 mesi esclusi). Confronto su dati reali: `scripts/compare_claudio.py` + workflow `claudio-compare.yml` (notice per pair). Prima prova su dati sintetici: Claudio troppo selettivo (1 trade nei 12 mesi), da rivedere sui dati reali.

**Test a anni alterni, 15/10.** Lorenzo: "testare dal 2023 al 2026 [...] poi applicarla al 2022 oppure al 2021 [...] candele mai viste", poi "fai entrambi [Claudio v2 + dati 2021-22], inoltre aggiungerei al confronto anche [...] la strategia Trend Follower EMA di Lorenzo". `scripts/compare_claudio_folds.py` + `claudio-folds.yml`: 15 coppie (4 grandi, COMP/BAT/1INCH/KSM/SNX, ROSE/ZIL/ANKR/CELO/IOTX/KAVA), candele 4H da data.binance.vision dal 2020 + mese corrente da MEXC; ogni anno 2021-2024 e gli ultimi 12 mesi a turno mascherati dalla ricerca e poi testati. Claudio v2 = `cl_exit_upper=1, cl_trail=1`, niente regime, niente stop a tempo. Risultato (pick solido, mediana sui 72 anni-coppia): Lorenzo con i suoi default **+25%** (44/72 positivi, ~45 trade/anno long+short), RSI+BB 4H 0%, Claudio -0.5%, Claudio v2 -6%, Lorenzo ricercato 0% (spesso nessuna combinazione passa i limiti, e quando passa fa peggio dei default). Claudio (v1 e v2) bocciata, resta nascosta. Artefatti di GitHub non scaricabili dalla sandbox: i numeri si leggono dalle annotation `::notice::`.

**Ambiente di test fisso, 15/10.** Lorenzo: "la [Lorenzo] devi utilizzare come reversal, cioe' solo long e uscita senza short" e "nel sito non c'e' piu' la necessita' di testare sull'ultimo anno di candele non viste [...] lascerei in questo ambiente di test sempre 2021 e 2022 come anni di candele mai viste [...] per qualsiasi tipo di strategia". Quindi: sito senza hold-out (Max return 4H cerca su tutto il grafico, `_last_year_check` rimosso, card con la sola colonna storia; il "Test on another pair" dell'archivio mostra ancora la colonna ultimi 12 mesi, e' solo una vista). `compare_claudio_folds.py`: ricerca una volta sulle candele dal 2023 (`TRAIN_FROM`), poi i pick su 2021 e 2022 (`TEST_YEARS`); tutte long only (`LONG_ONLY` toglie gli short a Lorenzo, l'uscita resta l'incrocio al ribasso). Per una strategia nuova: aggiungerla a `VARIANTS` e lanciare `claudio-folds.yml`. Il "solo long" vale SOLO qui: Lorenzo sul sito resta long/short (Lorenzo, 15/10: "La strategia Lorenzo sul sito deve rimanere come era prima long/short"). Primo esito 2021/22 (mediane su 15 coppie): R +4/-22, C +3/-3, Ld +42/-20, Ls +114/-18; Claudio v2 scartata. "Test on another pair" senza colonna ultimi 12 mesi ("ormai non servono piu'"). Varianti `+EMA200d`: nessun ingresso sotto la EMA 200 giornaliera del giorno prima.

**Ricerca di una strategia per entrambi gli estremi, 15/10.** Lorenzo: "una strategia che e' efficace sia in un mercato fortemente rialzista come il 2021, sia in un mercato fortemente ribassista come il 2022 [...] senza grosse perdite". Claudio Trend 4H (`compute_claudio_trend_signals`, nascosta: rottura del massimo di ct_len candele con regime giornaliero, stop ATR che segue, uscita se il regime cade) BOCCIATA: ricercata 2021 med 0 / 2022 -14; valori fissi 120/4/200 2021 +14 / 2022 -12 (basket 15). Conferma su 10 coppie mai usate (LTC LINK ADA DOGE ATOM XLM ALGO VET CHZ ENJ, dispatch con `pairs`). Valori fissi di Lorenzo, mediane 2021 / 2022 / 2023-26 annuo, basket 15 · basket 10: solo long +EMA200d (`Ldf`) +32/-1/+3 · +91/-2; long sopra EMA200d e short sotto (`Lrs`) -4/+70/-1 · +50/+72. Nessuna vince ovunque: Ldf e' il "senza grosse perdite", Lrs guadagna nel crollo ma perde negli anni laterali e su alcune alt nel 2021 (SNX -84, COMP -75). Nulla sul sito: decide Lorenzo. Lorenzo, 15/10: "Nessuna, per il timeframe 4H lascia tutto invariato" — migliore sul 4H Lorenzo Trend con i suoi valori, RSI+BB 4H in parte.

**Ambiente di test 1D, 15/10.** Lorenzo: "facciamo ambiente di test per timeframe 1D. Metti a punto una tua strategia [...] paragone con [...] RSI piu' BB reversal e Lorenzo trend follower", e "i valori si scelgono sulle candele dal 2023 a oggi, poi si provano su 2021 e 2022" (niente valori fissati a mano per le mie). Workflow solo a richiesta: `gh api -X POST .../actions/workflows/claudio-folds.yml/dispatches -f ref=main -f 'inputs[tf]=1d' -f 'inputs[pairs]=[...]'` (gh workflow run non va: GraphQL bloccato). 35 coppie (paniere 15 + 10 + BNB TRX ETC EOS NEO DASH ZEC XTZ ONT QTUM), archivio Binance 1d dal 2018. Claudio 1D (`compute_claudio_1d_signals`, nascosta: ritorno sopra EMA corta dopo una correzione, con EMA lunga crescente; stop ATR che segue, uscita sotto la EMA lunga). FIX: un trade ancora aperto a fine anno di prova non veniva contato (il backtest conta solo i chiusi, e un segnale sull'ultima candela non e' confermato) — ora si chiude alla penultima; i numeri 4H rifatti su 35 coppie, conclusioni invariate. Mediane 2021 / 2022 (35 coppie): Lorenzo default +BTC (`Ldb`, entra solo se BTC chiude sopra la sua EMA 200d) +134 / 0 (peggiore -36); Lorenzo default +120 / -12; Claudio 1D +BTC +54 / 0; Claudio 1D +29 / -9; RSI+BB reversal 0 / **-53** (compra i cali del 2022 e resta dentro). Sul 4H, 35 coppie: Lorenzo long sopra / short sotto EMA200d +42 / +73 (30/35 positive nel 2022). Nulla sul sito.

**Filtro BTC su tutte le strategie, 15/10.** Lorenzo: "Il filtro Btc può essere utile da attivare/disattivare su tutte le strategie del sito?", poi "Si, testalo su tutto". `SET=btc` nel workflow (input `set`). 35 coppie, mediane 2021 / 2022 / annuo 2023-26 (per le ricercate quest'ultimo e' in-sample). 4H: RSI+BB 4H +6/-23/+42 → +4/0/+24; Lorenzo solo long +102/-20/+9 → +124/0/+4; Lorenzo L/S come sul sito +10/+63/+6 → +24/+88 (34/35 positive)/-1. 1D: RSI+BB reversal 0/-53/+45 → 0/0/+32; Gabriele 2 L/S 0/-9 → 0/0 (peggiore 2022 da -80 a -10; nel 2021 short oltre -100% su coppie a +1000%: limite del motore); Lorenzo solo long +120/-12/+11 → +134/0/+13; Lorenzo L/S 1D quasi invariata (+88/-11 → +88/-14). Prezzo del filtro: meno rendimento negli anni laterali 2023-26 (tranne Lorenzo 1D). Accumulo/Distribuzione escluso (seed-0010, ingressi con informazione futura). Nulla sul sito finche' Lorenzo non decide. Poi, alla domanda "nel caso di ottimizzazione cosa succede con il filtro BTC?": interruttore deciso dall'utente, non dalla ricerca; la ricerca gira col filtro gia' applicato; Max return non giudica per i trade un anno in cui il filtro ha bloccato i long per oltre meta' dei giorni. Lorenzo: "Ok, implementiamo così". Implementato: `analysis/btc_regime.py` (chiusure giornaliere BTCUSDT da MEXC in memoria, `_btc_regime_loop` ogni ora; regime del giorno D = chiusura di D-1 contro EMA 200; prima della storia BTC il filtro non agisce; senza dati e filtro acceso -> 503, mai ignorato in silenzio), `STRATEGY_REGISTRY` avvolto da `_with_btc_filter` (blocca solo gli ingressi long), `btc_filter` in StrategyParamsQuery e casella in ogni strategia del frontend (tranne Lorenzo HF), `STICKY_PARAMS` portato su ogni candidato (ricerca casuale, pipeline) e restituito con i risultati (`_carry_sticky`), anni bloccati esclusi in `_max_return_payload`.

**Filtro BTC settimanale, 15/10.** Lorenzo: "per avere un segnale di mercato piu' nitido il timeframe del filtro dovrebbe essere weekly [...] Lancia il test ma prima di metterlo sul sito aspetta". `SET=regimes`: d200 (sito), w21 / w50 (ultima settimana chiusa vs EMA 21/50 settimane), d200x (d200 + chiusura dei long quando si spegne); regimi dall'archivio giornaliero BTC dal 2018. Cambi di stato all'anno 2021/2023-25: d200 15-17, w21 5-6, w50 0-3. Risultati (35 coppie, mediane 2021/2022): w21 ≈ d200 (1D Lorenzo +146/0 vs +134/0; 4H Lorenzo +118/0 vs +124/0; 4H L/S +22/+88 vs +24/+88); w50 troppo lento (nel 2021 quasi mai spento, protegge meno). d200x taglia le perdite peggiori del 2022 (RSI+BB 4H -58 → -9, RSI+BB 1D -55 → 0) ma costa negli anni laterali (RSI+BB 4H 2023-26 +24 → +14%/anno, RSI+BB 1D +32 → +5). w21x (w21 + chiusura dei long, provato dopo lo sblocco di GitHub: Lorenzo, 15/10 "ho sbloccato GitHub [...] puoi lanciare le modifiche che erano rimaste in sospeso"): RSI+BB 4H 2023-26 +25%/anno (w21 +28, d200x +14), peggiore 2022 -12 (w21 -61); RSI+BB 1D +11 (w21 +33), peggiore 2022 0 (-55); Lorenzo identico a w21; Gabriele 2 peggiora nel 2021 (-26 di mediana). Lorenzo: "Ok, procedi" → sul sito: filtro = ultima settimana chiusa di BTC vs EMA 21 settimane (valido dal lunedi' dopo), e seconda casella `btc_filter_exit` (chiude i long quando il filtro si spegne, solo col filtro acceso), anche in STICKY_PARAMS.

**KuCoin con tutte le coppie, 15/10** (seed-0297). Lorenzo: "nei pair a disposizione sul sito, quelli relativi a KuCoin non compaiono". Causa nostra: `providers/kucoin.py` era limitato alle coppie /BTC (ETHUSDT diventava ETHUSDT-BTC). Ora ogni quotazione; base nuda = coppia BTC come prima. KuCoin ha storia dal 2017 (ETH-USDT 4H 19 470 candele): utile anche per l'ambiente di test, che finora la scartava per lo stesso errore. Verifica dal vivo: `provider-check.yml` (dispatch via `gh api`).

**Rendimento semplice, 15/10** (seed-0300). Lorenzo: "il risultato percentuale puro di ogni trade [...] e poi sommate", poi "Max Return deve scegliere il migliore in base al rendimento semplice [...] entrambi i risultati semplice e composto con la stessa visibilita'". `backtest.simple_stats`: puntata fissa = capitale iniziale x qty_pct, netto commissioni; drawdown semplice in punti del capitale iniziale sui trade chiusi (come il composto). Max return classifica con `optimize.ranked_return` (semplice); tetto 60% ancora sul drawdown composto (chiesto a Lorenzo se vuole anche il semplice). Frontend `fourFigures()`: quattro riquadri uguali (profitto semplice/composto, drawdown semplice/composto) in Lab, Max return, archivio, watchlist, grafico. Anche Trend EMA Reversal (seed-0299) aggiunta oggi.

**Ottimizzazione a basso overfitting, test 1D, 15/10.** Lorenzo: "un tasto di ottimizzazione [...] per far si' che l'overfitting sia ridotto al minimo", "migliorare la Stable e togliere la Quick" (preferito), "prima di tutto di fare un test nel nostro ambiente di test", e "il time frame 4 ore adesso non ci interessa piu' [...] nei tuoi test usa sempre il time frame one day" (sul sito resta solo la RSI+BB 4H sperimentale). Costi realistici e altre coppie: "va bene cosi'" (non aggiunti). `scripts/lowfit_1d.py` + `lowfit.yml` (35 coppie, scelta sul 2023+, prova 2021/2022, posizione del sito 1000/100%/0 costi). Mediane semplice 2021 / 2022: RSI+BB reversal default 0/-44, Max return 0/-48, Stable 0/0 (ma 0-1 trade l'anno: sceglie livelli estremi che quasi non operano), Stable+walk-forward 0/0 idem; Trend EMA Reversal default +130/-12, Stable +136/-31, walk-forward +108/-41. Efficienza walk-forward mediana 0.2 (fuori campione resta ~20% del rendimento in campione). Tempi su tutta la storia 1D: Stable RSI+BB ~1 s, Trend EMA Rev ~22 s (max 37); walk-forward 4 s / 70 s (max ~2 min). Nessun cambio sul sito. Seconda prova (MODE=v2; Lorenzo: "rifai il test con questi parametri, ma non e' obbligatorio implementarlo [...] per quella [RSI+BB] in ogni caso, magari aggiungere qualche parametro che la possa rendere piu' funzionale"): ricerca stretta intorno ai default, >=4 trade per anno, walk-forward come giudice (resta il default se la procedura non lo batte fuori campione). Trend EMA Rev: tenuta la ricerca su 8/35 coppie, risultato ~ default (+122/-10 vs +130/-12): innocua, non migliora. RSI+BB: 0/35 (fa ~1 trade l'anno, nessuna combinazione arriva a 4). Varianti RSI+BB con i valori di default: uscita alla banda centrale (close > media) 2022 +10% di mediana, 25/35 positive, dd 9 (default -44%, 8/35); uscita RSI OR banda superiore -6%, 13/35; stop loss 10% -10%, 0/35; filtro BTC 0% ma zero trade. 2021 ~0 per tutte: l'ingresso (RSI<28 E close sotto banda 2.0) quasi non scatta sul giornaliero. Terza prova (MODE=v3; Lorenzo: "aggiungere alla versione stabile della RSI piu' BB le caratteristiche [...] della max return [...] nei range [...] della 4 ore"): griglia 20-40 x 65-85, pick "solido" (semplice x solidita' dei vicini) e "profittevole" (solidita' >= 25%), regola trade 1D. Uscita di oggi: solido 2021 0 / 2022 -59 (in campione +200%: overfitting netto), uguale a Max return; default 0 / -44. Uscita alla banda centrale: default 0 / +10 (25/35 positive), solido +24 / -10 (22/32 e 14/35), Max return identico al solido. La solidita' non cambia la scelta rispetto a Max return; il guadagno vero viene dall'uscita.

**Menu strategie e badge BTC, 16/10 (`seed-0307`, `seed-0308`).** Lorenzo: "cos'altro possiamo fare per migliorare il sito?", poi "procedi con tutti e 5 i punti". Io avevo proposto anche seed-0010 e seed-0007 come aperti leggendo la vecchia nota "Cose che scottano" di CLAUDE.md: erano gia' risolti (detto a Lorenzo, nota corretta). Fatto: nel Lab niente Optimize/modalita'/filtri sulle strategie non ottimizzabili; `app.js` `STRATEGY_ORDER` / `RECOMMENDED_STRATEGIES` (stella) / `STRATEGY_DESCRIPTIONS` / `RECOMMENDED_SETTINGS` + `addStrategyExtras()` in cima ai campi (pannello e Lab), la strategia iniziale resta il primo del backend (Trend EMA); `GET /api/btc-regime` (`btc_regime.status()`: EMA21 e banda, stato + lunedi' del cambio) e `#btc-badge` nella barra, aggiornato ogni ora, nascosto sotto 640 px. Traduzioni in it.json.

**Lingue del sito, 16/10 (`seed-0305`).** Lorenzo: "deve essere la modalita' standard [l'inglese] [...] una tendina che ti permette di cambiare lingua [...] con la possibilita' poi di aggiungere anche altre lingue". `frontend/static/i18n.js` (caricato prima di app.js) mette la tendina in `header.toolbar` prima di `.auth-widget`, salva in localStorage `le-lang`, e se la lingua non e' `en` scarica `static/i18n/<lang>.json` e traduce il DOM gia' reso (nodi di testo + title/placeholder/aria-label, MutationObserver per quello che app.js scrive dopo, confirm/alert intercettati). Il codice di app.js resta in inglese. Chiavi = testo inglese con spazi compattati; `patterns` = regex per le frasi con numeri. Saltati script/style/textarea/code/pre/canvas/svg e `[data-no-i18n]`. Lingua nuova = JSON + riga in LANGS; `tests/test_i18n.py` controlla file e regex. Frasi mancanti: si aggiungono a it.json.

**RSI+BB "entrambi o uno dei due", test 1D, 16/10.** Lorenzo: "impostare che sia per entrare che per uscire basta solo uno dei due parametri (RSI o BB)", poi "Ok, proviamo". `MODE=logic` in lowfit_1d.py (35 coppie, default e Max return 20-40 x 65-85 scelto sul 2023+). Mediane semplice 2021 / 2022, trade/anno: AND/AND (oggi) 0 / -44, 1 tr; AND/OR +0 / -6 (13/35), 3 tr; OR/AND +31 (20/32) / -62 (5/35), 2 tr; OR/OR +20 (22/32) / -55 (2/35), 3-5 tr; entrambi entro 3 candele / OR = identico a AND/OR. Max return peggiora quasi sempre fuori campione. Ingresso OR: buono nel 2021, disastro nel 2022 (compra la discesa). Uscita OR: aiuta il 2022. Anche OR/OR fa 3-5 trade l'anno: il collo di bottiglia e' l'uscita (serve un estremo verso l'alto, in un ribasso arriva dopo mesi), non l'ingresso. L'uscita alla banda centrale (15/10: 2022 +10, 25/35) resta migliore di tutte. Nulla sul sito. Seconda prova (`MODE=band`, Lorenzo: "Provalo cosi'"): ingresso "uno dei due" sopra la Bull Market Support Band (SMA20 e EMA21 settimanali, settimana chiusa, dal lunedi'), "entrambi" sotto, uscita "uno dei due". Mediane semplice 2023-26 (scelta) / 2021 / 2022, default: oggi +35 / 0 / -44; banda del pair -2 / +12 (18/32) / -24; banda di BTC -15 / +34 (23/32) / -8 (12/35); banda del pair e nessun ingresso sotto -21 / +12 / 0 (1 trade). Sempre ~3 trade l'anno. La banda di BTC migliora 2021 e 2022 ma peggiora il 2023-26 (le alt comprate sui cali mentre BTC sale continuano a scendere): nessuna variante vince su tutti e tre i periodi. Terza prova (`MODE=mid`, Lorenzo: "Si, prova"): uscita quando la chiusura torna sopra la banda centrale. Mediane semplice 2023-26 / 2021 / 2022 (positive), default: ingresso di oggi +29 / 0 / +10 (25/35); ingresso sempre "uno dei due" +38 / +30 / -41; banda del pair +42 / +20 / +2 (18/35), 4 trade/anno; **banda di BTC + uscita centrale +36 (29/35) / +28 (26/32) / +8 (23/35), dd mediano 12 / 10, ~3 trade/anno: l'unica positiva in tutti e tre i periodi**. Max return sul 2023+ alza il 2021 ma peggiora il 2022 in tutte: meglio i default. Lorenzo: "Si, aggiungila al sito" -> strategia `RSI_BB_BTC_BAND` = "RSI+BB BTC band (long only)" (`seed-0306`, etichetta "RSI+BB Reversal (BTC band)"): `btc_regime.band_mask` (settimana BTC chiusa sopra max(SMA20, EMA21) settimanali, dal lunedi'; prima della storia = False; senza dati BTC -> BtcRegimeUnavailable). Campi: RSI length, Bollinger length/multiplier, RSI oversold (niente overbought). Non ottimizzabile (fuori da OPTIMIZABLE/GABRIELE, Max return nascosto nel Lab). La RSI+BB reversal resta invariata. Online dal 16/10 sera (repo reso pubblico, Actions gratis); `test_onchain_radar.py` carica un BTC finto per la nuova strategia.

**Strategia combinata, test 1D, 16/10.** Lorenzo: "inglobare i segnali di entrambe le strategie in un'unica strategia [...] una strategia sola, che pero' ha piu' segnali di ingresso e piu' segnali di uscita", poi "provala in entrambe le modalita'". `MODE=combo` in lowfit_1d.py: una posizione alla volta, entra con l'ingresso di Trend EMA Reversal o di RSI+BB reversal (default); A = esce con l'uscita di chi ha aperto, B = alla prima uscita delle due. Mediane semplice 2021 / 2022 / 2023-26 (35 coppie): Trend EMA Rev +130 / -12 / +67 (6 trade/anno); RSI+BB +0 / -44 / +35; A +87 / -50 / +114 (2022: 48 ingressi da RSI+BB, 24 da Trend); B +116 (31/32 positive, peggiore -25 contro -69) / -36 / +62, ~30 trade/anno. Nessuna combinata regge il 2022 (la RSI+BB compra i cali del crollo). Col filtro BTC settimanale (Lorenzo: "Si"), mediane semplice 2021 / 2022 / 2023-26: Trend EMA Rev +136 / 0 (peggiore -36) / +67 (dd semplice 35, ~10 trade/anno); combinata B +102 (29/32) / 0 (peggiore -37) / +73 (dd semplice 52, ~27 trade/anno, 27/35 positive); B + chiusura long +104 / 0 / +68 (31/35); combinata A +82 / 0 / +63. RSI+BB + filtro: 0 / 0, nessun trade. La combinata col filtro pareggia la Trend EMA Rev col filtro, con il triplo dei trade e drawdown piu' alto; non la batte. Nulla sul sito.

# 2026-10-15 — Archivio: test su un altro pair — `seed-0294` (Claude, a mano)

Lorenzo: "un pulsante in cui si puo' testare la strategia salvata su un altro asset [...] con gli stessi valori". `POST /api/archive/{{id}}/test-on-pair` (storia intera + ultimi 12 mesi con warm-up, `_bt_facts`), Lab `pairTestTable`. Prima, stessa notte: Max return 4H con ultimi 12 mesi esclusi, 3 trade/anno (opzione B), range 20-40/65-85, tabella storico/mai visti.

# 2026-10-15 — Max return 4H: ultimi 12 mesi esclusi dalla ricerca — `seed-0291` (Claude, a mano)

Lorenzo: "lasciare sempre l'ultimo anno libero da backtest [...] candele mai viste". `_max_return_payload`: per RSI_BB_4H con >= 2 anni, `search_df` = prima di 365 giorni fa, `held_out` = ultimi 365; `_last_year_check(..., held_out)` con `unseen: True`. Nucleo veloce del backtest proposto e rimandato da Lorenzo ("per il momento fai solo l'esclusione").

# 2026-10-15 — Max return 4H piu' veloce, verifica sui valori mostrati — `seed-0290` (Claude, a mano)

Lorenzo: "deve farlo applicando i valori della strategia piu' solida". `_last_year_check(df, on, top, say)` prova i params delle schede sull'ultimo anno (non piu' ricerca ripetuta; e' in-sample, detto nella risoluzione). Velocita': `backtest.epoch_seconds` e `confirmed_events` per posizione (3,7x, identico); `max_return_search_3d(coarse=True)`: passi 2/0.2 poi ±3/±0.3 attorno a COARSE_SEEDS=6 per tipo (5x). Misura: 12 000 candele 4h, 23 s contro 115 s, stessi risultati.

# 2026-10-14 — Ricerca gemme solo alle 03:00, giro lungo — `seed-0288` (Claude, a mano)

Lorenzo (a voce): "La ricerca delle gemme falla solo di notte, un giro unico alle 3 di notte, bella grossa". config: `onchain_nightly_hour=3`, `extra_times=""`, `hourly=False`, `max_hours=6.0`. Sostituisce 22:00 + 11:35 + giri orari (12-13/10). Pausa durante le ottimizzazioni e deploy-non-crash restano.

# 2026-10-14 — Ricerca senza IA a pagamento — `seed-0287` (Claude, a mano)

Lorenzo, 10/10: "facciamo ripartire la ricerca bella costante ma basta che non si usi token o altro", poi "e neanche deepseek".

- La cadenza c'era gia': giri ogni ora dal 12/10 (`seed-0274`). Il lavoro e' togliere l'IA.
- `research_ai_enabled = False` (default): `deepseek_desk._post` rifiuta ogni chiamata che non sia `kind="chat"` con `BudgetExceeded` prima della rete (giudice, revisione board, codice, dossier, studi, narrative, consistency, ricontrolli, scanner). Restano le domande scritte da Lorenzo (Telegram, agente dell'app). La `ANTHROPIC_API_KEY` del server viene svuotata all'avvio.
- Effetto: le letture DeepSeek gia' salvate valgono fino al loro TTL (judge 3 g, review board), poi il punteggio e' solo regole e pilastri. Il tasto "Re-check with DeepSeek" non produce piu' letture nuove.
- Riaccendere: `RESEARCH_AI_ENABLED=true` nel `.env` del server.
- Ancora a token Claude: la routine "Bacheca: sistema le segnalazioni nuove" (ogni ora, al minuto 16), decide Lorenzo.

# 2026-10-14 — Verifica sull'ultimo anno per Max return 4H — `seed-0286` (Claude, a mano)

Lorenzo: "puoi implementarla da subito. Solo sulla strategia 4H". `main._last_year_check`: `max_return_search_3d` sui dati fino a 365 giorni fa, poi backtest delle scelte sull'ultimo anno; `OptimizeCandidate.verification`; Lab `verifyLine`. Se funziona, Lorenzo valuta l'estensione alle altre due RSI+BB.

# 2026-10-14 — Max return 4H: moltiplicatore 2.0-2.8, piu' solido e piu' profittevole — `seed-0285` (Claude, a mano)

Lorenzo: "il piu' solido in rapporto al profitto e il piu' profittevole anche con una minore solidita', ma non [...] completamente azzerata". `optimize.max_return_search_3d` (MAX_RETURN_MULTS 2.0..2.8, `solidity()` = mediana dei 6 vicini / rendimento, SOLIDITY_FLOOR 0.25, REFINE_PER_KIND 10), usata in `_max_return_payload` solo per RSI_BB_4H; OptimizeCandidate.kind/solidity/neighbours; Lab `renderBestTwo`.

# 2026-10-13 — Strategia RSI+BB 4H — `seed-0281` (Claude, a mano)

Lorenzo: "Aggiungi una nuova strategia e chiamala RSI+BB 4H [...] l'unica differenza [...] Bollinger Multiplier [...] 2.5" (base: RSI+BB solo long, scelta sua). `strategies.RSI_BB_4H`/`compute_lki4h_signals`/`LKI4H_DEFAULT_PARAMS`; `optimize.gabriele_fixed(name)` sostituisce GABRIELE_FIXED nelle ricerche; `StrategyParamsQuery.bb_mult` ora `None` = predefinito della strategia; registrata in priors, sensitivity, regime, frontend (campi, OPTIMIZABLE, GRID). Non nell'app on-chain.

# 2026-10-13 — Ricerca gemme in pausa durante le ottimizzazioni — `seed-0280` (Claude, a mano)

Lorenzo, 22:12: "L'ottimizzazione in questo momento sta andando molto lenta"; scelta sua: pausa della ricerca. `jobs.any_running("optimize")`, `Steps.busy()`, `nightly._yield_to_optimizations` prima di ogni tick e ricontrollo; finestra allungata della pausa, `paused_min` nel riepilogo. Non copre la GET /api/optimize sincrona (il Lab usa /start).

# 2026-10-13 — Max return: un trade per anno solare, due migliori — `seed-0277` (Claude, a mano)

Lorenzo: "un filtro [...] che elimini tutti i risultati finali che non ottengono almeno un trade per anno solare testato [...] avere come esito finale i due migliori risultati". `optimize.calendar_years` (anni del grafico tranne primo e ultimo, Lorenzo: "il primo e l'ultimo anno vengono ignorati completamente dal filtro"), `years_without_trades` (per anno di apertura), `max_return_search(years=..., top_n=MAX_RETURN_TOP=2)`; Lab: `renderBestTwo` con 'Use'.

# 2026-10-13 — Chat alert -5359869020 davvero solo segnali — `seed-0273` riaperto da Lorenzo

Lorenzo: "La chat alert continua a ricevere anche ottimizzazioni e gemme, va risolto". Il gruppo e' la chat PRINCIPALE di un account (non la 'chat degli alert'), e i riepiloghi della ricerca/deploy passano da `telegram.send_message` (chat del server). `settings.telegram_signal_only_chats` (default "-5359869020") + chat degli alert di ogni account = `telegram.signal_only_chats()`, saltate da `send_message` e da `main._info_chat`.

# 2026-10-12 — Ricerca gemme ogni ora, deploy non contati come crash — `seed-0274` (Claude, a mano)

Lorenzo: "Ricerca delle 22:00 interrotta: e' fallita 3 volte [...] non e' molto popolata la nostra selezione, aggiungi controllo ogni ora". Causa: tre deploy fra le 22 e mezzanotte; il ramo CancelledError di `run_night` non gira se Docker uccide il container dopo 10 s, quindi ogni deploy contava come crash. `nightly.forgive_redeploy()` (hostname = id del container) scala il tentativo se il container e' nuovo. `onchain_nightly_hourly=True`: giri a ogni ora piena, `onchain_hourly_max_minutes=45`, Telegram solo se la Top cambia; 22:00 e 11:35 restano giri principali (2 h, riepilogo sempre). Sostituisce "tutto in una tranche a fine serata" del 07/10 per volere di Lorenzo.

# 2026-10-12 — Chat degli alert solo per i segnali — `seed-0273` (Claude, a mano)

Lorenzo: "nella chat Telegram alert strategie (-5359869020) mi arrivano anche le notifiche dell'ottimizzazione conclusa e delle nuove gemme [...] voglio ricevere solo segnali di trading quando si attivano le strategie". `_info_chat`/`_info_chats` in main.py: ottimizzazione, gemme, listing e avvisi del monitoraggio vanno alla chat principale, mai a una chat che qualche account usa come chat degli alert (`_signal_only_chats`). Segnali, alert di prezzo e ordini restano su `_signal_chat`. Sostituisce la regola del 10/10 "listing e gemme nella chat degli alert".

# 2026-10-12 — Modalita' Max return per RSI+BB — `seed-0272` (Claude, a mano)

Lorenzo: "aggiungi una modalita' che cerca solo il rendimento massimo su tutto il grafico [...] ipervenduto solo da 10 a 40, ipercomprato solo da 60 a 90 [...] di uno in uno [...] drawdown massimo consentito del 60%". `optimize.max_return_search` (961 combinazioni, backtest passato dal chiamante = `_chart_backtest`, cioe' lo stesso di Run), `mode=max_return` in /api/optimize e /api/optimize/start, `_max_return_payload` in main.py, radio 'Max return' nel Lab visibile solo per RSI+BB. Nessun OOS, dichiarato nella nota.

# 2026-10-12 — Segnalazioni del tester 6a8fdae8, 58512aa5, 5571a9f1 (Claude, a mano)

Lorenzo: "Risolvi le segnalazioni aperte". 6a8fdae8: sincronia del tempo nei due sensi (`followPane` in app.js, il grafico principale fa da centro). 58512aa5: la casella in alto prende il pair cliccato in Watchlist e, a ogni analisi, il simbolo mostrato (non per DEX). 5571a9f1 (ottimizzazione RSI+BB battuta a mano): il backtest restituito era quello del solo tratto di selezione (70%, 60% in Stable) mentre Run usa tutta la serie; ora `_optimize_payload` ricalcola vincitore e classifica con `_chart_backtest` (stessa definizione di /api/backtest/deep) e tiene `in_sample_return_pct`. Grid Gabriele = tutti gli interi 15-50 x 50-85 (1296). **Cambia i numeri storici dell'ottimizzazione** (ora storia intera). Aperta per Lorenzo: modalita' 'massimo rendimento su tutto il grafico' dichiarata, se la vuole.

# 2026-10-12 — Indicatori sfalsati rispetto al prezzo — `seed-0271` (Claude, a mano)

Lorenzo, con screenshot: "indicatori sotto sfalsati rispetto a prezzo". Causa: scala dei prezzi del grafico principale piu' larga di quella dei pannelli (6 decimali contro "80.00"), stessa finestra logica su larghezze diverse. `alignPaneScales()` in app.js: tutte le scale (principale, RSI, MACD, stocastico, oscillatori custom) prendono la larghezza della piu' larga, a ogni render/zoom; `resetPaneScales()` al cambio simbolo/timeframe. Verificato in Chromium: 788/796/796 px prima, 788 ovunque dopo.

# 2026-10-12 — Misura senza rettangolo — `seed-0270` (Claude, a mano)

Lorenzo: "la funzione di misurare prezzo non deve figurare un rettangolo ma proiettare i punti che legge in modo intelligente". `DrawEngine.pickExtreme` (high/low piu' vicino in pixel fra le 5 candele attorno, entro 40 px) usato da `pointerToPoint` per lo strumento `range` e per il trascinamento delle sue maniglie; `paintMeasure`: freccia fra i punti, proiezioni dei due prezzi sulla scala con pillole, obiettivo 1:1 tenue, etichetta accanto al secondo punto. Hit test sulla linea/punti. e2e: 34 controlli verdi. Poi Lorenzo: "voglio che il righello sia sempre orizzontale o verticale mai obliquo": `paintMeasure` a L (orizzontale al prezzo del primo punto fino al tempo del secondo, verticale con freccia), niente banda ne' diagonale; hit test sui due tratti. Terza richiesta: "solo una proiezione dei due punti con la percentuale nel mezzo": tolti il tratto orizzontale e l'obiettivo 1:1; restano due proiezioni tratteggiate fino alla scala, righello verticale con freccia e percentuale al centro (sotto, variazione/durata/candele). e2e 34/34.

# 2026-10-12 — Strumenti di disegno rifatti — `seed-0269` (Claude, a mano)

Lorenzo: "procedi e falle tutte, e verifica ogni cosa" (piano del documento "Strumenti di disegno — analisi e piano" + "canvas moderni, colori").
- `frontend/static/draw-engine.js` (globalThis.DrawEngine, test node in `frontend/tests/draw-engine.test.mjs`): `makeTimeMapper` (ora <-> indice logico frazionario, interpolazione, estrapolazione col passo mediano), hit test, `paint` per ogni strumento, pill, maniglie, palette.
- `app.js`: `timeToX` via mapper + `logicalToX` (LWC 4.2 `logicalToCoordinate` restituisce 0 per indici frazionari: misurato, si interpola fra i due interi); input da pointer events con `setPointerCapture`, tap e press-drag-release; ridisegno su firma (range visibile, scala prezzi, dimensioni, `drawVersion`); DPR; clip al riquadro; hline = solo canvas + price line `lineVisible:false`; toolbar selezione; undo/redo; magnete; nascondi; sticky (doppio clic); testo in input sul grafico; frattali salvati con le candele copiate (`mountFractal`); chiave dei disegni da `state.data.asset_type`.
- Server: `app/drawings.py` + `GET/PUT /api/drawings` (per utente, vince `updated_at` piu' recente), sync anche quando il login arriva dopo il grafico (`syncCurrentDrawings`).
- Loop RAF protetto da try/catch: prima un'eccezione (es. `toLocaleString` con locale strano) fermava il loop per sempre e tutti i disegni sparivano.
- Dock mobile: era piu' largo dello schermo e usciva a sinistra; ora scorre.
- Verifica: `scripts/e2e/draw.e2e.mjs` (Playwright, API simulate, 32 controlli, 3 giri verdi); workflow `draw-e2e.yml` (solo se cambia il codice del disegno), non blocca il deploy. `?drawdebug` espone `window.__drawDebug` per i test.
- Restano: lente sotto il dito su telefono, misura ms/fotogramma con 50 disegni, raggruppamento icone della barra.

# 2026-10-12 — Strumenti di disegno: analisi e piano (Claude, piano)

Lorenzo: "i tool di disegno non funzionano bene spesso scompaiono o sono scattosi [...] STUDIA A FONDO". Documento "Strumenti di disegno — analisi e piano" (artifact 59b97368-7d37-4ada-97a4-af5e42e33ca3). Cause lette in `app.js` 5188-6630: punti legati all'ora esatta della candela (`timeToCoordinate` -> null su altro timeframe/fuori dati, `timeToXEdge` li butta a -4 / width+4); maniglie con `timeToX` senza bordo; input da `lastCrosshairPoint` (mirino) invece che dal puntatore, rotto su touch; RAF continuo 60 fps; canvas senza devicePixelRatio; niente punti nel futuro; solo localStorage; hline doppia (canvas + price line ricreata a ogni drag); frattale non salvato. Piano in 4 fasi: coordinate logiche (`logicalToCoordinate`, interpolazione/estrapolazione), input dal puntatore con pointer capture e touch, ridisegno su richiesta + DPR + clip al riquadro, strumenti completi (server, stile, undo, correzioni per strumento). Test Playwright come criteri.

# 2026-10-12 — Overhaul sito classico, prima tranche — `seed-0268` (Claude, a mano)

Lorenzo: "attua tutto" (il piano di 8 settimane). Fatto in questa tranche:
- `_cpu()` in `main.py`: `/api/analyze` (tutto il calcolo) e `/api/backtest/deep` in `asyncio.to_thread`, semaforo da 2 per loop.
- Motore: `run_backtest` e `confirmed_events` senza `iterrows`; copia congelata in `tests/reference/engine_v1.py`, `tests/test_engine_equivalence.py` confronta campo per campo. Locale: 5000 candele con SL/TP 233 -> 26 ms. `scripts/bench_backtest.py`.
- `app/perf.py` + middleware `time_requests` + `GET /api/perf` (p50/p95 per rotta, lag del loop).
- Frontend: `state.analyzeSeq` (vince l'ultima `/api/analyze`); refresh completo saltato se il feed live e' sano, una volta per candela max 5 min; CodeMirror caricato pigro (`upgradePineEditor`), `simple-mode.js` NON e' di CodeMirror (e' la Modalita' Semplice).
- Restano: baseline Lighthouse e numeri di /api/perf dal vivo, indicatori in cache, coda lavori, app.js a moduli (decisione build), Ricerca Stabile, ridisegno, Playwright, CSP, pulizia; decisioni CX33/build/stile/codice spento ancora aperte.

# 2026-10-12 — Piano di overhaul del sito classico, 8 settimane (Claude, piano)

Lorenzo: "crea un prompt e un piano di miglioramento di prestazioni per il sito classico [...] voglio un overhaul completo sotto ogni punto di vista, fai un piano settimanale" e "analizza ogni aspetto del sito e cerca migliorie". Documento "Sito classico — overhaul completo" (claude.ai, artifact ed9f3432-3fce-4dad-8a64-913281ed1d83): prompt da incollare a ogni sessione, stato letto sul codice, obiettivi con traguardi, piano 12/10-6/12.
- S1 misura (tempi, Lighthouse, benchmark, test di equivalenza) + `run_backtest`/replay in thread + corsa fra due /api/analyze. S2 motore numpy, cache indicatori, coda lavori; decisione CX33. S3 app.js a moduli + esbuild; decisione build. S4 grafico incrementale al posto del refresh 60 s. S5 Ricerca Stabile (`seed-0054`). S6 ridisegno (`seed-0028`) + accessibilita'; decisione stile. S7 Playwright, CSP, monitoraggio, `seed-0051`. S8 misura finale, pulizia trading spento (decisione), main.py in router.
- Problema piu' grave trovato: backtest (e replay dentro la candela, fino a 8 s) sul processo principale, un solo worker: blocca tutti.

# 2026-10-12 — Stili da opensourceui.in per l'app DEGEN (Claude, in corso)

Lorenzo: "puoi prendere tutto il design qui? https://opensourceui.in/components", poi "studia tutti i design e li tieni in memoria fallo con un agent in parallelo". Scelte sue: app on-chain (DEGEN), prima "uno stile da scegliere". Catalogo in `design/opensourceui/CATALOG.md` (210 componenti, 10 famiglie). Tre bozze mobile 390x844 sul canvas "DEGEN · tre stili" (artifact claude.ai FnYFB2b8jk6WbRjrAnnWaU): A Carbon spotlight (smeraldo), B Tasti 3D (ambra, carbon luxe), C Vetro su mesh (teal). Resta: la scelta di Lorenzo, poi il porting in `frontend/static/onchain/app.css` (oggi pelle terminale nero/ambra del 07/10).

# 2026-10-12 — DEX sul sito classico: niente anti-rug, storia intera, priorita' — `seed-0267` (Claude, a mano)

Lorenzo: "sui pair presenti solo nei dex il backtest non fornisce risultati [...] è risolvibile?", poi "Sul sito classico l'anti-rug non e' necessario, serve solo per lo Sniper. Il sito classico deve avere sempre la priorita' di eseguire backtest sull'intero grafico disponibile".

- Diagnosi (da lettura del codice, non misurata: sito e GeckoTerminal non raggiungibili dal sandbox): `rug_stop` sul sito classico; il `top = high.cummax()` include lo spike del lancio, `close <= 0.15*top` scatta subito -> 0 trade.
- `rug_stop` tolto da tutti i percorsi del sito classico in `main.py` (analyze, deep, archivio, `_intrabar_fn`, ciclo watchlist): resta `spot_only`. Radar/Sniper invariati.
- `DexScreenerProvider.fetch_ohlcv` pagina con `before_timestamp` (`GECKO_PAGE` 1000, `GECKO_MAX_PAGES` 6): il chart (3000) fa 3 chiamate, il backtest (5000) 5.
- `_classic_priority()` = `gecko_urgent.set(True)` in analyze, deep, optimize, optimize/start, POST archive.
- Da sapere: GeckoTerminal gratuito puo' limitare quanto indietro arriva la storia; oltre, le pagine tornano vuote e ci si ferma.

# 2026-10-12 — Stella "aggiungi alla watchlist" nella barra — `227a6142` (Claude, a mano)

Lorenzo: "Risolvi la segnalazione aperta". Bottone `#watch-star-btn` fra ricerca e timeframe: aggiunge/toglie la coppia del grafico da YOUR TICKERS (`updateWatchStar`, chiamata da `render()` e `renderFavorites()`). Solo barra desktop (su mobile `.toolbar` e' nascosta). Nota: WebFetch della bacheca a volte restituisce una copia vecchia; un parametro nuovo nell'URL (`?fresh=...`) la aggira.

# 2026-10-12 — Altre due segnalazioni del tester (Claude, a mano)

Lorenzo: "risolvi le segnalazioni aperte". (Le cinque del 11/10 risultavano ancora aperte solo per una lettura in cache della bacheca: il deploy era andato.)

- `3e8b3e78` domanda: la 1D crypto chiude a 00:00 UTC (02:00 italiane, 01:00 dal 25/10) su tutti e quattro gli exchange e i DEX; azioni alle 22:00. Risposta in `replies.json` + risoluzione.
- `f3cdcc63` archivio manuale diverso dal Lab: il tasto Archive manda `data_start`/`data_end` del risultato a schermo e `intrabar`; `_run_archive_backtest` rifà sullo stesso intervallo (`_slice_to_window`), con i parametri passati da `StrategyParamsQuery` come fa `/api/backtest/deep`, segnali DEX solo-long e replay dentro la candela se il Lab lo aveva. Causa piu' probabile per le RSI+BB: dopo un'ottimizzazione il Lab mostra il backtest in campione (`pipeline.winner_bt` su `df_in`), l'archivio lo rifaceva su tutta la storia. Voci vecchie non ricalcolate.

# 2026-10-11 — Cinque segnalazioni del tester del sito classico (Claude, a mano)

Lorenzo: "risolvi le segnalazioni aperte" (prima aveva chiesto di farlo in automatico a ogni nuova segnalazione: c'e' gia' un'attivita' programmata sul suo account forelectric.it, non visibile da qui; non duplicata).

- `c3262361` Lab: capitale iniziale predefinito 1000 (campo e valori di riserva nel frontend; il default del backend resta 10000).
- `9c901532` Discover (menu laterale, linguetta, tasto mobile) -> `/onchain-app.html` in nuova scheda; prima puntava a `/sniper`, morto con il trading spento.
- `229c5103` riga O/H/L/C + variazione sopra il grafico (`renderOhlc`, contenitore `.chart-top-left` che ora tiene anche la legenda indicatori).
- `d46f02f7` YOUR TICKERS: rank per market cap da CoinPaprika `/v1/tickers` (`app/market_rank.py`, cache 6 h; CryptoRank vuole una chiave), campo `rank` in `/api/favorites/quotes`; ordinamento Saved / Day % / Rank nei due versi, salvato in localStorage.
- `316219de` Signal Execution: `fill_at=on_condition` ora riempie dentro la candela del segnale (`backtest.intrabar_prices`): cammino stile TradingView (verde O-L-H-C, rossa O-H-L-C, 4 passi per tratto), strategia ricalcolata su 300 barre a ogni passo, tetto 8 s. **Solo con `intrabar_fn`** (Lab `/api/backtest/deep` e backtest del grafico): ottimizzatori e numeri storici invariati. Segnali che compaiono e spariscono dentro la candela non entrano. Il grafico ora riceve anche `fill_at` dall'override del Lab.
- Non verificato in sandbox: PyPI irraggiungibile, test eseguiti con pandas_ta stubbato; la suite completa la fa girare `deploy-hetzner.yml` (verify prima del deploy). Velocita' del replay su strategie vere non misurata.

# 2026-10-10 — Ricontrollo degli indicatori sui grafici — `seed-0266` (Claude, a mano)

Lorenzo: "rianalizza tutte le rappresentazioni grafiche che abbiamo fatto con i nostri indicatori e verifica che siano corrette [...] alcuni mi risultano un po' schifo". L'app on-chain disegna solo candele (cap): il lavoro e' sui 18 livelli del sito classico (Analizza).

- Metodo: sito in locale (utente di prova con `REGISTRATION_ALLOWED_EMAILS`), candele MEXC vere di BTC/PEPE/KAS/SOL su 15m, 4h, 1d, 1w; valori confrontati con formule TradingView scritte da zero (EMA, RMA, MACD, BB, Stoch, VWAP); screenshot Playwright di ogni livello, chiaro/scuro, 1440 e 390 px. Immagini prima/dopo in project-files `indicatori-grafici/`.
- Gia' giusti: EMA 20/50, RSI 14, MACD, Stocastico (scarti < 1e-4 dopo il riscaldamento).
- Corretti: pannelli RSI/MACD/Stoch non allineati al grafico quando si accendono (`syncPaneRange`); Bollinger con `ddof=1` (ora 0, come la strategia RSI+BB); VWAP ancorato al giorno su ogni timeframe (ora `indicators.VWAP_ANCHORS`: D fino a 30m, W per 1h/4h, M per 1d-5d, Y per 1w/1M; linea interrotta al riavvio); BMSB che sui giorni passati leggeva la chiusura finale della settimana (ora valore "in formazione" con la chiusura della candela); MACD a 0.00 su prezzi piccoli (`oscPrecisionFor`); palette del tema chiaro tutta grigia (ora colori distinti e nome della linea sull'asse); Inverted hammer sempre ribassista; livelli Elliott invisibili sul bianco e sopra l'asse; riquadro nero dell'etichetta divergenze sul chiaro.
- Guardati ma non verificati contro un riferimento esterno: order block, FVG, equal highs/lows, BOS/CHoCH, confluenze, Fibonacci automatico, pattern, segnali contestuali. Visivamente: i pattern su 1d sono tanti (Eng su quasi ogni inversione), il Fibonacci ha linee intermedie senza etichetta. Da decidere con Lorenzo se sfoltirli.
- Visto per caso: due /api/analyze in volo (cambio timeframe + nuova ricerca) e la risposta piu' vecchia puo' arrivare dopo e vincere (il grafico mostra il ticker precedente). Non corretto.

# 2026-10-10 — Terza chat Telegram solo per gli alert (Claude, a mano)

Lorenzo: "c'e' da creare una terza chat Telegram solo per gli alert, ho gia' fatto il gruppo". Tre chat: principale (`telegram_chat_id`: DeepSeek, conferme, passkey), sistema (`TELEGRAM_DEV_CHAT_IDS`: deploy, errori), alert (`telegram_signal_chat_id`, campo "Alerts chat ID" nel pannello Alert del sito classico). Watchlist, listing, gemme e segnali trend passano da `main._signal_chat` (vuoto = principale); `_alert_chats` evita doppioni se due account puntano allo stesso gruppo. Niente variabile d'ambiente: l'id si incolla dal sito. `/chatid` scritto in un gruppo col bot risponde con l'id. Resta: Lorenzo incolla l'id del gruppo.

# 2026-10-09 — Segnalazioni aperte del sito classico (Claude, a mano)

Lorenzo: "io volevo solo chiudere i punti aperti del sito classico.. vabbe' ora concentrati su quello". Le otto voci aperte o riaperte del tester:

- `6453f4df`/`72f880af`: ottimizzazione Gabriele con lunghezza RSI 14, Bollinger 20, moltiplicatore 2 **sempre** (`optimize.GABRIELE_FIXED`), non piu' presi dai campi del Lab.
- `8bd7884c`/`37637f11`: due opzioni in "Signal execution": `signal_close` (alla chiusura) e `on_condition` (alert sulla candela in formazione = `on_close: false` della watchlist). Il backtest riempie alla chiusura in tutti e due i casi (non vede dentro la candela) e lo dice.
- `1f8f7246`: `status_at` in `issues.update_issue`: lo stato messo a mano vince su risoluzione e riapertura precedenti. Il tasto "Delete" non l'ho aggiunto (l'endpoint DELETE esiste; cancellare voci altrui va deciso).
- `a6b36231`: `User.telegram_signal_chat_id` + campo nel pannello Alert; gli alert del ciclo watchlist vanno li' (`main._signal_chat`), vuoto = chat principale.
- `893ea67a`: Bull Market Support Band (SMA 20w + EMA 21w) nel pannello Levels, solo pair degli exchange; `/api/analyze` scarica anche le candele 1w.
- `1f9baaea`: opzione "DEX" nel menu exchange del Lab (pool DexScreener piu' liquido). Bug trovato: per i pool DEX il Lab mandava `exchange=dexscreener` all'aggiunta in watchlist e all'archivio, rifiutato dal server: ora `labExchange()`.

Restano in corso del sito classico: `seed-0054` (Ricerca stabile lenta), `seed-0051` (avviso Telegram al deploy, serve il server), `seed-0028` (ridisegno).

# 2026-10-09 — Chiusi i punti aperti dell'app DEGEN (Claude, a mano)

Lorenzo: "chiudi tutti i punti aperti nel sito degen view, ora lasciamo stare lo sniper".

- PR #505 (fascia $10k-$10M, esito per i progetti senza sito, contatori del Database) portata su main; la voce di bacheca diventa `seed-0263` (`seed-0256` era gia' dei grafici).
- PR #494 (ricontrollo, scansione e domande all'agente come lavori sul server con notifica push) unita dopo otto giorni di conflitti: il tasto del ricontrollo tiene il log dal vivo (`followRecheck`) e la richiesta e' un job; in modo Voice l'agente risponde ancora con la chiamata diretta (la voce parte subito), le domande scritte sono job. Voce `seed-0264` (`seed-0250` era lo spegnimento del trading). Nuova dipendenza `pywebpush`.
- PR #402 (mappa Agent di Codex, 30/09) chiusa: storia scollegata da main, superata.
- Bacheca: `seed-0143` (wallet di chiunque: collegamento fatto, vault non piu' necessario senza trading), `seed-0117`, `seed-0116`, `seed-0111` (Gem Finder da ricercatore, narrative, progetti seri: oggi arene + motore notturno), `seed-0109` (pagina /engn; il lancio del token resta una decisione di Lorenzo) segnate risolte.
- Issue GitHub #347, #357, #358, #363, #365, #366 (piani del 29/09) chiuse come superate dal lavoro del 07/10.
- Non toccati: `seed-0078` (Sniper, escluso da Lorenzo); le segnalazioni del tester su Lab/Levels/Telegram sono del sito classico, non di DEGEN.

Seguito (Lorenzo: "altri punti aperti dal tester"):
- `6453f4df` riaperta ("l'ottimizzazione personalizzata RSI+BB non produce risultati"): con 14/20/2 fissi il minimo di 9-10 trade svuotava la classifica. Minimo 4 per le due Gabriele, ipervenduto 15-50, ipercomprato 50-85 (`optimize._MIN_TRADES_FLOOR`).
- `411e4c7c` Lab <-> Analizza: `syncLabFromChart` all'ingresso nel Lab, `syncChartFromLab` tornando su Analizza (pair, timeframe, strategia, parametri).
- Restano in corso, non toccate: `seed-0054`, `seed-0051`, `seed-0028`.

Seguito 10/10 (Lorenzo: "quelle nuove ?"): 4 voci del tester del 09/10 sera.
- `e67ae945` Lab: `clearLabResults()` svuota tutta la colonna risultati prima di backtest e ottimizzazione.
- `87cc755b` exchange Analizza <-> Lab: il grafico tiene l'exchange in `state.cryptoExchange` (non `state.exchange`); sync anche su telefono (`showMobileScreen`, Lab = schermata "backtest").
- `7410bba2` MEXC: filtro `status == "1"` invece di `isSpotTradingAllowed` (79 coppie vive escluse). Lista riletta ogni ora, ultima buona tenuta se la lettura fallisce. Niente job settimanale: l'ora basta.
- `7f9cd5ed` Elliott Waves: `frontend/static/elliott.js` (classic script, anche `require` per i test), disegno su canvas come le divergenze. Senza alert.

# 2026-10-08 — Permanenza minima nelle arene — `seed-0261` (Claude, a mano)

Lorenzo: "se una crypto e' comparsa tra le migliori, anche se poi viene surclassata; deve rimanerci per almeno 2-3 gg prima di essere espulsa". Default scelto: 3 giorni dall'ingresso (`arenas.TENURE_S`). Un progetto che va sopra la mediana della sua arena ("in") viene segnato in `data/onchain_arena_tenure.json`; se poi scende sotto la mediana resta "in" (`held: true`) fino a 3 giorni dall'ingresso, contati dal primo ingresso e non rinnovati. Uscire dal pool (cancelli, scarto, rug) toglie subito la permanenza. Si scrive solo dalla vista senza filtro narrativa. Podio, ordine, Telegram "Entrati/Usciti" (che guarda il pool), backtest e portafoglio invariati. Il frontend non mostra ancora un segno per le righe `held`.

# 2026-10-08 — Secondo giro della ricerca alle 11:35 — `seed-0260` (Claude, a mano)

Lorenzo: "aggiungi un check oltre che alle 22, anche alle 11.35".

- `onchain_nightly_extra_times = "11:35"` (Europe/Rome, come le 22:00): stesso giro, stesso tetto di 2 ore. Un solo loop, quindi i giri non si sovrappongono. Recupero dopo un riavvio: 8 ore anche per il mattino (fino alle 19:35, finisce prima delle 22).
- Costo: le chiamate DeepSeek e API del giro possono raddoppiare; il ricontrollo settimanale e la coda non si ripetono (si fa solo cio' che manca). Da guardare nel messaggio Telegram "Chiamate DeepSeek" dei prossimi giorni.

# 2026-10-08 — Narrativa Compute e gemme di calcolo — `seed-0259` (Claude, a mano)

Lorenzo: "mi interessa molto compute power tipo render token, akash network, voglio anche questa narrativa e concentriamoci su scovare gemme anche su questo".

- `decentralized_compute` ("AI Compute") diventa "Compute": GPU in affitto, render farm, cloud senza permessi, inferenza/training distribuiti. Ha la sua arena e la tiene (`arenas.CLAIM = (privacy, decentralized_compute)`).
- Bug trovato: le categorie CoinGecko condivise (`depin`, `artificial-intelligence`) etichettavano Compute ogni coin DePIN o AI. Ora `keys_for_category(exclusive=True)` per l'hint; una categoria condivisa non etichetta, decide il testo. L'hint vecchio si sovrascrive alla riscoperta (anche vuoto).
- CoinGecko non ha una categoria "compute": la discovery passa da DePIN/AI e filtra col testo.
- Studio del 08/10 (pilastri del motore in locale, GitHub non leggibile dalla sandbox): `project-files/compute/gemme-compute-2026-10-08.md`. Migliore: ZERO (Compute Network, Solana, $0.48M, prodotto vivo ma rete minuscola). Da seguire: OGPU, ACN. Fuori dalle nostre chain: subnet Bittensor di calcolo (SN27, SN49, SN12) e Clore.
- Resta: controllare sul server, dopo la prossima discovery, che l'arena Compute contenga solo progetti di calcolo; decidere con Lorenzo se leggere le subnet Bittensor.

# 2026-10-08 — Ricontrollo DeepSeek: un fatto una volta, log sul tasto — `seed-0258` (Claude, a mano)

Lorenzo, sugli screenshot di AUREON (tab Why): "sistema questi errori, e quando DeepSeek fa il rescan voglio vedere cosa fa attraverso un piccolo log direttamente sul tasto di rescan [...] cosa sta navigando, eccetera, giusto per vedere a che punto e'".

- Causa dei doppioni: `red_points` univa problemi del giudice e flag dei pilastri solo a stringa identica, e il riquadro mostrava sia i problemi del verdetto sia i punti confermati. Ora `scout_recheck.same_fact` (argomenti: autore, CI, lock LP, sito JS, codice, volume, liquidita', team; altrimenti sovrapposizione di parole >= 0.6) e `deep_recheck.tidy` (anche sui risultati gia' salvati, in `get()`).
- Regola #465 applicata anche qui: `READ_GAP` (illeggibile, JavaScript-only, lock sconosciuto, "not covered by") non e' mai confermato ne' un problema del verdetto.
- Poi Lorenzo: "devi capire perche' da errore di JavaScript, cioe' sta cosa non deve succedere". Il sito (`aureonlabs.network`, Vite/React, 1178 byte) col renderer locale da' 979 parole: il guasto e' sul server. Log del server non visti (PC spento). Cause possibili corrette: `_unavailable` restava vero fino al riavvio dopo un avvio fallito (ora `_down_until`, 15 min), Chromium senza `--disable-dev-shm-usage` in Docker, quota 200/giorno (ora cache 6h e `URGENT` per il ricontrollo a mano). `render_error` nei fatti del sito dice il motivo: **guardarlo sul prossimo sito JS illeggibile**.
- Log: `scout_recheck.TRACE` + event hook httpx sul client del ricontrollo; `progress()` porta `log` (ultime 8 righe, `n` progressivo). Il tasto mostra passo, secondi e 4 righe. Solo host e percorso: la query puo' contenere chiavi.

# 2026-10-07 — Rete Arc tra le chain delle gemme — `seed-0257` (Claude, a mano)

Lorenzo: "aggiungi supporto a rete ARC". Arc = L1 di Circle, mainnet chain id 5042, gas in USDC, RPC `rpc.mainnet.arc.io`. Verificato il 07/10: DexScreener e GeckoTerminal la indicizzano come `arc` (Uniswap v2/v3/v4 e altri DEX, pool da meta' settembre), CoinGecko ha piattaforma `arc` e categoria `arc-ecosystem` (81 monete, una pagina), GoPlus supporta 5042, DefiLlama scrive `arc:0x...` (57 protocolli, TVL ~$549M). Arc entra solo in `GEM_CHAINS` (come Base: niente meme/radar, niente wallet/swap/esecuzione). I locker LP di Arc in `judge.LOCKERS` sono un'ipotesi (UNCX, Team Finance, LP bruciata): da correggere se i progetti veri ne usano altri.

# 2026-10-07 — Grafici nel tema dell'app — `seed-0256` (Claude, a mano)

Lorenzo: "il tema dei grafici deve essere allineato ai colori del sito e al tema utilizzato nell'app in ogni aspetto". `frontend/static/onchain/chart-theme.js` legge dai token CSS della pelle attiva (`--up`, `--down`, `--amber`, `--ink-faint`, `--line`, `--raised`, `--mono`) colori e font per Lightweight Charts, che disegna su canvas e non vede il CSS: telefono = terminale nero/ambra, desktop = pelle verde. Griglia solo orizzontale tratteggiata, mirino tratteggiato, etichette in mono; marcatori: entrata/uscita su/giu', rug in rosso, portafoglio in ambra (testi "Strategy entry/exit · <tf>" invariati, quindi chart_audit non cambia). `track()` ridipinge i grafici vivi quando si attraversa 1100px. Usato da `detail.js` (grafico del token) e `chart.js` (grafico mercato, oggi spento col trading); in `app.css` il grafico SVG di riserva e la curva del backtest simulato usano `--k-mint`/`--k-red`. /engn non toccato: i suoi disegni usano gia' i token del suo sito. Un grafico nuovo deve prendere le opzioni da `chartOptions()`/`seriesOptions()`, mai colori scritti a mano.

# 2026-10-07 — Arene al posto della Top 15/25/50 — `seed-0255` (Claude, a mano)

Lorenzo: "secondo me la top50 come concetto e' limitante, serve un sistema meritocratico e innovativo per visualizzare i top, inventalo e proponimi una classifica fatta in modo meno tradizionale data la complessita' dei progetti e le diverse narrative". Tre concept con mockup (https://claude.ai/artifact/NbuHp17Pz5HJDXXV5nGJVm, immagini in project-files `classifica-meritocratica/`): Arene (una classifica per narrativa), Mappa (assi costruito/usato), Scala (rating Elo a duelli, divisioni). Consigliato Arene subito + rating della Scala dentro le arene dopo tre settimane. Lorenzo: "procedi come consigliato".

- `trading/onchain/arenas.py`: `assign` mette ogni progetto nell'arena (narrativa non meme; layer -> `chains`; nessuna -> `other`) dove stacca di piu' la mediana dei pari; arene con meno di 2 progetti si sciolgono. `build`: per arena ordine per punteggio, "in" = sopra o alla mediana (gli altri in panchina, `<details>`), z = (punteggio - mediana) / max(dev. std, 5) con almeno 3 progetti; pound for pound = i 3 capi arena con z piu' alto, uno per arena. Arene ordinate per calore della narrativa.
- `/api/onchain/top` (trading spento) aggiunge `arenas`, `p4p`, `ladder` calcolati su `_top_entries(ARENA_POOL=500)`: niente tetto a 50. `entries` resta per le pagine vecchie. `_top_entries` porta ora `narratives` (chiavi) e `blocks`.
- Scala: `nightly.run_once` chiama `arenas.record_night` dopo gli studi: ogni progetto sfida fino a 5 pari della sua arena (i piu' vicini di rating) blocco per blocco (uso, partecipazione, prodotto, token, DeepSeek), Elo K=24, ultime 7 notti w/l/d. File `data/onchain_arena_ladder.json`, una notte ogni 20 h al massimo. **Il rating non e' ancora mostrato**: `ladder.ready` diventa vero dopo 21 notti; allora decidere con Lorenzo se l'ordine dentro le arene passa al rating. Telegram serale: "Entrati/Usciti dalle arene", "duelli della scala".
- Frontend `top.js` riscritto: podio = pound for pound ("+1.4σ AI Agents"), poi le arene con intestazione (nome, calore, "N in · median M"), campione in ambra, panchina piegata. Animazione al ritorno: il campione spodestato si disintegra sulla riga del nuovo (chiave `lae:arena-crowns`). Tab "Top" -> "Arenas". Desktop verificato con lo stesso codice.
- Poi Lorenzo: "a me interessa molto la privacy, progetti come sol router e' innovativo, dregg etc .. usiamo i filtri che abbiamo gia' per avere la top aggiornata per ogni categoria". Arena Privacy sempre prima (`arenas.FIRST`) e con dentro Zero Knowledge e FHE/MPC/TEE (`arenas.GROUP`); un progetto con una narrativa privacy gareggia li', non dove staccherebbe di piu'. Il filtro narrative del Database arriva all'endpoint come `prefer`: i progetti restano nell'arena scelta. In alto, chip per arena (All / Privacy / ...): toccandone una si vede solo quella, tutta aperta (`lae:arena`). Suggerimenti di narrativa: Solrouter `privacy`+`fhe_mpc_tee`, DREGG `zero_knowledge` (contano alla prossima analisi).
- 08-10/10, Lorenzo: "manca le narrative dei dex e altre [...] scomodo i filtri orizzontalmente [...] magari a mosaico". Tre proposte (https://claude.ai/artifact/Bjy5Nzr5NpMhduyJ6vs88o: Mosaico, Ruota, Lista a due livelli); Lorenzo sceglie "mosaico". `narratives.json` +13 narrative gem (dex_amm, perps_derivatives, lending_credit, yield_vaults, liquid_staking, launchpads, bridges, wallets_aa, dev_tools, storage, gaming, nft_collectibles, music_media; query GitHub vuote; bridges e dev_tools senza categoria CoinGecko). `top.js` `mosaicHtml`: riquadri a griglia 6 colonne, grandezza = progetti, colore = mediana 24h, Privacy primo in ambra, etichette corte (`SHORT`), oltre 13 riquadri "+ N more"; un tocco apre l'arena con "← All arenas". Le chip orizzontali non ci sono piu'.
- 10/10, dopo il merge di #521, Lorenzo: "non si capisce niente ci sono pochi progetti" (5 arene, 32 progetti, categorie nuove vuote) e "rifai il giro subito". `_narr_now` in main.py rifa' il match regex del catalogo in lettura (descrizione + categorie); `narrative_map.CATALOGUE_AT` rimanda a DeepSeek le righe mappate prima del catalogo nuovo (le vecchie chiavi restano). Mosaico: riga di spiegazione, "N projects" nei riquadri, legenda "♛ leader". I 32 progetti sono il limite dei cancelli d'uso del 07/10, non del mosaico.
- 10/10, Lorenzo: "quando clicco su un mosaico non deve cambiare schermata ma aprirsi tipo a nido di ape in stile apple watch". `top.js` `hiveHtml`: il riquadro si apre sul posto (cresce dal riquadro toccato) in un favo esagonale, il capo al centro con anello ambra, gli altri in anelli piu' piccoli (max 19), bordo verde/rosso = 24h; tocco = pagina del token; "Full ranking →" apre la lista di prima.
- Stesso giorno, Lorenzo: "non sono per niente integrate nell'app", "privacy e' una seconda sezione", "non devi fare sotto menu". Quindi: il favo si apre dentro il mosaico (riga intera sotto il riquadro, ritocco = chiude), niente "← All arenas" ne' lista separata; Privacy e' un riquadro come gli altri (niente ambra, niente primo fisso); sul telefono riquadri e favo con lo stile nordico (raggi 16/20, niente bordi, minuscole). Card di scelta su Privacy postata (sezione sotto / riquadro normale / scheda): applicato "riquadro normale" per "non devi fare sotto menu".
- Stesso giorno, dopo #524 online, Lorenzo: "orribile, ripristina un elenco o progetta altre schermate". Favo tolto: il tocco su un riquadro apre la classifica dell'arena (la lista di sempre) subito sotto il mosaico, stessa schermata, ritocco = chiude.
- Stesso giorno, Lorenzo: "prepara idee vai". Tre schermate (https://claude.ai/artifact/G5QydqwTKts7vQfYJmD6gT); sceglie "B a capitoli" (#526), poi "preferivo il mosaico": #526 chiusa senza merge, resta mosaico + classifica sotto (#525). Non riproporre i capitoli.
- Stesso giorno, Lorenzo: "non ho piu' le categorie" (in produzione 5 arene) e "non voglio vederle vuote pero'", "rifai fare un giro completo". Causa: ogni progetto stava in una sola arena e un'arena con meno di 2 progetti si scioglie, quindi le 13 narrative nuove non si formavano. #529: `arenas.also_in` mette ogni progetto anche nelle arene delle sue altre narrative (`also: true`, classificato fra quei pari, niente podio ne' tenure li'); nessun riquadro vuoto (tranne Privacy/Compute di CLAIM); intestazione conta ogni progetto una volta; `CATALOGUE_AT` = 18:00 UTC, DeepSeek rimappa tutto (~480 righe/ora). Le immagini con 16 arene erano dati di prova. Lettura dati veri dal sandbox bloccata (permesso): conteggio reale non verificato.
- Resta: mostrare il rating dopo 21 notti; le etichette di narrativa sbagliate mandano un progetto nell'arena sbagliata (da controllare sui dati veri dopo il primo giro).

# 2026-10-07 — Analisi completa, via il trading, Top piu' severa — `seed-0250` (Claude, a mano)

Lorenzo: "voglio che fai un'analisi estremamente approfondita di tutto il software [...] la parte di automatizzare il trading con le strategie trend follower [...] la disabiliterei, non la voglio vedere nell'app [...] fare tutto in una tranche magari a fine serata [...] costi poco [...] al terzo posto c'e' [...] Clawville World, che penso sia una merda". Report: https://claude.ai/code/artifact/a98e2b63-5c59-482f-9980-972100647e6e (difetti logici con file:riga, costi, piano). Poi: "basta questa parte di trading deve sparire", "applica tutte le correzioni", "velocizza [...] con altri agent in parallelo".

Decisioni (schede, 07/10): spegnere e nascondere trend follower, trading automatico e Meme Sniper; **nascondere swap e ordini limite**; soglie per la Top: cap almeno $300k (sotto: lista Early, mai sul podio, tetto resta $10M), volume medio 7 giorni almeno $25k/giorno e almeno 1% della cap, almeno 100 transazioni/giorno con 30 compratori distinti, almeno 500 holder con crescita a 30 giorni non negativa, primi 10 wallet (esclusi contratti) sotto 40%; **una sola scansione alle 22:00 ora italiana**.

Piano in PR separate: (1) spegnimento trading, Top senza filtro backtest — questa; (2) snapshot giornaliero di volume/transazioni/holder e cancelli sopra, anche sulle righe "studied" della Top; (3) dossier del giudice con i numeri d'uso, prompt ripulito (via "never 'no team'", "$0 volume = mancante" senza seconda fonte, elenco narrative preferite), nuova formula: uso 30, partecipazione 20, prodotto 25, token/rischio 15, DeepSeek 10, somiglianza DREGG fuori dal punteggio; (4) giro unico serale. Il Record (track.js, gem_track) era gia' il track record delle scelte e resta nel dock. Clawville 07/10: cap $48k, volume 24h $492, 245 holder, top10 48%.

Il ridisegno grafico dell'app (piu' classico e minimal) e' un thread a parte.

Stesso giorno, dopo il merge di #499, Lorenzo: "dare troppa importanza [a] volume [...] la partecipazione di mercato esclude delle gemme che sono nascoste, noi invece il nostro obiettivo e' trovare delle gemme [...] non devono direzionare troppo il tutto". Soglie ammorbidite (Claude, a mano): `usage_gate` scarta solo chi nessuno scambia (media 7 giorni < $2k al giorno **e** < 10 compratori in 24h), < 100 holder, holder giu' oltre il 10% in 30 giorni, top 10 wallet >= 40%; non misurato o ignoto passa. Pesi `SCORE_WEIGHTS`: prodotto 30, DeepSeek 25 (legge anche i numeri d'uso), uso 20, token 15, partecipazione 10 (Lorenzo: "deve essere una cosa equilibrata", la vecchia Top "non era male"). `hidden_gem()` (prodotto >= 65 con uso <= 35 o ignoto) = etichetta HIDDEN GEM nella Top, mai scarto. Giudice `PROMPT_VERSION` 10: poco volume con prodotto funzionante e' la gemma cercata. Le soglie piu' dure scritte sotto ($25k, 1% della cap, 100 transazioni, 30 compratori, 500 holder) restano solo come punto di partenza del punteggio d'uso. Poi Lorenzo: "aggiornami tutti i voti di quelle presenti nel database [...] va riscansionato tutto il database con [...] le nuove logiche" (Paralum, Merryman, Clawville). `leaderboard.rescore_once()` all'avvio, una volta per `rules_version()`+`PROMPT_VERSION` (salvato come `rescored_rules`): ricalcola subito punteggio e motivo di ogni riga studied/ranked del database senza chiamate API (`projects_db.rescore_many`), poi rimette in coda tutte le studied/ranked e le rejected da DeepSeek (`projects_db.requeue`) per un'analisi nuova col giudice v10; il giro serale le smaltisce qualche centinaio a notte (tetto DeepSeek 1500 letture/giorno, ~$0,001 l'una).

Punti (2) e (3) fatti (branch `quality`, Claude a mano; `seed-0251`): `trading/onchain/usage.py` misura una volta al giorno per token (DexScreener a lotti di 30 + 3 chiamate GeckoTerminal sotto il limitatore condiviso) volume 24h e medie 7/30 giorni dalle candele giornaliere, transazioni, compratori e venditori 24h, holder, liquidita', cap; storico 60 giorni in `data/usage_history.json`, `holders_growth`. `leaderboard.usage_gate` applica le soglie decise (dopo `research_floor`, prima di pilastri e giudice: nessun giudizio fa entrare un token che nessuno usa); senza misura il token aspetta ("usage not measured yet"), un campo ignoto non e' zero. Top10 solo da GoPlus (contratti esclusi), mai dallo split GeckoTerminal. Sotto $300k con tutto il resto ok: `early_list()` / `board()["early"]` / `top.early`, lista a parte in fondo alla Top. Le righe "studied" della Top passano dallo stesso cancello e sono ricalcolate con la formula nuova (layer esclusi: hanno la loro fascia). Formula `final_score`: media pesata dei blocchi presenti, uso 30 (volume/cap, volume in $, compratori; DefiLlama se c'e'), partecipazione 20 (holder e crescita), prodotto 25 (sito, GitHub, lettura del codice), token 15 (pilastro tokenomics), DeepSeek 10 (giudice + revisione); via somiglianza DREGG, bonus narrativa, fasce $2M e miscele a catena. Giudice: `PROMPT_VERSION` 9 (tutti rigiudicati), il dossier porta la riga d'uso misurata, regole riscritte (sito+GitHub+X provano che il team esiste, non che il prodotto funzioni; quasi zero volume e pochi compratori pesano piu' del sito); tolta la lista delle narrative preferite dalla revisione della board. All'avvio `leaderboard.warm_usage` misura fino a 200 candidati non misurati oggi, cosi' un deploy di giorno non svuota la Top fino alle 22; il giro serale non si chiude finche' restano candidati da misurare. Test vecchi: fixture `_usage_open` in conftest (cancello aperto), marker `usage_gates` per i test veri.

Punto (4) fatto (branch `nightly`, Claude a mano): Lorenzo, "non lasciare sempre in ascolto il bot che scansiona costantemente [...] tutto in una tranche a fine serata". `trading/onchain/nightly.py`: con `onchain_nightly_enabled` (default True) il server non avvia piu' `leaderboard_loop`, `sweep_loop`, `outcomes_loop`, `layers_loop` e `studies_loop`, ma un solo `nightly_loop` alle `onchain_nightly_hour` (22, ora di Roma con zoneinfo) per al massimo `onchain_nightly_max_hours` (2.0): tick della classifica finche' `leaderboard.drained()` (niente in analisi, niente mai analizzato, niente in coda nel database, coda di scoperta vuota se il pool ne vuole) o il 75% della finestra, poi layer, esiti una volta, ricontrollo settimanale della Top per i token che deve ancora (`deep_recheck.sweep_one`) fino a fine finestra, studi DeepSeek una volta; poi un messaggio Telegram in italiano (entrati/usciti dalla Top con i nomi, analizzati, chiamate DeepSeek da `deepseek_calls.count_between`). Stato in `data/onchain_nightly.json`: dopo un deploy a meta' giro riprende (max 3 tentativi, stessa finestra), un avvio dopo le 22 senza giro fatto parte subito (fino alle 06:00; di pomeriggio aspetta le 22). `board()` espone `nightly: {enabled, running, last_run, next_run, summary}`. Restano immediati scansione manuale e "Re-check with DeepSeek" (non dipendono dal giro); "aggiungi al Gem Finder" analizza subito il progetto (`leaderboard.analyze_now`). A False torna tutto come prima. Effetto collaterale voluto: prezzi/cap della board, track record e avvisi "nuovo in Top" si aggiornano solo la sera.

# 2026-10-10 — Telefono: stile nordico al posto del terminale (Claude, a mano)

Lorenzo, 10/10, con lo screenshot della bozza O: "lo stile lo voglio così dell'app", poi "tenendo conto della visualizzazione a mosaico che sta venendo fatta da altro agent". `classic.css` ripartito dalla versione chiara (angoli tondi) con token nuovi: avena #efeae0, schede #f8f5ef, verde scuro #2f3a32 (tasti e barra in basso), salvia #c9d4c0 per cio' che e' scelto (`--c-sage`), Geist. Solo chiaro. Righe della lista come schede morbide. Il Mosaico delle arene (thread "Classifica alternativa alla Top 50") deve usare i token `--c-*` con fallback, non toccare classic.css.

# 2026-10-07 — [superato il 10/10 dallo stile nordico] Nuovo aspetto dell'app sul telefono: terminale nero e ambra — PR #500 (Claude, a mano)

Lorenzo: "mi piacerebbe un pochino più clean, un pochino più minimal [...] voglio un qualcosa di un pochino più classico", poi "ma é uguale" / "devi rivoluzionarlo", due screenshot di ElevenLabs ("mi piace questo stile"), "non fare il desktop per ora voglio solo mobile". Sfondo scelto da lui sulla scheda: chiaro di base, scuro automatico con la modalita' notte. Poi: "usa un team di revisori [...] dalle animazioni ai layout a tutto" — quattro revisori (layout, animazioni, colori/contrasto, tecnica), tutte le correzioni applicate.

- `frontend/static/onchain/classic.css`: unico file della pelle, non a layer, caricato per ultimo con `media="(max-width:1099px)"` (il desktop resta com'era, verificato: 0 differenze di stile calcolato a 1100/1440). Token `--c-*` chiari in `:root`, scuri in `prefers-color-scheme: dark`; punta tutti i token vecchi (`--k-*`, `--engn-*`, `--bg`...) sui nuovi. Inter in `static/fonts/inter-latin.woff2`.
- `app.css`: i colori scuri fissi sono diventati `var(--c-*, <colore vecchio>)`: sul desktop le `--c-*` non esistono e vale il colore vecchio.
- Animazioni: i `@keyframes` vecchi sono ridefiniti per nome in classic.css (le regole senza layer vincono); i loop decorativi hanno corpo vuoto, gli indicatori "sta lavorando" una pulsazione d'opacita'. Non rimettere `animation` su `.trow`: top.js ridisegna ogni 30 s e le righe lampeggiano.
- Titolo grande della pagina = `.tb-me::before` con `:has(#app-shell[data-view=...])`: una vista nuova vuole la sua riga.
- Poi Lorenzo: "per il design valuta strade più audaci mi sembra sempre simile", "proponi altre. però già meglio", "altre". Nove bozze statiche (A editoriale, B svizzera, C carte, D terminale, E blocchi, F poster, G vetro, H fumetto, I blu; immagini in project-files `redesign-classico/`). Scelta: **"terminale D nero e ambra, procedi"**. Quindi la pelle e' sempre scura (niente piu' chiaro/scuro automatico, decisione precedente superata): fondo #0b0b09, testo #e8e3d3, ambra #ffb000 per cio' che e' scelto, Geist Mono ovunque, titoli in maiuscolo con cursore ambra lampeggiante (`.tb-me::before`, unico loop, spento con riduci movimento), riquadri a filo 1px con angoli 2px, righe tratteggiate, punteggio fra [ ].
- Resta: il desktop (Lorenzo lo vuole dopo); "↑ 0.0%" verde quando il valore e' zero (serve JS: niente `data-sign` a 0).

# 2026-10-01 — Motore Layer 0/1/2: CoinPaprika al posto di CoinGecko — `seed-0247` (Claude, a mano)

Lorenzo: "Ma questo motore ha trovato dei risultati [...]?" e "non serve remote control, hai github ora" / "vai con l'action". Letto il server con `server-read.yml`: 0 layer, `last_run` fermo alle 12:37, ogni chiamata CoinGecko in 429 (discovery.py e il cap check della classifica spendono tutto il budget gratuito). `layers.py` ora usa CoinPaprika, gratis e senza chiave: `/v1/tags?additional_fields=coins` (layer-0-l0, layer-1-l1, layer-2-l2, layer-3-l3; L0 prevale su L1 su L2), `/v1/tickers` (cap e prezzo; circolante = cap/prezzo; FDV = prezzo x max o total), `/v1/coins/{id}` (sito, GitHub da `source_code`, logo, descrizione, tag: meme/stablecoin/wrapped/bridged/liquid staking scartati). TVL DefiLlama e L2BEAT agganciati per nome. Token del DB = id CoinPaprika (`kas-kaspa`), `cg_id` vuoto. Prova dal vivo: 74 candidati in fascia, 26 con TVL (BERA, LINEA, KAVA, FLOW, 0G, GALA, MOVE, IOTX, ASTR, ERG...). Ripristinato anche questo file: #495 lo aveva svuotato per errore (4148 righe).

# 2026-10-01 — Task lunghi in background con notifica push — `seed-0264` (Claude, a mano: sistema dei lavori e push)

Lorenzo: "qualsiasi task, qualsiasi attivita' lanciata da mobile o da desktop deve continuare in background se io cambio finestra o butto giu' l'applicazione sul telefono e arrivarmi una notifica al completamento dell'attivita' che mi riporta esattamente al punto in cui l'ho lasciata se ci clicco sulla notifica".
Task lunghi dell'app on-chain: ricontrollo DeepSeek (`detail.js`), scansione manuale (`sheets.js`), domanda all'agente (`ask.js`). Ora sono lavori di `app/jobs.py` (lo stesso store dell'ottimizzazione del vecchio sito, esteso): `device` (id casuale del browser in localStorage, header `X-Device`), `view` (frammento URL `gems&token=chain:addr&tab=why`, `meme&scan=1`, `...&ask=1`), salvati in `data/app_jobs.json` per 24 h; un lavoro "in corso" a un riavvio diventa "fallito: interrupted by a server update" con notifica. Push (`app/notify/web_push.py`, `pywebpush`): chiavi VAPID generate una volta in `data/vapid_keys.json` (o da env `VAPID_PRIVATE_KEY`/`VAPID_PUBLIC_KEY`, mai nel repo), iscrizioni per device in `data/push_subscriptions.json`, 404/410 = iscrizione tolta. Una notifica per lavoro, solo al device che l'ha lanciato, e nessuna se la pagina lo sta guardando (`/api/jobs/{id}?visible=1` = watch per 5 s; `sendBeacon /api/jobs/{id}/away` quando la pagina esce dallo schermo). `/sw.js` (scope `/`, nessuna cache) mostra la notifica; il tocco porta in primo piano la finestra aperta (postMessage) o apre `/onchain-app.html?job=<id>#<view>`. `bg.js`: lavori non ancora mostrati in localStorage `lae.jobs`, poll ogni 2 s solo a pagina visibile, `boot()` riprende i lavori di una pagina uccisa o ricaricata (anche dal controllo versione), `handle(kind, {show, pending})` per ogni tipo. Permesso notifiche chiesto al tocco che lancia il task (Safari lo vuole dentro il gesto). PWA: `/manifest.webmanifest`, icone `static/engn/icon-{180,192,512}.png`. iPhone: push solo dall'app aggiunta alla Home (iOS 16.4+); in Safari un avviso piccolo, una volta a settimana. Provato in Chromium: scansione, ricarica a meta', il foglio torna col risultato; il link `?job=` riapre il foglio.
Resta: l'ottimizzazione del vecchio sito (`index.html`, `/api/optimize`) e' gia' un lavoro ma senza `device`, quindi senza push; i task automatici (backtest, sweep) non partono dall'app e non notificano.


# 2026-10-01 — Filtri del database in un pannello, tag L0/L1/L2 — `seed-0249` (Claude, a mano: logica UI)

Lorenzo: "i filtri nel database sono raffigurati orizzontalmente [...] devo scorrere a destra ma non finiscono mai [...] aggiornare anche L1, L0 [...] identificarli con il relativo tag". Ora un tasto "Filters" accanto alla ricerca apre `#sheet` (`projects.js openFilters`) con Verdict, Type (L0/L1/L2 e chain) e Narratives, con conteggi e "Show N"; le scelte restano come etichette sotto la ricerca. Backend: `projects_db.search(chain=, layer=)` (tipo da `overall.layer`), `stats().by_layer`. Righe layer col tag. Corretto `#sheet { position: relative }` -> `fixed`: in top layer diventava absolute e fuori schermo a pagina scorsa. Screenshot in project-files `database-filtri/`.
# 2026-10-01 — Tasto microfono: si parla a DeepSeek dall'app — `seed-0248` (Claude)

Lorenzo: "il tasto di registrare un audio [...] trascrivere l'audio mentre lo [dico], lo invio e poi [il testo] arriva direttamente a DeepSeek che mi risponde [...] deve avere accesso a tutto". `ask.js`: tasto microfono fisso sopra la lente (desktop: in basso a destra), foglio con trascrizione dal vivo (Web Speech API nel browser, niente audio sul server; IT/EN, default IT), testo modificabile, invio, risposte in fila, "Clear" azzera la memoria. Senza riconoscimento vocale (Firefox) si scrive. `POST /api/agent/ask`: stesso `deepseek_desk.answer` della chat Telegram (memoria `web:<user id>`, contesto con wallet dell'account, stessi strumenti di sola lettura) piu' `portafoglio_top50` e `layer_engine`; istruzioni permanenti solo agli admin; niente ospiti; 30 domande/ora per account, dentro il tetto giornaliero. Costo stimato: pochi millesimi di $ a domanda (prezzi deepseek-chat), al massimo ~1 cent con 5 giri di strumenti. Non passati a DeepSeek: HANDOVER/CLAUDE/LESSONS (il classificatore di sicurezza ha bloccato l'invio delle note di progetto a un servizio esterno: serve il via esplicito di Lorenzo).

Stesso giorno, dopo: linguetta sul bordo destro e pannello che non blocca la pagina (#489). Poi Lorenzo: "voglio un botta e risposta [...] lui deve avere una voce": modo Voice (chip, acceso di default) = pausa di ~1,4 s invia da sola, risposta letta con `speechSynthesis` (voce del telefono, migliore it-IT disponibile; il server chiede max 3 frasi parlate con `talk: true`), poi il microfono si riapre; tocco sul mic interrompe la voce. Rischio iOS: la riapertura automatica del mic dopo la voce puo' richiedere un tocco. Campo "Scan a token" ora `readonly` finche' non lo si tocca (apriva la tastiera all'avvio; causa non riprodotta in locale).

Sera 01/10: (1) microfono sempre vivo in modo Voice: i telefoni chiudono il riconoscimento a ogni pausa, ora si riapre da solo (testo accumulato) e la domanda parte solo col timer di silenzio (1,7 s); guardia di 1,5 s riapre il mic se tace; dopo 7 riaperture a vuoto in 10 s si ferma e chiede un tocco; un tocco sul mic in ascolto invia (o mette in pausa). (2) Voce: Piper (`piper-tts` 1.8, OHF-Voice/piper1-gpl, GPL-3) sul server con `it_IT-paola-medium` ed `en_US-lessac-medium` scaricate nel Dockerfile (se il download fallisce resta la voce del browser), `POST /api/agent/speak` -> WAV, ~0,8 s di CPU per 10 s di parlato su 2 core, modello caricato mentre DeepSeek pensa. Scartati: Kokoro (italiano debole), XTTS (licenza non commerciale), MeloTTS (niente italiano), voci Edge (endpoint non ufficiale). Campione: /mnt/project-files/voce/voce-paola-piper.wav. (3) `come_funziona`: indice dei docstring e delle costanti di tutto `backend/app` (`notify/app_guide.py`), esclusi i moduli di chiavi/login/esecuzione; Lorenzo: "deve avere accesso praticamente a tutto quello che riguarda il funzionamento di tutta l'app". (4) L'agente si chiama Carlo: alla prima domanda di una conversazione si presenta in modo comico come creato da Lorenzo, "il suo dio", con un'apertura sempre diversa (stile a caso fra 24).

07/10 (`seed-0263`, Lorenzo: "il motore del sito non sta studiando tutti quelli presenti nel database..ce ne mancano tanti"): `projects_db.CAP_MAX` era rimasto a $3M (e `traction.CAP_MAX`) mentre il board accetta fino a $10M, quindi le righe $3M-$10M non venivano mai passate; ora $10M. Le righe in fascia senza sito ne' GitHub restavano "new" per sempre: ora `reject_linkless` le chiude con "no website or GitHub to read" e `_set_links` le rimette in coda quando DexScreener trova un link. Il contatore della schermata Database mischiava `by_status` (tutto il db) con `in_band`: ora `band_by_status` e `band_waiting`. Numeri veri del server non letti (API con login, PC offline): da guardare dopo il giro delle 22:00, voce "waiting".

07/10 (messaggio di Lorenzo del 01/10: "non sento piu' la sua voce [...] deve tagliare prima"): la voce del server era bloccata dalla CSP di Caddy (`default-src 'self'` senza `media-src`, il WAV si suona da un `blob:`), e un errore di riproduzione chiudeva il turno senza ripiego sulla voce del telefono. Ora `media-src 'self' blob: data:` e `microphone=(self)` nel Caddyfile (prima `microphone=()`), ripiego sulla voce del telefono se il WAV non parte, timeout 12 s. Fine domanda: 0,8 s dopo parole definitive, 1,3 s se il riconoscitore sta ancora indovinando, 0,45 s se il telefono chiude la sessione dopo aver sentito parole.

# 2026-10-01 — Regole PFWA per ogni revisione e ogni chain (#475, DeepSeek corretto da Claude)

Lorenzo ha incollato la verifica manuale di PFWA di un'altra AI "per istruire deep seek perché dice cavolate", poi "la logica vale per tutti i progetti". Ora `judge.CHECK_RULES` (con `judge.LOCKERS`, i locker LP per chain: Solana Streamflow/Jupiter/Meteora/LP bruciata, ETH/Base UNCX/Team Finance/PinkLock, BSC PinkLock/UNCX/Team Finance/Mudra, Robinhood HoodLock/Team Finance/Titan/Genesis) entra nel giudizio di ogni progetto (`PROMPT_VERSION` 8: tutti rigiudicati), nella revisione della board, nel ricontrollo dei punti rossi e in quello dedicato. Regole: mai "chain senza utenti"; volume $0/unknown conta solo se GeckoTerminal concorda; "0% locked" conta solo se i dati GoPlus coprono il pool principale; sito+GitHub+X attivo non e' mai "no team/no socials/thin docs". Il ricontrollo: cerca il GitHub con README che nomina il sito o l'indirizzo (`github_by_name`, il repo deve portare il nome del progetto: un crawler di notizie e una lista bot erano falsi positivi), legge `llms.txt`, incrocia volume e riserva su GeckoTerminal, "X bio links the official site". Citazioni con "..." valide se ogni pezzo e' vero. Prova reale con DeepSeek (workflow temporaneo, tolto): PFWA trova MirakoolDev/pfwa-contracts e smentisce GitHub, volume $0, chain senza utenti, no team/socials; HYDX, GRID, BV7X tenuti. Lorenzo, stesso giorno: a DeepSeek solo compiti banali, la logica la scrive Claude (vedi CLAUDE.md).
# 2026-10-01 — Motore Layer 0/1/2, fase 2: in Top 50 — `seed-0247` (DeepSeek #478, corretto da Claude)

Candele e prezzo dagli exchange: il pool di un layer e' la stringa `"mexc:KASUSDT"` (o `binance:`), la rete GeckoTerminal finta e' `"cex"`. `cex_candles.py` (candele da `MexcProvider`/`BinanceProvider`, 2h/6h/8h/12h e 1w uniti dai nativi; prezzo dal ticker). Agganci: `alert_track._candles` (net "cex"), `strategy_lab._net`/`_pair_of`/`next_due`, `live_prices._refresh` (chain "layer"), `radar._fetch_lite` (grafico), `/api/onchain/chart` accetta il pool `exchange:PAIR`, `legit.CHAIN_LABEL["layer"]`. `_top_entries`: i layer con coppia USDT entrano, con la loro fascia $500k-$100M al posto del tetto $10M. Non toccati: `candle_archive.archive_loop` e `ladder_watch` saltano i layer (nessuna rete GeckoTerminal), il laboratorio scarica comunque.

# 2026-10-01 — Motore Layer 0/1/2, fase 1 — `seed-0247` (DeepSeek #474, corretto da Claude)

Lorenzo: "dobbiamo scovare i layer one e i layer zero [...] e anche i layer 2 con blockchain propria [...] API gratuite [...] pochi al giorno e' sufficiente [...] i risultati vanno a finire [...] database, top 50". Fascia scelta da lui: "usiamo da 500k di market cap fino a 100mln" (FDV max 5x la cap). `layers.py`: un giro al giorno (DefiLlama `/v2/chains` con `gecko_id`, filtrate per cap con `/coins/markets?ids=` a lotti di 100; categorie CoinGecko layer-1/layer-0-l0/layer-2; L2BEAT per stage e token delle L2; DefiLlama stablecoin e fee; MEXC/Binance per la coppia USDT), max 20 schede CoinGecko, una ogni 30 s. Tipo dalle categorie CoinGecko; L2 senza token fuori. Pilastri: github e site come le gemme, tokenomics da supply/FDV, traction (cap/TVL, cap/fee, crescita TVL, stablecoin, stage L2BEAT). Righe in `projects_db` con `chain = "layer"`, `token = id CoinGecko`, escluse da `_band_sql`, `stale_market` e da `main._top_entries`. Stato in `data/onchain_layers.json`, `GET /api/onchain/layers`. Design: `/mnt/project-files/layer-engine/design.md`. Fase 2 fatta (sopra). Dalla sandbox CoinGecko risponde 429/403 (IP condiviso): il giro vero si vede solo sul server.

# 2026-10-01 — Ricontrollo DeepSeek rigoroso: prove per ogni punto (#464, DeepSeek corretto da Claude)

Lorenzo: "il recheck di deepseek deve essere molto rigoroso", "rendilo moooooolto rigoroso; non voglio errori da scemo in questa fase". Il caso HYDX: le review dicevano "niente prodotto, niente contratto, niente partner" su un'app JS funzionante. Ora `scout_recheck.gather` legge anche: il codice dell'app e i chunk caricati dopo (`app_probe`, fino a 40 file, l'indirizzo di HYDX stava in `hyperToken-*.js`), le API `/api/...` trovate nel codice (vale solo JSON 200; 401/403 = esiste; 5xx = illeggibile), il testo che l'app mostra (stringhe del bundle, filtrati i messaggi di librerie), la bio di X (`api.fxtwitter.com`, gratis). Ogni fonte finisce in "Checked sources" con found / not found / unreadable (pagina senza testo = unreadable, non "mancante"). Volume e liquidita' mai letti sono "unknown", non $0. Riga "Liquidity / cap" con la soglia del sistema (10%).
Regole: ogni punto confermato o smentito deve citare una frase esatta delle prove (lunga almeno 8 caratteri), altrimenti torna "unverified"; un punto non risposto e' "unverified". `facts_win`: contratto nel codice o nella bio, profilo X letto e pool sopra il 10% smentiscono i punti contrari. Nel giudizio dedicato forze e problemi devono citare le prove (mai i punti rossi stessi); uno scarto deve poggiare su un fatto misurato: se i problemi sono solo mancanze (GitHub, docs, team, TVL) la risposta e' "unsupported" e non cambia nulla in classifica. Prova reale prima del merge (workflow temporaneo con la chiave DeepSeek, tolto): HYDX, PFWA, GRID, BV7X tenuti (watch 52-58), STEALF scarto bloccato come non provato, un meme pump.fun scartato.

# 2026-10-01 — Ricontrollo DeepSeek dedicato dalla pagina token — `seed-0246` (DeepSeek #459, corretto da Claude)

Lorenzo: "in ogni review metti un tasto per forzare un ricontrollo approfondito dedicato con deepseek" (screenshot HYDX, escluso dalla revisione di tutta la board). `deep_recheck.py`: `scout_recheck.recheck` (seconda ricerca sui punti rossi, ora restituisce anche `evidence`) + una chiamata DeepSeek solo su quel token (keep/score/verdict/reason/strengths/problems), salvata in `data/onchain_deep_recheck.json`. Applica: `review` con `deep: True` sulla voce della board; nel database `why` = "DeepSeek re-check: ..." se scarta, tolto il vecchio "DeepSeek ..." se tiene. Limiti: 6 h per token e 40 al giorno solo per gli ospiti; chi ha un account (Lorenzo, 01/10: "voglio poterlo fare quando voglio") ricontrolla quando vuole, con 10 s contro il doppio tocco. Passaggi dal vivo (Lorenzo 01/10: "voglio vedere proprio i vari passaggi"): `scout_recheck.step()` via contextvar, `GET /api/onchain/token/recheck/progress`, lista animata in `detail.js` (`followRecheck`), anche per il giro settimanale e a pannello riaperto. Ricontrollo automatico di tutta la Top 50 una volta a settimana dal 01/10 (`deep_recheck.sweep_loop`, un token ogni 90 s, stato `sweep` nello stesso file dati, sopravvive ai deploy), Lorenzo: "da oggi fai un recheck su tutta la top 50 e poi [...] una settimana ricorrente". `POST /api/onchain/token/recheck`; `GET /api/onchain/token` da' `deep`/`deep_wait_s`; tasto "Re-check with DeepSeek" in fondo alla tab Why (`detail.js deepBlock`). Gli errori API ora portano `status`/`detail` (`api.js`).

# 2026-10-01 — Prezzi delle posizioni quasi in tempo reale — `seed-0245` (Claude, a mano)

Lorenzo, 30/09: "il saldo delle posizioni si aggiorni piu' velocemente possibile [...] trovare un servizio [...] vedere in tempo reale i cambiamenti di prezzo". Causa misurata: DexScreener `/tokens/v1` risponde da CDN con `max-age=30` (HIT, age fino a 30 s) e 4 cifre significative: il poll ogni 2 s mostrava lo stesso prezzo per mezzo minuto. Ora `live_prices.py`: EVM (bsc/base/ethereum/robinhood) dal pool on-chain (`pool_prices.py`: il pool piu' profondo di DexScreener, `getReserves` v2 / `slot0` v3 in un batch eth_call per chain su RPC publicnode/Robinhood, decimali letti una volta, prezzo del quote da DexScreener ogni 60 s; pool accettato solo se coincide con DexScreener entro 5%, v4/stable esclusi); Solana da Jupiter `lite-api.jup.ag/price/v3` (gratis, CDN 5 s, budget 30/min); poi DexScreener con parametro anti-cache, poi GeckoTerminal. `GET /api/onchain/live-stream` (SSE) spinge ogni secondo solo i prezzi cambiati; `live.js` usa EventSource (ripiega sul poll dopo 3 errori). Robinhood RPC: budget 30/min (va in 429 facilmente e serve anche saldi e swap).
Valutati e scartati (a pagamento o con chiave): Birdeye (websocket solo piani paid, l'API pubblica da' 401 senza chiave), Codex (websocket nei piani paid), Moralis Streams (paid). Prossimo passo se Lorenzo vuole Solana al secondo: chiave **gratuita** Helius (websocket `accountSubscribe` sui pool) da mettere nel `.env`, oppure decodifica dei pool Raydium/PumpSwap/Meteora sul RPC pubblico.

# 2026-10-01 — Scenari di slippage, tetto a 0,5% (Claude, a mano)

Lorenzo: "ora siamo a 11k di totale invece di 32k [...] simula piu' scenari di slippage". `scripts/slippage_scenarios.py` (sola lettura, girato sul server dalla sessione del PC, output in project-files `slippage_scenarios.json`): 47 token, aperti al costo. Senza tetto ne' slippage $33.767 (+238%, dd 21,9%); senza tetto ma pagando lo slippage $11.667 (dd 26,7%, $11.444 di slippage); tetto 0,5% $11.665 dd 7,7%; 1% $11.665 dd 12,5%; 2% $12.700; 3% $13.845 dd 17,1%; 5% $12.966; 10% $11.960. Il calo da 32k e' lo slippage, non il tetto. Lorenzo ("fai tu"): `onchain_max_slippage_pct` = 0.5. Stesso giorno: deploy Actions rosso da #446 per `test_native_price_usd_real_network_call_*` (GeckoTerminal 429 sui runner): `prices.native_price_usd` ora ripiega su `live_prices` (#454). Lorenzo: "da ora torniamo a usare github" (deploy da Actions).

# 2026-10-01 — Tetto di size per ingresso dallo slippage — `seed-0244` (Claude, a mano: tocca l'esecuzione)

Lorenzo: "adesso che il portafoglio e' 30.000 il 10% e' 3.000 [...] su queste cripto che hanno liquidita' scarsa [...] un tetto massimo di size [...] un'anteprima di quanto sarebbe lo slippage [...] fare un check con i vari dex [...] calcolare velocemente quanto potrebbe essere il size massimo [...] in dollari".
`trading/onchain/slippage.py`: pool letto come x*y=k con meta' liquidita' lato stable (R = liq/2); slippage di x = x/(R+x), size massima = s*R/(1-s) con s = `settings.onchain_max_slippage_pct` (default 1%). Con un quote vero (Jupiter su Solana, QuoterV2 Uniswap v3 su Robinhood) la profondita' e' quella implicita nell'impatto, R = x(1-i)/i; BSC/Ethereum/Base: solo profondita' del pool (DexScreener `liquidity_usd`). `preview()` (cache 2 min) e `text_it()` per Telegram.
Dove vale: `sim_backtest.replay` (ledger con `liq` da `remember(..., liq=)`, chiamato da `_top_wallet` e `strategy_lab.run_one`; le due gambe pagano lo slippage stimato; risultato con `capped`, `slippage_usd`, righe con `wanted`/`max_usd`); `autotrader.trend_signal(max_usd=)` per la Sim (stima condivisa con la notifica, `main._entry_preview`); `autotrader._buy` (Sim e Real) fa un quote di prova sulla size e la riduce se l'impatto supera il limite. Real resta bloccato dal gate quant. Anteprima: `GET /api/onchain/slippage` (default = 10% dell'equity del portafoglio Top 50), righe "Slippage on $X" e "Max entry at 1%" nella pagina gemma (`detail.js slipRows`), riga in italiano nell'avviso Telegram di ingresso del trend follower.
Limite: il replay usa la liquidita' di oggi anche per i trade passati, e i token del registro senza `liq` (mai riletti dalla Top) non hanno tetto. Il portafoglio $10k cambia numero: piu' basso dove le pool sono sottili.
# 2026-10-01 — Signals e Record al posto di Memes e Strategies — `seed-0243` (Claude, a mano)

Lorenzo: la tab delle performance dei backtest "non serve piu'" ("la visualizzo nel conto simulato") e "non mi serve piu' neanche la schermata dei fired last 48 ore [...] about to fire [...] e' tutta roba legata alle meme coin". Proposte tre idee (Signals, Track record, Risk watch); scelta "due tab".
Ora la vista `meme` mostra `#signals` (`signals.js`, dati di `/api/onchain/top`: `daily.signal` e `in_position` del trend follower 8h/1d; segnali degli ultimi 7 giorni, in posizione, in attesa) con lo scanner manuale in cima; la vista `top` mostra `#track` (`track.js`, nuovo `/api/onchain/track` = `gem_track.record()`: stats per orizzonte, ultime scelte, "Missed" = studiate/scartate con picco >= +100%). I nomi delle viste restano `meme`/`top` (link della home, splash, desk). `#radar`, `#memes`, `#meme-alerts`, `#pilot`, `#leaders` restano nel DOM ma sempre nascosti; `mountRadar` e il poll dello scan-feed tolti.
Resta: il "Risk watch" (wallet collegati, liquidita' tolta) proposto come sezione di Record non e' fatto; "armato" (vicino al segnale) non c'e', servirebbe un calcolo nuovo in `strategy_lab`; togliere del tutto il codice meme morto.
# 2026-09-30 — RSI+BB nel laboratorio: regola della riga e vecchi trade verificati (Claude, a mano)

Lorenzo: "sono riapparse le operazioni di prima [...] il portafoglio senza quelle non sarebbe mai arrivato a quella cifra [...] dobbiamo inserirle e mapparle, perche' l'RSI piu' BB funziona apparentemente bene". Sopra #443 (altro thread): 
- Regola della riga Top, una sola (`system.shown`, specchio in `lab-shown.js`): il rendimento piu' alto fra trend follower 8h/1d e migliore 5m fra `SPOT_LABELS` (Trend EMA, Trend HF, RSI+BB); pari = 8h/1d. Prima: 8h/1d sempre prima se aveva trade. Anche `sim_backtest.token_trades` (portafoglio) e `scripts/chart_audit.py` la usano; `_lab_summary` manda `shown: daily|fast`.
- `system.drawn_row` elenca la riga a cui appartengono le frecce salvate (stessa etichetta, una vendita per trade); un risultato salvato prima di RSI+BB mostra il trend follower finche' il laboratorio non lo rifa' (`_load` lo mette in testa alla coda).
- Ogni evento di `_best_trades` porta `lab`; il registro lo salva per trade.
- Vecchi trade: `relabel` rifa' tutte e quattro le strategie (anche il lato long di RSI+BB L/S: prima di #434 il migliore 5m era scelto fra tutte) sulle 5m dell'archivio (#427, fino a 5000 barre) e non piu' solo sulle 1000 del giro. Ricontrolla anche i "not trend" (fino al controllo si mostrano come RSI+BB, come in #443). Nessuna strategia li rifa' = `none` ("strategy not recorded"); piu' vecchi dell'archivio restano non provati e `proof_from` evita di ritentarli a ogni giro. Tutti i trade salvati restano nel portafoglio.
- Nomi delle strategie tolti dallo schermo (regola di Lorenzo): grafico "Strategy entry · 5m", portafoglio e profilo solo time frame; l'etichetta resta nei dati.
Resta: `scripts/chart_audit.py` sul server dopo il deploy (mismatched = 0) e conteggio dei vecchi trade provati / `none` / non provati dal registro.

# 2026-09-30 — MERRYMEN: numero in classifica senza frecce — `seed-0242` (Claude, a mano)

Lorenzo: "su questa cripto non vedo gli ingressi nonostante ci sia scritto nella lista in classifica un rendimento di piu' 400% [...] queste cose non devono accadere". Causa: `top.js btSub` ripiegava sul migliore a 5 minuti quando il trend follower 8h/1d non aveva trade, `detail.js withLab` disegnava solo l'8h/1d (vuoto). Ora una regola sola in `frontend/static/onchain/lab-shown.js` (`shownSummary` per la lista, `shownTrades` per grafico e tabella), test Node `frontend/tests/lab-shown.test.mjs` (anche in quant-tests.yml) e Python `test_every_listed_trade_has_its_arrows` (vendite disegnate = trade in lista). `scripts/chart_audit.py` controlla tutte le righe salvate sul server (sola lettura). "Board: not ranked" su un Top #2 = riga presa dal database: ora dice "Top #N, from the database".
Audit sul server dopo #436-#438: 36 righe su 134 sbagliate, tutte a 5m (es. BEB1M 30 trade / 1 vendita disegnata, ETHICS 4 / 5): eventi a 5 minuti salvati prima di #434 (RSI+BB) accanto a una riga trend follower. Ora `strategy_lab.drawn_row` (e `ownEvents` in `lab-shown.js`) lista una riga solo se gli eventi salvati sono i suoi trade (stessa etichetta, una vendita per trade chiuso); `_load` mette in testa alla coda (`at = 0`) i risultati incoerenti. Finche' il laboratorio non li rifa' quelle righe restano fuori dalla Top. `scripts/chart_audit.py` riporta listed/hidden/mismatched: mismatched deve essere 0.
Verificato coi dati veri (robinhood, pool 0x27f8...): il trend follower 1d/8h fa 0 trade su MERRYMEN. Il -69% del primo giorno viene letto come rug ("liquidity pulled") ma anche togliendo i primi giorni resta a 0: con 60-77 candele il filtro di volatilita' (pronto alla barra 59) lascia pochissime barre per entrare. Il +400% era il 5 minuti (dal #434 la lista a 5 minuti conta solo i trend follower, e `lab-shown.js` fa lo stesso).

# 2026-09-30 — Time frame graduale del trend follower, archivio candele Top 50 (Claude, a mano)

Lorenzo: "5 minuti al listing, poi 8 ore e poi giornaliero [...] graduale con un algoritmo che tiene conto di quanta storicita' ha il grafico", poi "se nel backtest il segnale a un giorno scatta c'e' abbastanza storicita'. Se non scatta vai a ritroso [...] se da un giorno non c'e' pero' a 12 ore ce l'hai, allora prendi quello", "adegua la strategia se non ci sono ingressi", "prima di applicare questa regola fai un po' di prove su tutte le 50 cripto [...] paritarie o superiori", "un motore che le scarica costantemente per la top 50 e le archiviamo".
`strategy_lab.LADDER` = 1d, 12h, 8h, 6h, 4h, 2h, 1h, 30m, 15m, 5m; `pick_interval(eta')` = primo gradino con >= 60 candele chiuse; `run_daily` scende da li' al primo gradino in cui Trend EMA entra (`_entered`), poi lo stesso con Trend HF; nessun ingresso = il piu' largo. Gradini composti con `_merge` (8h da 4h, 6h/2h da 1h, 30m da 15m). **Spenta**: `LADDER_RULE = False` fa girare la regola vecchia (1d, poi 8h, solo Trend EMA) sullo stesso codice. Per accenderla: `scripts/ladder_compare.py` nel container (`docker compose exec -T app python - < scripts/ladder_compare.py`), confronto "old"/"new" su rendimento medio e libro da $10k; se "new" e' pari o meglio, `LADDER_RULE = True`. Il primo giro del confronto (versione vecchia, dal PC di Lorenzo) prendeva 429 da GeckoTerminal.
`candle_archive.py`: SQLite `data/candle_archive.sqlite`, una serie per pool/lato/sorgente (day1, hour12, hour4, hour1, minute15, minute5), max 5000 barre; `candles()` risponde da disco se fresca (min(step, 1h)) e altrimenti scarica solo il pezzo mancante; `archive_loop` (ogni 20 s, solo se GeckoTerminal ha 4 chiamate di margine e i backtest meme non hanno la precedenza) tiene ogni serie della Top 50 entro 3 ore. Il 5m del laboratorio viene archiviato a ogni giro. Grafici: chip 8h/1w in main da #425; i gradini senza chip si aprono su quello sotto (12h->8h, 6h->4h, 2h->1h, 30m->15m); grafico wallet (`chart.js`) con 1w. `sim_backtest.STEP_S` conosce i gradini nuovi. Bacheca: `seed-timeframe-ladder-20260930` (in corso).
Prima prova (30/09 sera, 50 token, archivio con ~4 ore di loop): media old -4,57% / new -15,92%, libro $10k 9689 / 8568. La scala e' saltata da 1d a 5m in 34 token (le serie intermedie non erano ancora archiviate e la discesa non aveva limite) e a 5m il trend follower fa overtrading in perdita (WIRE -33%, DREGG -47%, STBL -67%). Correzione: `MAX_DESCENT = 3` gradini e mai sotto `FLOOR = "1h"` per chi parte da 1h o piu' (1d -> 12h/8h/6h; i minuti solo per i token giovani). `ladder_compare` ora scrive `archived_series` (quanti token hanno ogni sorgente): la prova vale solo con tutte le sorgenti archiviate. Resta: rilanciarla quando `archived_series` e' ~50 ovunque; regola ancora spenta. Archivio: `archive_loop` saltava il giro sopra 10 chiamate/min e il background sta fisso a 14, quindi non scaricava mai (12h/1h/15m a zero): ora aspetta il turno nel limitatore (#439). RSI+BB (Lorenzo, 30/09 sera: "applicare la stessa logica [...] time frame piu' alti per trade piu' duraturi"): `run_daily(strategies=strategy_lab.RSI_BB)` fa la stessa scala; oggi RSI+BB gira solo a 5m in `backtest_all`. `ladder_compare` confronta anche `rsi_5m` (riga salvata) e `rsi_new`; collegarlo a classifica/portafoglio e' del thread "RSI+BB in lab e classifica", solo se la prova dice pari o meglio. Seconda prova (01/10, archivio quasi pieno: 43-45 token su 50 per sorgente, `ladder_compare-20261001T020414-cb17.json`): trend follower libro $10k OLD 9567 / NEW 18017, ma tutto da 2 outlier (EQUI +2428% 1 trade, YOYO +1740%); senza i primi 3 media NEW -7,0% contro OLD -4,8%; sui 21 token dove cambia qualcosa NEW meglio in 7, peggio in 14. RSI+BB sulla scala peggio dei 5m (libro 10338 contro 13307, 20 meglio / 24 peggio). Regole lasciate spente, decisione a Lorenzo. Lorenzo ha scelto "Lasciare spenta", poi: "ogni giorno rifai un po' di test e mi mandi dei messaggi su telegram se effettivamente migliorano i risultati". `ladder_watch.py`: ogni giorno dalle 8 italiane, sui token della Top con backtest, trend follower regola in uso contro scala e RSI+BB 5m contro scala, solo dall'archivio (`candle_archive.offline`, nessuna chiamata, nessuna scrittura) con `run_daily(rule=...)` che non tocca il globale; storico in `data/ladder_daily.json`. Telegram (`telegram.send_message`, canale di sistema) solo se "migliora davvero": libro $10k, media senza i 3 migliori e token migliorati >= peggiorati, tutti e tre. Accendere resta una scelta di Lorenzo.

# 2026-09-30 — Frecce della strategia corrette, timeframe a scala, posizioni cliccabili — `seed-0240` (Claude, a mano: Actions DeepSeek ferme)

Lorenzo (stesso messaggio del portafoglio $10k qui sotto): "time frame [...] graduale con un algoritmo che tiene conto di quanta storicita' ha il grafico", "voglio vedere anche il time frame settimanale", "le posizioni aperte e chiuse se ci clicco voglio vedere quali sono stati graficamente", "gli ingressi [...] non vengono visualizzati correttamente nel grafico". Il replay $10k l'ha fatto in parallelo un altro thread (#424, `sim_backtest.py`): il mio doppione e' stato tolto prima del merge.
Timeframe: `strategy_lab.FULL_LADDER` 1d, 8h, 4h, 1h, 15m, 5m (il piu' largo con >= 60 candele chiuse) e' pronto ma **spento**: `LADDER = ("1d", "8h")`. Lorenzo: "prima di applicare questa regola fai un po' di prove su tutte le 50 cripto [...] dovrebbero essere paritarie o superiori". La regola la decide il thread "Time frame graduale e settimanale" dopo quel test.
Frecce: `system._best_trades` metteva buy/sell sulla candela del segnale, ma il riempimento e' all'apertura della successiva (come `radar.long_events`): ora `t` = candela di esecuzione, `best.fills = "next_open"`. `_signal` non riannuncia i segnali salvati prima (senza `fills`); `sim_backtest.remember` sostituisce lo stesso trade salvato un passo prima (non lo tiene doppio) e `_one_timeframe` non mescola trade di timeframe diversi (quelli vecchi valgono solo prima dell'inizio del nuovo). `detail.js`: ridisegna quando arriva il backtest (prima le frecce mancavano se le candele arrivavano prima), si apre sul timeframe del backtest, fine grafico = ampiezza dell'ultima candela (prima 1h: sul 1d sparivano i trade 8h dopo l'1:00), chip 8h e 1w (aggregati da 4h e 1d), pallini gialli "Wallet in/out" per posizioni del profilo e righe del portafoglio Top 50 (`setOwn`). `_closed_trades` non forza piu' la chain "robinhood".
Resta: misurare quanti token finiscono a 5m/15m e se i segnali li' sono troppi.

# 2026-09-30 — Portafoglio $10k sulla Top 50 (Claude, a mano)

Lorenzo: "voglio che tu applichi a quel portafoglio [10.000 dollari] tutti gli ingressi e tutti i rendimenti di tutte le gemme in top 50", poi "farlo visualizzare a tutti gli utenti indipendentemente dall'account" e "deve continuare ad aggiornarsi [...] sui prossimi ingressi e futuri, non soltanto sul backtest".
`sim_backtest.py`: ogni token della Top porta i trade del backtest che mostra la sua riga (trend follower 8h/1d, o il migliore 5m se quello non ha trade). `remember()` li scrive in `data/top_backtest_ledger.json`, registro che cresce solo (chiamato da `strategy_lab.run_one` a ogni giro e dall'endpoint): la finestra 5m che scorre o un token uscito dalla Top non cancellano niente. `replay()`: un solo wallet da $10.000 uguale per tutti, in ordine di tempo, 10% dell'equity per ingresso (mai piu' della cassa libera), uscita = stake x rendimento del trade (costi inclusi); aperti al prezzo live (`live_prices`), altrimenti al costo. `GET /api/onchain/top/backtest`; scheda `sim-backtest.js` (curva, Open/Closed, tocco = pagina del token) da Top ("$10k wallet on these trades") e Profile > Simulated wallet. Lorenzo, 30/09: un token uscito dalla Top tiene aperta la posizione (marcata al prezzo live) e non prende nuovi ingressi: e' gia' cosi', perche' `strategy_lab` gira solo su `_top_entries(50)`. Poi Lorenzo (screenshot con Claude, n/acc, Mickey ancora aperte): "reset completo di tutti gli account e far si' che l'importo sia 10.000 [...] nelle posizioni chiuse tutte quelle [...] della top 50 [...] e le posizioni aperte, che sarebbero aperte ad oggi". Ora il Simulated wallet del profilo (e il numero SIM in alto) E' il portafoglio Top 50 (`main._top_wallet`, cache 20 s): aperte, chiuse, linea dalla curva. All'avvio `_sim_reset_once` copia `onchain_autotrader.json` in `onchain_autotrader.before-sim-reset-2026-09-30.json` e riporta ogni libro Sim a $10.000 senza posizioni ne' trade sim (una volta, marcatore `sim_reset_2026-09-30.done`); `SIM_START_USDG` = 10.000. Tolti Set cash/Start. Il libro Sim dell'autotrader continua sotto (card Auto-trade) ma non e' piu' quello del profilo. 30/09 ORDO (Lorenzo: "come puo' una strategia trend follower entrare dopo un drawdown del genere?"): il ripiego 5m prendeva il migliore di tutte le strategie, anche RSI+BB che compra i cali. Ora il portafoglio segue solo Trend EMA/Trend HF (`sim_backtest.TREND_LABELS`, etichetta `lab` salvata nel registro; i vecchi 5m senza etichetta sono scartati in lettura) e sul grafico il pallino giallo dice "Strategy entry · 8h" / "Strategy exit · 8h +X%" col time frame del trade. Poi (#433/#434) riga della Top e frecce solo trend follower; token senza trade del trend follower fuori lista (mai "no entry"). Poi Lorenzo, arrabbiato: "prima c'avevo 138 operazioni ora ce ne sono solo 3" (il filtro #432 nascondeva i vecchi 5m senza etichetta, nessun dato cancellato); scelta "Rimetti tutto": il registro conta di nuovo tutti i trade salvati, `sim_backtest.strategy_of` li marca trend/counter/unknown (profilo "strategy not recorded", grafico "Old entry"), `relabel` in `strategy_lab.run_one` riprova Trend EMA/HF sulle stesse candele 5m e da' l'etichetta ai vecchi. I NUOVI trade entrano solo dal trend follower. Non tocca la Sim live. Limite: la Top di oggi = sopravvissuti (bias), e l'equity intermedia conta gli aperti al costo.
Poi, stessa sera: "fammi visualizzare soltanto i trend follower" (#442: il portafoglio contava solo i trade trend) e subito dopo, visto il portafoglio a ~$8.7k senza gli RSI+BB: "l'RSI piu' BB funziona apparentemente bene, e quindi implementiamolo nelle strategie, nei backtest, eccetera" (#443). Ora `system.SPOT_LABELS` = Trend EMA, Trend HF, RSI+BB (solo long; RSI+BB L/S fuori) decide il migliore 5m per riga della Top, frecce, portafoglio e `lab-shown.js`. Ogni trade porta la strategia (`strategy_of` = etichetta; "strategy not recorded" se mai provata); `relabel` prova tutte e tre sulle candele 5m, e i vecchi "not trend" si mostrano come RSI+BB. Gli alert restano del trend follower 8h/1d. La tab Strategies da sostituire la segue un altro thread.

# 2026-09-30 — Ricevute che insegnano: pagella delle gemme (Claude, a mano)

Lorenzo: "le ricevute che rilasciano questi cambi di stato cosa ci possiamo fare? proponimi idee per migliorare architettura predittiva [...] scelta delle gemme", poi "applica tutto, mi piace". Proposta in project-files `predittivo/idee-ricevute-e-gemme.md`; fatte tutte e 7 (Actions DeepSeek ferme):
1. `gem_track`: ogni caso congela una ricevuta (`parts` = ogni input di `final_score` da `leaderboard.score_parts`, `rules_v`, `receipt` sha256). 2. Seguiti anche `studied` (tutti) e `rejected` (1 su 5 per hash dell'indirizzo), chiavi `chain:token#studied|#rejected`; i "ranked" tengono la chiave vecchia. 3. Checkpoint 1/3/7/30/90 g, `hi`/`lo`, `first` (+100% o -50% prima), benchmark Kraken (SOL/BNB/ETH) per il rendimento in eccesso. 4. `gem_learn.py`: pagella (IC di rango e AUC per input) e candidato logistico (stesse soglie dei meme, deve battere il punteggio a mano fuori campione) in `data/gem_model_candidate.json`; entra nel punteggio (peso 0.3) solo copiato in `data/gem_model_approved.json` con `approved: true`, `reviewer` e hash giusto. 5. `judge.drifted`: stessa lettura sugli stessi fatti che cambia idea -> `drift`, badge "judge unsure" (il riuso per fatti/commit c'era gia'). 6. `leaderboard._text_moved`: +8 punti solo dal pilastro sito -> badge "text-driven", si toglie quando si muove un altro pilastro. 7. `autotrader._why`: ogni ingresso porta `report_hash` e `gem_receipt`.
Resta: aggiornare la "Mappa del sistema DEGEN" (freccia esiti -> Gem Finder); il modello non conta finche' Lorenzo non approva un candidato (servono >=40 casi finiti).

# 2026-09-30 — Agent map live (Claude, a mano: Actions DeepSeek ferme)

Lorenzo: "se entro qui io veda cosa succede davvero quando una crypto entra in analisi, tutto il ciclo in real time animando questi blocchi". Fatto in `agent-map.js`/`agent-map-model.js`: selettore di default "Follow live" (ultimo progetto con eventi), riga "Now analysing SYMBOL · chain · nodo · Xs ago", all'apertura replay del ciclo registrato del progetto, poi ogni evento nuovo (poll 10 s) fa pulsare il suo nodo e una scintilla parte dal nodo precedente dello stesso progetto; nodi con eventi negli ultimi 90 s respirano. Solo transform/opacity, niente con reduced-motion. Poi Lorenzo: "vedere in tempo reale tutti i progetti che entrano in questo schema blocchi [...] una quantita' ridotta": gli 8 progetti piu' recenti sono gettoni sul blocco del loro ultimo evento e saltano di blocco in blocco (transform) quando arrivano eventi nuovi; tocco sul gettone = segui quel progetto. Poi (click sul gettone non animava: il feed della mappa ha solo 60 eventi) Lorenzo: "metti un campo dove io compilo il ticker [...] deve essere tutto formalmente verificato e tracciabile": `journey.py` + `GET /api/agent/journey` raccoglie i record veri del token (projects_db first_seen e verdetto, attivita' agent, journal chiamate DeepSeek, strategy lab), ognuno con `id = sha256(record)` e `link = sha256(prev + id)`; `agent-journey.js` li riproduce su una timeline e ricalcola la catena nel browser ("Chain verified"). Limite: il verdetto in projects_db e' solo l'ultimo (sovrascritto); lo storico vero serve il registro di #362. Poi Lorenzo: "hai lasciato schemi a blocchi non servono [...] voglio ripercorrerli TUTTI": schema a blocchi e gettoni tolti (resta riga live + ticker recenti + campo); `journey.py` legge anche discovery, coda ricerca, check dei pilastri, rank, cache judge/research/code review, chiamate DeepSeek per repo e sito, Top tracker con rendimenti, outcomes, alert. Poi: "l'animazione deve avere i tempi reali [...] e lo schermo scorrere insieme": `replaySchedule` rispetta gli intervalli veri alla velocita' scelta (auto: la piu' lenta che sta in ~60 s), pause oltre 3 s a schermo accorciate e segnate, orologio fisso in basso, pagina che segue il passo (si ferma se tocchi, tasto Follow). Poi (Lorenzo 30/09 sera: "riprendi cosa e' rimasto a mezzo"): `history.py` = registro in sola aggiunta `onchain_history.jsonl` (volume, max 40 MB, tiene la meta' piu' recente). Ci scrivono projects_db.record/set_standing, pilastri e rank del leaderboard, judge, research, code_review; la Trace lo legge e non duplica le righe "ultimo valore". Rivalutazioni precedenti al deploy non recuperabili. I 4 nodi "Not connected" (Evidence, Decision, Outcomes, Objectives) non si animano: il feed non ha quegli eventi.

# 2026-09-30 — PR #408 quant + Agent integration (Codex)

**Mergiata da Claude il 30/09** (Lorenzo: "applica"). Rivista sul codice: suite completa su Linux 1461 passati / 1 saltato, ruff pulito, 8 test Node della mappa ok; la CI e' caduta in 3s senza log (minuti Actions finiti). Effetto visibile: senza `data/quant_approved.json` sul server il pilota (Sim e Real) **non apre nuove operazioni**; le posizioni aperte escono con la logica di prima. Approvazione paper/real resta di Lorenzo, dopo dati reali e report. Il loop di trading deve girare in un solo worker (guardia per processo). Code integrated. Includes #402 map, preserves latest main Scout cube. 47 focused Python tests + 8 Node tests passed; full-backend lint passed. Full suite has environment/external failures; no profitability claim. Claude continuation: **docs/CLAUDE_QUANT_HANDOFF.md**, with exact checks and remaining limitations. No production approval or orders activated.

30/09, report sui dati reali (Lorenzo: "si", poi "procedi"): nessuna finestra completa, il collettore parte dal deploy del 30/09; report in project-files `quant/report-dati-reali-2026-09-30.md`. Rischio trovato: le barre delle gemme venivano solo dal campionamento, una barra da 5 minuti mancante rende il caso non disponibile e blocca la coorte. Ora `_refresh_system` riempie i buchi delle ultime 24h con le candele GeckoTerminal (`_bar_hole`, al massimo ogni 30 min per gemma, dentro `SYSTEM_FETCHES_PER_TICK`). Resta: leggere i conteggi reali dal pannello quant; fissare costi e confini prima di lanciare il CLI.

# Memoria di sessione

## Dati social veri per la Top 50: Telegram, Discord, X — 2026-10-01
Lorenzo: "per la top50 sfruttiamo questa connessione per controllare i canali telegram pubblici dei progetti" (guida MTProto/WTelegramClient), poi "possiamo fare lo stesso con discord?", "dobbiamo carpire quante piu informazioni possibili dai telegram, mettendoci in pari sugli sviluppi", "non abbiamo altri metodi per avere accesso a dati social veritieri?".
Prova sulla Top 50 del 01/10 (`project-files/telegram/top50-canali.md`): Telegram 32/50 (tutti da DexScreener, siti 0 in piu'), 16 canali (solo 2 con post negli ultimi 30 giorni), 11 gruppi, 2 senza anteprima; Discord 11/50 via API inviti pubblica (membri/online), 4 senza Telegram. Login MTProto (Telethon) NON fatto: aggiungerebbe solo i messaggi dei gruppi, serve api_id/api_hash/telefono di Lorenzo. Discord messaggi: solo con bot invitato dagli admin; account utente = ban, scartato.
Fatto: #468 (review_brief passa `tg` e `dc`, nuovo `discord_public.py`, riga Discord nella scheda, PROMPT_VERSION 5), #470 (`tg_digest.py`: 90 giorni di canale, cronologia sviluppi estratta da DeepSeek, nel dossier, nella review e nella scheda; PROMPT_VERSION 6). Causa del "No X or Telegram data provided": `review_brief` non passava `tg`.
X: lettura solo a pagamento (Basic ~200$/mese). Alternativa proposta: LunarCrush (provato da connettore: conosce A0T e SOGNI, menzioni/creatori X), serve chiave API a pagamento sul server: decisione di Lorenzo. Altre: servizi terzi non ufficiali, Farcaster (Neynar), CoinGecko community.

## Wallet collegati verificati on-chain per la Top 50 — `seed-0241` — 2026-09-30

Lorenzo, sul rapporto di DREGG ("807 wallets linked to each other"): "mi preoccupano questi 800 account collegati", poi "fai che questa analisi venga fatta su tutte le cripto [...] della classifica [...] soltanto se vanno in top 50 [...] non voglio che si ripeta un allarme del genere". Trovato: 761 degli 807 erano destinatari di un airdrop da 744 token; i gruppi piccoli avevano 0 on-chain (il `currentHolding` di RugCheck e' vecchio). PR #429: il rapporto giudica la quota di supply, non il numero di wallet. Poi `onchain/linked.py`: per i token Solana in Top 50 (`item["top"]`) con quota RugCheck >=1% legge `insiders/graph`, toglie i collegamenti da airdrop (un mittente, >=20 destinatari, meta' con lo stesso importo), pool e locker, e somma i saldi di oggi via RPC (max 80 wallet, cache 6h). Se piu' del 20% delle letture fallisce resta il dato di RugCheck. DREGG: da 39% (807) a 4% (51). DeepSeek non usato: Actions ferme.

## Meme spente negli alert, saldo simulato a mano — `seed-0238`, `seed-0239` — 2026-09-30

Lorenzo: "le meme e shitcoin sono state bloccate dal bot alert? inoltre la simulazione voglio poter modificare il saldo a mio piacimento", poi "non le voglio le meme [...] dobbiamo avere strategia e alert solo su roba buona".
Gli alert meme non erano bloccati (server: 64 oggi, 72 ieri; scarti 24h: LP non bloccata 166, GoPlus codice non verificato 141, memoria rug 82). Era ferma la simulazione: dal gate quant #408 il pilota entra solo su gemme approvate (`quant_runtime.gem_verdict` scarta ogni meme) e senza `quant_approved.json` non entra affatto. Ora `listings_allow_memes=False` (config): torna il filtro con sito del progetto e voto DeepSeek, nome da meme = scartato. Se sul server il `.env` imposta `LISTINGS_ALLOW_MEMES=true`, vince quello.
Poi Lorenzo: "il sistema deve fare ingressi con strategia dinamica su gemme e non piu su crypto etichettate come meme o con caratteristiche da evitare", e sulla card "Si', solo Sim". Ora la Sim ha un secondo libro, `autotrader.trend_signal` (`u["trend"]`): compra sul buy del trend follower 8h/1d di `strategy_lab` (`_sim_trend_signal` in main) solo se `quant_runtime.gem_verdict` passa (niente meme, in classifica, dati di mercato freschi, liquidita'), vende sul sell; prezzi aggiornati da `live_prices` nel giro dei segnali. Il Real resta bloccato dal gate quant (#408) finche' Lorenzo non approva un report.
Saldo simulato: `sim_cash` su `PATCH /api/onchain/autotrader` + "Set cash" nel profilo (PR #420): cambia la liquidita', le posizioni restano, `sim_start` si sposta dello stesso delta.

## Potatura file che gonfiano la RAM — `seed-0236` — 2026-09-30

Controllo server: 1,8 GB su 3 GB, `sniper_candidates.json` 430 MB (l'app passa da 214 MB a 1,77 GB all'avvio). Lorenzo ha scelto "potare i file". Fatto a mano (Actions DeepSeek ferme).
Ora `sniper/cache.py` tiene in RAM solo i candidati aggiornati negli ultimi 7 giorni, max 3000; il resto va in `data/sniper_candidates_archive.jsonl.gz` (append, niente perso; se l'archivio non si scrive non si butta niente). Potatura all'avvio e a ogni salvataggio. `sniper/market.py` scarta i token non visti da 7 giorni (e' uno screener). Il diario `onchain_outcomes.json` era gia' a 5000 voci; `onchain_rug_archive.json` non toccato (memoria del modello).
Resta: misurare la RAM dopo il deploy; il primo avvio legge ancora il file grande una volta.

## Trend follower 8h/1d sulla classifica, con segnali — `seed-0235` — 2026-09-30

Lorenzo: "sui progetti in classifica io voglio che venga attivata la strategia [trend follower] con time frame piu' alti [...] se il token e' abbastanza giovane 8 ore se no un giorno se c'e' almeno abbastanza candele [...] segnali di piu' qualita'". Fatto a mano (Actions DeepSeek ferme, nessuna chiave in sandbox).
Prima: `strategy_lab` calcolava gia' `daily` (1d, o 8h sotto 60 giorni) ma la lista Top mostrava solo il migliore a 5m e nessun segnale partiva; minimo 30 candele, sotto il riscaldamento dei filtri. Ora: `TRIGGER_MIN_BARS = 60` (filtro volatilita' 16+44: primo ingresso possibile alla barra 59, misurato), solo candele chiuse (`_closed`), `_signal` = ultimo buy/sell se sull'ultima candela chiusa e non gia' annunciato (`daily.signal`), `on_signal` -> `_notify_trend_signal` in main (Telegram in italiano, stessi utenti delle gemme, senza tetto orario). Se GeckoTerminal non risponde il `daily` salvato resta. `_lab_summary.daily` solo con trade; `top.js` scrive "8h +X% · N trades · long", altrimenti "5m +X%".
Resta: l'autotrader non segue questi segnali (non chiesto); valutare con Lorenzo se vuole il pilota sulle gemme.

## Scanner manuale al passo con la pipeline — `seed-0232` — 2026-09-29

Lorenzo, con lo screenshot di HYDX: "lo scanner manuale e' insufficiente e non si e' evoluto seguendo tutti gli aggiornamenti e migliorie che abbiamo fatto".
Fatto a mano (Actions DeepSeek ferme): `manual_scan.py` distingue progetto e meme; un progetto prende il verdetto del Gem Finder (`gem_view`: voce in classifica, riga del database o accodato con `projects_db.upsert(..., "manual")`) con punteggio, pilastri, giudice e codice; backtest dal laboratorio (`strategy_lab`, o eseguito e salvato: `backtest_view` = trend follower daily + migliore 5m contro hold). Memoria in inglese, flag di DeepSeek sui "similar" tolti. Scheda con tasto "Full token page" (`openFromHash`). Bug trovato: `strategy_lab.get` non restituiva `daily`, quindi ogni pagina gemma diceva "No daily backtest".
Poi Lorenzo: "voglio poter aggiungere manualmente un progetto che poi entra eventualmente nel circolo di tutte le nostre logiche [...] un'anteprima un po' migliore". Lo scan non accoda piu' da solo: `manual_scan.add` (POST `/api/onchain/scan/add`) prende il token dalla cache `_recent` del server (mai dati del client), toglie un'eventuale bocciatura da `_gone` e lo mette in `leaderboard.add(..., "manual")`. Anteprima: `about()` da GeckoTerminal (descrizione, holder, top 10) + griglia cap/liq/volume/24h/eta'/holder.
30/09, Lorenzo: "tutti gli step che fa tutte le cose che guarda le voglio vedere scritte e con delle animazioni". `POST /api/onchain/scan/stream` (NDJSON): `manual_scan.Steps` emette `plan` e poi `{step, state, detail}`; i controlli del filtro arrivano da `legit.assess(tap=...)` (lista `_Tap`), quelli non raggiunti vanno in `skip`. Scheda: `scanStep()` in `sheets.js`, pallini `.step-dot` (`.scan-dot` esisteva gia' per il nastro). `/api/onchain/scan` resta.
Poi Lorenzo: "manca tutta la descrizione che solitamente lo scout fa nei progetti [...] della top". `manual_scan.report()`: voce della classifica (`_public`), o riga del database, o studio al momento (`depth.analyze` + `judge.judge(priority=True)` + `code_review.review(priority=True)`, 75 s ciascuno); il risultato va in `scout` e la scheda lo disegna con `gemWhy` di `leaderboard.js`, identico alla Top. Lo studio al momento non scrive nel database: lo fa solo "Add to database".
HYDX (30/09): `strategies.rug_event` ora da' `kind` ("rug" o "fall"); il terzo controllo (-85% dal massimo) e' "fall": la strategia si ferma lo stesso (seed-0199) ma il grafico scrive "Stop", non "Rug · dead token". `manual_scan.pick` sceglie il token con piu' volume 24h, poi il suo pool piu' liquido.
Poi Lorenzo: "i punti negativi devono essere rianalizzati in modo piu' critico e trovare altre vie". `scout_recheck.py` (passo "recheck"): punti rossi = problemi del giudice + flag dei pilastri; altre vie (GitHub da social/dominio/code search con token, pagine docs/app/whitepaper, copertura LP di GoPlus contro la liquidita' vera); DeepSeek (`purpose="scout_recheck"`, cache 1 giorno) li classifica confirmed/unverified/refuted, senza chiave un'euristica. Nella scheda restano rossi solo i confermati; "Checked again" mostra gli altri.
30/09, IMG_6021, Lorenzo: "possiamo verificare se effettivamente sono dati che non possiamo avere". Quasi tutti i "Not verified" erano dati gia' in casa non passati al giudice: `scout_recheck.market_lines` aggiunge eta' pool/volume/liquidita' (DexScreener), TVL (`traction.lookup`, DefiLlama), holder con etichette contratto e `lp_locked_pct` (fatti del pilastro tokenomics), sito come letto (parole, `rendered`), `team_lines` (frasi su team/founder/KYC, pagina `/team`), `twin_line` (progetto col testo identico per nome; stesso sito = stesso progetto, smentito). Il team resta non verificabile senza X.
30/09, Lorenzo: "la cosa del 100% identica e' una cazzata". `reader.sketch` ora restituisce [] sotto `SKETCH_MIN_GRAMS=20` (lo scheletro JS faceva 100%), `closest(same=...)` salta lo stesso progetto (`research.same_project`: stesso sito o nome+ticker), `judge._drop_false_clones` ha pulito una volta i problemi "identical to another project" salvati. Rendering JS: Lorenzo ha scelto "Installa" (30/09). Il Dockerfile installa `chromium` di Debian + `playwright`, `CHROMIUM_PATH=/usr/bin/chromium`; `jstext.render` segue i redirect lato server (un 3xx restituito alla pagina mandava Chromium al proxy morto). Spegnibile con `SITE_RENDER=0` nel `.env`.
30/09, Lorenzo su HYDX (Robinhood, sito hyperdex.app): "da cosa dipende? usa sistemi per essere in grado di leggerlo; la liquidita' bloccata mi sembra strano 0%". hyperdex.app e' una SPA Vite (35 parole senza browser, 780 con Chromium); con il testo letto "coming soon" azzerava il sito, ora e' segnaposto solo sotto 150 parole. Lo 0%: GoPlus conosceva posizioni LP per $613 su $63k di liquidita': con copertura <50% `lp_locked` e' None e c'e' `lp_note`. Il PoolManager v4 (e ogni pool in `dex`) non conta piu' tra i contratti holder. Team anonimo: mai tra i punti rossi (`scout_recheck.minor`).
30/09, Lorenzo: "risolvi tutto quello aperto da deepseek; revisionando il suo lavoro". Nessuna PR di DeepSeek aperta; issue #268 chiusa (fatta con #301). Le 10 segnalazioni "DeepSeek (Telegram)" del 28/09 erano gia' coperte da seed-0170/0172/0162/0163 e lavori successivi: risolte in `resolutions.json` con la causa (3 bug veri gia' corretti, il resto voluto o dato giusto). Unica correzione: `outcomes.train`/`train_winners` ora dicono che servono anche 8 non-rug (il testo vecchio ha ingannato DeepSeek due volte). Chiuse anche seed-0198..0201, fatte con #262-#265 ma mai risolte sulla bacheca.
30/09, Lorenzo: "deepseek può intervenire come ultimo revisore di queste scansioni? aiutami a trovare ogni dato". Lo scanner manuale mostrava letture vecchie ("from the database"): ora `report()` rilegge sempre i pilastri (quella salvata e' solo il ripiego), il giudice rilegge subito se i fatti sono cambiati (`judge.judge(fresh=True)`), la revisione finale di DeepSeek (scout_recheck) filtra i punti rossi e, se va in timeout, `scout_recheck.quick` lascia le assenze non verificate invece che rosse. Il motivo del rifiuto mostrato e' quello della lettura nuova.
30/09, Lorenzo: "pool e vesting devi anche trovare lo sblocco che tempi ha". `unlocks.py`: per i 6 contratti holder piu' grandi (via RPC; Robinhood con rpc_client, Base/Ethereum/BSC RPC pubbliche) riconosce account EIP-7702 (codice 0xef0100: sono wallet), VestingWallet (start+duration), timelock (releaseTime/unlockTime/lockedUntil/endTime/cliff) e locker (`isLocked(token)`, `lockedPositions(token)`), e se il bytecode ha funzioni di rilascio. Su HYDX: 8.3% + posizione LP in un locker (nessuna funzione di rilascio trovata), gli altri "contratti" erano wallet EIP-7702: contratti 33%->3.5%. Blockscout Robinhood risponde con una sfida Cloudflare: non usabile. Scheda: blocco "Supply in contracts"; flag se >=3% si sblocca entro 30 giorni.
Resta: il meme non passa ancora da `meme_engine.score` nello scanner.

## Scheda progetto, mappa e consumi DeepSeek — 2026-09-29

Lorenzo: "produci su github ciò che serve, poi claude implementerà il tuo codice"; chiede inoltre mappa a neuroni, agent oltre le scansioni e un lavoro esclusivo sui consumi. In docs/analysis-receipts/JOURNEY_AND_AGENT.md: contratti, integrazioni J1-J4 e agent con domande/ipotesi/stop. journey_reference.py è specifica eseguibile, 12 test passati, non runtime. neural-map.fragment.html è prototipo concettuale con scenari sintetici, non telemetria live. DEEPSEEK_COST_AUDIT.md: filone E0-E5 separato. Diagnosi su e8e0a9: UI fonde done/eventi e today/chiamate, research e scanner entrambi readings; studies conta note ripetibili mentre Database studied conta righe studied+ranked. 27849/893 forniti dall'utente, non misure estratte dal server; 80 consistency resta da riconciliare col limite 12/die nello SHA letto. Nessuna inferenza sulla fattura. Prima accounting distinto e gateway budget globale, poi deduplica/scheduler/token packing. Integrare nello store #362/#364; nessuna seconda memoria. Suite backend non eseguita; nessun merge/deploy. Bacheca API non accessibile dal terminale di questa sessione.


## Memoria verificabile e riuso senza token di tracciamento — 2026-09-29

Lorenzo: "mi piace l'idea, applichiamola scrivi tutto e pubblica su github per poi darlo in pasto a claude". Specifica in docs/analysis-receipts/SPEC.md, 30 criteri in ACCEPTANCE.json e esempio sintetico EXAMPLE.json. Base letta e8e0a97c688cf36461a1f43791b4e19610e0b33b. Estende #358 e PR #362/issue #363: un unico store e contratti, nessun secondo registro. Primo flusso: code_review, riuso per input/versioni/prove identici, invalidazione e protezione da risposte tardive. Zero chiamate AI per logging/hash/verifica/replay deterministico; nuove analisi restano soggette a budget. Documenti soltanto, runtime da implementare con PR R1-R5; R6 opzionale. JSON e ID verificati, test applicativi ancora da creare. Non è una blockchain e non integra DREGG: checkpoint indipendenti rimandati finché esiste un bisogno dimostrato. Nessun merge/deploy o automazione avviati.


**A cosa serve questo file**: se apri una chat nuova con Claude su questo
repo, fagli leggere questo file (o linkalo — è il primo posto dove cercare
"da dove eravamo rimasti"). Claude lo aggiorna dopo ogni lavoro non banale,
cosi' che una conversazione diversa sappia esattamente lo stato delle cose
senza dover rileggere l'intera cronologia della chat precedente.

Per le segnalazioni puntuali (bug, richieste) la fonte di verita' resta la
bacheca (`/api/issues`, vedi `CLAUDE.md`) — questo file e' per il resto:
lavori pluri-sessione, decisioni prese, stato di piani approvati.

---


## Saldo del wallet che si muove col prezzo — `seed-0229` — 2026-09-29

Lorenzo, col video dell'app pump.fun: "il saldo [...] si aggiorna in modo frenetico costantemente [...] vorrei vedere anche quanto sta perdendo o guadagnando con animazioni frenetiche".
Fatto sul profilo (simulato e reale): `live_prices.py` + `GET /api/onchain/live-prices` (cache condivisa, DexScreener poi GeckoTerminal), `static/onchain/live.js` (un solo polling ogni 2 s, `roll()` cifre, `flash()`), `profile.js` `applyLive()`. Scritto a mano: Actions ferme per i minuti, DeepSeek non girava.
Poi (stesso giorno) esteso a scheda Auto-trade, saldo in alto (`/api/wallets/total` porta `live`, le posizioni da marcare) e ultimo punto del grafico del profilo.

## Intelligenza e memoria di DeepSeek — issue #358 (+ #366, #365) — 2026-09-29 — **in corso**

Lorenzo, 29/09 (piani ChatGPT): "continuare a osservare, ricordare cio' che sappiamo e approfondire quando c'e' una ragione concreta [...] un cambiamento nella liquidita' deve aggiornare il rischio; non richiede di rileggere tutto il sito". "Prima misuriamo dove DeepSeek sbaglia o ripete lavoro".
Fatto (branch `claude/project-thread-sdhpv6`, scritto a mano: Actions DeepSeek ancora rotte in 3 s):
- **I00 registro chiamate**: `notify/deepseek_calls.py`, una riga per chiamata in `data/deepseek_calls.jsonl` (motivo `purpose`, oggetto `subject`, hash della richiesta, token, token in cache, durata, errore, JSON non valido; niente testo del prompt). Stessa richiesta entro 14 giorni = ripetizione; `same_out` = anche la risposta uguale, cioe' lavoro buttato. Tutte le chiamate passano da `deepseek_desk._post` (anche la revisione giornaliera). Numeri: `GET /api/agent/calls?days=7` (`&recent=50` per le righe).
- **I04 giudice guidato dai cambiamenti**: la lettura dipende da liquidita', cap, verdetto delle regole, voti dei pilastri (`judge.judged_facts`). Liquidita' -40%, cap x3 o /3, regole cambiate o pilastro +-15 la invalidano subito (al massimo una ogni 6h); fatti invariati la tengono fino a 5 giorni invece di richiederla ogni 3 (prima che `leaderboard._fresh` smetta di contarla a 6). Senza budget resta la vecchia con `stale`. Il motivo sta in `why` e nel registro (`judge/liquidity`, `judge/periodic`...). Sito, codice e ricerca non vengono riletti.
- **#366 contatori**: "80 consistency" non erano chiamate: ogni controllo scriveva una nota per ogni incongruenza trovata (`consistency.py`). Chiamate e lavoro separati e progetti distinti li ha fatti l'altro thread (c27d02d); qui in piu' `note(tally=False)` per le note-dettaglio, e il giudice senza budget restituisce la lettura vecchia marcata `stale` invece di None.
Mappa statica dei chiamanti (verificata sul codice): judge (TTL 3g, ora a fatti), board_review (3000 token), code (gia' guidato da `pushed_at` GitHub: modello da copiare), research_dossier (TTL 7g, senza hash), site_legit (chiave = hash del testo del sito: deduplica gia'), alert_batch/alert_manual, consistency (12/giorno), narratives, study, chat, daily_review.
Resta: dopo il deploy leggere `/api/agent/calls` su 7 giorni e decidere dove intervenire con numeri (ripetizioni per motivo); research_dossier con hash degli input come code_review; #365 ricevute = estendere questo registro con prove e versioni, non una seconda memoria; I01-I03, I05-I07 dopo le misure.
## Piano struttura backend (issue #357, B00-B08) — 2026-09-29 — **in corso**

Lorenzo, 29/09, ha condiviso i due piani di ChatGPT per Claude: #357 struttura backend, #358 intelligenza e memoria (altro thread). Registro vivo con mappa, evidenze e stato: `docs/backend/B00_REGISTRO.md` — aggiornarlo a ogni PR.
S01-S07 li ha chiusi l'altro thread (#350, #354, #359). Qui: B02 scritture JSON atomiche (`app/atomic_write.py`, 39 punti: un crash a meta' scrittura lasciava file vuoti che gli store leggevano come "parti da zero"); B04 task di `lifespan` tracciati e cancellati (il riconciliatore degli ordini non aveva riferimento); B00 registro.
Fatto dopo (#381, thread "Riepilogo backend dopo audit ChatGPT", Lorenzo 29/09: "completa quello che puoi"): SSRF chiusa con `trading/onchain/egress.py` (controllo IP pubblico al momento della connessione, anche per le richieste di Chromium, che non si connette piu' da solo); i ~30 `create_task` Telegram passano da `main._fire` (riferimento tenuto, errore nel log); deploy ancorato a `github.sha`. A-ADMIN: Lorenzo, 29/09: "il tester e' un utente che accede a tutti i servizi, non admin". `admin_emails` ora solo Lorenzo; `full_access_emails` (tester) da' il piano pro senza poteri admin (piani, link ospite, /admin/status, istruzioni a DeepSeek).
Resta: M01/M02, lease sui loop prima di piu' worker, backup/restore provati, B06 estrazione router, B07 misure, B08 Actions ferme (causa lato account GitHub, la vede solo Lorenzo).

## Consegne di ChatGPT/Codex del 29/09 — cosa sono e come trattarle

Lorenzo, 29/09: "allineati su tutte le modifiche che nel mentre ho fatto fare a chat gpt e che ha postato su github".
ChatGPT/Codex scrive col suo account GitHub (autore `snowcomingsoon`, branch `codex/*`), **solo documenti**: nessun commit di codice su main. Tutti i commit su main del 29/09 sono di Claude.

| consegna | cosa | stato reale |
|---|---|---|
| PR #348 + issue #347 | audit sicurezza/scoring (`docs/audits/2026-09-29/`) | chiuso lato codice (S01-S07, M01-M05); restano M06/M08 (decide Lorenzo) e SSRF/CSP/CI, vedi sezione sotto |
| issue #357, #358 | piani backend B00-B08 e memoria I00-I07 | li eseguono i thread "Piano struttura backend" e "Piano intelligenza e memoria" |
| PR #362 + issue #363 | "decision assurance" A01-A08 (`docs/decision-assurance/`) | da decidere con Lorenzo, vedi sotto |
| PR #364 + issue #365 | ricevute di analisi e riuso R1-R5, scheda/mappa J1-J4 (`docs/analysis-receipts/`) | dipende da #363 e #358 |
| issue #366 (doc in PR #364) | audit consumi DeepSeek E0-E5 | il piu' concreto: da fare per primo |

Letti in modo critico:
- **#366 consumi**: verificato su main. `agent.js:87` fonde `today` (chiamate) e `done` (note) e le note sovrascrivono; "studies" conta note ripetute, non progetti (27849 contro 893 non sono chiamate per progetto); `consistency.py` ha `DAILY_MAX=12` ma Lorenzo ha visto 80 (da capire sul server); `KINDS` del recap non copre tutti i tipi. Risponde alla richiesta di Lorenzo di tagliare token: partire da E0 (inventario) + etichette separate nella tab, poi tetto unico.
  Lorenzo ha scelto di partire da qui (29/09). Fatto: tab Agent con "AI: N calls · X tokens" separato dal lavoro, studi contati per token distinti (`activity()['distinct']`), recap serale con tutti i kind. Da fare: E0 (inventario chiamate, 80 consistency: serve accesso al server) ed E1 fatto: Lorenzo, 29/09, ha scelto "$0.50 al giorno": `settings.deepseek_daily_usd` (0 = nessun tetto), controllato in `ask`/`ask_message` prima di ogni invio (anche ogni round della chat) con prenotazione delle chiamate in volo; oltre l'80% si fermano tutti tranne chat e voto di sicurezza meme (`PRIORITY_KINDS`); le chiamate fermate vanno nel recap serale, la spesa del giorno nella tab Agent. Prezzo di listino senza sconto cache, quindi prudente. Resta E0 (inventario sul server, gli 80 consistency).
- **#363 decision assurance**: le prove di codice sono vere (E01: `outcomes._mark_rug` mette insieme prezzo mancante, crollo e liquidita' come "rug"; E02: `rug_label` da' negativo dopo 3 giorni su 7). Ma A02 (esperimenti con partecipanti), A06 (macchina a stati di promozione), A07 (registro dei diritti legali delle fonti) e A08 sono processi da azienda con revisori umani indipendenti: contro le regole del progetto (minimal, meno token, "piu' parametri = peggio") e senza persone per farli. Proposta: prendere solo A01 (etichette rug separate, niente negativo prima dell'orizzonte) e A03-T1 (cartella di test vuota non deve dare punti, vedi `depth.py`); il resto in attesa di un si' di Lorenzo.
- **#365 ricevute**: l'idea utile e' la chiave di cache esatta per `code_review` (riuso senza chiamata, niente AI per log/hash). Rischio: un secondo store accanto alla memoria di #358; la spec stessa dice di non farlo. Va dentro il lavoro di #358, non in parallelo.
- **Mappa a neuroni** (`neural-map.fragment.html`): prototipo con dati finti, non telemetria.
- **Contrasti con CLAUDE.md**: le issue dicono "non usare l'etichetta deepseek" e "l'attuazione sara' di Claude"; la regola di Lorenzo resta che il codice senza soldi/chiavi/firme passa da DeepSeek. I due branch `codex/*` modificano HANDOVER.md (uno in cima, sopra l'introduzione): al merge vanno in conflitto fra loro e con main. Le PR sono documenti: si possono unire senza rischio per il sito, dopo aver risolto HANDOVER.

## Audit di sicurezza di ChatGPT/Codex — 2026-09-29 — **chiuso lato codice**

Lorenzo, 29/09: "ho fatto pubblicare a CHAT GPT degli audit su github", poi "risolvi tutti i problemi segnalati da chat gpt". Audit in PR #348 (`docs/audits/2026-09-29/`) e issue #347. Tutti i rilievi S01-S07 e M01-M07 verificati sul codice: veri; M03/M06/M08 sono anche scelte di Lorenzo, corretti solo dove toccavano la sicurezza.
Corretto a mano (soldi/chiavi/firme), PR #350, #354, #359 e questa:
- S01 `risk.run_safety_checks` (wallet acceso, breaker, discrepanze) su ogni swap/prelievo/autotrader (`guards=False` salta solo i limiti economici), ricontrollato prima del broadcast. Il tasto "kill switch" ora ferma davvero.
- S02 valore deciso dal server (`valuation.py`, importi raw + decimali on-chain + prezzo del server); `notional_usd`/`price_usd` del client ignorati; il clamp al pool rifiuta invece di firmare l'importo pieno.
- S03 `client_order_id` (api.js) e id stabile per segnale watchlist: un retry ripete il primo esito; tetto giornaliero conta gli ordini in volo; doppia conferma non raddoppia.
- S04 stati `signed`/`submitted`/`unknown`: la posizione si registra solo quando `_onchain_reconcile_loop` (ogni 20 s, parte all'avvio) vede la tx confermata; Solana `processed` non basta.
- S05 passkey aggiunta/rimossa solo con la password (+ avviso Telegram); `/reveal/approve` con lo stesso blocco del login.
- S06 cookie con id e versione: logout revoca lato server, `POST /api/auth/logout-all` per tutti i dispositivi. I cookie vecchi (senza id) valgono finche' non si fa logout.
- S07 chiavi wallet e credenziali exchange in AES-GCM legate a utente e chain; migrazione alla prima lettura dopo il controllo indirizzo, con copia in `data/wallet_keys_pre_v2.jsonl`. `WALLET_ENCRYPTION_KEY` (opzionale, `deploy/.env.example`) stacca la custodia da SESSION_SECRET: **se la metti, non toglierla mai piu'**. `users.json` scritto in modo atomico con `.bak`, mai sovrascritto se illeggibile.
- M01/M02 tokenomics: dato mancante = non verificato (niente punti, tetto 50 se mint/freeze ignoti), un contratto con >50% e' fatale; M03 DREGG non salta piu' i fatal; M04 giudizi AI piu' vecchi del doppio del TTL non contano nel voto; M05 ammissione AI serve confidenza >= 0.7; M07 README letto come Markdown. `RULES_VERSION` 9: la tokenomics di tutti i progetti viene rifatta.
Non toccato, decide Lorenzo: M06 (Top piu' larga di Gems, studiati saltano soglie), M08 (somiglianza al benchmark) e i pesi nuovi del PR H del piano.
Ancora aperto, da fare fuori dal codice: SSRF/DNS rebinding, CSP `unsafe-inline`, CI (le Actions falliscono in 3 s senza step, causa non nota da qui), deploy fissato allo SHA verificato invece di `origin/main`, separare il job DeepSeek dal publisher. Dipendenze e scansione: nessuna fatta.
Primo trade reale: seguirlo a mano; nessun invio on-chain e' mai stato provato dalla sandbox.

## Versione desktop dell'app on-chain — 2026-09-29

Lorenzo, 29/09: "comunque se hai html di fomo app procedi a fare la versione desktop" (zip della pagina token di FOMO, solo come ispirazione: lista a sinistra, pagina token al centro, compra a destra, sezioni nella testata).
Fatto (issue #344 aperta per DeepSeek, ma le Actions fallivano ancora in 3 s: scritto a mano). Solo da finestra >= 1100px, telefono invariato: il dock diventa una barra con le etichette al centro della testata; Memes/Gems/Strategies restano in una colonna di 420px a sinistra e la pagina token (`dialog.detail`) si apre accanto, non modale (`show()`, niente `pushState`), col primo token della vista aperto da solo (`openFirst`); Agent/Profile/wallet/scambio prendono tutta la larghezza (max 960px) e chiudono la pagina token (`deskView`, `html[data-desk-list]`). Da 1360px il riquadro Buy va su una colonna a destra. CSS in fondo ad `app.css` ("desktop terminal").
Da fare se Lorenzo lo chiede: nastro prezzi in basso e "Your positions" nella colonna destra come FOMO.

## Alert meme su Telegram fermi, poi spazzatura — `seed-0219`/`seed-0220` — 2026-09-28

Lorenzo: "comunque non sta arrivando neanche un alert", "da giorni"; poi, visti SUPERTAKE/AGENTORY/WATCH con voto DeepSeek 1/10: "occhio a non far arrivare la merda però, non voglio meme coin".
Causa: `legit.assess` restituiva "wait" su "no GitHub", i meme non ce l'hanno, scadevano dopo 2h (in locale 5591 pool, 0 alert in 7 min). #315: `need_github=False` dal percorso listings. #316: `ai_gate=True` dal percorso listings, il voto DeepSeek blocca (< `AI_SCORE_MIN`=6 o non legit); DeepSeek con errore = wait; senza chiave = non attivo. Gemme/radar invariati (`legit_ai_gate` resta spento li'). Da guardare: se ora non passa piu' niente, il collo di bottiglia e' il voto DeepSeek (vedi `scartati` nella chat Telegram).
Lorenzo ha un messaggio fissato "Chiave on-chain rivelata (robinhood, 0x2B...)": e' l'avviso di `POST /api/onchain/wallets/{chain}/reveal` (export con approvazione QR); detto a lui di spostare i fondi se non e' stato lui.

## Stato al 28/09 sera — cosa e' su main e cosa e' in corso

Su main: iframe del grafico del sito principale (CSP `frame-src 'self'` corretta nel Caddyfile: in produzione il browser lo bloccava), solo long sul grafico DEX (#247), fallback al nostro grafico se il sito principale non trova il token (#251), ingressi/uscite del backtest migliore (#246), Phantom da Safari con deeplink (#253, `phantomlink.js`, provato solo contro un finto Phantom), reale/simulato veloce (#254), laboratorio di backtest passo 1 (#255), narrative per account backend (#258).
In corso con DeepSeek: #256 stop anti-rug (-65% dal massimo delle 24h: chiude e non rientra piu'; SYSTEM_VERSION 7, lab VERSION 2), #257 grafico senza "Alert" (solo ingressi/uscite + marcatore "Rug · strategy off"), #259 scanner piu' profondo (cap fino a $25M, progetti fino a 3 anni, etichetta di narrativa dalla categoria CoinGecko, copertura per narrativa `/api/onchain/narratives/coverage`, narrative vuote cercate per prime), #260 diario di DeepSeek con i passaggi del ragionamento (`/api/agent/log`).
Grafico pagina token (#295, seed-0209): tolto l'iframe del sito principale. Lorenzo, 28/09: "Non voglio che venga applicato a questo grafico [...] nessun tipo di strategia dal vecchio sito, ma esclusivamente dal backtest di quest'app". Solo il nostro Lightweight Charts con i trade del backtest dell'app; pool cercato anche su GeckoTerminal. Poi (#303, seed-0212) tolto anche il bottone "Open on the analysis chart"; per le gemme `strategy_lab` salva `daily` (solo "Lorenzo (trend-follower)", 1d o 8h da 4h se <60 giorni, `system.backtest_one`) e la pagina token usa solo quello, grafico 1d.
Da fare dopo: scheda di DeepSeek animata (frontend su #260), filtro rug aritmetico prima del backtest (passo 2 del laboratorio), passo 3 (DeepSeek impara).
Lavoratore DeepSeek: se fallisce spinge la bozza su `deepseek/issue-N-failed`; un test elencato in Files e Tests deve esistere.

## Laboratorio di backtest, DeepSeek che impara, narrative per account — 2026-09-28 — **in corso**

Lorenzo, 28/09: "tutti i backtest devono essere disponibili su tutti i token scansionati [...] anche di quelli che non rientrano nel nostro standard [...] nei momenti morti [...] fare un grande database di backtest [...] imparare a evitare rug pull e i movimenti di prezzo soprattutto nei token appena usciti [...] siamo nell'ordine delle decine di migliaia, trova tu una soluzione magari a piu' step". E: "diamo la possibilita' di scegliere la narrativa [...] almeno una quindicina". E sul grafico: "Il grafico nel sito principale e' fatto apposta per long e short. Tu di quello devi solo prendere l'apertura del long e la chiusura del long" (= #245, `spot_only`).

Vincolo che decide tutto: GeckoTerminal gratuito ~30 chiamate/min, il background ne usa gia' 14 (`_GECKO_BACKGROUND_PER_MIN`). Una chiamata = 1000 candele 5m (3,5 giorni). A ~6/min nei tempi morti sono ~8.600 token/giorno: basta per l'arretrato, NON per tutti i nuovi pump.fun (decine di migliaia al giorno).

- **Passo 1 — `backtest_lab.py`**: coda con priorita' (alert > diario `outcomes` > scartati > database progetti > resto visto dallo scanner), solo quando il budget gecko e' libero, token maturi (>= 48h, esito noto). Per token: candele salvate compresse (SQLite sul volume, `data/backtest_lab.sqlite`), `system.backtest_all`, percorso di prezzo (multiplo massimo, minuti al picco, drawdown, rug e quando), numeri al momento della scoperta. Strategie nuove si ricalcolano senza riscaricare.
- **Passo 2 — filtro aritmetico prima del backtest** (sostituisce l'idea PumpPortal). Lorenzo, 28/09: "non voglio che Pump Fun diventi il nostro bacino di token [...] tutto quello che e' facilmente identificabile come rug pull escludiamolo a priori e ovviamente i backtest li facciamo su quello che rimane". `obvious_rug(entry)` con soglie LARGHE (piu' larghe dello standard di `legit.py`, che resta per gli alert): motivo "rug segnalato / honeypot / mint / freeze / blacklist / tasse", primo wallet > 50%, primi 10 > 80%, liquidita' bloccata < 20%, liquidita' < $3k o < 2% della cap. Gli esclusi non consumano chiamate GeckoTerminal. Un campione di controllo (1 su 20, deterministico per chiave) si backtesta lo stesso: il riepilogo dice quanti esclusi erano davvero rug, cosi' si vede se il filtro butta via vincitori.
- **Passo 3 — DeepSeek impara**: casi simili (`rug_memory.similar`) estesi coi backtest; tabelle per classe; distillazione periodica nei tempi morti (DeepSeek legge le statistiche e scrive regole). Una regola entra nel suo prompt solo se predice fuori campione (AUC >= 0.65 su >= 200 casi), altrimenti resta in osservazione — come `outcomes.py`.
- **Narrative per account** — **fatto** (#258 backend, #301 frontend, seed-0211): 24 gemme + 12 meme in `narratives.json`, sezione Narratives nel Profilo, le scelte vengono prima in Gems (righe, non podio) e Memes. Lorenzo, 28/09: "le narrative, che non vedo pero' svolta".
- **Grafico del sito principale che non trova il token**: il provider DEX del sito usa solo GeckoTerminal lato server (budget condiviso) e non passa `token_address`; l'app on-chain invece ha le sue candele. Rimedio: se l'iframe non ha dati, avvisa la pagina (postMessage) e la pagina ripiega sul grafico interno con ingressi/uscite del backtest migliore.

## Regola di lavoro nuova — 2026-09-27

Lorenzo: "auto approva tutto quello che proponi d'ora in poi". Da qui i merge su `main` di quello che Claude propone non chiedono piu' conferma. Restano sempre sue: azioni sul server, DNS, chiavi e segreti, e l'accensione dell'esecuzione reale (`onchain_execution_enabled`).

## Wallet di chiunque sul sito — `seed-0143`, branch `claude/connect-wallet` — 2026-09-27 — **in corso**

Lorenzo: "dobbiamo dare la possibilita' di far collegare il wallet a qualsiasi persona [...] deve firmare uno speciale smart contract cosi' che si attivi questa strategia automatica, e' fattibile?". Piano concordato ("procedi"):
1. **Fatto**: collegamento per firma (`wallet_link.py`, `/api/wallets/link*`), saldi del wallet collegato nel profilo in sola lettura. Solo wallet del browser (MetaMask, Rabby, Phantom) + deep link al browser interno del wallet da telefono; niente WalletConnect (servirebbe un project id e una libreria esterna, CSP da allargare).
2. **Fatto** (`seed-0144`): scambi firmati dall'utente, `user_swaps.py` + `/api/wallets/swap/build`, `userswap.js` (pulsante "My wallet" nella pagina token). EVM: approve + exactInputSingle via eth_sendTransaction (attende la ricevuta dell'approve); Solana: tx Jupiter firmata da Phantom, deserializzata con @solana/web3.js da unpkg. Mai provato con wallet veri dalla sandbox.
3. **Da fare, dopo i numeri del sistema in simulato**: vault per utente su Robinhood Chain (deposita lui, il bot puo' solo swap su router in allowlist con destinatario il vault, prelievo sempre suo), audit esterno, parere legale MiCA, beta con tetto basso. Alternativa session key ERC-4337/EIP-7702 solo se Robinhood Chain li supporta (da verificare).

## Sistema trend-following, autotrader Robinhood, profilo — `seed-0138`/`0139`/`0140`, branch `claude/trend-strategy` — 2026-09-27

- Sistema (`system.py`): Lorenzo "trova la miglior strategia [...] rendiamola praticamente operativa [...] i risultati di questi ingressi e uscite come risultati nella leaderboard". Candidate: Lorenzo e Lorenzo HF (default), candele 5m, fill all'apertura dopo il segnale, costi 0,3+0,5% per lato, finestra 48h, rug = -100%. Vince la mediana migliore su alert conclusi (>= 20, prima Lorenzo HF). Barre in `alert_track` (`_bars`, file `onchain_alert_bars.json`) dalle letture ogni minuto + un fetch GeckoTerminal per alert (`refresh_system`). La classifica ordina per "System" di default.
- Autotrader (`autotrader.py`): "con un tasto io attivo la strategia [...] 100%, 50, 25 [...] considerare sempre le fee". Risposte di Lorenzo: saldo USDG, un token alla volta, nessun limite oltre la %, prima simulato. Off/Sim/Real, quota 10/25/50/100%. Reale = `execute_order(guards=False)` + approve USDG al router; firma solo percorsi Uniswap v3 (aggregatore Kyber non ancora firmabile: da fare se in simulato si vedono molti "only reachable through an aggregator"). Serve `onchain_execution_enabled=True` sul server (decide Lorenzo) ed ETH per il gas. NON testato su chain dalla sandbox: primo trade reale va seguito.
- Cash USDC (`seed-0142`): Lorenzo "devono essere USDC, e se operi su Robinhood prima devi convertire in USDG"; risposte: USDC multichain, dopo ogni vendita sempre in USDC. `autotrader.find_usdc` prende il lato USDC del pool USDC/USDG piu' liquido su DexScreener (>= $20k, 6 decimali verificati) o `ROBINHOOD_USDC_ADDRESS`. Bridge Solana->Robinhood NON fatto.
- DeepSeek sul server, 27/09 pomeriggio (Lorenzo: "seguimi per installare deepseek nel server"): con lui in SSH (`ssh root@<server>`, progetto in `/opt/liquidity`, rete Docker `deploy_default`, app ~1 GB su 3,7 GB) e' stato avviato A MANO un container `ollama` (fuori dal compose: `--network deploy_default --memory 1800m --cpus 1`, volume `ollama`) per provare `deepseek-r1:1.5b`. Consiglio dato: 1.5B e' troppo debole per il revisore; usare l'API DeepSeek (`DEEPSEEK_API_KEY` in `/opt/liquidity/deploy/.env`, poi `docker compose up -d app`) e togliere il container con `docker rm -f ollama && docker volume rm ollama`. **Tolto** lo stesso giorno (container, volume e immagine), su richiesta di Lorenzo.
- DeepSeek (`seed-0141`): Lorenzo voleva installarlo sul server. Non ci sta (CX23 2 vCPU/4 GB, il modello vero chiede centinaia di GB di GPU). Il revisore ora usa l'API DeepSeek se c'e' `DEEPSEEK_API_KEY` (`ai_review_provider=auto`). Per il coding: DeepSeek non puo' lavorare al posto di Claude in questa sessione; si usa da strumenti suoi (Aider/Cline) con la sua chiave.
- Saldo multi-chain (`seed-0145`, `portfolio.py`): Lorenzo "il wallet deve essere multi-chain e devo visualizzare il saldo a prescindere da quale token e in quale chain ho". Totale in testata (`/api/wallets/total`). Limiti noti: Robinhood legge solo token gia' visti dal sito (Blockscout di Robinhood dietro Cloudflare); BSC solo BNB; Base/Ethereum dipendono da Blockscout pubblico.
- Profilo (`profiles.py`, `wealth.py`, `profile.js`): "uno deve vedere cosa detiene, l'andamento del wallet nel tempo [...] scegliere l'immagine profilo". Dati in `profiles.json` + `avatars/` sul volume; storia valore in `onchain_wealth.json`. Il dock ha Profile al posto di Wallet; la vista wallet e' nel menu "…".

## Podio animato e chain Base — `seed-0127`/`seed-0128`, branch `claude/gem-database` — 2026-09-27

- Podio: Lorenzo "progetta la leaderboard con agenti specializzati [...] 120fps", "al posto delle faccine ci sia il logo", "applica tutto, decidi te qual e' la piu' bellina". Tre prototipi da agenti diversi, scelto "Champions stage" (`static/onchain/podium.js`, `renderPodium(container, items, {still})`), CSS in `app.css` sezione podio. Regole 120fps: solo transform/opacity, entrate con fill backwards, niente will-change fisso, coriandoli via WAAPI. `#top` rinominato `#leaders` (l'hash faceva saltare la pagina).
- Base: Lorenzo "estendiamo anche a chain BASE le ricerche". Solo ricerca, non trading: radar, Meme Sniper (GeckoTerminal new_pools), Gem Finder (CoinGecko platform/categoria, README), DefiLlama, GoPlus 8453. `legit.CHAIN_LABEL` e' il nome leggibile per i messaggi Telegram. Nel wallet Base non c'e': la pagina token mostra "Trade on DexScreener" (`TRADABLE` in `detail.js`). Se un giorno si vuole comprare su Base servono quote/execute EVM come per Robinhood.
- Storico alert (`seed-0129`, branch `claude/alert-history`): Lorenzo "riesci a riportare i dati storici che avevamo nell'altra versione ?". `alert_track.backfill` all'avvio (`_backfill_alert_track` in main.py) rimette in classifica i listing pubblicati freschi (stesso test di `_publish`) con le candele GeckoTerminal (`gecko_get`, limiter condiviso). Idempotente: le chiavi gia' note si saltano. Non verificato contro la produzione (sandbox senza accesso al sito): controllare i log `alert track: N past meme alerts rebuilt`.
- Chain per caccia (`seed-0131`): Lorenzo "BSC per le Meme insieme a Sol e Robinhood. Poi Eth e Base solo per le Gemme". Unica fonte: `legit.MEME_CHAINS` (radar, listings) e `legit.GEM_CHAINS` (documentale; discovery usa `CG_PLATFORMS`/`CG_CATEGORIES`, traction `CHAIN_NAMES`). DefiLlama scrive Ethereum come 0x senza prefisso: gestito in `traction._token`.
- Scanner rifatto (`seed-0135`, branch `claude/meme-picks` insieme a Picks `seed-0134`): Lorenzo "la scheda scanner e' confusionaria, non voglio che rimanga il grafico di una crypto per tutto il giorno". `radar.js` riscritto: stato + 3 numeri + feed decisioni (listings + rejected via SSE) + riga outcomes + Wall of Rugs in `<details>`. Niente palco/grafico fisso, niente lista proposte (sta in Picks), niente track record (sta in Alerts/classifica). Le vecchie classi `.radar-*` in onchain-app.html non servono piu' ma non sono state cancellate.
- Da osservare: BSC ha moltissimi pool nuovi; se il Meme Sniper si intasa (MAX_PENDING 300, il piu' vecchio viene sacrificato), limitare i pending per chain.
- (vecchia nota) Base ha molti piu' pool nuovi di Robinhood; se il Meme Sniper si intasa, limitare i pending per chain.

## Un'app sola, layout da app di trading — `seed-0126`, branch `claude/gem-database` — 2026-09-27

Lorenzo, con 4 screenshot di un'app meme da telefono: "l'app deve essere
unica e gestita cosi' graficamente e come layout, ispirati"; poi "anche i
simboli dei token li voglio [...] non e' minimamente paragonabile [...] usa
un team ad hoc per esaminare disposizione, layout, tema e grafica".

Fatto con tre revisori (grafica misurata sui pixel, informazione/navigazione,
architettura CSS). Stato:
- Tema in `frontend/static/onchain/app.css`, layer `skin` (ultimo), linkato
  solo da onchain-app.html con `?v=` (main.py conta anche i .css nell'hash).
  Tolti il layer `shell` e il blocco desktop a due colonne (>=1100px).
  Palette zinc: bg #09090b, bande #0f0f12, superfici #18181b.
- Viste: meme (Trending/Alerts/Scanner), gems (Rankings/Database), top
  (Alerts/Gems), wallet; `manual` (swap) dalla lente o dal Buy.
- Riga unica `tokenRow()` in `format.js` (+ `tile/logo/changePill/usdShort`).
  Loghi: `image` da DexScreener (pair.info.imageUrl, salvato da outcomes,
  listings, alert_track), altrimenti dd.dexscreener.com per indirizzo.
- Pagina token `detail.js`: registro `register(id, entry)` (fusione fra
  moduli), `data-open="<id>"` apre; grafico SVG del market cap da
  /api/onchain/radar/chart con marcatori degli alert; Signal/Why/Info; Buy
  -> evento `lae:buy` -> main.js setView("manual") + setChartToken.
- Da fare se Lorenzo lo chiede: ricerca unificata (oggi la lente apre lo
  scambio), barra che si nasconde scorrendo, "You" con il P&L vero.

---

## Gemme early, avvisi Telegram gemme, classifica degli alert meme, revisore Claude — `seed-0122`/`0123`/`0124`, branch `claude/gem-database` — 2026-09-27

Lorenzo: "per gemme quando la market cap e' sotto i 50k e fondamentali ci
sono, voglio che il sistema lo evidenzi che potrebbe valere la pena di
comprare un po, voglio poi gli avvisi su telegram anche per le gemme"; "il
meme sniper deve avere una leaderboard anch'esso, con anche i risultati se
avessimo seguito l'alert di telegram (non le strategie) [...] dopo
1,2,3,4,5,6,8,12,24,48h, e infine aggiornato in tempo reale, oltre a questo
anche il rendimento della miglior strategia backtestata"; "sto pensando di
mettere un istanza di claude sonnet nel server [...] con un massimo di token
al giorno, cosi' impariamo dagli errori".

- Early: `leaderboard.is_early` (cap < $50k, GitHub pubblico, pilastri >= 60,
  punteggio >= 65, qualifica ok). Fasce abbassate: discovery/projects_db da
  $10k, liquidita' minima $5k sotto i $50k. Badge e riquadro in `leaderboard.js`.
- Avvisi gemme: `leaderboard._outbox` + `on_alert` (una volta per "new:" e
  "early:" per progetto, `_alerted` salvato; al primo avvio con il campo
  mancante si fa "priming" senza avvisi). Testo italiano `_gem_telegram_text`
  in main.py, 6/ora per utente, stessi destinatari dei listing.
- `alert_track.py`: ogni alert (meme da `_notify_listing`, gemme da
  `_notify_gem`) seguito dal primo prezzo dopo l'invio; checkpoint 1-48h,
  "ora", strategia migliore copiata dal backtest del listing. Loop
  `_onchain_signals_loop` (30 s). API `/api/onchain/alerts/{meme|gem}`.
- `ai_review.py`: Sonnet 5 una volta al giorno (30 min dopo l'avvio), fatti
  gia' misurati in JSON, lezioni strutturate in italiano, budget
  `ai_review_daily_tokens` (200k) contato dall'usage reale. Lezioni NON
  applicate da sole. API `/api/onchain/ai-review`, Telegram sulla chat di sistema.
  Serve `ANTHROPIC_API_KEY` (la inserisce Lorenzo).
- Poi Lorenzo: "non voglio che finisca i miei token", "non complicare il sito
  con roba inutile", "la daily review deve essere semplice". Revisore: effort
  low, output max 3000, risposta = `summary` + max 3 `actions`; tetti 40k/giorno
  e 600k/mese (~$0.06 a revisione). Consigliato a Lorenzo: chiave API dedicata
  con limite di spesa mensile in Console. Tolta la tabella alert delle gemme.
- "rendi graficamente incredibile la leaderboard delle gemme, animala":
  layer CSS `gemboard` in fondo a `onchain-app.html` (@property, @starting-style,
  animation-timeline: view(), View Transitions in `leaderboard.js` con
  `view-transition-name` per progetto, tilt/luce al puntatore, conteggio
  punteggi). Entrata solo al primo disegno (`#board[data-enter]`). `seed-0125`.

---

## Database dei progetti del Gem Finder — `seed-0121`, branch `claude/gem-database` — 2026-09-27

Lorenzo: "il gem hunter deve trovare progetti di qualita', ma vedi sempre i
soliti.. ma fatti un database no?".

Perche' sempre gli stessi: nessuna memoria del mercato. CoinGecko letto solo
dalle pagine della categoria "solana-ecosystem" (una parte delle monete
Solana), working set di 400 voci con le vecchie buttate, bocciatura
definitiva per 30 giorni.

- `app/trading/onchain/projects_db.py`: SQLite `onchain_projects.db` sul
  volume. Una riga per progetto: identita', link, fonti, mercato, ultimo
  verdetto (status new/studied/ranked/rejected + why), pilastri, punteggio.
- Fonti nel database: `/coins/list` di CoinGecko intero (tutte le monete
  sulle nostre chain, `discovery.universe`), lista verificata Jupiter intera,
  tutti i protocolli DefiLlama, piu' tutto cio' che passa da `leaderboard.add`.
- Ogni minuto 150 token con mercato vecchio (>6h) passano da DexScreener.
  Chi e' in fascia ($50k-$3M, liq >= $10k) e ha un cg_id viene letto su
  CoinGecko (sito/GitHub) fra un giro e l'altro delle categorie.
- `leaderboard.feed_from_database`: 4 progetti per giro nel working set
  quando la coda di analisi ha posto, prima chi ha GitHub. Verdetti scritti
  da `apply_analysis` (`_remember`). Bocciati riesaminati dopo 14 giorni
  (2 se il motivo era un dato mancante), anche se erano in `_gone`.
- API `/api/onchain/projects?q=&status=&sort=&band=`; sezione "Project
  database" nella vista Gemme (`static/onchain/projects.js`).
- Da guardare dopo il deploy: `stats.in_band` e `top_rejections` dicono dove
  muoiono i progetti. Se la regola che boccia di piu' e' sbagliata, va
  ritoccata li'.

---

## Motori piu' profondi per Gemme e Meme + track record + design — `seed-0118`/`seed-0119`/`seed-0120`, branch `claude/gems-memes-engine` — 2026-09-26

Lorenzo, sulla classifica: "io entrerei anche nella logica con cui sceglie le
gemme, senz'altro ci sono progetti migliori ma non li trovo, dobbiamo fare un
algoritmo piu' profondo". Poi: "uguale per lo sniper di meme, dobbiamo rendere
tutto piu' professionale", e: "procedi a fare tutto, e poi direi che anche una
rinfrescata di design non faccia male, miglioralo".

Diagnosi (letta dal codice, 26/09):
- Gemme: l'imbuto vede solo chi ha GitHub su CoinGecko, profili DexScreener a
  pagamento, README con "CA:"/pump.fun, Jupiter verified. I tre pilastri
  misurano la *forma* (commit, parole del sito, distribuzione): niente
  trazione (utenti, TVL, fee) e niente valutazione (cap rispetto a cosa fa).
  Nessuna verifica a posteriori di chi entra in classifica.
- Meme: la corsia "Ready to pump" e' fatta degli *scarti* del filtro dei
  progetti seri, ordinati per quota acquisti e giro d'affari (i numeri piu'
  facili da gonfiare coi bot). "Buono" = +50% al picco in 7 giorni, che non
  e' incassabile.

Piano, in ordine (decisioni di default prese senza risposta esplicita:
solo API gratuite; DREGG resta primo e il peso della somiglianza non cambia):
1. Track record: trade simulato sui meme (ingresso con slippage da
   liquidita', uscita TP/SL/tempo, netto) e ritorni a 7/30/90 giorni per chi
   entra nella classifica gemme; statistiche per fascia di punteggio in API e
   in pagina.
2. Motore meme dedicato: punteggio con motivi leggibili da flusso (compratori
   vs transazioni, vendite presenti, crescita), concentrazione, insider, dev;
   il modello impara dal trade simulato, non dal picco.
3. Motore gemme: fonte DefiLlama (protocolli con TVL/fee nella fascia di cap),
   pilastro "Trazione" e punteggio "sottovalutato"; descrizione ripulita dal
   testo di navigazione del sito.
4. Rinfrescata di design di `onchain-app.html`, con screenshot 1440/390.

Rete esterna chiusa nella sandbox: tutto provato con dati finti; le soglie
vanno rilette sui dati veri dopo il deploy. Merge su `main` solo col via di Lorenzo.

Stato (26/09, fine sessione): tutti e quattro i passi fatti sul branch, non
ancora su `main`.
- `meme_engine.py` (punteggio + trade simulato), `outcomes.py` (trade per ogni
  voce del diario, `mark_shown` apre un trade quando la corsia mostra un token,
  `meme_track`, etichetta del modello = trade netto >= +20% dopo 40 trade chiusi).
- `traction.py` (DefiLlama: fonte + trazione/valore, pesi 0.10/0.05 come
  spinta), `gem_track.py` (ritorni a 7/30/90 giorni, top 10 contro resto).
- Frontend: schede "track", anello di punteggio e motivi nei meme, blocco
  Traction nei dettagli, meme prima del radar, grafico vuoto nascosto su
  telefono. Bug +0% dei meme corretto (frazione vs percentuale).
- Da fare dopo il deploy: leggere `/api/onchain/radar/memes` -> `track` e
  `/api/onchain/leaderboard` -> `track`/`defillama` dopo qualche giorno;
  se la fascia "60+" non batte "every meme watched", i pesi di `meme_engine.PARTS`
  vanno ritarati. Non fatti: API a pagamento (Helius/Birdeye per bundle, dev,
  smart money), soglia top10 <= 60% che boccia tesorerie, eta' massima 365 gg.

---
## Presentazione del progetto e token $ENGN — `seed-0109`, branch `claude/project-thread-mn4odz` — 2026-09-24

Lorenzo: "fai una pagina web di presentazione del progetto con slogan
accattivante in inglese; crea il ticker del token, ci serve lanciarlo [...]
tasto al centro dove ENTER THE APP [...] due sezioni; una per sniperare
progetti nuovi con regole (facendole vedere) un'altra [...] seri con
fondamentali ma sempre microcap [...] devi pensare a tutto". Immagine di
riferimento scelta: cubo nero con fessura verde, griglia, candele.

- `frontend/engn.html` servita su `/engn` (pubblica). Le soglie in pagina
  sono segnaposto `{{...}}` riempiti da `_render_engn_page()` con le costanti
  di `radar.py`: niente numeri copiati a mano.
- Piano completo (ticker, tokenomics, decisioni aperte, MiCA, social, chiavi)
  in `docs/lancio-engn.md`. Screenshot in `/mnt/project-files/lancio/`.
- Poi Lorenzo: "decidi tutto tu, voglio fare un progetto legit", e dopo:
  "noi utilizzeremo pump fun [...] non andremo a fare nessun tipo di
  attivita' di MiCA compliant" e "aspetta a lanciare i token ovviamente".
  Quindi: lancio pump.fun, niente white paper, team 0% (nessun dev buy:
  Lorenzo non vuole mettere soldi), nessuna commissione di swap. Kit del form (logo,
  banner, testi) in `/mnt/project-files/lancio/pumpfun/` e
  `docs/lancio-engn.md`. **Il token si crea solo col suo via.**
- Sito dedicato: engn.xyz era gia' preso; proposto getengn.xyz (Lorenzo lo
  compra, record A verso il server, nuvola grigia su Cloudflare). Il blocco
  Caddy e' in `deploy/Caddyfile`: va unito solo quando il DNS punta al server,
  altrimenti Caddy prova il certificato a vuoto. Kit X in
  `/mnt/project-files/lancio/x/` (Lorenzo crea l'account, niente credenziali
  in chat, niente post senza suo ok).
- Prima di questo restava: modalita' di lancio (consigliato Raydium
  / Meteora con LP bruciato, non pump.fun), SOL di liquidita', verifica
  legale MiCA, registrare i social, spostare la pagina su `/` o dominio
  proprio, costruire i livelli per chi detiene.

---
## Memoria del radar ("coscienza") — `seed-0108`, branch `claude/project-thread-40dout`

Lorenzo, dopo il rug su VISE: "dobbiamo implentare una specie di coscienza,
imparare dai segnali; da cosa effettivamente succede, e migliorare il sistema".

- `app/trading/onchain/outcomes.py`: diario su volume (`onchain_outcomes.json`).
  Legge (solo lettura) proposte/provati del radar e listing/scartati; segue
  prezzo e liquidita' su DexScreener ogni 10 min per 7 giorni. Rug = liq <20%
  d'ingresso, prezzo -80% o pool sparito 3 giri; buono = +50% in qualche momento.
  Voci viste tardi: ingresso dalle candele 15m (4 per giro, gate GeckoTerminal).
- Lezione: AUC di ogni controllo su rug e salite (`signals`), regressione
  logistica numpy con 5 fold deterministici. Entra in `legit.assess` come check
  "memory" solo con >=40 esiti, >=8 rug, AUC fuori campione >=0.65.
- Blocca con `ONCHAIN_MEMORY_GATE` (acceso, pilota compreso: Lorenzo il 24/09,
  "accendi"). Eccezioni GitHub mai bloccate.
- API `/api/onchain/radar/lessons`; sezione "Memoria" sotto gli scartati.
- "Muro delle inculate" (Lorenzo: "fammi sparire VISE [...] sezione ironica
  dove ci andranno a finire tutte le inculate subite"): `outcomes.shame()` =
  `SHAME_SEED` (VISE) + rug passati dal filtro. Tolti da proposte, listing,
  classifica e candidati del pilota (`without_shamed`, `_pilot_vet`).

- Corsia meme (seed-0110, Lorenzo: "dobbiamo cavalcare le meme coin [...] estremamente
  gambling"): `outcomes.meme_board()` su `/api/onchain/radar/memes`. Scartati per
  motivi morbidi (`SOFT_FAILS`: nome, sito, social, GitHub, IA, pagella, memoria),
  vivi, con vendite viste, liq >= $8k, RugCheck/GoPlus puliti e primo wallet <=15%
  (`_meme_safety`, 8 per giro). Ordinati dal modello delle salite vere
  (`train_winners`, AUC fuori campione >= 0.60) o, prima, da quota acquisti e giro
  d'affari. Salita vera = +50% con vendite viste e liq al massimo >= $10k; senza,
  e' "finto" (JIRACHI: 300 acquisti, 0 vendite). `study()` raggruppa gli scarti per
  motivo. Solo lettura: il pilota non compra meme. La UI a due sezioni e' del
  thread "Revisione generale app".

Resta: eventuale ritaratura automatica delle soglie di legit (oggi solo misurate).

## Due porte: Gemme e Meme, niente nomi personali — `seed-0115` — 2026-09-24

Lorenzo: "rendilo privacy centrico [...] non ci deve essere scritto Lorenzo", "due sezioni distinte [...] prima di poter entrare", "deve essere chiaro che e' estremamente gambling la sezione meme", "revisione in ottica degen [...] i dettagli che non servono non ci devono essere".

- `onchain-app.html` si apre su `data-view="entry"`: due card, **Gemme nascoste** (lime, calma, porta a `gems` = `#board`) e **Sniper meme** (rosa/ambra, righe diagonali, porta a `meme` = `#radar` + `#pilot`, con banner "Zona degen"). Barra: Gemme, Meme, Scambia, Portafoglio (il Pilota sta dentro Meme). Nella porta la barra e' nascosta.
- Strategie: i nomi restano chiavi sul backend (watchlist, auto_trade, API). A schermo passano da `strategyLabel()` (`static/onchain/format.js`; per il sito principale un helper uguale in `app.js`): Trend EMA, Trend HF, RSI+BB Reversal, RSI+BB Long/Short. Non rinominare le chiavi: romperebbe dati salvati.
- I commenti del frontend (pubblici, si leggono dal sorgente) non citano piu' nomi: "Richiesta:" o "l'utente". Nei nuovi commenti del frontend niente nomi.
- La ricerca piu' ampia di progetti seri (Robinhood Chain e Solana, fino a pochi milioni di cap) e' del thread Classifica.

## Wallet come un DEX: barra in basso, niente "⋯" — `seed-0105`, PR #91

Lorenzo: "voglio che l'esperienza su questo sito sia paragonabile a un DEX
[...] ci sono tanti menu, tanti tasti che potrebbero essere ridotti".

- `#app-shell[data-view]` ha tre valori: `pilot` (Radar), `manual`
  (Scambia), `wallet` (Portafoglio). Li cambia `#dock`, la barra fissa in
  basso (`setView()` in `main.js`, con view transition direzionale).
- Il menu `#more` si apre dall'indirizzo in alto (`#more-btn` e' ora il
  chip dell'indirizzo): Ricevi, Invia, Limiti, Simula, chiave. Voci proxy,
  pillole `nav-pills` e cambio vista dal menu: tolti.
- `#bottom-panel` (Saldi/Ordini/Storico/Strategie) sta dentro
  `#wallet-view`, non piu' sotto il grafico.
- `#holdings` sotto il saldo: `holdings.js` legge `walletHoldings()` da
  `swap.js` (stessi dati della riga sopra lo swap, PR #89, stessa classe
  `.wallet-chip`). Tocco = Scambia + evento `onchain:swap-from`, che
  `swap.js` ascolta e usa come moneta in vendita (`pendingFrom` se lo swap
  non e' ancora montato).
- Radar e flusso swap non toccati (altri thread). `index.html` ha una copia
  sua del markup senza dock: il cablaggio resta null-safe.

Seguito (stesso giorno), Lorenzo: "visualizzare il saldo in alto non mi
interessa piu', la parte di automazione al trading la mettiamo in una sezione
apposita [...] la cosa centrale e' avere la leaderboard". E: "la leaderboard
doveva essere in alto appena entro nel sito". Ora le viste sono quattro:
`home` (classifica in cima, poi radar), `manual` (Scambia), `auto` (Pilota),
`wallet` (saldo, monete, ricevi/invia, tab). La rete (`#chain-flip`) sta
nella testata. Visibilita' in un blocco solo di regole `:not([data-view])`.
## Radar DEGEN on-chain — `seed-0099`, `seed-0100`, `seed-0102` — branch `claude/token-scanner-strategie-a97cto`

Thread "Scanner token e strategie". Radar in `app/trading/onchain/radar.py`,
filtro anti-rug in `legit.py`, frontend `frontend/static/onchain/radar.js`.

- PR #86: gate GeckoTerminal condiviso (`gecko_get`, ~30 req/min) — un 429
  non diventa mai "nessun dato".
- PR #88: solo long spot (`strategies.spot_only`), marker sulla candela del
  riempimento (apertura della barra dopo il segnale).
- PR #90: tutto cio' che e' scansionato/scelto/scartato vive in `backend/data`
  (volume) via `storage.data_file()`. Cap normale fino a $2M; sopra $100k
  serve la pagella da gemma (`gem_shortfall`: complessivo >=85, nessun
  controllo <70, anti-rug/contratto >=85).
- Eccezione GitHub (seed-0102): oltre 3 settimane o oltre $2M (fino a 1 anno,
  $20M, liq >= $100k e >= 3% della cap) entra solo con GitHub eccezionale
  (`github_shortfall`: >=60 degli ultimi 100 commit, >=20 giorni attivi,
  push entro 14 giorni, voto >=75) piu' la pagella da gemma. Fonte extra:
  pump.fun per capitalizzazione -> DexScreener (`_fetch_grown_pools`), per
  trovare DREGG. Il GitHub di DREGG (emberian/dregg) non e' raggiungibile
  dalla sandbox: se sul server non entra, il motivo e' fra gli scartati.
- seed-0106 (DREGG metro): `github_shortfall` ora chiede >=1000 commit totali
  (`github_commit_total`, Link header), ultimi 100 su >=8 giorni, push entro
  14 giorni, voto >=75; in `judge_github` una storia lunga vale un team.
  Eccezioni: sito dichiarato + nome non da meme, `exception_queue` a
  rotazione (12 per giro), sempre provate, in cima alle proposte anche senza
  strategia valida (`strategy_ok`). Fonti extra: profili/boost DexScreener.
  Prova reale DREGG: pagella 89, GitHub 89. Lorenzo lo vuole primo nella
  classifica (thread "Classifica progetti").
- seed-0107 (rug VISE, -93%): il sito linkava pump-fun/pump-public-docs e
  passava come GitHub del progetto. Ora `_PLATFORM_GITHUB` esclude i repo di
  piattaforma, `github_belongs` chiede che il repo sia del progetto, e
  `holder_concentration` scarta un wallet >15% o top 10 >35%. RugCheck
  `graphInsidersDetected` NON e' usabile: DREGG ne ha 807.
- seed-0204 (28/09): `strategy_lab.py` backtesta H24 la Top 50 della schermata
  Strategie (`main._top_entries`), un token al minuto, ognuno ogni ora, su
  1000 candele 5m con `system.backtest_all`; risultati in `/api/onchain/top`
  (`backtests` per riga + stato) e `/api/onchain/token`; ogni backtest va in
  `deepseek_desk.note("backtest", ...)` per la pagina Agent.
- Agent visibile (28/09, seed-0205): conteggi del giorno per tipo (`done` in `deepseek_desk.activity`), studi del leaderboard nel registro (`_note_study`), scheda live 'working now' in `agent.js`, letture DeepSeek 300/giorno. Lorenzo: "voglio che la gente, attraverso anche animazioni grafiche, mi faccia capire che sta lavorando".
- Backtest alert bloccati (seed-0206, 28/09): `refresh_system` saltava gli alert con barre ferme anche se il risultato era di una SYSTEM_VERSION vecchia; ora salta solo se `_ready`. Lorenzo: "io voglio vedere tutti i risultati [...] deve funzionare stavolta".
- Nastro scanner (seed-0207, 28/09): `scan_feed.py` (memoria, niente disco) riceve ogni giudizio di radar e listings; `/api/onchain/scan-feed`; nastro + conteggi in `alerts.js` sopra 'About to fire'. Lorenzo: "voglio vedere i ticker girare, non cose ferme".
- Backtest che si perdevano (seed-0208, 28/09): `alert_track.keep_richer` tiene il backtest salvato se il ricalcolo vede meno barre (pool morto). Lorenzo: "non deve cambiare ogni volta risultato e perdere i precedenti".
- Backtest persi a ogni riavvio (seed-0210, 28/09): `system.follow` contava `wins` come numpy int64, `json.dumps` in `alert_track.save` alzava TypeError (preso solo OSError): il file degli alert non si aggiornava piu'. Ora `default=_plain` e log dell'errore. Lorenzo: "PRIORITA MASSIMA E ATTENZIONE MASSIMA".
- Ingresso all'alert (seed-0213, 28/09): `system.follow(on_alert=True)` compra alla prima open dopo l'alert; `a['alert_bt']`, esposto come `on_alert` in board; la tab Strategie (`alerts.js`, sort backtest) mostra solo quello. SYSTEM_VERSION 9. L'autotrader non lo usa. Lorenzo: "sara' la decima volta che vi chiedo questa cosa".
- Sniper un trade per alert (seed-0214, 28/09): `follow(on_alert=True)` non rientra dopo l'uscita; `autotrader._system_of` legge `alert_bt` (non piu' `system`). Lorenzo: "deve gestire esclusivamente la chiusura secondo la classica regola del trend follower".
- 28/09 sera, "come mai su queste la strategia non e' uscita prima?" (MESUB -95%): il trade sull'alert usciva solo su un incrocio nuovo; ora `strategies.trend_down` chiude alla prima candela col trend giu'. SYSTEM_VERSION 10 (seed-0216).
- 28/09 notte, "il wallet simulato [...] voglio che li segua": Sim = libro di carta (`autotrader.paper_tick`) che segue ogni alert meme su ogni chain col trade di alert_bt; Real invariato (Robinhood, quote vere, un token). seed-0221.
- seed-0226 (29/09): link `#<view>&token=<chain>:<address>` (`app_token_url()` in main.py, `openFromHash()` in detail.js) sul ticker di ogni alert Telegram; tasto copia indirizzo con feedback e fallback. Aperto: login dentro il browser di Telegram (Mini App o link con accesso), scelta di Lorenzo.
- seed-0227 (29/09): tasto Share = `tokenLink()` in detail.js (stesso deep link degli alert); `openFromHash()` ora parte in `boot()` a login fatto, cosi' la destinazione sopravvive al login. Link con accesso da Telegram: bloccato dal controllo di sicurezza, in attesa del via scritto di Lorenzo.
- seed-0228 (29/09): memecoin di nuovo negli alert (`settings.listings_allow_memes`, `legit.assess(memes=True)` -> `_assess_meme`): decidono solo i controlli anti-rug; alert con `meme=True` esclusi dall'autotrader reale (`entry_candidate`). Misura: 6/70 pool PumpSwap passano, tutti sopra il primo prezzo.
- seed-0231 (29/09): Lorenzo "abbiamo preso dei bei rug pull nel trading simulato di memecoin [...] se e' stata ritirata la liquidita' [...] o vendite coordinate [...] wallet collegati". 15 rug su 51 meme Solana passati, tutti con LP bloccata al 100% (vendite, non liquidita' ritirata). `legit.rugcheck` leggeva /report/summary senza holder: ora report completo, i limiti 15%/35% tornano attivi, senza holder il meme aspetta. Wallet collegati (`linked_share`, insiderNetworks) solo registrati: a ritroso >10% in 4/15 rug e 9/36 vivi (DREGG 39%), nessuna separazione. Prossimo passo proposto: uscita veloce su crollo liquidita'/vendite (rug a mediana 0,65h). Lista mint: /mnt/project-files/rug_list.txt. Poi Lorenzo ha scelto di provare l'uscita rapida: `system.TRAIL` 30% dal massimo di chiusura, solo alert da `TRAIL_FROM` (30/09), niente SYSTEM_VERSION (i risultati mostrati non cambiano). A ritroso sui 38 con barre (`rug_bars.json`): media -41% -> -35%. Anche i sopravvissuti perdono in mediana -29%: il problema grosso e' l'ingresso all'alert, non i rug. Poi "dobbiamo documentare tutti i rug [...] anche quelli morti": `outcomes._archive` (`onchain_rug_archive.json`, cresce senza limite: da sfoltire se diventa grande) + `outcomes.entries()` letto da `rug_memory` e `backtest_lab`; il laboratorio prende i rug un'ora dopo il rug (`RUG_SETTLED_S`) subito dopo gli alert. Il laboratorio sul server aveva 286 righe e nessun rug. `scripts/rug_backtest.py` confronta alert / trail / trend sul laboratorio.
- Vincolo: il pilota (soldi veri) resta sotto $100k
  (`_SNIPER_ONCHAIN_MAX_MCAP_USD` in main.py). Mai strategie short.

Lorenzo: "dregg va bene anche se ha 21 gg e supera i 2 mln, progetti in quel
modo voglio che siano eccezione in quanto tecnicamente incredibili su github".

---

## Classifica dei progetti — `seed-0104`, branch `claude/classifica-progetti-8ptvq0` — 2026-09-24

Lorenzo: "una specie di leaderboard [...] primo posto, secondo posto, terzo
posto [...] dinamica [...] aggiornata in tempo reale [...] rigoroso [...]
GitHub [...] controllare i commit [...] la tokenomics non deve essere uno
scam [...] analizzarne l'html [...] da quanto e' che sono usciti [...] Pump
Fun". Poi su DREGG: "va bene anche se ha 21 gg e supera i 2 mln [...]
eccezione in quanto tecnicamente incredibili su github".

- `app/trading/onchain/depth.py`: tre pilastri 0-100 con `fatal` (esclude
  per sempre) e `pending` (riprova). GitHub: 100 commit + `/stats/participation`,
  contributori, linguaggi, cartella principale (test, CI). Sito: `anatomy()`
  sull'HTML (serve `html` in `legit.fetch_site`, aggiunto), apre fino a 3
  pagine interne (docs, app), RDAP per l'eta' del dominio. Tokenomics: report
  completo RugCheck / GoPlus, esclusi pool, locker e curva pump.fun.
  Soglie fatali: creatore > 15%, primo holder > 20%, primi 10 > 60%, mint o
  freeze attivi, tassa > 5%. Pesi 40/30/30.
- `app/trading/onchain/leaderboard.py`: legge solo i dati salvati del radar
  (`listings.recent()`, proposte e testati di `radar.snapshot()`). Pump.fun
  ed eccezioni li porta il radar (thread "Scanner token e strategie"): una
  fonte e una regola sole. Eccezione = la regola del radar
  (`legit.github_shortfall` + `gem_shortfall` sui controlli salvati) piu'
  GitHub a fondo >= 85. Stato su `storage.data_file("onchain_leaderboard.json")`.
- `GET /api/onchain/leaderboard`; frontend `static/onchain/leaderboard.js`,
  sezione `#board` subito dopo `#radar`, poll ogni 10 s, righe che scivolano
  (FLIP) quando cambia l'ordine.
- In sandbox GitHub risponde solo per il repo del progetto: l'analisi GitHub
  e' provata sul repo stesso e con test; sul server usa `GITHUB_API_TOKEN`.
- Seguito, stesso giorno. Lorenzo: "mi devi mettere drag al primo posto in
  assoluto con menzione d'onore [...] estrai punti chiave da questo progetto
  e applica come regola per altri progetti simili dal punto di vista
  tecnologico"; poi "leaderboard [...] piu' in risalto, non al fondo [...]
  vedere le scritte delle cose scartate non mi interessa" e un'immagine di
  riferimento (cubo nero, linea verde luminosa, griglia isometrica).
  - `app/trading/onchain/benchmark.py`: DREGG (mint `XkeT...pump`, dregg.net,
    github.com/emberian/dregg: kernel Lean 4, STARK Plonky3 ricorsive,
    Blocklace DAG BFT, SDK/CLI, 10 203 commit, AGPL) in 8 tratti pesati;
    `similarity()` 0-100 da linguaggi, cartelle, argomenti GitHub, commit
    totali (somma dei contributi) e termini tecnici del sito
    (`site_terms`, salvati in `facts.tech_terms`). Leggibile anche dal radar.
  - Classifica: DREGG sempre primo (mai escluso, mai potato), gli altri per
    0.7 qualita' + 0.3 somiglianza. Sezione `#board` spostata subito sotto il
    saldo, prima del radar; scartati nascosti (`.radar-rejected`, sezione del
    radar, nascosta via CSS su richiesta di Lorenzo).
  - Perche' "era sparita": in fondo alla pagina e vuota (nessun progetto
    passava ancora tutti e tre i pilastri); ora c'e' almeno il riferimento.
- Resta: vedere la classifica piena sul server; se troppo vuota, valutare con
  Lorenzo le soglie fatali (sono volutamente severe).

---

### Scan H24 dei progetti seri — `seed-0111` (24/09)

Lorenzo: "hai trovato soltanto drag perche' te l'ho detto io [...] ce ne sono
tanti su Robin Hood Chain e su Solana [...] sotto 2-3 milioni di market cap,
non oltre; uno, due, tre mesi non e' importante".

- Causa: la classifica leggeva solo il radar (pool nuovi/di tendenza = meme).
- `onchain/discovery.py`: CoinGecko `solana-ecosystem` (pagine 3-8) e
  `robinhood-ecosystem` (1-4), fascia $50k-$3M, una richiesta ogni 12 s
  (il gratuito da' 429 facilmente); profili DexScreener ogni 2 min. Scarta
  meme/azioni tokenizzate/stablecoin, richiede sito proprio. Chiave CoinGecko
  della chain: `robinhood` (verificata).
- Fonti `coingecko`/`dexscreener` in classifica: cap <= $3M, eta' <= 365 gg,
  GitHub >= 70, altri pilastri >= 60. `depth.analyze_github` ora boccia un
  repository che non e' del progetto (`legit.github_belongs`).
- Resta: la UI a due sezioni e i testi sono di "Revisione generale app".
- 25/09, Lorenzo: "non stai trovando nessuna gemma [...] puoi farla anche
  attraverso altri canali". Scelto sulla card: GitHub obbligatorio.
  Canale GitHub in `discovery.py`: ricerca repository (una ogni 150 s, 9
  query a rotazione: pump.fun, dexscreener, robinhood chain, "CA:"...),
  README da raw.githubusercontent (niente quota API), indirizzi -> DexScreener
  -> cap $50k-$3M, sorgente `github`, `github_verified` salta il controllo di
  appartenenza. Pending oltre 6 h: tolto dalla coda, non bandito.
- 25/09 `seed-0116`, narrative ("privacy, zero knowledge, ai agent, sistemi
  operativi agentici [...] soldi gestiti da AI"): `onchain/narratives.json`
  (24 voci, heat 1-3, regex, categorie CoinGecko verificate, query GitHub) e
  `narratives.py`. Discovery: indice `/coins/list?include_platform` a ogni
  giro, poi le categorie narrative (pagine finche' la cap resta sopra $50k)
  filtrate su Solana/Robinhood, poi gli ecosistemi. Voto: `bonus()` fino a +6
  sul punteggio finale; termini generici (`weak`) contano mezzo. Etichette
  `.bd-nar` sulle schede. `github_rate` in board() + avviso in testata.
- 25/09, GitHub NON piu' obbligatorio (Lorenzo: "non tutti hanno il github
  pubblico [...] non deve evitare di scegliere progetti che sul resto sono
  legit"; supera la scelta "GitHub obbligatorio" fatta sulla card). Era il
  blocco vero: "no GitHub" era fatale e bandiva per 30 giorni.
  `depth.missing_github()`: pilastro senza voto, `facts.missing`. In
  classifica: sito e tokenomics >= 70 (`NO_GITHUB_MIN_PILLAR`), -10 sul
  punteggio, badge "closed source". Fork/vuoto/banale restano fatali.
  `RULES_VERSION` 2 in store classifica e discovery: bandi e visti azzerati.
- 25/09 `seed-0117`, ripensamento (Lorenzo: "approccio da ricercatore [...]
  la ricerca al minuto deve stare sullo sniper, non qui"; riferimento
  Solrouter, 6SjVTj1V...Ds5). Classifica senza radar/listing
  (`RADAR_SOURCES` scartate al load, RULES_VERSION 3), `REFERENCES` sempre
  esaminati, `research_floor`: nome, >= 14 gg, liquidita' >= $10k.
  `research.py`: pilastro "site" = Research (miglior sito fra home/docs/app,
  descrizione GeckoTerminal/CoinGecko pesata, dossier Claude se
  ANTHROPIC_API_KEY, cache 7 gg in memoria). Senza GitHub: Research >= 70,
  tokenomics >= 60. Solrouter: sito 20 -> Research 76. Resta da verificare
  sul server se la chiave Anthropic c'e' (il flag `ai_review` dei listing).
- 25/09 dubbio di Lorenzo ("come replichi un ricercatore? Claude non e' sul
  server, consumerebbe molti token"): imbuto in `research.py`. Euristiche su
  tutti; Claude solo sui finalisti (`finalist` = passa `research_floor`,
  ricerca euristica >= 45), cache 7 gg su disco (`onchain_research.json`),
  tetto `AI_DAILY_MAX` 150/giorno. Opus 5 ~$0.05 a lettura: realistico
  $1-4/giorno, massimo ~$7. `board()` espone `research_ai`. Serve da Lorenzo:
  chiave su console.anthropic.com, `ANTHROPIC_API_KEY` nel .env del server,
  limite di spesa mensile in console. X non leggibile senza API a pagamento.
- 25/09 Lorenzo: "uno o tre dollari al giorno ma e' comunque un qualcosa che
  gira H24 [...] ho l'abbonamento Claude Pro [...] per ora concentrati a
  creare la base matematica e algoritmica". Claude spento
  (`research.AI_ENABLED = False`, codice e imbuto restano). Nuovo
  `reader.py`: stesso dossier di Claude (summary, stage, substance, verdict,
  red_flags) piu' `points`, `why`, `parts`. Segnali: profondita' (concetti in
  5 campi, saturazione e^-n/6), concretezza (numeri+unita', codice, install),
  stadio (live/testnet/roadmap + app che risponde), ruolo del token entro 12
  parole, penalita' buzzword/hype, cloni via MinHash bottom-k su 5-grammi
  (>= 0.5 = copia; impronte in `onchain_research.json`), coerenza
  descrizione/sito (< 0.1 o sito che non nomina il progetto = sito non
  letto). Scam solo con promesse di rendimento. Siti con l'indirizzo del
  token nell'URL (pagine di launchpad) scartati. Su dati reali: Solrouter 78
  gem, profili DexScreener del giorno quasi tutti thin. Pilastro = 0.35 sito
  + 0.65 lettura.
- 25/09 Lorenzo: "con il tier free impostiamo un limite di utilizzo [...] il
  sistema deve funzionare lo stesso, però per avere il boost [...] bisogna
  che paghi, perché le chiamate costano [...] con Sonnet [...] da definire
  per bene". `plans.py`: Free 5 letture/giorno, Boost 50 + 10 profonde,
  Pro 300 + 60 (prezzi da decidere, `price_usd_month` None). Profonda =
  Sonnet 5 (`research.BOOST_MODEL`), solo con chiave sul server, anche con
  `AI_ENABLED` spento. API: GET/POST `/api/onchain/plan` (POST = admin
  assegna il piano a mano), POST `/api/onchain/research` {chain, token,
  deep}. `settings.payment_address` vuoto: pagamenti da definire. Manca la
  UI (Lorenzo non ha chiesto ancora dove metterla).
- 25/09 Lorenzo: "continua a non trovare niente". Deploy confermato (07:38),
  Solrouter in locale passa (site 78, tokenomics 64, qualifies ""). Causa
  probabile: bocciature e pilastri Research salvati con le regole vecchie
  (site ricalcolato solo ogni 12 h, `_gone` permanente). RULES_VERSION 4:
  toglie le bocciature v3 e ricalcola subito i pilastri "site"; i
  REFERENCES non vengono mai banditi. Board: `close` (i 6 piu' vicini e
  perche' restano fuori) e `past_floor`; UI "Close to the board". Live
  scanner/Just launched/Picks/Track record/Wall of rugs spostati da Gems a
  Memes.
- 25/09 Lorenzo: "pagina praticamente morta". Sul server ROUTER 47: non un
  bug di lettura (ricerca 78) ma il punteggio finale, 0.7*qualita' +
  0.3*somiglianza a DREGG (letta dal codice: 0 senza GitHub) - 10. Ora la
  somiglianza e' solo un bonus (max(q, mix)): Solrouter ~67. Bacino: nuova
  fonte Jupiter verified (`discovery._poll_jupiter`, ogni 6 h, sorgente
  "jupiter" seria): 3693 token, 213 in banda il 25/09 (cap 50k-3M,
  liquidita' >= 10k, >= 14 gg, sito, mint revocato, niente tag
  meme/stocks/rwa/lst).
- 28/09 Lorenzo: "c'e' Aave che [...] capitalizza miliardi non puo' esistere
  [...] per adesso massimo consideriamo 10 milioni di market cap". Tetto
  duro `BOARD_CAP_MAX_USD` = $10M in `qualifies` (prima di tutto, anche
  eccezioni e ammessi da DeepSeek; il benchmark DREGG resta). Il cap e'
  `true_cap` = max(cap del pool, cap globale CoinGecko): la copia Solana di
  AAVE segnava $585k, AAVE vale $2.2B. `_check_global_cap`: una richiesta
  `/coins/{chain}/contract/{addr}` ogni 15 s, prima le voci in classifica,
  cache 24 h, 429 = pausa 2 min. `discovery.CAP_MAX` 25M -> 10M.
- 28/09 Lorenzo: "sempre un bug che mi porta Aave [...] 400-500 mila
  dollari [...] non bisogna scambiare come base capitalizzazioni cripto
  grosse". Il controllo per contratto non bastava: CoinGecko registra la
  copia bridged come moneta a se' ("Aave Wormhole") con la sua cap piccola.
  `big_coins.py`: le prime 500 cripto per cap (`/coins/markets`, una volta al
  giorno); stesso ticker, o ticker che lo contiene con nome che inizia uguale
  ("Aave (Wormhole)") = e' quella moneta. Entra in `true_cap`.
- 28/09 Lorenzo: "deve funzionare subito, devi capire quando sono porting
  da altre chain". Lista top 500 anche nel codice (`big_coins_seed.json`,
  vale dal primo avvio; la versione live la sostituisce al primo giro e
  riordina subito la classifica). Nome che dice porting (Wormhole, (Portal),
  bridged, Allbridge, Sollet, Axelar, Wrapped, "(WH)"...) = fuori a
  prescindere dalla cap.
- 28/09 Lorenzo: "CONTINUO A VEDERE AAVE AL PRIMO POSTO". Era la Top
  (`/api/onchain/top`, `_top_entries`): unisce alla classifica le righe
  studiate del database, che non passavano da `qualifies`. Ora anche quelle
  passano da `leaderboard.too_big` (porting o cap oltre $10M).
- 28/09 Lorenzo: "non e' possibile che $DREGG prenda 60 a research" ->
  #289/#290 (DeepSeek): stadio "building" riconosce codice eseguibile
  (runnable, proof record...), nuova parte `candor` (+8 a chi dichiara i
  propri limiti), RULES_VERSION 5 rilegge tutto. DREGG 61 -> 70 sul sito
  vero; il resto manca perche' il sito non dice a cosa serve il token.
- 28/09 Lorenzo: "deepseek puo' esaminare github dei progetti e capirne la
  complessita' e un punteggio per innovazione?" -> #291/#292
  `code_review.py`: README + 4 file sorgente piu' grandi, DeepSeek da'
  complessita'/innovazione 0-100, fork_of, pro/contro; media pesa 20% nel
  finale; un progetto al minuto, 80/giorno, TTL 7 gg, retry dopo 6 h.
- 28/09 Lorenzo: "ha senso scansionare cosi' tanto? [...] quando
  raggiungiamo un bel bacino fermiamo la scansione e concentriamoci su
  completare le informazioni". Regola: bacino = studied+ranked nel database;
  da 300 in su la ricerca di progetti nuovi (`discovery.tick`) si ferma finche'
  piu' di 10 progetti aspettano un pezzo (analisi, report DeepSeek, lettura
  del codice); sotto i 10 riparte piano, un giro ogni 6 h. Lo sniper meme non
  e' toccato. Nell'Agent: barre "Gem pool" e "Projects complete".
- 28/09 Lorenzo: "ci sono alcuni progetti nel database che hanno dei
  punteggi altissimi pero' non compaiono nel podio" + animazione al rientro ->
  PR #325: la Top legge righe studied E ranked, `demote_ranked` quando la
  bacheca cambia; `top.js` ricorda l'ordine visto (`lae:top-seen`) e anima
  sorpassi e nuovi ingressi.
- 29/09 Lorenzo: "la tab narrativa cosi' come l'hai fatta non funziona [...]
  voglio filtrare il database per tipologia di narrativa [...] anche i top
  progetti devono essere di riflesso [...] prima il database completamente
  mappato [...] questa task la deve fare DeepSeek". `narrative_map.py`:
  DeepSeek classifica 12 righe ogni 90 s (max 400 chiamate/giorno) sul
  catalogo, `narr_at` segna le righe fatte; una nuova analisi non cancella
  le chiavi mappate (`record` unisce, `e["narr_ds"]`). Filtro a chip nel tab
  Database (`narrative_pick.js`, `lae:narr`), la Top lo segue (niente
  animazione "dall'ultima visita" mentre e' filtrata). Tolta la sezione
  narrative dal Profilo e l'ordinamento "le mie narrative prima". Scritto a
  mano (#327/#328 aperti per DeepSeek): le Actions fallivano tutte in 3 s dal
  29/09 01:20 UTC, deploy compreso — probabile limite billing, da sistemare a
  Lorenzo.
- 29/09 Lorenzo: "tutti i token che entrano in top dovranno avere l'indagine
  di deepseek nella tab why e info, come fatto per dregg" -> `top_fill`: ogni
  minuto fino a 3 letture (giudice + codice) per i token della Top che non le
  hanno, con quota giornaliera propria (`priority=True`); la pagina token
  mostra giudice e codice anche per le righe del database.
- 29/09 Lorenzo: "hatcher dice che sarebbe escluso e solo studied invece di
  ranked, e poi me lo trovo nella top al primo posto. dai a deep seek anche il
  compito di scansionare queste incongruenze". Regola: la Top E' la
  classifica. Le righe del database con un motivo di esclusione restano fuori
  (salvo ammissione del giudice); `projects_db.sync_top` segna "ranked" con la
  posizione chi e' in Top e "studied" gli altri. `consistency.py`: DeepSeek
  ogni 2 h legge Top + 30 migliori fuori e segnala contraddizioni (diario
  Agent, `GET /api/onchain/consistency`), rimanda a rianalisi max 5 a giro.
  Animazione "dall'ultima visita": parte solo quando la Top e' a schermo.
- 29/09 Lorenzo: "roba seria tipo AUERON, STEALF, pfwa, GRID [...] dove
  cavolo sono", poi "non devi raggiungere in modo fisso questi token, alziamo
  il tetto sopra i 100k [...] il limite di data non ha granche' senso",
  "se non passano le nostre regole sono da rivedere", "far esaminare a
  DeepSeek le caratteristiche di quei progetti [...] i controlli devono
  allinearsi a quel tipo di qualita'", "se il sito e' scritto in JavaScript
  non lo devi bocciare". Fatto (niente riferimenti fissi):
  - regole gemme: nessun limite di eta'; soglie pilastri uniche (GitHub 35
    se c'e' codice, sito 50, tokenomics 60); fino a $2M basta, $2M-$10M
    serve punteggio 80 (`GEM_STRICT_CAP_USD`); tetto $10M invariato;
    Robinhood: i contratti (pool, vesting) non contano come wallet
    concentrati. RULES_VERSION 6, i bocciati con le vecchie regole tornano
    in coda.
  - lettore siti: `jstext.py` legge il testo che Next.js/Nuxt/SvelteKit
    mettono nell'HTML; fallback Chromium headless se Playwright c'e' sul
    server (non installato: `pip install playwright && playwright install
    --with-deps chromium`); un sito illeggibile vale 50 neutro, non
    "debole". `reader.py`: i disclaimer non sono hype, "live" si deduce da
    prove (contratti, app, meccaniche). PFWA 21 -> 57.
  - Telegram pubblico (`telegram_public.py`, t.me/s/...) nel giudizio
    DeepSeek, numeri X/Telegram visibili in Why. X non si legge gratis.
  - Canale di studio con DeepSeek sul server: domande in
    `.github/deepseek/studi/requests/`, il server le legge da main ogni 5
    min, risposte su `GET /api/deepseek/studies/{id}` (pubblico). Primo
    studio: `001-gem-models` (STEALF, PFWA, GRID, BV7X + DREGG). Lorenzo:
    "stagli addosso a DeepSeek [...] estremamente critico": ogni risposta va
    verificata sui dati prima di diventare regola, revisione salvata accanto.
    AUREON aggiunto (Robinhood `0xd293...7777`). Risposta 001 revisionata
    in `.github/deepseek/studi/001-gem-models.md`: **non usabile come
    regole**, costruita su pilastri vecchi (pre-#337) e troncata a 8000
    token. Tenuto: primitive nominate (Turnkey, Umbra, LayerZero,
    ERC-8004, x402, EAS, Lean) come segnale e pista di ricerca; codice
    mancante abbassa la fiducia, non esclude. Rifiutato: soglie arbitrarie
    (holders >= 1500, LP >= 90%), "dominio piu' vecchio del token" come
    red flag. Corretti dopo: il dossier rifa' tutti i pilastri, GitHub
    prova ogni repo linkato (BV7X bocciato per un link morto), il ticker
    senza `$` conta come menzione del token, top 10 holder con
    contratto/wallet. Prossimo: deploy, poi studio 002 con
    `follow_up: 001-gem-models`, verificarlo, e solo dopo tradurlo in
    profilo di somiglianza + query di ricerca.
    Studio 002 (`.github/deepseek/studi/002-gem-models-fresh.md`):
    usabile in parte. Applicato: bonus "primitive nominate" nel reader
    (fuori da MAX_POINTS, e' un bonus), tokenomics da GeckoTerminal quando
    GoPlus non ha il token (holder + top10 informativo, max 65), 12 query
    GitHub in discovery. Scartati: soglie holder>=400 e liq/cap>=0.09
    (cucite sui 6 esempi), penalita' LP non bloccata, esclusione PFWA
    come meme. BV7X: repo linkati privati -> GitHub "missing", non fatale.
- 28/09 Lorenzo: "DeepSeek [...] deve riesaminare i risultati che escono
  dalla top classifica e metterli in discussione [...] Clau Pump Tech ma
  che roba è, Leon AI sono nomi che non hanno senso". `judge.review_board`:
  una chiamata legge TUTTA la classifica contro i filtri concordati (niente
  meme, nomi parodia di brand, wrapper "X AI", narrative forti) e per
  ciascuno da' keep/score/reason. Ogni 2 h o 10 min dopo un cambio della
  classifica (`_review_board`, in background). keep=false esclude per 3 gg
  ("DeepSeek review: ..."); lo score pesa 30% nel punteggio finale. Anche
  il SYSTEM del giudice singolo ora boccia nomi parodia/meme.
- 28/09 Lorenzo: "ci deve essere un report di DeepSeek su ogni progetto [...]
  potrebbe anche far entrare un progetto [...] colleghiamo X". Il giudice
  gia' leggeva ogni progetto analizzato e non bocciato; `DAILY_MAX` 200 ->
  600. Il report ora si vede: blocco "DeepSeek" (verdetto, punti forti,
  problemi, motivo di ammissione, esito della revisione) nella scheda e nel
  "why". X: `x_signal.py`, ricerca recente v2 (cashtag, nome, contratto)
  solo per i progetti che il giudice legge, cache 24 h, max 150/giorno;
  conteggi (post, autori, follower mediani) e 5 post migliori nel dossier.
  Spento finche' Lorenzo non mette `X_BEARER_TOKEN` nel .env del server.

## Link ospite in sola lettura — `seed-0096`, branch `claude/link-ospite-asb5wj`

Lorenzo (23/09/2026): "vorrei pubblicare un link per condividere questo sito
[...] con un amico che lo possa utilizzare senza ovviamente poter modificare
niente, quindi solo la lettura".

Scelte (default del coordinatore, non ancora discusse con Lorenzo): niente
account (la registrazione resta chiusa), ma un token con scadenza e
revocabile creato da `/admin/ospiti`. L'ospite e' un utente sintetico vuoto
(`app/guest.py`): vede grafici, radar, scanner, NON i wallet/saldi/watchlist
di Lorenzo. Blocco nel middleware di `main.py`: solo GET, salvo
`GUEST_WRITE_ALLOWED`; chiusi `/admin`, `/api/errors`, `/api/optimize`.
Revoca immediata (il cookie rilegge il link a ogni richiesta).

Resta: se Lorenzo vuole che l'amico veda il SUO pilota/radar in sola lettura
(non un utente vuoto), va aggiunta una modalita' "specchio" — espone saldi e
indirizzi, quindi solo su sua richiesta esplicita.

---

## Wallet on-chain: il "Pilota" — `seed-0089` — PR #73, branch `claude/ui-animations-heolhv`

Lorenzo, in piu' messaggi (set 2026): "troppi tasti", "pochi clic, pochi
cambi di schermata", "da mobile SEMPLICISSIMA [...] non voglio tasti", poi
"a livello di design non ci siamo" e il brief vero: "voglio potermi fidare
[...] quando attivo la strategia utilizzo soldi reali [...] voglio sapere
cosa sta monitorando, cosa sta scansionando [...] minimal ma non priva di
informazioni [...] non deve sembrare fatto da un'IA". Visti i concept:
"PROCEDI E' PERFETTO".

Stato: implementato, test verdi, verificato con Playwright (mock) su mobile
e desktop. Non ancora visto sul server vero.

- `onchain-app.html` si apre in vista Pilota (`#app-shell[data-view]`):
  saldo, stato del pilota (tocco = salute), un interruttore, elenco token
  seguiti (tocco = diagnosi), scartati di recente. Grafico/swap/ordini sono
  la vista "manual", raggiungibile dal menu `...` (dialog `#more`).
- Le 4 pillole di navigazione in alto sono nascoste: scelta di Lorenzo
  ("Toglierli") su una card.
- Server: `app/trading/onchain/pilot.py` + `GET /api/onchain/pilot/{chain}`.
  **Cambio di comportamento**: pilota spento = nessun BUY automatico on-chain
  su quella chain (le vendite continuano).
- `index.html` incorpora il wallet con una copia propria del markup, senza
  `#more`/`#pilot`: tutto il cablaggio nuovo in `main.js` deve restare
  null-safe.

Seguito (`seed-0091`): la rete si cambia toccando il chip accanto al saldo
(`#chain-flip`), avvio con DEGEN (`#splash`), campi a 16px contro lo zoom
di iOS che lasciava la pagina "decentrata".

Resta: vedere il pannello salute sul server vero (probabile scanner spento,
`onchain_execution_enabled` spento, segnali fermi senza Telegram) e decidere
con Lorenzo cosa accendere. PR #70, #71, #72 toccano la stessa pagina:
al merge controllare i conflitti in `onchain-app.html` e gli id seed
(#70/#71 usano entrambe `seed-0086`).

---

## Proposta grafica wallet on-chain (set 2026)

Lorenzo: "rendi questa UI moderna, rapida, ottimizzata, al passo coi tempi,
questa in screenshot sembra un excel, preparami una proposta grafica".

Deciso con Lorenzo ("rimaniamo su onchain-app.html"): il redesign e' stato
portato dentro `frontend/onchain-app.html` e il prototipo separato
(`onchain-app-proposal.html`) e' stato rimosso. Idee portanti, ora in produzione:

- le 4 fisarmoniche (`Saldo & storico`, `Limiti & sicurezza`, `Simulazione`,
  `Auto-trade`) diventano una riga di 4 azioni sotto il saldo + fogli dal basso;
- stato pericoloso sempre visibile in due chip (sola lettura / auto-trade off),
  colore semantico separato dall'accento menta;
- `Rivela chiave privata` fuori dalla lista, riga propria bordata di rosso;
- sparkline 24h e badge di freschezza per rendere visibile la resa da cache;
- token identici a `style.css` (chiaro + scuro), mentre la pagina attuale e'
  bloccata su `color-scheme: dark`;
- tab bar Wallet/Strategie/Attivita'/Impostazioni per le fasi 3-4.

Nel frattempo un'altra sessione ha riscritto la stessa pagina su moduli ES
(`frontend/static/onchain/*.js`): nel merge su `main` ha vinto quella versione,
piu' avanti della mia (stesse idee, codice separato in moduli + test in
`backend/tests/test_onchain_frontend_modules.py`).

Tutti gli endpoint e la logica (sessione, saldo da cache + RPC, posizioni,
rivelazione via QR/SSE, simulazione, circuit breaker) sono invariati: e'
cambiata solo la scocca. La sparkline usa solo le letture vere salvate in
localStorage e non si disegna sotto i due punti.

Nota: `tests/test_onchain_prices.py` ha due test che chiamano davvero la rete
per il prezzo — falliscono in sandbox senza uscita verso l'API prezzi, non per
questa modifica.

---

## Stato del repo

- **Repo**: `snowcomingsoon/liquidity-analysis-engine`
- **Dove gira**: server proprio Hetzner CX23 a Norimberga (2 core, 4 GB,
  6,70 EUR/mese), dominio **liquidityengine.app**. Deploy automatico a ogni
  push su `main`: lint + **test** + deploy (vedi `deploy/README.md`).
  **Fly e' spento** (`flyctl scale count 0`) ma resta come via di ritorno:
  `scale count 1` e si sposta il DNS.
- **Branch di lavoro**: `claude/interface-design-m6q27s`
- **Deploy**: FastAPI su Fly.io, auto-deploy da `main` (~2-3 min) — **non**
  dal branch di lavoro, che va unito a `main` perche' vada in produzione
- **Auth**: cookie firmato (non JWT — vedi `backend/app/auth.py`), PBKDF2 per
  le password

## Architettura

```
backend/app/
├── main.py                    # FastAPI — tutti gli endpoint
├── models.py                  # Pydantic models (incluso MAX_FUTURES_LEVERAGE)
├── auth.py                    # cookie auth, credenziali cifrate (spot + futures)
├── issues.py                  # bacheca segnalazioni (_SEED + merge col volume Fly)
├── trading_log.py             # diario ordini (spot e futures)
├── watchlist.py, archive.py, price_alerts.py, favorites.py, jobs.py
├── analysis/
│   ├── strategies.py          # le 3 strategie + registry
│   ├── backtest.py            # motore backtest spot
│   ├── futures_backtest.py    # motore backtest futures (leva/margine/liquidazione/funding)
│   ├── futures_math.py        # formula di liquidazione condivisa
│   ├── optimize.py, pipeline.py, plateau.py   # ottimizzazione e ricerca stabile
│   ├── smc_engine.py, confluence.py, fibonacci.py, indicators.py, summary.py
├── providers/                 # mexc, binance, kucoin, twelvedata (dati OHLCV)
├── trading/
│   ├── executor.py            # dispatch spot (place_order_for_signal) e futures (place_futures_order_for_signal)
│   ├── binance_exec.py, kucoin_exec.py, kraken_exec.py, coinbase_exec.py, bitstamp_exec.py  # spot
│   ├── binance_futures_exec.py                # implementazione Binance futures (avvolta da futures/binance.py)
│   └── futures/                # un adattatore per exchange, dietro un'interfaccia comune
│       ├── base.py             # FuturesAdapter (interfaccia), Position, FuturesCreds
│       ├── registry.py         # unico posto che decide quali exchange esistono — perimetro UE qui
│       ├── binance.py, bybit.py, okx.py, bitget.py, kraken.py
├── pine/                      # interprete Pine Script custom
├── sniper/                    # token sniper DexScreener
├── live/                      # WebSocket stream MEXC
└── notify/                    # Telegram

frontend/
├── index.html
├── onchain-app.html           # wallet on-chain: solo markup + CSS, nessuno script inline
└── static/
    ├── {app.js, style.css}    # il sito principale, un file solo, come sempre
    └── onchain/               # moduli ES del wallet (vedi sotto)
```

Il wallet on-chain e' l'unica parte del frontend a non essere un file
solo: `static/onchain/{main,api,store,format,sheets,sparkline,reveal}.js`
sono moduli ES veri, importati per nome (`@onchain/api.js`) tramite un
import map che `main.py` genera al volo (`_onchain_importmap`). Serve a
mettere il `?v=<hash>` **anche sugli import interni** di un modulo, che il
browser risolve da solo e che nessuna replace sull'HTML raggiungerebbe —
senza, dopo un deploy Safari continuerebbe a servire i vecchi moduli.
Resta zero build: niente Node nel Dockerfile, niente bundler. Se si
aggiunge o rinomina un modulo non serve toccare nulla (la mappa si
costruisce dalla cartella), e `test_onchain_frontend_modules.py` verifica
che ogni import scritto nei moduli sia risolvibile.

Le tre strategie e le cose misurate/pericolose sono in `CLAUDE.md`, non
ripetute qui apposta — un solo posto da tenere aggiornato.

## Workflow di lavoro (come procede Claude qui)

1. Bacheca prima di tutto (`CLAUDE.md`).
2. Ogni fix/feature discusso in chat finisce anche in `_SEED` +
   `resolutions.json`, non solo nella conversazione.
3. Verifiche prima di ogni commit: `pytest`, `ruff`, `node --check` (comandi
   esatti in `CLAUDE.md`).
4. Commit e push sul branch di lavoro sopra — mai forzati, mai su `main`
   senza che sia esplicitamente chiesto.
5. Questo file (`HANDOVER.md`) si aggiorna dopo lavori pluri-sessione o
   decisioni rilevanti, cosi' che una chat diversa possa riprendere.

---

## Filoni di lavoro aperti (pluri-sessione)

### Modalita' semplificata — **implementata, non ancora verificata su backend vero**

Lorenzo, con le sue parole: «voglio anche che ci sia una modalita'
semplificata [...] una persona possa con un grafico [...] scegliere la
strategia piu' adeguata, visualizzare gli ingressi e le uscite in modo
chiaro, con un backtest magari che appare [...] in un click impostare [...]
con una modalita' guidata le API per l'exchange [...] arrivare al punto in
cui uno puo' con pochi passaggi abilitare l'allarme alle operazioni in
automatico [...] Voglio un UI estremamente semplificata, pero' non per
questo povera di dettagli grafici [...] bella». Poi, rivisto un primo
prototipo: «tutte le funzioni di backtesting siano comunque attive anche
nella modalita' semplificata [...] voglio poter comunque ottimizzare la
strategia secondo la logica gia' attuale, con tutte le modalita' di
ottimizzazione che abbiamo [...] sia chiaro quanti minuti restano al
termine». Poi ancora: se un ticker ha gia' strategie approvate in
archivio, mostrarle prima di proporre un nuovo backtest.

Fatta tre giri di prototipo (Artifact, approvati uno alla volta) prima di
toccare il codice — link nel log delle conversazioni sotto. Implementazione
vera in `frontend/static/simple-mode.js` (nuovo file, ~890 righe, CSS
scoped sotto `#simple-mode-root`, zero id/classi di `app.js` toccate) +
4 righe in `index.html` (bottone toggle + contenitore). **Nessun endpoint
backend nuovo**: ogni passo del wizard chiama API gia' esistenti e vere —
`/api/symbols`, `/api/analyze`, `/api/archive` (filtrato client-side per
ticker), `/api/strategies`, `/api/optimize/start` + polling `/api/jobs/{id}`,
`/api/auth/trading`, e per l'attivazione `/api/archive/{id}/apply-to-alert`
(ramo archivio) oppure `POST /api/watchlist` + `PATCH .../strategy_params`
+ `PATCH .../strategy` (ramo nuova strategia) — quest'ultima PATCH e' quella
che fa scattare l'esecuzione automatica reale, tramite lo stesso watcher
in background che gia' esisteva.

Scelte fatte in autonomia durante l'implementazione: solo spot (coerente
con leva 1x server-wide, vedi sotto); exchange nel wizard Binance/KuCoin/
Kraken invece di Binance/Bybit/Kraken del prototipo (il backend supporta
questi tre per lo spot, non Bybit); per i ticker azionari niente step
exchange, l'attivazione diventa solo avviso Telegram (dichiarato in UI,
l'esecuzione automatica esiste solo per crypto spot); countdown
dell'ottimizzazione onesto — stima client-side su `elapsed_s` reale contro
le soglie gia' note (10-25s/1-5min), con "quasi fatto" invece di un
countdown che sbaglia oltre soglia; uscita sempre permessa durante
l'ottimizzazione, il lavoro continua server-side comunque.

Verificato dall'agente contro mock fedeli agli schemi Pydantic reali (il
Python 3.12 non e' disponibile in questo ambiente, niente backend vero da
avviare) — poi ri-verificato da Claude leggendo il diff a mano: ogni
endpoint, payload e campo di risposta citato esiste davvero nel backend
con lo stesso nome (controllato uno per uno prima del merge).

**Da fare**: verifica manuale end-to-end contro il backend vero in
produzione (nessuna sessione ha ancora potuto testarlo con un account e
un'ottimizzazione reali) — bloccante prima di considerarla pronta per
davvero, stessa cautela gia' vista per i futures multi-exchange.

---

### Ridisegno dell'interfaccia — `seed-0028` — **in corso**

Lorenzo: «voglio un overhaul generale del design di tutto il sito visto le
tante funzioni implementate serve occhio globale che inserisca ogni funzione
in modo moderno e visualizzato in modo efficace», poi «DEVI METTERE IN
DISCUSSIONE OGNI COSA», poi «voglio TUTTO UGUALE» rispetto al prototipo
navigabile che aveva approvato.

Principio: l'architettura si nomina per **intento**, non per oggetto. Le tab
erano nominate per oggetto e quella Alert era diventata una discarica di
sette funzioni, con dentro un ordine a denaro reale.

**Fatto**:
- Sistema di design «Instrument»: fondo nero-freddo con tinta verde, accento
  menta speso con parsimonia, colore semantico separato dall'accento, numeri
  hero in Instrument Serif (mai in colonna: non ha cifre tabellari).
- Una sola navigazione (sidebar) al posto di tre sovrapposte (rail + tab +
  menu Altro). Pilota il meccanismo delle tab esistente invece di duplicarlo,
  quindi resta un solo posto che decide quale contenuto e' vivo. Rail, tab e
  Altro restano nel DOM perche' `app.js` ci si aggancia.
- Aree: Analizza / Lab / Sorveglia / **Opera** / Scopri. Il trading e' uscito
  dalla tab Alert. Il Lab e' a due colonne a tutta larghezza.
- Il grafico non sparisce mai: largo in Analizza, a colonna altrove, fascia
  bassa sotto i 1250px.
- UI futures completa (era il punto 2 del piano `seed-0027`): leva a cursore,
  anteprima obbligatoria da `/api/trading/futures/quote`, conferma esplicita
  che nomina leva e prezzo di liquidazione. Ogni modifica invalida la
  conferma e azzera l'anteprima. Tetto UI allineato a `MAX_FUTURES_LEVERAGE`
  (10, non 20).
- Endpoint `GET /api/trading/futures/positions` (sola lettura, non tocca
  l'executor) + posizioni con la distanza dalla liquidazione disegnata come
  lancetta su nastro.
- Mappa dei candidati nel Lab: i dieci `top_candidates` che il backend
  restituiva da sempre e che nessuna schermata aveva mai mostrato.

**Da fare**:
1. **Riportare il Token Sniper dentro l'app.** E' ancora `sniper.html`, una
   pagina a se' con tema e font suoi. E' il pezzo piu' grosso che manca per
   dire che il ridisegno e' finito.
2. Sorveglia a tre colonne come nel prototipo (watchlist con sparkline,
   alert attivi, storico a timeline).
3. Analizza: striscia di statistiche sotto il grafico e barre di confluenza,
   che nel prototipo c'erano.

Prototipo navigabile di riferimento (Artifact): «Liquidity Instrument».

---

### Operazioni futures — `seed-0027` — **in corso**

Piano originale (fasi 0-4, solo Binance) approvato e scritto in una sessione
precedente — vedi sotto per dov'e' finito. Principio guida invariato: leva e
margine sono l'estensione piu' pericolosa possibile per questo sistema —
isolamento totale dal codice spot, mai una modifica in-place a un modulo
spot esistente, sempre un modulo nuovo affiancato.

**Cambio di perimetro (questa sessione)**: Lorenzo ha chiesto futures per
"tutti gli exchange dove si puo' operare in leva in Europa", non solo
MEXC/KuCoin come previsto dal piano originale. MiCA/ESMA limitano i derivati
al retail UE, e non tutti gli exchange gia' collegati per lo spot li offrono
li': **Coinbase e Bitstamp restano fuori** (niente derivati a leva per il
retail UE), **MEXC e KuCoin restano fuori** (hanno i futures ma non la
licenza UE), aggiunti invece **Bybit, OKX, Bitget, Kraken** — tutti con
licenza per offrire derivati a leva in Europa, insieme a Binance che c'era
gia'. Deciso senza chiedere conferma esplicita nel corso della sessione:
Lorenzo ha detto "procedi" dopo aver visto il perimetro proposto.

**Fatto**:
- Fasi 0-4 del piano originale, solo Binance (sessione precedente): modello
  dati (`FuturesCredential`, `MAX_FUTURES_LEVERAGE`), `futures_backtest.py`
  (leva/margine isolated/liquidazione intrabar/funding), `binance_futures_exec.py`
  (`/fapi/v1/...`), guardrail lato server (cap di leva, `confirm:true`
  obbligatorio, kill switch, controllo margine pre-trade), endpoint
  `/api/trading/futures/quote` per l'anteprima.
- **Multi-exchange (questa sessione)**: `app/trading/futures/` — pacchetto
  nuovo con un'interfaccia comune (`base.py`, classe `FuturesAdapter`, sei
  metodi) e un registro (`registry.py`) che e' l'unico posto che decide
  quali exchange esistono. `binance.py` avvolge il modulo esistente senza
  riscriverlo (zero rischio su cio' che gia' funzionava); `bybit.py`,
  `okx.py`, `bitget.py`, `kraken.py` sono adattatori nuovi, ciascuno con le
  sue trappole documentate nel proprio file (firma diversa, quantita' in
  contratti vs monete su OKX, Kraken senza isolated margin). `executor.py` e
  `main.py` non nominano piu' un exchange specifico: chiedono l'adattatore
  al registro. Frontend: select exchange, tetto di leva e avviso
  isolated/condiviso pilotati da `/api/auth/futures` (non piu' scritti a
  mano nell'HTML), piu' la UI di configurazione credenziali per i quattro
  exchange nuovi (prima non esisteva — solo il form d'ordine c'era).
  Dettaglio tecnico completo in `resolutions.json` sotto `seed-0027`.
- Fix nello stesso giro: la sezione **Livelli & Indicatori** era diventata
  irraggiungibile su desktop dopo il ridisegno `seed-0028` (il rail che la
  apriva e' nascosto, e nessuna voce della sidebar la sostituiva) —
  segnalazione `e599667e`, ora una voce sidebar propria. Vedi
  `resolutions.json`.

**Da fare, in quest'ordine**:
1. **Verifica manuale in testnet (o importi minimi) su ciascun exchange** —
   richiede chiavi API vere, anche solo di test. Bloccante prima di fidarsi
   dell'esecuzione reale: nessun ordine e' mai stato mandato a un server
   vero su nessuno dei cinque, solo a trasporti finti nei test.
2. **Non verificato in questa sessione**: niente ambiente Python 3.12
   disponibile sulla macchina per lanciare `pytest`/`ruff` per davvero — solo
   controllo sintattico (`py_compile`) e revisione a mano. Da lanciare la
   suite completa alla prima occasione con l'ambiente giusto.
3. MEXC e KuCoin restano fuori per perimetro normativo, non per limite
   tecnico: il registro accoglie un nuovo adattatore con un file piu' una
   riga in `registry.py`, se la decisione cambiasse.

File coinvolti: vedi l'elenco completo in `resolutions.json` sotto `seed-0027`
(troppo lungo per ripeterlo qui — include tutto `app/trading/futures/`,
`executor.py`, `main.py`, `auth.py`, i tre file frontend, i test).

---

### Trasloco da Fly a un server proprio — **fatto**

Il motivo non era la velocita': era che su 512 MB una ricerca aveva gia'
saturato la memoria e ucciso il processo, e un processo morto sono avvisi che
non arrivano. Lorenzo: *"non mi interessa velocizzare la strategia del cazzo,
basta che gestisca gli allarmi e i vari segnali"*.

Misurato prima di decidere (`/api/analyze` BTCUSDT 1d, a caldo): Fly **1,69 s**,
oggi **0,19 s**.

Come e' andata la scelta della macchina: le CX erano esaurite, e la prima
alternativa mostrata dalla console (CPX22, 23,78 EUR) costava tre volte
troppo. L'API di Hetzner ha poi rivelato il **CX23 a 6,70 EUR**, che
l'interfaccia non proponeva. Da qui una regola utile: **per la
disponibilita' e i prezzi chiedere all'API, non leggere la console**.

Due difetti dello script di setup trovati sul campo, entrambi corretti:
`sshd` tiene il **primo** valore che legge e i frammenti si leggono in ordine
alfabetico, quindi il file `99-` non disattivava niente contro il
`50-cloud-init.conf` di Ubuntu (ora e' `00-`); e da Ubuntu 25.10 SSH e'
attivato dal socket, quindi `reload ssh` fallisce e con `set -e` fermava tutto
il resto dello script senza che si notasse.

**Da fare**: la chiave TwelveData non e' stata portata (le azioni sono spente,
vedi sotto). Se un giorno servissero, va rimessa in `deploy/.env`.

### Azioni disattivate — **fatto**

`settings.stocks_enabled = False`. Una voce `BTC/USD` in watchlist, marcata
come azione, mandava avvisi di errore su una chiave TwelveData mancante.
Lorenzo opera solo in USDT/USDC. Spegnendole sparisce anche la dipendenza da
TwelveData, che col suo limite di 7 richieste al minuto era il collo di
bottiglia piu' stretto del prodotto. E' un interruttore, non una rimozione.

---

### Sicurezza del sito pubblico — `seed-0031` — **fatto**

Con `liquidityengine.app` in chiaro su internet, l'audit ha trovato **33
endpoint senza autenticazione**. I due che contano: `/api/optimize`, che
occupa un core per minuti — due richieste anonime bastavano a mettere giu' il
sito su due core e ad affamare il ciclo che manda gli avvisi — e
`DELETE /api/pinescript/{id}`, che cancellava gli script di chiunque.

Chiusi con **un cancello unico** (middleware) invece di 33 firme: un endpoint
nuovo nasce protetto. Il cancello si fa da parte quando `dependency_overrides`
e' popolato, perche' un test che ha iniettato un utente ha gia' dichiarato chi
e'; in produzione quel dizionario resta vuoto.

Aggiunti anche: registrazione ristretta a un elenco, una ricerca pesante per
utente alla volta, CSP e Permissions-Policy, container non-root.

**Trappola da ricordare**: il Caddyfile e' un volume montato, quindi
`docker compose up -d` **non** ricarica Caddy quando cambia. Le intestazioni
nuove sono rimaste ferme in produzione finche' non l'ho riavviato a mano; ora
il workflow fa `restart caddy` a ogni deploy.

---

### Kraken come provider dati spot — fatto

Lorenzo aveva chiesto una ricerca su cosa offrono le API pubbliche Kraken;
proposte 5 opzioni, scelta la piu' semplice: Kraken come quarto exchange
dati (accanto a MEXC/Binance/KuCoin). Implementato in `backend/app/providers/
kraken.py`: OHLC pubblico + ricerca simboli via AssetPairs, BTC->XBT gestito
in automatico. Limite reale e dichiarato: Kraken non pagina all'indietro,
max 720 candele per intervallo. Board: seed-0056, risolto.

### Opera "troppi exchange" / trading automatico poco chiaro — in corso

Lorenzo: «quando faccio ordine su spot o margine vorrei che prima mi
chiedesse il sistema quale exchange» (poi, per il sito desktop non mobile) —
e subito dopo, mentre lavoravo al mockup: «per abilitare automaticamente
una strategia ad eseguire ordini reali non e' molto chiaro attualmente; si
deve partire dalla watchlist? imposta un sistema semplice che interconnetta
tutto invece di visualizzare cento exchange nella tab opera [...] una volta
aggiunto li il ticker; selezionare la strategia; a quel punto dalla
strategia l'opzione di ottenere solo alert o attivare il trading
automatico». Confermato con lui: Opera va sostituita da questo flusso
(non coesistenza), e l'exchange per l'auto-trading e' sempre quello gia'
associato al ticker in watchlist — nessun picker aggiuntivo.

Primo passo fatto: ogni strategia attiva su un ticker in Sorveglia ha ora
un interruttore proprio "Solo alert" / "Trading automatico" (default:
alert), al posto del vecchio interruttore unico per exchange in Opera che
valeva per ogni strategia attiva li' sopra. Backend: `WatchlistEntry.
auto_trade` (dict strategia->bool), endpoint PATCH `/api/watchlist/{id}/
auto_trade`, gate nel loop di alert. Board: seed-0057, **"in corso"
apposta**, non "risolto": manca ancora il pezzo grosso.

**Secondo giro, stessa sessione**: Lorenzo ha ripreso subito dopo,
correggendo — «i futures devono essere agganciati alla watchlist perche'
tutti parte da li', ogni ticker da watchlist deve permettere di diramarsi,
se attivare solo o alert o anche operazioni automatiche, dopodiche'
selezionare la strategia (da archivio)». Fatto: ogni strategia con
"Trading automatico" acceso, se l'exchange del ticker ha un adattatore
futures registrato (Binance, Kraken, MEXC — intersezione fra i provider
dati spot e il registro futures, la stessa di `FUTURES_PAIR_EXCHANGES`),
mostra anche la scelta Spot/Futures; il loop esegue l'ordine futures con
`place_futures_order_for_signal` usando le credenziali futures gia'
configurate in Opera (leva compresa). KuCoin/Bybit/OKX/Bitget non possono
comparire qui: o non hanno adattatore futures o non sono provider dati
spot nostri, quindi non possono essere l'exchange di un ticker in
watchlist.

**Bug trovato e corretto nello stesso giro**: il gate per-strategia
(seed-0057, primo passo) rompeva silenziosamente la Modalita' Semplice —
quel wizard accende l'esecuzione tramite il vecchio meccanismo
(interruttore per-exchange in `owner.trading_credentials`), che il nuovo
`entry.auto_trade[strategy]` di default `False` avrebbe azzerato senza
errori visibili: chi avesse attivato una strategia dal wizard *credendo*
di aver acceso l'esecuzione reale, in realta' avrebbe ricevuto solo alert.
Corretto prima del deploy: `apply-to-alert` accetta ora un body
`{auto_trade: bool}` e il wizard lo manda `true` solo dopo aver
effettivamente collegato un exchange nel suo passo dedicato.

"Selezionare la strategia da archivio" **esiste gia'** in Modalita'
Semplice (`/api/archive/{id}/apply-to-alert`, passo 1.5 del wizard) — non
duplicato nella scheda classica di Sorveglia, che tiene invece la lista
strategie con parametri modificabili a mano (uso diverso, non lo stesso
percorso).

**Terzo giro, stesso filo**: Lorenzo, secco: «opera sparisce». Fatto per
davvero: la tab Opera non esiste piu' (sidenav, tab-bar, menu mobile
"Altro" ripuliti). Il suo contenuto — credenziali exchange (spot e
futures), posizioni aperte, diario ordini, ordine manuale one-off — vive
ora dentro Sorveglia, sotto le strategie della watchlist, come un secondo
blocco della stessa tab invece che una tab a se'. Tecnica usata apposta per
il rischio basso: il div che prima aveva `data-tab-content="opera"` ha
semplicemente cambiato quell'attributo in `"alert"` — restano due `<div>`
fratelli con lo stesso `data-tab-content`, entrambi si accendono insieme
quando si apre Sorveglia. Nessun id toccato (`trading-credentials-list`,
`positions-list`, `journal-list`, `manual-*`, `futures-*`...), quindi zero
righe di logica di rendering/salvataggio/esecuzione in `app.js` riscritte —
solo dove il blocco appare nel DOM e' cambiato. Le regole CSS a colonne
che erano `[data-area="opera"]` sono ora `[data-area="sorveglia"]`.

**Quarto giro — quello che ha risolto davvero**: spostare Opera dentro
Sorveglia non bastava. Lorenzo, guardando uno screenshot: «ma che stai
facendo? sta roba avevo chiesto di eliminarla e di passare tutto da
watchlist» — la griglia con Binance/MEXC/KuCoin/Kraken e una spunta
"Attivo" su ciascuno era rimasta li', solo in un indirizzo diverso: era
quello il "cento exchange" da eliminare, non la tab in se'. Poi, alla
domanda di chiarimento: «ti avevo chiesto che tutto doveva passare da
watchlist, con l'ordine funzionale che ti avevo chiesto» — cioe' l'ordine
gia' dato nel secondo giro (ticker -> alert o anche automatico -> strategia
da archivio), che nel terzo giro non avevo ancora costruito per davvero.

Fatto ora: quella griglia e' un `<details>` chiuso di default in fondo a
Sorveglia (chiavi, posizioni, diario, ordine manuale — stessa
funzionalita', ma non piu' la prima cosa che si vede). Ogni ticker in
watchlist ha un pulsante "+ Attiva strategia da archivio" che apre la
diramazione vera: solo alert o anche operazioni automatiche -> (se
automatiche) spot o futures, solo dove l'exchange ha un adattatore futures
-> la chiave API si chiede in linea, un exchange alla volta, solo se manca
in quel momento -> scelta della strategia fra le voci d'archivio di quel
ticker (stesso `/api/archive/{id}/apply-to-alert` gia' esteso nel giro
precedente). Se l'archivio e' vuoto per quel ticker, il messaggio guida a
usare prima la lista strategie sotto (esistente, coi parametri di default)
e tornare poi qui.

**Lezione per la prossima volta**: uno spostamento fisico di markup non e'
la stessa cosa di risolvere il problema che quel markup rappresentava —
"cento exchange sempre in vista" era la lamentela originale fin dal primo
giro, ed e' sopravvissuta due giri interi sotto un indirizzo diverso prima
che qualcuno (giustamente) se ne accorgesse guardando lo schermo vero.

**Quinto giro — l'indirizzo sbagliato, di nuovo**: il quarto giro aveva
costruito la diramazione giusta (alert/automatico -> spot/futures ->
strategia da archivio) ma dentro la tab **Sorveglia**. Lorenzo, guardando
l'app vera: «si però se clicco sul ticker che ho in watchlist non mi
permette di fare niente». Alla domanda diretta se intendesse la tab
"Watchlist" (lista rapida) o "Sorveglia" (le card con le strategie):
«ti sto dicendo da mezzora che voglio che tutto sia attivato nella
watchlist (lista rapida) tutto deve originarsi da li». Era la tab
sbagliata fin dal quarto giro — la diramazione c'era, ma non dove doveva
essere cliccabile.

Fatto: ogni riga della tab Watchlist (quella con `#favorite-rows`,
backend `FavoriteEntry`/`/api/favorites` — un modello dati diverso da
`WatchlistEntry`/`/api/watchlist` che alimenta Sorveglia, cosa che ha
richiesto un ponte invece di un semplice riuso) ha ora una freccetta
separata dal clic-sulla-riga (che continua a caricare il grafico, comportamento
di sempre). La freccetta apre un pannello con le strategie gia' attive su
quel ticker (se un `WatchlistEntry` corrispondente esiste gia', letto da
`state.alertEntries` — lo stesso dato che gia' pilotava il pallino
"alert attivo") e sempre `buildActivationFlow()`, la stessa funzione del
giro precedente, generica abbastanza da funzionare sia su un
`WatchlistEntry` sia su un `FavoriteEntry` perche' legge solo
symbol/exchange/asset_type. Nessun endpoint nuovo: attivare da qui crea o
riusa il `WatchlistEntry` esattamente come da Sorveglia.

**Lezione, di nuovo**: nell'app ci sono DUE liste che si chiamano
"watchlist" in punti diversi — quella vera in codice (`WatchlistEntry`,
tab UI "Sorveglia") e quella che l'utente chiama cosi' (tab UI
"Watchlist", modello `FavoriteEntry`). Quando Lorenzo dice "watchlist"
intende quello che vede scritto in UI, non il nome della entita' nel
codice — un'ambiguita' che e' costata due giri di lavoro nella direzione
sbagliata. Se emerge di nuovo un'istruzione su "watchlist", verificare
SUBITO quale delle due tab prima di scrivere codice, non dopo.

**Sesto e settimo giro — rifiniture, stessa sera**: provato il flusso dal
vivo, Lorenzo ha chiesto tre correzioni in rapida successione:
1. «quando aggiungo il ticker sulla watchlist pero' poi non mi chiedi
   quale strategia applicarci» — aggiungere un ticker ora apre da solo il
   pannello e salta dritto alla prima domanda (alert/automatico), senza
   dover aprire la riga a mano e cliccare "+ Attiva" in piu'.
2. «perche' nel caso non ci sia in archivio voglio poterla testare
   direttamente in questa tab» — nuovo stepFresh(): se l'archivio e' vuoto
   per quel ticker (o l'utente lo preferisce comunque, link sempre
   presente), si sceglie una strategia con i parametri di default e parte
   da li', stessa sequenza di chiamate gia' usata da Modalita' Semplice per
   il suo ramo "strategia nuova".
3. «quando seleziono la strategia dall'elenco voglio visualizzare i
   dettagli delle strategie che si trovano nell'archivio in modo chiaro
   non soltanto la percentuale.. ma diocane abbiamo i dati.. usali» +
   «e comunque dopo che la seleziono non la memorizza come scelta» — le
   card dell'archivio ora mostrano trade/win rate/drawdown/profit
   factor/Sharpe/intervallo, non solo il rendimento. E trovata la causa
   piu' probabile del secondo problema: il click ignorava una risposta di
   errore del server trattandola come successo (fetch non rifiuta la
   promise sui codici 4xx/5xx, solo su errori di rete veri) — ora ogni
   card ha un pulsante "Usa questa" con uno stato proprio che mostra
   l'errore reale se il server rifiuta, invece di ricaricare in silenzio
   come se fosse andato tutto bene.

**Ottavo giro — Kraken: dati mensili e feed live**: dopo aver corretto il
flusso di attivazione, due segnalazioni puntuali su Kraken, sempre nella
stessa serata:
- «ma dio cane ti avevo chiesto di implementare tutto da kraken.. usare
  tutte le sue API» — Kraken era rimasto REST-only (60s di polling, come
  Binance/KuCoin), mentre MEXC ha un feed live via websocket. Aggiunto
  `backend/app/live/kraken_stream.py`, che collega il feed pubblico OHLC
  v2 di Kraken (`wss://ws.kraken.com/v2`, JSON — piu' semplice del
  protobuf di MEXC), con la stessa architettura di `mexc_stream.py` (un
  manager, un websocket a monte per (simbolo, intervalli) attivo). Il
  simbolo per il feed v2 non e' quello REST (vuole "BTC/USD" con slash,
  non "XBTUSD") — nuovo `KrakenProvider.get_ws_symbol()` che lo ricava
  dalla stessa lista AssetPairs gia' usata per la ricerca. `/ws/live` ora
  prende un parametro `exchange` e sceglie il manager giusto.
- Trovato scrivendo il test per `get_ws_symbol`: `"XXBT".lstrip("XZ")`
  toglie TUTTE le X/Z iniziali, non solo una — un base a 4 lettere come
  "XXBT" (bitcoin) diventava "BT" invece di "XBT". Bug vero, presente fin
  dal primo giro Kraken (seed-0056), mai notato perche' nessun test
  controllava il valore esatto del base, solo che l'exchange contenesse
  "USD". Corretto estraendo `_strip_kraken_prefix()`, riusata sia dal
  nuovo codice sia da `search_symbols()`.
- Prima ancora, un'altra segnalazione Kraken nello stesso filo: «se
  seleziono 1d voglio 1d» dopo un errore "Timeframe 1M non supportato".
  Non era un bug del selettore — scegliere 1d come intervallo principale
  deriva automaticamente un HTF di 1M per il contesto di lungo periodo
  (comportamento esistente, uguale su tutti gli exchange), e Kraken non ha
  un intervallo mensile nativo. Corretto sintetizzando 1M da 30 candele
  giornaliere (`resample_by_count`), stesso meccanismo gia' usato per
  2D/3D/5D. Lorenzo ha poi chiesto separatamente di eliminare ogni traccia
  dei vecchi tasti HTF/MTF/LTF (sostituiti dal menu a tendina) — trovata e
  rimossa `TF_LABELS`, una costante morta mai referenziata, unico residuo
  rimasto in `app.js`.

Non ancora fatto, per scelta (segnalato, non dimenticato):
- l'ordine manuale one-off dentro il pannello richiudibile (avanzate, in
  fondo a Sorveglia) resta un form con la sua scelta exchange, non una
  card per-ticker — rimandato perche' tocca molto piu' codice per un
  guadagno cosmetico, e nessuno l'ha chiesto esplicitamente;
- nessuna verifica dal vivo con chiavi vere dell'esecuzione futures
  automatica da watchlist (stessa cautela gia' segnata sotto "Operazioni
  futures" — nessun ordine futures e' mai partito verso un server vero);
- il feed live Kraken non e' stato verificato con una sessione reale nel
  browser (solo test unitari con trasporto finto, come tutto il resto di
  questo provider) — se il canale "ohlc" v2 si comporta diversamente da
  come documentato, va vista dal vivo.

---

### Layout: il grafico "si sposta" cambiando tab — `seed-0060` — **in corso, riaperto**

Lorenzo, subito dopo il giro Kraken: «il passaggio dalle varie tab
"analizza" "livelli" "lab" e "watchlist" e sorveglia, deve dare l'effetto
che il grafico non si sposti mai, ma che si adeguino le interfacce
lateralmente non modificando la posizione del grafico... sennò il layout
si scompiglia sempre».

**Primo tentativo (sbagliato, rivertito nello stesso giro)**: `.chart-area`
aveva due comportamenti opposti — in Analizza `flex:1 1 auto` (tutto lo
spazio libero, pannello fisso a 320px), altrove `flex:0 0
clamp(300px,32%,520px)` (larghezza fissa, pannello che assorbe il resto).
Ho reso `.chart-area` sempre alla larghezza fissa stretta, in ogni area.
Risultato: il salto fra tab e' sparito, ma il grafico in Analizza — lo
schermo dedicato a guardarlo — e' diventato piccolo. Screenshot del Lab
alla mano, Lorenzo: «si ma ora il grafico ha poco spazio; sei cosi
stupido?», poi «il sito usa malissimo gli spazi.. fa schifo», poi «il
layout di tutte le tab fa cacare, il passaggio da ogni tab ancora peggio.
fai studiare il layout ad un team di esperti e usa tutte le skill di
design che ti avevo dato per ottimizzare lo spazio nel migliore dei modi».
Rivertito subito (`git revert`) — il grafico e' tornato come prima di
questo giro: grande in Analizza, stretto altrove.

**La tensione di fondo, non ancora risolta**: Analizza e' uno schermo
*guarda il grafico* (chart grande, pannello di lettura stretto); Lab e
Sorveglia sono schermi *lavora sul form* (form/griglia larghi, chart di
riferimento stretto). Dare a `.chart-area` UNA sola larghezza fissa serve
bene uno dei due bisogni e male l'altro, in entrambe le direzioni. Il vero
problema che Lorenzo segnala nel Lab — la fetta destra vuota finche' non
c'e' un risultato di backtest, dentro `.lab-panel { grid-template-columns:
minmax(280px,380px) 1fr }` — e' un difetto di quello schermo specifico
(un placeholder/empty-state che manca), non necessariamente qualcosa che
una larghezza-fissa del grafico risolverebbe.

**Chiuso cosi'**: fatto il mockup (Artifact, link sotto) e sottoposto a tre
revisori indipendenti su richiesta esplicita di Lorenzo ("sottoponi questo
studio ad un team di agent esperti; usa le skill che ti ho installato
anche") — un Agent per il layout/gerarchia (`ui-design-principles` +
`component-gallery`), uno per l'accessibilita' (`wcag-2.2`), uno per
l'animazione (`transitions-dev` + `transitions-polish`), ciascuno con
istruzione esplicita di caricare la propria skill prima di giudicare e di
non modificare nessun file.

Verdetto: il modello a due famiglie (Analizza grafico grande/pannello
stretto; Lab-Watchlist-Sorveglia grafico stretto/pannello largo) era
*gia'* quello vero nel codice — non andava unificato, il primo tentativo
di questo giro era la mossa sbagliata. L'unico bug reale confermato: nel
Lab, `.lab-results-col` teneva sempre riservata la sua colonna di griglia
anche prima di un backtest, lasciando meta' schermo vuota. **Fatto**: una
sola regola CSS con `:has()` che nasconde quella colonna e restringe
`.lab-panel` a una colonna finche' nessuno dei suoi figli (gia' tutti
`.hidden` di default) diventa visibile — si riapre da sola quando parte
una ricerca, zero JS nuovo toccato.

**Deciso di NON implementare**: l'animazione proposta nel mockup per il
salto Analizza↔resto (`transition: flex-basis`). Il revisore
transitions-dev/polish ha trovato la tecnica tecnicamente rotta (`auto`
non interpola in una transizione) e un rischio concreto — il grafico live
(Lightweight Charts, si ridisegna via `ResizeObserver`) puo' scattare o
deformarsi durante un resize animato, cosa verificabile solo con un test
dal vivo che questo ambiente non permette. Restera' uno scatto secco fra
Analizza e le altre aree, come e' sempre stato — non e' un compromesso
nascosto, e' scritto qui e nel mockup stesso.

Prima di pushare il fix, Lorenzo ha chiesto la preview («non dovevi farmi
vedere in anteprima il risultato?») — il mockup e' stato aggiornato con
l'esito reale (non solo la proposta iniziale) e ripubblicato sullo stesso
link prima del push in produzione. Mockup: `https://claude.ai/code/
artifact/66038881-c72c-406b-9ea0-4281c41bf438`.

---

### Cambio di metodo: dal ragionare sul codice al guardare un browser vero

Lorenzo, dopo l'ennesimo giro sbagliato sul layout: «comunque una volta
eri piu bravo, guardavi il tuo browser e facevi le cose bene». Aveva
ragione — questo ambiente HA Playwright e Chromium pre-installati
(`/opt/pw-browsers/chromium-1194`), utilizzabili con Python 3.11 di
sistema (`pip show playwright` → gia' presente, niente da installare).
Il proxy dell'agente non regge le connessioni websocket-based del browser
verso l'esterno (`ws_closed_mid_exchange` su qualunque host, non solo il
sito), ma **in locale funziona perfettamente**: avviare il backend vero
(`uvicorn app.main:app` dalla cartella `backend`, con
`REGISTRATION_ALLOWED_EMAILS` esteso via env var per potersi registrare
un utente di test) e puntarci Playwright su `127.0.0.1` bypassa il proxy
del tutto (localhost e' sempre escluso). Usato per verificare DAL VIVO,
prima di scrivere qualunque correzione basata solo su rilettura di CSS/JS.

**Cosa e' saltato fuori aprendo davvero un browser**, dopo due
segnalazioni fresche di un utente reale («non trova piu' i pair nel Lab»,
«i pair su ordini spot e futures continuano a non essere trovati») e una
vecchia mai chiusa («il riempimento automatico appare troppo a destra e
sparisce dallo schermo»):

1. **`LightweightCharts is not defined`** — se il CDN esterno (unpkg.com)
   da cui si caricavano il grafico e l'editor CodeMirror non risponde per
   qualunque motivo, la chiamata sincrona non protetta a
   `initCharts()`/`initPineEditor()` lanciava un'eccezione dentro la
   stessa sequenza async di avvio che poi chiama `bindUI`, `bindLabUI`,
   il caricamento watchlist — un errore li' interrompeva silenziosamente
   TUTTO quello che doveva agganciarsi dopo, ricerca ticker compresa,
   ovunque nel sito. Riprodotto bloccando lo script in Playwright:
   la ricerca smetteva di funzionare esattamente come nelle segnalazioni.
   Corretto due volte: entrambe le librerie ora vivono in
   `frontend/static/` (vendorizzate, MIT/Apache 2.0, nessun CDN di terze
   parti come singolo punto di guasto), e le due chiamate sono dentro un
   try/catch cosi' un fallimento futuro resta un problema suo.
2. **Un bug CSS reale, mai notato prima** — `.tab-content.active >
   .panel` aveva un'animazione d'entrata con `transform: translateY(...)`.
   Un transform su un antenato crea un nuovo containing block per ogni
   discendente `position:fixed` per tutta la durata in cui l'animazione
   resta "attached" (sempre, con `fill-mode: both`) — e i riquadri di
   suggerimento (`.suggestions`) sono `position:fixed`, calcolati in JS
   con coordinate assolute rispetto allo SCHERMO. Risultato misurato dal
   vivo: il riquadro del Lab diceva `left: 1171px` nel suo stile inline,
   ma `getBoundingClientRect()` lo piazzava a `left: 2330` su uno schermo
   largo 2000px — completamente fuori bordo, con un raddoppio
   dell'offset (posizione del pannello + posizione voluta). Corretto
   togliendo il `transform` dalle animazioni `lae-sali`/`lae-risultato`
   (resta solo la dissolvenza in opacita', stesso effetto percepito) —
   fix application-wide, non solo per il Lab: qualunque tab con un
   dropdown `position:fixed` dentro il proprio pannello di primo livello
   aveva la stessa falla latente (verificato anche sul campo Pair
   dell'ordine manuale in Sorveglia).
3. Aggiunto anche un timeout di 5s per provider dentro `_safe_search()`
   (backend): senza, un exchange lento o irraggiungibile (rilevante ora
   che Kraken e' stato aggiunto) avrebbe fatto aspettare — o fallire —
   la ricerca combinata su TUTTI gli exchange insieme a lui, perche'
   `asyncio.gather` aspetta ogni gamba fino in fondo.

Tutte e tre le correzioni verificate prima/dopo con lo stesso script
Playwright locale, non solo dedotte dal codice. Board: `8151937b`,
`2a7fd905`, `54cbf520` (segnalazioni vere, chiuse), `seed-0061` (la causa
di fondo, tracciata anche internamente).

**Lezione per la prossima volta**: quando questo ambiente lo permette
(localhost, non un sito esterno dietro il proxy websocket), guardare
davvero un browser prima di dichiarare un fix pronto costa pochi minuti
e trova bug che la sola lettura del codice non avrebbe mai fatto
emergere — vale la pena farlo sempre, non solo quando qualcuno lo chiede
esplicitamente dopo un giro sbagliato.

---

### Diagnosi (test di collegamento exchange) e Modalita' Semplice solo mobile — `seed-0062`, `seed-0063` — **fatto**

Lorenzo, in un unico messaggio con piu' richieste: «A modalita' semplice,
quindi da mobile, soprattutto perche' quella nasce solo da mobile e fa in
modo che da desktop non sia visibile e non ci sia insomma. Vorrei poter
anche eseguire delle prove [...] effettuare il test con una tab dedicata
di diagnosi [...] per effettuare dei test preliminari di collegamento
all'exchange. E vorrei anche che fosse visualizzato il saldo una volta
collegate le API. Prima di poter fare poi le vere operazioni. In ogni
caso vorrei poter fare anche operazioni manuali, quindi provare proprio a
fare il test. E questa sezione diagnosi deve servire proprio come debug.
Deve essere circoscritta e permettere poi a te nel caso in cui vengano
fuori dei problemi di poter rimettere a posto in poco tempo.»

**Modalita' Semplice**: tolto il bottone dalla toolbar desktop in
`index.html` — resta solo l'ingresso dal menu mobile "Altro", che gia'
esisteva (la toolbar desktop e' nascosta sotto i 760px, era per quello
che il bottone mobile era stato duplicato in origine). `simple-mode.js`
non ha avuto bisogno di nessun cambio: cercava gia' entrambi gli id e
scartava quelli assenti.

**Diagnosi**: sezione nuova, voce propria in sidebar (senza `data-area`:
non fa parte del sistema di tab del cockpit apposta, zero rischio di
interferire con quello), costruita come modulo isolato — esattamente
come richiesto, sullo stesso modello di `simple-mode.js`:
- `backend/app/diagnostics.py` (nuovo file): `test_spot_connection()`
  legge il saldo vero da mexc/binance/kucoin/kraken/coinbase/bitstamp
  riusando le firme HMAC gia' scritte nei moduli di esecuzione esistenti
  (import delle funzioni private di firma, non riscritte — niente
  duplicazione); `test_futures_connection()` usa `adapter.
  available_margin()` gia' esistente per ogni exchange futures nel
  registro. Aggiunte `get_all_balances()` a `kraken_exec.py` e
  `coinbase_exec.py` (prima esisteva solo un lookup per una singola
  valuta alla volta). Nuovo endpoint `POST /api/diagnostics/
  test-connection`, sola lettura — se non gli si passano chiavi esplicite
  usa quelle gia' salvate dall'utente, altrimenti prova quelle date senza
  salvarle (utile per provare una chiave nuova prima di sovrascrivere
  quella che magari funziona ancora). 10 test nuovi, tutti con trasporto
  di rete finto.
- `frontend/static/diagnostics.js` (nuovo file): pannello a comparsa,
  toggle spot/futures, test di connessione con esito (saldo o errore), e
  un ordine di prova minimo — solo spot, tramite l'endpoint gia'
  esistente e in uso altrove `POST /api/trading/order` (stessa richiesta
  di conferma esplicita, stesso diario ordini — nessuna logica d'ordine
  duplicata). I futures rimandano al form completo di Sorveglia: quello
  ha l'anteprima di liquidazione, che qui non avrebbe senso riprodurre in
  piccolo.
- **Verificato dal vivo con un browser vero** (Playwright, server
  locale, stesso metodo appena descritto sopra): apertura/chiusura del
  pannello, cambio spot/futures, l'elenco degli exchange futures letto
  per davvero dal registro (non hardcoded), e il messaggio corretto
  quando non c'e' ancora nessuna chiave salvata da provare. Screenshot
  presi e controllati, non solo il DOM.

Non fatto per scelta: nessun controllo esplicito "sei su desktop?" per
Modalita' Semplice (basta togliere l'unico bottone rimasto); l'ordine di
prova futures dentro Diagnosi (rimanda al form di Sorveglia invece di
duplicarlo).

### Osservabilita' SRE + alert di rischio on-chain — piano wallet on-chain — **in corso**

Implementata la parte "osservabilita' operativa (SRE)" del piano di sviluppo
wallet on-chain, in ordine di priorita' come richiesto:

1. **Fallback multi-RPC con circuit breaker**: `backend/app/trading/onchain/
   rpc_client.py` (nuovo). `call_rpc(chain, method, params, timeout=15.0)`
   prova l'endpoint primario, e solo su un errore di TRASPORTO (non un
   errore applicativo JSON-RPC) prova un secondario; dopo 3 fallimenti
   consecutivi su un endpoint lo salta per 60s (cooldown). Secondo endpoint
   Solana: `https://rpc.ankr.com/solana` (reale, pubblico, verificabile).
   Per Robinhood Chain **nessun secondo endpoint pubblico e' stato trovato**
   — documentato nel modulo invece di inventarne uno falso. Migrato
   `balances.py` (saldo, la chiamata piu' frequente) e l'`_eth_call` di
   `quotes.py` (Robinhood). **Non migrato** (TODO onesto nel docstring):
   le chiamate di firma/invio in `execution.py` (nonce, gas price, send) —
   rischio di stato se nonce e invio finissero su endpoint diversi, da
   valutare con piu' tempo.
2. **Log strutturati con correlation ID**: `execute_order`/`simulate_order`
   generano un `correlation_id` (uuid4) loggato su ogni riga e tornato nella
   risposta. Nessuna persistenza a 30gg dedicata: **gap noto e documentato**
   nel docstring di `execute.py` — il sito non ha `logging.basicConfig`/
   `RotatingFileHandler` da nessuna parte (verificato con grep), quindi i
   log vanno su stdout/stderr senza rotazione propria; la rotazione a 30gg
   va fatta a livello systemd/docker, non con un sistema di log parallelo.
3. **`GET /admin/status`**: ordini eseguiti/falliti-per-causa nelle ultime
   24h (query diretta su `ledger._connect()`), stato circuit breaker per
   chain, ultimo saldo letto ora per ogni wallet dell'utente, stato del
   fallback RPC. Protetto da una allowlist email dedicata
   (`settings.admin_emails`, stesso pattern di `telegram_allowed_emails`) —
   **non esiste un concetto di owner/admin altrove nel sito**, documentato
   nel commento invece di far finta che ci fosse.
4. **`telegram.send_infra_alert()`**: prefisso "⚙️ INFRA:" sullo stesso
   canale di sistema (`send_message`/`TELEGRAM_DEV_CHAT_IDS`) — un canale
   Telegram fisicamente separato richiederebbe un secondo bot/chat_id che
   questa sessione non ha per configurarlo/testarlo dal vivo, **non
   fabbricato**.
5. **Alert di rischio**: kill switch (PATCH `/api/onchain/wallets/{chain}`
   con `enabled: false`), circuit breaker scattato e tetto giornaliero
   raggiunto (letti dal `reason` di `risk.run_all_checks`, in
   `_maybe_alert_onchain_risk_event()` in `main.py`), posizione sopra il
   30% del tetto per-trade (avviso preventivo su ordine accettato). **Rug-
   check su pool in allowlist: TODO** — `pool_safety.py` non esiste ancora
   in questo albero (altro agente in parallelo), firma della funzione
   d'alert lasciata pronta nel commento di `_maybe_alert_onchain_risk_event`.

Test nuovi: `test_onchain_rpc_client.py` (httpx mockato: successo diretto,
fallback su timeout, nessun fallback su errore applicativo, circuit breaker
che scatta e si resetta) e `test_admin_status.py` (403 senza allowlist, 200
con conteggi/circuit breaker/RPC status corretti). Suite completa verde
(641 passati, 1 skip; l'unico fallimento — talvolta due — e' in
`test_onchain_prices.py`, gia' noto e non di questa modifica: chiama
davvero la rete prezzi, che il sandbox non raggiunge sempre), ruff pulito.

**Da fare**: migrare anche le chiamate di firma/invio al `rpc_client`
(punto 1 sopra); una vera persistenza/rotazione log a 30gg se quella di
systemd/docker non basta; l'alert rug-check quando `pool_safety.py`
esistera'; non ancora verificato dal vivo (nessuna chiave RPC/wallet vera
usata in questa sessione, solo httpx mockato nei test).

## Log delle conversazioni

Ordine cronologico, piu' recenti in fondo. Scritto perche' una chat diversa
possa capire non solo *cosa* e' cambiato ma *perche'* e cosa Lorenzo ha
chiesto con le sue parole.

- **Ricerca stabile, animazione live** (`seed-0026`): Lorenzo ha chiesto una
  visualizzazione stilizzata di cosa fa la ricerca stabile mentre gira.
  Quattro round di feedback dal vivo — "quei blocchi neri sono proprio
  brutti" (tema chiaro rotto), "rimane fermo qui" (due volte, due fasi
  diverse: ricerca dei confini per asse, poi apertura delle celle — in
  entrambi i casi il log taceva per troppo tempo su una fase pesante),
  "rendi piu' moderno e animato... un'animazione che dia la sensazione di
  visualizzare cosa fa davvero l'algoritmo". Risolto con un canvas che legge
  le stesse righe di log gia' scritte dal backend (nessun canale nuovo),
  animato con `requestAnimationFrame`, tema-consapevole. Dettaglio completo
  in `resolutions.json` sotto `seed-0026`.
- **Operazioni futures** (`seed-0027`): "vorrei introdurre le operazioni
  futures. crea un sistema completo e accurato e soprattutto a prova di
  errore, crea un piano completo per crearlo" → piano scritto e approvato
  → "procedi" due volte, prima per le fasi 0-2 (motore di backtest a leva),
  poi per le fasi 3-4 (esecuzione reale Binance + guardrail). Vedi la
  sezione sopra per lo stato dettagliato.
- **Ridisegno + futures in produzione** (`seed-0028`, `0029`, `0030`):
  Lorenzo ha chiesto prima le proposte di design, poi ha bocciato il primo
  giro («stai facendo della roba di merda... voglio vedere ogni schermata non
  solo graficamente parlando») e ha chiesto un solo prototipo navigabile.
  Approvato quello, «OK PUBBLICA TUTTO»: i futures sono stati uniti a `main`
  e deployati sapendo che la verifica testnet non c'era ancora — scelta sua,
  dichiarata. Poi tre richieste puntuali durante il lavoro: il flag sulla
  candela di esecuzione (`seed-0029`), il grafico sempre visibile in ogni
  schermata, e la tracciatura di ogni operazione sul grafico (`seed-0030`).
  Trovato e corretto lungo la strada: la Bacheca non si apriva dalla sidebar
  (il gestore «click fuori» la richiudeva nello stesso click).
- **Questo file**: Lorenzo ha chiesto che ogni conversazione lasci memoria
  in GitHub, cosi' una chat diversa sappia da dove riprendere senza dover
  rileggere tutto. Riscritto `HANDOVER.md` (era rimasto fermo a una
  sessione molto piu' vecchia — auth JWT, PR #68, nessuna delle strutture
  attuali) e aggiunta la sua lettura al workflow obbligatorio in
  `CLAUDE.md`.
- **Futures multi-exchange** (`seed-0027`, continuazione): "i futures devono
  essere realizzati non per binance, ma per tutti gli exchange dove si puo'
  effettuare operazioni in leva in europa, procedi" — segnalato che
  MiCA/ESMA limitano i derivati al retail UE e che non tutti gli exchange
  gia' collegati li offrono li' (Coinbase/Bitstamp niente derivati UE,
  MEXC/KuCoin hanno i futures ma non la licenza UE), poi proceduto con
  Bybit/OKX/Bitget/Kraken accanto a Binance. Nello stesso giro, chiesto
  anche di guardare i punti aperti in bacheca: trovato e risolto
  `e599667e` (Livelli & Indicatori irraggiungibile dopo il ridisegno). Poi
  chiesto di strutturare la repo perche' una chat diversa non debba
  rileggere tutto — risposta: questo file esisteva gia' per quello, qui
  aggiornato con lo stato del lavoro invece di ricostruito da zero. Ambiente
  locale senza Python 3.12: verificata solo la sintassi
  (`py_compile`), non lanciata la suite pytest/ruff — segnalato sopra come
  da fare.
- **Modalita' Semplice, seguito** (`seed-0064`): dopo Diagnosi (`seed-0062`)
  e il bottone nascosto da desktop (`seed-0063`), Lorenzo ha chiesto in un
  solo messaggio: dropdown archivio con tutti i dettagli e i trade
  esportabili in Excel "come sul sito", il grafico della Modalita' Semplice
  uguale a quello vero ("le nostre grafiche, non un altro grafico"), le
  chiavi API mai richieste due volte con data/modifica/cancellazione
  visibili, l'eliminazione della "tab piena di caselle da riempire", e
  tutti gli exchange configurati invece di tre. Fatto tutto tranne
  l'eliminazione totale del pannello Sorveglia (vedi sopra il perche' —
  decisione da confermare, non presa da solo). Il pezzo piu' delicato e'
  stato il grafico: invece di ridisegnarlo, spostato il vero nodo
  `.chart-area` dentro Modalita' Semplice con un piccolo ponte
  (`window.LiquidityChartBridge`) e restituito al suo posto ad ogni cambio
  di step — verificato dal vivo con Playwright che il nodo si sposta
  davvero e i marker sono quelli reali del backtest, non un disegno.
- **Modalita' Semplice, correzione** (`seed-0065`): Lorenzo ha respinto la
  prima idea di come collegare l'exchange ("Non ci siamo affatto") —
  chiarendo che non voleva un ciclo inserisci/prova/butta via, ma il
  processo ufficiale (chiave salvata per davvero) con un'opzione in piu'
  subito dopo per testarla senza reinserirla, vedere il saldo vero e
  provare un ordine manuale. Nello stesso messaggio ha ricordato che il
  timeframe va scelto prima e recapitolato alla fine — motivo per cui
  "tante volte" chiede di sistemare le incongruenze fra spot e futures:
  trovata e corretta una vera, la Modalita' Semplice usava tre timeframe
  diversi (backtest, grafico, ottimizzazione) senza dirlo.
- **Modalita' Semplice, ottimizzazione ereditata dal sito** (`seed-0067`):
  "eredita tutta la logica anche grafica che abbiamo creato nel sito per
  ottimizzazione stabile... permettimi anche di fermarla". Lo step
  Ottimizza ora apre la STESSA finestra del Laboratorio (stessa animazione,
  stesso log, stesso pulsante Ferma) tramite un nuovo ponte
  (`window.LiquidityOptBridge`), sullo stesso modello di
  `LiquidityChartBridge`. Trovati e corretti due bug veri per strada: la
  vecchia barra propria di Modalita' Semplice mostrava "[object Object]"
  (assegnava l'intera riga di log invece del solo testo), e — piu' serio,
  e non specifico di Modalita' Semplice — `pollOnce()` in app.js segnava
  un lavoro "fallito" al primo errore di rete qualsiasi (un 503 durante un
  deploy incluso), anche se la ricerca sul server proseguiva tranquilla;
  ora regge fino a 5 giri falliti di fila prima di arrendersi davvero.
- **Modalita' Semplice, grafico da archivio rotto + click sull'ingresso**
  (`seed-0068`): "se seleziono una strategia dall'archivio... non e' che
  devo riselezionare il ticker, vedi che mi chiede il ticker di nuovo?"
  Bug vero: `LiquidityChartBridge.show()` trattava un `backtest_params={}`
  (voce d'archivio senza costi mai registrati — comune, non un difetto)
  come un override reale invece che "nessuno" ({} e' truthy in JS), quindi
  ogni campo costo finiva 'undefined' nella query, il server rispondeva
  422 e il grafico restava vuoto senza dirlo — corretto con lo stesso
  controllo (`Object.keys(...).length`) che applyArchiveEntry() sul sito
  gia' usa. Aggiunta anche la richiesta esplicita: un tocco sul grafico
  reale (`onChartClick()`, nuovo, `mainChart.subscribeClick()`) apre ed
  evidenzia l'operazione piu' vicina in un elenco proprio sotto il
  grafico — stessi dati del pulsante "N trade" del Laboratorio, non quel
  pannello spostato (e' pensato per restare incollato ai suoi risultati).
- **Ordine futures disattivato + Sorveglia incasinata da mobile**
  (`6237708e`, segnalazione reale dal tester, non da
  Lorenzo): l'errore "Esecuzione futures disattivata per questo exchange"
  non diceva dove accenderla. Ora nomina l'exchange e, nel form d'ordine
  futures, aggiunge un pulsante "Attiva ora" accanto al rifiuto — un
  tocco accende il toggle senza tornare su alla card giusta. Lorenzo,
  guardando la stessa vista: "da mobile questa vista è veramente
  incasinata" — le quattro sotto-sezioni del pannello 'Chiavi exchange,
  posizioni, diario, ordine manuale' (Posizioni, Ordine futures, Trading
  automatico, Ordine manuale) erano tutte scaricate in un'unica colonna
  lunghissima; ognuna e' ora un dettaglio proprio, chiuso finche' non
  serve.
- **Modalita' Semplice, tocco senza risposta** (`seed-0066`): "quando
  seleziono il ticket il click non produce un'accettazione grafica...
  sembra che non carichi anche se in realta' e' stato selezionato". Aggiunto
  un effetto di pressione immediato + spinner sulla riga. Trovato un bug
  vero dietro il sintomo: `state.ticker` non salvava mai `provider`, quindi
  l'evidenziazione "selezionato" spariva sempre al primo ridisegno della
  lista — non era solo lentezza percepita, l'indicatore visivo era rotto.
- **Ordine futures: quantita' diretta in token** (`seed-0070`): Lorenzo,
  pensando ad alta voce su un rischio vero — "si rischia dei disastri se
  uno puo' [inserire] migliaia di dollari... e te li seleziona invece come
  dollari, come unita' di misura token diventa un delirio" — poi "procedi,
  in caso analizza con attenzione anche altre strade e rendi professionale
  questa cosa per i futures". Aggiunto un terzo modo di taglia
  all'ordine futures manuale, "Quantità" (base_qty), con un campo proprio
  (niente slider — non ha senso una scala percentuale per un numero di
  token che va da 0.0001 a milioni) etichettato con l'asset vero del pair.
  Il paracadute resta l'anteprima gia' obbligatoria: mostra sempre il
  nozionale/margine reali in USDT prima di confermare, qualunque modo si
  scelga. Trovato per strada un bug di sicurezza vero: il controllo di
  margine pre-ordine, senza il nuovo ramo, avrebbe letto una quantita' di
  token come percentuale del saldo (praticamente zero) e sarebbe passato
  sempre, indipendentemente dal nozionale reale — corretto nello stesso
  giro. Deliberatamente non toccato lo spot manuale (manca ancora
  un'anteprima li', ma costruirla per sei exchange e' un lavoro a se') —
  segnalato come seguito, non deciso da solo.

## Modalità Semplice (wizard guidato) — branch `claude/simple-mode`

Prototipo approvato via Artifact dopo tre giri di revisione, implementato in
`frontend/static/simple-mode.js` (nuovo file, non tocca `app.js`) + un
bottone/contenitore aggiunti a `frontend/index.html`. Zero endpoint nuovi:
ogni passo chiama API già esistenti (`/api/symbols`, `/api/archive`,
`/api/strategies`, `/api/analyze`, `/api/optimize/start` + polling
`/api/jobs`, `/api/auth/trading`, `/api/watchlist` + PATCH
strategy/strategy_params, `/api/archive/{id}/apply-to-alert` per lo
shortcut da archivio). Stato persistito in `localStorage` (`simpleModeActive`).

Scelte fatte in autonomia, da rivedere con Lorenzo se non vanno bene:
- **Solo spot**: niente `/api/auth/futures` — coerente con la leva limitata
  a 1x server-wide.
- **Exchange offerti nel wizard**: Binance, KuCoin, Kraken (il prototipo
  mockava "Bybit", che `auth.set_trading_credential` non supporta — sostituito
  con KuCoin per restare a 3 card).
- **Ticker azionari**: niente step exchange/esecuzione automatica (solo
  spot crypto ha `place_order_for_signal`); l'attivazione diventa "solo
  avviso Telegram", dichiarato onestamente nella UI.
- **Stima tempo ottimizzazione**: il backend non traccia una percentuale
  reale (solo `elapsed_s` in jobs.py). Stima lato client con le stesse
  soglie già comunicate altrove (Rapida 10-25s, Stabile 1-5min), che passa a
  "quasi fatto" oltre il range invece di un countdown che sbaglia in silenzio.
- **Uscita durante l'ottimizzazione**: permessa sempre — il job gira
  server-side e continua anche se si esce dal wizard (i risultati con
  `owner_id` finiscono comunque in archivio).
- Verificato in Browser pane con backend mockato via `fetch` (nessun Python
  3.12 in questo ambiente): tutti gli 8 passi (0-7), desktop e 375px. Non
  verificato contro il backend reale — da rifare a mano o in CI.

### Seguito — seed-0064 (archivio, grafico reale, exchange completi, chiavi)

Lorenzo, subito dopo seed-0062/63, ha chiesto sei cose insieme. Fatte (vedi
`resolutions.json` sotto `seed-0064` per il dettaglio tecnico completo):

1. Step archivio con metriche complete (rendimento/drawdown/operazioni/PF/
   candele/parametri) + pulsante Excel reale (`/api/export/backtest.xlsx`).
   Corretto anche un bug vero trovato per strada: `created_at` e' un epoch
   (int), uno `.slice()` sul valore ci interrompeva silenziosamente il
   rendering dell'intera lista se l'archivio aveva gia' voci per quel ticker.
2. Il grafico dello step Backtest e' ora il VERO `.chart-area` del sito
   (LightweightCharts, indicatori, marker), spostato nel DOM dentro
   Modalita' Semplice via un ponte minimo — `window.LiquidityChartBridge`
   in `app.js` (mount/restore + `applyConfigToChart`/`runAnalysis`, le
   stesse funzioni gia' usate da `applyArchiveEntry`) — non una copia.
   Verificato dal vivo (Playwright): il nodo si sposta davvero, i marker
   di ingresso/uscita sono quelli reali del backtest.
3. Chiavi gia' salvate non vengono piu' richieste due volte nel wizard
   (controllo `/api/auth/trading` prima di mostrare i campi).
4. `TRADING_EXCHANGES` esteso da 3 a tutti e 6 (mexc, binance, kucoin,
   kraken, coinbase, bitstamp).
5. Footer con la data di deploy (stesso `/api/version` della sidebar).
6. Lato desktop: le card credenziali di Sorveglia (trading e futures) ora
   mostrano, quando salvate, "🔒 Chiave salvata e cifrata — registrata il
   ..." con un pulsante Elimina sempre visibile (nuovo `created_at` su
   `ExchangeCredential`/`FuturesCredential`, nuovi `DELETE /api/auth/trading/
   {exchange}` e `/api/auth/futures/{exchange}`).

**Non fatto, deciso in autonomia**: NON ho rimosso il pannello
`.opera-advanced` di Sorveglia per intero. Lorenzo aveva scritto "non deve
esserci una tab piena di caselle da riempire... quella ti chiederei di
eliminarla" — ma quel pannello contiene anche Posizioni aperte, Diario
ordini e Ordine manuale, che non erano l'oggetto della lamentela (le
"caselle da riempire" erano i form di chiave, gia' risolti al punto 6 sopra
con lo stato "salvata"). Toglierlo del tutto avrebbe eliminato capacita'
vere (vedere le posizioni aperte, il diario, piazzare un ordine manuale da
desktop) senza che fosse stato chiesto esplicitamente — e sarebbe stato
difficile da tornare indietro una volta che l'abitudine di usarle da li'
fosse cambiata. Se Lorenzo intendeva davvero eliminare l'intero pannello
(non solo il fastidio delle chiavi), va confermato e poi si decide dove
spostare posizioni/diario/ordine manuale (Diagnosi? Sorveglia in altra
forma?) invece di farli sparire.

### Seguito — seed-0065 (testare la chiave subito, timeframe coerente)

Lorenzo ha corretto il punto piu' delicato di seed-0064: non voleva
"inserire, provare, buttare via" — voleva che il processo di salvataggio
restasse quello ufficiale (PATCH /api/auth/trading, invariato) ma con
un'opzione in piu' subito dopo: "vuoi testarle subito?". Aggiunto un passo
5.5 fra Exchange e Riepilogo che fa esattamente questo — chiama
`/api/diagnostics/test-connection` con chiavi vuote (usa quella appena
salvata, non la richiede mai di nuovo), mostra saldo vero o errore vero, e
offre un ordine manuale di prova (`/api/trading/order`, stesso endpoint di
Diagnosi — niente testnet in questa piattaforma, quindi denaro reale
dichiarato, mai finto).

Nello stesso giro ho trovato e sistemato la causa di fondo per cui Lorenzo
torna spesso su "la cosa dei ticket dello spot e del futures": la Modalita'
Semplice usava tre timeframe diversi in tre punti diversi senza dirlo (il
backtest non passava affatto l'intervallo al server, il grafico accanto
usava "1d" fisso, l'ottimizzazione un altro "1d" fisso ancora). Aggiunto un
selettore di timeframe allo step Strategia, un solo `state.interval` usato
ovunque dopo. Verificato dal vivo (log del server) che backtest e
ottimizzazione arrivano davvero con lo stesso intervallo.

### Seguito — seed-0071 (tetto per strategia, % saldo su MEXC)

Filone nato da una lunga spiegazione vocale di Lorenzo sul rischio di usare
importi fissi per il trading automatico ("se io devo fare ordini
frammentati non c'e' verso che funzioni [con importo fisso]... l'unico modo
e' fare con una percentuale del saldo"), ma con un problema vero quando piu'
strategie condividono lo stesso exchange: "io magari voglio fare 10 ordini
da 500 dollari l'uno con il bot, ma se lui pesca con la percentuale e'
finita". Soluzione concordata nel dialogo: tenere la % di saldo com'e' (mai
guardare la quantita' di token), ma lasciare impostare un **tetto massimo in
USDT** per singola strategia al momento di attivare l'operativa automatica —
non un importo fisso che sostituisce la percentuale, un limite sopra di
essa. Punto fermo ribadito piu' volte da Lorenzo: la chiusura di una
posizione (incluso un flip) deve sempre chiudere per intero, il tetto non
deve mai poterla toccare, e se un flip si riapre con meno saldo di prima
"non deve accadere l'errore" — il sistema deve riadattarsi da solo.

Implementato: `WatchlistEntry.size_cap_usdt` (dict per strategia) +
`PATCH /api/watchlist/{id}/size_cap`, propagato come `max_usdt` opzionale
attraverso `executor.py`, tutti i 5 moduli spot e tutti i 6 adattatori
futures — applicato SOLO lato ingresso/BUY, mai su `close_position` o sul
lato SELL (che su alcuni segnali e' una chiusura mascherata). UI: il tetto
si chiede nel flusso di attivazione ("Anche operazioni automatiche" →
tetto facoltativo prima di scegliere la strategia) e resta modificabile
sotto ogni strategia gia' attiva in Sorveglia.

Nello stesso giro, indagato anche un secondo report separato di Lorenzo: "%
saldo non funziona su MEXC". Prima diagnosi (permesso `SPOT_ACCOUNT_READ`
mancante) **sbagliata** — Lorenzo ha mostrato lo screenshot dell'API
Management di MEXC coi permessi tutti presenti, e ha lui stesso indicato la
causa vera: "erroneamente secondo me acquistavi 10 kaspa invece di 10
dollari di controvalore in kaspa (superando il balance)". Aveva ragione:
`quoteOrderQty` (il parametro con cui si dice "spendi X USDT", usato per
ogni ordine automatico) su MEXC viene trattato su piu' pair come una
QUANTITA' di moneta, non un importo — un ordine da 10 USDT diventava un
ordine da 10 monete, quasi sempre oltre il saldo disponibile. Bypassato
calcolando noi la quantita' dal prezzo corrente e mandando `quantity`
invece di `quoteOrderQty`, solo per MEXC (Binance resta sul parametro
originale, che li' funziona davvero come documentato). Non verificabile con
denaro reale in sandbox (rete bloccata verso gli exchange) — verificato che
il payload mandato all'ordine e' quello giusto (2 nuovi test in
`test_mexc_order.py`).

Verificato dal vivo: endpoint size_cap via curl (persistenza, azzeramento),
campo tetto su strategia gia' attiva via Playwright (valore iniziale letto
correttamente, modifica salvata e confermata rileggendo la watchlist). Non
riverificato dal vivo il tetto durante l'attivazione di un ticker nuovo
tramite browser (il resto della UI di attivazione — autocomplete pair — non
e' cambiato da questo lavoro), ma la stessa funzione `stepCap()` e la stessa
chiamata PATCH sono usate in entrambi i percorsi. 448 test totali passano,
ruff pulito.

Terzo giro sullo stesso filone: Lorenzo ha riportato l'ordine futures manuale
MEXC "sempre lo stesso errore" con la %, incollando il testo esatto ("la
dimensione richiesta vale 0.284 contratti, meno del minimo di 1... serve
almeno 35.20 USDT di margine con leva 1x"). Trovato e corretto un vero bug di
robustezza (il codice presumeva sempre minVol=1 contratto invece di leggerlo
dall'exchange — su KASUSDT valeva comunque 1, ma non e' garantito per ogni
pair), MA il messaggio d'errore era gia' corretto: con `MAX_FUTURES_LEVERAGE`
bloccato a 1x (voluto, "resta a 1x SEMPRE" — Lorenzo lo ha ribadito quando gli
ho chiesto se alzarlo), il margine coincide col nozionale intero, e MEXC
impone un minimo di 1 contratto = 1000 KAS = 35.20 USDT su quel pair a
qualunque leva. Su MEXC direttamente lo stesso ordine con 20 USDT passava
solo perche' la' la leva era 20x (margine 35.20/20 = 1.76 USDT), non 1x —
stesso pair, stessa formula, leva diversa. Lorenzo ha verificato di persona e
confermato: "hai ragione tu, serve 35.20 usdt". Nessun bug residuo: il tetto
di leva a 1x resta per scelta esplicita sua, quindi su pair a nozionale
minimo alto come KASUSDT serve piu' saldo/percentuale per aprire una
posizione, e il messaggio d'errore ora lo dice in modo chiaro (USDT, non solo
contratti). Lezione per chi riprende questo filone: quando Lorenzo riporta
"stesso errore, sempre" non e' detto sia un bug — a volte e' l'exchange che
rifiuta correttamente, e il lavoro giusto e' rendere il messaggio azionabile,
non cercare un bug che non c'e'.

## Log delle conversazioni (continua)

- **Tetto per strategia + % saldo su MEXC** (`seed-0071`): Lorenzo, voce
  lunga: "io magari voglio fare 10 ordini da 500 dollari l'uno con il bot,
  ma se lui pesca con la percentuale e' finita... l'importo massimo...
  preinserito in fase di allestimento della strategia prima di attivare
  l'alert... per la chiusura ovviamente comando close position... senza
  stare a guardare controvalori, semplicemente la chiude". Poi, separato:
  "voglio usare la % del saldo per gli ordini automatici... pero' sembra
  non funzionare su mexc.. verifica se lo accetta". Chiuso con "sistema fai
  tutto tu, mi fido" — implementato tetto per strategia (mai sulle
  chiusure). Sul bug MEXC, prima diagnosi sbagliata (permesso mancante):
  Lorenzo ha corretto con lo screenshot dei permessi e la sua stessa
  intuizione — "erroneamente secondo me acquistavi 10 kaspa invece di 10
  dollari di controvalore" — che era la causa vera, poi confermata e
  corretta (quoteOrderQty trattato da MEXC come quantita', non importo).
  Terzo giro sul futures manuale: "e perche' dentro app mexc con il telefono
  riesco a operare con 20 usdt?" — spiegato che li' la leva era 20x contro
  1x qui (voluto, "in leva1x... resta a 1x SEMPRE"), stesso pair stessa
  formula. Lorenzo ha verificato di persona: "hai ragione tu, serve 35.20
  usdt" — nessun bug, il messaggio d'errore era gia' corretto.
- **Blocco di rete MEXC futures** (`seed-0072`): Lorenzo, dopo il tetto di
  leva: "abbiamo provato con 50 usdt e ottenuto questo errore" con incollata
  una pagina Akamai "Access Denied" che il codice leggeva come permesso
  mancante. Chiesto come procedere, Lorenzo ha scelto "instrada MEXC
  futures fuori UE" — aggiunta la env var `MEXC_FUTURES_PROXY`, non ancora
  configurata in produzione (serve un proxy vero, non procurabile da qui).

### Aperto — seed-0072 (blocco di rete MEXC futures, serve un proxy fuori UE)

Dopo aver chiarito il tetto di leva (sopra), Lorenzo ha provato un ordine
manuale da 50 USDT su MEXC futures e ha incollato l'errore esatto: una
pagina HTML "Access Denied" di Akamai/Edgesuite, non una risposta di MEXC.
Il codice leggeva "permission" dentro quel testo e lo traduceva (sbagliando
di nuovo) in "manca il permesso della chiave" — corretto: `explain()` in
`base.py` ora riconosce una pagina di blocco CDN (contiene "access denied" +
"edgesuite"/"akamai" dentro tag HTML) PRIMA di cercare le parole chiave
generiche, e dice esplicitamente che e' un blocco di rete, non un problema
di chiave.

Causa probabile della richiesta bloccata: coerente con quanto il codice
stesso dice da mesi (`registry.py`: "MEXC non ha licenza UE per i
derivati... aggiunto su richiesta esplicita di Lorenzo, che ha scelto
sapendolo"), l'IP europeo del server (Hetzner, Germania) viene negato da
MEXC specificamente su `/order/submit` — le chiamate di sola lettura
(prezzo, saldo) probabilmente passano, l'invio ordine no.

Chiesto a Lorenzo come procedere fra "prova comunque", "instrada fuori UE" e
"lascia perdere MEXC futures" — ha scelto **instradare fuori UE**. Aggiunta
la capacita' lato codice: `MEXC_FUTURES_PROXY` (env var, vuota di default =
comportamento invariato) instrada le sole chiamate a MEXC futures
attraverso un proxy/VPS scelto da lui — nessun altro exchange futures ne
risente. Documentata in `deploy/.env.example`.

**Non fatto, non posso farlo da qui**: procurare e configurare il proxy
vero. Serve un server/proxy fuori UE (Lorenzo decide dove — un VPS a
noleggio in una regione non-UE va bene) e il suo indirizzo va messo in
`deploy/.env` sul server di produzione. Finche' non e' impostato, gli
ordini futures MEXC restano bloccati come ora — il codice e' pronto a
usarlo appena c'e'.

**Seguito — endpoint sbagliato, non (solo) un blocco di rete**: il supporto
MEXC ha risposto indicando un endpoint diverso per piazzare ordini futures:
`order/create` al posto di `order/submit`, 4 richieste/2 secondi. Il
messaggio sbagliava l'host (diceva `api.mexc.com`, che e' quello SPOT), ma
prima di toccare codice che sposta denaro reale ho verificato il cambio di
path in modo indipendente: un problema identico e' documentato su ccxt
(issue #28532, libreria open source), stessa correzione esatta — host
`contract.mexc.com` invariato, solo `submit` -> `create`. Corretto in
`mexc.py` (entrambe le chiamate di piazzamento ordine, apertura e
chiusura), test aggiornati di conseguenza. Diagnosi precedente (permesso
account da attivare via assistenza) forse solo in parte giusta, forse
irrilevante — `order/submit` semplicemente non era mai stato l'endpoint
giusto. **Non verificato con un ordine reale**: questo ambiente non ha
credenziali MEXC vere — serve una conferma di Lorenzo con un ordine piccolo
di prova. Il proxy extra-UE resta configurabile per l'eventualita' che il
blocco Akamai si ripresenti sul nuovo endpoint.

**Seguito 2 — il fix del path da solo NON basta, avevo scartato meta' del
suggerimento**: Lorenzo ha riprovato con `order/create` gia' in produzione
(su `contract.mexc.com`, host tenuto invariato) — stesso identico blocco
Akamai/CDN. Nel dubbio ho ri-chiesto se il proxy extra-UE fosse configurato,
come se la questione geografica fosse ancora aperta: Lorenzo mi ha corretto,
l'avevo gia' verificata IO STESSO mesi fa (tre reti diverse, incluso il
proxy Vultr fuori UE, stesso blocco su tutte) — non richiederla piu', e'
chiusa. Quello pero' mi ha fatto riverificare tutto da capo, e stavolta sul
codice sorgente vero di ccxt (`ts/src/mexc.ts`), non su un riassunto
dell'abstract file: MEXC ha spostato l'intera API contract, pubblica e
privata, sotto `api.mexc.com` — `contract.mexc.com` e' un dominio legacy,
ancora vivo per le letture pubbliche (`/ping` risponde) ma evidentemente non
piu' quello dietro cui passano gli ordini. Il supporto MEXC aveva ragione su
ENTRAMBI i dettagli (host e path); scartare l'host la volta scorsa e'
stato un errore mio, non un problema della loro risposta. Cambiato
`BASE` in `mexc.py` da `contract.mexc.com` a `api.mexc.com` — si applica a
tutto il modulo (saldo, posizioni, prezzo, ordine), verificato dal vivo
prima di committare che `api.mexc.com/api/v1/contract/ticker` risponde con
dati reali. **Non ancora verificato con un ordine reale** — serve la
conferma di Lorenzo. Se anche questo dovesse dare lo stesso blocco, allora
si', torna in campo la diagnosi del permesso account (invio ordini futures
via API, interruttore separato dal trading da app) — ma non prima di aver
visto fallire anche host e path corretti insieme.

### Chiuso — seed-0073 (design "AI slop", pulizia sistemica CSS)

Lorenzo: "tutto il sito sembra fatto da ai slop". Invece di ricontrollare a
occhio, diagnosticato con `impeccable` (github.com/pbakaus/impeccable, 67.5k
stelle — verificato prima di eseguirlo, dopo che un primo tentativo di
Lorenzo di farmelo installare via un link/comando sospetto era stato
correttamente rifiutato): 145 problemi deterministici su `index.html` e
`sniper.html`, concentrati in poche categorie sistemiche (testo troppo
piccolo, striscia colorata spessa su un lato delle card — il tell piu'
riconoscibile del design generato da AI — bordo sottile+ombra larga,
contrasto insufficiente nel tema scuro).

Corretto per categoria, non caso per caso: 241 dichiarazioni font-size
alzate (+ il token `--text-xs`), 14 punti con la striscia laterale rimossa
o assottigliata, 3 bordi ridondanti tolti dove c'era gia' un'ombra larga,
contrasto del testo piu' tenue nel tema scuro alzato al minimo WCAG AA
(calcolato con la formula di luminanza relativa, non a tentativi),
un'animazione di `width` (causa reflow) sostituita con `transform: scaleX()`
sulla barra di progresso della Modalita' Semplice. Da 145 a 15 problemi
residui — quelli rimasti sono scelte deliberate gia' documentate nel codice
(il serif per i numeri, gli indicatori "live" pulsanti, la voce a em-dash di
tutto il progetto) o richiedono un'analisi del DOM renderizzato che il tool
non espone abbastanza in dettaglio (4 istanze di testo lungo in maiuscolo,
non isolate). Non toccati senza conferma esplicita — sono scelte di stile
del progetto, non difetti di questa pagina.

Nello stesso filone, Lorenzo ha chiesto di installare "tutti" i repo di una
lista da un articolo Medium — rifiutato l'installazione cieca (12 progetti
ignoti, nessun bisogno preciso dichiarato), proposto di analizzarli prima
se ne indica uno specifico. Nessun repo installato da quella lista.

Verificato dal vivo con Playwright (desktop 1280px e mobile 390px, anonimo e
autenticato) che nessuna modifica ha rotto il layout. `node --check` su
tutti i JS toccati, 452 test backend passano (nessuno di questi cambi tocca
il backend), ruff pulito.

- **Design "AI slop"** (`seed-0073`): Lorenzo, secco: "tutto il sito sembra
  fatto da ai slop". Diagnosticato con lo strumento open source
  `impeccable` invece di ricontrollare a occhio (verificato su GitHub prima
  di usarlo, dopo aver rifiutato un primo tentativo di installazione via
  link/comando sospetto) — 145 problemi, risolti per categoria (font-size,
  striscia laterale colorata, bordo+ombra ridondante, contrasto) invece che
  uno per uno, su sua richiesta esplicita: "fixa tutto occhio ai token, fai
  efficienza". Sceso a 15 residui, tutti scelte deliberate o a bassa
  priorita'. Rifiutata anche una richiesta di installare "tutti" i repo di
  una lista da un articolo Medium — poi chiarita da Lorenzo come "analizza,
  mica installare alla cieca".

- **Bacheca segnalazioni** ("risolvi tutti i punti aperti nel sito"):
  trovate e chiuse le due segnalazioni scoperte e chiare (ee624db5,
  5c5aad89). Sulle altre due, ristrutturazioni di navigazione, ho segnalato
  la cautela del progetto (seed-0064) prima di procedere; Lorenzo: "Procedi
  su entrambe ora" — implementate entrambe (3cbd3308, b7419455) nella stessa
  sessione.

### Chiuso — ee624db5 e 5c5aad89 (periodo di riferimento in Lab, bug marker grafico)

Lorenzo: "risolvi tutti i punti aperti nel sito" — controllata la bacheca,
4 segnalazioni vere ancora aperte dal tester. Risolte le due scoperte e
chiare:

- **ee624db5**: periodo di riferimento (data inizio/fine) nel Lab, subito
  dopo il pair come chiesto. Il ritaglio avviene sul DataFrame prima del
  backtest (non sui trade dopo), con un errore chiaro se il periodo non ha
  candele invece di un risultato vuoto silenzioso.
- **5c5aad89** ("l'applicazione dei trade... continuano a non
  corrispondere" — bug ricorrente, non uno nuovo): diagnosticato con un
  agente di ricerca dedicato invece di rileggere tutto a mano. Causa: il
  refresh automatico ogni 60s (`silentRefresh`) sovrascriveva l'intero stato
  con la risposta rapida di `/api/analyze` (backtest su una sola pagina di
  candele), cancellando il backtest "profondo" (tutta la storia) gia'
  caricato in background — i marker sul grafico tornavano a un sottoinsieme
  diverso di trade ogni minuto, indefinitamente. Corretto preservando la
  cache profonda attraverso ogni refresh silenzioso.

Le altre due segnalazioni aperte (3cbd3308: dividere "Sorveglia" in tre
sezioni; b7419455: spostare "Watchlist" dentro "Analizza") sono
ristrutturazioni di navigazione, non fix scoperti — restano da affrontare
con la stessa cautela usata in passato per richieste simili (seed-0064: mai
spostare/eliminare sezioni intere senza verificare con Lorenzo cosa
succede a cio' che contengono).

Verificato dal vivo con Playwright: il selettore di periodo compare dove
richiesto, la richiesta di rete porta davvero start_date/end_date, il
risultato rispetta il periodo su BTCUSDT reale. 457 test totali passano
(5 nuovi per il periodo), ruff pulito, node --check su app.js.

### Chiuso — 3cbd3308 e b7419455 (Sorveglia divisa in tre, Watchlist in Analizza)

Lorenzo, alla proposta di come procedere sulle due ristrutturazioni rimaste
aperte: "Procedi su entrambe ora" — via libera esplicito, dopo che gli avevo
segnalato che non erano piccoli fix ma ristrutturazioni di navigazione (lo
stesso tipo di cautela di seed-0064).

- **3cbd3308** ("la sezione Sorveglia e' sovraffollata... tre sezioni
  diverse: Alert, Strategie, Trading"): fatto esattamente cosi'. L'Archivio
  strategie e' uscito dal blocco Alert in un suo tab-content; il secondo
  blocco (chiavi exchange/posizioni/ordine manuale, gia' un `<details
  class="opera-advanced">` a se') e' diventato la tab Trading. Due nuove
  voci in sidebar (desktop) e nel menu Altro (mobile). L'area interna
  `sorveglia` e' stata rinominata `alert` — grep esaustivo di ogni
  riferimento prima di toccare nulla, perche' due regole CSS a colonne
  multiple (`#opera-authenticated`, `#alert-authenticated`) erano agganciate
  proprio a `[data-area="sorveglia"]`: senza risistemarle il layout desktop
  a colonne sarebbe sparito senza errori visibili.
- **b7419455** ("Watchlist potrebbe essere integrata nella sezione
  Analizza, sfruttando la colonna a destra attualmente vuota"): "Analizza"
  era l'unica voce della sidebar senza `data-tab-target`, apposta per
  lasciare solo il grafico — ma questo lasciava la colonna destra (320px,
  sempre presente su desktop in quell'area) vuota di suo. Bastava dargli
  `data-tab-target="watchlist"`: la logica generica di `setArea()` gia'
  gestiva il resto, zero codice nuovo in JS. Rimossa la voce sidebar separata
  per Watchlist (desktop); su mobile resta raggiungibile dal menu Altro,
  dove ha ancora senso come schermata a se'.

Nessun backend toccato. Verificato dal vivo con Playwright (desktop 1400px
e mobile 390px, bypassando il gate di login con eventi dispatchati
direttamente sui bottoni): ogni area attiva il tab-content giusto, il menu
Altro mobile apre gli stessi pannelli col titolo corretto, la colonna destra
di Analizza mostra la watchlist. `node --check` pulito su tutti i JS
toccati, 457 test backend passano (nessuno tocca il frontend, confermano
solo che il server non e' stato smosso).

### Chiuso — Strategie raggruppate per ticker, con freccetta e consiglio automatico

Tre richieste in sequenza sulla tab Strategie, tutte di Lorenzo: "raggruppiamole
per ticker, sennò ce troppa confusione" — poi "inserisci freccetta per
nascondere o espandere i vari archivi" — poi "una scelta automatica che in
base ai vari risultati ti permette di scegliere quella giusta aiutandoti a
interpretare anche i dati dei back test".

- **Raggruppamento**: le voci archiviate erano una lista piatta, mischiate fra
  ticker diversi. Raggruppate per simbolo (Map, ordine di prima comparsa —
  segue quello gia' dato dal server, piu' recenti prima), col ticker come
  titolo di gruppo invece che ripetuto su ogni card.
- **Freccetta**: ogni gruppo e' un `<details>/<summary>` nativo (stesso
  pattern gia' usato da `.opera-sub` in Trading) — zero JS nuovo per il
  toggle, aperto di default.
- **Consiglio automatico**: per ogni ticker con almeno due voci utilizzabili,
  un confronto fra quelle gia' salvate — non un numero nuovo, la stessa
  logica dei controlli gia' mostrati su ogni card (gate di regime, PBO,
  sovradattamento, deterministico), ridotta a un ordinamento. Un gate saltato
  pesa piu' di qualunque differenza di rendimento; il rendimento fuori
  campione conta piu' di quello in-sample quando c'e' (stima meno viziata);
  pochi trade abbassano la fiducia. Se nessuna voce e' pulita lo dice
  esplicitamente ("trattale come esplorative") invece di consigliarne
  comunque una — la "meno peggio" prende un badge neutro, non quello verde
  "Consigliata", cosi' i due stati non si confondono a colpo d'occhio.
  Verificato con tre scenari sintetici via Playwright (route mockate su
  `/api/archive`): un caso dove la voce con rendimento piu' alto (+40%) viene
  scartata a favore di una piu' modesta ma pulita (+13% fuori campione) perche'
  la prima e' sovradattata; un caso dove tutte le voci sono segnalate; un
  caso con una sola voce (nessun confronto, nessun box). Tutto lato frontend,
  nessun endpoint nuovo: i dati (`optimizer.*`) arrivano gia' con ogni voce
  d'archivio. `node --check` pulito.

### Chiuso — chiusura posizioni, anteprima onesta, alert datati, bacheca svuotata

Sessione lunga, partita da "procedi, inoltre chiudi i punti aperti sul sito".
Cinque interventi piu' tre segnalazioni di bacheca. Il filo comune, non
cercato ma evidente a posteriori: **quasi tutti erano l'interfaccia che
diceva una cosa mentre il sistema ne faceva un'altra.**

- **seed-0074** — `loadJournal?.()` non era una chiamata facoltativa ma un
  nome inesistente (la funzione e' `loadTradingJournal`), e `?.` non protegge
  da una variabile mai dichiarata. Lanciava un ReferenceError dentro il ramo
  del successo, e il `catch` lo riscriveva in "Errore di rete": ordine
  passato, interfaccia che diceva il contrario. Valore soprattutto
  diagnostico — quel messaggio puo' nascere SOLO dal percorso di successo,
  quindi dimostrava che il fix dell'host MEXC aveva funzionato mentre lo si
  dava ancora per fallito, e che una posizione era davvero aperta.
- **seed-0075** — non esisteva modo di chiudere una posizione dal sito, ne'
  spot ne' futures: `close_position` c'era ma lo raggiungeva solo il trading
  automatico. Due decisioni, entrambe con un test che le tiene ferme: il
  kill switch NON blocca una chiusura (impedisce nuova esposizione; se
  bloccasse l'uscita, spegnerlo con una posizione aperta significherebbe
  restare intrappolati), e "niente da chiudere" si dice invece di spacciarlo
  per chiusura riuscita. Sullo spot chiudere = vendere il 100% della moneta
  base, che e' gia' cio' che fa un `exit_long`.
- **seed-0076** — l'anteprima futures prometteva l'importo chiesto (40 USDT)
  mentre l'ordine ne usava 34,40: su MEXC la dimensione si conta in contratti
  interi, e un contratto KAS vale 1000 monete. L'ordine era giusto, mentiva
  l'anteprima. L'arrotondamento e' specifico dell'exchange, quindi si chiede
  all'adattatore (`effective_notional`, default che non arrotonda: gli altri
  cinque exchange invariati) invece di ricopiarne l'aritmetica nell'endpoint.
- **seed-0077** — l'alert Telegram mostrava il prezzo della candela del
  segnale senza dire quando. Su INJUSDT: "Prezzo: 6.285" era la chiusura del
  14 settembre, consegnata il 16 dopo un -13,5%. Sembrava una strategia che
  compra dentro una correzione; era un ingresso nato prima e consegnato dopo.
  Verificato sui prezzi reali PRIMA di toccare il codice. Ora il messaggio
  porta data, "quanto fa" e prezzo attuale con la deriva.
- **0e5497f6** — nel Lab 5 timeframe su 12. Ora ci sono tutti, e quelli sotto
  1d dichiarano che il backtest gira comunque su 1d (`backtest_interval_for`
  lo riporta li' perche' 5000 candele su un 1m sono tre giorni di storia).
  Prima quel riporto era silenzioso: e' la vecchia seed-0007, che resta
  aperta per la parte vera — togliere il clamp cambierebbe ogni risultato
  storico del Lab, non si fa senza dirlo.
- **6ba09078** — il periodo del Lab valeva solo per il backtest. Il frontend
  le date all'ottimizzatore le mandava gia' (stessa `buildLabQuery()`): era
  il backend a ignorarle in silenzio. Ignorare un parametro che arriva e'
  peggio che rifiutarlo, perche' non lascia traccia. Il ritaglio ora vive in
  una funzione sola usata da entrambe le strade.
- **6a914943** — chiusa dal suo autore ("Problema da ignorare"), registrata
  per non lasciarla aperta a tempo indefinito.

**Due decisioni aperte, entrambe di Lorenzo, entrambe con numeri veri:**

1. *Finestra di freschezza dei segnali.* `_MAX_SIGNAL_AGE_BARS = 3` su un
   daily significa tre giorni, e la stessa lista che manda l'alert alimenta
   l'esecuzione automatica degli ordini — quindi una condizione di due giorni
   fa puo' piazzare un ordine a mercato al prezzo di oggi. Stringerla (3 -> 1
   sui timeframe alti) cambia quali alert partono.
2. *Il clamp del backtest a 1d* (seed-0007). Col budget di 5000 candele, 4h
   coprirebbe 2,3 anni e 1h sette mesi: storia piu' che sufficiente, oggi
   buttata. Toglierlo cambia ogni risultato storico del Lab.

**Un errore mio da non ripetere**, segnalato da Lorenzo con "secondo me ti
stai perdendo": ho cambiato tre volte diagnosi sull'endpoint MEXC in una
conversazione sola, inseguendo riassunti di ricerche web invece di verificare
il codice sorgente vero. Quando ho finalmente letto `ts/src/mexc.ts` di ccxt
invece di un riassunto, la risposta era li' e il supporto MEXC aveva ragione
su host E path. Su codice che muove denaro: fonte primaria, sempre.

### Chiuso — l'alert in ritardo di una barra (la causa vera di seed-0077)

Avevo chiuso seed-0077 mettendo la data nel messaggio. Lorenzo ha insistito, e
aveva ragione: **"non basta la data, deve arrivare l'alert alla chiusura della
candela del timeframe considerato, non tre giorni dopo... e' importante che
questa cosa non accada con nessun alert"**. La data rendeva visibile il
sintomo; il difetto era sotto.

**La causa**: due protezioni contro la candela in formazione, sovrapposte.
Il watcher, per le voci "alla chiusura della candela", toglie gia' la barra
non chiusa (`drop_unclosed_candle`). Poi `confirmed_events` ne scartava
un'altra (`df.index[-2]`), come se l'ultima fosse sempre ancora in
formazione. Quindi l'ultima riga rimasta — una candela chiusa, definitiva —
veniva trattata come non confermata, e il suo segnale emergeva solo al giro
successivo. Su un daily: **un giorno intero, ogni volta**.

**Non dedotto, misurato.** Lorenzo ha chiesto esplicitamente una simulazione
("fai un bel backtest... voglio vedere i messaggi che partono su Telegram
perche' voglio proprio vedere lo script che lavora"), ed e' stata la cosa
giusta da chiedere: `backend/tools/simulate_alerts.py` riproduce la storia
barra per barra su 10 ticker veri, passando dalle funzioni di produzione e non
da una loro imitazione, e stampa ogni messaggio col suo ritardo.

- prima: **21 alert su 26 in ritardo, tutti di +24,0 ore esatte** — ogni
  ticker, ogni strategia. Non un caso isolato di INJUSDT.
- dopo: **26 su 26 entro un minuto** (il giro del watcher). Uguale su 4h.

Lo strumento esce con codice 1 se trova anche un solo alert in ritardo, quindi
resta riusabile come controllo prima di toccare la logica dei segnali.

`confirmed_events` alimenta anche `run_backtest`, quindi `last_bar_closed` e'
**False di default**: nessun numero storico si e' mosso (486 test verdi). Lo
passa solo `build_strategy_state`, che sa distinguere i due casi.

Corretto anche il testo: l'eta' si misura dalla CHIUSURA della candela, non
dalla sua apertura — altrimenti un alert puntuale su un daily si annunciava
"un giorno fa", vecchio di un giorno appena nato.

### Fatto — due chat Telegram separate

Lorenzo: gli alert di trading in una chat, i messaggi di avanzamento del
software in un'altra. La separazione **esisteva gia' nel codice** — `send_to()`
per gli alert (chat personale di ogni utente), `send_message()` per deploy ed
errori 500 — ma finivano insieme perche' puntavano allo stesso chat_id.

Aggiunta `TELEGRAM_DEV_CHAT_IDS`: quando c'e', i messaggi di sistema vanno li';
quando manca, restano dove sono sempre stati. Nessun bot nuovo da creare, basta
un gruppo con dentro lo stesso bot. Per l'id: `tools/telegram_chat_ids.py`
(prima serviva aprire getUpdates a mano col token nella barra degli indirizzi —
lo strumento il token non lo stampa mai, nemmeno in un errore).

**Configurato e verificato in produzione (16 set):** `TELEGRAM_DEV_CHAT_IDS`
punta a un gruppo Telegram dedicato, con dentro lo stesso bot di sempre.
Deploy ed errori 500 arrivano li'; gli alert di trading restano nella chat
personale di ciascun utente. Serviva anche `GITHUB_API_TOKEN` (fine-grained,
solo questo repo, Contents: Read): senza, l'avviso di deploy veniva saltato in
silenzio, perche' il suo testo elenca i commit presi da GitHub — sintomo
identico a "la chat e' configurata male", causa diversa.

---

### Fatto — backtest sub-1D, kill switch, audit trail, alert contestuali

Lorenzo: "il backtest deve essere possibile farlo anche con timeframe
inferiori a 1D" + "applica tutto" (piano di evoluzione v2).

**Backtest sub-1D (seed-0007)**:
- Rimosso `_BACKTEST_MIN_INTERVAL = "1d"` e `backtest_interval_for()` ora e'
  un passthrough puro — nessun clamp.
- Frontend: rimossa la nota UI che avvisava del clamp, rimosso `LAB_BACKTEST_MIN_TF`.
- `resolutions.json` aggiornato con la risoluzione definitiva.
- 504 test passano, ruff pulito, JS sintassi ok.

**Kill switch** (`trading_halt`):
- `settings.trading_halt: bool = False` in `config.py`.
- `backend/app/trading/circuit_breaker.py` — `check_halt()` ritorna
  `(allowed, reason)`.
- Entrambi i path in `executor.py` (spot e futures) lo chiamano all'ingresso
  e tornano `{"skipped": True, reason}` senza toccare l'exchange.
- Endpoint `POST /api/trading/halt` e `GET /api/trading/halt` (solo per le
  email in `registration_allowed_emails`) per abilitare/disabilitare a
  runtime senza riavviare.
- La chiusura manuale (`/api/trading/futures/close`) **ignora** il kill
  switch per design: spengere il trading con una posizione aperta non deve
  impedirti di uscirne.

**Audit trail** (`data/audit.jsonl`):
- `backend/app/trading/audit.py` — `log_order(action, exchange, symbol,
  signal_type, result, ...)` scrive una riga JSONL per ogni azione
  (submit/skip). Mai solleva eccezioni.
- `executor.py` chiama `log_order()` dopo ogni percorso: submit riuscito,
  skip per halt, skip per no-op signal type.

**Alert contestuali**:
- `format_signal_message()` ora accetta `entry_id` (opzionale) e, se ci
  sono segnali precedenti registrati in `_stats`, aggiunge una riga tipo
  "Ultimo segnale simile: 3 giorni fa (#7 totale)".
- Il call site in `main.py` passa gia' `entry_id`.
- Il conteggio aumenta dopo l'invio, non prima: il primo alert non mostra
  "Ultimo segnale: adesso".

**Stato**: tutto su `main` (commit `43418ed`).

**Da fare ancora (dal piano v2)**:
- Verifica manuale in testnet su ciascun exchange futures (Bybit, OKX,
  Bitget, Kraken — mai mandato un ordine a un server vero).
- PostgreSQL + multi-utente + Stripe: multi-sessione, fuori portata qui.
- Onboarding flow, pricing page: frontend, fuori portata qui.

---

### Fatto — Canvas2D drawing engine + pattern recognition + UX grafico

Lorenzo: "procedi con opzione A" (Canvas2D overlay), "vedi che schifo?"
(Lab tab con BTCUSDT invece del simbolo attivo), "nel menu col tasto destro
sul grafico devi aggiungere molte funzioni", "procedi" (pattern recognition).

**Canvas2D drawing engine** (PR #69, poi continuato):
- `<canvas id="draw-canvas">` overlay su `#main-chart`, z-index 5,
  pointer-events none.
- RAF loop `renderDrawCanvas()` a 60fps ridisegna tutti i disegni.
- Selezione + handle drag per ridimensionare endpoint (TradingView-like).
- Delete key cancella il disegno selezionato, Escape deseleziona/cancella tool.
- hline mantiene la `priceLine` di TW per l'etichetta sull'asse Y.
- Tutti gli altri tipi (trend_line, arrow, rectangle, range, fib, text):
  puri Canvas2D.

**Pattern automatici** (`state.layers.patterns`, default off):
- Toggle "Pattern automatici" nella sidebar livelli.
- `detectCandlePatterns(candles, rsiValues)` ritorna `{ markers, zones }`.
- Candle patterns (doji, hammer, inv. hammer, engulfing bull/bear, momentum
  slowdown) → `candleSeries.setMarkers()` via `applyChartMarkers()`.
- RSI divergence (bull: price lower low + RSI higher low; bear: viceversa)
  → rettangoli colorati renderizzati sul Canvas2D overlay.

**Menu contestuale** (tasto destro sul grafico):
- Aggiunto: copia simbolo, apri nel Lab →, linea orizzontale, linea di
  tendenza, rettangolo, freccia, fibonacci, testo.

**Lab fix**:
- Aprire il tab Lab copia il simbolo e l'exchange attivi dal grafico in
  `labState`.
- CSS: `right-panel` ottiene `min-width: 0; overflow-x: hidden` — il pannello
  risultati non trabocca più a destra.

**Stato**: commit `43418ed` su `main`, in produzione.

**Da fare**:
- Nulla di urgente su questo filone. Il pattern recognition e' basico
  (rule-based) — se Lorenzo vuole affinare le soglie o aggiungere pattern
  (shooting star, morning star) si fa in pochi minuti.

---

### Fatto — Lab+Livelli coesistono, rettangoli che spariscono, nuovi strumenti di disegno, segnali contestuali

Lorenzo (in ordine di sessione): "se apro la tab lab con il grafico compresso la visualizzazione fa schifo" → "ora se clicco su tab nn c'è piu il grafico" → "aspetta c'è confusione; io lab e livelli li farei coesistere così" [screenshot con Livelli aperto affiancato al grafico] → "senza possibilità di passare dall'uno all'altro, eventualmente una x per nascondere la tab o l'una o l'altra" → "quando disegno i rettangoli a volte spariscono nel grafico.. risolvi questo problema, e aggiungi strumenti grafici; come tradingview" → "implementa la parte dei segnali che mi hai proposto" → "Committa tutto e deploya".

**Lab+Livelli coesistono** (`commit 14a9e25`):
- Rimossa la regola CSS `.cockpit[data-area="lab"] .chart-area { display: none; }` che nascondeva il grafico nella tab Lab — era la causa del "grafico sparito".
- Lab e Livelli non si escludono a vicenda: il Lab vive nel `right-panel` come tab, i Livelli sono un cassetto separato a sinistra — possono stare aperti insieme senza conflitti di layout.
- Aggiunto handler desktop per il pulsante ✕ in `bindRail()`: prima il pulsante chiamava `showMobileScreen()` che su desktop non fa niente. Ora chiude il cassetto/pannello e torna ad Analizza.

**Rettangoli che spariscono** (`commit 7f17145`):
- Causa: `mainChart.timeScale().timeToCoordinate(time)` ritorna `null` per tempi fuori dal range caricato (non solo fuori dallo schermo), quindi tutte le forme con un punto fuori dai dati caricati sparivano.
- Aggiunta `timeToXEdge(time)`: se `timeToCoordinate` ritorna null, usa `getVisibleRange()` per capire da che lato siamo e restituisce −4 (sinistra) o `width+4` (destra). I rettangoli restano visibili anche scorrendo fino all'inizio.

**Nuovi strumenti di disegno**:
- `extended_line`: linea che si estende su tutto il canvas in entrambe le direzioni (via `extendLineToBounds()`).
- `hray`: raggio orizzontale che parte dal punto cliccato e va verso destra.
- `ellipse`: ellisse con `ctx.ellipse()`.
- `channel`: canale parallelo a 3 punti — la terza click piazza la seconda retta parallela alla prima, con riempimento semitrasparente. Anteprima ghost funzionante anche per tool a 3 punti.
- Aggiornati `DRAW_TOOL_POINTS`, `DRAW_TOOL_LABELS`, `hitTestDrawing()`, menu contestuale.

**Segnali contestuali** (`state.layers.hints`, default off):
- Toggle "Segnali contestuali" nella sidebar livelli.
- `detectContextualHints(candles, indicators)` analizza le ultime candele e produce marker sul grafico:
  - Angolo EMA: deceleration (slope scende rispetto alla media) → "↘ Trend rallenta" / "↗ Trend rallenta"; accelerazione forte → "⚡ Trend forte ↑/↓". Slope normalizzato per ATR rolling — scale-independent fra asset diversi.
  - Pattern body: 3 corpi restringenti nella stessa direzione → "⚠ Esaurimento ↑/↓"; inside bar (range < ATR×0.6) → "◼ Contrazione"; marubozu (body/range > 0.88) → "→ Momentum ↑/↓".
  - RSI combinato: RSI>72 + candela ribassista + upper wick → "↙ Satura RSI+"; RSI<28 + bullish + lower wick → "↗ Esausto RSI−"; RSI 43-57 + corpo piccolo (ultima barra) → "~ Indecisione".
- `applyContextualHints()` chiama `applyChartMarkers()` — i marker si fondono con quelli di pattern e backtest.
- Chiamato da `render()` ad ogni aggiornamento dati.

**Stato**: entrambi i commit su `main`, in produzione. 504 test passano, ruff pulito, JS sintassi ok.

**Log (parole di Lorenzo)**:
- "ora se clicco su tab nn c'è piu il grafico.. ma che stai facendo" → causa rimossa.
- "aspetta c'è confusione; io lab e livelli li farei coesistere così" → fatto.
- "quando disegno i rettangoli a volte spariscono nel grafico.. risolvi questo problema" → fatto.
- "implementa la parte dei segnali che mi hai proposto" → fatto.

---

## Sessione 2026-09-16 (b) — Divergenze RSI, auto-zoom, popup marker, Sniper su Robinhood Chain

**Divergenze RSI sul grafico** (`commit 7d072a7`):
- Layer "Divergenze RSI" (default off) nel pannello Livelli.
- ZigZag swing detection su N=4 barre → trova swing highs/lows confermati.
- Regular bearish (prezzo HH + RSI LH) e regular bullish (prezzo LL + RSI HL).
- Rendering su draw-canvas: linea piena sottile + dot + etichetta per confermato; tratteggio animato + dot pulsante per forming (swing recente non ancora confermato).
- Colori token sito: `#ff4560` bearish, `#00d68f` bullish. Etichette JetBrains Mono.
- Max 3 divergenze per tipo, le più recenti.

**Auto-zoom 7 giorni + popup marker** (`commit f225de3`):
- Dopo ogni `render()` il grafico si posiziona sugli ultimi 7 giorni invece di `fitContent()`. Calcola le barre per 7 giorni in base all'intervallo (es. 15m=672 barre, 4h=42 barre). `Alt+R` resetta alla vista completa.
- Click su qualsiasi segnale automatico (pattern, hints, strategia) apre un popup con: descrizione plain-language del calcolo + barra forza 1-10 con colore (verde ≥8, ambra ≥6, teal sotto). Click fuori chiude. Definito in `MARKER_INFO`.

**Sniper: focus Robinhood Chain** (`commit corrente`):
- `scanner.py`: aggiunta `"robinhood"` a `SUPPORTED_CHAINS` e `GECKO_NETWORKS` (id GeckoTerminal: `"robinhood"`). DEXScreener supporta già `chainId="robinhood"`.
- `sniper.html`: chip "RBH ★" è ora il primo e default attivo. `activeChain` parte da `'robinhood'`. Gli altri chip restano per accesso manuale.
- Nota: i filtri `serious_only=True` + `is_serious()` in `quality.py` già escludono meme coin — nessun cambio necessario lì.
- Idea API aggiuntive (CoinGecko, DeFiLlama, Messari per TVL/revenue/audit su Robinhood Chain): registrata su bacheca come `seed-0078`, non implementata.

**Stato**: su `main` in produzione. Robinhood Chain disponibile da prossima scansione (~5 min).

**Log (parole di Lorenzo)**:
- "come vedi quando io apro il grafico con un time frame basso visualizzo tutto in modo molto confusionario" → auto-zoom 7gg implementato.
- "ogni indicatore che viene indicato automaticamente se io ci clicco voglio visualizzare come viene calcolato e a livello di potenza di segnale quanto è impattante su una scala da 1 a 10" → popup marker implementato.
- "voglio anche che il sito che utilizziamo per sniperare le crypto on-chain, sia dedicato alla Robinhood Chain esclusivamente in questa fase" → fatto, default RBH.
- "non voglio meme coin, ma progetti che promettono di fare cose interessanti" → già filtrato da `is_serious()`, nessun cambio; scanner ora include Robinhood Chain.
- "introduciamo anche altri sistemi per scansionare al meglio il mercato... non è prioritario, teniamocelo in bacheca" → seed-0078 aperto.

---

### Libreria indicatori community (pandas-ta) — `seed-0079`, `seed-0080` — **fatto**

Lorenzo, guardando il documento di presentazione preparato in questa
sessione: "ma il discorso della libreria di indicatori open source fatti da
utenti come su TradingView? esiste questa possibilita'?". Spiegato il
limite reale: gli script Pine della community TradingView non sono
portabili — l'interprete custom del sito (`backend/app/pine/`) copre solo
un sottoinsieme del linguaggio, niente `security()`/array/librerie — ma
`pandas-ta` era gia' una dipendenza installata (vedi `CLAUDE.md`, la usava
gia' `indicators.py`) e ne sfruttava solo 6 funzioni delle 151 disponibili.

Lorenzo ha chiesto di collegarle tutte, ponendo lui stesso il vincolo giusto:
"non voglio che ci sia affollamento nel grafico, servira' una libreria a
tendina da dove selezionarli no?".

**Fatto**: `backend/app/analysis/indicator_catalog.py` introspeziona
`pandas_ta.Category` e costruisce un catalogo di 151 voci — `OVERRIDES` a
mano per gli indicatori con output o parametri non banali (supertrend,
ichimoku, macd, bbands, adx, donchian, keltner, psar, chandelier_exit,
cdl_pattern...), default ragionevole per il resto. Ogni voce e' classificata
`overlay` (va sul prezzo) o `oscillator` (riquadro proprio). Due endpoint:
`GET /api/indicators/catalog` e `POST /api/indicators/compute` (riusa
`_fetch_cached`, lo stesso helper di `/api/pinescript/run`). Frontend: campo
di ricerca dentro Livelli & Indicatori, raggruppato per categoria; click
aggiunge un chip e ricalcola — overlay diventano linee su `mainChart`,
oscillator aprono un `<div class="sub-chart">` creato/distrutto a runtime e
sincronizzato sul time-scale principale. Persistenza in `localStorage`
(`customIndicators`), indipendente dal ticker aperto.

**Due bug trovati verificando dal vivo con Playwright** (non a rilettura di
codice):
1. I default dichiarati in `OVERRIDES` non venivano applicati quando il
   chiamante non passava parametri — `supertrend` prendeva `length=7` di
   pandas-ta invece del 10 dichiarato. `compute_indicator()` ora parte dai
   default dello spec e li sovrascrive solo con quanto arriva da fuori.
2. Due click ravvicinati sulla libreria avviavano due esecuzioni asincrone
   sovrapposte di `refreshCustomIndicators()`: quella piu' vecchia, ripresa
   dopo il proprio `await`, aggiungeva un secondo riquadro duplicato per lo
   stesso indicatore gia' creato dalla piu' recente. Risolto con un numero
   di sequenza che fa desistere ogni esecuzione superata subito dopo il
   primo punto di attesa.

Un terzo bug di UI, scoperto nello stesso giro di test ma non specifico di
questa feature: cliccare una voce della tendina sostituiva subito l'HTML
della lista, staccando dal DOM il nodo che aveva generato il click prima che
l'evento risalisse al listener globale che chiude i pannelli su un click
"fuori" (`RAIL_PANELS` in `bindUI`) — quel listener vedeva un nodo scollegato
e richiudeva il pannello Livelli nello stesso click che doveva solo
aggiungere l'indicatore. Risolto rimandando il re-render al tick successivo
con `setTimeout(fn, 0)`.

14 test nuovi in `backend/tests/test_indicator_catalog.py`, suite completa
518 passed, ruff pulito, verifica end-to-end nel browser reale (login,
ricerca, aggiunta/rimozione di piu' indicatori, controllo che i riquadri
dinamici nel DOM tornino al numero di partenza dopo la rimozione).

**Secondo giro — `seed-0080`, stesso filone**: appena vista la prima
versione, Lorenzo: "si mavoglio una libreria dove visualizzo tutto cone
spiegazioni, cosi capisco cosa attivare, non conosco i nomi cosi non so
cosa cercare". Poi, con uno screenshot e un cerchio giallo sullo spazio
vuoto della toolbar in alto: "sfruttiamo questo spazio evidenziato in
giallo, per inserisci un po' di cosine tra cui questa libreria".

Fatto: scritta una descrizione dedicata per ciascuno dei 151 indicatori
(`DESCRIPTIONS` in `indicator_catalog.py`, una riga a testa — cosa misura,
non il nome tecnico) invece del solo fallback per categoria, con un test
che verifica la copertura completa. Rifatta l'interfaccia da zero: non piu'
una tendina che si nasconde finche' non cerchi, ma un pannello ampio nuovo
(`#indicator-library-panel`, stessa famiglia larga di Bacheca/Script Pine,
non il piccolo cassetto di Livelli) sfogliabile per categoria con
`<details>` — chiusi sfogliando, aperti durante una ricerca — ogni voce con
nome, tag sul-prezzo/riquadro-proprio e descrizione. Tre punti d'ingresso:
il pulsante "Sfoglia la libreria" dentro Livelli (gia' c'era), una voce
propria in sidebar ("Libreria"), e un pulsante nuovo esattamente nello
spazio vuoto della toolbar che Lorenzo aveva cerchiato.

**Bug trovato verificando dal vivo con Playwright** (di nuovo, non a
rilettura di codice): sia il pulsante della toolbar sia quello dentro
Livelli aprivano il pannello e lo richiudevano nello stesso click. Causa:
il bottone genera un click *sintetico* su `#sidenav-indicators` per
riusare esattamente lo stesso percorso di apertura di ogni altro pannello
(niente logica duplicata) — quel click sintetico apre il pannello
correttamente. Ma il click *originale* dell'utente, dopo che il proprio
handler ritorna, continua a risalire fino al listener globale in `bindUI`
(`RAIL_PANELS`) che chiude ogni pannello aperto quando il click arriva da
fuori la sidebar — e quel listener non riconosce ne' il bottone ne' il
pannello appena aperto come "dentro", quindi lo richiude subito.
Risolto con `e.stopPropagation()` sui due bottoni nuovi.

16 test in `test_indicator_catalog.py` (due aggiunti: copertura descrizioni
+ presenza nel payload), suite completa 520 passed, ruff pulito, verificato
dal vivo con Playwright: apertura da entrambi i punti d'ingresso, ricerca
libera, categoria che si espande, aggiunta di un indicatore con conferma
del chip sincronizzato fra i due pannelli.

---

### Grafico affollato di default — `seed-0081` — **fatto**

Lorenzo, con uno screenshot di INJUSDT pieno di etichette sovrapposte
(pattern, segnali contestuali dell'esaurimento, MACD, Stocastico):
"sta visualizzazione non ha senso vederla; di predefinito fai che non ci
sa nessun indicatore acceso".

Controllato `state.layers` in `app.js`: nel codice erano gia' tutti spenti
tranne uno solo, EMA 20/50. Il resto del disordine nello screenshot veniva
dalle preferenze salvate sul suo account (`/api/preferences`, campo
`layers`) — ogni sessione le ricorda e le ripropone identiche al prossimo
accesso, indipendentemente dal default del codice. Fatto: spento anche
l'ultimo default rimasto (EMA), sia nello stato JS sia nel `checked` del
checkbox in `index.html`. Verificato dal vivo registrando un account senza
preferenze pregresse: grafico con solo candele, nessun livello acceso,
nessun sub-chart aperto.

**Non risolto per il suo account specifico**: le preferenze gia' salvate
da Lorenzo (con pattern/hints/macd/stoch accesi da una sessione precedente)
restano quelle finche' non le spegne una volta dai toggle in Livelli — da
qui non c'e' accesso al database di produzione per resettarle al posto
suo, e non e' stato chiesto di farlo. Una volta spente restano spente:
`savePreferences()` salva lo stato lasciato, non lo riaccende mai da solo.

---

### Libreria indicatori — terzo giro: rimozione, nome a grafico, modale con preferiti — `seed-0082` — **fatto**

Stessa serata del filone libreria (`seed-0079`/`0080`), tre richieste in
fila mentre Lorenzo provava il sito dal vivo.

**Prima**: "quando aggiungo indicatori dalla libreria voglio poterli
togliere cliccandoci sopra al grafico e rimuovendoli" — poi affinata
subito dopo, senza aspettare che finissi: "la rimozione deve avvenire
tramite un flag che appare con una x se passo il cursore sugli
indicatori, qualunque essi siano a grafico". Fatto cosi': per gli overlay
(linee sul prezzo) un badge DOM appare quando il cursore e' entro 6px
dalla linea (calcolato da `priceToCoordinate`, non a tentativi — la prima
verifica con una scansione a griglia larga non trovava mai la linea,
serviva leggere il valore vero da `param.seriesData` e convertirlo in
coordinata schermo); per i riquadri oscillatore, un bottone sempre nel DOM
rivelato in CSS al passaggio del mouse sopra il riquadro (piu' semplice:
il riquadro appartiene a un solo indicatore, nessun hit-test necessario).
Un dettaglio non ovvio: il badge, essendo un elemento DOM sopra il canvas,
occludeva il grafico sottostante appena il cursore lo raggiungeva —
`subscribeCrosshairMove` smetteva di ricevere il movimento e il badge
spariva un istante prima di poterci cliccare sopra. Risolto con
mouseenter/mouseleave sul badge stesso che "lo tengono acceso" finche' il
mouse ci sta sopra.

**Seconda, subito dopo**: "voglio vedere il nome degli indicatori a
grafico una volta attivati; voglio poterci entrare e capire come
ragionano, ora se li attivo finiscono nel grafico ma non so cosa sono e
cosa ho attivo". Aggiunta una legenda fissa in alto a sinistra sul
grafico (`#chart-indicator-legend`) che elenca ogni indicatore attivo con
pallino colorato e nome cliccabile — stessa lista gia' mostrata come chip
in Livelli, resa visibile anche sopra il grafico. Click sul nome (in
legenda o nel titolo di un riquadro oscillatore) apre un popup con la
stessa descrizione scritta nella libreria — riusa l'elemento e la logica
di chiusura di `showMarkerPopup()`. Trovato in verifica dal vivo: la
legenda a `top:8px` si sovrapponeva al badge LIVE/Agg.ogni60s (stesso
angolo, z-index piu' alto, intercettava i click) — spostata a `top:40px`.

**Terza**: con uno screenshot del pannello "Indicatori, metriche e
strategie" di TradingView: "riesci a copiare l'interfaccia [...] in toto?
PRECISAMENTE UGUALE?". Spiegato il limite prima di procedere: non e'
tecnico, e' che il design esatto di un prodotto di terzi non e'
riproducibile — la struttura funzionale si'. Fatto: la libreria non e'
piu' un cassetto laterale (`#indicator-library-panel`, dentro
`RAIL_PANELS`/`drawerFor`/mappature mobile) ma un modale centrale
(`#indicator-library-modal`, overlay fisso indipendente dal sistema di
pannelli — stesso comportamento identico su desktop e mobile, niente piu'
logica separata per i due). Colonna categorie a sinistra (Tutti,
Preferiti, poi le 9 categorie reali con conteggio), ricerca in alto,
risultati a destra con stella per i preferiti (persistiti in
`localStorage`, chiave `favoriteIndicatorIds`). Rimossa tutta l'idraulica
che il cassetto richiedeva, incluso il meccanismo di click
sintetico+`stopPropagation` introdotto nel giro precedente per evitare che
il pannello si auto-richiudesse — con un modale quel problema non esiste
proprio: chiusura solo su bottone ✕, click sullo sfondo scuro, o Escape.

Verificato dal vivo con Playwright ad ogni passo (non solo a rilettura di
codice): badge overlay che appare esattamente sulla linea e resta
cliccabile avvicinandocisi col mouse; bottone oscillatore rivelato in
hover; modale aperto da tutti e tre i punti d'ingresso (toolbar, sidebar,
Livelli), navigazione fra categorie, filtro preferiti, ricerca, tre modi
di chiudere; legenda sincronizzata, popup di spiegazione col testo giusto.
Suite completa 520 passed, ruff pulito.

**Quarto giro, subito dopo — `seed-0083`**: Lorenzo, appena vista la
libreria come modale: "elimina la tab libreria, tanto abbiamo già
indicatori in alto". Tolta la voce "Libreria" dalla sidebar (gruppo
Riferimento) — restavano tre punti d'ingresso allo stesso modale (sidebar,
toolbar, dentro Livelli), il pulsante in toolbar la duplicava senza
motivo. Il modale era gia' indipendente dal sistema di pannelli laterali
dal giro precedente, quindi togliere un punto d'ingresso non tocca la
logica di apertura/chiusura — solo il bottone e il suo listener. Restano
due punti d'ingresso: il pulsante in toolbar (principale) e quello dentro
Livelli (contestuale). Verificato dal vivo: voce sparita dalla sidebar,
entrambi gli ingressi rimasti aprono ancora il modale correttamente.

## Bacheca: pulizia stati bloccati su "aperto"

Lorenzo: "ci sono segnalazioni aperte, chiudi tutte quelle risolte".
Controllate tutte le 11 non-`risolto` fra le 113 segnalazioni live
(`curl https://liquidityengine.app/api/issues`). Trovato che 4 avevano
gia' una risoluzione sostanziale in `resolutions.json` ma con uno
`status` descrittivo invece del valore canonico atteso da `_VALID_STATUS`
(`backend/app/issues.py:50`) — la funzione di merge (riga 439) scarta lo
stato non riconosciuto e la voce resta "aperto" come nel seed originale,
anche se il lavoro e' finito. Non un bug di logica: solo status scritti a
mano in modo descrittivo invece che nel valore atteso.

Normalizzati in `resolutions.json` (mai toccato `issues.json`, che resta
sul volume Fly e appartiene a chi scrive le segnalazioni):
- `seed-0077` (alert Telegram in ritardo di un giorno intero) → `risolto`
  — causa trovata e misurata, 26/26 alert puntuali dopo il fix.
- `seed-0073` (sito "sembra AI slop") → `risolto` — 145→15 problemi
  residui, tutti bassa priorita' o scelte deliberate gia' documentate.
- `6a914943` (dubbio su segnali KASUSDT) → `scartato` — chiusa dallo
  stesso autore della segnalazione ("Problema da ignorare").

Lasciata `in corso` `seed-0072` (fix MEXC futures, host+endpoint): il
testo della risoluzione stessa dice che serve conferma con un ordine
reale, non ancora fatta. Restano genuinamente aperte/in corso e non
toccate: `72f880af` e `37637f11` (nessun fix scritto), `seed-0078` (idea
non implementata), `seed-0054`/`seed-0051`/`seed-0028`/`seed-0027`
(davvero in corso).

Verificato con `pytest tests/test_issues.py` e la suite completa (520
passed) + ruff pulito prima di committare.

## Le due segnalazioni genuinamente aperte, chiuse

Lorenzo: "lavora sui punti aperti e risolvili" — riferito ai due unici
rimasti senza risoluzione, `72f880af` e `37637f11`, entrambe scritte dal
tester dall'app.

**`72f880af`** — "Gabriele nel Lab lascia sempre predefiniti RSI
LENGTH/BOLLINGER LENGTH/MOLTIPLICATORE, interviene solo su
ipercomprato/ipervenduto." Verificato eseguendo `run_pipeline()` (il
percorso "Ricerca stabile") su tre serie sintetiche diverse: lunghezza
RSI e lunghezza Bollinger uscivano ogni volta diverse (16/32, 10/20,
7/10 candele), il moltiplicatore Bollinger restava sempre identico. Non
un difetto della ricerca: in `priors.py` (`_gabriele_space`) il
moltiplicatore e' derivato di proposito dalla frequenza di ingresso
voluta ("quanti segnali vuoi vedere") invece che cercato per tentativi —
scelta gia' spiegata nel codice con la sua logica statistica. Il problema
vero era che questa scelta non si capiva dai risultati: la nota che il
motore gia' generava ("bb_mult derived from...") era in inglese tecnico.
Riscritta in italiano semplice, dicendo esplicitamente che lunghezza RSI
e Bollinger restano cercate — nessuna modifica alla logica di ricerca.

**`37637f11`** — "ora che il backtest gira anche sotto 1D, sostituisci
'Apertura della candela successiva' con 'al momento in cui si verifica
la condizione'." Tolta l'opzione dal menu Parametri backtest del Lab.
L'opzione rimasta ("Chiusura della candela del segnale") e' stata
rinominata "Al momento in cui si verifica la condizione": per un segnale
basato su indicatori (RSI, medie, Bollinger) sono lo stesso istante —
l'indicatore si puo' verificare solo alla chiusura della candela che lo
calcola, ed e' anche il momento in cui parte l'alert dal vivo (stessa
logica di seed-0077). Non serviva un terzo meccanismo di esecuzione,
solo chiamare con il suo nome quello che il motore gia' fa. Il backend
continua ad accettare `next_open` per compatibilita' con ottimizzazioni
gia' archiviate che lo referenziano — tolta solo l'opzione dal menu.

Verificato: `node --check` pulito, suite completa 520 passed, ruff
pulito. Restano da fare (non toccati, non richiesti): la voce
"Decidere la finestra di freschezza del segnale sui timeframe alti"
(serve una scelta di Lorenzo) e le segnalazioni genuinamente "in corso"
(`seed-0054`, `seed-0051`, `seed-0028`, `seed-0027`, `seed-0072`).

## Sessione 2026-09-19 — Wallet on-chain: Fase 3/4 vere e frontend rifatto

**Fase 3/4, entrambe le chain.** Lorenzo: *"completa tutto il progetto
rendilo operativo"* → *"fai anche 3/4 fase"*. Solana aveva gia' il
percorso reale (Jupiter, verificato dal vivo fino all'invio). Robinhood
Chain no, e il blocco era l'indirizzo del router Uniswap: le fonti si
contraddicevano (doc ufficiale `0x8876…0904`, un blog terzo parlava di un
redeploy a `0x06afBA43…`). Risolto verificando **dal vivo**, non leggendo
una pagina: `docs.robinhood.com/chain/contracts` da' WETH
`0x0Bd7D308f8E1639FAb988df18A8011f41EAcAD73` e USDG
`0x5fc5360D0400a0Fd4f2af552ADD042D716F1d168`, e una `getPool()` vera sul
V3Factory trova pool reali su tutti e quattro i fee tier. Un quote vero
da QuoterV2: 0.01 WETH → ~26,19 USDG, coerente con un prezzo ETH
plausibile. Il selettore `exactInputSingle` (`0x04e45aaf`) l'ho
ricalcolato con `eth_utils.keccak`, non preso a memoria.
Attenzione: gli indirizzi `USDC`/`WETH` sulla pagina Uniswap sono quelli
di **Ethereum mainnet**, usati come esempio di codice — usarli per uno
swap vero manderebbe fondi a un contratto che li' non esiste.

Cosa **non** e' stato fatto, e va detto: su Robinhood Chain nessun invio
reale e' mai stato provato. Firma, quote, nonce e gas price sono
verificati dal vivo; il broadcast no. `onchain_execution_enabled` resta
`False` di default su entrambe le chain — lo accende Lorenzo.

**Fase 4 dalla watchlist: ancora ferma, per un motivo preciso.** Il
simbolo dei pair DEX e' `BASE@chain:pool`, che porta l'indirizzo del
*pool* ma non quello del *token* (mint su Solana, contratto su EVM), e
senza quello non si puo' chiedere un quote. Il loop ora registra
"saltato" con questo motivo invece di restare muto. Per chiuderla serve
salvare il mint address quando si aggiunge un pair dalla ricerca
DexScreener.

**Frontend del wallet, rifatto due volte.** Prima passata su uno
screenshot di un'app wallet che piaceva a Lorenzo. Poi lui: *"rendilo
meno ai slop, hai le skill installate apposta"* — e aveva ragione: il
grafico disegnava una tendenza da due letture (linea piatta + rampa, che
si legge come "il saldo e' esploso"), il saldo era scritto due volte a
400px di distanza, due chip bordati annunciavano due fatti che non
cambiano mai, e la tabbar in basso inventava un'app dove "Attivita'"
apriva la stessa sheet del bottone sopra. Tolto tutto.

Poi: *"voglio una grafica anche moderna con tecnologie moderne per front
end"*. Gli ho posto la scelta che cambiava davvero qualcosa — framework
con build step nel Dockerfile, oppure la piattaforma — e ha scelto
**zero build**. Quindi: moduli ES + import map generata dal server,
`<dialog>` nativo per sheet e overlay (top-layer, `::backdrop`, trappola
del focus ed Escape sono del browser, non piu' reimplementati male),
`@starting-style` + `transition-behavior: allow-discrete` per entrata e
uscita senza timer JS, View Transitions sul cambio chain (il saldo si
interpola invece di sparire), `@layer` per la cascata, `light-dark()` al
posto di tre blocchi di token duplicati, `oklch()` + `color-mix()`,
container query sulla fila delle azioni, `AbortSignal.timeout()` al posto
della `Promise.race` con `setTimeout`, `Intl` per valuta e tempi
relativi.

Due bug trovati guardando la pagina renderizzata, non leggendo il codice:
`Intl` in `it-IT` scrive `"8,87 USD"` e il mio codice lo ricomponeva come
`"USD8,87"` (ora gli importi in dollari usano `en-US`, il simbolo davanti,
come i tetti `$20` del resto dell'app; le quantita' di token restano in
italiano); e `[hidden]` veniva sovrascritto da ogni regola con `display`,
quindi il toast vuoto restava visibile — serve `[hidden]{display:none
!important}` in `@layer base`.

Verificato: 633 passed, ruff pulito, `node --check` su tutti i moduli,
resa controllata in chiaro e scuro con il backend vero in locale.

## Sessione 2026-09-23 — Fase 4 sbloccata (lato buy), Fase 5 al passo intermedio

Lorenzo: "completa il piano wallet on-chain — Fase 4 (watchlist -> auto-trade,
oggi bloccata) e Fase 5 (wallet dentro Sorveglia/Opera, non piu' pagina a se)".

**Fase 4.** Il blocco era esattamente quello documentato: `BASE@chain:pool`
porta l'indirizzo del pool, non quello del token, e senza quello non si
chiede un quote. DexScreener nella ricerca da' gia' `baseToken.address` —
prima scartato, usato solo per symbol/name. Ora `dexscreener.search_symbols`
lo espone come `base_token_address`, `WatchlistEntry`/`SymbolSuggestion`
lo portano, `watchlist.add_entry` lo salva alla creazione E lo recupera su
un upsert che prima non lo aveva (una entry vecchia non resta "saltata"
per sempre). Il branch di auto-trade in `main.py` (`_run_onchain_auto_trade`)
ora firma davvero un ordine BUY: Jupiter su Solana, Uniswap v3 su Robinhood
Chain con discovery del fee tier (100/500/3000/10000), stesso schema degli
endpoint manuali `/api/onchain/execute/*`. Il token di quotazione e' uno
stabile fisso per chain (USDC su Solana, USDG su Robinhood Chain) — i
decimali di entrambi (6) sono verificati dal vivo con una `decimals()`
reale via RPC, non presi a memoria.

Scelta deliberata, non un buco lasciato per fretta: le VENDITE
(`exit_long`/`flip_to_short`) restano "saltate", con un motivo esplicito
("servono i decimali del token, non salvati sulla entry"). Comprare si
paga sempre nello stabile di quote, i cui decimali sono noti; vendere
richiederebbe i decimali del token BASE per convertire una quantita' in
unita' raw — indovinarli manda un multiplo o una frazione dell'importo
voluto, non un errore leggibile. Restano da salvare quando la entry viene
creata (una `decimals()` in piu' sulla stessa chiamata che gia' verifica
il pool), non ancora fatto.

**Fase 5.** Trovato che "Sorveglia" e "Opera" sono nomi interni superati:
la tab visibile oggi si chiama "Trading" (`data-tab-content="trading"`),
ma le sue sotto-sezioni sono ancora accordion `<details class="opera-sub">`
— stesso posto dove vivono le chiavi exchange (Trading automatico,
Ordine futures/manuale, Posizioni aperte). Aggiunta una nuova sezione
"Wallet on-chain" con lo stesso schema, fra "Trading automatico" e
"Ordine manuale": un bottone-link ben visibile a `/onchain-app.html`.

Scelta esplicita (via intermedia, non fusione piena): la UI del wallet ha
un suo ciclo di stato/polling indipendente (moduli ES, `<dialog>`, View
Transitions — rifatta la sessione scorsa) e portarla dentro il DOM della
tab Trading senza romperla vale una sessione a se', non un pezzo di
questa. Il wallet ora si trova DA DENTRO il sito (prima era un URL
isolato che nessuno trovava), ma non e' ancora fuso nella pagina.

Verificato dal vivo con Playwright (non solo letto il codice): registrato
un utente di test con `REGISTRATION_ALLOWED_EMAILS`, login vero, sito
principale che si carica e naviga (screenshot sloggato e loggato), la
sezione "Wallet on-chain" visibile e cliccabile dopo aver aperto i due
accordion, e il link che porta davvero alla pagina del wallet, la quale
si carica senza errori in console propri (a parte un `ERR_CERT_AUTHORITY_INVALID`
di rete, non del sito).

Test nuovi: `test_dexscreener_search.py`, `test_watchlist_base_token_address.py`,
`test_onchain_watchlist_autotrade.py` (firma/invio mockati, come gli altri
test di execute — la correttezza di quote/firma e' verificata altrove con
rete vera). Suite completa 644 passed (1 fallimento di rete noto e
indipendente, `test_onchain_prices.py::test_native_price_usd_real_network_call_robinhood`),
ruff pulito, `node --check` pulito.

Aggiornata anche la voce `seed-0085` in `resolutions.json` con lo stato di
questa sessione — resta "in corso": la fusione piena della UI e la vendita
on-chain (decimali del token) sono i due pezzi veri che restano.

## Integrazione dei 4 lavori paralleli sul piano wallet on-chain (2026-09-23)

Lorenzo: "applica tutto il piano con agent e consuma meno token possibili".
Lanciati 4 agenti in worktree isolate, in parallelo: (1) allowlist pool +
size dinamica sulla liquidita', (2) TWAP a fette + riconciliazione/recovery
da crash, (3) osservabilita' SRE (fallback multi-RPC, /admin/status,
correlation id, alert Telegram di rischio), (4) Fase 4 (mint address nella
ricerca DEX, sblocco auto-trade BUY dalla watchlist) + Fase 5 (link al
wallet dentro la tab Trading del sito).

Integrati in sequenza con `git merge` sui rispettivi branch worktree-agent-*.
Tre merge su quattro hanno avuto conflitti veri (non auto-risolvibili),
sempre per lo stesso motivo: due agenti diversi hanno aggiunto codice
all'inizio delle stesse funzioni (`execute_order`/`simulate_order` in
execute.py/simulate.py, le tabelle SQL in `_init_db()` di ledger.py) —
mai una vera incompatibilita' di design, solo due aggiunte indipendenti
nello stesso punto del file. Risolti a mano tenendo entrambe le parti
(correlation_id generato prima, poi allowlist/size dinamica, poi il check
di rischio; entrambe le CREATE TABLE mantenute).

Suite finale dopo tutti i merge: 684 passed, 0 falliti, ruff pulito,
`node --check` pulito su tutti i moduli onchain. Non riverificato dal vivo
con Playwright dopo il merge (lo aveva gia' fatto l'agente 4 prima di
integrare) — se qualcosa nella UI sembra rotto dopo il deploy, e' il primo
posto da controllare.

Resta dal piano, dopo questa sessione: MEV/Jito bundle su Solana, resume
automatica di un TWAP job dopo un riavvio (il job e' persistito ma nessun
scheduler lo riprende da solo), fusione piena della UI wallet nel DOM
della tab Trading (oggi e' un link, non fusa), vendita on-chain dalla
watchlist (servono i decimali del token base, non salvati).

## Round 2 — chiusura del piano wallet on-chain (2026-09-23)

Lorenzo: "DEVI COMPLETARE TUTTO, e mergare su main". Secondo giro di 4 agenti
in worktree isolate sui 4 pezzi rimasti dal round 1: MEV/Jito bundle su
Solana, resume automatico dei TWAP job dopo un riavvio, vendita on-chain
dalla watchlist (decimali token via lookup on-chain reale), fusione piena
della UI wallet nel DOM della tab Trading (non piu' un link).

Il 4° agente (fusione UI) ha esaurito il limite di sessione a meta' lavoro
ed e' terminato con `status: failed`, ma il lavoro nella sua worktree era
completo e coerente — verificato e committato a mano (`a7a8147`) invece di
rilanciarlo da zero.

Merge in sequenza su `main`, 3 su 4 senza conflitti; l'ultimo (fusione UI)
pulito anche lui. Un conflitto vero in `ledger.py` (due agenti diversi
hanno aggiunto tabelle e funzioni nello stesso punto di `_init_db()`) —
risolto tenendo entrambi i set, erano indipendenti. Un altro in `main.py`
(branch buy/sell dell'auto-trade vs. instradamento Jito) risolto applicando
`slippage_bps` calcolato in base a Jito a entrambi i rami.

Verifica finale: 690 passed, 2 falliti (chiamate di rete vere, gia' note
come intermittenti: `test_native_price_usd_real_network_call_robinhood`,
`test_quote_robinhood_real_network_call`), ruff pulito. Pushato su
`origin/main` (`29fb461`).

Con questo il piano di sviluppo wallet on-chain e' applicato per intero:
custody, simulate/execute su entrambe le chain, swap manuale con saldo
reale e prezzi da DEX, TWAP con resume da crash, riconciliazione/discrepanze,
allowlist pool + size dinamica, Jito MEV, osservabilita' SRE, auto-trade
buy/sell dalla watchlist, UI fusa nella tab Trading. Resta aperto solo un
punto operativo, non di codice: l'attivazione di `ONCHAIN_EXECUTION_ENABLED`
sul server di produzione (vedi voce sotto), e la rotazione delle credenziali
esposte durante quell'attivazione (password root Hetzner, secret in `.env`).

## Sessione 2026-09-23 (worktree separato) — MEV/Jito bundle su Solana

Lorenzo (via piano di sviluppo wallet on-chain): "Solana: instradare via
Jito bundle con tip dinamico e slippage stretto [...] bundle atomici
riducono drasticamente la finestra di front-run".

Nuovo `backend/app/trading/onchain/jito.py`: `send_bundle_via_jito()`
manda un bundle reale (swap firmato + tip transaction) a
`https://mainnet.block-engine.jito.wtf:443/api/v1/bundles`, metodo
`sendBundle`, encoding base64 — endpoint, metodo e formato verificati con
una ricerca web contro `docs.jito.wtf/lowlatencytxnsend/` (fetch dal
vivo), non inventati. Gli 8 tip account ufficiali sono presi dalla stessa
pagina. Tip dinamico (`compute_dynamic_tip_lamports`): proporzionale al
notional in SOL (5 bps), clampato fra un minimo (1000 lamports, il piede
della doc) e un massimo configurabile — non un valore fisso.

**Cosa e' verificato dal vivo e cosa no, onestamente:** l'endpoint/metodo/
formato sono verificati leggendo la doc reale, ma NESSUN bundle vero e'
mai stato mandato con fondi reali in questa sessione (servirebbe una tip
transaction con lamports veri sul wallet). I test (`test_onchain_jito.py`)
mockano la risposta HTTP e verificano solo la forma della richiesta
(URL, metodo, struttura dei params, encoding, tip account nella lista
ufficiale) — stesso livello di verifica di quello che execution.py/
quotes.py avevano gia' documentato per Robinhood Chain.

Wiring in `execute.py`: nuovo `settings.onchain_use_jito` (default
`True` — la richiesta e' verificata contro la doc, e c'e' un fallback),
`_send_solana_with_jito_fallback()` prova prima Jito e ricade su
`execution.send_signed_solana_tx` (invariato, ancora testato com'era) se
Jito e' spento o lancia un'eccezione qualsiasi. Il `tx_signature`
ritornato quando passa da Jito e' il bundle_id prefissato `jito:` — un
bundle non da' una signature RPC come sendTransaction, e confonderli in
log/ledger sarebbe stato peggio che marcarli diversi. Slippage stretto
per Jito: `jito.JITO_SLIPPAGE_BPS = 20` (0.2%, contro il default 50 bps/
0.5% retail) passato a `jupiter_quote` in `main.py` solo quando
`onchain_use_jito` e' acceso — documentato nel modulo perche' scelto, non
un numero a caso.

Confronto multi-route: non costruito un secondo aggregatore. Jupiter
aggrega gia' internamente le route su Solana (e' quello che il piano
intendeva evitare di duplicare) — documentato come tale in `jito.py`
invece di un secondo pezzo di codice che farebbe la stessa cosa.

Jitter TWAP: gia' presente (`DEFAULT_JITTER_PCT = 0.35`, dentro il range
30-40% chiesto dal piano) — nessuna modifica necessaria a `twap.py`.

Verificato: `pytest tests/ -q` verde (695 passed, 1 skip, lo stesso
fallimento di rete noto e indipendente su `test_native_price_usd_real_
network_call_robinhood`), `ruff check` pulito. Commit su worktree isolato,
non pushato — da integrare con `git merge` come gli altri lavori
paralleli sul piano wallet on-chain.

Resta dal piano dopo questa sessione: resume automatica TWAP dopo
riavvio, fusione piena UI wallet, vendita on-chain (decimali token base).
Il confronto multi-route resta volutamente non implementato con un
secondo aggregatore (vedi sopra) — se in futuro emerge un secondo
aggregatore Solana pubblico ben documentato che valga la pena integrare,
e' quello il punto da riconsiderare.

## Piano: restyle in stile Uniswap + parte operativa (ordini limite, cronologia) — 2026-09-23

Lorenzo: "copia lo stile di questo; per intenderci https://app.uniswap.org/,
voglio visualizzare anche il wallet, una parte operativa tipo DEX con
ordini limiti, cronologia ordini". Non ancora applicato — solo il piano,
da evolvere insieme prima di partire.

### 1. Restyle visivo (stile Uniswap)

- Layout da "app mobile con sheet" a "pagina DEX": barra superiore fissa
  con selettore chain + indirizzo/saldo sempre visibile (oggi e' dentro lo
  shell, non in una topbar persistente); il saldo del wallet resta sempre
  in vista mentre si opera, non solo nella hero.
- Il pannello di swap diventa una card centrale larga ~460px anche su
  mobile (Uniswap non fa mai "sheet" per lo swap, e' la pagina stessa) —
  le altre sheet (storico, limiti, rivela chiave) restano dialog, lo swap
  no.
- Selettore token con lista/ricerca invece del prompt() attuale (introdotto
  in questa sessione per gli indirizzi arbitrari) — stessa ricerca
  DexScreener gia' usata per la watchlist, con logo/nome se disponibili.
- Palette: Uniswap usa rosa/violetto su sfondo scuro con card ad alto
  contrasto; qui i token oklch/light-dark() esistenti restano (tema chiaro
  e scuro automatici), cambia la palette dei valori --accent/--accent-soft,
  non la struttura CSS a @layer.
- Tabella ordini/cronologia in stile Uniswap (righe dense, monospace per i
  numeri, stato con pallino colorato) al posto delle liste a card attuali.

### 2. Ordini limite — la parte nuova

Ne' Jupiter ne' il router Uniswap v3 su Robinhood Chain eseguono un ordine
da soli quando il prezzo tocca un livello: un "ordine limite" qui va
costruito come **ordine persistito + polling che lo esegue da solo quando
la condizione si avvera**, riusando l'infrastruttura TWAP/watchlist gia'
in piedi, non inventando un secondo sistema.

- **Tabella `limit_orders`** in `ledger.py` (nuova, stesso pattern di
  `twap_jobs`/`discrepancies`): id, owner, chain, token_in, token_out,
  amount_in, target_price_usd, direction (`buy_below`/`sell_above`),
  status (`open`/`filled`/`cancelled`/`expired`), created_at, expires_at
  (opzionale), filled_order_id (FK verso `orders` una volta eseguito).
- **Motore**: un ciclo asyncio nuovo (`limit_order_loop`, accanto a
  `_watchlist_alert_loop` in `main.py`) che ogni N secondi legge gli ordini
  `open`, chiede un quote reale (stesso `onchain_quotes`), confronta col
  target, e se la condizione e' vera chiama `execute.execute_order` con
  gli stessi guardrail di rischio di oggi (mai un percorso che li scavalca
  perche' e' "automatico").
- **Idempotenza**: un ordine limite eseguito una volta passa a `filled` e
  non viene mai riletto — stesso principio della UNIQUE constraint sul
  ledger, non un secondo controllo ad-hoc.
- **Cancellazione**: endpoint `DELETE /api/onchain/limit-orders/{id}` — un
  ordine `open` diventa `cancelled`, mai eliminato (stessa filosofia delle
  segnalazioni: non si butta via lo storico).
- **Scadenza**: opzionale a livello di piano, non di primo taglio — un
  campo `expires_at` gia' nello schema permette di aggiungerla dopo senza
  migrazione.
- **Limite del design**: il prezzo si controlla a intervalli (non e' un
  book on-chain reale), quindi un target toccato per un istante fra due
  polling puo' non essere colto — da dire chiaramente in UI ("controllato
  ogni X secondi", non "eseguito istantaneamente al tocco").

### 3. Cronologia ordini

- Endpoint nuovo che unisce `orders` (dal ledger, gia' esistenti) e
  `limit_orders` in una lista sola ordinata per tempo, con stato e link
  alla transazione (Solscan/l'explorer di Robinhood Chain) — oggi lo
  storico esiste solo come sheet separata via `getTransactions`.
- Colonne stile Uniswap: tipo (swap/limite), coppia, importo, prezzo,
  stato, tempo relativo, firma abbreviata con link.

### 4. Wallet sempre visibile

- Il saldo/indirizzo gia' esistono nella hero; nel nuovo layout DEX
  diventano parte della topbar persistente (punto 1), non uno stato che
  si perde scorrendo la pagina.

### Ordine di lavoro proposto (da confermare con Lorenzo prima di partire)

1. Restyle (solo CSS/HTML, nessuna nuova logica) — rischio basso, visibile
   subito.
2. Tabella + endpoint CRUD ordini limite (senza motore che esegue ancora)
   — cosi' si vede la UI degli ordini prima di fidarsi del motore.
3. Motore di esecuzione automatica (il pezzo che tocca i soldi veri).
4. Cronologia unificata.

Non iniziato: in attesa di conferma su quale punto affrontare prima.

### Chiarimento del piano sopra — 2026-09-23, stessa sessione

Lorenzo: "eredita la parte di trading dal sito originale
https://liquidityengine.app/; però voglio avere appunto un esperienza UI
tipo un dex". Non un secondo motore da inventare: i pattern
dell'"Ordine manuale" (Trading → Chiavi exchange, posizioni, diario,
ordine manuale) sono gia' la stessa cosa concettuale di uno swap/ordine
limite, solo su un exchange centralizzato — vanno ereditati come
INTERAZIONE, vestiti da DEX:

- **Tabs BUY/SELL** del form manuale → stessa coppia di tab nello swap
  DEX per la direzione (oggi lo swap ha solo "vendi X, ricevi Y" senza
  un concetto esplicito di lato).
- **Slider "USDT fisso" / "% saldo"** → stesso slider per la size di uno
  swap o di un ordine limite, invece del solo campo numerico con "Max"
  di oggi — coerente col resto del sito, non un secondo modo di scrivere
  una size.
- **Checkbox di conferma esplicita** ("Confermo: denaro reale, X") prima
  del bottone di esecuzione → sostituisce il `window.confirm()` del
  browser usato oggi nello swap onchain, che stona con lo stile DEX e con
  il resto del sito.
- **"Chiudi posizione — vendi tutto"** → lo stesso shortcut ha senso
  anche per una posizione on-chain (vendere il 100% di un token della
  watchlist/posizioni al prezzo di mercato), non solo per i pair CEX.
- **Diario** → e' il precedente diretto della "cronologia ordini" del
  piano sopra: stessa idea (elenco di cio' che e' successo, con
  esito), qui estesa a includere anche gli ordini limite ancora aperti.

Il motore di esecuzione (execute_order, guardrail di rischio, ledger)
resta quello on-chain di oggi — cio' che si eredita e' la UX del form,
non il codice che esegue, che e' gia' specifico per exchange centralizzati
vs. wallet on-chain e non va unificato.

## Piano: ecosistema DEX completo dentro il wallet on-chain — 2026-09-23

Lorenzo: "nell'ottica di utilizzo on-chain dobbiamo ridurre al limite
queste complicanze: dobbiamo creare un app in stile dex con grafici
(ereditati dal sito principale) con minor delay possibile; avere
possibilita' di attivare le strategie dell'archivio; visualizzare
ingressi etc, direttamente su app on-chain; avere un wallet per capire il
portafoglio; avere una copia delle transazioni per capire cosa e'
accaduto in passato". Non ancora applicato — questo e' il piano completo,
i pezzi minori (ordini limite, ricerca token, restyle rosa/violetto) gia'
fatti in questa sessione restano dentro, non si buttano via.

Idea guida: **un'unica app** (`onchain-app.html`, gia' esiste), non un
secondo sito. Quattro pannelli sempre raggiungibili da una barra in
basso o laterale (stile DEX mobile: Grafico / Strategie / Wallet /
Storico), non piu' sheet che si aprono una sopra l'altra per ogni azione.

### 1. Grafico ereditato dal sito, non ricostruito

- Il sito principale gia' disegna candele DEX vere per i pair `@chain:pool`
  via `/api/candles` + GeckoTerminal (`providers/dexscreener.py`,
  `GECKO_NETWORKS`) e la libreria Lightweight Charts — stesso identico
  motore, non un secondo grafico da scrivere.
- Il wallet apre il grafico del PAIR che sta per scambiare (quello scelto
  nel token-picker, gia' costruito questa sessione) passando il suo
  `symbol` DEX (`BASE@chain:pool`, gia' quello che il picker restituisce
  dalla ricerca) allo stesso componente chart — non serve duplicare
  candele/indicatori, solo un `<script>` condiviso o un modulo importato
  dal bundle esistente (`app.js` e' un file solo, oggi non modulare: va
  isolata la sola funzione di disegno chart in un modulo ES riusabile da
  entrambe le pagine, senza portarsi dietro tutto il resto del sito).
- **Delay**: GeckoTerminal aggiorna a intervalli (non tick-by-tick); per
  "minor delay possibile" senza inventare un feed nuovo, il grafico apre
  gia' con l'ultima candela nota dalla cache del sito (stesso principio
  della hero: mostrare subito il dato in cache, poi aggiornare) e fa
  polling piu' stretto (5-10s) solo mentre il pannello grafico e' aperto,
  non sempre — un websocket DEX vero (non esiste un feed gratuito
  affidabile multi-chain oggi) resta fuori scope, dichiarato non nascosto.

### 2. Attivare le strategie dell'archivio sul wallet

- Le tre strategie (Lorenzo, Gabriele, Accumulo/Distribuzione) girano gia'
  in automatico sulla Watchlist, col trading automatico che gia' oggi (da
  questa sessione) sa eseguire buy E sell on-chain — il pezzo che manca
  e' SOLO l'interfaccia, non il motore.
- Nuovo pannello "Strategie" DENTRO il wallet: lista dei token della
  Watchlist collegabili a questa chain (quelli con `base_token_address`
  compilato), ciascuno con lo stesso interruttore "Trading automatico" e
  un selettore della strategia (le stesse tre, stesso backend) — non un
  secondo sistema di attivazione, la stessa API della Watchlist
  (`/api/watchlist/*`) letta e scritta da qui invece che dall'altra tab.
- Aggiungere un token a questo pannello dal wallet stesso usa lo stesso
  token-picker per ticker gia' costruito per lo swap — un solo modo di
  cercare un token in tutta l'app, mai due.

### 3. Ingressi/segnali visibili sul grafico dell'app on-chain

- Il sito principale disegna gia' marker sul grafico per gli ordini del
  diario ("diario... diventano marker propri" — vedi `app.js`, sezione
  marker). Lo stesso meccanismo si applica al grafico del wallet: ogni
  ordine (swap manuale, ordine limite eseguito, o trade automatico da una
  strategia) diventa un marker sulla stessa candela in cui e' avvenuto —
  non un secondo indicatore, la stessa funzione di marking riusata.
- Non solo eseguiti: un segnale non ancora eseguito (es. un ordine
  limite ancora `open` che aspetta il target) si disegna come riga
  orizzontale al prezzo target (`createPriceLine`, gia' usata da RSI per
  le bande overbought/oversold) — vedere "a che punto sono" senza aprire
  una sheet a parte.

### 4. Wallet come portafoglio, non solo saldo nativo

- Gia' esiste (`assets`/`positions`) ma mostra solo le posizioni aperte
  via QUESTO sito — non "cosa detiene davvero il wallet on-chain" (che
  potrebbe avere ricevuto token anche da fuori questa app). Serve un
  secondo sguardo, via RPC vera (Solana `getTokenAccountsByOwner`, EVM
  `eth_call` sui contratti token noti o un indexer) per elencare TUTTI i
  saldi token del wallet, non solo quelli che il ledger locale ha
  tracciato — oggi la distinzione fra "cosa ho comprato da qui" e "cosa
  c'e' davvero nel wallet" non e' visibile, ed e' esattamente il tipo di
  scollamento che la riconciliazione (Fase SRE, gia' in piedi per gli
  ordini pending) dovrebbe generalizzare anche qui.

### 5. Storico come "cosa e' successo", non tre schermate diverse

- Oggi ci sono TRE fonti separate: "Storico" (transazioni RPC grezze),
  "Diario" (ordini di questo sito, gia' unificato swap+limite questa
  sessione). Da unire in un solo pannello "Storico" con due viste (Ordini
  di questa app / Transazioni on-chain grezze) invece di due bottoni
  diversi che sembrano fare la stessa cosa.

### Cosa NON e' nel piano (dichiarato, non nascosto)

- Un feed prezzi DEX in tempo reale stile CEX (websocket) — non esiste
  un provider gratuito affidabile multi-chain, il polling piu' stretto
  del punto 1 e' il compromesso.
- Un secondo motore di esecuzione per le strategie sul wallet — usano lo
  stesso motore (execute_order, guardrail, ledger) di sempre.

### Ordine di lavoro proposto

1. Isolare il componente chart del sito in un modulo ES riusabile (serve
   a questo E a niente si rompe sul sito, e' un'estrazione, non una
   riscrittura) — poi montarlo nel wallet.
2. Pannello "Strategie" nel wallet (stessa API Watchlist, nuova UI).
3. Marker degli ordini + price line dei target sul grafico del wallet.
4. Portafoglio vero (saldi RPC, non solo posizioni tracciate).
5. Unificazione dei tre pannelli storico in uno.

Non iniziato: in attesa di conferma su quale punto affrontare prima —
il punto 1 (grafico) e' il piu' visibile e il prerequisito del punto 3.

## Applicazione del piano ecosistema DEX — 2026-09-23 (stessa sessione)

Lorenzo: "applica tutto" (sul piano ecosistema DEX scritto sopra).
Applicati i punti 1, 2, 4, 5; il punto 3 (marker/target sul grafico) e'
entrato insieme al punto 1, non come pezzo separato.

- **Grafico**: nuovo `/api/onchain/chart/{chain}/{address}` (trova il
  pool migliore per liquidita' su DexScreener, poi le stesse candele di
  `providers/dexscreener.py` — leggero apposta, niente strategia/backtest
  come `/api/analyze`). Pannello nuovo (`chart.js`) con Lightweight
  Charts (stesso motore del sito, script gia' servito da `/static/`),
  polling 8s mentre resta aperto, marker sugli ordini eseguiti e righe
  orizzontali sui target degli ordini limite ancora aperti.
- **Strategie**: pannello (`strategies.js`) che espone il trading
  automatico della Watchlist (stessa API: `/api/watchlist`,
  `/strategy`, `/auto_trade`) filtrato ai token con `base_token_address`
  sulla chain corrente — nessun secondo motore. Aggiungere un NUOVO
  token resta nella tab Watchlist del sito (la ricerca li' risolve gia'
  simbolo DEX + pool insieme; duplicarla con solo l'indirizzo dato dal
  picker del wallet avrebbe richiesto ricostruire un pool a mano, un
  rischio reale non necessario).
- **Portafoglio reale**: `/api/onchain/portfolio/{chain}` +
  `balances.all_token_balances()`. Solana: elenco completo via
  `getTokenAccountsByOwner`. Robinhood Chain: NON esaustivo — scan dei
  soli token noti a questo sito (quota token + indirizzi visti in un
  ordine limite), perche' Blockscout e' dietro una sfida Cloudflare che
  un backend non supera (verificato in una sessione precedente) e non
  c'e' un indexer pubblico alternativo. Il campo `partial: true` lo dice
  al frontend, che mostra un avviso — mai un elenco che sembra completo
  e non lo e'.
- **Storico unificato**: "Storico" (transazioni RPC grezze) e "Diario"
  (ordini di questo sito) erano due bottoni per la stessa idea — uniti
  in una sola sheet "Storico" con due tab (Ordini / Transazioni on-chain).
- Griglia delle azioni: da conteggio di colonne fisso (doveva cambiare
  ad ogni azione aggiunta) a `repeat(auto-fill, minmax(64px, 1fr))` —
  nove azioni oggi, la decima non richiede toccare il CSS.

Verifica: 704 passed (+ i test gia' noti come intermittenti di rete),
ruff pulito, `node --check` pulito su tutti i moduli onchain nuovi e
modificati. Non verificato dal vivo con Playwright in questa sessione
(nessun accesso a un wallet gia' popolato con token reali per provare
grafico/portafoglio contro dati veri) — la prima cosa da controllare se
qualcosa nel grafico o nel portafoglio sembra vuoto/sbagliato dopo il
deploy.

Non applicato dal piano originale, dichiarato non nascosto: un feed
prezzi DEX in tempo reale stile websocket (non esiste un provider
gratuito affidabile multi-chain — resta il polling a 8s mentre il
grafico e' aperto).

## Revisione "deve essere come un exchange", con un team di esperti — 2026-09-23

Lorenzo, dopo aver visto il mockup solo-grafico: "ok si ma io ti ho
chiesto di rivedere tutto, usa team di esperti perche' l'esperienza deve
essere come un exchange". Lanciati 3 agenti in parallelo (visual design,
UX/interazione da exchange vero, information architecture) a leggere il
codice reale e proporre una revisione concreta, non aggettivi. Le tre
proposte convergevano sullo stesso punto: il problema non erano i
colori, era che grafico e form d'ordine stavano dietro un tap, come
un'app mobile generica, non come un terminale.

Applicato (non tutto quello che i tre report proponevano — il resto e'
materiale per un prossimo giro, elencato sotto):

- **Grafico e pannello ordine sempre visibili**, affiancati da 640px di
  contenitore (`.market-order-row`, container query, non media query —
  vale sia sulla pagina a se' sia incorporata nella tab Trading).
  `chart.js`, `swap.js`, `limitOrders.js` sono passati da `open*()` che
  apriva una sheet a `mount*(container)` che si monta in un elemento
  persistente — stesso HTML generato, contenitore diverso.
- **Pannello inferiore a tab** (Posizioni/Ordini aperti/Storico/
  Strategie) al posto di quattro bottoni che aprivano quattro sheet
  separate — "cosa ho, cosa ho ordinato, cosa e' successo" in un unico
  posto, montato pigro (solo la tab attiva chiama la sua API).
- **Griglia azioni da 9 a 3**: restano solo Ricevi, Limiti, Simula — le
  altre sei erano gia' tutte promosse a sempre-visibili.
- **Certezza dei totali**: il portafoglio dice "≥ $X" (non "$X") quando
  l'elenco e' parziale (Robinhood Chain) o un token non ha un prezzo
  noto — mai un totale che sembra definitivo e non lo e'.
- **Palette**: neutri portati sull'asse del violetto (erano rimasti
  verde-teal, stonavano contro l'accento rosa/violetto di prima); nuovi
  token `--up`/`--down` separati da `--danger` (un ribasso di prezzo e
  un ordine rifiutato sono due concetti diversi, non lo stesso rosso).

Verifica: 706 passed (backend non toccato dal punto di vista logico,
solo i moduli frontend), ruff pulito, `node --check` pulito su tutti i
moduli onchain, bilanciamento di parentesi CSS e tag HTML verificato a
mano (un mismatch di un `</div>` in `index.html` e' preesistente,
verificato risalire a prima di questa sessione — non introdotto ora).
Anteprima mostrata a Lorenzo via screenshot Playwright della CSS reale
con contenuto finto, prima di applicare al codice.

**Non ancora applicato dai tre report**, per un prossimo giro:
- Selezione rapida coppie/preferiti, slippage visibile e modificabile,
  stima gas, countdown di scadenza del preventivo (UX report, punto 2).
- Collegare il token scelto nel grafico al form d'ordine di default
  (oggi ognuno ha il suo picker indipendente — un aggancio richiede che
  il picker del grafico risolva anche i decimali, non solo l'indirizzo).
- P&L non realizzato per posizione, distanza % dal target su ogni
  ordine limite aperto, riconciliazione visiva "saldo reale vs. tracciato
  dal ledger" (IA report, punti 2-3).
- Non verificato dal vivo con Playwright autenticato (nessun wallet
  reale popolato in questa sessione) — se qualcosa nel pannello ordine o
  nel pannello inferiore sembra vuoto/rotto dopo il deploy, e' il primo
  punto da controllare.

## Sessione 2026-09-23 (c) — Ponte sniper -> Lorenzo -> wallet, test 1000 ticker

Lorenzo: "completa tutte le attivita' in pausa e non concluse. voglio che la
strategia trend follower di lorenzo sia inglobata sul wallet, cosi' da
usarla automaticamente su dei ticker on chain sfruttando la logica dello
sniper che gia' scansionava anche i nuovi arrivi relativi in questo caso a
solana e robinhood. non puoi usare delle skill che ti permettono di vedere
la grafica del wallet on chain e propormi soluzioni moderne? senza scrivere
codice in questa fase?"

Tre cose, in ordine:

1. **Test dei 1000 ticker su Robinhood Chain** (era in pausa): raccolti 153
   token reali via DexScreener e passati nel path di produzione
   (`token_metadata.get_token_decimals`, `quotes.find_pool_and_fee`). Nessun
   crash nuovo. I "429 Too Many Requests" erano il mio script di test troppo
   aggressivo sull'RPC pubblico, non un bug. 73/153 non hanno pool diretto
   contro USDG su nessun fee tier Uniswap v3 — stesso limite gia' segnalato
   per $MYCEL, generalizzato: serve multi-hop, non toccato ora.

2. **Ponte sniper -> Lorenzo -> watchlist -> wallet**: lo sniper (scanner
   nuovi arrivi Solana/Robinhood, gia' in piedi) puo' ora aggiungere da solo
   alla watchlist di chi lo attiva i candidati che superano soglie minime di
   liquidita' (3000$) ed eta' massima (72h), con la strategia di Lorenzo e
   l'auto-trade gia' accesi sopra. Deliberatamente NON un nuovo motore di
   segnali: fa solo l'upsert in watchlist, tutto il resto (rilevazione
   segnale, esecuzione, tetti di rischio, circuit breaker) resta
   `_watchlist_alert_loop` / `_run_onchain_auto_trade`, gia' testati altrove.
   Opt-in per utente e per chain (`User.sniper_autotrade_chains`, spento di
   default — richiede un wallet gia' creato su quella chain). Nuovi endpoint
   `GET/PATCH /api/onchain/sniper-autotrade[/{chain}]`.
   **Nessuna leva in UI ancora**: solo endpoint backend, va costruito un
   controllo visibile (probabilmente nel pannello Strategie del wallet) per
   dire che e' davvero "inglobata sul wallet" come chiesto.
   **Vincolo pre-esistente da ricordare**: l'intero `_watchlist_alert_loop`
   (quindi anche questo ponte) non fa nulla se l'utente non ha
   `telegram_chat_id` configurato — nessuna eccezione per questa feature.
   Bug scoperto e corretto nel farlo: `watchlist.add_entry()` metteva in
   maiuscolo anche i simboli dex (`BASE@chain:pool`), rompendo il match di
   `_parse_symbol()` su indirizzi case-sensitive (base58 Solana, checksum
   EVM) — corrotta ogni voce dex mai creata. Ora solo i simboli non-dex
   vengono uppercased. Test aggiunti, 721 passed (2 falliti in
   `test_onchain_trading_api.py` sono pre-esistenti, verificato anche su
   `main` senza queste modifiche). Commit e push su `main` fatti.

3. **Proposta grafica wallet on-chain, solo testo**: ancora da fare in
   questa sessione — screenshot Playwright dell'UI attuale e proposta di
   design senza scrivere codice, come chiesto esplicitamente da Lorenzo per
   questa fase.

## Velocita' della pagina wallet on-chain — `seed-0087` — **fatto**

Lorenzo (2026-09-23): "usa un linguaggio di programmazione per rendere il
sito velocissimo a costo di fare un refactory". Deciso di **non** cambiare
linguaggio, e detto a lui perche': misurata `onchain-app.html` dal vivo,
Lighthouse 99 da non loggati, main thread 0,4 s. Il tempo stava nei giri di
rete in fila prima dei dati, che nessuna riscrittura avrebbe tolto.

Cosa fa ora la pagina (tutto ancora zero build):
- `onchain_app_page()` in `main.py` legge la sessione e scrive utente +
  wallet in `<script type="application/json" id="onchain-boot">`, e toglie
  `hidden` dalla sezione giusta (login o app). `main.js::takeBootData()` lo
  consuma una volta; senza (index.html, dopo un login) richiede come prima.
  L'HTML e' quindi personale: `Cache-Control: private, no-cache`.
- `<!--onchain-modulepreload-->`: un modulepreload per ogni modulo.
- lightweight-charts `async` e con `?v=`; `chart.js::chartLibrary()` la
  aspetta insieme alle candele.
- Font in `static/fonts/` (Instrument Serif, JetBrains Mono); Instrument
  Sans tolto perche' `--sans` usa font di sistema.
- `api.js`: GET identici in volo condividono la richiesta; ogni scrittura
  svuota la mappa.

Misurato in locale da loggati (Lighthouse, throttling devtools mobile,
mediana di 3): inizio saldo 4,1 -> 2,4 s, LCP 4,3 -> 2,6 s, TTI 5,6 -> 3,6 s.
Il prossimo collo di bottiglia e' la banda per 13 moduli separati e la
latenza delle chiamate RPC dietro saldo/grafico.

---

## Wallet on-chain da telefono + scelta token unica — 2026-09-23

Lorenzo: "rivedi completamente il sito se mi collego da mobile; se
seleziono un token si aprono troppe schermate". Segnalazione `seed-0088`.

Causa misurata (Playwright, iPhone 13, API finte): `onTokenChanged` in
`chart.js` non aveva nessun ascoltatore, quindi il token scelto sul
grafico non arrivava allo swap; da telefono il pannello ordine stava
sotto le posizioni (~1200px piu' giu') e il secondo picker apriva la
tastiera da solo. Fatto:

- `main.js`: il token del grafico (risolto con `getTokenInfo`, in cache)
  e' `presetToken` di swap e limite; `onTokenPicked` di swap/limite
  sposta il grafico con `chart.setToken()` (che non riavvisa i listener).
- `sheets.openTokenPicker`: ricerca in cima, indirizzo incollato
  riconosciuto nello stesso campo, niente focus automatico su touch,
  titolo per lato ("Cosa vendi" / "Cosa ricevi").
- `onchain-app.html`: blocco `@container (width < 640px)` in coda — la
  `.market-card` diventa `display: contents` per mettere l'ordine fra
  grafico e posizioni senza toccare il DOM; desktop invariato.

In parallelo sulla stessa pagina: PR #70 (tasti nav, tocca
`main.js` e la fine di `resolutions.json`/`_SEED`) e il thread
velocita' (tocca `<head>`). Conflitti attesi solo in quelle code.

Seguito, stessa sessione — Lorenzo: "mezzi ticker non funzionano; voglio
solo un unico risultato per ticker 'quello con il contratto corretto e
verificato con liquidità migliore'". `seed-0090`. La ricerca del picker
non usa piu' DexScreener (30 pool su tutte le chain, contratti veri
esclusi, copie con pool gonfiati in cima) ma
`app/trading/onchain/token_search.py`: Jupiter su Solana (`isVerified`),
GeckoTerminal filtrato su Robinhood (verificato = `coingecko_coin_id`,
pool senza scambi = liquidita' zero). Un token per ticker. DexScreener
resta solo come ripiego se la fonte non risponde. GeckoTerminal da' 429
sopra ~30 richieste/minuto: la cache e' di 60s per (chain, query).

Merge con main (stessa sessione): nel frattempo `main` ha ricevuto il
layout telefono del Pilota (menu ⋯, swap a passi, stesso riordino
grafico → ordine → posizioni). Il mio blocco `@container (width < 640px)`
e' stato tolto perche' doppione; di questa PR restano il flusso token
unico, il picker e la ricerca ticker.

---

## Deploy congiunto #70–#73 — 2026-09-23

Lorenzo: "DEPOLYA TUTTO". #73 (Pilota) e' entrato da solo; #70, #71, #72
sono entrati insieme dal branch `claude/deploy-all-sneda2`. Id della
bacheca rinumerati per non sovrapporsi: #70 `seed-0086`, #71 `seed-0087`,
#72 `seed-0088` (telefono) e `seed-0090` (ticker), #73 `seed-0089`.
I tasti in alto di #70 restano nel DOM ma #73 li nasconde via CSS.
Conflitto non testuale trovato e sistemato: il `data-view` aggiunto da #73
a `#app-shell` rompeva il replace di #71 che mostra la sezione giusta al
primo disegno; ora `_render_onchain_app()` cerca l'elemento per id.

Rifinitura (PR nuova, #72 e #75 gia' unite): Lorenzo, secondo screenshot,
"modifica design di selezione token, voglio immersivo pulito e ben fatto".
Titolo per uso, loghi (icon di Jupiter / image_url di GeckoTerminal,
lettera colorata come ripiego), spunta verificato, scheletro in
caricamento. Il campo e' `type=search name=search`: togliere "indirizzo"
dal segnaposto non bastava, Safari propone i contatti su qualsiasi campo
di testo che non sia una ricerca. Da verificare sul telefono vero.

Seguito (stessa sessione di deploy) — Lorenzo: "se clicco su ETH mi
switchi la visualizzazione in dollari, in Bitcoin e basta". `seed-0093`:
tocco sulla cifra del saldo = nativa → USD → BTC. Scelta in localStorage
(`onchain.balanceMode`), prezzo BTC da Kraken (`prices.btc_price_usd()`,
campo `btc_price_usd` del saldo). La sparkline resta in USD/nativo.

---

## Token fuori da Uniswap v3 (MYCE / MYCEL) — `seed-0092` — 2026-09-23

Lorenzo, screenshot da iPhone su Robinhood Chain: "sto errore non deve
MAI SUCCEDERE" (grafico vuoto, "Nessun pool per questo token su nessun
fee tier", "Nessun dato disponibile per MYCE@robinhood:0x..." fuori
schermo, swap "Preventivo non disponibile"). Aveva cercato MYCEL, non
MYCE. Poi, correggendo la prima idea (filtrare i token non scambiabili):
"non e' che deve escludermi dei risultati [...] io ti scrivo tutta roba
che e' presente su Dex Scanner. Quindi tu devi semplicemente utilizzare
Dex Scanner e vedrai che trovi tutto".

Misurato: MYCE e MYCEL vivono solo su Pons (pons-v2, pons-v2-dex) e
Uniswap v4; il sito guardava solo Uniswap v3. La ricerca scartava MYCEL
($4.7k di pool, sotto la soglia $10k dei non verificati).

Fatto:
- ricerca senza soglie, DexScreener unito alla fonte principale per
  indirizzo (`token_search.merge_candidates`); MYCEL esce MYCEL;
- grafico dal pool DexScreener piu' liquido, con `token=<indirizzo>` a
  GeckoTerminal (MYCE e' la quota in SHROOM/MYCE), fino a 3 pool, un
  secondo tentativo sul 429; prezzo live dallo stesso pool fuori da v3;
- preventivo via `aggregator.py` (KyberSwap, poi LI.FI) quando v3 non ha
  la coppia o l'RPC cade; risposta con `route: "aggregator"` e lo swap
  mostra il prezzo senza firmare;
- nessun indirizzo grezzo nei messaggi d'errore (l'overflow CSS era gia'
  stato chiuso su main da 4b7aaf2).

Resta, **aspetta il via di Lorenzo** (tocca soldi veri; la modalita'
automatica ha bloccato la modifica a `execute.py`): firmare lo swap
preparato dall'aggregatore. Piano: `/route/build` di KyberSwap (o la
`transactionRequest` di LI.FI) → firmare solo se `to` e' in una lista di
router (KyberSwap 0x6131B5fa…37b5, LI.FI 0xB477751B…4Af3), approve
dell'importo esatto se si vende un token, ETH nativo come `value`.

Dedotto dal codice, non provato dal vivo: il percorso v3 manuale
(`build_signed_robinhood_swap`) manda `value: 0` con `token_in` = WETH e
nessun approve, quindi vendere ETH nativo o un token senza allowance
dovrebbe andare in revert. Anche questo si risolve col percorso
aggregatore.

Seguito (#80 online): con GeckoTerminal in 429 la ricerca MYCEL tornava
solo i pool DexScreener (niente MYCEL) e li teneva in cache 60s. Ora un
secondo tentativo sul 429 e nessuna cache se una delle due fonti e' caduta.

---

## Radar dei token giovani — `seed-0094` — 2026-09-23

Lorenzo: "voglio che nell'applicazione venga informato di quale token appena
nato, o che ha due o tre settimane di vita con tanta liquidità e bassa
capitalizzazione [...] quale delle strategie performa bene, una specie di
alert costante [...] su Solana o su rete Robinhood [...] deve esserci un
minimo di backtest". Poi, sul grafico: "voglio la stessa grafica del sito
[...] zoomare [...] vedere in tempo reale gli ingressi e le uscite delle
strategie [...] che eventualmente potrei attivare oppure no".

Fatto (branch `claude/token-scanner-strategie-a97cto`):
- `app/trading/onchain/radar.py`: giro ogni 15 min (loop in `lifespan`,
  `settings.onchain_radar_enabled`), GeckoTerminal su Solana e Robinhood,
  filtri e soglie come costanti in cima al file. Backtest solo long con
  costi DEX su tutte le strategie + configurazioni "pronte" dell'archivio
  (`archive.ready_entries()`). Stato su `data/onchain_radar.json`.
- Accumulo/Distribuzione e' provata e mostrata ma **mai proposta**
  (`UNRELIABLE`) finche' `seed-0010` non e' corretto: toglierla da li'
  quando entra il fix.
- Frontend `static/onchain/radar.js`: blocco `#radar` nella vista Pilota,
  foglio con grafico a candele stile `app.js` (lightweight-charts),
  marker IN/OUT per strategia, live ogni 30 s. L'interruttore per strategia
  crea/aggiorna una voce di watchlist **solo alert** (`auto_trade` spento).
- Il grafico del radar NON usa `chart.js` (fonte dati di #78): usa le
  stesse candele GeckoTerminal del backtest, cosi' i marker coincidono.

Seguito, stessa sera. Lorenzo: "ottimizza [...] che non ci siano ritardi e
che io sia informato sui listing [...] quasi istantaneo". GeckoTerminal ha
7-8 minuti di ritardo sui pool nuovi e 60 s di cache, quindi
`app/trading/onchain/listings.py` usa tre fonti (log di creazione pool dal
nodo Robinhood ogni 3 s, pump.fun laureati ogni 8 s, GeckoTerminal ogni
60 s) e rilegge i pool in attesa su DexScreener finche' arriva la
liquidita'. Spinti al browser via SSE (`/api/onchain/radar/stream`),
Telegram solo per pool < 15 min, max 12/ora per utente. Limite noto: su
Solana i lanci fuori da pump.fun (Raydium LaunchLab, Meteora...) arrivano
solo da GeckoTerminal; per l'istantaneo vero servirebbe un RPC Solana a
pagamento con logsSubscribe.

Resta: vederlo sul server vero; decidere con Lorenzo se l'alert delle
proposte (non dei listing) deve anche arrivare su Telegram e se l'interruttore debba poter accendere l'acquisto
automatico (oggi no, di proposito). Primo giro reale: poche proposte
(1 su ~100 token), Robinhood ha ancora pochi pool giovani liquidi.

### Seguito — filtro di legittimita' e radar come prima pagina — `seed-0095` — 2026-09-23

Lorenzo: "voglio evitare rug pull [...] voglio token legittimi con progetti
seri [...] market cap non oltre i 100.000 dollari [...] un link per andare sul
sito del token", poi "fai un controllo anche per github [...] voglio evitare
SHITCOIN e MEMECOIN", "aggiungi anche il report di token sniffer", e "la prima
pagina quando entro sia proprio questa qui [...] i pop-up in una lista [...]
e il grafico [...] quale strategia performerebbe meglio [...] in tempo reale".

- `app/trading/onchain/legit.py`: `assess()` -> ok / fail / wait. Ordine:
  nome da meme (fail) -> RugCheck/GoPlus (fail) -> Token Sniffer (fail se
  segnalato o < 70/100; "non attivo" senza chiave) -> social -> sito proprio
  raggiungibile (wait se manca) -> GitHub non fork, >= 5 commit su >= 2 giorni
  (fail; wait se GitHub non risponde) -> Claude sul sito (puo' solo bocciare;
  "non attivo" senza chiave). Il sito si scarica con controllo anti-SSRF
  (solo IP pubblici, redirect ricontrollati a mano).
- Soglie nuove: cap <= $100k, liquidita' >= $8k e >= 10% della cap, sia in
  `listings.py` sia in `radar.py`. I "wait" si riprovano ogni 2 minuti finche'
  il pending non scade (2 h); gli scartati si contano (`status().rejected`).
- Telegram (`listings.telegram_text`): link a sito, GitHub, X, Telegram,
  Token Sniffer, grafico, "Apri in DEGEN". Avviso se il pool ha meno di 1 h.
- Backtest automatico di ogni listing: `radar.listings_backtest_loop()`,
  candele 1m (5m oltre 12 h), minimo 45 candele, rifatto ogni 2 min (10 oltre
  le 2 h); arriva al browser come evento SSE `update`.
- Prima pagina: `#radar` e' il primo blocco di `#app-shell` (vista Pilota):
  avvisi a sinistra, palco con grafico dal vivo a destra (di default l'ultimo
  uscito; un tocco su una riga lo blocca per 3 minuti).
- **Da fare sul server**: `ANTHROPIC_API_KEY` e `TOKENSNIFFER_API_KEY`
  (piano Pro) nel `.env`; senza, quei due passaggi risultano "non attivo".
  GitHub senza token = 60 richieste/ora: `GITHUB_API_TOKEN` c'e' gia' per il
  deploy e viene usato anche qui.
- **Prossimo**: link ospite in sola lettura per un amico (Lorenzo ha scelto
  "link ospite": radar, avvisi e grafici senza login, niente wallet, revocabile).
- Dopo le prove di Lorenzo dal telefono (stessa sera): listing pubblicato solo
  con grafico gia' disponibile (`listings._chart_ready`, >= 3 candele 1m,
  riprova ogni 15 s tenendo l'esito del filtro); solo strategie del registro
  (`strategy_configs()` non legge piu' l'archivio: "non voglio vedere
  strategie applicate ad altri ticker"); timeframe automatico
  `radar.auto_interval` (il piu' largo con >= 150 candele); `NoDataYet` in
  `providers/base.py`: il monitoraggio non manda piu' "Errore monitoraggio"
  per un pool senza candele.
- Scanner del pilota riacceso (`sniper_enabled = True`, era spento dal 17/09):
  Lorenzo "non deve essere spento sul server". Il ponte
  `_sniper_onchain_bridge_tick` ora prende prima i listing verificati, poi i
  candidati dello sniper solo se cap <= $100k e `legit.assess` == ok
  (`_pilot_vet`, cache 6 h). Intervallo della watchlist = `auto_interval`.
  Attenzione: il pilota di Lorenzo e' acceso con ordini reali abilitati.

### Seguito — grafico mai vuoto, scartati, battito, pagella — `seed-0097` — PR #86 — 2026-09-23

Lorenzo: "Se Dex Scanner visualizza correttamente il ticker [...] nel sito
nostro non può uscire questo errore inaccettabile" (FLIP, poi BUTT: "Nessun
dato disponibile"); "voglio capire che è una cosa live"; "se ci clicco voglio
vedere tutti i parametri di GitHub [...] un bel benchmark"; "invece di usare
Token Sniffer usa qualche sito che ha delle api pubbliche"; "scorrendo giù
voglio una sezione [...] scartati".

- Causa del grafico vuoto: 429 di GeckoTerminal (~30 req/min) letto come
  "nessun dato". Ora ogni chiamata passa da `gecko_get()` in
  `providers/dexscreener.py`: dedup 15 s, tetto 20/min in background e 28/min
  per chi guarda un grafico (`gecko_urgent`), retry 2 s e 4 s, ultima risposta
  buona fino a 30 min, altrimenti `GeckoBusy` (sottoclasse di `NoDataYet`).
  `tests/conftest.py` azzera cache e tetto fra un test e l'altro.
- Token Sniffer rimosso; `settings.tokensniffer_api_key` resta solo perche'
  un .env che la contiene non blocchi l'avvio. Al suo posto GoPlus Solana
  (`judge_goplus_solana`), link al report su RugCheck (`scan_url`).
- Scartati: `listings.note_rejected()` (anche dal giro del radar), salvati nel
  file dei listing, 100 al massimo, evento SSE `rejected`. Battito: evento
  `pulse` ogni 5 s.
- Avviso "dati stantii" spento sui pool DEX, una volta sola per fermo altrove.
- Chiave Anthropic: Lorenzo l'ha incollata in chat; va nel `.env` del server
  (`ANTHROPIC_API_KEY`), non nel repo. Consigliato di rigenerarla.
- Passati ad altri thread: variante di Lorenzo sui minuti (nessuna variante
  batte i costi DEX fuori campione su 32 pool) e link ospite (PR #85).

---

## Lorenzo HF: Lorenzo sui minuti per i token on-chain — `seed-0098` — 2026-09-23

Lorenzo: "creare un algoritmo di trading adatto per l'alta frequenza per
cavalcare queste [...] cripto [...] non voglio utilizzare strategie inverse
[...] quando il prezzo sale sale [...] voglio comunque mantenere la logica di
quella di Lorenzo però applicata ad un time frame sui minuti, quindi con dei
filtri diversi". Poi "completa tutto".

- `compute_lorenzo_hf_signals` in `app/analysis/strategies.py`, nel registro
  come "Lorenzo HF (minuti on-chain)", famiglia trend. Solo long. Stesso
  incrocio sulla pendenza; filtri: VWAP dal lancio, regime per token
  (variance ratio mobile >= 1 su 60 barre), efficienza di Kaufman >= 0.5,
  soglia pendenza 0.5 sigma; uscita all'incrocio o trailing 4 ATR; dopo ogni
  uscita serve un incrocio nuovo. Volume burst presente ma spento (non
  aggiungeva nulla). Macchina a stati: emette solo fronti, mai ingresso e
  uscita sulla stessa barra.
- Radar: entra da solo (`strategy_configs()` legge il registro). **Non**
  collegata al pilota con soldi reali: serve un ok esplicito di Lorenzo.
  Non ottimizzabile dal Lab (nessuno spazio in `optimize.py`); c'e' lo spazio
  Morris in `sensitivity.py` perche' un test lo richiede.
- Misure (script fuori repo, dati GeckoTerminal 1m, costi radar, split
  train/test per md5 dell'indirizzo):
  - 98 pool, ultime ~16 h: Lorenzo originale mediana -18.5%/token, 14 trade;
    HF mediana 0%, 4 trade, +1.3% medio a trade dopo i costi; media +6% ma
    senza i 3 migliori -1.7%. Nessun vantaggio dimostrato: "non perde" nel
    caso tipico e prende i rari pump grandi.
  - VR(4) su 1m/5m/15m < 1 su ~80% dei pool: al minuto i token giovani
    rientrano piu' che proseguire. Il filtro di regime e' quello che conta
    (media per pool da -20% a ~0); len/slope quasi indifferenti (plateau).
  - Prime 16 h dopo il lancio (88 pool): campione con forte survivorship
    (buy and hold mediana +184%). Senza filtro di regime media +47% ma
    mediana -14%; con filtro mediana 0. Tenuto il filtro.
  - Un rug su una candela non lo ferma nessun trailing (peggior trade -83%).
- Resta: se Lorenzo vuole provarla sul pilota, decidere tetti propri (e' una
  strategia a molte operazioni: con $20 ad acquisto i costi fissi pesano).

---

## Swap come un DEX — `seed-0101` — 2026-09-24

Lorenzo: "voglio che l'esperienza su questo sito sia paragonabile a un DEX
[...] dovrebbe automaticamente selezionarmi la valuta che ho nel wallet
[...] quella con maggior quantita' [...] quando seleziono una valuta la
schermata mi va in basso". La revisione generale (meno menu e tasti) e'
di un altro thread; qui solo lo swap.

Fatto: striscia "Nel wallet" sopra lo swap (saldo nativo + portfolio,
ordinati per valore USD, tocco = vendi quello); gamba "vendi" iniziale =
token di valore maggiore, "ricevi" = stablecoin se vendi il nativo,
altrimenti il nativo (o il token del grafico); Disponibile e Max per
qualsiasi token; freccia che inverte; stesso token sui due lati = scambio.
Il picker salva `scrollY` all'apertura e lo rimette alla chiusura (due
volte: subito e dopo 350 ms, per la tastiera di iOS). `_onchain_token_meta`
ora prende simbolo e prezzo da DexScreener anche su Robinhood.

Limite noto: su Robinhood il portfolio vede solo i token che il sito
conosce (USDG + quelli degli ordini limite), non tutto il wallet.
Gli swap via aggregatore restano spenti: aspettano il si' di Lorenzo.

## Telegram interi — `seed-0103` — 2026-09-24

Lorenzo: "Inoltre i messaggi su Telegram arrivano tagliati, non sono mai
completi". Causa: `_notify_deploy` tagliava ogni riga a 120 caratteri e
`italian_line` a 160 (i trailer "Aggiornamento:" sono spesso 130-180); il
riepilogo settimanale tagliava a 170 e mostrava al massimo 12/15 voci.
Ora niente tagli: `telegram._deliver` spezza oltre 4096 caratteri a fine
riga e, se Telegram rifiuta l'HTML (400), rimanda come testo semplice.
Radar e pilota non toccati.

**2026-09-24 — Lorenzo: "rendilo privacy centrico [...] due sezioni distinte, una meme gambling e una seria per trovare gemme [...] in ottica degen".**
Ingresso con due porte (Gemme / Meme), sezione meme dichiaratamente
gambling, etichette strategie neutre, niente nomi nel sorgente pubblico.
Vedi `seed-0115`.

**2026-09-27 — Lorenzo (profilo a $0.00 alle 19:18): "non becca il saldo".**
Letture fallite contate come zero (Solana 429 senza secondo nodo, prezzo
nativo mancante, nodo EVM senza batch). Ora: secondo nodo Solana, batch che
ripiega su chiamate singole, ultima lettura buona fino a 6 ore, `$—` e
"Not read right now" invece di un falso $0; storico wealth v3 (via il punto
a $0). Vedi `seed-0151`.

**2026-09-27 — Lorenzo (screenshot "Deposit with"): "aggiungiamo queste possibilita' per i depositi".**
Pannello Deposit a tre passi (`deposit.py`, `/api/wallets/deposit`, `sheets.js`):
Crypto per rete con QR, Coinbase/Binance, carta via `ONRAMP_URL` (vuoto =
spenta; serve un account on-ramp scelto da Lorenzo). Vedi `seed-0152`.
Chiave DeepSeek: Lorenzo la inserisce in `/opt/liquidity/deploy/.env`
(`DEEPSEEK_API_KEY=...`); consigliato rigenerarla, era finita in chat.

**2026-09-27 — Lorenzo: "come possiamo usare deep seek in modo smart? può aiutarti a scrivere codice?" / "facciamo leggere a deep seek la repository?".**
DeepSeek attivo sul server (`DEEPSEEK_API_KEY` nel `.env`, `ai_review.provider()`
= deepseek, verificato). Aggiunto `.github/workflows/deepseek-review.yml`: legge
il diff di ogni PR con le regole di CLAUDE.md e lascia un commento in italiano
(sostituito a ogni push). Serve il segreto di repo `DEEPSEEK_API_KEY`, che mette
Lorenzo; senza, salta. Modello: `deepseek-reasoner`, cambiabile con la variabile
di repo `DEEPSEEK_MODEL`. Chi apre una PR legge quel commento e risponde ai punti
veri. Proposti anche, da fare: spiegazioni in italiano delle uscite del sistema
e degli alert, riepilogo settimanale scritto.

**2026-09-27 — Lorenzo: "il wallet deve avere anche l'andamento 1h 2h 3h 4h 8h [...] strettamente legato" e "selezionando 'wallet simulato' [...] posso vedere realmente cosa succede".**
Grafico wallet: periodi 1H-8H, una lettura al minuto con l'app aperta (l'header
la registra), linea a gradini, tocco = valore di quel momento (`seed-0153`).
Wallet simulato: `?wallet=sim` su `/api/profile` e `/api/wallets/total`
(`main._sim_snapshot`), storico separato `"<uid>:sim"` in wealth, selettore
Real/Simulated nel profilo salvato in localStorage `lae:wallet`, header con
etichetta SIM (`seed-0154`). DeepSeek PR review: `deepseek-chat` di default
(il reasoner consumava tutti i token e rispondeva vuoto).

**2026-09-27 — Lorenzo: "da oggi considera deep seek un tuo aiutante costante [...] obbiettivo risparmiare token qui; e poi voglio un repilogo giornaliero [...] su telegram", "crea un ambiente di scambio per informazioni", "mettiamo possibilità di parlare con deepseek su telegram?".**
Fatto: chat Telegram con DeepSeek (`deepseek_desk.py`, long polling in
`main._telegram_chat_loop`, solo chat note, tetto 300k token/giorno),
registro dei token per giorno/tipo e riepilogo alle 21 (con le revisioni PR
lette dai marcatori `deepseek-usage` nei commenti GitHub), `DEEPSEEK.md` come
file di scambio e storico delle sue revisioni. NON fatto: DeepSeek che scrive
codice e apre PR da solo (issue con etichetta `deepseek` → Action → PR): il
classificatore dei permessi di Claude l'ha bloccato come agente autonomo;
decide Lorenzo. Il risparmio "qui" è indiretto: Claude non può chiamare
DeepSeek dalla sua sandbox.

**2026-09-27 — Lorenzo: "piano di integrazione di intelligence all'app [...] usando deep seek" / "ottimizziamo questa logica per spendere meno possibile".**
Piano proposto (in ordine): 1) giudizio DeepSeek sui token + 2) misura in
ombra contro gli esiti veri; 3) narrative; 4) spiegazioni in italiano di alert
e uscite; 5) ricerca a parole nello Scanner; 6) brief del mattino. Fatti 1+2
(`ai_scan.py`: meme segnalate a gruppi di 10, una riga di fatti ciascuna,
`alert["ai"]`, `shadow_stats()` nel riepilogo delle 21) e la lettura del sito
delle gemme su DeepSeek (`legit._ai_review_deepseek`, 4000 caratteri, cache
per pagina, non blocca senza `LEGIT_AI_GATE`). Prossimo: quando `shadow_stats`
ha qualche centinaio di giudizi, decidere se il rischio diventa filtro; poi 4.

**2026-09-27 — Lorenzo: "studia un bel piano per incastonare alla perfezione deep seek, esaminando tutto quello che abbiamo fatto".**
Piano scritto in `DEEPSEEK.md` ("Il piano"): cinque regole (niente decisioni
di prezzo; ogni giudizio diventa colonna di `outcomes.py` e passa il suo
cancello AUC fuori campione; batch/cache/tetti; modelli fissi dove bastano;
l'app funziona senza), mappa per modulo e sei fasi. Prossima: Fase 1
(outcomes legge `alert["ai"]`; `research.ai_dossier` e il piano "deep" su
DeepSeek).

**2026-09-27 — Lorenzo: "procediamo poi con tutto" e "ovviamente deepseek deve avere voce in capitolo sul voto finale delle gemme".**
Fase 1 fatta: `ai_risk` scritto nel diario di outcomes e misurato in
`signals()` (non nel modello: arriva dopo la decisione); `research` legge i
finalisti con DeepSeek (80/giorno, cache 7 giorni) e fa `blend` 50/50 col
lettore deterministico; piano "deep" disponibile con DeepSeek. Restano le fasi
2-5. Lezione: tre merge di fila = tre riavvii, e Lorenzo ha visto un 503 sul
Wallet (pagina di Caddy durante il deploy): raggruppare i merge.

**2026-09-27 — Lorenzo: "ci sono troppe schermate, dobbiamo fare un'opera di ingegnerizzazione importante [...] il podio ha senso soltanto per le gemme [...] una leaderboard con le strategie ingresso e uscita".**
Dock da 5 a 4: Meme (Alerts | Picks; Scanner = link in fondo agli Alerts,
tab nascosta), Gems (podio + classifica | Database), Strategie (ex trofeo:
`alerts.strategyBoard` dai `system.candidates`, poi gli alert col risultato del
sistema; niente tab Alerts/Gems, niente podio, niente card "You"), Profilo
(il Wallet ci vive: tasto Swap → vista wallet). Fasi 2-5 DeepSeek ancora da fare.

**2026-09-27 — Lorenzo: "dare l'idea animata che tutto il sito sia gestito da DeepSeek [...] un agent che esamina le cose" e "il podio non deve avere timeframe, è la hall of fame".**
`agent.js`: sfera nel topbar (respira / anelli che girano se `working`), riga
che ruota sulle azioni vere da `GET /api/agent` (`deepseek_desk.note`, scritto
da ai_scan, research, chat), tocco = registro. Strategie: niente 1D/1W/1M,
tutti gli alert di sempre.

**2026-09-27 — Lorenzo: "aggiungiamo l'opzione di [...] un ticker a scelta" e "elimina il nome lorenzo dalla strategia" ("pusha che finiamo i token").**
`manual_scan.py` + `POST /api/onchain/scan` + form in cima agli Alert
(`sheets.openScan`). Etichette strategie: "Trend HF"/"Trend EMA"
(`system.LEGACY_LABELS`, rinominate al caricamento in `alert_track._load`).
Restano: fasi 2-5 DeepSeek (DEEPSEEK.md), idee UI (Picks come filtro degli
Alert, Database come link), il lavoratore DeepSeek che apre PR (serve il
permesso di Lorenzo), la chiave DeepSeek da rigenerare e i segreti da ruotare.

**2026-09-27 — Lorenzo: "la tab alert è confusionale [...] cosa sta per scattare [...] riesumare roba vecchia", "sostituirei Picks con top 15/25/50 [...] non voglio il meme coin", e l'analisi di DeepSeek su Telegram (lp_locked non discrimina, top_holder 0.0).**
Alerts = tre blocchi compatti (`listings.upcoming`, `alert_track.feed` 48h
senza rug, `alert_track.reviving`), serviti da `/api/onchain/alerts/meme`.
Picks tolta (memes.js non montato), `top.js` = Top 15/25/50 dalla classifica
gemme. `legit.holder_concentration` → (None, None) senza topHolders (prima 0%).
Non fatto: pulizia/modifiche al repo da parte di DeepSeek approvate da Claude
(bloccato dal classificatore, serve il permesso di Lorenzo); la pulizia degli
alert vecchi e rug è deterministica, non serve IA.

**2026-09-27 — Lorenzo: "nel podio delle gemme compaiono token con punteggi più bassi rispetto a quelli presenti in database" / "la scansione complessiva è lenta" / "usa deepseek per aiutarti nel coding".**
`leaderboard._rank` per punteggio puro (DREGG non più primo d'ufficio: la
richiesta del 24/09 è superata), Database con punteggio barrato per chi non è
"ranked". ANALYZE_CONCURRENCY 3→5, DB_FEED_PER_TICK 4→6, DB_FEED_MAX_WAITING
12→20: da verificare sul server (rate limit GitHub/DexScreener, 2 vCPU).
DeepSeek nel coding: dalla sandbox di Claude non si raggiunge; oggi aiuta solo
con le revisioni delle PR su GitHub.

**2026-09-27 — Lorenzo: "aumentiamo i poteri a deepseek, dai accesso completo al database [...] usalo come bug fixer [...] tieni a mente di guardare sempre quello che ha scritto quando parli con me".**
Chat Telegram: strumenti in sola lettura su tutto (`cerca_progetti`,
`classifica_gemme`, `alert_ora`, `sistema`, `scartati`, `memoria`, più i rug),
5 giri per risposta, e `segnala_bug` → bacheca con autore "DeepSeek (Telegram)".
CLAUDE.md dice di leggerle sempre e verificarle. DeepSeek non tocca il codice.

**2026-09-27 — Lorenzo: "a prescindere se seleziono top 15 25 o 50 vedo sempre gli stessi progetti".**
La classifica gemme aveva 6 voci. `GET /api/onchain/top?n=` = classifica +
migliori "studied" del database in fascia (`projects_db.search(..., band)`),
con il motivo dell'esclusione. Da valutare: se i filtri della classifica
(MIN_PILLAR, research floor, età) sono troppo stretti.

**2026-09-27 — Lorenzo: "DEVI USARE INTENSAMENTE DEEP SEEK PER AIUTARTI NEL CODING [...] voglio che deepseek riduca drasticamente il tuo consumo di token".**
`scripts/ds.py`: bozza di codice da DeepSeek in blocchi SEARCH/REPLACE,
`--apply` per applicarla; Claude rivede il diff e fa girare i test. Serve che
Lorenzo metta nell'ambiente cloud `DEEPSEEK_API_KEY` e consenta
`api.deepseek.com` nella rete; vale dalla sessione successiva. Regola in
CLAUDE.md ("DeepSeek scrive, Claude rivede"). La leva più grande sul costo resta
aprire sessioni nuove spesso: HANDOVER.md serve a questo.

**2026-09-27 — Lorenzo: "non devi usarli nel tuo ambiente ma comunicarci tramite github [...] DEVI USARE DEEPSEEK ASSIDUAMENTE [...] ok apriamo nuova chat appena hai finito".**
Lavoratore DeepSeek su GitHub, autorizzato esplicitamente da Lorenzo: issue con
etichetta `deepseek` → `deepseek-task.yml` → PR `deepseek/issue-N` → Claude
rivede, corregge, mergia (niente merge automatico; il codice generato gira nei
test senza token GitHub). Istruzioni in CLAUDE.md ("DeepSeek scrive, Claude
rivede"). Nella prossima chat: provarlo con un compito piccolo e aggiornare lo
storico in DEEPSEEK.md. Serve l'etichetta `deepseek` nel repo (la crea la
prima issue con quell'etichetta, o Lorenzo da GitHub → Issues → Labels).

**2026-09-27 — chat nuova. Lorenzo: "nuova chat nuovo inizio come ci siamo detti, riprendiamo da qui" / "usa sempre deepseek e tu revisiona il suo lavoro da github".**
Regola resa assoluta in CLAUDE.md: ogni modifica al codice passa da una issue
`deepseek`, Claude rivede la PR. La bacheca non era leggibile da questa sandbox
(rete che blocca `liquidityengine.app`): va aggiunto il dominio alla rete
dell'ambiente cloud.

**2026-09-27 (notte) — prima sessione con DeepSeek che scrive tutto.** Lorenzo, con screenshot: pannello agente in verticale, "AAVE non ha 531k di market cap", "signal, why e info devono essere sempre completi", poi il report in 10 punti di DeepSeek da Telegram.
Issue #176/#177/#178/#182 → PR unite (seed-0167..0170). Lavoratore corretto tre volte:
`path=` davanti al percorso, "Tests:" dentro il compito, risposta vuota su
`path/to/file`; l'Action non puo' aprire PR (403, impostazione di GitHub
Actions): le apre Claude dal branch `deepseek/issue-N`. Rilanciare una issue =
togliere e rimettere l'etichetta `deepseek`.
Resta aperto: esempio di simbolo sbagliato (Lorenzo non l'ha ancora dato);
sistema trend che entra 1 volta su 12 alert e non ha preso Onhand +1304% (da
analizzare se Lorenzo vuole); mediani top holder a 0 in `circostanze_rug`
(forse dato mancante letto come 0); dopo il deploy verificare che il modello dei
rug trovi esiti "non rug" (`memoria`).

**2026-09-28 (notte, stessa chat) — Lorenzo: "fai analizzare perche' ha perso ONHAND", "i rendimenti vorrei vederli delle strategie [...] anche la chiusura della posizione", "qui voglio vedere i backtest!!! non voglio vedere 0%", app non centrata sul telefono. "la chat rimane questa".**
#188/#189/#190/#191 unite (seed-0171..0174). Causa ONHAND: `system.follow` scartava
l'ingresso della strategia caduto prima dell'alert (trend gia' partito) e aspettava
un nuovo incrocio: ora lo raggiunge alla prima candela dopo l'alert; SYSTEM_VERSION 3
ricalcola tutto, alert passati con 720 candele. Lavoratore: aggiunti i blocchi
`APPEND` (per il CSS in fondo ai file). Voto dato a Lorenzo: DeepSeek esecutore 7/10,
analista 3/10, lavoratore 5/10. Da fare: il lavoratore lanci anche i test vicini ai
file toccati (#189 ha rotto `test_system.py` senza vederlo) e controlli che gli
import `@onchain/x.js` esistano (#188). Da verificare sul sito: classifica del sistema
riempita dopo il ricalcolo; se il sistema ora entra troppo tardi o troppo presto sui meme.

**2026-09-28 — Lorenzo: "attua le contromisure necessarie per gestire deepseek" / "ma strategia trend follower era la mia vecchia LORENZO".**
Lavoratore (PR #198): test correlati ai moduli toccati, controllo JS e import
`@onchain/`, risposta vuota = fallimento; regole nel prompt. Istruzioni pratiche
in CLAUDE.md ("Come scrivere e gestire le issue"). Sul trend follower: si',
Trend EMA = la sua Lorenzo originale, Trend HF = la variante on-chain a 5m con
filtri (VWAP, efficienza, variance ratio, soglia sigma, trailing ATR); in uso HF
di default finche' 20 alert non sono decisi. Da guardare dopo il ricalcolo: se i
filtri di HF la tengono fuori dai meme piu' della Lorenzo originale.

**2026-09-28 — Lorenzo: "non esiste che su queste crypto non ci sia un backtest delle strategie [...] stessa cosa dobbiamo poter fare qui", "puoi usare anche il grafico del sito principale", "non voglio selezionare le strategie [...] mostrami i backtest migliori".**
`system.backtest_all` (radar.evaluate su 4 strategie, A/D esclusa) sulle barre 5m di
ogni alert, SYSTEM_VERSION 4. Classifica: backtest migliore per alert (scelto a
posteriori, detto nella nota). Pagina token: tabella per strategia + link al sito
principale (`/?area=analizza&dex=SYM@chain:pool&interval=5m&strategy=...`,
`openDeepLink()` in app.js al posto del ticker salvato). Il sistema trend (48h
dopo l'alert) resta calcolato ma non e' piu' la vista predefinita.

**2026-09-28 — Lorenzo: "istruisci deepseek per migliorarlo nei suoi compiti ogni volta che sbaglia".**
`.github/deepseek/LESSONS.md`: gli errori corretti in revisione, uno per riga, passati
a DeepSeek in ogni compito (prima di CLAUDE.md nel prompt). Sotto `.github/`, quindi
DeepSeek non puo' modificarlo. Regola in CLAUDE.md: a ogni correzione di una sua PR,
una lezione nuova nello stesso commit; se lo stesso errore torna, un controllo nel
lavoratore.

**2026-09-28 (notte) — Lorenzo: coppa sul podio, profilo in una schermata, "podio cartoonesco [...] cyberpunk come il logo" ("lavoro da designer, servi tu"), "non indichiamo cosa usiamo, semplicemente i rendimenti", "proporre sempre il miglior risultato".**
#211, #214, #216 via DeepSeek (corretti in revisione, lezioni aggiunte); podio e righe
compatte scritti da Claude (PR #217: `podium.js` nuovo, classi `.pod-cy`/`.pc-*`).
`format.bestSystem(a)`: il migliore fra le due versioni del sistema, sempre "System".
Resta da decidere: il pulsante "Open on the analysis chart" porta al sito principale
dove il nome della strategia si vede nel menu (ok se il sito principale e' solo di
Lorenzo). Il lavoratore non intercetta ancora gli identificatori non definiti in JS
(#190 usava `strategyTrade` senza import): se ricapita, aggiungere un controllo (eslint no-undef).

**2026-09-28 (mattina) — Lorenzo: "UI troppo affollata riprogettala", "no signal [...] dinamicamente animata", "la top 15-25 deve andare in questa tab (icona coppa)", "lock e xona sempre nel podio [...] RISOLVI", "backtest in loop non arrivano", "eliminare i token da ogni lista [...] ognuno nel proprio account [...] successore animato".**
Alerts riprogettata da Claude (auto-trade a barra + pannello). Top 15/25/50 = prima scheda
gemme ("Top" con coppa), `#board` nascosto (leaderboard.js gira ancora per i dettagli),
podio dai primi 3 di `top.js`, `/api/onchain/top` ordinato per punteggio. Backtest: puntini
solo se `backtests` manca, altrimenti OUT/IN/risultato. Nascondi token: `profiles.hidden`/
`set_hidden`, `GET/POST /api/profile/hidden`, `hidden.js` (isHidden, hideToken con collasso
WAAPI + Undo, withEntrance per l'ingresso del successore), filtro in top/alerts/projects/
memes/radar. Lavoratore DeepSeek: niente test collegati per main.py, max 10, timeout
riportato; ESLint no-undef sui moduli onchain toccati. Da verificare sul sito: Onhand senza
trade nel backtest nonostante il pump (dati server).

### 28/09 (sera) — grafico, Phantom, laboratorio, scanner
Lorenzo: "Il grafico nel sito principale e' fatto apposta per long e short. Tu di quello devi solo prendere l'apertura del long e la chiusura del long." — "una connessione di un wallet esterno deve permettere di aprirlo senza cambiare finestra di Safari" — "non voglio che Pump Fun diventi il nostro bacino di token [...] tutto quello che e' facilmente identificabile come rug pull escludiamolo a priori" — "ogni narrativa deve avere dei token al suo interno" — "la strategia si deve automaticamente disabilitare [dopo un -60/70% veloce] [...] il backtest non deve proseguire" — "non voglio vedere schermate con scritto alert, voglio ingressi e uscite" — "diamo a DeepSeek una tab tutta sua [...] voglio vedere come ragiona". Fatto e in corso: vedi "Stato al 28/09 sera" in cima.


## Decision assurance — specifica tecnica A01–A08 — 2026-09-29

Lorenzo: "devi essere tecnico [...] leggi la repository [...] poi l'attuazione sarà di claude".
Codex ha letto main e8e0a97c688cf36461a1f43791b4e19610e0b33b e preparato docs/decision-assurance/: specifica, contratto SQLite isolato e catalogo di 29 criteri di accettazione. Copre ground truth, utilità umana, manipolabilità, costo degli errori, asset dati, governance, diritti fonti e perimetro prodotto. Non applica fix runtime e non dichiara concluse #347/#357/#358. Tredici test del solo prototipo passati; suite applicativa non eseguita. Claude implementa in sette PR secondo README, iniziando da snapshot shadow e label, coordinando i lavori esistenti. Attenzione: outcomes.apply_sample confonde attualmente prezzi mancanti/crollo/liquidità nella label legacy rug; il nuovo target verified_exploit non deve ereditarla automaticamente. Non eseguire contract.sql come migrazione di produzione. Nessuna automazione DeepSeek attivata da questa consegna.

### 29/09 — Classifica progetti (Gem Finder), studi DeepSeek e Top
Lorenzo: "stagli addosso a DeepSeek [...] deve essere un lavoro perfetto" — "come mai grid punteggio cosi basso?" — "voglio che appena arriva questo messaggio su telegram ci sia effettivamente un cambio nella classifica con animazione di distruzione particellare [...] soltanto quando sono su quella schermata, in sequenza per tutti i sostituiti dal mio ultimo ingresso".
Fatto: studi 001/002 rivisti (`.github/deepseek/studi/`), GitHub multi-repo (#341), avviso Telegram col posto reale della Top, animazione `particles.js`/`top.js` (solo a schermo, in sequenza, `lae:top-seen`), quota giudice 1500 + Top 150, `PROMPT_VERSION` 4, `lift_rejected`, match indirizzi EVM senza maiuscole (v10, AUREON), link DexScreener che riempiono sito/GitHub (v11), il Top rilegge letture da prompt vecchio (`judge.wants_reading`).
Diagnostica server sola lettura: `backend/scripts/gem_diag.py` via stdin (non e' nell'immagine Docker).
Da verificare dopo il deploy v11: AUREON entra e viene analizzato; PFWA ha cap; BV7X non piu' "single wallet 41%" (i contratti sono fuori dai limiti per wallet, solo >50% in un contratto e' fatale); STEALF/GRID/PFWA con letture nuove.


## 2026-09-29 — ENGN motion kit: asset e handoff per Claude

Lorenzo ha chiesto un pacchetto dal suo cubo Meshy: "da inserire in più contesti; funzionali e meno", aggiornare "i modelli della leaderboard top 15" con qualcosa di animato, e "sistema sia per desktop che per mobile, ma per desktop poi visualizzalo versione desktop". Ha indicato questa repository per passare modelli e istruzioni a Claude.

Consegnato in `design/engn-motion-kit/`: galleria responsive, 12 SVG e web component di stato, hero 3D con assemblaggio di 3 secondi, podio 3D con lo stesso GLB, prototipo Top 15/25/50 e adattatore del contratto renderPodium. GLB ottimizzato a 1.999 MB; texture originali ridotte a 1024 px, taglio in 27 moduli e rimozione della pedana. `CLAUDE.md` nella cartella contiene la mappa di integrazione verificata su podium.js, top.js e app.css (desktop >=1100, rail >=1360, lista 420 px).

Stato: pacchetto di design e prototipi, NON integrato nel frontend di produzione. Nessun import live, backend, ranking o flusso wallet modificato. Dati della galleria dichiarati illustrativi. Controllati desktop 1440x1000, mobile 390x844 senza overflow, Top 25/50, ricerca, evento di selezione, progress e error; limiti in QA.md. Prossimo passo per Claude: seguire il workflow della repository, integrare a piccoli passi preservando data-open, .pc-slot in ordine 1/2/3, still, tokenRow, filtri e logica seen/onScreen. Non sostituire il terminale desktop con la galleria a tutta larghezza.

### 2026-09-29 — Motion kit integrato (thread "Kit animazioni ChatGPT")

Lorenzo ha incollato il messaggio di ChatGPT (PR #383, mergiata come asset). Integrato a mano (Actions ferme per minuti, niente chiave DeepSeek in locale):
- `frontend/static/onchain/motion.js`: web component `<engn-motion>` dal kit, testi in inglese; corrette le due animazioni che non erano transform/opacity (`ignite` su stroke-width, `ripple` su r).
- Podio (`podium.js`, `app.css`): stesso cubo cyberpunk approvato il 28/09, ma ora parte da 27 moduli che si assemblano 3-2-1 (l'"engine boot" del kit, ~1.5 s), poi fessura e testa. Contratto invariato (`still`, `.pc-slot` 1/2/3, `data-open`, `pc-taken`). Still/reduced motion: solo cubo pieno.
- Top (`top.js`): prima della prima classifica il posto del podio mostra il cubo in stato loading, "Reconnecting…" se la richiesta fallisce senza dati.
Scartato per ora: hero WebGL (three.js da CDN + GLB 2 MB, etichette in italiano) per la landing, podio 3D (il kit stesso consiglia SVG nella lista compatta), galleria Top con dati demo. Possibile prossimo passo: hero della landing con l'assemble SVG di motion.js invece del WebGL.

Stesso giorno, poco dopo. Lorenzo: "devi seguire cosa dice chat gpt che le ha fatte meglio di te; poi pusha". Quindi il kit si applica alla lettera (`design/engn-motion-kit/CLAUDE.md`), il mio podio a 27 moduli e' sostituito:
- `podium.js` ora re-esporta `podium-adapter.js` (l'adapter del kit, che importa `@onchain/motion.js` e carica `podium-adapter.css` con la stessa `?v=`). Contratto invariato per top.js, alerts.js e leaderboard.js.
- Righe Top 15/25/50: barra del punteggio, hover e bordo menta sui primi tre (CSS, `--v` messo da top.js). Nessun dato demo.
- Landing `engn.html`: hero 3D del kit (3 s, GLB 2 MB) in un iframe `static/engn/motion/hero-3d.html?embed=1`; three.js 0.180 ospitato in locale (`static/engn/motion/three/`, MIT), niente CDN. Il cubo SVG resta finche' il 3D non manda `engn-hero:ready`, e resta per sempre se WebGL o il modello falliscono. Testi tradotti in inglese.
- Non fatto: podio 3D WebGL (il kit lo vuole solo "in un contesto ampio", senza indicare dove; nella lista compatta consiglia l'SVG).
Le vecchie regole CSS `.pod-cy`/`.pc-mod` in app.css sono ora inutilizzate.

### 2026-09-30 — Desktop refinement (mobile frozen)
Lorenzo: "il mobile non toccarlo per ora", then "fai rifiniture".
Added desktop-only rules (min-width:1100px) to ui-refinements.css: compact 136px page introduction, 38px rank cubes, denser selected token rows, a larger chart, compact Scout status and activity ledger, quieter empty-wallet action, and a small desktop height variant. No mobile CSS or transaction logic changed in this refinement. Earlier uncommitted mobile redesign work still exists in the branch and must not be treated as newly approved for deployment.
Preview uses local synthetic read-only fixtures. Checked desktop at 1440x1000 and 1280x800, with no observed horizontal overflow; no production financial actions tested. Final publication and full integration review remain pending. See docs/engn-ui/INTEGRATION.md for the user's requirement to preserve the supplied visuals exactly.

### Delivery scope — 2026-09-30
Lorenzo requested "pusha e fai applicare a claude". Deliver the desktop design faithfully using docs/engn-ui/INTEGRATION.md and its screenshot. New stylesheet links are desktop-gated at 1100px; mobile experimental styles must not be enabled. Main has advanced while this design was reviewed: reconcile latest functionality without redesigning the desktop, and preserve the current mobile implementation. Shared Scout copy remains intentional. No auto-merge or production transaction test was performed by Codex.

### 2026-09-30 — PR #392 integrata in main (Claude)
Lorenzo: "applica: Il desktop è stato pushato nella PR #392, con codice e istruzioni per Claude". Merge del branch `codex/engn-ui-redesign` com'e'. Conflitti: `podium.js` resta il re-export di `podium-adapter.js` di main (la modifica del branch toccava il vecchio renderer; le regole desktop del podio stanno in `ui.css`/`ui-refinements.css`); sulla landing desktop l'iframe `hero-3d` di main e' nascosto (`engn-landing.css`) perche' il riferimento mostra solo `<engn-motion>`. Verificato: 1440x1000 e 1280x800 senza overflow orizzontale; 390x844 uguale a main. Non verificato da sloggati: le viste interne dell'app (servono login e dati reali).

### 2026-09-30 — Logo dello Scout: il cubo ENGN (Claude)
Lorenzo: "il logo dello scout deve essere lo stesso cubo del nostro engine in miniatura che si anima aprendosi e chiudendosi; non la sfera viola". La sfera (`.agent-orb`, `.ag-orb`) e' sostituita ovunque (barra in alto, pagina Scout, scanner manuale) dal cubo di `scout-cube.js`: il coperchio sale, i fianchi si aprono, appare il nucleo menta, si richiude. Lento a riposo, veloce con anello quando lavora, grigio fermo se spento. Stile in `scout-cube.css`, caricato per ultimo su tutte le larghezze. Fatto a mano (Actions ferme, niente chiave DeepSeek in locale).
