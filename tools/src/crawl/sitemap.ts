import { XMLParser } from 'fast-xml-parser';
import { fetchCached } from './fetcher.js';
import { DEMO_URL } from '../config.js';

export type ResourceKind =
  | 'product'
  | 'collection'
  | 'page'
  | 'blog'
  | 'article'
  | 'unknown';

export interface SitemapNode {
  url: string;
  kind: ResourceKind;
  handle: string;
  lastmod?: string;
  image?: string;
  imageTitle?: string;
}

const parser = new XMLParser({
  ignoreAttributes: false,
  attributeNamePrefix: '@',
  isArray: (name) => name === 'url' || name === 'sitemap',
});

function classify(url: string): { kind: ResourceKind; handle: string } {
  const u = new URL(url);
  const parts = u.pathname.split('/').filter(Boolean);
  if (parts[0] === 'products' && parts[1])
    return { kind: 'product', handle: parts[1] };
  if (parts[0] === 'collections' && parts[1] && !parts[2])
    return { kind: 'collection', handle: parts[1] };
  if (parts[0] === 'pages' && parts[1])
    return { kind: 'page', handle: parts[1] };
  if (parts[0] === 'blogs' && parts[1] && !parts[2])
    return { kind: 'blog', handle: parts[1] };
  if (parts[0] === 'blogs' && parts[1] && parts[2])
    return { kind: 'article', handle: `${parts[1]}/${parts[2]}` };
  return { kind: 'unknown', handle: u.pathname };
}

export async function walkSitemap(
  rootUrl: string = `${DEMO_URL}/sitemap.xml`,
): Promise<SitemapNode[]> {
  const visited = new Set<string>();
  const nodes: SitemapNode[] = [];

  async function walk(url: string) {
    if (visited.has(url)) return;
    visited.add(url);
    const xml = await fetchCached(url);
    const parsed = parser.parse(xml) as {
      sitemapindex?: { sitemap: Array<{ loc: string }> };
      urlset?: {
        url: Array<{
          loc: string;
          lastmod?: string;
          'image:image'?: { 'image:loc'?: string; 'image:title'?: string };
        }>;
      };
    };

    if (parsed.sitemapindex?.sitemap) {
      for (const s of parsed.sitemapindex.sitemap) {
        await walk(s.loc);
      }
      return;
    }
    if (parsed.urlset?.url) {
      for (const entry of parsed.urlset.url) {
        if (!entry.loc) continue;
        const { kind, handle } = classify(entry.loc);
        if (kind === 'unknown') continue;
        nodes.push({
          url: entry.loc,
          kind,
          handle,
          lastmod: entry.lastmod,
          image: entry['image:image']?.['image:loc'],
          imageTitle: entry['image:image']?.['image:title'],
        });
      }
    }
  }

  await walk(rootUrl);
  return nodes;
}
