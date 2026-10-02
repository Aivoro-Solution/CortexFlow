/* Shared auth helpers for CortexFlow (Cloudflare Pages Functions).
 *
 * Auth: Firebase Authentication (Google) — email/password.
 *   - Browser signs in/up with the Firebase JS SDK, gets an ID token.
 *   - POST /api/auth/firebase-session {idToken} verifies the token with
 *     Google and mints our own HttpOnly session cookie.
 * Storage:
 *   - Sessions: KV binding AUTH_KV — sess:<token> -> {uid,name,email,created} (30-day TTL)
 *   - Profiles: Firebase Firestore — users/<firebase-uid> (written from the
 *     browser after sign-in; security rules restrict each user to their own doc)
 *   - Cookie: cf_auth (HttpOnly, Secure, SameSite=Lax, Path=/)
 *
 * !!! Fill in FIREBASE_PROJECT_ID below (Firebase console -> Project settings).
 */

export const FIREBASE_PROJECT_ID = "cortexflow-7c274";
// Web API key — public by design (Firebase docs), also embedded in the site's pages.
export const FIREBASE_API_KEY = "AIzaSyBgmyFmzeP9nzhlDPd1800b0ycYmg-yDeM";

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

/* Verify a Firebase ID token with the Firebase Auth backend and return
 * normalized claims {sub, email, name, email_verified}.
 * Throws on any failure. accounts:lookup validates the signature, expiry
 * and project binding server-side — stronger than a local check. */
export async function verifyFirebaseIdToken(idToken) {
  if (!firebaseConfigured()) throw new Error("Firebase not configured");
  if (typeof idToken !== "string" || idToken.split(".").length !== 3) {
    throw new Error("Malformed token");
  }
  const res = await fetch(
    "https://identitytoolkit.googleapis.com/v1/accounts:lookup?key=" + FIREBASE_API_KEY,
    {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ idToken }),
    }
  );
  if (!res.ok) throw new Error("Token rejected by Firebase");
  const data = await res.json().catch(() => ({}));
  const user = data && data.users && data.users[0];
  if (!user || !user.localId) throw new Error("No user for token");
  return {
    sub: user.localId,
    email: user.email || "",
    name: user.displayName || "",
    email_verified: !!user.emailVerified,
  };
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

/* Simple per-IP rate limit. Returns true when over the limit. */
export async function rateLimited(kv, request, action, max = 10, windowSecs = 3600) {
  const ip = request.headers.get("cf-connecting-ip") || "unknown";
  const key = `rl:${action}:${ip}`;
  const count = parseInt((await kv.get(key)) || "0", 10);
  if (count >= max) return true;
  await kv.put(key, String(count + 1), { expirationTtl: windowSecs });
  return false;
}
