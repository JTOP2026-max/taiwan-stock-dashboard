# Unified Quote Proxy

Target architecture:

Desktop / Mobile -> Cloudflare Worker -> TWSE MIS / TPEx -> dashboard refresh every 30 seconds.

## Files
- `cloudflare-worker/src/index.js`: Worker quote proxy.
- `cloudflare-worker/wrangler.toml`: Worker config.
- `.github/workflows/deploy-quote-proxy.yml`: manual Worker deployment.
- `quote-sync.js`: proxy-first quote sync, 30-second refresh.

## Required GitHub Secrets for deployment
- `CLOUDFLARE_API_TOKEN`
- `CLOUDFLARE_ACCOUNT_ID`

After deployment, copy the Worker URL (for example `https://taiwan-stock-quote-proxy.<subdomain>.workers.dev`) into `PROXY_URL` at the top of `quote-sync.js`.

Until `PROXY_URL` is filled, the dashboard safely keeps browser-direct MIS as the live fallback and official closing data as the final fallback.
