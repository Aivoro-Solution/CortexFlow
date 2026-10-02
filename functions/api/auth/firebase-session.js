/* POST /api/auth/firebase-session
 * Body: { idToken } — Firebase ID token from the JS SDK.
 * Verifies it with Firebase, then mints our HttpOnly session cookie.
 * (The user profile itself is stored in Firestore, written from the browser.) */
import {
  json,
  rateLimited,
  createSession,
  sessionCookie,
  verifyFirebaseIdToken,
  firebaseConfigured,
  EMAIL_RE,
} from "./_lib.js";

export async function onRequestPost(context) {
  const { request, env } = context;
  const kv = env.AUTH_KV;
  if (!kv) return json({ ok: false, error: "Auth is not configured yet." }, 500);
  if (!firebaseConfigured()) {
    return json({ ok: false, error: "Sign-in is being set up. Please try again soon." }, 503);
  }
  if (await rateLimited(kv, request, "fbsess", 20)) {
    return json({ ok: false, error: "Too many attempts. Try again later." }, 429);
  }

  let body;
  try {
    body = await request.json();
  } catch {
    body = {};
  }
  const idToken = body && body.idToken;
  if (!idToken) return json({ ok: false, error: "Missing sign-in token." }, 400);

  let claims;
  try {
    claims = await verifyFirebaseIdToken(idToken);
  } catch {
    return json({ ok: false, error: "Sign-in token invalid or expired. Please try again." }, 401);
  }

  const email = (claims.email || "").trim().toLowerCase();
  if (!EMAIL_RE.test(email)) {
    return json({ ok: false, error: "No verified email on this account." }, 400);
  }
  const name = (claims.name || "").trim().slice(0, 64) || email.split("@")[0] || "Member";
  const uid = "fb:" + claims.sub;

  const token = await createSession(kv, uid, { name, email });
  return new Response(JSON.stringify({ ok: true, name, email }), {
    headers: {
      "content-type": "application/json; charset=utf-8",
      "set-cookie": sessionCookie(token),
    },
  });
}
