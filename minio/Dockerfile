# syntax=docker/dockerfile:1

ARG GO_VERSION=1.24
ARG ALPINE_VERSION=3.21

FROM golang:${GO_VERSION}-alpine AS source

RUN apk add --no-cache git

WORKDIR /src

ENV CGO_ENABLED=0 \
    GOFLAGS=-trimpath


FROM source AS minio-build

ARG MINIO_RELEASE=RELEASE.2025-04-08T15-41-24Z
ARG MINIO_VERSION=2025-04-08T15:41:24Z

RUN --mount=type=cache,target=/root/go/pkg/mod \
    --mount=type=cache,target=/root/.cache/go-build \
    for attempt in 1 2 3 4 5; do \
        git clone --depth 1 --branch "${MINIO_RELEASE}" https://github.com/minio/minio.git . && break; \
        rm -rf /src/* /src/.git; sleep $((attempt * 5)); \
    done \
    && for attempt in 1 2 3 4 5; do go mod download && break; sleep $((attempt * 5)); done \
    && go build -o /out/minio -ldflags "-s -w \
        -X github.com/minio/minio/cmd.Version=${MINIO_VERSION} \
        -X github.com/minio/minio/cmd.ReleaseTag=${MINIO_RELEASE} \
        -X github.com/minio/minio/cmd.CommitID=$(git rev-parse HEAD)" .


FROM source AS mc-build

ARG MC_RELEASE=RELEASE.2025-04-08T15-39-49Z
ARG MC_VERSION=2025-04-08T15:39:49Z

RUN --mount=type=cache,target=/root/go/pkg/mod \
    --mount=type=cache,target=/root/.cache/go-build \
    for attempt in 1 2 3 4 5; do \
        git clone --depth 1 --branch "${MC_RELEASE}" https://github.com/minio/mc.git . && break; \
        rm -rf /src/* /src/.git; sleep $((attempt * 5)); \
    done \
    && for attempt in 1 2 3 4 5; do go mod download && break; sleep $((attempt * 5)); done \
    && go build -o /out/mc -ldflags "-s -w \
        -X github.com/minio/mc/cmd.Version=${MC_VERSION} \
        -X github.com/minio/mc/cmd.ReleaseTag=${MC_RELEASE} \
        -X github.com/minio/mc/cmd.CommitID=$(git rev-parse HEAD)" .


FROM alpine:${ALPINE_VERSION} AS runtime-base

RUN apk add --no-cache ca-certificates curl


FROM runtime-base AS minio

COPY --from=minio-build /out/minio /usr/bin/minio

EXPOSE 9000 9001

ENTRYPOINT ["minio"]


FROM runtime-base AS mc

COPY --from=mc-build /out/mc /usr/bin/mc

ENTRYPOINT ["mc"]
