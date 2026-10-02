/* POST /api/auth/signout -> destroys session, clears cookie */
import { json, getSessionToken, clearCookie } from "./_lib.js";

export async function onRequestPost(context) {
  const { request, env } = context;
  const kv = env.AUTH_KV;
  const token = getSessionToken(request);
  if (kv && token) {
    await kv.delete("sess:" + token);
  }
  return new Response(JSON.stringify({ ok: true }), {
    headers: {
      "content-type": "application/json; charset=utf-8",
      "set-cookie": clearCookie(),
    },
  });
}
