ARG UV_VERSION
ARG BASE_IMAGE_TAG

FROM ghcr.io/astral-sh/uv:${UV_VERSION} AS uv
FROM registry.314ecorp.tech/veritable-accounts-base:${BASE_IMAGE_TAG}

ENV DEBIAN_FRONTEND noninteractive

WORKDIR /tmp

# COPY UV script
COPY --from=uv /uv /bin/uv
COPY pyproject.toml poetry.lock /tmp/

# Install Python dependencies
RUN uv pip install --upgrade pip --system && \
    uv pip install -U poetry==1.8.2 setuptools poetry-plugin-export --system && \
    poetry export -f requirements.txt --output requirements.txt --without-hashes --without dev && \
    poetry export -f requirements.txt --output dev_requirements.txt --without-hashes --only dev

FROM registry.314ecorp.tech/launchpad-app-base:${PYTHON_VERSION}-${VERSION}

ENV DEBIAN_FRONTEND noninteractive

COPY rootfs /
WORKDIR /app
COPY . .
COPY --from=requirements-stage /tmp/requirements.txt /tmp/dev_requirements.txt /app/

COPY --from=uv /uv /bin/uv

# Install dependencies
RUN uv pip install --upgrade pip --system && \
    uv pip install -r requirements.txt --system && \
    uv pip install -e . --system && \
    rm /bin/uv

# Expose port and set entrypoint
EXPOSE 8000

WORKDIR /app/formrender
RUN npm i

WORKDIR /app

ENTRYPOINT [ "/init" ]
