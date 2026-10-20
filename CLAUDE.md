# Note per Claude

## Da fare a ogni conversazione, prima di altro

Leggi `HANDOVER.md`: e' la memoria fra una conversazione e l'altra — filoni
di lavoro pluri-sessione, il loro stato, e un log di cosa Lorenzo ha chiesto
e perche'. Una chat diversa da quella che ha fatto l'ultimo lavoro deve
poter ripartire da li' senza rileggere tutta la cronologia precedente.

Leggi la bacheca segnalazioni:

```
curl -s https://liquidityengine.app/api/issues
```

Sono i problemi che Lorenzo e chi lavora con lui hanno scritto dall'app.
Quelli con autore **"DeepSeek (Telegram)"** li scrive DeepSeek dalla chat
(Lorenzo, 27/09: "usalo come bug fixer [...] tieni a mente di guardare sempre
quello che ha scritto quando parli con me"): leggili sempre, citali a Lorenzo,
e verificali sul codice prima di agire — la sua prima revisione aveva 0
osservazioni valide su 5, la seconda un bug vero (holder a 0%). Se ce
ne sono di nuovi o di aperti, dillo subito e proponi da quale partire, senza
aspettare che te lo chiedano.

Dopo un lavoro non banale (un piano nuovo, piu' sessioni sullo stesso filone,
una decisione presa insieme a Lorenzo) aggiorna anche `HANDOVER.md` — stato
del filone, cosa resta, e una riga nel log delle conversazioni con le parole
di Lorenzo, non solo un riassunto tecnico. Un piano scritto con lo strumento
di planning locale (`ExitPlanMode`) non e' mai versionato da solo: il suo
contenuto va riportato qui o si perde alla fine della sessione — nessuna
chat futura potra' piu' leggerlo.

Quando risolvi qualcosa, scrivi la risoluzione in
`backend/app/data/resolutions.json`, con chiave uguale all'`id` della
segnalazione. **Non modificare le segnalazioni**: quelle vivono sul volume Fly e
appartengono a chi le ha scritte.

| | dove vive | chi scrive |
|---|---|---|
| segnalazioni | volume Fly, `data/issues.json` | loro, dall'app |
| risposte loro | volume Fly, `data/issue_replies.json` | loro, dall'app |
| risoluzioni | repo, `app/data/resolutions.json` | Claude, via git |
| risposte Claude | repo, `app/data/replies.json` | Claude, via git |

Ogni problema segnalato in chat va **anche** sulla bacheca: una voce in `_SEED`
con la sua risoluzione. Altrimenti resta solo nella conversazione, e la bacheca
racconta metà del lavoro.

Una risposta con `reopen` riapre la voce: "risolto" lo decide chi ha segnalato.
Per richiuderla serve una risoluzione con un campo `at` più recente della
riapertura — senza `at`, la riapertura vince sempre.

L'unione avviene in lettura, per `id`. Un id che non corrisponde a nessuna
segnalazione è una diagnosi che nessuno vedrà mai — c'è un test che lo verifica.

## Il progetto

Repository: `snowcomingsoon/liquidity-analysis-engine` (account rinominato il 16-17/10 da `lorenzocorazzi-wq`; i nomi vecchi solo reindirizzano, nel codice il nome sta in `settings.github_repo`).

FastAPI + frontend vanilla JS, deploy automatico da `main` su un server
proprio (Hetzner CX23, ~2 minuti). Vedi `deploy/README.md`. Fly e' spento ma
resta come via di ritorno.
**Ogni lavoro finito va online senza chiedere** (Lorenzo, 16/10: "I deploy
devono sempre andare online", poi "scrivi tu la regola in CLAUDE.md"): dopo
le verifiche, PR dal branch della chat e merge in `main`.
**Due grafiche nell'app on-chain, una per account** (Lorenzo, 17/10, "nota
importante, ricorda sempre"): il sito classico e' uguale per tutti, e li' si
modifica per tutti gli account senza chiedere. Nell'app on-chain (gemme e
Discover): le modifiche di **funzionamento** valgono per tutti gli account
(anche nella copia v1, senza cambiarne la grafica); le modifiche **grafiche,
le sezioni nuove e simili** solo per l'account whitekobra (Lorenzo) (`static/onchain/`).
Gli altri account (`settings.onchain_v1_emails`) hanno la copia congelata
`static/onchain-v1/` + `onchain-app-v1.html` (HANDOVER 16/10 `seed-0325`).
Per la sezione gemme **chiedi sempre conferma** prima di applicare.
**Chiedi anche per quali account** (Lorenzo, 20/10: "il podio va cambiato
solo per whitekobra. Chiedilo sempre prima di modificare"): nelle gemme e
in Discover non decidere da solo se una modifica e' "di funzionamento" e
quindi per tutti; prima di toccare `static/onchain-v1/` chiedi.
Il codice sta in `backend/app`, il frontend in `frontend/`.

**Python 3.12 obbligatorio** — `pandas-ta` non si installa su 3.11. Se la shell
ha una versione più vecchia: `uv venv --python 3.12 backend/.venv`, poi
`uv pip install --python backend/.venv/bin/python -r backend/requirements.txt`.

Tre strategie, e **una sola è trend-following**:

| strategia | meccanica | famiglia |
|---|---|---|
| Lorenzo | incrocio EMA sulla derivata di una media | trend-following |
| Gabriele | RSI + banda di Bollinger | mean-reversion |
| Accumulo / Distribuzione | divergenze RSI su swing | contro-trend |

Confonderle è il modo più facile di sbagliare: un filtro che chiede persistenza
è giusto per la prima e rovesciato per le altre due.

## App on-chain: niente trading (07/10)

Lorenzo, 07/10: "non voglio piu' vedere strategie automatiche [...] questa
parte di trading deve sparire". Trend follower, RSI+BB, pilota/autotrader,
portafoglio simulato, Meme Sniper, swap e ordini limite sono spenti
(`settings.onchain_trading_enabled = False`, `<html data-trading="off">`).
Le regole del 28-30/09 "ogni token della Top mostra un backtest" e "frecce
ingresso/uscita della strategia su ogni grafico" **non valgono piu'**: non
ripristinarle. Il lavoro adesso e' la qualita' della Top (uso reale, volumi,
partecipazione): vedi `HANDOVER.md`, voce del 07/10.

## Catalogo di design (12/10)

`design/opensourceui/CATALOG.md`: i 210 componenti di opensourceui.in (MIT,
Bidyut Kundu) studiati e ridotti a token CSS esatti, 10 famiglie di stile,
indice per componente e note di porting da Tailwind a CSS puro. Lorenzo:
"studia tutti i design e li tieni in memoria". Leggi solo la sezione che
serve (`grep -n "^### "`), non tutto il file.

## Minuti GitHub Actions (16/10)

Il 16/10 i 3.000 minuti del piano privato sono finiti (ambiente di test
chiesto dal tester ~1.870 min, deploy ~1.370) e GitHub ha fermato anche
il deploy. Lorenzo ha reso il repo **pubblico**: le Actions ora sono gratis.
Quindi niente segreti nel repo, mai (chiavi solo nei Secrets di GitHub o nel
`.env` del server). I tagli di #533/#534 restano: job raggruppati, niente
job per singola coppia.

## Cose misurate, da non riderivare

- **L'obiettivo del backtest è una funzione a gradini.** 200 valori di un
  parametro danno 5 risultati distinti; il 98% dei passi non cambia nulla. I
  metodi che presuppongono continuità (Nelder-Mead, CMA-ES, ottimizzazione
  bayesiana con kernel lisci) qui non si applicano.
- **L'espansione guidata batte il sorteggio a parità di budget.** KASUSDT
  daily, ramo a 7 parametri, 93 312 celle, budget 700: guidata 57.44 contro
  50.39 / 26.93 / 37.35 di tre semi diversi. Ed è deterministica, quindi non
  esiste più nessun ramo "non riproducibile".
- **La ricerca casuale è una lotteria.** Stessa serie, cambia solo il seed:
  `cv_oos` 66% su Gabriele, 225% su Lorenzo. Con la pipeline deterministica
  scende a 0% — ma solo dove le celle si enumerano.
- **Su KASUSDT daily nessuna delle due strategie ha edge.** Il gate blocca
  entrambe (VR≈1.15, indistinguibile da random walk), tutti i seed danno OOS
  negativo, e buy-and-hold faceva +643%.
- **Il PBO conferma il verdetto dello Sharpe deflazionato, non lo duplica.** Su
  una serie senza edge: PBO 0.56 su 5 candidati (soglia 0.20), DSR 0.02. Il
  primo giudica la *selezione*, il secondo corregge un *numero* — un risultato
  può superare l'uno e fallire l'altro.
- **La volatilità da sola non dice niente; l'efficienza sì.** Rapporto di
  Kaufman (distanza percorsa / strada fatta) su daily reali: BTCUSDT 0.037,
  KASUSDT 0.006, PEPEUSDT 0.008. Una serie sintetica in trend fa 0.54. È la
  misura che separa "si muove molto" da "va da qualche parte".
- **La soglia di pendenza in unità di sigma paga sulle coppie agitate.**
  `slope_threshold_sigma=0.5` su daily reali: PEPEUSDT +195.6%→+230.6% con
  drawdown 14.2%→10.0% e PF 2.88→4.55; KASUSDT +120.0%→+124.4% con DD
  32.2%→28.2%; BTCUSDT invariato. A 1.0 peggiora ovunque. Default 0 (spenta):
  accenderla cambia tutti i risultati storici.
- **Più parametri = risultato peggiore.** Il ramo di Lorenzo a 4 parametri batte
  quello a 8 sia in-sample sia fuori campione.

## Cose che scottano

Le due voci che stavano qui (`seed-0007` feed dell'ottimizzazione, `seed-0010`
look-ahead di Accumulo) sono **risolte**: `backtest_interval_for()` ora
restituisce il time frame del grafico, `_find_confirmation()` parte da
`swing_pos + swing_length`. Il 16/10 le ho riproposte a Lorenzo come aperte
leggendo solo questa nota: prima di dire che un bug c'e', guarda il codice e
`resolutions.json`.

## Verifiche prima di committare

```
cd backend && .venv/bin/python -m pytest tests/ -q
ruff check backend/ --select E,F,W --ignore E501   # identico alla CI
node --check frontend/static/app.js
```

`node --check` su un `.js` lo legge come CommonJS e lascia passare errori
che il browser rifiuta: i moduli di `frontend/static/onchain/` li controlla
`tests/test_frontend_syntax.py` (copia in `.mjs`). Un solo errore di
sintassi in un modulo blocca tutta l'app (30/09: niente tocchi da telefono).

LibreOffice in sandbox non ricalcola i file Excel: `recalc.py` fallisce
all'avvio, non per colpa del file.

## Consumo di token

Ogni richiesta rimanda l'intera conversazione: il costo cresce con i giri, non
con la difficolta'. Regole che Lorenzo ha chiesto esplicitamente:

- Leggi solo i pezzi di file che servono (`sed -n`, `grep`), mai file interi da
  migliaia di righe per cercare una funzione.
- Raggruppa le chiamate indipendenti in un solo messaggio.
- Non rileggere un file dopo averlo modificato per "verificare": se `Edit` non
  ha dato errore, la modifica c'e'.
- Niente comandi ripetuti per controllare la stessa cosa gia' verificata.
- Risposte sintetiche: dire cosa e' cambiato e cosa resta, senza riepiloghi
  lunghi ne' ripetizioni di quanto gia' detto.

## DeepSeek scrive, Claude rivede

**Aggiornato 01/10.** Lorenzo: "fagli fare soltanto delle cose banali,
semplici [...] la mente devi essere tu e l'intelligenza ce la devi mettere
te [...] non vale la pena far scrivere codice con troppa libertà a lui" e
"revisiona in modo meticoloso tutto il codice scritto da DeepSeek [...] fai
in modo che apprenda da ogni errore". Quindi a DeepSeek solo compiti
banali e ripetitivi, gia' decisi fin nel dettaglio (nomi, firme, dove va
ogni riga); progetto, logica, prompt, regole e tutto cio' che e' delicato
li scrive Claude. Ogni riga di DeepSeek si rilegge, e ogni errore diventa
una lezione in `LESSONS.md`. Quanto segue vale per quei compiti banali.

Lorenzo, 27/09: "devi usare deepseek assiduamente, voglio ridurre
drasticamente il consumo di token con te [...] comunicarci tramite github".
Ribadito in apertura di chat nuova: "usa sempre deepseek e tu revisiona il
suo lavoro da github". Quindi **sempre**, non solo per le modifiche grosse:
ogni modifica al codice che non tocchi soldi, chiavi, firme o esecuzione
reale passa da DeepSeek. Claude scrive a mano solo quelle, i ritocchi al
diff di DeepSeek in revisione, e i file di memoria (CLAUDE.md, HANDOVER.md,
resolutions.json):

**Limite (Lorenzo, 01/10):** "fagli fare soltanto delle cose banali, semplici
[...] la mente devi essere tu e l'intelligenza ce la devi mettere te". A
DeepSeek solo codice ripetitivo e semplice; progetto, scelte, filtri,
integrazioni fra moduli e regole li scrive Claude. Ogni riga di DeepSeek si
rivede (il 01/10, #474 e #478: entrambi falliti, e #478 aveva mancato il
filtro che bloccava ogni backtest dei layer).

1. apri una issue con etichetta `deepseek` (corpo: il compito in poche righe,
   poi `Files:` con i file o `file:inizio-fine`, poi `Tests:`);
2. l'Action `deepseek-task.yml` fa scrivere il codice a DeepSeek, fa girare
   ruff e i test indicati e apre una PR `deepseek/issue-N`;
3. leggi solo il diff della PR, correggi quello che non va, verifica, fai il
   merge. Niente si mergia da solo; se DeepSeek fallisce, lo dice nella issue.

`scripts/ds.py` fa lo stesso da locale, se l'ambiente ha la chiave e la rete.

Come scrivere e gestire le issue (imparato il 27-28/09):

- `Files:` e `Tests:` una sola volta, in fondo; righe `- percorso` o
  `- percorso:inizio-fine`. Un file nuovo va elencato in `Files:` e detto
  nel testo ("crea"); per aggiungere in fondo a un file (CSS) di' "APPEND".
- Il compito deve nominare il comportamento da cambiare **e** cosa va
  ricalcolato o migrato (versioni, dati gia' salvati): DeepSeek non lo vede.
- Rilanciare una issue = togliere e rimettere l'etichetta `deepseek`
  (il branch viene sovrascritto).
- Se l'Action non puo' aprire la PR (403), il branch c'e' comunque: la apre
  Claude da `deepseek/issue-N`, corregge sul branch, poi merge.
- **Ogni volta che correggi una PR di DeepSeek, aggiungi la lezione** in
  `.github/deepseek/LESSONS.md` (una riga: l'errore, la regola, il numero
  della issue), nello stesso commit della correzione. Il lavoratore la passa
  a DeepSeek in ogni compito. Lorenzo, 28/09: "istruisci deepseek per
  migliorarlo nei suoi compiti ogni volta che sbaglia". Se una lezione non
  basta (lo stesso errore torna), il controllo va messo nel lavoratore.
- Il lavoratore fa girare anche i test che importano i moduli toccati,
  controlla la sintassi JS e che gli import `@onchain/` esistano: se uno di
  questi fallisce, DeepSeek riprova una volta e poi lo scrive nella issue.

## Lingua

Lorenzo scrive in italiano. Rispondi in italiano; commenti e messaggi di commit
in inglese, come il resto del codice.

**Ma le notifiche che legge lui sono in italiano sempre** ("i messaggi degli
aggiornamenti li voglio in italiano sempre"). L'avviso di deploy e il riepilogo
settimanale elencano i commit, che sono in inglese: per questo ogni commit
porta un trailer con la riga italiana gia' pronta, in fondo al messaggio, prima
delle righe di attribuzione.

```
Fire alerts at the candle close, not one bar later

<corpo in inglese>

Aggiornamento: gli alert partono alla chiusura della candela, non un giorno dopo
```

Una frase sola, che dica cosa cambia **per chi usa il sito** — non cosa cambia
nel codice. Senza trailer non si rompe niente: `italian_line()` ricade sul
titolo inglese, che e' meglio di un buco, ma il messaggio smette di essere
tutto in italiano. Vedi `app/notify/weekly_recap.py`.

**Modifiche solo per whitekobra** (Lorenzo, 17/10: "quando le modifiche
riguardano solo l'account whitekobra non sono necessarie notifiche su
Telegram"): il commit porta anche la riga `Solo-account: whitekobra`, dopo
`Aggiornamento:`. L'avviso di deploy e il riepilogo settimanale la saltano, e
un deploy fatto solo di modifiche cosi' non manda niente. Senza la riga, la
modifica viene annunciata a tutti.
