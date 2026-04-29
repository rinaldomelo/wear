import { mkdir, writeFile } from 'node:fs/promises';
import { join } from 'node:path';
import { Command } from 'commander';
import { walkSitemap, type SitemapNode } from './crawl/sitemap.js';
import { extractNav } from './extract/nav.js';
import { extractHomepageSections } from './extract/sections.js';
import { syncCollections } from './admin/sync-collections.js';
import { PATHS } from './config.js';

const program = new Command()
  .name('wear-cloner')
  .description('Clone a Shopify demo store into wear-revamp using Horizon');

program
  .command('crawl')
  .description('Walk demo sitemap and persist node graph')
  .action(async () => {
    const nodes = await walkSitemap();
    await persist('sitemap.json', nodes);
    summarize(nodes);
  });

program
  .command('extract')
  .description('Extract nav menus and homepage section order')
  .action(async () => {
    const [nav, sections] = await Promise.all([
      extractNav(),
      extractHomepageSections(),
    ]);
    await persist('nav.json', nav);
    await persist('homepage-sections.json', sections);
    console.log(
      `\nHeader: ${nav.header.length} links, Footer: ${nav.footer.length} links`,
    );
    console.log(`Homepage sections: ${sections.length}`);
    console.log('Section order:');
    for (const s of sections) {
      console.log(
        `  ${String(s.order).padStart(2)}. ${s.ritualType} → ${s.horizonType ?? 'UNMAPPED'}`,
      );
    }
  });

program
  .command('sync-collections')
  .description(
    'Add products to collections (mapped from demo) and publish all collections to all sales channels',
  )
  .action(async () => {
    await syncCollections();
  });

program
  .command('all')
  .description('Run crawl + extract end-to-end')
  .action(async () => {
    const nodes = await walkSitemap();
    await persist('sitemap.json', nodes);
    summarize(nodes);
    const [nav, sections] = await Promise.all([
      extractNav(),
      extractHomepageSections(),
    ]);
    await persist('nav.json', nav);
    await persist('homepage-sections.json', sections);
    console.log(
      `\nNav captured: header=${nav.header.length} footer=${nav.footer.length}`,
    );
    console.log(`Homepage sections captured: ${sections.length}`);
  });

async function persist(name: string, data: unknown) {
  await mkdir(PATHS.data, { recursive: true });
  const path = join(PATHS.data, name);
  await writeFile(path, JSON.stringify(data, null, 2), 'utf8');
  console.log(`→ wrote ${path}`);
}

function summarize(nodes: SitemapNode[]) {
  const by: Record<string, SitemapNode[]> = {};
  for (const n of nodes) (by[n.kind] ??= []).push(n);
  console.log('\nSitemap summary:');
  for (const kind of Object.keys(by).sort()) {
    console.log(`  ${kind.padEnd(11)} ${by[kind]!.length}`);
  }
}

program.parseAsync(process.argv).catch((err) => {
  console.error(err);
  process.exit(1);
});
