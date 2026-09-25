import { z } from 'zod';
export let csrf = '';
export const setCsrf = (token: string) => { csrf = token; };
export async function api<T = any>(path: string, method = 'GET', body?: unknown): Promise<T> {
  const raw = body instanceof FormData || body instanceof ArrayBuffer;
  const r = await fetch('/api/v1' + path, {method, headers: {...(raw ? {} : {'Content-Type': 'application/json'}), 'X-CSRF-Token': csrf}, body: body === undefined ? undefined : raw ? body as BodyInit : JSON.stringify(body)});
  const json = await r.json();
  if (!r.ok) throw new Error(z.object({code: z.string().optional(), detail: z.unknown().optional()}).parse(json).code || 'Request failed');
  return json;
}
import type { components } from './generated/api';
export type Meeting = components['schemas']['MeetingView'] & Partial<Pick<components['schemas']['MeetingDetail'], 'assets'|'jobs'|'participants'|'recordings'>>;
