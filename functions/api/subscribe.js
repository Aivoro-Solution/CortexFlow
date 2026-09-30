/* CortexFlow newsletter subscribe API (Cloudflare Pages Function).
 * POST /api/subscribe  -> {email} JSON or form-encoded. Stores in KV.
 * GET  /api/subscribe?op=unsubscribe&email=..&t=.. -> removes subscription.
 * KV binding: NEWSLETTER_KV
 */

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;

function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "content-type": "application/json; charset=utf-8" },
  });
}

function page(title, bodyHtml, ok) {
  return new Response(
    `<!doctype html><html lang="en"><head><meta charset="utf-8">` +
      `<meta name="viewport" content="width=device-width,initial-scale=1">` +
      `<title>${title} — CortexFlow</title>` +
      `<style>body{font-family:ui-monospace,Menlo,Consolas,monospace;max-width:640px;margin:4rem auto;padding:0 1.5rem;color:#16181D}` +
      `.box{border:2px solid #16181D;padding:2rem}` +
      `h1{font-size:1.2rem;margin:0 0 1rem}` +
      `a{color:#FF4D00}.ok{color:#0a7a3d}.err{color:#b00020}</style></head>` +
      `<body><div class="box"><h1 class="${ok ? "ok" : "err"}">${title}</h1>` +
      `<p>${bodyHtml}</p><p><a href="/">Back to CortexFlow</a></p></div></body></html>`,
    { status: ok ? 200 : 400, headers: { "content-type": "text/html; charset=utf-8" } }
  );
}

async function sha256hex(str) {
  const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(str));
  return [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

function randomHex(n) {
  const b = new Uint8Array(n);
  crypto.getRandomValues(b);
  return [...b].map((x) => x.toString(16).padStart(2, "0")).join("");
}

export async function onRequestPost(context) {
  const { request, env } = context;
  const kv = env.NEWSLETTER_KV;
  if (!kv) return json({ ok: false, error: "Newsletter storage is not configured yet." }, 500);

  const ct = request.headers.get("content-type") || "";
  const wantsHtml = !ct.includes("application/json");
  let email = "", honeypot = "", source = "";
  try {
    if (ct.includes("application/json")) {
      const body = await request.json();
      email = String(body.email || "").trim().toLowerCase();
      honeypot = String(body.website || "");
      source = String(body.source || "").slice(0, 64);
    } else {
      const form = await request.formData();
      email = String(form.get("email") || "").trim().toLowerCase();
      honeypot = String(form.get("website") || "");
      source = String(form.get("source") || "").slice(0, 64);
    }
  } catch {
    return wantsHtml
      ? page("Something went wrong", "The request could not be read. Please try again.", false)
      : json({ ok: false, error: "Invalid request." }, 400);
  }

  // Honeypot field: bots fill it; pretend success.
  if (honeypot) {
    return wantsHtml
      ? page("Subscribed", "Please check your inbox to confirm.", true)
      : json({ ok: true });
  }

  if (!EMAIL_RE.test(email) || email.length > 254) {
    return wantsHtml
      ? page("Invalid email", "Please go back and enter a valid email address.", false)
      : json({ ok: false, error: "Please enter a valid email address." }, 400);
  }

  // Rate limit: 10 attempts per IP per hour.
  const ip = request.headers.get("cf-connecting-ip") || "unknown";
  const rlKey = "rl:" + ip;
  const count = parseInt((await kv.get(rlKey)) || "0", 10);
  if (count >= 10) {
    return wantsHtml
      ? page("Too many attempts", "Please try again later.", false)
      : json({ ok: false, error: "Too many attempts. Try again later." }, 429);
  }
  await kv.put(rlKey, String(count + 1), { expirationTtl: 3600 });

  const id = await sha256hex("cortexflow-nl:" + email);
  const key = "sub:" + id;
  const prev = await kv.get(key);
  let token = randomHex(16);
  if (prev) {
    try {
      const p = JSON.parse(prev);
      if (p.token) token = p.token; // keep original unsubscribe token
    } catch {}
  }
  await kv.put(key, JSON.stringify({ email, ts: Date.now(), source: source || "site", token }));

  return wantsHtml
    ? page(
        "Subscribed",
        `You are on the list as <b>${email.replace(/</g, "&lt;")}</b>. ` +
          `One email per new post, unsubscribe anytime.`,
        true
      )
    : json({ ok: true });
}

export async function onRequestGet(context) {
  const { request, env } = context;
  const url = new URL(request.url);
  if (url.searchParams.get("op") !== "unsubscribe") {
    return new Response("Not found", { status: 404 });
  }
  const kv = env.NEWSLETTER_KV;
  if (!kv) return page("Unavailable", "Newsletter storage is not configured yet.", false);
  const email = String(url.searchParams.get("email") || "").trim().toLowerCase();
  const t = String(url.searchParams.get("t") || "");
  if (EMAIL_RE.test(email) && t) {
    const id = await sha256hex("cortexflow-nl:" + email);
    const raw = await kv.get("sub:" + id);
    if (raw) {
      try {
        if (JSON.parse(raw).token === t) {
          await kv.delete("sub:" + id);
          return page("Unsubscribed", `${email.replace(/</g, "&lt;")} has been removed from the newsletter.`, true);
        }
      } catch {}
    }
  }
  return page("Not found", "That subscription link is invalid or already used.", false);
}
