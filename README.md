<p align="center">
  <img src="https://github.com/radiantearth/stac-site/raw/master/images/logo/stac-030-long.png" width=400>
  <p align="center">FastAPI implemention of the STAC API spec.</p>
</p>
<p align="center">
  <a href="https://github.com/stac-utils/stac-fastapi/actions?query=workflow%3Acicd" target="_blank">
      <img src="https://github.com/stac-utils/stac-fastapi/workflows/stac-fastapi/badge.svg" alt="Test">
  </a>
  <a href="https://pypi.org/project/stac-fastapi" target="_blank">
      <img src="https://img.shields.io/pypi/v/stac-fastapi?color=%2334D058&label=pypi%20package" alt="Package version">
  </a>
  <a href="https://github.com/stac-utils/stac-fastapi/blob/master/LICENSE" target="_blank">
      <img src="https://img.shields.io/github/license/stac-utils/stac-fastapi.svg" alt="Downloads">
  </a>
</p>

---

**Documentation**: [https://stac-utils.github.io/stac-fastapi/](https://stac-utils.github.io/stac-fastapi/)

**Source Code**: [https://github.com/stac-utils/stac-fastapi](https://github.com/stac-utils/stac-fastapi)

---

Python library for building a STAC compliant FastAPI application.  The project is split up into several namespace
packages:

- **stac_fastapi.api**: An API layer which enforces the [stac-api-spec](https://github.com/radiantearth/stac-api-spec).
- **stac_fastapi.extensions**: Abstract base classes for [STAC API extensions](https://github.com/radiantearth/stac-api-spec/blob/master/extensions.md) and third-party extensions.
- **stac_fastapi.server**: Standalone FastAPI server for the application.
- **stac_fastapi.sqlalchemy**: Postgres backend implementation with sqlalchemy.
- **stac_fastapi.types**: Shared types and abstract base classes used by the library.

`stac-fastapi` was initially developed by [arturo-ai](https://github.com/arturo-ai).

## Installation

```
pip install stac-fastapi

# or from sources

git clone https://github.com/stac-utils/stac-fastapi.git
cd stac-fastapi
pip install -e \
    stac_fastapi/api \
    stac_fastapi/types \
    stac_fastapi/extensions \
    stac_fastapi/sqlalchemy
```

## Local Development
Use docker-compose to deploy the application, migrate the database, and ingest some example data:
```bash
docker-compose build
docker-compose up
```

For local development it is often more convenient to run the application outside of docker-compose:
```bash
make docker-run
```


### Testing
The database container provided by the docker-compose stack must be running.  Run all tests:
```bash
make test
```

Run individual tests by running pytest within the docker container:
```bash
make docker-shell
$ pytest -v
```

## Aidash specific

### Local dev

  $ docker-compose -f docker-compose.dev.yml up --build --force-recreate

### Deploying to AWS

 - Setup [ECS CLI](https://github.com/aws/amazon-ecs-cli/pull/1105)
 - Read through [sample deployment to Fargate](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/ecs-cli-tutorial-fargate.html)
 - setup docker [ecs](https://www.docker.com/blog/docker-compose-from-local-to-amazon-ecs/), or [ecs-cli compose](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/cmd-ecs-cli-compose-up.html) to deploy.
 - `cp ecs-params.example.yml ecs-params.yml`, one has to replace subnet ids, and security group id in this file before deploying.
