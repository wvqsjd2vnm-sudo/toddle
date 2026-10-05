// One-time-code gate for the games site.
//  POST /api/redeem        {code}  -> marks the code USED (atomically) and sets a session cookie
//  GET  /api/session               -> {ok:true} if this browser holds a valid redeemed code
//  GET  /api/admin/codes           -> full list with used/unused   (header x-admin-code)
//  POST /api/admin/reset   {code}  -> makes a code usable again    (header x-admin-code)
//  POST /api/admin/label   {code,label} -> note who you gave it to (header x-admin-code)
// Game files (f1, storm) are only served to browsers with a valid session.

// matches /storm, /storm.html, /storm/, any casing: the assets layer redirects .html -> pretty URLs
const isGame = (path) => {
  let p = path;
  try { p = decodeURIComponent(path); } catch { /* keep raw */ }
  return /^\/+(f1|storm)(\.html)?\/*$/i.test(p);
};
const COOKIE = 'gh_session';
const MAX_ATTEMPTS = 10; // wrong guesses allowed per IP...
const WINDOW_MS = 10 * 60 * 1000; // ...per 10 minutes
const YEAR = 365 * 24 * 3600;

const json = (obj, status = 200, headers = {}) =>
  new Response(JSON.stringify(obj), {
    status,
    headers: { 'content-type': 'application/json', 'cache-control': 'no-store', ...headers },
  });

const enc = new TextEncoder();
const b64url = (buf) =>
  btoa(String.fromCharCode(...new Uint8Array(buf))).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');

async function hmac(secret, msg) {
  const key = await crypto.subtle.importKey('raw', enc.encode(secret), { name: 'HMAC', hash: 'SHA-256' }, false, ['sign']);
  return b64url(await crypto.subtle.sign('HMAC', key, enc.encode(msg)));
}

function safeEqual(a, b) {
  if (typeof a !== 'string' || typeof b !== 'string') return false;
  let d = a.length ^ b.length;
  const n = Math.max(a.length, b.length);
  for (let i = 0; i < n; i++) d |= (a.charCodeAt(i) || 0) ^ (b.charCodeAt(i) || 0);
  return d === 0;
}

// cookie value: code.usedAt.signature  (usedAt ties the cookie to this redemption, so a reset kills it)
async function makeToken(env, code, usedAt) {
  return `${code}.${usedAt}.${await hmac(env.SESSION_SECRET, `${code}.${usedAt}`)}`;
}

async function sessionOk(request, env) {
  const m = (request.headers.get('cookie') || '').match(new RegExp(`(?:^|; )${COOKIE}=([^;]+)`));
  if (!m) return false;
  const [code, usedAt, sig] = m[1].split('.');
  if (!code || !usedAt || !sig) return false;
  if (!safeEqual(sig, await hmac(env.SESSION_SECRET, `${code}.${usedAt}`))) return false;
  const row = await env.DB.prepare('SELECT used_at FROM codes WHERE code = ?').bind(code).first();
  return !!row && String(row.used_at) === usedAt;
}

function isAdmin(request, env) {
  return !!env.ADMIN_CODE && safeEqual(request.headers.get('x-admin-code') || '', env.ADMIN_CODE);
}

async function redeem(request, env) {
  const ip = request.headers.get('cf-connecting-ip') || 'unknown';
  const now = Date.now();
  await env.DB.prepare('DELETE FROM attempts WHERE at < ?').bind(now - WINDOW_MS).run();
  const { n } = await env.DB.prepare('SELECT COUNT(*) AS n FROM attempts WHERE ip = ? AND at > ?').bind(ip, now - WINDOW_MS).first();
  if (n >= MAX_ATTEMPTS) return json({ ok: false, error: 'too_many' }, 429);

  let code = '';
  try { code = String((await request.json()).code || '').replace(/\D/g, ''); } catch { /* bad body */ }
  if (code.length !== 6) return json({ ok: false, error: 'invalid' }, 400);

  // Atomic: only one request can ever flip used_at from NULL, even if two people submit at once.
  const res = await env.DB.prepare('UPDATE codes SET used_at = ?, used_ua = ?, used_ip = ? WHERE code = ? AND used_at IS NULL')
    .bind(now, (request.headers.get('user-agent') || '').slice(0, 200), ip, code).run();

  if (res.meta.changes === 1) {
    const token = await makeToken(env, code, now);
    return json({ ok: true }, 200, {
      'set-cookie': `${COOKIE}=${token}; Max-Age=${YEAR}; Path=/; HttpOnly; Secure; SameSite=Lax`,
    });
  }

  await env.DB.prepare('INSERT INTO attempts (ip, at) VALUES (?, ?)').bind(ip, now).run();
  const row = await env.DB.prepare('SELECT 1 FROM codes WHERE code = ?').bind(code).first();
  return json({ ok: false, error: row ? 'used' : 'invalid' }, row ? 409 : 404);
}

async function admin(request, env, path) {
  if (!isAdmin(request, env)) {
    await new Promise((r) => setTimeout(r, 400));
    return json({ ok: false, error: 'forbidden' }, 403);
  }
  if (path === '/api/admin/codes' && request.method === 'GET') {
    const { results } = await env.DB.prepare('SELECT code, label, used_at, used_ua, used_ip FROM codes ORDER BY rowid').all();
    return json({ ok: true, codes: results });
  }
  if (request.method !== 'POST') return json({ ok: false }, 405);
  const body = await request.json().catch(() => ({}));
  const code = String(body.code || '').replace(/\D/g, '');
  if (path === '/api/admin/reset') {
    const r = await env.DB.prepare('UPDATE codes SET used_at = NULL, used_ua = NULL, used_ip = NULL WHERE code = ?').bind(code).run();
    return json({ ok: r.meta.changes === 1 });
  }
  if (path === '/api/admin/label') {
    const r = await env.DB.prepare('UPDATE codes SET label = ? WHERE code = ?').bind(String(body.label || '').slice(0, 100), code).run();
    return json({ ok: r.meta.changes === 1 });
  }
  return json({ ok: false }, 404);
}

export default {
  async fetch(request, env) {
    const path = new URL(request.url).pathname;
    if (path === '/api/redeem' && request.method === 'POST') return redeem(request, env);
    if (path === '/api/session') return json({ ok: await sessionOk(request, env) });
    if (path.startsWith('/api/admin/')) return admin(request, env, path);
    if (isGame(path) && !(await sessionOk(request, env))) {
      return new Response('Enter a valid code first.', { status: 403, headers: { 'cache-control': 'no-store' } });
    }
    const res = await env.ASSETS.fetch(request);
    if (isGame(path)) {
      const h = new Headers(res.headers);
      h.set('cache-control', 'private, no-store');
      return new Response(res.body, { status: res.status, headers: h });
    }
    return res;
  },
};
