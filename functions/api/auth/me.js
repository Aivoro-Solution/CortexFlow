/* GET /api/auth/me -> {ok, name, email} when signed in, else 401 */
import { json, getSessionUser } from "./_lib.js";

export async function onRequestGet(context) {
  const { request, env } = context;
  const kv = env.AUTH_KV;
  if (!kv) return json({ ok: false, error: "Auth is not configured yet." }, 500);
  const user = await getSessionUser(kv, request);
  if (!user) return json({ ok: false }, 401);
  return json({ ok: true, name: user.name, email: user.email });
}
