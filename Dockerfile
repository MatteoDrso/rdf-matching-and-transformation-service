# syntax=docker/dockerfile:1.7

# ── Stage 1: Karma JAR build ──────────────────────────────────────────────
FROM maven:3.9-eclipse-temurin-11 AS karma-build

# Pin to a specific Karma revision for reproducibility. Override at build
# time with --build-arg KARMA_REF=<sha-or-branch>.
ARG KARMA_REF=master

WORKDIR /src
RUN git clone --depth 1 --branch "${KARMA_REF}" \
      https://github.com/usc-isi-i2/Web-Karma.git .

# Patch 1: enable the karma-spark module in the parent reactor.
RUN sed -i 's|<!--\s*<module>karma-spark</module>\s*-->|<module>karma-spark</module>|' pom.xml

# Patch 2: drop the dead karma-mr dependency from karma-spark/pom.xml.
# It pulls old Cloudera / Pentaho artefacts from HTTP-only repositories
# (blocked by Maven 3.8+), and the karma-spark source never uses any
# karma-mr classes — the dependency is dead weight.
RUN awk ' \
    /<dependency>/ { buf=""; in_dep=1 } \
    in_dep { buf = buf $0 ORS } \
    !in_dep { print } \
    /<\/dependency>/ && in_dep { \
        if (buf !~ /karma-mr/) printf "%s", buf; \
        buf=""; in_dep=0 \
    }' karma-spark/pom.xml > karma-spark/pom.xml.new \
 && mv karma-spark/pom.xml.new karma-spark/pom.xml \
 && ! grep -q "<artifactId>karma-mr</artifactId>" karma-spark/pom.xml

# Build the shaded fat JAR. `-pl karma-spark -am` scopes the reactor;
# `-P shaded -Denv=shaded` activates the maven-shade-plugin profile and
# names the artefact karma-spark-0.0.1-SNAPSHOT-shaded.jar.
RUN --mount=type=cache,target=/root/.m2 \
    mvn -B -DskipTests -P shaded -Denv=shaded -pl karma-spark -am package \
 && cp karma-spark/target/karma-spark-*-shaded.jar /tmp/karma.jar


# ── Stage 2: runtime ──────────────────────────────────────────────────────
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    KARMA_JAR=/app/lib/karma-spark-shaded.jar

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
