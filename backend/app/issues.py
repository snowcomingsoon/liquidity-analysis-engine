"""
Segnalazioni dei problemi, scritte dall'app.

Chi scrive cosa è separato di proposito, come per i file nel repo:

  * Le SEGNALAZIONI le scrivete voi dall'interfaccia. Vivono nel volume Fly, in
    `data/issues.json`, e sopravvivono ai deploy.
  * Le RISOLUZIONI le scrive Claude, in `app/data/resolutions.json`, che è
    versionato in git e viaggia con il deploy.

Nessuno dei due lati può quindi sovrascrivere l'altro, e ogni risoluzione porta
con sé la storia del commit che l'ha introdotta invece di un campo "data" che
qualcuno deve ricordarsi di compilare.

L'unione avviene in lettura, agganciando la risoluzione all'id della
segnalazione: gli id sono generati dal server e restano stabili, quindi il
riferimento regge anche se l'elenco viene riordinato o filtrato.
"""

from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Literal
from app.atomic_write import write_text_atomic

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_DATA_DIR.mkdir(parents=True, exist_ok=True)
_STORE_FILE = _DATA_DIR / "issues.json"
# Le risposte seguono la stessa divisione delle segnalazioni: quelle scritte
# dall'app vivono sul volume e appartengono a chi le scrive, quelle di Claude
# arrivano col deploy. Un botta e risposta in cui una parte puo' riscrivere le
# parole dell'altra non e' una conversazione.
_REPLIES_FILE = _DATA_DIR / "issue_replies.json"
# Quali voci della lista iniziale sono gia' state inserite. Serve a distinguere
# "mai inserita" da "inserita e poi cancellata": senza questo file l'unico modo
# per non resuscitare una voce cancellata era non inserirne mai di nuove.
_SEEDED_FILE = _DATA_DIR / "seeded_ids.json"

# Versionato in git e distribuito col deploy: è il lato di Claude.
_RESOLUTIONS_FILE = Path(__file__).resolve().parent / "data" / "resolutions.json"
_CLAUDE_REPLIES_FILE = Path(__file__).resolve().parent / "data" / "replies.json"

_MAX_ISSUES = 500

Status = Literal["aperto", "in corso", "risolto", "scartato"]
Priority = Literal["alta", "media", "bassa"]

_VALID_STATUS = {"aperto", "in corso", "risolto", "scartato", "riaperto"}
_VALID_PRIORITY = {"alta", "media", "bassa"}

_issues: list[dict] = []
_seeded_ids: set[str] = set()
_replies: list[dict] = []


def _load() -> None:
    if not _STORE_FILE.exists():
        return
    try:
        raw = json.loads(_STORE_FILE.read_text(encoding="utf-8"))
        if isinstance(raw, list):
            _issues.clear()
            _issues.extend(raw)
    except (json.JSONDecodeError, OSError):
        pass


def _save() -> None:
    try:
        write_text_atomic(_STORE_FILE, json.dumps(_issues, ensure_ascii=False), encoding="utf-8")
    except OSError:
        pass


def _load_replies() -> None:
    if not _REPLIES_FILE.exists():
        return
    try:
        raw = json.loads(_REPLIES_FILE.read_text(encoding="utf-8"))
        if isinstance(raw, list):
            _replies.clear()
            _replies.extend(x for x in raw if isinstance(x, dict))
    except (json.JSONDecodeError, OSError):
        pass


def _save_replies() -> None:
    try:
        write_text_atomic(_REPLIES_FILE, json.dumps(_replies, ensure_ascii=False), encoding="utf-8")
    except OSError:
        pass


def _claude_replies() -> dict[str, list[dict]]:
    """Le risposte di Claude, rilette a ogni richiesta come le risoluzioni."""
    try:
        raw = json.loads(_CLAUDE_REPLIES_FILE.read_text(encoding="utf-8"))
        return raw if isinstance(raw, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def add_reply(issue_id: str, text: str, author: str = "", reopen: bool = False) -> dict:
    """Una risposta a una segnalazione, con la possibilita' di riaprirla.

    Riaprire serve perche' "risolto" lo decide chi ha scritto la segnalazione,
    non chi ha scritto la correzione: se il problema si vede ancora, la voce
    deve tornare in cima all'elenco invece di restare chiusa per decreto.
    """
    text = (text or "").strip()
    if not text:
        raise ValueError("Risposta vuota")
    entry = {
        "id": uuid.uuid4().hex[:8],
        "issue_id": issue_id,
        "text": text[:4000],
        "author": (author or "").strip()[:120],
        "created_at": int(time.time()),
        "reopen": bool(reopen),
    }
    _replies.append(entry)
    _save_replies()
    if reopen:
        for it in _issues:
            if it["id"] == issue_id:
                it["reopened_at"] = entry["created_at"]
                _save()
                break
    return entry


def _load_seeded() -> None:
    if not _SEEDED_FILE.exists():
        return
    try:
        raw = json.loads(_SEEDED_FILE.read_text(encoding="utf-8"))
        if isinstance(raw, list):
            _seeded_ids.update(str(x) for x in raw)
    except (json.JSONDecodeError, OSError):
        pass


def _save_seeded() -> None:
    try:
        write_text_atomic(_SEEDED_FILE, json.dumps(sorted(_seeded_ids)), encoding="utf-8")
    except OSError:
        pass


def _resolutions() -> dict[str, dict]:
    """Le risoluzioni scritte da Claude, lette a ogni richiesta.

    Rilette ogni volta anziché memorizzate all'avvio: il file arriva col deploy,
    e un processo che sopravvive a più deploy servirebbe altrimenti le
    risoluzioni della versione con cui è partito.
    """
    try:
        raw = json.loads(_RESOLUTIONS_FILE.read_text(encoding="utf-8"))
        return raw if isinstance(raw, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


_SEED = [
    ("seed-0366", "Le funzioni di DeepSeek delle gemme rifatte con Groq e Gemini",
     "Lorenzo, 20/10: 'le opzioni che avevamo per analizzare le gemme dove era attivo DeepSeek, come ad esempio la scansione manuale o la rescansione con DeepSeek, vanno tutte risistemate e fatte fare a Grok oppure a Gemini'.",
     "media"),
    ("seed-0365", "BORLY ancora nella Top dopo il rug; scansione manuale e Top che non si aggiornano",
     "Lorenzo, 20/10: 'Borli sia rimasto nella top e tuttora figuri nella top [...] le nostre arene, la nostra top non si aggiornano bene. [...] avevo analizzato un altro token che aveva raggiunto un punteggio da classifica, ma non e' stato inserito in automatico [...] non risulta correttamente aggiornato il sito delle gemme con nuovi ingressi e nuove uscite'.",
     "alta"),
    ("seed-0364", "BORLY, la gemma col voto piu' alto, e' stato un rug pull in poche ore",
     "Lorenzo, 20/10: 'Grave problema nelle gemme, Borli, che risultava tra l'altro la gemma con il voto piu' alto, e' stato un rug pull nel giro di poche ore. Noi dobbiamo assolutamente evitare queste situazioni', poi 'Imposta i punti per tutti gli account, tranne il punto C'.",
     "alta"),
    ("seed-0363", "La libreria degli indicatori va in blocco",
     "Lorenzo, 20/10: 'La libreria degli indicatori va in blocco. Testa e risolvi il problema'.",
     "media"),
    ("seed-0362", "Cycle Bottom Index fra gli indicatori del sito classico",
     "Lorenzo, 20/10: 'Vorrei provare a inserire [...] questo Cryptic Bottom Index [...] Prova a vedere se in qualche modo riesci ad aggiungerlo tra i nostri indicatori', poi 'Mettilo solo nel sito classico per tutti, prima pero' testane il corretto funzionamento'.",
     "bassa"),
    ("seed-0361", "Podio: i primi tre della Top per punteggio",
     "Lorenzo, 20/10: 'risistema anche il podio con una regola molto semplice [...] i primi tre della top 25 [...] finiscono nel podio in alto. Chi ha il miglior valore e' primo e poi tutti gli altri'.",
     "bassa"),
    ("seed-0360", "Token truffa dai launchpad nelle gemme (un falso Apple su pump.fun)",
     "Lorenzo, 20/10: 'Stanno passando nelle gemme token che non vanno bene [...] PumpFun purtroppo ha molti token truffa [...] un token Apple che di fatto sembrerebbe quello ufficiale della Apple, ma non lo e' assolutamente', poi: 'implementerei il tuo suggerimento A completamente [...] le regole vecchie per i token dei Launchpad le applicherei tutte tranne l'eta' minima [...] come Veil'.",
     "alta"),
    ("seed-0359", "Podio con due soli token e Top che non si riempie",
     "Lorenzo, 19/10: 'il podio, che non si aggiorna sempre bene e a volte rimangono solo due token sul podio. Lo stesso vale per la sezione top [...] non riesca a riempirsi in modo diciamo corretto'.",
     "media"),
    ("seed-0358", "Scansione manuale: punteggio da arena ma il token non entra",
     "Lorenzo, 19/10: 'capire se funziona bene la scansione di un token manualmente [...] ho ricevuto un punteggio che sarebbe entrato nelle arene, ma poi nelle arene il token in questione non e' entrato'.",
     "media"),
    ("seed-0357", "Doppioni: PRIORS e Priors Agents con lo stesso contratto",
     "Lorenzo, 19/10: 'il problema dei doppioni [...] Priors e Priors Agents, che hanno pero' lo stesso contratto [...] Deve far fede l'indirizzo di contratto'.",
     "media"),
    ("seed-0356", "Spidey Show, una meme coin, entrato nelle gemme",
     "Lorenzo, 19/10: 'Con le ultime modifiche ho visto passare un progetto che assolutamente non deve passare. Si tratta del progetto Spidey Show, che e' entrato nelle gemme e e' una meme coin a tutti gli effetti. Bisogna capire come ha fatto a entrare, perche', e risolvere il problema'.",
     "alta"),
    ("seed-0355", "Ricerche delle gemme a 12 ore di distanza, quella del pomeriggio leggera",
     "Lorenzo, 19/10: 'Secondo te ha senso modificare gli orari delle ricerche, magari impostandoli a 12 ore di distanza? Hai consigli diversi sulle due ricerche?', poi 'Sì, procedi con 04:00 e 16:00 e la ricerca leggera'.",
     "bassa"),
    ("seed-0354", "GeckoTerminal: limiti e attese, solo con fonti gratuite",
     "Lorenzo, 19/10: 'volevo sapere se possiamo aggirare i limiti di GeckoTerminal in qualche modo, anche affidandosi ad un'altra piattaforma', poi 'Nessun piano a pagamento, solo fonti gratuite. Cerca di ottimizzare al meglio il loro utilizzo per quello che dobbiamo fare'.",
     "media"),
    ("seed-0353", "Gemme: progetti seri scartati per emissione, GitHub e sito letti male",
     "Lorenzo, 19/10: 'Vedi altre criticita' che potrebbero falsare i risultati delle gemme o escludere progetti che non lo meriterebbero?', poi 'procedi con la misura dei punti'.",
     "media"),
    ("seed-0352", "Gemme: holder che sono pool, lock o contratti contati come wallet nel limite del 40%",
     "Lorenzo, 19/10: 'in alcuni casi quelli che risultano tra i top 10 holders sono anche indirizzi dove magari c'e' il pool della liquidita' oppure l'indirizzo dove ci sono i token bloccati [...] studiare un sistema che ci puo' permettere di non scartare progetti che potrebbero rientrare in questa categoria'.",
     "media"),
    ("seed-0351", "Candele: meno limiti e attese da GeckoTerminal, e candele Ethereum proprie",
     "Lorenzo, 19/10, con ISTRUZIONI_CLAUDE_SQUID.md: 'ridurre i limiti e le attese nell'acquisizione delle candele, coordinando prima tutte le richieste GeckoTerminal e introducendo poi un provider autonomo per le pool Ethereum Uniswap V3. Usa come riferimento https://github.com/subsquid-labs/uniswapv3-squid'.",
     "media"),
    ("seed-0350", "Con DeepSeek spento la ricerca lo chiama comunque",
     "Lorenzo, 19/10, dopo il controllo della ricerca delle 3 (75 errori nei log, 52 di DeepSeek spento): 'forse ha senso anche impedire direttamente che chiamino DeepSeek che comunque e' spento e quindi non puo' rispondere, no?'.",
     "bassa"),
    ("seed-0349", "Whitekobra: gemme al massimo di un anno, fuori quelle che si spengono",
     "Lorenzo, 18/10: 'abbassare il tetto della vita di un progetto dagli attuali 1000 giorni a un anno, quindi 365 giorni massimo [...] entro i 1000 giorni ho visto tanti progetti ormai morti o semimorti', poi 'applicalo anche ai layer e per i suggerimenti applica solo il secondo'.",
     "media"),
    ("seed-0348", "Whitekobra: Pearl a 30 giorni, FDV invisibile, gemme che entrano ed escono",
     "Lorenzo, 18/10: 'devono esserci solo progetti datati max un mese' in Pearl; 'non ho visto nella sezione gemme da nessuna parte il nuovo parametro che indica i due tipi di capitalizzazione'; 'un progetto per uscire per capitalizzazione dalle gemme deve superare il tetto [...] per almeno 7 giorni consecutivi', poi 'mettili tutti tranne quello relativo al tetto d'emergenza'.",
     "media"),
    ("seed-0347", "Gemme: ricerca accesa piu' a lungo",
     "Lorenzo, 18/10: 'Con tutte le fonti attuali ha senso tenere accesa la ricerca delle gemme piu' a lungo. Comporterebbe costi maggiori?', poi 'Procedi con la sentinella, notifiche subito a qualsiasi ora'.",
     "media"),
    ("seed-0346", "Gemme: progetti nuovi intercettati tardi (Veil)",
     "Lorenzo, 18/10: 'non sono molti i progetti recenti, nuovi, che entrano tra le gemme [...] come possiamo fare per intercettare progetti come Veil prima che spicchino il volo?', poi fonti 'pump.fun [...], Meteora, Pons' e 'Procedi'.",
     "alta"),
    ("seed-0345", "Gemme senza data escluse",
     "Lorenzo, 18/10: 'se non c'e' modo di identificare la data di un layer, va rimosso. Quelli senza data non possono entrare nelle gemme. Questa e' una regola da ammettere.' (la regola dei 1000 giorni resta).",
     "media"),
    ("seed-0344", "Layer tutti con la stessa data",
     "Lorenzo, 18/10: 'I layer presenti tra le gemme hanno tutti la stessa data, ho controllato e non e' corretto. Perche' succede?'.",
     "media"),
    ("seed-0343", "Limitless Exchange: capitalizzazione $4M invece di $30M",
     "Lorenzo, 18/10: 'questa gemma Limitless Exchange ha una capitalizzazione diversa rispetto a quella reale. Nel nostro ambiente risulta 4 milioni, poco piu'. In realta' ne ha piu' di 30. Perche'?', poi 'Applica 1 piu' 3' (mostrare la FDV ed escludere le gemme con FDV oltre 5 volte la cap).",
     "media"),
    ("seed-0342", "Poche gemme su Ethereum e Base: fonte di token nuovi",
     "Lorenzo, 17/10: 'tra le gemme vedo pochissime gemme della chain Ethereum e pochissime gemme della chain base', poi 'aggiungi la fonte di token nuovi per Ethereum e Base su tutti gli account'.",
     "media"),
    ("seed-0341", "Whitekobra: nuovi pesi del voto delle gemme",
     "Lorenzo, 17/10: togliere la partecipazione, prodotto 35%, uso 25% con dentro la crescita degli holder, token 20%, DeepSeek 20%, penalita' GitHub 5 punti: 'Procedi con la crescita nell'uso e quindi poi ridisegna completamente tutti i nuovi parametri delle gemme solo per l'account whitekobra'.",
     "alta"),
    ("seed-0340", "Whitekobra: data di listing per le gemme senza data di creazione",
     "Lorenzo, 17/10: 'vorrei capire se e' possibile utilizzare come data di creazione delle gemme che attualmente non hanno data la data di listing sull'exchange in cui viene analizzata', poi 'Si [...] mettile online'.",
     "media"),
    ("seed-0339", "Whitekobra: layer fra $300k e $30M",
     "Lorenzo, 17/10: 'per quanto riguarda le soglie di capitalizzazione vanno tutte bene, tranne quella dei layer che rimodulerei da 300k a 30M'.",
     "media"),
    ("seed-0338", "Whitekobra: gemme senza doppioni, vecchie o sotto 60; Pearl sempre notificata; ordinamento; arene a 3",
     "Lorenzo, 17/10: 'esiste uno Sherwood Protocol che ha due presenze [...] Tutti i casi doppi vanno eliminati [...] quelli vecchi con oltre 1000 giorni dalla creazione non vanno inseriti [...] non considerare tutti i progetti che non raggiungono un punteggio di almeno 60 [...] gli ingressi in Pearl devono essere notificati sempre [...] ordinamento per capitalizzazione e per quanto una gemma e' recente [...] per ogni narrativa far vedere massimo a vista scoperta le prime 3'.",
     "alta"),
    ("seed-0337", "Avviso di deploy: le modifiche solo per whitekobra solo nella sua chat",
     "Lorenzo, 17/10: 'Quando effettui modifiche solo per l'account whitekobra invia la notifica del repository solamente alla chat dell'account whitekobra'.",
     "media"),
    ("seed-0336", "Whitekobra: niente limiti sugli avvisi Telegram, gemme solo se nuove",
     "Lorenzo, 17/10: 'Solo per account whitekobra: Rimuovi tutti i limiti per tutte le chat Telegram e utilizza lo stratagemma di qualche secondo di pausa per l'invio [...] solo quando una gemma non presente nelle classifiche, qualsiasi sia, allora scatta la notifica'.",
     "media"),
    ("seed-0335", "Chat gemme: nessun avviso dopo la ricerca delle 18",
     "Lorenzo, 17/10: 'La ricerca delle gemme delle ore 18 e' finita e ho visto i risultati nella chat del repository, pero' non mi sono arrivate le notifiche delle nuove gemme nelle arene [...] la chat dedicata alle gemme continua a non funzionare'.",
     "alta"),
    ("seed-0334", "App on-chain: modalita' dark",
     "Lorenzo, 17/10: 'visto che ci sei aggiungi anche modalita' dark'.",
     "media"),
    ("seed-0333", "Punteggi diversi fra arene e pagina del token",
     "Lorenzo, 17/10: 'I punteggi delle gemme continuano a risultare diversi tra le classifiche per narrative e il rank sotto il grafico una volta cliccato sulla gemma. Perche'?'. Poi: 'Per ora falla solo per whitekobra'.",
     "alta"),
    ("seed-0332", "App on-chain: pagina bianca ricaricando",
     "Trovato da Claude il 16/10 e chiuso il 17/10 su richiesta di Lorenzo ('Risolvi il punto 2'): ricaricando l'app on-chain compariva 'Failed to resolve module specifier @onchain/nozoom.js' e l'app non partiva.",
     "alta"),
    ("seed-0331", "Grafico vuoto: 'Unknown strategy' e email tagliata in More",
     "Lorenzo, 17/10 (web app da iPhone): 'Unknown strategy: Check the ticker...' nel grafico senza aver cercato nulla, 'non vedo il ticker', 'non si vede email loggato'.",
     "alta"),
    ("seed-0330", "Seconda ricerca delle gemme alle 18",
     "Lorenzo, 17/10: 'aggiungi per tutti gli account una nuova ricerca alle ore 18. Quindi non ci sara' piu' solo la ricerca delle 3 la notte, ma anche quella delle ore 18. Due ricerche al giorno'.",
     "media"),
    ("seed-0329", "Telegram: alert anche per le gemme che entrano in Pearl",
     "Lorenzo, 17/10: 'aggiungi l'alert nella chat delle gemme anche per quelle che eventualmente entrano nella sezione Pearl'.",
     "media"),
    ("seed-0328", "Telegram: nessun messaggio nella chat delle gemme",
     "Lorenzo, 17/10: 'continuano a non arrivare i messaggi delle nuove gemme. Anche stanotte, dopo la ricerca delle tre, non sono arrivati messaggi su nuove gemme nella chat dedicata'.",
     "alta"),
    ("seed-0327", "Whitekobra: di nuovo la grafica nuova delle gemme e la sezione Pearl",
     "Lorenzo, 17/10: 'io voglio le modifiche che avevamo fatto in questa chat nelle ore precedenti per quanto riguarda le modifiche grafiche e la sezione Pearl. Riprendi tutto da li' e applicalo all'account White Cobra, solo all'account White Cobra'.",
     "media"),
    ("seed-0326", "App on-chain: grafica per account, funzionamento per tutti",
     "Lorenzo, 17/10: 'Lascia intatte le modifiche grafiche negli altri account e applicale solo su White Cobra. Per quanto riguarda [...] le modifiche di funzionamento, quelle applicale invece a tutti gli account', poi 'tutto cio' che riguarda la sezione del sito va bene per tutti gli account sempre, mentre per quanto riguarda le gemme e la sezione Discover [...] devi sempre fare la richiesta'.",
     "media"),
    ("seed-0325", "App on-chain: due versioni, quella di ieri per Lorenzo",
     "Lorenzo, 16/10: 'ripristina l'app come era prima per il mio utente [...] mentre per white kobra applica queste cose' (scelta: prima di oggi).",
     "media"),
    ("seed-0324", "Gemme: torna il mosaico delle arene",
     "Lorenzo, 16/10: 'rivoglio il mosaico sulle gems'.",
     "media"),
    ("seed-0323", "Sezione Pearl eliminata",
     "Lorenzo, 16/10: 'togli il minimo di 70 per essere nelle gemme early perche' cosi' e' vuota la classifica', poi 'cosa e' la sezione pearl?' e 'eliminala'.",
     "media"),
    ("seed-0322", "Revisione dell'app on-chain: correzioni e miglioramenti",
     "Lorenzo, 16/10: 'Ricontrolla tutta le sezioni dello Sniper e dimmi se c'e' qualcosa che non va. Se hai suggerimenti [...] dimmelo', poi 'Risolvi tutto e implementa i suggerimenti tranne Riepilogo della ricerca notturna'.",
     "media"),
    ("seed-0321", "Gemme: il podio in alto non segue l'ordine della Top 25",
     "Lorenzo, 16/10: 'il podio in alto (top 3) dovrebbe rispecchiare anche l'ordine dei primi 3 posti nella Top25 ma non e' cosi'. Analizza e risolvi'.",
     "media"),
    ("seed-0320", "Grafici e MarketCap delle gemme sempre aggiornati con i dati DEX",
     "Lorenzo, 16/10: 'Assicurati inoltre che i grafici siano sempre aggiornati con i dati dex, cosi' come la MarketCap'.",
     "alta"),
    ("seed-0319", "Sezione Top: le 25 gemme migliori per punteggio; Pearl subito dopo Gems",
     "Lorenzo, 16/10: 'La sezione Pearl spostala subito dopo Gems, prima di Early. Poi crea anche una sezione Top (da inserire prima di Scout) dove classificare le migliori 25 gemme per punteggio rank'.",
     "media"),
    ("seed-0318", "Nuova sezione Pearl: le gemme di Early con punteggio da 70 in su",
     "Lorenzo, 16/10: 'Crea una nuova sezione Pearl in cui inserire le gemme selezionate su Early che pero' hanno ottenuto un punteggio pari o superiore a 70'.",
     "media"),
    ("seed-0317", "Gemme: punteggio diverso fra arena e pagina del token (VEIL 89 / 73)",
     "Lorenzo, 16/10: 'Veil, che ha un punteggio di 89 nella classifica della narrativa della privacy, ma [...] cliccando sul token [...] il rank e' diverso, da un punteggio di 73. Bisogna capire come mai c'e' questa discrepanza e modificarla'.",
     "alta"),
    ("seed-0316", "Gemme: primi tre fissi in alto, arene elencate aperte, grafico solo al clic",
     "Lorenzo, 16/10, con screenshot: 'lo spazio dove andare a inserire gli attuali primi tre posti delle gemme, sempre in alto, in cima, fissi [...] in Arenas le sezioni [...] non siano chiuse ma elencate [...] a centro pagina togliendo il grafico. Il grafico si attivera' solo se l'utente clicca su una delle gemme'.",
     "media"),
    ("seed-0315", "Telegram: la chat delle gemme non riceve niente",
     "Lorenzo, 16/10: 'questa terza, dedicata alle nuove gemme trovate dalla ricerca, non mi arrivano le notifiche [...] e' come se fosse ferma', poi 'non e' impostata come chat principale, in quanto la chat principale e' quella degli alert'.",
     "media"),
    ("seed-0314", "Ricerca dei pair: risultati tagliati in alto e fuori schermo nel Lab",
     "Lorenzo, 16/10, con due screenshot: 'i pair scompaiono, cioe' non appaiono tutti nella loro interezza, ma vengono troncati [...] nella sezione Lab [...] appaiono tutti sulla destra e non sono visualizzabili [...] vanno visti tutti nella loro interezza'.",
     "media"),
    ("seed-0313", "Togliere dal codice le due strategie di prova (RSI+BB 4H, RSI+BB BTC band)",
     "Lorenzo, 16/10, dopo averle tolte dal Lab: 'Alleggerisci'.",
     "bassa"),
    ("seed-0312", "Lab: via RSI+BB 4H e RSI+BB BTC band, strategie raggruppate per tipo, niente stella",
     "Lorenzo, 16/10: 'Rimuovi la RSI piu' BB Reversal BTC Band e la RSI piu' BB 4 ore, perche' sono strategie che non utilizziamo [...] erano delle prove [...] la trend EMA Reversal deve andare incolonnata insieme alla RSI piu' BB Reversal, mentre la trend EMA che e' long short deve andare insieme alla RSI piu' BB long short [...] e rimuovi la stellina accanto a trend ema reversal'.",
     "media"),
    ("seed-0311", "Barra in alto del sito troppo affollata",
     "Lorenzo, 16/10: 'La sezione superiore del sito e' troppo affollata. Ottimizza lo spazio senza togliere niente'.",
     "media"),
    ("seed-0310", "Repository pubblico: nessun dato personale, chiave o IP nei file",
     "Lorenzo, 16/10: 'rimuovere completamente ogni riferimento alle nostre email o qualsiasi altro dato personale o qualsiasi chiave, API [...] ovviamente preservando il funzionamento di tutto'.",
     "alta"),
    ("seed-0309", "Repository pubblico: togliere dai file gli indirizzi email",
     "Lorenzo, 16/10: 'come si puo' cercare di modificare il fatto che siano visibili gli indirizzi email, i due indirizzi email, si possono in qualche modo oscurare'.",
     "media"),
    ("seed-0308", "Menu strategie ordinato, con descrizione, consigliate e impostazioni consigliate; stato di BTC nella barra in alto",
     "Lorenzo, 16/10: 'Secondo la tua analisi cos'altro possiamo fare per migliorare il sito?', poi 'procedi con tutti e 5 i punti'.",
     "media"),
    ("seed-0307", "Lab: niente tasto Optimize sulle strategie che non si ottimizzano",
     "Lorenzo, 16/10: 'per quanto riguarda le strategie sul sito, solo quelle dove non si puo' utilizzare l'ottimizzazione, forse sarebbe necessario eliminare direttamente il pulsante'.",
     "bassa"),
    ("seed-0306", "Nuova strategia RSI+BB Reversal (BTC band): piu' trade, positiva anche nel 2021 e nel 2022",
     "Lorenzo, 16/10: 'le strategie RSI piu' BB [...] riescono a fare troppi pochi trade [...] aggiungerei pero' dei parametri che possano permettere di aumentare il numero di trade', 'basta solo uno dei due parametri (RSI o BB)', poi la Bull Market Band e l'uscita alla banda centrale, infine 'Si, aggiungila al sito'.",
     "media"),
    ("seed-0305", "Lingue del sito: inglese di base, italiano dalla tendina in alto",
     "Lorenzo, 16/10: 'Attualmente e' impostato tutto in inglese e va bene, deve essere la modalita' standard. Pero' ci deve essere anche la possibilita' di selezionare nella barra in alto sul sito una tendina che ti permette di cambiare lingua [...] solo l'italiano [...] con la possibilita' poi di aggiungere anche altre lingue successivamente'.",
     "media"),
    ("seed-0304", "Strategia combinata Trend EMA Reversal + RSI+BB reversal",
     "Lorenzo, 16/10: 'inglobare i segnali di entrambe le strategie in un'unica strategia [...] una strategia sola, che pero' ha piu' segnali di ingresso e piu' segnali di uscita', poi 'aggiungi anche la combinata, potrebbe essere utile comunque per fare anche ulteriori confronti'.",
     "media"),
    ("seed-0303", "Lab: final equity semplice, Max return raccomandata per le RSI+BB, conferma prima di cancellare dall'archivio",
     "Lorenzo, 15/10: 'aggiungere un altro final equity [...] anche quello del rendimento semplice', 'per quanto riguarda solo le strategie RSI piu' BB, il max return come ricerca ottimizzata raccomandata', 'nella sezione dell'archivio strategie [...] chiedere sempre conferma alla richiesta di cancellazione'.",
     "media"),
    ("seed-0302", "Lista dei trade: profitto e perdita di ogni trade anche col rendimento semplice",
     "Lorenzo, 15/10: 'In questa lista andrebbero aggiunti anche altri dettagli [...] quelli del profitto e della perdita di ogni trade con il rendimento semplice [...] date piu' brevi e mettendo massimo due decimali dopo la virgola dei prezzi di ingresso e di uscita'.",
     "media"),
    ("seed-0301", "Stessa posizione per tutte le strategie, anche senza impostazioni salvate",
     "Lorenzo, 15/10: 'Tutte le strategie presenti sul sito hanno lo stesso tipo di posizione, cioe' aprono con lo stesso tipo di capitale iniziale e la stessa percentuale poi di equity trade', poi 'Si' all'allineamento dei valori di riserva.",
     "media"),
    ("seed-0300", "Rendimento semplice accanto al composto, e Max return che sceglie sul semplice",
     "Lorenzo, 15/10: 'il risultato percentuale puro di ogni trade [...] e poi sommate [...] nelle strategie reversal e' probabile che una volta uscito potrei anche non reinvestire tutto', poi 'Max Return deve scegliere il migliore in base al rendimento semplice e [...] metti in evidenza sia nel drawdown che nel profitto entrambi i risultati semplice e composto con la stessa visibilita''.",
     "alta"),
    ("seed-0299", "Strategia Trend EMA in versione reversal (solo long)",
     "Lorenzo, 15/10: 'Aggiungi alle strategie anche la versione reversal del trend EMA in modo che io la possa confrontare con la RSI piu' BB reversal [...] uguale alla trend EMA per quanto riguarda i valori, ma non andare short. Invece di aprire lo short deve uscire dalla posizione e chiudere il long'.",
     "media"),
    ("seed-0298", "KuCoin: 'timeframe 1M not supported' con 1d selezionato",
     "Lorenzo, 15/10: 'quando lo seleziono mi dice time frame 1 month not supported on KuCoin. Pero' era selezionato 1d non 1M'.",
     "alta"),
    ("seed-0297", "KuCoin: le coppie non compaiono fra quelle disponibili",
     "Lorenzo, 15/10: 'nei pair a disposizione sul sito, quelli relativi a KuCoin non compaiono. Dovresti verificare il motivo, se e' legato a delle API di KuCoin oppure se e' un problema nostro [...] in modo da avere a disposizione anche tutti i pair presenti su KuCoin'.",
     "alta"),
    ("seed-0296", "Max return: range RSI ridotti anche su RSI+BB reversal e Gabriele 2",
     "Lorenzo, 15/10: 'Imposta la riduzione del range delle RSI che abbiamo adottato nella strategia 4H anche alle altre due strategie sul sito'.",
     "media"),
    ("seed-0295", "Archivio: l'esito del test su un altro pair non si puo' ne' salvare ne' togliere",
     "Lorenzo, 15/10: 'Una volta terminato il test su un altro pair dall'archivio strategie e' necessario inserire un tasto per decidere se salvare o eliminare l'esito del test. Al momento resta visibile ed e' impossibile da rimuovere'.",
     "media"),
    ("seed-0294", "Archivio: provare una strategia salvata su un altro pair",
     "Lorenzo, 15/10: 'applicare all'archivio strategie un pulsante in cui si puo' testare la strategia salvata su un altro asset [...] con gli stessi valori. A quel punto la strategia sarebbe testata su candele mai viste'.",
     "media"),
    ("seed-0293", "Max return 4H: confronto storico / ultimi 12 mesi poco chiaro",
     "Lorenzo, 15/10: 'La discrepanza tra il risultato ottimizzato sugli anni escluso l'ultimo e il test sulle candele mai viste e' molto netta [...] vorrei conferma che correttamente viene applicata quella strategia con quei valori', poi 'inserisci anche piu' dettagli possibili nella schermata finale'.",
     "media"),
    ("seed-0292", "Max return 4H: range RSI piu' stretti e almeno 3 trade per anno",
     "Lorenzo, 15/10: 'ridurrei i range RSI: solo da 20 a 40 e da 65 a 85 [...] un minimo piu' alto di trade per anno: almeno tre invece di uno', poi 'Procedi con B' (media di 3 per anno, nessun anno vuoto).",
     "media"),
    ("seed-0291", "Max return 4H: lasciare libero l'ultimo anno per testare su candele mai viste",
     "Lorenzo, 15/10: 'vorrei lasciare sempre l'ultimo anno libero da backtest, in modo da poterci testare la strategia su candele mai viste. Quindi il primo backtest dovrebbe essere fatto escludendo gli ultimi 12 mesi [...] per ora alla sola strategia RSI+BB 4H'.",
     "alta"),
    ("seed-0290", "Max return 4H: lento, e la verifica sull'ultimo anno usa valori diversi da quelli mostrati",
     "Lorenzo, 15/10: 'il test finale sull'anno scoperto lo fa con una strategia dai valori diversi [...] Cosi' non ha senso, deve farlo applicando i valori della strategia piu' solida'; e su velocita': 'Ok, procedi' (due passate + calcolo piu' leggero).",
     "alta"),
    ("seed-0289", "Backtest e ottimizzazione a 4H vanno indietro solo ~2 anni",
     "Lorenzo, 14/10: 'Abbiamo un problema con la strategia RSI+BB 4H: non avevamo tenuto conto del limite che abbiamo con le candele. Non riusciamo ad andare indietro nel grafico a sufficienza'. Era il nostro tetto di 5000 candele, non le API; scelta sua: 20000.",
     "alta"),
    ("seed-0288", "Ricerca gemme: un solo giro lungo alle 3 di notte",
     "Lorenzo, 14/10 (a voce): 'La ricerca delle gemme falla solo di notte', 'farne una bella bella grossa', 'si' alle tre va bene'.",
     "media"),
    ("seed-0283", "All'apertura a destra compare Structure invece della Watchlist",
     "Lorenzo, 14/10: 'All'apertura del sito sulla colonna a destra accanto al grafico principale appare la sezione Structure. Invece deve apparire subito la Watchlist.'",
     "media"),
    ("seed-0282", "Archivio: le strategie con valori scritti a mano vengono salvate con i default",
     "Lorenzo, 13/10: 'le strategie testate con valori scritti a mano non vengono esportate in archivio strategie con i valori giusti, ma vengono salvate con i valori di default. Bisogna correggere e ritestare'.",
     "alta"),
    ("seed-0287", "Ricerca dei progetti costante, senza token Claude e senza DeepSeek",
     "Lorenzo, 10/10: 'facciamo ripartire la ricerca bella costante ma basta che non si usi token o altro' e poi 'e neanche deepseek'.",
     "alta"),
    ("seed-0286", "Max return RSI+BB 4H: verifica sull'ultimo anno",
     "Lorenzo, 14/10: 'scegliere sui dati fino all'anno scorso e vedere come va nell'ultimo anno, che la ricerca non ha visto [...] Questa e' una buona idea, puoi implementarla da subito. Solo sulla strategia 4H'.",
     "media"),
    ("seed-0285", "Max return RSI+BB 4H: cercare anche il moltiplicatore e dare il risultato piu' solido e il piu' profittevole",
     "Lorenzo, 14/10: 'rendere ottimizzabile anche il parametro Bollinger Moltiplicatore con un range da 2.0 a 2.8 [...] e combinarli con i range stabiliti per ipercomprato e ipervenduto', poi 'due tipi di risultati: il piu' solido in rapporto al profitto e il piu' profittevole anche con una minore solidita', ma non deve essere una solidita' completamente azzerata'.",
     "alta"),
    ("seed-0284", "Max return molto lento con il riempimento dentro la candela",
     "Lorenzo, 14/10 alle 00:20: 'L'ottimizzazione sta procedendo molto lentamente, che succede?'",
     "alta"),
    ("seed-0281", "Nuova strategia RSI+BB 4H (moltiplicatore Bollinger 2.5)",
     "Lorenzo, 13/10: 'Aggiungi una nuova strategia e chiamala RSI+BB 4H. Deve funzionare esattamente come le altre due RSI+BB, l'unica differenza deve essere il Bollinger Multiplier settato di default a 2.5 anziche' 2.0 in modo da essere piu' adatto al timeframe 4H.' Base scelta: la RSI+BB solo long.",
     "media"),
    ("seed-0280", "Ottimizzazione lenta durante la ricerca gemme",
     "Lorenzo, 13/10 alle 22:12: 'L'ottimizzazione in questo momento sta andando molto lenta. Dipende da qualcosa?' — era in corso la ricerca gemme delle 22:00, sullo stesso server e processo. Soluzione scelta da Lorenzo: la ricerca si mette in pausa mentre gira un'ottimizzazione.",
     "alta"),
    ("seed-0279", "Archivio strategie: compaiono voci 'from alert' salvate da sole",
     "Lorenzo, 13/10: 'Nell'archivio strategie ne compaiono alcune con la dicitura from alert. Dobbiamo capire perche' succede e risolvere, visto che abbiamo deciso di impostare il sistema in modo che nessuna strategia venga salvata automaticamente in archivio con nessun tipo di backtest'.",
     "media"),
    ("seed-0278", "Sezione backtest non funziona da app, solo da browser",
     "Lorenzo, 13/10: 'La sezione backtest non funziona da app, solo da browser. Bisogna capire perche' e risolvere'.",
     "alta"),
    ("seed-0277", "Max return: almeno un trade in ogni anno solare e i due migliori risultati",
     "Lorenzo, 13/10: 'inserire un filtro nella scansione che elimini tutti i risultati finali che non ottengono almeno un trade per anno solare testato [...] dal 2022 al 2026 deve aver ottenuto almeno un trade valido in ognuno di questi diversi anni [...] c'e' bisogno di ottenere un backtest con continuita' e affidabilita' temporale. Infine [...] avere come esito finale i due migliori risultati anziche' uno solo'.",
     "alta"),
    ("seed-0276", "Ottimizzazioni salvate da sole nell'archivio strategie",
     "Lorenzo, 13/10: 'Annulla il salvataggio automatico delle strategie ottimizzate in archivio. Se interessano vengono salvate manualmente, altrimenti si affolla l'archivio strategie inutilmente'.",
     "media"),
    ("seed-0275", "Alert: conferma prima di cancellare e livelli RSI visibili per RSI+BB",
     "Lorenzo, 13/10: 'Nella sezione degli alert inserisci sempre la richiesta di conferma quando si preme sul tasto x per cancellare un alert attivo [...] Inoltre, solo per le strategie RSI+BB, tra i dati visibili di ogni strategia negli alert aggiungi anche la visualizzazione dei valori di riferimento per ipercomprato e ipervenduto'.",
     "media"),
    ("seed-0274", "Ricerca gemme: 'fallita 3 volte' e selezione poco popolata",
     "Lorenzo, 12/10: 'Ricerca delle 22:00 interrotta: e' fallita 3 volte, riprova alle 11:35. Vedi i log del server., poi non e' molto popolata la nostra selezione, aggiungi controllo ogni ora'.",
     "alta"),
    ("seed-0273", "Chat Telegram degli alert: arrivano anche ottimizzazioni e gemme",
     "Lorenzo, 12/10: 'Nella chat Telegram alert strategie (Chat ID: -5359869020) attualmente mi arrivano anche le notifiche dell'ottimizzazione conclusa e delle nuove gemme in classifica. Io in questa chat voglio ricevere solo segnali di trading quando si attivano le strategie.'",
     "alta"),
    ("seed-0272", "Ottimizzazione RSI+BB: modalita' che cerca solo il rendimento massimo su tutto il grafico",
     "Lorenzo, 12/10: 'aggiungi una modalita' che cerca solo il rendimento massimo su tutto il grafico [...] per l'ipervenduto solo da 10 a 40, per l'ipercomprato solo da 60 a 90 [...] andando di uno in uno [...] incrociando fra loro tutti i risultati possibili [...] selezionando la performance migliore con un drawdown massimo consentito del 60%'.",
     "alta"),
    ("seed-0271", "Indicatori sotto il grafico sfalsati rispetto al prezzo",
     "Lorenzo, 12/10, con screenshot: 'indicatori sotto sfalsati rispetto a prezzo'. Il minimo del prezzo cadeva circa 40 px prima del minimo dello stocastico.",
     "alta"),
    ("seed-0270", "Misura del prezzo: niente rettangolo, deve proiettare i punti che legge",
     "Lorenzo, 12/10: 'la funzione di misurare prezzo non deve figurare un rettangolo ma proiettare i punti che legge in modo intelligente'.",
     "media"),
    ("seed-0269", "Strumenti di disegno: spariscono o scattano",
     "Lorenzo, 12/10: 'i tool di disegno non funzionano bene spesso scompaiono o sono scattosi, devi analizzare nel dettaglio ogni funzione di disegno e creare un piano per renderli perfetti', poi 'voglio dei canvas moderni, colori etc' e 'procedi e falle tutte, e verifica ogni cosa'.",
     "alta"),
    ("seed-0268", "Sito classico lento: un backtest blocca il sito per tutti",
     "Lorenzo, 12/10: 'crea un prompt e un piano di miglioramento di prestazioni per il sito classico [...] voglio un overhaul completo', poi 'attua tutto'. "
     "Trovato leggendo il codice: grafico e backtest calcolati sul processo che risponde a tutti, motore riga per riga, refresh completo ogni 60 s, editor Pine caricato sempre.",
     "alta"),
    ("seed-0267", "Sito classico: sui pair presenti solo sui DEX il backtest non da' risultati",
     "Lorenzo, 12/10: 'sui pair presenti solo nei dex il backtest non fornisce risultati. C'e' un motivo specifico legato alle API dei Dex?' "
     "Poi: 'sul sito classico l'anti-rug non e' necessario, serve solo per lo Sniper. Il sito classico deve avere sempre la priorita' di eseguire backtest sull'intero grafico disponibile'.",
     "alta"),
    ("seed-0266", "Ricontrollo completo degli indicatori sui grafici: calcoli e qualita' visiva",
     "Lorenzo, 10/10: 'rianalizza tutte le rappresentazioni grafiche che abbiamo fatto con i nostri indicatori e verifica che siano corrette, che siano affidabili e visualizzate in modo corretto su standard elevati [...] alcuni mi risultano un po' schifo'.",
     "alta"),
    ("seed-0265", "Sito classico: il nome di un token DEX e' troppo lungo nella barra sotto il grafico",
     "Lorenzo, 10/10, da telefono con DREGG: 'ticker troppo lungo nella barra una volta caricato'. "
     "Sotto il grafico e nella ricerca compariva tutto 'DREGG@solana:2XHrhkx...', che usciva dallo schermo.",
     "media"),
    ("seed-0264", "I task lunghi lanciati dall'app si perdono se cambio finestra o chiudo l'app; manca una notifica a fine lavoro",
     "Lorenzo, 01/10: 'qualsiasi task, qualsiasi attivita' lanciata da mobile o da desktop deve continuare in background se io cambio finestra o butto giu' l'applicazione sul telefono e arrivarmi una notifica al completamento dell'attivita' che mi riporta esattamente al punto in cui l'ho lasciata se ci clicco sulla notifica'.",
     "alta"),
    ("seed-0263", "Il motore non studia tutti i progetti del database: ne mancano tanti",
     "Lorenzo, 07/10: 'mi sembra che il motore del sito non stia studiando tutti quelli presenti nel database..ce ne mancano tanti ancora'. Schermata: 19.122 noti, 6.779 nella fascia $10k-$3M, 3.698 studiati, 2.514 scartati.",
     "alta"),
    ("seed-0262", "Forzare subito un giro della ricerca delle gemme, senza aspettare le 11:35 o le 22:00",
     "Lorenzo, 08/10: 'forza il giro ora', per studiare i progetti appena inseriti (lista Robinhood e Compute).",
     "media"),
    ("seed-0261", "Un progetto entrato tra i migliori di un'arena deve restarci almeno 2-3 giorni, anche se superato",
     "Lorenzo, 08/10: 'se una crypto e' comparsa tra le migliori, anche se poi viene surclassata; deve rimanerci per almeno 2-3 gg prima di essere espulsa'.",
     "media"),
    ("seed-0260", "Un secondo giro della ricerca delle gemme alle 11:35, oltre a quello delle 22:00",
     "Lorenzo, 08/10: 'aggiungi un check oltre che alle 22, anche alle 11.35'.",
     "media"),
    ("seed-0259", "Narrativa Compute (GPU, render, cloud decentralizzato) e gemme in questa narrativa",
     "Lorenzo, 08/10: 'mi interessa molto compute power tipo render token, akash network, voglio anche questa narrativa e concentriamoci su scovare gemme anche su questo'.",
     "media"),
    ("seed-0258", "Ricontrollo DeepSeek: punti ripetuti, sito JS rosso e cancellato insieme, nessuna vista di cosa sta facendo",
     "Lorenzo, 08/10, scheda AUREON tab Why: 'sistema questi errori, e quando DeepSeek fa il rescan voglio vedere cosa fa attraverso un piccolo log direttamente sul tasto di rescan [...] cosa sta navigando, eccetera, giusto per vedere a che punto e''.",
     "media"),
    ("seed-0257", "Aggiungere la rete Arc tra le chain delle gemme",
     "Lorenzo, 07/10: 'aggiungi supporto a rete ARC'.",
     "media"),
    ("seed-0256", "I grafici non hanno i colori e il font del tema dell'app",
     "Lorenzo, 07/10: 'il tema dei grafici deve essere allineato ai colori del sito e al tema utilizzato nell'app in ogni aspetto'.",
     "media"),
    ("seed-0255", "La Top 50 come concetto e' limitante: serve una classifica meritocratica che tenga conto delle narrative",
     "Lorenzo, 07/10: 'secondo me la top50 come concetto e' limitante, serve un sistema meritocratico e innovativo per visualizzare i top [...] una classifica fatta in modo meno tradizionale data la complessita' dei progetti e le diverse narrative'. Tre proposte (Arene, Mappa, Scala), scelta: 'procedi come consigliato'.",
     "media"),
    ("seed-0254", "La lista Early non si trova; la schermata Record non si capisce a cosa serva",
     "Lorenzo, 07/10: 'la sezione EARLY non la trovo pero', la metterei al posto di questa schermata che non capisco neanche a cosa serva'.",
     "media"),
    ("seed-0253", "Errore 500 sulla pagina di un token layer (AttributeError: 'list' object has no attribute 'get')",
     "Avviso Telegram del 07/10: 'Errore 500 su GET /api/onchain/token, AttributeError: 'list' object has no attribute 'get''.",
     "alta"),
    ("seed-0252", "La ricerca delle gemme gira tutto il giorno: basta un giro solo alle 22:00",
     "Lorenzo, 07/10: 'Non mi interessa scansionare 1 miliardo di token al secondo, mi basta fare tutto in una tranche magari a fine serata, e quindi non lasciare sempre in ascolto il bot'. Scheda: 22:00 ora italiana.",
     "media"),
    ("seed-0251", "In Top 50 entrano progetti che nessuno usa (Clawville World terzo con $492 di volume)",
     "Lorenzo, 07/10: 'al terzo posto c'e' [...] Clawville World, che penso sia una merda [...] progetti che hanno un prodotto molto funzionante, che ci siano volumi, che ci sia partecipazione, e rimanendo sempre nei limiti della market cap'. Schede: cap almeno $300k (sotto: lista Early), volume 7 giorni almeno $25k/giorno e 1% della cap, 100 transazioni e 30 compratori al giorno, 500 holder non in calo, top 10 wallet sotto 40%.",
     "alta"),
    ("seed-0250", "Togliere dall'app il trading e le strategie automatiche: trend follower, pilota, Meme Sniper, swap",
     "Lorenzo, 07/10: 'non voglio piu' vedere comunque strategie automatiche non hanno senso, basta questa parte di trading deve sparire'. Nelle schede: spegnere trend follower, trading automatico e Meme Sniper, e nascondere swap e ordini limite.",
     "alta"),
    ("seed-0249", "I filtri del database sono una riga orizzontale infinita; i layer non hanno il loro tag",
     "Lorenzo, 01/10: 'i filtri nel database sono raffigurati orizzontalmente e non riesco a gestirli tutti perche' sono veramente tanti [...] devo scorrere a destra ma non finiscono mai [...] aggiornare anche L1, L0 [...] identificarli con il relativo tag'.",
     "media"),
    ("seed-0248", "Tasto microfono nell'app: parlare e farsi rispondere da DeepSeek su qualsiasi cosa del sito",
     "Lorenzo, 01/10: 'possiamo aggiungere il tasto di registrare un audio per parlare o meglio trascrivere l'audio mentre lo [dico], lo invio e poi [il testo] arriva direttamente a DeepSeek che mi risponde [...] deve avere accesso a tutto [...] mi possa rispondere su qualsiasi cosa'.",
     "media"),
    ("seed-0247", "Trovare layer 0, layer 1 e layer 2 con chain propria: lo scanner cerca solo contratti",
     "Lorenzo, 01/10: 'dobbiamo scovare i layer one e i layer zero [...] col sistema attuale non li possiamo trovare perche' cerchiamo i contratti [...] anche i layer 2 con blockchain propria [...] API gratuite [...] pochi al giorno e' sufficiente [...] i risultati vanno a finire [...] database, top 50'. Fascia: 'usiamo da 500k di market cap fino a 100mln'.",
     "alta"),
    ("seed-0246", "Nella review di ogni token serve un tasto per un ricontrollo approfondito con DeepSeek",
     "Lorenzo, 01/10: 'in ogni review metti un tasto per forzare un ricontrollo approfondito dedicato con deepseek' (screenshot HYDX: 'Not on the board: DeepSeek review: Six-day-old generic DEX...').",
     "media"),
    ("seed-0245", "Il valore delle posizioni si aggiorna lento: serve il prezzo in tempo reale",
     "Lorenzo, 30/09: 'il saldo delle posizioni si aggiorni piu' velocemente possibile [...] trovare un servizio che ci permetta di avere queste informazioni in modo rapido [...] vedere in tempo reale i cambiamenti di prezzo e non dover aspettare diversi secondi'.",
     "alta"),
    ("seed-0241", "DREGG: '807 wallets linked to each other' preoccupa",
     "Lorenzo, 30/09: 'mi preoccupano questi 800 account collegati tra loro... indaghiamo'. Il rapporto token contava i wallet dei gruppi collegati di RugCheck, non quanta supply tengono.",
     "media"),
    ("seed-0236", "Memoria del server quasi piena: il file dello sniper cresce senza limite",
     "Controllo del server, 30/09: 1,8 GB usati su 3 GB; sniper_candidates.json a 430 MB fa salire l'app da 214 MB a 1,77 GB all'avvio. Lorenzo ha scelto di potare i file che gonfiano la memoria.",
     "alta"),
    ("seed-0237", "Scansione manuale: 'Load failed' spesso da telefono",
     "Lorenzo, 30/09: 'ricevo spesso errore' (scansione di cpool, messaggio Load failed).",
     "alta"),
    ("seed-0238", "Niente meme negli alert: strategia e alert solo su progetti seri",
     "Lorenzo, 30/09: 'le meme e shitcoin sono state bloccate dal bot alert?', poi 'non le voglio le meme [...] dobbiamo avere strategia e alert solo su roba buona'.",
     "alta"),
    ("seed-0239", "Wallet simulato: poter impostare il saldo a piacere",
     "Lorenzo, 30/09: 'la simulazione voglio poter modificare il saldo a mio piacimento'.",
     "media"),
    ("seed-timeframe-ladder-20260930", "Classifica: time frame della strategia graduale secondo la storia, e grafico settimanale",
     "Lorenzo, 30/09: 'questa differenziazione di time frame deve essere graduale con un algoritmo che tiene conto [...] di quanta storicita' ha il grafico [...] voglio vedere anche il time frame settimanale', poi 'se da un giorno non c'e', pero' a 12 ore ce l'hai, allora prendi quello [...] vai all'indietro finche' non trovi il primo time frame corretto'.",
     "alta"),
    ("seed-0244", "Tetto di size per ingresso: niente slippage da $500 sulle cripto illiquide",
     "Lorenzo, 30/09: 'adesso che il portafoglio e' 30.000 il 10% e' 3.000 [...] su queste cripto che hanno liquidita' scarsa [...] dobbiamo far si' che ci sia un tetto massimo di size [...] un'anteprima di quanto sarebbe lo slippage [...] fare un check con i vari dex e vedere quanto e' lo slippage in base a quello calcolare velocemente quanto potrebbe essere il size massimo [...] in termini di dollari'.",
     "alta"),
    ("seed-0243", "Via le schermate meme e backtest: al loro posto Signals e Track record",
     "Lorenzo, 30/09: 'dobbiamo rivalutare completamente [...] la tab [...] per le performance [...] non serve piu''; 'non me ne frega piu' niente di quelle perche' abbiamo applicato la logica [alle gemme] e la visualizzo nel conto simulato'; 'non mi serve piu' neanche la schermata dei fired last 48 ore e di visualizzare about to fire perche' e' tutta roba legata alle meme coin [...] dobbiamo rivoluzionare queste due schermate'. Scelta: due tab.",
     "media"),
    ("seed-0242", "MERRYMEN: +400% in classifica ma nessun ingresso sul grafico",
     "Lorenzo, 30/09: 'su questa cripto non vedo gli ingressi nonostante ci sia scritto nella lista in classifica un rendimento di piu' 400% [...] queste cose non devono accadere verifica in modo molto meticoloso'.",
     "alta"),
    ("seed-0240", "Grafici: ingressi della strategia nel punto giusto, timeframe graduale, settimanale, posizioni cliccabili",
     "Lorenzo, 30/09: 'voglio che tu applichi a quel portafoglio tutti gli ingressi e tutti i rendimenti di tutte le GM in top 50 per vedere come avrebbe performato'; 'la differenziazione di time frame deve essere graduale con un algoritmo che tiene conto [...] di quanta storicita' ha il grafico'; 'voglio vedere anche il time frame settimanale'; 'le posizioni aperte e chiuse se ci clicco voglio vedere quali sono stati graficamente'; 'gli ingressi registrati secondo la strategia corretta non vengono visualizzati correttamente nel grafico'.",
     "alta"),
    ("seed-quant-engine-20260930", "Sniper solo gemme: ingresso su segnale e timeframe scelti dai backtest, senza DeepSeek",
     "Lorenzo, 30/09: 'non voglio piu memecoin'; '5 min all'inizio e poi 1ora dopo 24h va decisa in base ai dati di backtest'; 'questo lavoro vorrei sgravarlo da deepseek'; 'devi costruirlo'. Motore quantitativo e memoria incidenti in revisione: non attivare politiche non validate, non dichiarare risolto prima del collaudo sui dati reali.",
     "alta"),
    ("seed-0235", "Classifica: il trend follower del sito su 8 ore o giornaliero, con segnali",
     "Lorenzo, 30/09: 'sui progetti in classifica io voglio che venga attivata la strategia [trend follower] con time frame piu' alti quindi se il token e' abbastanza giovane il time frame 8 ore se no un giorno se c'e' almeno abbastanza candele sufficienti da generare un trigger [...] ho bisogno di segnali di piu' qualita''",
     "alta"),
    ("seed-0234", "L'app da telefono non parte e i tocchi non fanno niente",
     "Lorenzo, 30/09: 'da mobile l'app non parte rimane in questa schermata [...] e se clicco non funziona nulla'",
     "alta"),
    ("seed-0233", "Scheda Alerts dello scanner lentissima: contatori a 0 e decisioni vuote",
     "Lorenzo, 30/09 (screenshot dal telefono): 'lentissimo a caricare'",
     "alta"),
    ("seed-0232", "Lo scanner manuale non si e' evoluto con il resto del sistema",
     "Lorenzo, 29/09 (screenshot HYDX su Robinhood): 'lo scanner manuale e' insufficiente e non si e' evoluto seguendo tutti gli aggiornamenti e migliorie che abbiamo fatto'",
     "alta"),
    ("seed-0231", "Rug pull nel trading simulato delle memecoin: wallet collegati e vendite coordinate",
     "Lorenzo, 29/09: 'abbiamo preso dei bei rug pull nel trading simulato di memecoin [...] controlliamo magari se e' stata ritirata la liquidita' [...] o se sono state vendite coordinate [...] indagando su wallet collegati tra loro avremmo potuto evitare [...] quel token su cui fare l'ingresso'",
     "alta"),
    ("seed-0230", "Wallet simulato: il saldo totale non torna con le posizioni aperte",
     "Lorenzo, 29/09: 'il saldo totale non corrisponde al saldo delle posizioni aperte'",
     "alta"),
    ("seed-0229", "Wallet: saldo e guadagno/perdita che si muovono col prezzo, come pump.fun",
     "Lorenzo, 29/09: 'su l'app di pump fun il saldo delle crypto nel wallet si aggiorna in modo frenetico costantemente [...] nel simulato vedo che praticamente non si aggiorna mai il valore del token e vorrei vedere anche quanto sta perdendo o guadagnando con animazioni frenetiche'",
     "media"),
    ("seed-0228", "Memecoin di nuovo negli alert, con filtri anti-rug",
     "Lorenzo, 29/09: 'a sto punto riattiviamo le memecoin per gli alert e la strategia che entra allo scoccare dell'alert, cercando di evitare i rugpull'",
     "alta"),
    ("seed-0227", "Tasto condividi: il link apre quel token a chi e' loggato",
     "Lorenzo, 29/09: 'voglio l'opzione di poter condividere un ticker dall'app con il tasto condividi e chi ha accesso ovviamente all'app tramite Safari o qualsiasi altro browser loggato deve aprire automaticamente quel token esattamente che ho condiviso'",
     "media"),
    ("seed-0226", "Ogni ticker degli alert apre la pagina del token; indirizzo copiabile",
     "Lorenzo, 29/09: 'ogni ticker per chi ho l'allarme deve aprirmi l'app in quella sezione specifica per visualizzare il token specifico, inoltre ogni ticker nell'app deve permettere se clicco qui di copiare l'indirizzo corretto on chain del token'",
     "media"),
    ("seed-0225", "Il live scanner diventa una tab accanto ad Alerts",
     "Lorenzo, 29/09: 'il live scanner in basso deve apparire come tab in alto di fianco ad alerts'",
     "bassa"),
    ("seed-0224", "DeepSeek su Telegram: accesso a tutto e istruzioni permanenti",
     "Lorenzo, 29/09: 'voglio potergli chiedere TUTTO, dagli completo accesso come risposte' e 'voglio poterlo auto istruire'",
     "media"),
    ("seed-0223", "Chiedere a DeepSeek cosa ha imparato dagli studi quotidiani",
     "Lorenzo, 29/09: 'chiediamo a deepseek cosa ha imparato dopo aver scansionato tutti i giorni le nostre crypto'",
     "media"),
    ("seed-0222", "Errore 500 su profilo e wallet (KeyError 'qty')",
     "Lorenzo, 29/09: 'che succede?' con gli avvisi di errore 500 su /api/profile e /api/wallets/total",
     "alta"),
    ("seed-0221", "Il wallet simulato non segue gli alert",
     "Lorenzo, 28/09: 'il wallet simulato non sembra replicare gli ingressi [...] voglio che li segua'",
     "alta"),
    ("seed-0220", "Alert meme spazzatura su Telegram",
     "Lorenzo, 28/09: 'occhio a non far arrivare la merda però, non voglio meme coin'",
     "alta"),
    ("seed-0219", "Nessun alert meme su Telegram da giorni",
     "Lorenzo, 28/09: 'comunque non sta arrivando neanche un alert', 'da giorni'",
     "alta"),
    ("seed-0218", "Barra di avanzamento per studi e ticker da scansionare",
     "Lorenzo, 28/09: 'aggiungiamo una barra di progressione per gli studi effettuati e quanti ticker mancano da scansionare e studiare'",
     "media"),
    ("seed-0217", "Token chiamati 'null' nella Top delle gemme",
     "Lorenzo, 28/09: 'ci sono ticker tra le top che si chiamano null'",
     "media"),
    ("seed-0216", "Sniper che non escono: MESUB -95%, GLANCE -61%, SUGAR -53%",
     "Lorenzo, 28/09: 'come mai su queste la strategia non e' uscita prima?'",
     "alta"),
    ("seed-0215", "Troppi ingressi sul grafico del token sniper (NYMA)",
     "Lorenzo, 28/09: 'troppi ingressi, ma sicuro che sia un trend follower decente?'",
     "alta"),
    ("seed-0214", "Sniper: entrare all'alert e chiudere solo con la regola del trend follower",
     "Lorenzo, 28/09: 'sugli sniper dobbiamo far si' che la strategia entri nel momento in cui viene fatto l'avviso [...] arriva l'alert su Telegram, la strategia deve entrare in quel momento. Poi deve gestire esclusivamente la chiusura secondo la classica regola del trend follower.'",
     "alta"),
    ("seed-0213", "Nella tab Strategie ogni token segnalato deve mostrare il suo backtest, non 'no entry yet'",
     "Lorenzo, 28/09: 'non deve accadere che venga scritto backtest no entry yet perche' in realta' la strategia su questa roba sarebbe entrata perche' sono stati segnalati [...] deve essere presente su tutti i ticker in questa sezione [...] il dodge che mi segnali dopo [...] a me non interessa [...] voglio vedere le performance del backtest applicato a quei token che sono stati scelti'.",
     "alta"),
    ("seed-0212", "Le gemme devono mostrare il trend follower sul giornaliero, non la strategia al minuto",
     "Lorenzo, 28/09: 'la strategia da applicare non e' quella sul minuto ma ovviamente il trend follower originario del sito nostro, quindi sul time frame giornaliero, solitamente quello, al massimo 8 ore [...] quella rapida e' esclusivamente per lo sniper'.",
     "alta"),
    ("seed-0211", "Le narrative che avevo chiesto non si vedono nell'app",
     "Lorenzo: 'Un'altra cosa importante che avevo fatto a fare a Claude in un'altra chat era quella delle narrative, che non vedo pero' svolta'.",
     "media"),
    ("seed-0210", "CERT passa da +64% a OUT, Matrix e NYMA tornano 'in arrivo'",
     "Lorenzo, 28/09: 'deve rimanere tutto salvato in database per la parte di backtest. e memorizzato, non deve cambiare ogni volta risultato e perdere i precedenti' e 'PRIORITA MASSIMA E ATTENZIONE MASSIMA'.",
     "alta"),
    ("seed-0209", "Il grafico della pagina token e' lentissimo e a volte resta su Analyzing",
     "Lorenzo: 'il motore che usiamo dal sito principale tiri dentro delle cose che non ci servono [...] Non voglio che venga applicato a questo grafico [...] nessun tipo di strategia dal vecchio sito, ma esclusivamente dal backtest di quest'app [...] in alcuni casi non carica proprio il grafico'.",
     "alta"),
    ("seed-0208", "FLOOR era primo con +132% e dopo qualche secondo e' sparito",
     "Lorenzo: 'inizialmente la foto riportava floor in vetta, dopo qualche secondo e' sparito... non deve accadere, deve rimanere tutto salvato in database per la parte di backtest. e memorizzato, non deve cambiare ogni volta risultato e perdere i precedenti'.",
     "alta"),
    ("seed-0207", "Voglio vedere la capacita' di scansione: ticker che girano, non una lista ferma",
     "Lorenzo: 'qui voglio capire la capacita' di scansione del sistema voglio vedere i ticker girare, non cose ferme'.",
     "media"),
    ("seed-0206", "Nella tab Strategie i backtest restano a meta' (5 su 13)",
     "Lorenzo: 'io apro la tab con tutte le cripto scelte, i backtest non ci sono. Vedo solo alcuni risultati [...] su questi token deve essere applicata la strategia trend follower [...] io voglio vedere tutti i risultati, ma non li sto vedendo. Fai di questo una questione fondamentale per la riuscita del sito, deve funzionare stavolta.'",
     "alta"),
    ("seed-0205", "La pagina Agent sembra ferma: DeepSeek deve vedersi lavorare",
     "Lorenzo: 'la gente non sta lavorando e non sta scansionando niente. Questo per me e' fondamentale. Voglio avere la sensazione che la gente stia lavorando costantemente [...] Voglio che la gente, attraverso anche animazioni grafiche, mi faccia capire che sta lavorando. Ed e' fondamentale che questo sia visibile, percepibile.'",
     "alta"),
    ("seed-0204", "Backtest H24 su tutti i token della schermata Strategie",
     "Lorenzo: 'voglio che quando il servizio del server e' online e siamo operativi, DeepSeek scansioni costantemente tutte le strategie e backtest [...] tutti quei token che sono finiti nella schermata delle strategie [...] nella tab a forma di grafico [...] vedo che non e' attivo su questo fronte, deve essere attivo costantemente H24'.",
     "alta"),
    ("seed-0203", "Coda Memes piena ma quasi nessun token passa i controlli",
     "Lorenzo: 'Ci sono un sacco di progetti in coda qui che non capisco perche' non vengono selezionati o scelti. Praticamente da stamattina soltanto un token ha passato i controlli. Bisogna un attimino che tu risistemi e eviti questi problemi.'",
     "alta"),
    ("seed-0202", "Il sito e' bloccato su 'Aggiornamento in corso'",
     "Lorenzo, 28/09: 'non va piu' il sito e' rimasto bloccato'.",
     "alta"),
    ("seed-0201", "La scheda di DeepSeek: un agente che si vede lavorare, con il suo ragionamento",
     "Lorenzo: 'diamo a DeepSeek una tab tutta sua con animazioni molto fatte bene [...] voglio che si veda il log su quello su cui sta lavorando, un log preciso, non soltanto cose generiche, voglio vedere come ragiona'.",
     "media"),
    ("seed-0200", "Lo scanner non e' abbastanza profondo: ogni narrativa deve avere i suoi token",
     "Lorenzo: 'non sono sicuro che lo scanner riesca a trovare progetti appartenenti ad ognuna [delle narrative] [...] magari dobbiamo alzare un po' i limiti di market cap [...] anche i progetti un po' piu' datati [...] ogni narrativa deve avere dei token al suo interno'.",
     "alta"),
    ("seed-0199", "Dopo un crollo del 90% la strategia rientra: deve fermarsi come su un rug",
     "Lorenzo (FLOOR): 'un ingresso, un'uscita e poi un nuovo ingresso con una market cap di 7000 dopo un meno 90%, questa cosa non deve accadere, la strategia si deve automaticamente disabilitare [...] il sistema flagga il token come rug pull e il backtest non deve proseguire'.",
     "alta"),
    ("seed-0198", "Sul grafico solo 'Alert', non ingressi e uscite",
     "Lorenzo (screenshot di MANSA): 'sta cosa non deve accadere, non voglio vedere schermate con scritto alert, voglio ingressi e uscite, come da strategia'.",
     "alta"),
    ("seed-0197", "Scegliere le narrative dei token da cercare, per account",
     "Lorenzo: 'diamo anche la possibilita' di scegliere la narrativa a chi comanda l'applicazione [...] almeno una quindicina di narrative'.",
     "media"),
    ("seed-0196", "Backtest su tutti i token scansionati, nei momenti morti, per far imparare DeepSeek",
     "Lorenzo: 'tutti i backtest devono essere disponibili su tutti i token scansionati [...] anche di quelli che non rientrano nel nostro standard [...] un grande database di backtest [...] tutto quello che e' facilmente identificabile come rug pull escludiamolo a priori'.",
     "alta"),
    ("seed-0195", "Passare da wallet reale a simulato e' lento e a volte non va",
     "Lorenzo: 'passare da real wallet a simulato e' laggoso e molto lento a volte non va neanche'.",
     "media"),
    ("seed-0194", "Collegare un wallet esterno da iPhone senza uscire da Safari",
     "Lorenzo: 'una connessione di un wallet esterno deve permettere di aprirlo senza cambiare finestra di Safari [...] cambiare il pannello su Safari e' una cosa ingestibile'.",
     "alta"),
    ("seed-0193", "Sul grafico del token si vede l'alert ma non ingressi e uscite della strategia",
     "Lorenzo (screenshot di FLOOR): 'visualizza un alert ma non sappiamo se e' un ingresso o altro.. qui deve comparire la strategia, come abbiamo detto. ingressi e uscite..'.",
     "alta"),
    ("seed-0192", "Il grafico del token deve essere quello del sito principale",
     "Lorenzo: 'sti ingressi e uscite nel grafico a linea fanno schifo, dovevamo usare il motore del sito principale no?' e poi 'sul grafico del minuto si apre dex scanner, ma poi perdo i dati di ingresso e uscita [...] USA QUELLO'.",
     "alta"),
    ("seed-0191", "Il giudizio sui siti e i pilastri a 85 vanno migliorati: voto finale con DeepSeek",
     "Lorenzo: 'site too weak, mi sembra un parametro non troppo significativo, MIGLIORA IL METODO DI GIUDIZIO' e 'potresti usare deepseek istruendolo a non farsi fregare, e soprattutto a leggere i dati raccolti in chiave critica [...] DREGG inizialmente neanche usciva dai parametri'.",
     "alta"),
    ("seed-0190", "Nella Top compaiono token NOT RANKED",
     "Lorenzo (screenshot della Top): 'vedo in classifica roba NOT RANKED, non va bene'.",
     "media"),
    ("seed-0189", "La strategia deve essere operativa subito dopo l'alert, con i suoi criteri",
     "Lorenzo: 'quando parte l'alert voglio che la strategia sia subito operativa con trend follower' e poi 'no, deve entrare con i criteri della strategia, sempre'.",
     "alta"),
    ("seed-0187", "Eliminare a mano i token da ogni lista, per account, con il successore animato",
     "Lorenzo: 'aggiungi opzione manuale di eliminare i token da ogni lista o classifica (ognuno nel proprio account), dando spazio (animandolo) ad un suo successore che ne prende il posto'.",
     "media"),
    ("seed-0186", "Backtest in loop che non arrivano",
     "Lorenzo (screenshot della classifica con i puntini su MESUB, MANSA, AGRARIS, Onhand): 'backtest in loop non arrivano, fai in modo che funzionino'.",
     "alta"),
    ("seed-0185", "LOCK e XONA sempre sul podio con voti piu' bassi di altri",
     "Lorenzo: 'ma lock e xona sono sempre nel podio anche se hanno voti piu' bassi di altri... RISOLVI'.",
     "alta"),
    ("seed-0184", "La Top 15/25/50 va nella scheda con la coppa delle gemme",
     "Lorenzo (screenshot della pagina gemme): 'la top 15-25 etc deve andare in questa tab (icona coppa da mettere) non dove l'hai messo tu'.",
     "media"),
    ("seed-0183", "'No signal on this chart' non ha senso",
     "Lorenzo: 'no signal on this chart non ha senso, se c'e' un chart c'e' il backtest AUTOMATICAMENTE, dai l'idea che deve essere ancora elaborato semmai, dinamicamente animata'.",
     "media"),
    ("seed-0182", "Pagina Alerts troppo affollata",
     "Lorenzo (screenshot di Memes > Alerts con auto-trade, scan, system e about to fire): 'UI TROPPO AFFOLLATA RIPROGETTALA'.",
     "media"),
    ("seed-0181", "Niente nomi delle strategie: solo i rendimenti, sempre il migliore",
     "Lorenzo: 'trend hf o trend ema non voglio vederli, il sistema e' proprietario nostro per cui non indichiamo cosa usiamo, semplicemente i rendimenti' / 'l'importante e' proporre la migliore delle due (internamente) proponendo sempre il miglior risultato'.",
     "alta"),
    ("seed-0180", "Podio cartoonesco e liste troppo grandi",
     "Lorenzo (screenshot della classifica gemme): 'qui e' tutto grosso, fin troppo, e il podio mi fa schifo cartoonesco, rifallo in stile cyberpunk come il logo del nostro sito'.",
     "media"),
    ("seed-0179", "Profilo: tutto in una schermata senza scorrere",
     "Lorenzo (screenshot del profilo): 'in questa schermata voglio vedere tutto senza dover scrollare giu''.",
     "media"),
    ("seed-0178", "La coppa nella barra delle strategie non ha senso, va sul podio",
     "Lorenzo: 'l'icona della coppa dove ci sono le strategie non ha senso, piuttosto va nel podio'.",
     "bassa"),
    ("seed-0176", "Non voglio selezionare le strategie: mostrami i backtest migliori",
     "Lorenzo: 'non voglio selezionare le strategie, il sistema deve essere gestito in modo invisibile, semplicemente mostrami i backtest migliori delle strategie disponibili'.",
     "media"),
    ("seed-0175", "Usare il grafico del sito principale per vedere gli ingressi",
     "Lorenzo: 'puoi usare anche il grafico del sito principale volendo, era ideale per visualizzare ingressi'.",
     "media"),
    ("seed-0177", "Backtest delle strategie sul grafico di ogni crypto, come sul sito principale",
     "Lorenzo (screenshot della classifica, tutte '— no entry yet'): 'non esiste che su queste crypto non ci sia un backtest delle strategie, come facciamo sul sito principale [...] stessa cosa dobbiamo poter fare qui'.",
     "alta"),
    ("seed-0174", "Nella classifica del sistema tutti 0%: voglio vedere i backtest",
     "Lorenzo (screenshot della hall of fame ordinata per System, CERT/GLANCE/Onhand... tutti '0% waiting'): 'qui voglio vedere i backtest!!! non voglio vedere 0%'.",
     "alta"),
    ("seed-0173", "Rendimenti delle strategie, non solo dal momento dell'alert, e la chiusura della posizione",
     "Lorenzo: 'i rendimenti vorrei vederli delle strategie, non solo dal momento dell'alert. Anche la chiusura della posizione e' importante'.",
     "alta"),
    ("seed-0172", "Il sistema trend ha perso ONHAND +1304%",
     "Lorenzo: 'fai analizzare perche' ha perso ONHAND, teoricamente il trend follower non puo' perdersi trend di mercato'.",
     "alta"),
    ("seed-0171", "L'app non e' centrata nel telefono, anche dopo aver scritto in una casella",
     "Lorenzo: 'quando apro l'app non risulta centrata perfettamente nel telefono, non voglio mai avere questo problema neanche quando inserisco testo in caselle'.",
     "media"),
    ("seed-0170", "Il modello dei rug non si attiva mai: tutti gli esiti sono rug",
     "Report di DeepSeek letto da Lorenzo: memoria active:false con n 3113 e rugs 3113, tutti gli AUC vuoti ('no rugs or no non-rugs').",
     "alta"),
    ("seed-0169", "Signal, Why e Info devono essere sempre completi, per ogni token",
     "Lorenzo (screenshot di Whales Market aperto da Top, solo 'No Telegram alert'): 'signal, why e info devono essere sempre completi di informazioni, per ogni token'.",
     "media"),
    ("seed-0168", "Aave in classifica con 531k di market cap",
     "Lorenzo (screenshot della Top): 'AAVE non ha 531k di market cap, e' un progetto molto grosso, fai controllare tutti i valori di market cap e anche i simboli'.",
     "alta"),
    ("seed-0167", "Il pannello dell'agente scrive il messaggio una lettera per riga",
     "Lorenzo (screenshot di 'The agent': 'Nothing yet since the last restart' in verticale, sotto 'Today: 28 chat'): 'comincia facendo risolvere questo bug'.",
     "media"),
    ("seed-0166", "Ogni tanto la schermata flasha e appaiono sovrapposizioni",
     "Lorenzo (screenshot con scheda di scansione, autotrader e alert sovrapposti): 'ogni tanto flasha la schermata e appaiono sovrapposizioni'.",
     "alta"),
    ("seed-0165", "Top 15, 25 e 50 mostrano sempre gli stessi progetti",
     "Lorenzo (screenshot della scheda Top, 6 progetti): 'a prescindere se seleziono top 15 25 o 50 vedo sempre gli stessi progetti'.",
     "alta"),
    ("seed-0164", "DeepSeek con accesso a tutto il database e segnalatore di bug",
     "Lorenzo: 'aumentiamo i poteri a deepseek, dai accesso completo al database cosi' da telegram posso interrogarlo su tutto; usalo come bug fixer [...] tieni a mente di guardare sempre quello che ha scritto quando parli con me'.",
     "media"),
    ("seed-0163", "Nel podio delle gemme punteggi piu' bassi di quelli nel database; scansione lenta",
     "Lorenzo: 'nel podio delle gemme compaiono token con punteggi piu' bassi rispetto a quelli presenti in database' e 'la scansione complessiva e' lenta, possiamo migliorarla?'.",
     "alta"),
    ("seed-0162", "Alerts troppo carichi; Picks sono meme coin; top 15/25/50; 'lp locked' non protegge",
     "Lorenzo: 'la tab alert e' confusionale, troppe informazioni, troppe cripto [...] vedere quali alert sono scattati in ordine cronologico [...] cosa sta per scattare [...] riesumare roba vecchia che sta ritornando in moda', 'sostituirei la scheda Picks con la top 15, top 25, top 50 [...] non voglio assolutamente il meme coin', e l'analisi di DeepSeek su lp_locked_pct e top_holder_pct a 0.",
     "alta"),
    ("seed-0161", "Scansione manuale di un ticker o indirizzo; togliere 'Lorenzo' dalla strategia",
     "Lorenzo: 'aggiungiamo anche l'opzione di aggiungere un indirizzo di un token o il suo ticker che poi va a cercare nel database di DexScreener [...] compresa anche la scansione di DeepSeek e tutto il processo' e 'elimina il nome lorenzo dalla strategia'.",
     "media"),
    ("seed-0160", "Un agente animato sempre presente; la hall of fame senza timeframe",
     "Lorenzo: 'dobbiamo dare l'idea animata che tutto il sito sia gestito da DeepSeek [...] ci deve essere qualcosa che si muove [...] un agent che esamina le cose' e 'il podio non deve avere timeframe, e' la hall of fame'.",
     "media"),
    ("seed-0159", "L'app e' troppo complicata: troppe schermate",
     "Lorenzo: 'mi sembra un po' troppo complicata l'applicazione, ci sono troppe schermate [...] il podio ha senso soltanto per le gemme [...] una leaderboard con le strategie ingresso e uscita [...] una leaderboard per le gemme [...] che sia semplice'.",
     "alta"),
    ("seed-0158", "DeepSeek deve avere voce in capitolo sul voto finale delle gemme",
     "Lorenzo: 'ovviamente deepseek deve avere voce in capitolo sul voto finale delle gemme'.",
     "media"),
    ("seed-0157", "DeepSeek con memoria dei rug pull e accesso al database",
     "Lorenzo: 'deepseek deve poter avere memoria dei rugpull, le circostanze con cui sono avvenuti, per cui accedere al database con tutti i dati delle crypto monitorate risulta fondamentale'.",
     "media"),
    ("seed-0156", "Scanner piu' intelligente con DeepSeek, spendendo il meno possibile",
     "Lorenzo: 'creiamo un piano di integrazione di intelligence all'app, deve diventare tutto piu smart la scansione [...] usando deep seek' e 'ottimizziamo questa logica per spendere meno possibile'.",
     "media"),
    ("seed-0155", "DeepSeek su Telegram e riepilogo giornaliero dei token",
     "Lorenzo: 'mettiamo possibilita' di parlare con deepseek su telegram?' e 'voglio un riepilogo giornaliero di quanti token ci ha fatto risparmiare, su telegram'.",
     "media"),
    ("seed-0154", "Un 'wallet simulato' da selezionare per vedere il saldo simulato",
     "Lorenzo: 'il fatto che sto simulando il denaro deve essere possibile selezionando \"wallet simulato\", cosi' visualizzo il saldo simulato e posso vedere realmente cosa succede'.",
     "media"),
    ("seed-0153", "Il grafico del wallet: periodi 1h-8h e legato al valore reale",
     "Lorenzo: 'il wallet deve avere anche l'andamento 1h 2h 3h 4h 8h; e il grafico deve essere realizzato seguendo il valore del portafoglio, strettamente legato'.",
     "media"),
    ("seed-0152", "Depositi: crypto per rete, carta, exchange",
     "Lorenzo (screenshot di un pannello 'Deposit with': Crypto / Debit / Exchanges and apps): 'aggiungiamo queste possibilita' per i depositi'.",
     "media"),
    ("seed-0151", "Il saldo del wallet esce a $0.00",
     "Lorenzo (profilo alle 19:18, $0.00 in alto e nel valore): 'non becca il saldo'.",
     "alta"),
    ("seed-0150", "Le icone non corrispondono a quelle corrette del token",
     "Lorenzo: 'le icone non corrispondono a quelle corrette del token'.",
     "media"),
    ("seed-0149", "Il grafico del profilo non rispetta l'andamento reale del portafoglio",
     "Lorenzo: 'il grafico non rispetta l'andamento reale del portafoglio'.",
     "alta"),
    ("seed-0148", "Non vedo il wallet nella barra in basso",
     "Lorenzo, con uno screenshot delle 19:00: 'non vedo wallet'. Nella barra c'erano solo tre icone.",
     "alta"),
    ("seed-0147", "Sul telefono si vedeva ancora la versione vecchia dell'app",
     "Lorenzo, con uno screenshot delle 18:40: in alto '0 SOL', in basso l'icona Wallet e la classifica su Now/best, cioe' la versione di prima, mentre la nuova era online da ore.",
     "alta"),
    ("seed-0146", "Backtest a -80% quando la strategia avrebbe dovuto chiudere molto prima",
     "Lorenzo: 'non capisco i backtest perche' ci sono delle percentuali di meno 80%, pero' la strategia dovrebbe aver chiuso molto prima. Verifica'.",
     "alta"),
    ("seed-0145", "Wallet multi-chain: vedere il saldo di qualunque token su qualunque chain",
     "Lorenzo: 'il wallet deve essere multi-chain e devo visualizzare il saldo a prescindere da quale token e in quale chain ho'.",
     "alta"),
    ("seed-0144", "Comprare e vendere dal proprio wallet collegato, firmando nel wallet",
     "Secondo passo del piano per i wallet di chiunque (seed-0143), avviato con 'procedi' e poi 'auto approva tutto quello che proponi d'ora in poi'.",
     "media"),
    ("seed-0143", "Chiunque deve poter collegare il proprio wallet al sito",
     "Lorenzo: 'dobbiamo dare la possibilita' di far collegare il wallet a qualsiasi persona al nostro sito per usufruire dei nostri servizi; l'unica cosa e' che non so bene se la strategia automatica in quel caso e' fattibile, deve firmare uno speciale smart contract cosi' che si attivi questa strategia automatica'. Poi: 'procedi'.",
     "alta"),
    ("seed-0142", "Il cash e' USDC; per operare su Robinhood prima si converte in USDG",
     "Lorenzo: 'fai in modo che l'applicazione utilizzi il solito sistema di cash, cioe' devono essere USDC, e ovviamente se operi su Robinhood prima di poterlo fare devi convertire in USDG'. Alle domande: USDC multichain; dopo ogni vendita si torna sempre in USDC.",
     "alta"),
    ("seed-0141", "DeepSeek sul server per analizzare i dati, dare insight e migliorare gli alert",
     "Lorenzo: 'mi piacerebbe inserire nel server DeepSeek perche' e' un modello gratuito [...] utilizzarlo come intelligenza per la gestione di tutti questi dati e dare degli insights e migliorare gli alert. Ma e' possibile installarlo? Se si', fallo. E se hai bisogno delle API vediamo come fare'.",
     "media"),
    ("seed-0140", "Un profilo vero: immagine, nome, bio, cosa detieni, andamento del wallet nel tempo",
     "Lorenzo, con lo screenshot del profilo di un'app di trading: 'uno deve vedere cosa detiene, l'andamento del wallet nel tempo con un grafico, e ovviamente l'account con cui uno si e' loggato deve rimanere tutto nel database, uno deve poter scegliere anche l'immagine profilo, queste cose qua, cosi' che uno abbia il suo profilo dove effettivamente avere un controllo maggiore su tutta la piattaforma. Fai un bello studio su questo e applica'.",
     "media"),
    ("seed-0139", "Con un tasto il sistema opera da solo sul wallet Robinhood, con la percentuale del saldo scelta",
     "Lorenzo: 'voglio semplicemente che con un tasto io attivo la strategia e che faccio operazioni sul wallet disponibile, in questo caso io ho depositato una cifra sul wallet di Robinhood, quindi voglio che automaticamente la strategia faccia i suoi ingressi, le sue uscite e che utilizzi sempre la totalita' del saldo [...] uno seleziona il 100% del saldo, il 50, il 25 eccetera, devi considerare sempre le fee, in modo tale che le operazioni vadano sempre in porto'. Alle domande: saldo in USDG, un token alla volta, nessun limite oltre alla percentuale, prima simulato.",
     "alta"),
    ("seed-0138", "Rendere operativa la miglior strategia trend-following e usarne ingressi e uscite come risultati della classifica",
     "Lorenzo: 'con tutti i backtest che abbiamo fatto finora trova la miglior strategia di quelle che avevamo a disposizione e rendiamola praticamente operativa [...] che i segnali di quella strategia siano entrare e uscire, ovviamente trend follower, e che sia utilizzato i risultati di questi ingressi e di queste uscite come risultati nella leaderboard [...] per evitare proprio i rug pull e per prendersi i movimenti rialzisti quando questi occorrono'.",
     "alta"),
    ("seed-0137", "Grafici ancora troppo lenti, e su alcuni ticker il grafico non c'e' proprio",
     "Lorenzo: 'ancora troppo lenti a caricare i grafici, in alcuni ticker non c'e' grafico proprio'.",
     "alta"),
    ("seed-0136", "Il grafico impiega almeno 10 secondi ad aprirsi",
     "Lorenzo: 'il grafico impegna almeno 10 secondi ad aprirsi, inammissibile'.",
     "alta"),
    ("seed-0135", "La scheda Scanner e' confusionaria e tiene il grafico di una crypto per tutto il giorno",
     "Lorenzo: 'la scheda scanner e' confusionaria, non voglio che rimanga il grafico di una crypto per tutto il giorno, devi ristudiarla per bene'.",
     "alta"),
    ("seed-0134", "La scheda Trending sembra una lista di token di tendenza, non la scelta del motore",
     "Lorenzo: 'ma la sezione trending cosa e'?' e poi 'non e' chiaro che siano state scelte, sembrano appunto trending, deve essere chiaro che sono uscite dalla logica'.",
     "media"),
    ("seed-0133", "Il logo DEGEN di caricamento non e' nello stile della home",
     "Lorenzo: 'il logo DEGEN di caricamento non e' adeguato alla home page come stile ... studia qualcosa'.",
     "bassa"),
    ("seed-0132", "I grafici nella pagina del token sono troppo lenti ad arrivare",
     "Lorenzo: 'i grafici caricati sono troppo lenti ad arrivare'.",
     "alta"),
    ("seed-0131", "BSC per le Meme insieme a Solana e Robinhood; Ethereum e Base solo per le Gemme",
     "Lorenzo: 'secondo me andrebbe aggiunta BSC per le Meme insieme a Sol e Robinhood. Poi Eth e Base solo per le Gemme'.",
     "media"),
    ("seed-0130", "Home page: un solo pulsante Enter app al posto delle due porte",
     "Lorenzo: 'la home page va migliorata non servono piu' i due tasti per le due sezioni, basta enter app'.",
     "bassa"),
    ("seed-0129", "Riportare i dati storici della versione precedente nella classifica degli alert",
     "Lorenzo: 'riesci a riportare i dati storici che avevamo nell'altra versione ?'.",
     "media"),
    ("seed-0128", "Estendere le ricerche anche alla chain Base",
     "Lorenzo: 'procedi, estendiamo anche a chain BASE le ricerche'.",
     "media"),
    ("seed-0127", "Podio della classifica progettato con agenti specializzati, animato a 120fps, con i loghi veri",
     "Lorenzo: 'progetta la leaderboard con agenti specializzati, voglio qualcosa che catturi attenzione animata con fluidita' 120fps [...] parlo del PODIO IO'. Poi: 'l'importante e' che poi al posto delle faccine ci sia il logo' e 'applica tutto, decidi te qual e' la piu' bellina'.",
     "media"),
    ("seed-0126", "Un'app sola, con grafica e layout da app di trading per telefono, e i loghi dei token",
     "Lorenzo (con quattro screenshot di un'app di trading meme): 'l'app deve essere unica e gestita cosi' graficamente e come layout, ispirati'. Poi: 'anche i simboli dei token li voglio [...] non e' minimamente paragonabile a quelle screenshot che ti ho mandato, usa un team ad hoc per esaminare disposizione, layout, tema e grafica dell'app'.",
     "alta"),
    ("seed-0125", "Leaderboard delle gemme graficamente incredibile e animata; sito senza roba inutile, review semplice",
     "Lorenzo: 'come gestiamo il revisore claude ? non voglio che finisca i miei token; non complicare il sito con roba inutile; la daily review deve essere semplice; rendi graficamente incredibile la leaderboard delle gemme, animala e usa linguaggio di programmazione modernissimo per farlo'.",
     "media"),
    ("seed-0124", "Un'istanza di Claude Sonnet sul server che impara dagli errori, con un tetto di token al giorno",
     "Lorenzo: 'sto pensando di mettere un istanza di claude sonnet nel server per farlo lavorare (con un massimo di token al giorno) cosi' impariamo dagli errori'.",
     "media"),
    ("seed-0123", "Meme Sniper: classifica degli alert Telegram con il rendimento da quando arriva il messaggio",
     "Lorenzo: 'il meme sniper deve avere una leaderboard anch'esso, con anche i risultati se avessimo seguito l'alert di telegram (non le strategie), semplicemente se fossimo entrati quando arrivava il messaggio di telegram quanto guadagno ci sarebbe stato [...] voglio che si veda le performance del segnale dopo 1,2,3,4,5,6,8,12,24,48h, e infine aggiornato in tempo reale, oltre a questo anche il rendimento della miglior strategia backtestata'.",
     "alta"),
    ("seed-0122", "Gemme sotto i $50k con fondamentali da evidenziare, e avvisi Telegram anche per le gemme",
     "Lorenzo: 'per gemme quando la market cap e' sotto i 50k e fondamentali ci sono, voglio che il sistema lo evidenzi che potrebbe valere la pena di comprare un po, voglio poi gli avvisi su telegram anche per le gemme'.",
     "alta"),
    ("seed-0121", "Gem Finder: vede sempre i soliti progetti, serve un database",
     "Lorenzo: 'il gem hunter deve trovare progetti di qualita', ma vedi sempre i soliti.. ma fatti un database no?'.",
     "alta"),
    ("seed-0120", "Rinfrescata di design dell'app on-chain",
     "Lorenzo: 'procedi a fare tutto, e poi direi che anche una rinfrescata di design non faccia male, miglioralo'.",
     "media"),
    ("seed-0119", "Sniper di meme piu' professionale: un motore suo, non gli scarti del filtro dei progetti seri",
     "Lorenzo: 'uguale per lo sniper di meme, dobbiamo rendere tutto piu' professionale'.",
     "alta"),
    ("seed-0118", "Gem Finder: algoritmo piu' profondo, ci sono progetti migliori che non trova",
     "Lorenzo: 'io entrerei anche nella logica con cui sceglie le gemme, senz'altro ci sono progetti migliori ma non li trovo, dobbiamo fare un algoritmo piu' profondo'.",
     "alta"),
    ("seed-0117", "Gem Finder da ricercatore, non caccia ai lanci: in classifica token di 15 minuti con $1 di liquidita'",
     "Lorenzo: 'il calciatore di gemme non deve scansionare il mercato degli ultimi 15 minuti, devi andare a trovare progetti anche esistenti soprattutto, avere un approccio da ricercatore [...] vede il sito, vede di cosa parla il sito e restituisce un risultato [...] ci deve essere una specie di coscienza [...] la ricerca al minuto delle cose che escono deve stare sullo sniper, non qui [...] io avevo trovato tipo Sol Router, che e' interessantissimo, pero' tu non stai trovando niente di equiparabile'.",
     "alta"),
    ("seed-0116", "Gem Finder: cercare anche per narrativa (privacy, ZK, AI agent, OS agentici, soldi gestiti da AI)",
     "Lorenzo: 'dobbiamo inserire nel cacciatore di gemme anche la parte di narrativa, quelle che vanno piu' forte ora, privacy, zero knowledge, ai agent, sistemi operativi agentici etc, usa un esperto e trova quanti piu' argomenti essenziali per il futuro delle cripto e dei soldi gestiti da AI, perche' non stanno ancora uscendo risultati, ho solo dregg e un altro'.",
     "alta"),
    ("seed-0115", "Sito senza nomi personali, con due sezioni distinte: gemme e meme",
     "Richiesta: 'rendilo privacy centrico, nel senso che non ci deve essere scritto Lorenzo [...] ci deve essere una sezione che riguarda il trading di meme coin [...] mentre per quanto riguarda i progetti seri voglio che anche li' ci sia uno scan H24 [...] che poi finisce nella leaderboard [...] anche a livello di interfaccia grafica siano distinte queste due sezioni prima di poter entrare'. Poi: 'deve essere anche chiaro che e' un qualcosa di estremamente gambling, la sezione per le meme coin' e 'revisione a tutto il sito in ottica degen [...] i dettagli che non serve a nessuno sapere non ci devono essere'.",
     "alta"),
    ("seed-0111", "I progetti seri non escono: in classifica solo DREGG",
     "Lorenzo: 'vedo che pero' hai trovato soltanto drag perche' te l'ho detto io [...] devi trovarli, ce ne sono tanti su Robin Hood Chain e su Solana, con low cap e micro cap bisogna che esca fuori qualcosa [...] anche uno, due, tre mesi non e' importante, l'importante e' che siano sotto uno barra due, tre milioni di market cap, non oltre'.",
     "alta"),
    ("seed-0110", "La memoria deve studiare i token scartati che poi sono esplosi, e le meme vanno cavalcate",
     "Lorenzo: 'ho visto che hai scartato dei token che hanno fatto grandissime percentuali, per cui devi andare a studiare tutti quei casi li' e fare in modo che la prossima volta quei progetti vengano fuori con le stesse caratteristiche. Dobbiamo cavalcare le meme coin sostanzialmente, per cui deve essere anche chiaro che e' un qualcosa di estremamente gambling'.",
     "alta"),
    ("seed-0109", "Pagina di presentazione del progetto e del token da lanciare",
     "Lorenzo: 'fai una pagina web di presentazione del progetto con slogan accattivante in inglese; crea il ticker del token, ci serve lanciarlo e inventati anche una tokenomics [...] mi piace lo stile dell'app (che dovra' essere un tasto al centro dove \"ENTER THE APP\") [...] facciamo chiaramente capire che ci sono due sezioni; una per sniperare progetti nuovi con regole (facendole vedere) un'altra sezione per progetti (seri con fondamentali) ma sempre microcap [...] devi pensare a tutto anche a cose che non ti ho detto'.",
     "alta"),
    ("seed-0108", "Il radar deve imparare da cosa succede davvero ai token che propone e scarta",
     "Lorenzo: 'dobbiamo implentare una specie di \"coscienza\", imparare dai segnali; da cosa effettivamente succede, e migliorare il sistema'.",
     "alta"),
    ("seed-0107", "Rug pull su VISE, token proposto: -93%",
     "Lorenzo: 'abbiamo appena subito un rugpull su VISE che era stata proposta, il token ha fatto -93%, impara da questo errore. Cosa non avevamo visto?'",
     "alta"),
    ("seed-0106", "Radar: DREGG deve uscire davvero, e cercare progetti tecnici anche oltre i token freschi",
     "Lorenzo: 'voglio che drag tu mi verifichi che esca con queste regole, perche' deve uscire [...] estrai punti chiave da questo progetto e applica come regola [...] per altri progetti che possono essere simili dal punto di vista tecnologico [...] devi ampliare le ricerche [...] scandagliare tutto compreso anche X [...] non ci limitiamo a token freschi [...] anche un anno puo' essere giusto'.",
     "alta"),
    ("seed-0105", "Wallet on-chain: troppi menu e tasti, voglio un'esperienza da DEX",
     "Lorenzo: 'voglio che l'esperienza su questo sito sia paragonabile a un DEX [...] devi rendere l'app migliore, esaminarla nel suo complesso, aggiungere funzioni, perche' e' molto carina adesso, pero' ci sono tanti menu, tanti tasti che potrebbero essere secondo me ridotti'.",
     "media"),
    ("seed-0104", "Classifica dei progetti migliori, con analisi profonda di GitHub, sito e tokenomics",
     "Lorenzo: 'devi fare una specie di leaderboard che è sostanzialmente una classifica [...] cose estetiche che facciano capire primo posto, secondo posto, terzo posto e deve essere una classifica dinamica [...] aggiornata in tempo reale [...] rigoroso [...] da GitHub E devi controllare i commit insomma deve essere profonda sta cosa la tokenomics non deve essere uno scam il sito deve essere fatto bene magari se riesci ad analizzarne l'html e vedere se è fatto bene o se è solo una pagina di presentazione ma dietro non c'è niente [...] segnalare anche da quanto è che sono usciti [...] e ampliamo anche la chain per i token lanciati su Pump Fun'.",
     "alta"),
    ("seed-0103", "Telegram: i messaggi arrivano tagliati, non sono mai completi",
     "Lorenzo: 'Inoltre i messaggi su Telegram arrivano tagliati, non sono mai completi.'",
     "alta"),
    ("seed-0102", "Radar: DREGG escluso perche' ha piu' di 3 settimane e supera i $2M",
     "Lorenzo: 'con questa regola dovresti trovare $DREGG, vediamo se sei bravo'. Poi: 'dregg va bene anche se ha 21 gg e supera i 2 mln, progetti in quel modo voglio che siano eccezione in quanto tecnicamente incredibili su github'.",
     "alta"),
    ("seed-0101", "Wallet on-chain: nello swap non si capisce cosa ho, e scegliere un token fa scendere la pagina",
     "Lorenzo: 'dovrebbe automaticamente selezionarmi la valuta che ho nel wallet. Io ho fatto degli swap da Ethereum a USDG, ma non e' chiaro che moneta io abbia nel portafoglio. [...] Deve essere selezionata automaticamente la valuta detenuta, quella con maggior quantita'. Poi quando seleziono una valuta per fare lo swap la schermata mi va in basso e mi tocca tornare su'.",
     "alta"),
    ("seed-0100", "Radar: cap fino a $2M per le gemme, e token scelti e scartati spariti dopo un aggiornamento",
     "Lorenzo: 'alziamo un po' il limite di market cap anche perché il mio obiettivo è trovare delle gemme per cui anche uno o due milioni di market cap potrebbe andare bene però nel momento in cui dal punto di vista GitHub, sito, tokenomics tante cose devono essere perfette [...] adesso ho refreshato il sito e non ho più l'elenco [...] dei token scartati e il token che prima era stato scelto non lo vedo più fa in modo che ogni volta che viene scelto un token venga salvato in database così che io ad ogni accesso possa rivedere anche dopo un riavvio'.",
     "alta"),
    ("seed-0099", "Radar: ingressi non nel punto preciso del grafico, e niente short",
     "Lorenzo: 'se seleziono una strategia non appare nel grafico gli ingressi in modo preciso'. E: 'non voglio short, solo acquisti spot e vendite'.",
     "alta"),
    ("seed-0098", "Strategia Lorenzo ad alta frequenza per i token on-chain appena usciti",
     "Lorenzo: 'creare un algoritmo di trading adatto per l'alta frequenza per cavalcare queste [...] cripto [...] e non perdersi [...] i rialzi. Non voglio utilizzare strategie inverse perché credo che qui quando il prezzo sale sale [...] il trend follower è corretto però voglio che lo ottimizzi per questa particolare applicazione on chain [...] voglio comunque mantenere la logica di quella di Lorenzo però applicata ad un time frame [...] sui minuti, quindi con dei filtri diversi'.",
     "alta"),
    ("seed-0097", "Radar: grafico vuoto con DexScreener pieno, token oltre i $100k, scartati e pagella dei filtri",
     "Lorenzo: 'Se Dex Scanner visualizza correttamente il ticker con tutta la liquidità, eccetera, nel sito nostro non può uscire questo errore inaccettabile, non deve mai succedere' (FLIP su Robinhood: 'Nessun dato disponibile'). E: 'voglio capire che è una cosa live [...] deve esserci un senso di movimento', 'se ci clicco voglio vedere tutti i parametri di GitHub [...] un bel benchmark [...] se in modo eccellente oppure [...] mediocri', 'invece di usare Token Sniffer usa qualche sito che ha delle api pubbliche', 'scorrendo giù voglio una sezione che mi faccia vedere tutti quelli che sono stati scartati'. Più l'avviso Telegram '⚠️ Dati stantii: UBR@solana [...] [1m] — ultima candela 0h fa'.",
     "alta"),
    ("seed-0096", "Condividere il sito con un amico in sola lettura",
     "Lorenzo: 'vorrei pubblicare un link per condividere questo sito che abbiamo fatto con un amico che lo possa utilizzare senza ovviamente poter modificare niente, quindi solo la lettura. È possibile mostrarglielo se copio il link del sito cosa gli arriva?'",
     "media"),
    ("seed-0095", "Radar: solo token legittimi sotto i $100k, con sito, GitHub e Token Sniffer, e il radar come prima pagina",
     "Lorenzo: 'voglio evitare rug pull, voglio evitare puttanate, stronzate, voglio token legittimi con progetti seri [...] una market cap non oltre i 100.000 dollari [...] voglio avere anche la possibilità con un link di cliccare e andare sul sito del token [...] se si riesce a fare anche questo controllo con Claude sarebbe ideale'. Poi: 'fai un controllo anche per github [...] voglio evitare SHITCOIN e MEMECOIN', 'aggiungi anche il report di token sniffer [...] che ci fa da filtro ulteriore', e 'vorrei che la prima pagina quando entro sia proprio questa qui [...] i pop-up che vanno in una lista e rimangono [...] e il grafico [...] di tutti quelli rilevati quale strategia performerebbe meglio facendo un backtest, in tempo reale con gli ingressi'.",
     "alta"),
    ("seed-0094", "Wallet on-chain: un alert costante sui token giovani, provati su tutte le strategie",
     "Lorenzo: 'voglio che nell'applicazione venga informato di quale token appena nato, o comunque che ha due o tre settimane di vita con tanta liquidità e bassa capitalizzazione [...] quale delle strategie performa bene, una specie di alert costante che scansionando il mercato mi propone [...] c'è questo ticker su Solana o su rete Robinhood che performerebbe bene con questo tipo di strategia [...] deve esserci un minimo di backtest'. Poi: 'per il grafico [...] voglio la stessa grafica del sito [...] zoomare [...] vedere in tempo reale gli ingressi e le uscite delle strategie se le avessi attivate [...] strategie che eventualmente potrei attivare oppure no'.",
     "alta"),
    ("seed-0093", "Wallet on-chain: il saldo si vede in una sola unità",
     "Lorenzo: 'in questo momento io visualizzo il saldo in Ethereum, voglio che se clicco su ETH mi switchi la visualizzazione in dollari, in Bitcoin e basta'.",
     "bassa"),
    ("seed-0092", "Wallet on-chain: cercando MYCEL esce MYCE, poi grafico vuoto e swap bloccato",
     "Lorenzo, da iPhone su Robinhood Chain: 'sto errore non deve MAI SUCCEDERE'. Aveva cercato MYCEL: la ricerca lo scartava (pool da $4.7k sotto la soglia) e restava MYCE; il grafico mostrava 'Nessun pool per questo token su nessun fee tier' e 'Nessun dato disponibile per MYCE@robinhood:0x...', lo swap 'Preventivo non disponibile'. Poi: 'non e' che deve escludermi dei risultati [...] io ti scrivo tutta roba che e' presente su Dex Scanner'.",
     "alta"),
    ("seed-0091", "Wallet da telefono: pagina decentrata all'apertura, rete da cambiare nel menu, nessun avvio",
     "Lorenzo, da iPhone: 'quando entro nel sito da mobile fai in modo che tutto sia perfettamente allineato al monitor, adesso appena lo apro e' decentrato, voglio un'animazione anche all'avvio appena mi collego [...] con scritto DEGEN'. E: 'per cambiare rete voglio che ci sia un simbolino [...] che mi faccia capire che posso cambiare rete con un click, senza andare a pigiare il tasto nel menu'.",
     "media"),
    ("seed-0090", "Wallet on-chain: molti ticker non si trovano, e per ogni ticker escono doppioni",
     "Lorenzo: 'mezzi ticker non funzionano; voglio solo un unico risultato per ticker, quello con il contratto corretto e verificato con liquidità migliore, non voglio dover scegliere altri doppioni'.",
     "media"),
    ("seed-0089", "Wallet on-chain: troppi tasti, e con la strategia accesa non si vedeva cosa stava facendo",
     "Lorenzo: 'voglio potermi fidare di questa applicazione visto che quando attivo la strategia utilizzo soldi reali, voglio avere il completo controllo di quello che sta succedendo [...] mi crea confusione un'interfaccia con troppi tasti [...] odio i tasti [...] tanta diagnosi nel momento in cui una strategia e' attiva'. Prima ancora: 'l'app deve funzionare con pochi clic, pochi cambi di schermata' e 'rendi l'app da mobile un'esperienza SEMPLICISSIMA'. Concept 'Pilota' approvato: 'PROCEDI E' PERFETTO'.",
     "alta"),
    ("seed-0088", "Wallet on-chain da telefono: scegliere un token apre troppe schermate",
     "Lorenzo: 'rivedi completamente il sito se mi collego da mobile; se seleziono un token si aprono troppe schermate'. Su /onchain-app.html da telefono il token scelto sul grafico non arrivava allo swap: andava riscelto nel pannello ordine, che stava sotto l'elenco delle posizioni, con un secondo foglio e la tastiera aperta in automatico.",
     "media"),
    ("seed-0087", "Pagina wallet on-chain lenta ad aprirsi",
     "Lorenzo: 'usa un linguaggio di programmazione per rendere il sito velocissimo a costo di fare un refactory'. Misurata onchain-app.html dal vivo: Lighthouse 99 da non loggati, main thread 0,4 s, JS leggero. Il tempo se ne andava in giri di rete in fila prima dei dati (HTML, main.js, poi i suoi import, poi /api/auth/me, poi /api/onchain/wallets, solo dopo il saldo), piu' i font Google che bloccavano il primo disegno e la libreria del grafico senza cache.",
     "media"),
    ("seed-0086", "Wallet on-chain: i tasti Strategie, Attività e Impostazioni in alto non rispondono",
     "Segnalato dal progetto 'Onchain app performance e pulsanti': su /onchain-app.html la barra in alto mostra Wallet / Strategie / Attività / Impostazioni, ma cliccare le ultime tre non fa nulla.",
     "media"),
    ("seed-0085", "Fase 1 del trading automatico on-chain: wallet generato sul server, sola lettura",
     "Lorenzo: 'si potrebbe iniziare ad imbastire il sistema per il trading automatico anche su wallet on-chain'. Chiarito con lui: custodia della chiave sul server (non un servizio esterno), nessuna conferma manuale per operazione — l'automazione deve dipendere solo dalla strategia — e wallet 'privacy driven' nel senso di generato da zero da noi, mai legato a un'identita', non tecniche di offuscamento on-chain. Chain scelte: Solana e Robinhood Chain (L2 Arbitrum Orbit di Robinhood, live da luglio 2026, chain id 4663). Questa e' solo la Fase 1 del piano (generazione chiave + saldo, nessuna firma reale) — le fasi successive (simulazione, poi esecuzione vera con tetti/allowlist) restano da fare, apposta.",
     "media"),
    ("seed-0084", "Ticker DEX (on-chain) nel ticker del sito principale, non solo nello Sniper",
     "Lorenzo: 'riusciamo ad ottenere anche i ticker di dex scanner?' — chiarito: non dentro lo Sniper (gia' collegato li'), ma nel campo ticker del grafico/backtest principale. Ricerca per nome/simbolo come i pair CEX, su tutte le chain gia' coperte dallo Sniper.",
     "media"),
    ("seed-0083", "Voce sidebar \"Libreria\" tolta, ridondante col pulsante Indicatori in toolbar",
     "Lorenzo: 'elimina la tab libreria, tanto abbiamo già indicatori in alto'. Il modale della libreria aveva tre punti d'ingresso (voce sidebar, pulsante nella toolbar, pulsante dentro Livelli) — tolta la voce sidebar, che duplicava il pulsante toolbar senza motivo. Restano il pulsante in toolbar (l'ingresso principale) e quello dentro Livelli (contestuale, per chi ha gia' aperto quel pannello).",
     "bassa"),
    ("seed-0082", "Indicatori della libreria: rimozione al passaggio del mouse, nome a grafico, modale con preferiti",
     "Tre richieste di Lorenzo nella stessa serata sullo stesso filone. Prima: 'quando aggiungo indicatori dalla libreria voglio poterli togliere cliccandoci sopra al grafico e rimuovendoli' — poi affinata: 'la rimozione deve avvenire tramite un flag che appare con una x se passo il cursore sugli indicatori, qualunque essi siano a grafico', per non rimuovere per sbaglio con un click diretto. Poi: 'voglio vedere il nome degli indicatori a grafico una volta attivati; voglio poterci entrare e capire come ragionano, ora se li attivo finiscono nel grafico ma non so cosa sono e cosa ho attivo'. Infine, con uno screenshot di TradingView: 'riesci a copiare l'interfaccia [...] PRECISAMENTE UGUALE?' — spiegato che il design esatto di un prodotto di terzi non e' riproducibile (non e' un limite tecnico), ma la struttura funzionale si': modale centrale con colonna categorie e Preferiti invece del disegno esatto.",
     "media"),
    ("seed-0081", "Il grafico apriva già affollato di livelli, per chi li aveva accesi una volta",
     "Lorenzo, con uno screenshot pieno di etichette sovrapposte (pattern, segnali contestuali, MACD, Stocastico): 'sta visualizzazione non ha senso vederla; di predefinito fai che non ci sia nessun indicatore acceso'. Nel codice i default erano gia' quasi tutti spenti (solo EMA era true) — il resto arrivava dalle preferenze salvate sull'account, che ricordano l'ultima combinazione di livelli accesa e la ripropongono ad ogni accesso. Cambiato l'ultimo default rimasto (EMA da acceso a spento): un account nuovo, senza preferenze salvate, parte ora con il solo prezzo. Verificato dal vivo registrando un account pulito. Non risolve da solo la vista di un account che ha gia' salvato dei livelli accesi in passato — quelli restano finche' non li si spegne una volta dai toggle in Livelli, dopodiche' restano spenti.",
     "media"),
    ("seed-0080", "Libreria indicatori: da tendina nascosta a pannello sfogliabile con spiegazioni",
     "Lorenzo, dopo la prima versione (seed-0079): 'voglio una libreria dove visualizzo tutto con spiegazioni, cosi capisco cosa attivare, non conosco i nomi cosi non so cosa cercare'. Scritta una descrizione dedicata per ciascuno dei 151 indicatori (cosa misura, in una riga, non solo il nome tecnico). Poi, guardando lo spazio vuoto nella toolbar in alto: 'sfruttiamo questo spazio evidenziato in giallo, per inserisci un po' di cosine tra cui questa libreria'. Rifatta l'interfaccia: non piu' una tendina che si nasconde finche' non cerchi, ma un pannello ampio (stessa famiglia di Bacheca/Script Pine) sfogliabile per categoria, con due punti d'ingresso nuovi — un pulsante nello spazio vuoto della toolbar e una voce propria in sidebar ('Libreria') — oltre al collegamento gia' esistente dentro Livelli. Un bug trovato verificando dal vivo con Playwright: il pulsante nella toolbar e quello dentro Livelli aprivano il pannello e lo richiudevano nello stesso click, perche' il click originale (non quello sintetico generato per aprire il pannello) risaliva fino al listener globale che chiude i pannelli su un click 'fuori dalla sidebar' — quel listener non riconosceva ne' il bottone ne' il pannello appena aperto come 'dentro'. Risolto con stopPropagation sui due bottoni.",
     "media"),
    ("seed-0079", "Libreria indicatori community (pandas-ta) collegata, con tendina cercabile",
     "Lorenzo aveva chiesto se si potesse accedere a indicatori open source fatti dalla community, come su TradingView. Gli script Pine reali non sono portabili (l'interprete custom del sito copre solo un sottoinsieme del linguaggio), ma pandas-ta era gia' una dipendenza installata e ne usava solo 6 dei 151 disponibili. Collegati tutti e 151, dietro una tendina cercabile in Livelli & Indicatori — 'non voglio affollamento nel grafico, servira' una libreria a tendina da dove selezionarli' — cosi' nessuno si calcola finche' non viene scelto esplicitamente. Ogni indicatore e' classificato overlay (va sul prezzo) o oscillator (apre un riquadro proprio, creato e distrutto dinamicamente). Verificato dal vivo con Playwright: aggiunta/rimozione crea e distrugge il riquadro senza lasciare residui.",
     "media"),
    ("seed-0078", "Idea: arricchire i profili Sniper con API pubbliche (TVL, revenue, audit)",
     "Lorenzo: 'introduciamo anche altri sistemi per scansionare al meglio il mercato, laddove sia disponibile qualche API online pubblica'. Candidati: CoinGecko (cap, volume), DeFiLlama (TVL, revenue per chain), Messari (developer activity), Token Terminal (protocol revenue), API nativa Robinhood Chain se esiste. Non prioritario: sbloccare dopo che lo Sniper e' stabile su Robinhood Chain.",
     "bassa"),
    ("seed-0077", "Alert Telegram: il prezzo mostrato era quello della candela del segnale, senza dire quando",
     "Lorenzo: 'ho ricevuto questo avviso dal bot: INJUSDT [1D] Ingresso long rilevato, Prezzo: 6.285 — ma il prezzo attuale e' 5,43$... inoltre mi sembra strano l'ingresso long dopo una correzione'. Il 6.285 era la chiusura del 14 settembre, consegnata il 16 dopo un -13,5%: il segnale era nato PRIMA della correzione, non dentro. Il messaggio pero' mostrava solo quel prezzo, senza data, quindi un segnale di due giorni prima si leggeva come uno di adesso.",
     "alta"),
    ("seed-0076", "Anteprima ordine futures: prometteva l'importo chiesto, l'ordine ne usava meno",
     "Dal socio di Lorenzo: 'non ha usato la giusta percentuale del portafoglio... 80%, quindi doveva essere 40 dollari ma ne ha usati 34 e qualcosa, come se avesse ordinato con il contract'. Intuizione giusta: su MEXC la dimensione si conta in contratti interi, e un contratto su KAS vale 1000 monete (~34,40 USDT). 40 USDT sono 1,16 contratti, troncati a 1. L'ordine era corretto; a mentire era l'anteprima, che mostrava i 40 chiesti.",
     "media"),
    ("seed-0075", "Nessun modo di chiudere una posizione dal sito, ne' spot ne' futures",
     "Dal socio di Lorenzo, con una posizione MEXC aperta: 'Ma l'opzione per chiudere la posizione non c'e'?'. Le posizioni erano sola lettura e non esisteva nemmeno l'endpoint: close_position c'era, ma lo raggiungeva solo il trading automatico sui segnali di uscita. Chi apriva dal sito poteva solo guardare, e per uscire doveva passare dall'app dell'exchange. Lorenzo: 'la chiusura deve esserci anche per lo spot'.",
     "alta"),
    ("seed-0074", "Un ordine futures riuscito veniva mostrato come 'Errore di rete'",
     "Lorenzo: 'Errore di rete: Can't find variable: loadJournal'. Il messaggio arrivava dal ramo del SUCCESSO: dopo un ordine eseguito, la chiamata a una funzione inesistente (loadJournal, il nome vero e' loadTradingJournal) lanciava un ReferenceError che il catch riscriveva come errore di rete. L'ordine era passato davvero, sullo stesso schermo da cui si rischiava di rifarlo una seconda volta.",
     "alta"),
    ("seed-0073", "Il sito sembra 'AI slop': testo minuscolo, bordi/ombre da template generico",
     "Lorenzo: 'tutto il sito sembra fatto da ai slop'. Scansione con lo strumento impeccable (61 regole deterministiche): 145 problemi, concentrati in pochi pattern sistemici (testo sotto gli 11px funzionali/12px di corpo, bordo colorato spesso su un lato delle card, bordo sottile+ombra larga).",
     "media"),
    ("seed-0072", "Ordine futures MEXC bloccato da un firewall/CDN, letto erroneamente come permesso mancante",
     "Lorenzo: ordine manuale con 50 USDT rifiutato con una pagina HTML 'Access Denied' di Akamai — il codice la leggeva come errore di chiave. Causa probabile: IP europeo del server negato da MEXC su /order/submit per i derivati.",
     "media"),
    ("seed-0071", "Trading automatico: nessun tetto per strategia, e % saldo non funzionava su MEXC",
     "Lorenzo (voce): 'io magari voglio fare 10 ordini da 500 dollari l'uno con il bot, ma se lui pesca con la percentuale e' finita' — la credenziale exchange (size_mode/size_value) e' UNA sola, condivisa da tutte le strategie automatiche che ci operano sopra, quindi non basta a limitare quanto rischia ciascuna. Separatamente: 'voglio usare la % del saldo per gli ordini automatici... pero' sembra non funzionare su mexc'.",
     "media"),
    ("seed-0070", "Ordine futures manuale: nessun modo di piazzare una quantita' di token diretta senza rischiare di confondere USDT e unita'",
     "Lorenzo: 'si rischia dei disastri se uno puo' [inserire] migliaia di dollari dentro e se va a pescare in maniera sbagliata e te li seleziona invece come dollari, come unita' di misura token diventa un delirio... stavo pensando alla possibilita' di fargli fare dall'app direttamente in token, ma e' un casino perche' poi hai un'unita' di misura fissa per tutti... bisognerebbe provare a fargli switchare a lui'.",
     "media"),
    ("seed-0069", "Modalita' Semplice: nessun riferimento al timeframe nello step Backtest/Ottimizza",
     "Lorenzo: 'non trovo il riferimento del timeframe...' — lo step Backtest mostrava solo il ticker, senza dire su quale timeframe la strategia stava lavorando.",
     "bassa"),
    ("seed-0068", "Modalita' Semplice: da archivio il grafico chiede il ticker di nuovo, e nessun collegamento fra un ingresso e l'operazione",
     "Lorenzo: 'se io seleziono una strategia dall'archivio, il ticker e' sottinteso, per cui tu quando carichi il grafico... non e' che devo riselezionare il ticker, vedi che mi chiede il ticker di nuovo? Tu mi devi far vedere il grafico aggiornato per quella strategia con quegli ingressi precisi... e ogni ingresso se ci clicco mi deve rimandare alla transazione effettuata dalla strategia'.",
     "alta"),
    ("seed-0067", "Modalita' Semplice: l'ottimizzazione finisce in errore, log illeggibile, nessun modo di fermarla",
     "Lorenzo: 'la strategia di ottimizzazione da errori alla fine e quindi non funziona, pero c'e' anche questa casella chiamata object che non si sa che cosa vuol dire. Eredita tutta la logica anche grafica che abbiamo creato nel sito per ottimizzazione stabile... Permettimi anche di fermarla se voglio fermarla, perche' vorrei poter cambiare idea'.",
     "alta"),
    ("seed-0066", "Modalita' Semplice: selezionare un ticker sembra non fare niente finche' non arriva il grafico",
     "Lorenzo: 'quando seleziono il ticket il click non produce un'accettazione grafica, ma sembra che non carichi anche se in realta' il ticket e' stato selezionato e poi il grafico arriva... voglio un effetto quando seleziono il ticket che mi faccia capire che sia selezionato'.",
     "bassa"),
    ("seed-0065", "Modalita' Semplice: impossibile testare una chiave exchange senza perderla, e timeframe incoerente fra backtest/ottimizzazione/attivazione",
     "Lorenzo, dopo seed-0064: 'voglio poterle testare, voglio poter capire se queste api funzionano subito... non voglio che siano non salvate. Voglio che il processo sia quello ufficiale, però con un'opzione in più... vuoi testarle subito? ... mi permetti di visualizzare il saldo... e di poter fare un ordine manuale... perché voglio che tu capisca proprio perché tante volte che ti chiedo di sistemare questa cosa dei ticket dello spot e del futures che voglio che non accada più'. Anche: 'devo già aver selezionato i timeframe sulla quale voglio che la strategia lavori' e il riepilogo finale deve mostrarlo.",
     "media"),
    ("seed-0064", "Modalita' Semplice: nessun archivio, grafico non reale, pochi exchange, chiavi da rifare ogni volta",
     "Lorenzo, dopo seed-0062/63: 'vorrei anche che quando sempre in modalita' semplice sia permesso di selezionare la strategia... accedere all'archivio... vedendo tutti i dettagli... esportarli in Excel'; 'il grafico che tu mi mostri nella versione semplificata... deve essere dello stesso tipo di quello raffigurato nel sito originario, le nostre grafiche, non un altro grafico'; 'una volta che uno inserito le API devono sparire... non deve esserci una tab piena di caselle da riempire'; 'ci deve essere tutti gli exchange, non soltanto per i tre'.",
     "media"),
    ("seed-0063", "Modalita' Semplice visibile anche da desktop",
     "Il bottone 'Modalita' Semplice' compariva nella toolbar desktop, non solo nel menu mobile 'Altro' — ma e' pensata solo per il telefono, su desktop il resto dell'app e' gia' raggiungibile per intero.",
     "bassa"),
    ("seed-0062", "Nessun modo di testare una chiave API o vedere il saldo prima di operare",
     "Lorenzo: 'vorrei poter effettuare dei test preliminari di collegamento all'exchange... vorrei anche che fosse visualizzato il saldo una volta collegate le API, prima di poter fare poi le vere operazioni... vorrei poter fare anche operazioni manuali, quindi provare proprio a fare il test'. Chiesta esplicitamente una sezione isolata ('circoscritta'), cosi' un problema li' dentro si sistema in poco tempo senza toccare il resto.",
     "media"),
    ("seed-0061", "Un CDN irraggiungibile (grafico o Script Pine) bloccava silenziosamente tutto il sito, ricerca pair compresa",
     "index.html caricava Lightweight Charts e CodeMirror da unpkg.com; se uno dei due non rispondeva, un'eccezione non gestita nella sequenza di avvio impediva a ogni altro bind (ricerca ticker in Lab, ordini spot/futures, navigazione) di partire — trovato investigando le segnalazioni 54cbf520 e 2a7fd905 sui pair introvabili.",
     "alta"),
    ("seed-0060", "Il grafico cambia dimensione/posizione passando da una tab all'altra",
     "In Analizza il grafico prendeva tutto lo spazio libero, nelle altre aree (Lab, Watchlist, Sorveglia, Livelli) si restringeva a una colonna fissa — il layout 'si scompigliava' a ogni cambio tab invece di restare stabile con solo il pannello laterale che si adegua.",
     "media"),
    ("seed-0059", "Kraken senza aggiornamento in tempo reale, solo ogni 60s",
     "Solo MEXC aveva un feed live via websocket; Binance, KuCoin e Kraken restavano a polling REST ogni 60 secondi (badge 'Agg. ogni 60s'). Kraken ha un feed pubblico websocket v2 gratuito, mai collegato.",
     "media"),
    ("seed-0058", "Kraken: 'Timeframe 1M non supportato' selezionando 1d",
     "Selezionare 1d come intervallo principale sceglie automaticamente 1M come HTF (contesto di lungo periodo) per l'analisi multi-timeframe — Kraken non ha un intervallo mensile nativo nella sua API pubblica e il provider lo segnalava come errore invece di calcolarlo dalle candele giornaliere.",
     "media"),
    ("seed-0057", "Attivare il trading automatico su una strategia non era chiaro: bisognava passare da Opera e scegliere l'exchange fra troppi",
     "In Opera si sceglieva l'exchange fra una lista lunga prima di poter fare qualsiasi cosa, e il trading automatico era un interruttore unico per exchange che valeva per TUTTE le strategie attive li' sopra — nessun modo di dire 'questa strategia solo alert, quest'altra anche ordini reali'.",
     "media"),
    ("seed-0056", "Kraken non era fra gli exchange dati spot, solo un'opzione morta nei menu",
     "Kraken mette a disposizione API pubbliche complete per dati OHLC e ricerca simboli, ma non c'era nessun provider collegato: chi lo selezionava non trovava mai nessun ticker.",
     "bassa"),
    ("seed-0055", "La bacheca (/api/issues) chiedeva login, rompendo la lettura automatica a inizio sessione",
     "CLAUDE.md dice di controllare 'curl -s https://liquidityengine.app/api/issues' prima di ogni conversazione, ma il cancello di autenticazione globale (seed-0031) bloccava quella richiesta con un 401 silenzioso: sembrava 'nessuna segnalazione nuova' invece di 'non ci sono nemmeno arrivato'.",
     "alta"),
    ("seed-0054", "Ricerca Stabile troppo lenta, sceglie configurazioni poco robuste",
     "Gabriele: dopo ~10 minuti sembra bloccarsi su piu' ticker, e spesso sceglie una configurazione che regge solo 1-2 scosse su 14 senza che sia chiaro cosa significhi.",
     "alta"),
    ("seed-0053", "Nessun pair trovato su spot (Binance) e futures (MEXC)",
     "In Opera, scegliendo Binance il campo Pair non suggeriva mai nulla (il backend non interrogava quel provider); sui futures MEXC il campo Pair non aveva alcun autocomplete e un simbolo sconosciuto dava un errore 500 generico invece del messaggio previsto.",
     "alta"),
    ("seed-0052", "Ogni salvataggio da 500 - Permission denied sul volume", "Salvare credenziali, preferenze o preferiti dava Internal Server Error: il volume dati non era scrivibile dall'utente del container.", "alta"),
    ("seed-0051", "Nessun avviso Telegram al deploy", "Dopo un deploy su main non arriva piu' il messaggio Telegram che elenca le modifiche.", "media"),
    ("seed-0050", "Nessun modo di vedere gli errori 500 senza SSH", "Quando qualcosa si rompe davvero sul server, il traceback vive solo nei log del container: nessuno lo vede finche' non lo segnalo io.", "alta"),
    ("seed-0049", "Salvare le credenziali futures a volte non fa nulla", "Dopo un primo tentativo che fallisce, il pulsante Salva nel pannello futures smette di rispondere del tutto: nessun errore, nessuna richiesta.", "alta"),
    ("seed-0040", "Bottone leva sotto la soglia di contrasto", "Il bottone APRI LONG aveva un contrasto di 4,08:1, sotto la soglia AA di 4,5:1 richiesta per il testo.", "media"),
    ("seed-0041", "Pallino LIVE invisibile con animazioni ridotte", "Con 'riduci le animazioni' attivo nel sistema, il pallino che dice se il feed prezzi e' vivo restava fisso acceso.", "media"),
    ("seed-0042", "Prezzi in notazione scientifica nel testo di analisi", "Il riepilogo struttura scriveva prezzi tipo 7.672e+04 invece di un numero leggibile.", "media"),
    ("seed-0043", "Label dei form di trading senza collegamento accessibile", "I campi di Opera (Exchange, Pair, Leva, Passphrase) avevano etichette visive non collegate ai controlli.", "media"),
    ("seed-0044", "Testi e nomi vecchi rimasti dopo il ridisegno", "La tab-bar mobile e alcuni testi dicevano ancora 'Alert' invece di 'Sorveglia'.", "bassa"),
    ("seed-0045", "Watchlist vuota non spiega cosa si puo' fare da li'", "Lo stato vuoto della watchlist non menzionava che da li' si attivano anche alert e ordini automatici.", "bassa"),
    ("seed-0046", "Il gate di regime (VR/z/p/H) non si spiega da solo", "Le sigle del gate di regime comparivano senza spiegazione, mentre Sharpe e PBO nello stesso pannello si' — e VR da solo, senza il p-value, non basta a concludere niente.", "media"),
    ("seed-0047", "Chip Sharpe e Profit factor senza spiegazione", "I due numeri comparivano colorati ma senza dire cosa significano a chi non e' un quant.", "bassa"),
    ("seed-0048", "'% saldo' nell'ordine spot ordina alla cieca", "Scegliendo la taglia come percentuale del saldo, il saldo vero non si vedeva da nessuna parte.", "media"),
    ("seed-0038", "Ordine spot manuale senza conferma",
     "L'ordine spot in Opera partiva al primo click, senza anteprima ne' conferma, a differenza dei futures.",
     "alta"),
    ("seed-0039", "Analizza e Lab non sincronizzati al primo caricamento",
     "La sidebar mostra Analizza attivo ma il pannello a schermo e' quello del Lab, al primo avvio dell'app.",
     "media"),
    ("seed-0037", "Durante un deploy il sito mostra un errore grezzo",
     "Quando c'e' un deploy in corso vorrei che chi si collega veda un avviso invece di un errore, "
     "cosi' non sembra che il sito sia rotto.",
     "media"),
    ("seed-0036", "Il grafico non proietta il prezzo corrente sull'asse",
     "Serve la linea del prezzo attuale che arriva fino all'asse con l'etichetta, come su TradingView, "
     "su ogni grafico.",
     "media"),
    ("seed-0035", "\"Errore di rete\" sull'archivio, senza dire altro",
     "Premendo 'Attiva l'alert' su una voce d'archivio compare 'Errore di rete' e basta: non si capisce "
     "se il server non ha risposto o se ha risposto male.",
     "media"),
    ("seed-0034", "Lo sniper propone meme coin invece di progetti seri",
     "Voglio vedere solo crypto legittime, o quantomeno progetti seri: le meme coin non mi interessano.",
     "alta"),
    ("seed-0032", "Il tema non viaggiava davvero con l'account",
     "Il frontend mandava 'theme' a PUT /api/preferences ma l'allowlist del backend non lo includeva: "
     "il valore veniva scartato in silenzio e il tema restava legato al browser, non all'account.",
     "media"),
    ("seed-0031", "Il sito e' pubblico e le API rispondono a chiunque",
     "Con il trasloco su un dominio pubblico serve verificare che le funzioni pesanti e i dati "
     "non siano raggiungibili senza credenziali.", "alta"),
    ("seed-0033", "La sezione Watchlist non si trovava piu' da desktop",
     "Dopo il ridisegno (seed-0028), 'Sorveglia' nella sidebar apriva solo la tab Alert: la lista dei "
     "ticker rapidi (tab Watchlist, i preferiti da un clic) non aveva piu' nessuna voce di navigazione "
     "su desktop, solo dal menu mobile 'Altro'.", "alta"),
    ("seed-0028", "Ridisegnare il sito: ogni funzione al suo posto",
     "Il prodotto e' cresciuto per innesti e ogni funzione era disegnata bene da sola, ma nessuna "
     "parlava la lingua delle altre. Serve un occhio globale che rimetta in discussione dove sta "
     "ogni cosa, non solo che colore ha.", "alta"),
    ("seed-0029", "Il backtest non dice a che prezzo entra",
     "Non era possibile sapere se una candela viene considerata alla chiusura oppure nel momento in "
     "cui il segnale si verifica. Due rendimenti calcolati con ipotesi diverse non sono confrontabili, "
     "e l'ipotesi non era scritta da nessuna parte.", "alta"),
    ("seed-0030", "Le operazioni eseguite non lasciano traccia sul grafico",
     "Il grafico mostrava cosa la strategia diceva, mai cosa e' successo davvero: guardando la serie "
     "non si poteva rispondere alla domanda \"quella volta sono entrato o no?\". Ogni operazione, "
     "manuale o automatica, deve restare segnata.", "alta"),
    ("seed-0001", "Bug grafico sui trade del backtest", "", "media"),
    ("seed-0002", "Salvare il backtest in database quando si attiva un alert",
     "Una volta attivato l'alert di una strategia bisogna poter accedere al backtesting e salvarlo, "
     "per avere un archivio consultabile delle strategie generate dall'ottimizzazione.", "alta"),
    ("seed-0003", "Strategia Gabriele 2 con movimento short",
     "Da testare e applicare poi sui futures.", "media"),
    ("seed-0004", "Graficare l'imbalance FVG in stile TradingView",
     "Zone d'interesse a barre orizzontali.", "media"),
    ("seed-0005", "Valore RSI sul pallino blu invece che sulla freccia del cursore", "", "bassa"),
    ("seed-0006", "Pulsante per attivare/disattivare modalita' black", "", "bassa"),
    ("seed-0007", "Discrepanza nel numero di trade fra ottimizzazione e manuale",
     "Con gli stessi valori impostati a mano si ottengono risultati simili ma quantita' di trade molto "
     "diverse rispetto alla modalita' automatica. Ogni variabile aggiuntiva usata dalla logica automatica "
     "deve essere parametrizzata e visibile dopo l'ottimizzazione, per rendere il risultato replicabile "
     "a mano e verificabile.", "alta"),
    ("seed-0008", "Venti notifiche Telegram con prezzi disparati dopo aver attivato un alert", "", "alta"),
    ("seed-0009", "Filtri di ottimizzazione su trade in perdita e drawdown",
     "Poter selezionare solo strategie con un minimo/massimo di trade in perdita (compreso 0) "
     "o una percentuale di drawdown (compreso 0%).", "media"),
    ("seed-0010", "Dubbi sui dati non usati in ottimizzazione nel backtest",
     "Verificare che non escluda trade 'a giochi fatti' per gonfiare la performance, e che quei trade "
     "sarebbero davvero stati aperti o chiusi dal bot in tempo reale.", "alta"),
    ("seed-0011", "Il trading automatico non ha mai piazzato un ordine",
     "Trovato lavorando sugli alert, non segnalato: non c'era modo di accorgersene. "
     "Nessun errore, nessun log, semplicemente nessun ordine.", "alta"),
    ("seed-0013", "Il sito non carica piu': resta la schermata vuota",
     "Segnalato con screenshot da telefono: nav e testo iniziale visibili, ma niente funziona.", "alta"),
    ("seed-0014", "La pagina resta vecchia dopo un deploy",
     "Il log dell'ottimizzazione mostrava ancora la versione precedente mentre in produzione c'era gia' quella nuova.", "alta"),
    ("seed-0015", "L'ottimizzazione fallisce con un errore che non parla di ottimizzazione",
     "'The string did not match the expected pattern', e nessun modo di sapere se sta lavorando.", "alta"),
    ("seed-0016", "La ricerca sembra tirare i dadi",
     "Deve capire la strategia e concentrarsi come fa un navigatore, non provare ogni strada.", "alta"),
    ("seed-0017", "La strategia non tiene conto della volatilita' delle coppie poco liquide",
     "Su altcoin che si muovono molto senza un trend vero rende male.", "alta"),
    ("seed-0018", "Se chiudo il browser perdo l'ottimizzazione in corso",
     "Deve continuare, avvisarmi su Telegram alla fine e restare salvata in un archivio.", "alta"),
    ("seed-0019", "Il sito diventa irraggiungibile mentre gira una ricerca",
     "Segnalato dal vivo durante una ricerca stabile.", "alta"),
    ("seed-0020", "L'indicatore non e' allineato al prezzo",
     "Segnalato con screenshot: il pannello sotto il grafico non e' agganciato alle stesse candele.", "alta"),
    ("seed-0022", "Lo stesso account vede il tema chiaro su un computer e scuro su un altro",
     "Gabriele dal suo pc non vede lo sfondo bianco.", "media"),
    ("seed-0023", "Le segnalazioni sono tante e non si trovano",
     "Serve un elenco richiudibile e una ricerca per parole chiave.", "media"),
    ("seed-0024", "Esportare i trade del backtest in Excel",
     "Cliccando sul numero di trade, poter scaricare tutto in un file con i grafici per "
     "riverificare il portafoglio.", "media"),
    ("seed-0025", "Errore 422 quando si avvia la strategia",
     "Premendo per far girare la strategia arriva 'Errore 422' e non parte niente.", "alta"),
    ("seed-0021", "Chiudendo il log non si sa piu' a che punto e' l'ottimizzazione",
     "Serve un indicatore che resti visibile finche' non e' salvata in archivio, e poter lanciare "
     "un'altra ricerca senza aspettare la prima.", "media"),
    ("seed-0012", "Voci della lista iniziale che non comparivano piu' sulla bacheca",
     "Trovato controllando la bacheca dal vivo: seed-0011 non c'era, e la sua risoluzione "
     "restava senza voce a cui agganciarsi.", "media"),
    ("seed-0026", "Visualizzare in modo stilizzato cosa sta facendo la ricerca stabile",
     "Durante la ricerca stabile, un'animazione che mostri graficamente l'equivalente di "
     "quello che l'algoritmo sta facendo — non serve fedele al dettaglio, basta che sia "
     "bella e minimale.", "bassa"),
    ("seed-0027", "Operazioni futures: leva, margine, liquidazione",
     "Introdurre le operazioni futures — completo, accurato e a prova di errore: leva, "
     "margine isolated, liquidazione intrabar, funding. Prima solo in backtest, esecuzione "
     "reale solo dopo validazione, exchange per exchange.", "media"),
]


def _seed() -> None:
    """Aggiunge le voci della lista iniziale che mancano, una per una.

    Gli id sono fissi e non generati: le risoluzioni scritte da Claude si
    agganciano per id, e un id casuale al primo avvio scollegherebbe le
    diagnosi gia' scritte da queste voci.

    Il controllo e' per id, non "l'elenco e' vuoto". Con quest'ultimo, una voce
    aggiunta alla lista dopo il primo avvio non compariva mai piu': il file sul
    volume esisteva gia', quindi il seeding usciva subito. E' successo con
    seed-0011, che dal vivo non c'era mentre la sua risoluzione, scritta e
    distribuita, restava senza voce a cui agganciarsi.

    Una voce cancellata a mano resta cancellata: `seeded_ids.json` ricorda cosa
    e' gia' stato inserito, cosi' "mai vista" e "vista e buttata" non si
    confondono.
    """
    now = int(time.time())
    have = {it.get("id") for it in _issues}
    added = False
    for i, (iid, title, detail, prio) in enumerate(_SEED):
        if iid in have or iid in _seeded_ids:
            _seeded_ids.add(iid)
            continue
        _issues.append({
            "id": iid, "title": title, "detail": detail, "priority": prio,
            "status": "aperto", "author": "lista iniziale",
            "created_at": now - (len(_SEED) - i),
        })
        _seeded_ids.add(iid)
        added = True
    if added:
        _save()
    _save_seeded()


_load()
_load_seeded()
_load_replies()
_seed()


def list_issues() -> list[dict]:
    """Segnalazioni con la risoluzione agganciata, le più recenti per prime."""
    res = _resolutions()
    mine = _claude_replies()
    out = []
    for it in _issues:
        merged = dict(it)
        r = res.get(it["id"])
        if r:
            merged["resolution"] = r
            # La risoluzione è la fonte di verità sullo stato: se Claude l'ha
            # segnata risolta, l'elenco non deve continuare a mostrarla aperta
            # solo perché nessuno ha aggiornato il campo a mano.
            if r.get("status") in _VALID_STATUS:
                merged["status"] = r["status"]
        # …tranne quando chi l'ha scritta dice che il problema si vede ancora.
        # Una risoluzione senza data si considera piu' vecchia di qualsiasi
        # riapertura: chiudere per decreto una voce riaperta sarebbe il modo
        # piu' veloce di rendere inutile la bacheca.
        reopened = int(it.get("reopened_at", 0) or 0)
        if reopened and reopened > int((r or {}).get("at", 0) or 0):
            merged["status"] = "riaperto"
        # Uno stato messo a mano dalla bacheca vince su cio' che e' venuto
        # prima (risoluzione o riapertura): senza, "Close manually" su una
        # voce riaperta tornava "riaperto" al giro dopo (segnalazione 1f8f7246).
        set_at = int(it.get("status_at", 0) or 0)
        if set_at and set_at > reopened and set_at >= int((r or {}).get("at", 0) or 0):
            merged["status"] = it["status"]
        thread = [dict(x, side="loro") for x in _replies if x.get("issue_id") == it["id"]]
        thread += [dict(x, side="claude") for x in mine.get(it["id"], [])]
        merged["replies"] = sorted(thread, key=lambda x: x.get("created_at", 0))
        out.append(merged)
    return sorted(out, key=lambda x: x.get("created_at", 0), reverse=True)


def add_issue(title: str, detail: str = "", priority: str = "media",
              author: str = "") -> dict:
    title = (title or "").strip()
    if not title:
        raise ValueError("Titolo mancante")
    entry = {
        "id": uuid.uuid4().hex[:8],
        "title": title[:300],
        "detail": (detail or "").strip()[:4000],
        "priority": priority if priority in _VALID_PRIORITY else "media",
        "status": "aperto",
        "author": (author or "").strip()[:120],
        "created_at": int(time.time()),
    }
    _issues.append(entry)
    if len(_issues) > _MAX_ISSUES:
        del _issues[: len(_issues) - _MAX_ISSUES]
    _save()
    return entry


def update_issue(issue_id: str, *, status: str | None = None,
                 priority: str | None = None, detail: str | None = None) -> dict | None:
    for it in _issues:
        if it["id"] != issue_id:
            continue
        if status is not None:
            if status not in _VALID_STATUS:
                raise ValueError(f"Stato non valido: {status}")
            it["status"] = status
            it["status_at"] = int(time.time())
            # list_issues() rilegge lo stato dalla risoluzione quando ce n'e'
            # una: senza segnare anche qui la riapertura, un "Riapri" manuale
            # spariva al giro dopo perche' la vecchia risoluzione "risolto"
            # tornava a vincere sul merge.
            if status in ("aperto", "riaperto"):
                it["reopened_at"] = int(time.time())
        if priority is not None:
            if priority not in _VALID_PRIORITY:
                raise ValueError(f"Priorità non valida: {priority}")
            it["priority"] = priority
        if detail is not None:
            it["detail"] = detail.strip()[:4000]
        _save()
        return it
    return None


def delete_issue(issue_id: str) -> bool:
    for i, it in enumerate(_issues):
        if it["id"] == issue_id:
            del _issues[i]
            _save()
            return True
    return False

