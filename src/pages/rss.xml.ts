import rss from "@astrojs/rss";
import { SITE } from "../config";
import { getPublishedPosts, postUrl } from "../lib/posts";

export async function GET(context: any) {
  const posts = await getPublishedPosts();
  return rss({
    title: SITE.name,
    description: SITE.description,
    site: context.site ?? SITE.url,
    items: posts.map((post) => ({
      title: post.data.title,
      description: post.data.description,
      pubDate: post.data.date,
      link: postUrl(post),
      categories: [post.data.category, ...post.data.tags],
      author: `${SITE.authorEmail} (${post.data.author})`,
    })),
    customData: `<language>${SITE.language}</language>`,
  });
}
