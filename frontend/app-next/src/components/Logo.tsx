import { useState } from "react";

const DS_CHAIN: Record<string, string> = { solana: "solana", robinhood: "robinhood", base: "base", bsc: "bsc", ethereum: "ethereum", arc: "arc" };
const MARK: Record<string, { d: string; fill?: string; stroke?: string }> = {
  solana: { d: "M5 16.5h12.5l2-2H7zM5 7.5h12.5l2 2H7zM5 12h12.5l2-2H7", stroke: "#14f195" },
  robinhood: { d: "M12 3 20 12 12 21 4 12z", stroke: "#c8f169" },
  base: { d: "M8.5 5h7A3.5 3.5 0 0 1 19 8.5v7a3.5 3.5 0 0 1-3.5 3.5h-7A3.5 3.5 0 0 1 5 15.5v-7A3.5 3.5 0 0 1 8.5 5z", fill: "#3c8aff" },
  bsc: { d: "M12 3.5 15 6.5 12 9.5 9 6.5zM12 14.5l3 3-3 3-3-3zM6.5 9l3 3-3 3-3-3zM17.5 9l3 3-3 3-3-3zM12 9.5l2.5 2.5-2.5 2.5L9.5 12z", fill: "#f0b90b" },
  ethereum: { d: "M12 2.5 6 12.2 12 16l6-3.8zM6 13.6l6 8 6-8-6 3.8z", fill: "#a5b4fc" },
  arc: { d: "M4 19a8 8 0 0 1 16 0h-3.5a4.5 4.5 0 0 0-9 0z", stroke: "currentColor" },
};

/** The token picture, or a rounded square with its initial (direction A). */
export function Tile({ symbol, image, chain, token, className = "" }: { symbol?: string; image?: string; chain?: string; token?: string; className?: string }) {
  const [broken, setBroken] = useState(false);
  const seed = String(token || symbol || "?");
  const h = [...seed].reduce((a, c) => (a * 33 + c.charCodeAt(0)) >>> 0, 5381);
  const addr = token && token.startsWith("0x") ? token.toLowerCase() : token;
  const src = image || (addr && chain && DS_CHAIN[chain] ? `https://dd.dexscreener.com/ds-data/tokens/${DS_CHAIN[chain]}/${addr}.png` : "");
  const style = { "--h1": h % 360, "--h2": (h >> 9) % 360, "--rot": `${(h >> 5) % 360}deg` } as React.CSSProperties;
  return (
    <span className={`tile ${className}`} style={style} data-shape={(h >> 3) % 4}>
      <b className="letter" aria-hidden="true">{String(symbol || "?").replace(/^\$/, "").charAt(0).toUpperCase()}</b>
      {src && !broken && <img src={src} alt="" loading="lazy" decoding="async" referrerPolicy="no-referrer" onError={() => setBroken(true)} />}
    </span>
  );
}

export function Logo({ size = 52, ...t }: { size?: number; symbol?: string; image?: string; chain?: string; token?: string }) {
  const m = t.chain ? MARK[t.chain] : undefined;
  return (
    <span className="relative block flex-none" style={{ width: size, height: size }}>
      <Tile {...t} />
      {m && size >= 48 && (
        <i className="absolute -bottom-1 -right-1 grid h-5 w-5 place-items-center rounded-full bg-pill not-italic shadow-[0_0_0_2px_var(--c-bg)]">
          <svg viewBox="0 0 24 24" className="h-[13px] w-[13px]" aria-hidden="true" fill={m.fill ?? "none"} stroke={m.stroke ?? "none"} strokeWidth={2.2} strokeLinecap="round" strokeLinejoin="round"><path d={m.d} /></svg>
        </i>
      )}
    </span>
  );
}
