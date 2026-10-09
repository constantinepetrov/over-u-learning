# syntax=docker/dockerfile:1
FROM python:3.14-slim-bookworm
RUN --mount=type=secret,id=ca_bundle,required=true \
    apt-get update && apt-get install -y --no-install-recommends \
    git curl file build-essential pkg-config libmariadb-dev mariadb-client \
    libcairo2 libmagic1 libpango-1.0-0 libpangocairo-1.0-0 \
    && rm -rf /var/lib/apt/lists/*
RUN --mount=type=secret,id=ca_bundle,required=true \
    PIP_CERT=/run/secrets/ca_bundle pip install --no-cache-dir frappe-bench uv \
    && CURL_CA_BUNDLE=/run/secrets/ca_bundle curl -fsSL \
       https://nodejs.org/dist/v24.19.0/node-v24.19.0-linux-x64.tar.xz \
       | tar -xJ -C /opt \
    && ln -s /opt/node-v24.19.0-linux-x64/bin/node /usr/local/bin/node \
    && ln -s /opt/node-v24.19.0-linux-x64/bin/npm /usr/local/bin/npm \
    && NODE_EXTRA_CA_CERTS=/run/secrets/ca_bundle npm install -g yarn@1.22.22 \
    && ln -s /opt/node-v24.19.0-linux-x64/bin/yarn /usr/local/bin/yarn
RUN useradd -m -u 1000 -s /bin/bash frappe \
    && mkdir -p /home/frappe/.pyenv/versions/3.14.8/bin \
    && ln -s /usr/local/bin/python3 /home/frappe/.pyenv/versions/3.14.8/bin/python3 \
    && chown -R frappe:frappe /home/frappe
ENV PATH="/opt/node-v24.19.0-linux-x64/bin:/usr/local/bin:/usr/bin:/bin"
WORKDIR /home/frappe
