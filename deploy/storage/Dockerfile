FROM golang:1.24.8-bookworm AS server-build
WORKDIR /src
RUN git init && git remote add origin https://github.com/minio/minio.git && git fetch --depth 1 origin refs/tags/RELEASE.2025-09-07T16-13-09Z && git checkout FETCH_HEAD
RUN CGO_ENABLED=0 go build -trimpath -o /out/minio .

FROM golang:1.24.8-bookworm AS client-build
WORKDIR /src
RUN git init && git remote add origin https://github.com/minio/mc.git && git fetch --depth 1 origin refs/tags/RELEASE.2025-08-13T08-35-41Z && git checkout FETCH_HEAD
RUN CGO_ENABLED=0 go build -trimpath -o /out/mc .

FROM debian:bookworm-slim AS server
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates && rm -rf /var/lib/apt/lists/* && useradd --uid 10001 app && mkdir /data && chown app /data
COPY --from=server-build /out/minio /usr/local/bin/minio
USER app
EXPOSE 9000 9001
ENTRYPOINT ["minio"]

FROM debian:bookworm-slim AS client
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates && rm -rf /var/lib/apt/lists/*
COPY --from=client-build /out/mc /usr/local/bin/mc
ENTRYPOINT ["mc"]
