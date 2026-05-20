# syntax=docker/dockerfile:1.7

# ── Stage 1: Karma JAR build ──────────────────────────────────────────────
FROM maven:3.9-eclipse-temurin-11 AS karma-build

# Pin to a specific Karma revision for reproducibility. Override at build
# time with --build-arg KARMA_REF=<sha-or-branch>.
ARG KARMA_REF=master

# `zip` is needed for the JAR-trim step below; install it once here so the
# trim iteration step doesn't depend on apt network availability. The
# `--fix-missing` + tolerated update lets the build survive intermittent
# noble-security mirror sync failures (Ubuntu ports mirror is flaky).
RUN apt-get -o Acquire::Retries=5 update || true \
 && apt-get install -y --no-install-recommends --fix-missing zip \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /src
RUN git clone --depth 1 --branch "${KARMA_REF}" \
      https://github.com/usc-isi-i2/Web-Karma.git .

# Build the shaded fat JAR for the karma-offline module. `OfflineRdfGenerator`
# lives in karma-offline; karma-spark only adds a Spark-cluster wrapper that
# we do not use and that pulls Spark + Hadoop + Scala into the artefact.
# `-pl karma-offline -am` scopes the reactor; `-P shaded` activates the
# maven-shade-plugin profile (shadedClassifierName="shaded").
RUN --mount=type=cache,target=/root/.m2 \
    mvn -B -DskipTests -P shaded -pl karma-offline -am package \
 && cp karma-offline/target/karma-offline-*-shaded.jar /tmp/karma.jar

# Lean trim: the upstream karma-offline shade config bundles ~250 MB of
# dependencies we never use (Spark, Hadoop, Scala runtime, native BLAS,
# Apache POI / OOXML, MySQL JDBC, NASA NetCDF README PDFs, …). The transform
# path we hit is CSV/TSV/JSON + Turtle model + Python pre-transforms, so we
# delete the unused payload directly from the JAR with `zip -d`. Keep:
# Jython (`org/python/**` — pyTransform), Jena (`com/hp/hpl/**`), Lucene,
# Guava, Jackson, commons-*, bouncycastle, Sesame/openrdf, edu/isi.
RUN zip -d /tmp/karma.jar \
      'org/apache/spark/*' \
      'org/apache/hadoop/*' \
      'scala/*' \
      'breeze/*' \
      'spire/*' \
      'netlib-native_*' \
      'resources/grib1/*' \
      'com/mysql/*' \
      'org/apache/poi/*' \
      'org/openxmlformats/*' \
      'org/apache/cxf/*' \
      'org/apache/xmlbeans/*' \
    > /tmp/trim.log \
 && echo "JAR size after trim:" && ls -lh /tmp/karma.jar


# ── Stage 2: runtime ──────────────────────────────────────────────────────
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    KARMA_JAR=/app/lib/karma-offline-shaded.jar

RUN apt-get update \
 && apt-get install -y --no-install-recommends default-jre-headless tini \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --from=karma-build /tmp/karma.jar ${KARMA_JAR}

COPY main.py ./
COPY src ./src

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD python -c "import urllib.request, sys; \
sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/', timeout=3).status == 200 else 1)" \
  || exit 1

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
