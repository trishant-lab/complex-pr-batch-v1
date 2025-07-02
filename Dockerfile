ARG UV_VERSION
ARG BASE_IMAGE_TAG

FROM ghcr.io/astral-sh/uv:${UV_VERSION} AS uv
FROM registry.314ecorp.tech/launchpad-app-base:${BASE_IMAGE_TAG}

ENV DEBIAN_FRONTEND noninteractive

RUN curl -sSf https://atlasgo.sh | sh -s -- -y

COPY rootfs /
WORKDIR /app
COPY . .

COPY --from=uv /uv /bin/uv

# Set up Python virtual environment and install dependencies
RUN uv pip install --upgrade pip --system --resolution highest && \
    uv export --format requirements-txt --frozen --no-dev > requirements.txt && \
    uv export --format requirements-txt --frozen --only-dev > requirements-dev.txt && \
    uv pip install --system -r requirements.txt && \
    rm /bin/uv

# Expose port and set entrypoint
EXPOSE 8000

WORKDIR /app/form_render
RUN npm i

WORKDIR /app

RUN python app/pre_commit_checks.py

ENTRYPOINT [ "/init" ]
