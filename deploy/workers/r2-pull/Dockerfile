# Vault R2-pull worker — M0.4 stub only (sleep loop). Logic lands in M1.10.
FROM alpine:3.20

RUN mkdir -p /var/lib/vault/db \
        /var/lib/vault/litestream \
        /var/lib/vault/snapshots/manifest \
    && addgroup -g 10002 terra \
    && adduser -D -H -u 10002 -G terra terra \
    && chown -R terra:terra /var/lib/vault

USER terra
WORKDIR /var/lib/vault

# Acceptance: long-interval sleep loop until real worker replaces this image.
CMD ["sh", "-c", "while true; do sleep 3600; done"]
