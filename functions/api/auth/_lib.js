/* Shared auth helpers for CortexFlow (Cloudflare Pages Functions).
 *
 * Auth: Firebase Authentication (Google) — email/password.
 *   - Browser signs in/up with the Firebase JS SDK, gets an ID token.
 *   - POST /api/auth/firebase-session {idToken} verifies the token with
 *     Google and mints our own HttpOnly session cookie.
 * Storage:
 *   - Sessions: KV binding AUTH_KV — sess:<token> -> {uid,name,email,created} (30-day TTL)
 *   - Profiles: R2 binding USER_DATA — users/<firebase-uid>.json
 *   - Cookie: cf_auth (HttpOnly, Secure, SameSite=Lax, Path=/)
 *
 * !!! Fill in FIREBASE_PROJECT_ID below (Firebase console -> Project settings).
 */

export const FIREBASE_PROJECT_ID = "__FIREBASE_PROJECT_ID__";

export const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;
export const SESSION_TTL = 30 * 24 * 3600; // 30 days
export const COOKIE_NAME = "cf_auth";

export function firebaseConfigured() {
  return !FIREBASE_PROJECT_ID.startsWith("__");
}

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

/* Verify a Firebase ID token with Google and return its claims.
 * Throws on any failure. Checks: valid Google signature, aud == our
 * project, iss == securetoken issuer, not expired. */
export async function verifyFirebaseIdToken(idToken) {
  if (!firebaseConfigured()) throw new Error("Firebase not configured");
  if (typeof idToken !== "string" || idToken.split(".").length !== 3) {
    throw new Error("Malformed token");
  }
  const res = await fetch(
    "https://oauth2.googleapis.com/tokeninfo?id_token=" + encodeURIComponent(idToken),
    { headers: { accept: "application/json" } }
  );
  if (!res.ok) throw new Error("Token rejected by Google");
  const claims = await res.json();
  if (claims.aud !== FIREBASE_PROJECT_ID) throw new Error("Wrong audience");
  if (claims.iss !== "https://securetoken.google.com/" + FIREBASE_PROJECT_ID) {
    throw new Error("Wrong issuer");
  }
  if (!claims.sub) throw new Error("No subject");
  const now = Math.floor(Date.now() / 1000);
  if (claims.exp && Number(claims.exp) < now - 30) throw new Error("Token expired");
  return claims; // {sub, email, email_verified, name?, ...}
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

export async function createSession(kv, uid, profile) {
  const token = randomHex(32);
  const sess = {
    uid,
    name: (profile && profile.name) || "Member",
    email: (profile && profile.email) || "",
    created: Date.now(),
  };
  await kv.put("sess:" + token, JSON.stringify(sess), { expirationTtl: SESSION_TTL });
  return token;
}

export async function getSessionUser(kv, request) {
  const token = getSessionToken(request);
  if (!token || !/^[0-9a-f]{64}$/.test(token)) return null;
  const raw = await kv.get("sess:" + token);
  if (!raw) return null;
  try {
    const s = JSON.parse(raw);
    if (!s.uid) return null;
    return { id: s.uid, name: s.name || "Member", email: s.email || "", _token: token };
  } catch {
    return null;
  }
}

/* Save/update the user profile in R2 (users/<firebase-uid>.json).
 * No-op when the USER_DATA binding is missing. */
export async function saveProfileToR2(r2, firebaseUid, profile) {
  if (!r2 || !firebaseUid) return false;
  const key = "users/" + firebaseUid + ".json";
  const now = new Date().toISOString();
  let doc = null;
  try {
    const existing = await r2.get(key);
    if (existing) doc = await existing.json();
  } catch {
    doc = null;
  }
  if (!doc) {
    doc = {
      uid: firebaseUid,
      name: profile.name || "Member",
      email: profile.email || "",
      provider: "firebase",
      created: now,
      updated: now,
    };
  } else {
    if (profile.name && profile.name !== doc.name) doc.name = profile.name;
    if (profile.email && profile.email !== doc.email) doc.email = profile.email;
    doc.updated = now;
  }
  await r2.put(key, JSON.stringify(doc), {
    httpMetadata: { contentType: "application/json; charset=utf-8" },
  });
  return true;
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
