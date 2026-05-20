# Karma JAR

Place the built Karma offline RDF generator JAR here, e.g.:

    lib/karma-offline-0.0.1-SNAPSHOT-shaded.jar

The JAR is **not** distributed via GitHub releases (the upstream Web-Karma
repository was archived on 16 April 2025). Build it from source — the
recipe below is the one that actually works on macOS / Linux with current
Maven, validated against the InfAI ground truth (`examples/*_oboe.ttl`).

## Prerequisites

- **JDK 11** — Karma is Java-8/11 code; Java 17+ has compatibility issues.
  On macOS Homebrew: `brew install openjdk@11` (the `temurin@11` *cask*
  works too but needs `sudo`; the keg-only formula does not).
- **Maven 3.9+** — `brew install maven`.
- **Git**, plus ~1 GB free disk for the local Maven cache.

Point Maven at JDK 11 explicitly (otherwise it may pick up a newer JDK that
ships with the Maven formula):

```bash
export JAVA_HOME=/opt/homebrew/opt/openjdk@11/libexec/openjdk.jdk/Contents/Home
export PATH="$JAVA_HOME/bin:$PATH"
java -version   # → openjdk version "11.0.x"
```

## Build

```bash
git clone https://github.com/usc-isi-i2/Web-Karma.git
cd Web-Karma
```

`OfflineRdfGenerator` lives in the `karma-offline` module, which builds
cleanly against current Maven without any POM patches — no `karma-spark`,
no `karma-mr`, no HTTP-only Cloudera / Pentaho repositories to fight.

```bash
mvn -DskipTests -P shaded -pl karma-offline -am package
```

- `-P shaded` activates the `maven-shade-plugin` profile, which produces
  `karma-offline-0.0.1-SNAPSHOT-shaded.jar` (the `shaded` classifier is
  configured inside `karma-offline/pom.xml`).
- `-pl karma-offline -am` scopes the reactor to `karma-offline` and its
  dependencies (also-make), skipping unrelated heavy modules like
  `karma-spark`, `karma-web`, and `karma-research`.
- First build is ~2–4 min (Maven downloads everything); subsequent
  builds are seconds from the local `~/.m2/repository` cache.

Copy the result:

```bash
cp karma-offline/target/karma-offline-0.0.1-SNAPSHOT-shaded.jar \
   /path/to/SP_WP8_SS26/lib/
```

## Verify

The repo ships an InfAI-provided sample (`examples/*_oboe.ttl` is the
ground truth). Reproduce it:

```bash
cd /path/to/SP_WP8_SS26/examples
java -cp ../lib/karma-offline-0.0.1-SNAPSHOT-shaded.jar \
  edu.isi.karma.rdf.OfflineRdfGenerator \
  --sourcetype CSV \
  --filepath plant_height_vegetative_raw_germany_20.csv \
  --delimiter TAB \
  --modelfilepath plant_height_vegetative_raw-model_oboe.ttl \
  --sourcename source \
  --outputfile /tmp/out.ttl

python -c "
from rdflib import Graph
from rdflib.compare import to_isomorphic
a = Graph().parse('/tmp/out.ttl', format='nt')
b = Graph().parse('plant_height_vegetative_raw_germany_20_oboe.ttl', format='nt')
print('isomorphic:', to_isomorphic(a) == to_isomorphic(b), '— triples:', len(a))
"
# → isomorphic: True — triples: 243
```

JAR files in this directory are git-ignored (see `.gitignore`); only this
README is tracked.
