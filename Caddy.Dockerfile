FROM ghcr.io/astral-sh/uv:0.12.9-python3.12-trixie-slim

ARG TARGETARCH
ARG CADDY_VERSION=2.11.3

RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates curl tar \
    && curl -fsSL "https://github.com/caddyserver/caddy/releases/download/v${CADDY_VERSION}/caddy_${CADDY_VERSION}_linux_${TARGETARCH}.tar.gz" \
        -o /tmp/caddy.tar.gz \
    && tar -xzf /tmp/caddy.tar.gz -C /tmp caddy \
    && install -m 0755 /tmp/caddy /usr/bin/caddy \
    && rm -rf /tmp/caddy /tmp/caddy.tar.gz /var/lib/apt/lists/*

ENV XDG_CONFIG_HOME=/config XDG_DATA_HOME=/data
WORKDIR /srv
EXPOSE 80 443 443/udp
ENTRYPOINT ["caddy"]
CMD ["run", "--config", "/etc/caddy/Caddyfile", "--adapter", "caddyfile"]
