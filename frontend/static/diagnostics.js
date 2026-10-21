// Diagnosi — sezione isolata apposta, come chiesto esplicitamente: test di
// collegamento a un exchange (spot o futures), saldo/margine mostrato prima
// di fidarsi delle chiavi, e un ordine di prova minimo. Nessuna dipendenza
// da app.js oltre a leggere lo stato di login gia' esposto sul DOM — se
// qualcosa qui dentro si rompe, la riparazione resta in questo file solo.
// Endpoint backend: POST /api/diagnostics/test-connection (backend/app/
// diagnostics.py, isolato per lo stesso motivo) + gli endpoint di ordine
// manuale gia' esistenti e in uso altrove (/api/trading/order).
(function () {
  "use strict";

  const root = document.getElementById("diagnosi-root");
  const navBtn = document.getElementById("sidenav-diagnosi");
  if (!root || !navBtn) return;

  const SPOT_EXCHANGES = [
    { id: "mexc", name: "MEXC" },
    { id: "binance", name: "Binance" },
    { id: "kucoin", name: "KuCoin", needsPassphrase: true },
    { id: "kraken", name: "Kraken" },
    { id: "coinbase", name: "Coinbase" },
    { id: "bitstamp", name: "Bitstamp" },
  ];

  const state = {
    open: false,
    market: "spot", // "spot" | "futures"
    exchange: "mexc",
    futuresExchanges: null, // caricato da /api/auth/futures al primo uso
  };

  async function api(path, opts) {
    const resp = await fetch(path, Object.assign({ headers: { "Content-Type": "application/json" } }, opts || {}));
    if (resp.status === 401) {
      const err = new Error("Sign in to use Diagnostics.");
      err.needsAuth = true;
      throw err;
    }
    let body = null;
    try { body = await resp.json(); } catch (_e) { /* nessun corpo */ }
    if (!resp.ok) throw new Error((body && body.detail) ? body.detail : `Error ${resp.status}`);
    return body;
  }

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  }

  async function ensureFuturesExchanges() {
    if (state.futuresExchanges) return state.futuresExchanges;
    try {
      state.futuresExchanges = await api("/api/auth/futures");
    } catch (_e) {
      state.futuresExchanges = [];
    }
    return state.futuresExchanges;
  }

  function open() {
    state.open = true;
    root.classList.remove("hidden");
    render();
  }

  function close() {
    state.open = false;
    root.classList.add("hidden");
  }

  navBtn.addEventListener("click", () => { state.open ? close() : open(); });

  async function render() {
    const isFutures = state.market === "futures";
    const futuresList = isFutures ? await ensureFuturesExchanges() : [];
    const exchangeOptions = isFutures
      ? futuresList.map((f) => `<option value="${esc(f.exchange)}" ${f.exchange === state.exchange ? "selected" : ""}>${esc(f.name)}</option>`).join("")
      : SPOT_EXCHANGES.map((e) => `<option value="${esc(e.id)}" ${e.id === state.exchange ? "selected" : ""}>${esc(e.name)}</option>`).join("");
    const currentSpot = SPOT_EXCHANGES.find((e) => e.id === state.exchange);
    const currentFutures = futuresList.find((f) => f.exchange === state.exchange);
    const needsPass = isFutures ? !!(currentFutures && currentFutures.needs_passphrase) : !!(currentSpot && currentSpot.needsPassphrase);

    root.innerHTML = `
      <div class="diag-overlay">
        <div class="diag-panel">
          <div class="diag-head">
            <h2>Diagnostics <span class="risk-badge">real money</span></h2>
            <button type="button" class="diag-close" id="diag-close-btn" title="Close">✕</button>
          </div>
          <p class="panel-hint">Test a key before you trust it: this only reads the balance and never places an order unless you explicitly press "Execute" below. Saved keys stay the ones in Trading — this section never creates new ones.</p>

          <div class="diag-mode-row">
            <button type="button" class="wl-mode-btn ${!isFutures ? "active" : ""}" id="diag-mode-spot">Spot</button>
            <button type="button" class="wl-mode-btn wl-mode-danger ${isFutures ? "active" : ""}" id="diag-mode-futures">Futures</button>
          </div>

          <div class="diag-section">
            <div class="section-title-row"><span class="section-eyebrow">1 · Connection test</span></div>
            <div class="mo-row">
              <div class="mo-field">
                <label class="mo-label" for="diag-exchange">Exchange</label>
                <select id="diag-exchange" class="mo-select">${exchangeOptions}</select>
              </div>
            </div>
            <p class="panel-hint">Leave the fields empty to test the saved key, or paste a new one below just for the test — it is not saved.</p>
            <div class="mo-row">
              <input type="text" id="diag-api-key" class="mo-input" placeholder="API Key (optional)" autocomplete="off" />
              <input type="password" id="diag-api-secret" class="mo-input" placeholder="API Secret (optional)" autocomplete="off" />
            </div>
            ${needsPass ? `<div class="mo-row"><input type="password" id="diag-passphrase" class="mo-input" placeholder="Passphrase" autocomplete="off" /></div>` : ""}
            <button type="button" class="wl-activate-btn" id="diag-test-btn">Test connection</button>
            <div id="diag-test-result"></div>
          </div>

          <div class="diag-section" id="diag-order-section">
            <div class="section-title-row"><span class="section-eyebrow">2 · Test order (spot only)</span></div>
            <p class="panel-hint">${isFutures
              ? "For futures use the full form in Trading — leverage and margin need the liquidation preview, which is deliberately not reproduced here."
              : "Requires a key already saved and enabled in Trading (the key tested on the fly above is not enough)."}</p>
            ${isFutures ? "" : `
            <div class="mo-row">
              <div class="mo-field mo-field-grow">
                <label class="mo-label" for="diag-order-symbol">Pair</label>
                <input type="text" id="diag-order-symbol" class="mo-input" placeholder="e.g. BTCUSDT" autocomplete="off" />
              </div>
            </div>
            <div class="mo-side-tabs">
              <button type="button" class="mo-side-tab mo-buy-tab mo-tab-active" data-diag-side="BUY">BUY</button>
              <button type="button" class="mo-side-tab mo-sell-tab" data-diag-side="SELL">SELL</button>
            </div>
            <div class="mo-row">
              <div class="mo-field">
                <label class="mo-label" for="diag-order-usdt">USDT (fixed)</label>
                <input type="number" id="diag-order-usdt" class="mo-input" value="10" min="1" step="1" />
              </div>
            </div>
            <label class="futures-confirm">
              <input type="checkbox" id="diag-order-confirm" />
              <span>I confirm: real money, test order on <b id="diag-order-confirm-text">${esc(state.exchange)}</b></span>
            </label>
            <button type="button" class="mo-execute-btn mo-execute-buy" id="diag-order-btn" disabled>EXECUTE TEST ORDER</button>
            <div id="diag-order-result"></div>
            `}
          </div>

          <div id="diag-service-keys"></div>
        </div>
      </div>
    `;
    bind();
    fillServiceKeys();
  }

  // Keys of outside services (backend/app/service_keys.py), admins only: the
  // section stays empty for anyone else (403). Lorenzo, 20/10: the Groq key
  // could reach the server from his phone only through the site.
  const SERVICES = [
    { id: "groq", name: "Groq", hint: "Free key from console.groq.com/keys — checks the gems before they enter the Top." },
    { id: "gemini", name: "Gemini", hint: "Free key from aistudio.google.com/apikey — the backup when Groq does not answer." },
    { id: "github", name: "GitHub Models", hint: "Free token from github.com/settings/tokens (fine-grained, permission Models: read) — the reserve after Gemini." },
  ];

  async function fillServiceKeys(message) {
    const box = document.getElementById("diag-service-keys");
    if (!box) return;
    let st;
    try { st = await api("/api/admin/service-keys"); } catch (_e) { box.innerHTML = ""; return; }
    box.innerHTML = `
      <div class="diag-section">
        <div class="section-title-row"><span class="section-eyebrow">3 · Service keys (admins)</span></div>
        <p class="panel-hint">Saved encrypted on the server, never in the code. Only the last 4 characters are shown.</p>
        ${SERVICES.map((sv) => {
          const x = st[sv.id] || {};
          const now = x.set
            ? `<p class="diag-ok">✓ ${esc(sv.name)} key set (…${esc(x.last4)})${x.source === "env" ? " — from the server's .env" : ""}</p>`
            : `<p class="panel-hint">No ${esc(sv.name)} key yet.</p>`;
          return `${now}<p class="panel-hint">${esc(sv.hint)}</p>
            <div class="mo-row"><input type="password" id="diag-sk-${sv.id}" class="mo-input" placeholder="${esc(sv.name)} API key" autocomplete="off" /></div>
            <button type="button" class="wl-activate-btn" data-sk-save="${sv.id}">Check and save</button>
            ${x.set && x.source === "site" ? `<button type="button" class="btn-quiet" data-sk-clear="${sv.id}">Remove</button>` : ""}`;
        }).join("")}
        <div id="diag-sk-result">${message || ""}</div>
      </div>`;
    box.querySelectorAll("[data-sk-save]").forEach((btn) => btn.addEventListener("click", async () => {
      const id = btn.dataset.skSave;
      const value = document.getElementById(`diag-sk-${id}`).value.trim();
      const out = document.getElementById("diag-sk-result");
      if (!value) { out.innerHTML = `<p class="diag-error">Paste the key first.</p>`; return; }
      btn.disabled = true;
      out.innerHTML = `<p class="panel-hint">Checking the key with the service…</p>`;
      try {
        await api("/api/admin/service-keys", { method: "POST", body: JSON.stringify({ name: id, value }) });
        fillServiceKeys(`<p class="diag-ok">✓ Key accepted and saved.</p>`);
      } catch (err) {
        out.innerHTML = `<p class="diag-error">✕ ${esc(err.message)}</p>`;
        btn.disabled = false;
      }
    }));
    box.querySelectorAll("[data-sk-clear]").forEach((btn) => btn.addEventListener("click", async () => {
      try {
        await api("/api/admin/service-keys", { method: "POST", body: JSON.stringify({ name: btn.dataset.skClear, value: "" }) });
        fillServiceKeys(`<p class="panel-hint">Key removed.</p>`);
      } catch (err) {
        document.getElementById("diag-sk-result").innerHTML = `<p class="diag-error">✕ ${esc(err.message)}</p>`;
      }
    }));
  }

  let orderSide = "BUY";

  function bind() {
    document.getElementById("diag-close-btn").addEventListener("click", close);
    document.getElementById("diag-mode-spot").addEventListener("click", () => { state.market = "spot"; render(); });
    document.getElementById("diag-mode-futures").addEventListener("click", () => { state.market = "futures"; render(); });
    document.getElementById("diag-exchange").addEventListener("change", (e) => { state.exchange = e.target.value; render(); });

    document.getElementById("diag-test-btn").addEventListener("click", async () => {
      const btn = document.getElementById("diag-test-btn");
      const out = document.getElementById("diag-test-result");
      btn.disabled = true;
      out.innerHTML = `<p class="panel-hint">Checking…</p>`;
      try {
        const res = await api("/api/diagnostics/test-connection", {
          method: "POST",
          body: JSON.stringify({
            exchange: state.exchange,
            market: state.market,
            api_key: document.getElementById("diag-api-key").value.trim(),
            api_secret: document.getElementById("diag-api-secret").value.trim(),
            passphrase: document.getElementById("diag-passphrase")?.value.trim() || "",
          }),
        });
        if (!res.ok) {
          out.innerHTML = `<p class="diag-error">✕ ${esc(res.error)}</p>`;
        } else if (res.market === "futures") {
          out.innerHTML = `<p class="diag-ok">✓ Connected — available margin: <b>${res.margin_usdt.toFixed(2)} USDT</b></p>`;
        } else {
          const rows = (res.balances || []);
          out.innerHTML = rows.length
            ? `<p class="diag-ok">✓ Connected — balance:</p><ul class="diag-balances">${rows.map((b) => `<li><span>${esc(b.asset)}</span><span>${b.free.toLocaleString("en-US", { maximumFractionDigits: 8 })}</span></li>`).join("")}</ul>`
            : `<p class="diag-ok">✓ Connected — no positive balance on this account.</p>`;
        }
      } catch (err) {
        if (err.needsAuth) { document.getElementById("auth-toggle-btn")?.click(); return; }
        out.innerHTML = `<p class="diag-error">✕ ${esc(err.message)}</p>`;
      } finally {
        btn.disabled = false;
      }
    });

    const symbolInput = document.getElementById("diag-order-symbol");
    if (!symbolInput) return; // futures: sezione ordine non renderizzata

    document.querySelectorAll("[data-diag-side]").forEach((tab) => {
      tab.addEventListener("click", () => {
        orderSide = tab.dataset.diagSide;
        document.querySelectorAll("[data-diag-side]").forEach((t) => t.classList.toggle("mo-tab-active", t === tab));
        const execBtn = document.getElementById("diag-order-btn");
        execBtn.textContent = `EXECUTE TEST ORDER (${orderSide})`;
        execBtn.classList.toggle("mo-execute-buy", orderSide === "BUY");
        execBtn.classList.toggle("mo-execute-sell", orderSide === "SELL");
      });
    });

    const confirmBox = document.getElementById("diag-order-confirm");
    const execBtn = document.getElementById("diag-order-btn");
    confirmBox.addEventListener("change", () => { execBtn.disabled = !confirmBox.checked; });

    execBtn.addEventListener("click", async () => {
      const out = document.getElementById("diag-order-result");
      const symbol = symbolInput.value.trim().toUpperCase();
      if (!symbol) { out.innerHTML = `<p class="diag-error">Missing pair</p>`; return; }
      execBtn.disabled = true;
      out.innerHTML = `<p class="panel-hint">Sending…</p>`;
      try {
        const res = await api("/api/trading/order", {
          method: "POST",
          body: JSON.stringify({
            exchange: state.exchange, symbol, side: orderSide,
            size_mode: "fixed_usdt",
            size_value: parseFloat(document.getElementById("diag-order-usdt").value) || 0,
          }),
        });
        out.innerHTML = `<p class="diag-ok">✓ Order sent — see the order log in Trading for details.</p>`;
        confirmBox.checked = false;
      } catch (err) {
        if (err.needsAuth) { document.getElementById("auth-toggle-btn")?.click(); return; }
        out.innerHTML = `<p class="diag-error">✕ ${esc(err.message)}</p>`;
      } finally {
        execBtn.disabled = !confirmBox.checked;
      }
    });
  }
})();
