import { storeExecute } from './exec.js';
import { fetchCollectionProductHandles } from '../crawl/collection-products.js';

const TARGET_COLLECTION_HANDLES = [
  'new',
  'tops',
  'bottoms',
  'knitwear',
  'dresses',
  'denim',
  'accessories',
  'bestsellers',
];

interface CollectionsResp {
  collections: { nodes: Array<{ id: string; handle: string }> };
}
interface ProductsResp {
  products: {
    nodes: Array<{ id: string; handle: string }>;
    pageInfo: { hasNextPage: boolean; endCursor: string | null };
  };
}
interface PublicationsResp {
  publications: {
    nodes: Array<{ id: string; catalog: { title: string } | null }>;
  };
}

async function fetchAllProducts(): Promise<Map<string, string>> {
  const map = new Map<string, string>();
  let cursor: string | null = null;
  for (let i = 0; i < 50; i++) {
    const resp = await storeExecute<ProductsResp>({
      query: `query Products($cursor: String) {
        products(first: 250, after: $cursor) {
          nodes { id handle }
          pageInfo { hasNextPage endCursor }
        }
      }`,
      variables: { cursor },
    });
    for (const p of resp.products.nodes) map.set(p.handle, p.id);
    if (!resp.products.pageInfo.hasNextPage) break;
    cursor = resp.products.pageInfo.endCursor;
  }
  return map;
}

async function fetchCollections(): Promise<Map<string, string>> {
  const resp = await storeExecute<CollectionsResp>({
    query: `query { collections(first: 50) { nodes { id handle } } }`,
  });
  return new Map(resp.collections.nodes.map((c) => [c.handle, c.id]));
}

async function fetchPublications(): Promise<Array<{ id: string; title: string }>> {
  const resp = await storeExecute<PublicationsResp>({
    query: `query { publications(first: 25) { nodes { id catalog { title } } } }`,
  });
  return resp.publications.nodes.map((n) => ({
    id: n.id,
    title: n.catalog?.title ?? n.id,
  }));
}

async function addProducts(collectionId: string, productIds: string[]) {
  if (productIds.length === 0) return;
  const chunkSize = 100;
  for (let i = 0; i < productIds.length; i += chunkSize) {
    const chunk = productIds.slice(i, i + chunkSize);
    const resp = await storeExecute<{
      collectionAddProducts: {
        userErrors: Array<{ field: string[]; message: string }>;
      };
    }>({
      query: `mutation collectionAddProducts($id: ID!, $productIds: [ID!]!) {
        collectionAddProducts(id: $id, productIds: $productIds) {
          collection { id title productsCount { count } }
          userErrors { field message }
        }
      }`,
      variables: { id: collectionId, productIds: chunk },
      allowMutations: true,
    });
    const errs = resp.collectionAddProducts.userErrors;
    if (errs.length) console.warn(`  userErrors:`, errs);
  }
}

async function publishToAll(
  resourceId: string,
  publications: Array<{ id: string; title: string }>,
) {
  const input = publications.map((p) => ({ publicationId: p.id }));
  const resp = await storeExecute<{
    publishablePublish: {
      userErrors: Array<{ field: string[]; message: string }>;
    };
  }>({
    query: `mutation publishablePublish($id: ID!, $input: [PublicationInput!]!) {
      publishablePublish(id: $id, input: $input) {
        publishable { resourcePublicationsCount { count } }
        userErrors { field message }
      }
    }`,
    variables: { id: resourceId, input },
    allowMutations: true,
  });
  const errs = resp.publishablePublish.userErrors;
  if (errs.length) console.warn(`  userErrors:`, errs);
}

export async function syncCollections() {
  console.log('→ Fetching publications, collections, products from wear-revamp');
  const [publications, collections, products] = await Promise.all([
    fetchPublications(),
    fetchCollections(),
    fetchAllProducts(),
  ]);
  console.log(
    `  publications=${publications.length}  collections=${collections.size}  products=${products.size}`,
  );
  for (const p of publications) console.log(`    publication: ${p.title}`);

  for (const handle of TARGET_COLLECTION_HANDLES) {
    const collectionId = collections.get(handle);
    if (!collectionId) {
      console.warn(`! collection "${handle}" not found on wear-revamp; skipping`);
      continue;
    }
    console.log(`\n→ Collection: ${handle}`);

    const demoHandles = await fetchCollectionProductHandles(handle);
    console.log(`  demo handles: ${demoHandles.length}`);

    const productIds: string[] = [];
    const missing: string[] = [];
    for (const h of demoHandles) {
      const id = products.get(h);
      if (id) productIds.push(id);
      else missing.push(h);
    }
    console.log(`  resolved on wear-revamp: ${productIds.length}, missing: ${missing.length}`);
    if (missing.length && missing.length <= 5)
      console.log(`    missing handles: ${missing.join(', ')}`);

    await addProducts(collectionId, productIds);
    console.log(`  added ${productIds.length} products`);

    await publishToAll(collectionId, publications);
    console.log(`  published to ${publications.length} sales channels`);
  }
  console.log('\n✓ Collection sync complete.');
}
