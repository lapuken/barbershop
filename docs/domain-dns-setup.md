# Domain and DNS Setup (machinjiri.net)

Use:

- `ROOT_DOMAIN=machinjiri.net`
- `APP_DOMAIN=app.machinjiri.net`

This deployment can either:

- serve only `app.machinjiri.net`, or
- redirect `machinjiri.net` to `https://app.machinjiri.net`

## 1. Point DNS to the VPS

Create or update these DNS records:

- `A machinjiri.net -> <VPS_PUBLIC_IP>`
- `A app.machinjiri.net -> <VPS_PUBLIC_IP>`

If you do not want the root-domain redirect, the `app` record is still mandatory.

## 2. Verify Propagation

From any machine:

```bash
dig +short machinjiri.net
dig +short app.machinjiri.net
```

Or:

```bash
nslookup machinjiri.net
nslookup app.machinjiri.net
```

Both names should resolve to the VPS before running Certbot.

## 3. TLS Issuance Note

Let's Encrypt can issue certificates only when:

- the DNS record is publicly resolvable
- inbound `80/tcp` is reachable during HTTP challenge validation
- the hostname in `.env` matches the DNS name (`APP_DOMAIN=app.machinjiri.net`)
