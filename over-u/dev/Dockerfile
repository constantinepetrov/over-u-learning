# syntax=docker/dockerfile:1
FROM python:3.14-slim-bookworm
ARG TARGETARCH
RUN --mount=type=secret,id=ca_bundle,required=true \
    apt-get update && apt-get install -y --no-install-recommends \
    cron git curl file build-essential pkg-config libmariadb-dev mariadb-client \
    libcairo2 libmagic1 libpango-1.0-0 libpangocairo-1.0-0 \
    && rm -rf /var/lib/apt/lists/*
RUN --mount=type=secret,id=ca_bundle,required=true \
    PIP_CERT=/run/secrets/ca_bundle pip install --no-cache-dir frappe-bench uv \
    && case "$TARGETARCH" in \
         amd64) NODE_ARCH=x64 ;; \
         arm64) NODE_ARCH=arm64 ;; \
         *) echo "Unsupported Docker build architecture: $TARGETARCH" >&2; exit 1 ;; \
       esac \
    && CURL_CA_BUNDLE=/run/secrets/ca_bundle curl -fsSL \
       "https://nodejs.org/dist/v24.19.0/node-v24.19.0-linux-${NODE_ARCH}.tar.xz" \
       | tar -xJ -C /opt \
    && ln -s "/opt/node-v24.19.0-linux-${NODE_ARCH}/bin/node" /usr/local/bin/node \
    && ln -s "/opt/node-v24.19.0-linux-${NODE_ARCH}/bin/npm" /usr/local/bin/npm \
    && NODE_EXTRA_CA_CERTS=/run/secrets/ca_bundle npm install -g yarn@1.22.22 \
    && ln -s "/opt/node-v24.19.0-linux-${NODE_ARCH}/bin/yarn" /usr/local/bin/yarn
RUN useradd -m -u 1000 -s /bin/bash frappe \
    && mkdir -p /home/frappe/.pyenv/versions/3.14.8/bin \
    && ln -s /usr/local/bin/python3 /home/frappe/.pyenv/versions/3.14.8/bin/python3 \
    && chown -R frappe:frappe /home/frappe
ENV PATH="/usr/local/bin:/usr/bin:/bin"
WORKDIR /home/frappe
