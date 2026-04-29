import { fetchCached } from './fetcher.js';
import { DEMO_URL } from '../config.js';

interface CollectionProductsJson {
  products: Array<{ handle: string; id: number; title: string }>;
}

export async function fetchCollectionProductHandles(
  collectionHandle: string,
): Promise<string[]> {
  const handles: string[] = [];
  for (let page = 1; page <= 20; page++) {
    const url = `${DEMO_URL}/collections/${collectionHandle}/products.json?limit=250&page=${page}`;
    let body: string;
    try {
      body = await fetchCached(url);
    } catch {
      break;
    }
    const json = JSON.parse(body) as CollectionProductsJson;
    if (!json.products?.length) break;
    for (const p of json.products) handles.push(p.handle);
    if (json.products.length < 250) break;
  }
  return handles;
}
