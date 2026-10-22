import { useState } from "react";
import * as api from "../lib/api";
import type { Gem } from "../lib/types";

const EVM = [["robinhood", "Robinhood"], ["ethereum", "Ethereum"], ["base", "Base"], ["bsc", "BSC"]] as const;

/** A pasted address: check its wallet clusters now (Lorenzo, 22/10:
 *  "indirizzo manuale per verificare un token a richiesta"). The check goes
 *  first in line and the token page opens on its status, then on the map. */
export function ClusterCheck({ address, onOpen, onStart, onFail }: { address: string; onOpen: (e: Gem) => void; onStart?: (chain: string) => void; onFail?: () => void }) {
  const sol = !address.startsWith("0x");
  const [busy, setBusy] = useState<string | null>(null);
  const [msg, setMsg] = useState("");
  const go = async (chain: string) => {
    setBusy(chain); setMsg("");
    onStart?.(chain);
    try {
      const r = await api.askClusterCheck(chain, address);
      onOpen({ chain, token_address: address, symbol: `${address.slice(0, 4)}…${address.slice(-4)}` } as Gem);
      if (r.error) setMsg(r.error);
    } catch (e) {
      setMsg((e as Error).message || "Not started, try again.");
      onFail?.();
    } finally { setBusy(null); }
  };
  const chains = sol ? [["solana", "Solana"]] as const : EVM;
  return (
    <div className="rounded-[16px] bg-card p-4">
      <b className="block text-[15px] font-semibold">Check wallet clusters</b>
      <small className="mt-0.5 block text-[13px] text-text-3">Who holds this token together, and whether they sell together. {sol ? "" : "Pick its chain."}</small>
      <div className="mt-3 flex flex-wrap gap-1.5">
        {chains.map(([k, label]) => (
          <button key={k} type="button" disabled={busy != null} onClick={() => go(k)}
            className="h-9 rounded-full bg-ink px-3.5 text-[13.5px] font-semibold text-on-ink disabled:opacity-50">{busy === k ? "Starting…" : label}</button>
        ))}
      </div>
      {msg && <p className="mt-2 text-[13px] text-down">{msg}</p>}
    </div>
  );
}
