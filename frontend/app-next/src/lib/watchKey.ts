/** The watchlist lives on the phone, one per account (Lorenzo 22/10: whitekobra's
 *  and his own are different). The old shared list stays with the main app variant. */
export const WATCH_KEY = (() => {
  try {
    const b = JSON.parse(document.getElementById("onchain-boot")?.textContent ?? "{}");
    const id = String(b.user?.id ?? "");
    if (!id) return "watchlist-v1";
    const key = `watchlist-v1:${id}`;
    const old = localStorage.getItem("watchlist-v1");
    if (old != null && localStorage.getItem(key) == null && b.app_variant !== "v1") localStorage.setItem(key, old);
    return key;
  } catch { return "watchlist-v1"; }
})();
