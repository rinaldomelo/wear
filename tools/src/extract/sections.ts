import { load } from 'cheerio';
import { fetchCached } from '../crawl/fetcher.js';
import { DEMO_URL } from '../config.js';

export interface SectionHit {
  id: string;
  ritualType: string;
  horizonType: string | null;
  order: number;
}

const RITUAL_TO_HORIZON: Record<string, string> = {
  header: 'header',
  footer: 'footer',
  'footer-content': 'footer',
  'footer-utilities': 'footer-utilities',
  'featured-product': 'featured-product',
  'featured_product': 'featured-product',
  'product-list': 'product-list',
  'product_list': 'product-list',
  'collection-list': 'collection-list',
  'collection_list': 'collection-list',
  'collection-links': 'collection-links',
  'layered-slideshow': 'layered-slideshow',
  'layered_slideshow': 'layered-slideshow',
  marquee: 'marquee',
  slideshow: 'slideshow',
  hero: 'hero',
  'media-with-content': 'media-with-content',
  'featured-blog-posts': 'featured-blog-posts',
  carousel: 'carousel',
  'product-recommendations': 'product-recommendations',
};

const RITUAL_TYPE_RE = /(?:section_|template--\d+__|migrated_)([a-z0-9_-]+)/i;

function normalize(raw: string): string {
  return raw.replace(/_[A-Za-z0-9]{4,}$/, '').replace(/_/g, '-');
}

export async function extractHomepageSections(): Promise<SectionHit[]> {
  const html = await fetchCached(`${DEMO_URL}/`);
  const $ = load(html);

  const hits: SectionHit[] = [];
  let order = 0;

  $('[id^="shopify-section-"]').each((_, el) => {
    const id = $(el).attr('id') ?? '';
    const innerId = id.replace(/^shopify-section-/, '');
    const m = innerId.match(RITUAL_TYPE_RE);
    const rawType = m?.[1] ?? innerId;
    const ritualType = normalize(rawType);
    const horizonType = RITUAL_TO_HORIZON[ritualType] ?? null;
    hits.push({ id, ritualType, horizonType, order: order++ });
  });

  return hits;
}
