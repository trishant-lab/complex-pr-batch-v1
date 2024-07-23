FROM registry.314ecorp.tech/launchpad-app-base as requirements-stage

ENV DEBIAN_FRONTEND noninteractive

WORKDIR /tmp

COPY pyproject.toml poetry.lock /tmp/

RUN pip install --upgrade pip
RUN pip install -U poetry==1.8.2 setuptools poetry-plugin-export
RUN poetry export -f requirements.txt --output requirements.txt --without-hashes --without dev
RUN poetry export -f requirements.txt --output dev_requirements.txt --without-hashes --with dev

FROM registry.314ecorp.tech/launchpad-app-base

ENV DEBIAN_FRONTEND noninteractive

COPY rootfs /
WORKDIR /app
COPY . .
COPY --from=requirements-stage /tmp/requirements.txt /tmp/dev_requirements.txt /app/

# poetry
RUN pip install --upgrade pip && \
  pip install -U setuptools && \
  pip install -r requirements.txt && \
  pip install -e .

EXPOSE 8000

WORKDIR /app/formrender
RUN npm i

WORKDIR /app

ENTRYPOINT [ "/init" ]
