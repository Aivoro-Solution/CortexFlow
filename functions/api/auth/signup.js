/* POST /api/auth/signup  {name, email, password} -> creates account + session */
import { json, EMAIL_RE, hashPassword, randomHex, emailKey, createSession, sessionCookie, rateLimited } from "./_lib.js";

export async function onRequestPost(context) {
  const { request, env } = context;
  const kv = env.AUTH_KV;
  if (!kv) return json({ ok: false, error: "Auth is not configured yet." }, 500);

  if (await rateLimited(kv, request, "signup", 10)) {
    return json({ ok: false, error: "Too many attempts. Try again later." }, 429);
  }

  let name = "", email = "", password = "";
  try {
    const body = await request.json();
    name = String(body.name || "").trim().slice(0, 64);
    email = String(body.email || "").trim().toLowerCase();
    password = String(body.password || "");
  } catch {
    return json({ ok: false, error: "Invalid request." }, 400);
  }

  if (!name) return json({ ok: false, error: "Please enter your name." }, 400);
  if (!EMAIL_RE.test(email) || email.length > 254) {
    return json({ ok: false, error: "Please enter a valid email address." }, 400);
  }
  if (password.length < 8) {
    return json({ ok: false, error: "Password must be at least 8 characters." }, 400);
  }
  if (password.length > 128) {
    return json({ ok: false, error: "Password is too long." }, 400);
  }

  const key = await emailKey(email);
  if (await kv.get(key)) {
    return json({ ok: false, error: "An account with this email already exists. Try signing in." }, 409);
  }

  const id = randomHex(16);
  const pass = await hashPassword(password);
  const record = JSON.stringify({ id, name, email, pass, created: Date.now() });
  await kv.put(key, record);
  await kv.put("user:id:" + id, record);

  const token = await createSession(kv, id);
  return new Response(JSON.stringify({ ok: true, name, email }), {
    status: 201,
    headers: {
      "content-type": "application/json; charset=utf-8",
      "set-cookie": sessionCookie(token),
    },
  });
}
