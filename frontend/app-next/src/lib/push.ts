import * as api from "./api";

// A finished re-check or scan sends a push (bg.js): the service worker at the
// site root shows it and reopens the app where the task started.
if ("serviceWorker" in navigator) navigator.serviceWorker.register("/sw.js").catch(() => {});

let subscribed = false;
const b64u = (s: string) => Uint8Array.from(atob(s.replace(/-/g, "+").replace(/_/g, "/") + "=".repeat((4 - (s.length % 4)) % 4)), (c) => c.charCodeAt(0));

async function subscribe() {
  if (subscribed || !("serviceWorker" in navigator) || !("PushManager" in window)) return;
  try {
    const reg = await navigator.serviceWorker.ready;
    let sub = await reg.pushManager.getSubscription();
    if (!sub) sub = await reg.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: b64u((await api.getPushKey()).key) });
    await api.pushSubscribe(sub.toJSON());
    subscribed = true;
  } catch { /* refused: the task still finishes and shows on return */ }
}

/** Call straight from the tap that launches a task: Safari asks only inside a gesture. */
export function askPush() {
  if (!("Notification" in window) || !("PushManager" in window)) return;
  if (Notification.permission === "granted") subscribe();
  else if (Notification.permission === "default") Notification.requestPermission().then((p) => { if (p === "granted") subscribe(); }, () => {});
}
