import { spawn } from 'node:child_process';
import { TARGET_STORE } from '../config.js';

export interface ExecOptions {
  query: string;
  variables?: Record<string, unknown>;
  allowMutations?: boolean;
}

export async function storeExecute<T = unknown>(
  opts: ExecOptions,
): Promise<T> {
  const args = [
    'store',
    'execute',
    '--store',
    TARGET_STORE,
    '--query',
    opts.query,
    '--json',
  ];
  if (opts.allowMutations) args.push('--allow-mutations');
  if (opts.variables) {
    args.push('--variables', JSON.stringify(opts.variables));
  }

  return new Promise<T>((resolve, reject) => {
    const child = spawn('shopify', args, { stdio: ['ignore', 'pipe', 'pipe'] });
    let stdout = '';
    let stderr = '';
    child.stdout.on('data', (d) => (stdout += d.toString()));
    child.stderr.on('data', (d) => (stderr += d.toString()));
    child.on('error', reject);
    child.on('close', (code) => {
      if (code !== 0) {
        reject(new Error(`shopify exited ${code}: ${stderr || stdout}`));
        return;
      }
      const m = stdout.match(/\{[\s\S]*\}\s*$/);
      if (!m) {
        reject(new Error(`No JSON in shopify output:\n${stdout}`));
        return;
      }
      try {
        const parsed = JSON.parse(m[0]);
        resolve((parsed.data ?? parsed) as T);
      } catch (err) {
        reject(new Error(`Bad JSON from shopify: ${(err as Error).message}\n${m[0]}`));
      }
    });
  });
}
