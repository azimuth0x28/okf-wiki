# okf-wiki memory service: one container, one bundle on a mounted volume.
# Build: docker build -t okf-wiki --build-arg VERSION=2026.9.0 .
# Run:   docker run -p 8080:8080 -e WIKI_API_KEY=... -v okf-bundle:/bundle okf-wiki
FROM python:3.12-slim

# git: okf_wiki/sync.py shells out to it for bundle backup.
RUN apt-get update && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /src
COPY . .
# .git is excluded from the build context (see .dockerignore), so hatch-vcs
# cannot read the tag. CI passes the real one: --build-arg VERSION=2026.9.0
ARG VERSION=0.0.0.dev0
ENV HATCH_VCS_PRETEND_VERSION=$VERSION
RUN pip install --no-cache-dir '.[server]'

RUN useradd --create-home wiki && mkdir -p /bundle && chown wiki:wiki /bundle
USER wiki

# A8 contract: the bundle lives on a mounted volume; the Config Resolution
# Protocol picks it up through OKF_BUNDLE_PATH.
ENV OKF_BUNDLE_PATH=/bundle WIKI_PORT=8080
VOLUME /bundle
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8080/health').status==200 else 1)"

CMD ["python", "-m", "okf_wiki.server"]
