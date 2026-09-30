import { SITE } from "../config";

export async function GET() {
  const body = `User-agent: *
Allow: /

Sitemap: ${new URL("sitemap-index.xml", SITE.url).toString()}
`;
  return new Response(body, {
    headers: { "Content-Type": "text/plain; charset=utf-8" },
  });
}
