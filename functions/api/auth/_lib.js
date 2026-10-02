/* Shared auth helpers for CortexFlow (Cloudflare Pages Functions).
 * KV binding: AUTH_KV
 * - Users:   user:email:<sha256(email)> -> {id,name,email,pass,created}
 *            user:id:<id>               -> same record
 * - Sessions: sess:<token> -> {uid, created}  (30-day TTL)
 * - Cookie: cf_auth (HttpOnly, Secure, SameSite=Lax, Path=/)
 */

export const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;
export const SESSION_TTL = 30 * 24 * 3600; // 30 days
export const COOKIE_NAME = "cf_auth";

export function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "content-type": "application/json; charset=utf-8" },
  });
}

export function randomHex(n) {
  const b = new Uint8Array(n);
  crypto.getRandomValues(b);
  return [...b].map((x) => x.toString(16).padStart(2, "0")).join("");
}

export function b64encode(bytes) {
  let s = "";
  for (const b of bytes) s += String.fromCharCode(b);
  return btoa(s);
}

export function b64decode(s) {
  const bin = atob(s);
  const out = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
  return out;
}

async function sha256hex(str) {
  const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(str));
  return [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

/* PBKDF2-SHA256, 100k iterations. Stored as pbkdf2$100000$<salt_b64>$<hash_b64> */
export async function hashPassword(password) {
  const salt = new Uint8Array(16);
  crypto.getRandomValues(salt);
  const key = await crypto.subtle.importKey("raw", new TextEncoder().encode(password), "PBKDF2", false, ["deriveBits"]);
  const bits = await crypto.subtle.deriveBits(
    { name: "PBKDF2", salt, iterations: 100000, hash: "SHA-256" },
    key,
    256
  );
  return `pbkdf2$100000$${b64encode(salt)}$${b64encode(new Uint8Array(bits))}`;
}

export async function verifyPassword(password, stored) {
  try {
    const [, iterStr, saltB64, hashB64] = stored.split("$");
    const iterations = parseInt(iterStr, 10);
    if (!iterations || !saltB64 || !hashB64) return false;
    const salt = b64decode(saltB64);
    const expected = b64decode(hashB64);
    const key = await crypto.subtle.importKey("raw", new TextEncoder().encode(password), "PBKDF2", false, ["deriveBits"]);
    const bits = new Uint8Array(
      await crypto.subtle.deriveBits({ name: "PBKDF2", salt, iterations, hash: "SHA-256" }, key, expected.length * 8)
    );
    if (bits.length !== expected.length) return false;
    let diff = 0;
    for (let i = 0; i < bits.length; i++) diff |= bits[i] ^ expected[i];
    return diff === 0;
  } catch {
    return false;
  }
}

export function emailKey(email) {
  return sha256hex("cortexflow-user:" + email).then((h) => "user:email:" + h);
}

export function getSessionToken(request) {
  const cookie = request.headers.get("cookie") || "";
  const m = cookie.match(/(?:^|;\s*)cf_auth=([^;]+)/);
  return m ? decodeURIComponent(m[1]) : null;
}

export function sessionCookie(token, maxAge = SESSION_TTL) {
  return `${COOKIE_NAME}=${encodeURIComponent(token)}; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=${maxAge}`;
}

export function clearCookie() {
  return `${COOKIE_NAME}=; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=0`;
}

export async function createSession(kv, uid) {
  const token = randomHex(32);
  await kv.put("sess:" + token, JSON.stringify({ uid, created: Date.now() }), { expirationTtl: SESSION_TTL });
  return token;
}

export async function getSessionUser(kv, request) {
  const token = getSessionToken(request);
  if (!token || !/^[0-9a-f]{64}$/.test(token)) return null;
  const raw = await kv.get("sess:" + token);
  if (!raw) return null;
  let sess;
  try {
    sess = JSON.parse(raw);
  } catch {
    return null;
  }
  const urec = await kv.get("user:id:" + sess.uid);
  if (!urec) return null;
  try {
    const u = JSON.parse(urec);
    return { id: u.id, name: u.name, email: u.email, _token: token };
  } catch {
    return null;
  }
}

/* Simple per-IP rate limit. Returns true when over the limit. */
export async function rateLimited(kv, request, action, max = 10, windowSecs = 3600) {
  const ip = request.headers.get("cf-connecting-ip") || "unknown";
  const key = `rl:${action}:${ip}`;
  const count = parseInt((await kv.get(key)) || "0", 10);
  if (count >= max) return true;
  await kv.put(key, String(count + 1), { expirationTtl: windowSecs });
  return false;
}
