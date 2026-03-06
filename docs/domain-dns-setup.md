# Domain and DNS Setup (machinjiri.net)

Use:

- `ROOT_DOMAIN=machinjiri.net`
- `APP_DOMAIN=app.machinjiri.net`

This deployment targets the app subdomain only so the apex/root domain can stay in use for another site.

## 1. Add Domain to DigitalOcean DNS

1. Open Networking -> Domains in DigitalOcean.
2. Add `machinjiri.net` if it is not already present.
3. If your registrar is external, ensure nameservers point to DigitalOcean DNS.

## 2. Create DNS Record for the App

Create an **A** record:

- Type: `A`
- Hostname: `app`
- Value: `<DROPLET_PUBLIC_IPV4>`
- TTL: default (or 300s for faster iteration)

Result: `app.machinjiri.net` points to your droplet.

## 3. Keep Apex Domain Optional

You do **not** need to move `machinjiri.net` apex to this droplet unless you want the same server to handle it.

This deployment works with only:

- `app.machinjiri.net` -> droplet IP

## 4. Verify DNS Propagation

From your workstation:

```bash
dig +short app.machinjiri.net
```

Or:

```bash
nslookup app.machinjiri.net
```

The returned IP must match your droplet before Caddy can issue a public TLS certificate.

## 5. TLS Issuance Note

Caddy can only obtain Let's Encrypt certificates when:

- the DNS record is publicly resolvable
- inbound `80/tcp` and `443/tcp` are reachable
- the hostname in `.env` matches the DNS name (`APP_DOMAIN=app.machinjiri.net`)
