/* POST /api/auth/signin  {email, password} -> creates session */
import { json, EMAIL_RE, verifyPassword, emailKey, createSession, sessionCookie, rateLimited } from "./_lib.js";

export async function onRequestPost(context) {
  const { request, env } = context;
  const kv = env.AUTH_KV;
  if (!kv) return json({ ok: false, error: "Auth is not configured yet." }, 500);

  if (await rateLimited(kv, request, "signin", 10)) {
    return json({ ok: false, error: "Too many attempts. Try again later." }, 429);
  }

  let email = "", password = "";
  try {
    const body = await request.json();
    email = String(body.email || "").trim().toLowerCase();
    password = String(body.password || "");
  } catch {
    return json({ ok: false, error: "Invalid request." }, 400);
  }

  const wrong = json({ ok: false, error: "Incorrect email or password." }, 401);
  if (!EMAIL_RE.test(email)) return wrong;

  const raw = await kv.get(await emailKey(email));
  if (!raw) return wrong;
  let user;
  try {
    user = JSON.parse(raw);
  } catch {
    return wrong;
  }
  if (!(await verifyPassword(password, user.pass))) return wrong;

  const token = await createSession(kv, user.id);
  return new Response(JSON.stringify({ ok: true, name: user.name, email: user.email }), {
    headers: {
      "content-type": "application/json; charset=utf-8",
      "set-cookie": sessionCookie(token),
    },
  });
}
