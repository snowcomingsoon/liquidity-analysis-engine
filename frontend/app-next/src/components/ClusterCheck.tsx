import { useState } from "react";
import * as api from "../lib/api";
import type { Gem } from "../lib/types";

export const ADDRESS = /^(0x[0-9a-fA-F]{40}|[1-9A-HJ-NP-Za-km-z]{32,48})$/;
const EVM = [["robinhood", "Robinhood"], ["ethereum", "Ethereum"], ["base", "Base"], ["bsc", "BSC"]] as const;

/** A pasted address: check its wallet clusters now (Lorenzo, 22/10:
 *  "indirizzo manuale per verificare un token a richiesta"). One big
 *  button starts it ("manca il tasto chiaro [...] per avviare l'attività");
 *  the chain is read from the address, a 0x one picks it on chips. */
export function ClusterCheck({ address, onOpen, onStart, onFail }: { address: string; onOpen: (e: Gem) => void; onStart?: (chain: string) => void; onFail?: () => void }) {
  const ok = ADDRESS.test(address);
  const sol = ok && !address.startsWith("0x");
  const [pick, setPick] = useState("robinhood");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");
  const chain = sol ? "solana" : pick;
  const go = async () => {
    if (!ok || busy) return;
    setBusy(true); setMsg("");
    onStart?.(chain);
    try {
      const r = await api.askClusterCheck(chain, address);
      onOpen({ chain, token_address: address, symbol: `${address.slice(0, 4)}…${address.slice(-4)}` } as Gem);
      if (r.error) setMsg(r.error);
    } catch (e) {
      setMsg((e as Error).message || "Not started, try again.");
      onFail?.();
    } finally { setBusy(false); }
  };
  return (
    <div className="rounded-[16px] bg-card p-4">
      <div className="flex items-baseline gap-2">
        <b className="flex-1 text-[15px] font-semibold">Check wallet clusters</b>
        {ok && <small className="text-[12.5px] text-text-3">{sol ? "Detected: Solana" : "Pick the chain"}</small>}
      </div>
      <small className="mt-0.5 block text-[13px] text-text-3">Who holds this token together, and whether they sell together.</small>
      {ok && !sol && (
        <div className="mt-3 flex flex-wrap gap-1.5" role="radiogroup" aria-label="Chain">
          {EVM.map(([k, label]) => (
            <button key={k} type="button" role="radio" aria-checked={pick === k} onClick={() => setPick(k)}
              className={`h-8 rounded-full px-3 text-[13px] ${pick === k ? "bg-pill font-semibold text-ink shadow-[inset_0_0_0_1.5px_var(--c-ink)]" : "bg-pill text-text-2"}`}>{label}</button>
          ))}
        </div>
      )}
      <button type="button" disabled={!ok || busy} onClick={go}
        className="mt-3 flex h-12 w-full items-center justify-center gap-2 rounded-full bg-ink text-[15.5px] font-semibold text-on-ink transition-opacity disabled:opacity-40">
        <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
          <circle cx="7" cy="8" r="3" /><circle cx="17" cy="7" r="2.2" /><circle cx="14" cy="17" r="3.5" /><path d="m9.6 9.6 2.3 4.4M9.9 7.7l4.9-.5M16.6 9.2l-1.6 4.3" />
        </svg>
        {busy ? "Starting…" : ok ? `Start cluster check · ${sol ? "Solana" : EVM.find(([k]) => k === pick)![1]}` : "Start cluster check"}
      </button>
      {!ok && address && <p className="mt-2 text-[13px] text-down">Not a token address: 0x… (40 characters) or a Solana mint.</p>}
      {!address && <p className="mt-2 text-[13px] text-text-3">Paste a token address above.</p>}
      {msg && <p className="mt-2 text-[13px] text-down">{msg}</p>}
    </div>
  );
}
