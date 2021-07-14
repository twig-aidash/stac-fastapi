FROM postgres:13 as pg

LABEL maintainer="Shivashis Padhi"

ENV PGUSER darthshivv
ENV PGDATABASE test1
ENV PGHOST host.docker.internal
ENV PGPORT 5432
ENV PGPASSWORD dummy

# EXPOSE 5432

RUN mkdir -p /docker-entrypoint-initdb.d
# COPY ./docker/initpgstac.sh /docker-entrypoint-initdb.d/initpgstac.sh
# COPY ./pgstac.sql /workspaces/pgstac.sql
COPY ./sql /sql

WORKDIR /workspaces