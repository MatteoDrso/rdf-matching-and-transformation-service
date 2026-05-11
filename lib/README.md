# Karma JAR

Place the built Karma offline RDF generator JAR here, e.g.:

    lib/karma-spark-0.0.1-SNAPSHOT-shaded.jar

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

Two patches to the upstream POMs are required before the build succeeds:

1. **Enable the `karma-spark` module** in the parent `pom.xml`:

   ```diff
   - <!--    <module>karma-spark</module>-->
   + <module>karma-spark</module>
   ```

2. **Drop the dead `karma-mr` dependency** from `karma-spark/pom.xml`.
   `karma-mr` pulls in old Hadoop / Cloudera / Pentaho artefacts that live
   on HTTP-only repositories which Maven 3.8+ blocks by default; and
   `karma-spark`'s source code does not actually use any `karma-mr` classes,
   so the dependency is dead weight.

   Remove the whole `<dependency>...karma-mr...</dependency>` block
   (~30 lines starting with `<groupId>edu.isi</groupId><artifactId>karma-mr</artifactId>`).
   Leave the `karma-mr` `<module>` entry commented out in the parent POM.

Then build the shaded fat-JAR (the `OfflineRdfGenerator` CLI lives in
`karma-offline` but is bundled into `karma-spark`'s shaded artefact):

```bash
mvn -DskipTests -P shaded -Denv=shaded -pl karma-spark -am package
```

- `-P shaded` activates the `maven-shade-plugin` profile.
- `-Denv=shaded` sets the artefact classifier, producing the filename
  `karma-spark-0.0.1-SNAPSHOT-shaded.jar` (matches the InfAI command).
- `-pl karma-spark -am` scopes the reactor to `karma-spark` and the
  modules it depends on (also-make), skipping unrelated heavy modules
  like `karma-web` and `karma-research`.
- First build is ~10–15 min (Maven downloads everything); subsequent
  builds are seconds from the local `~/.m2/repository` cache.

Copy the result:

```bash
cp karma-spark/target/karma-spark-0.0.1-SNAPSHOT-shaded.jar \
   /path/to/SP_WP8_SS26/lib/
```

## Verify

The repo ships an InfAI-provided sample (`examples/*_oboe.ttl` is the
ground truth). Reproduce it:

```bash
cd /path/to/SP_WP8_SS26/examples
java -cp ../lib/karma-spark-0.0.1-SNAPSHOT-shaded.jar \
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
