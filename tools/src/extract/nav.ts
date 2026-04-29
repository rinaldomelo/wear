import { load } from 'cheerio';
import { fetchCached } from '../crawl/fetcher.js';
import { DEMO_URL } from '../config.js';

export interface MenuLink {
  title: string;
  url: string;
  children?: MenuLink[];
}

export interface NavData {
  header: MenuLink[];
  footer: MenuLink[];
}

function rel(url: string): string {
  try {
    const u = new URL(url, DEMO_URL);
    return u.pathname + u.search;
  } catch {
    return url;
  }
}

function extractFromContainer(
  $: ReturnType<typeof load>,
  selector: string,
): MenuLink[] {
  const out: MenuLink[] = [];
  const seen = new Set<string>();

  $(selector)
    .find('a[href]')
    .each((_, el) => {
      const $a = $(el);
      const href = $a.attr('href') ?? '';
      const title = $a.text().trim().replace(/\s+/g, ' ');
      if (!title || !href || href.startsWith('#') || href.startsWith('mailto:'))
        return;
      const path = rel(href);
      const key = `${title}|${path}`;
      if (seen.has(key)) return;
      seen.add(key);
      out.push({ title, url: path });
    });

  return out;
}

export async function extractNav(): Promise<NavData> {
  const html = await fetchCached(`${DEMO_URL}/`);
  const $ = load(html);
  return {
    header: extractFromContainer($, 'header, [role="banner"]'),
    footer: extractFromContainer($, 'footer, [role="contentinfo"]'),
  };
}
