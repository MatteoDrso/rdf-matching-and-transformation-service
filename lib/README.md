# Karma JAR

Place the built Karma offline RDF generator JAR here, e.g.:

    lib/karma-spark-0.0.1-SNAPSHOT-shaded.jar

The JAR is **not** distributed via GitHub releases (the upstream Web-Karma
repository was archived on 16 April 2025). Build it from source:

```bash
git clone https://github.com/usc-isi-i2/Web-Karma.git
cd Web-Karma
mvn -DskipTests package
# the shaded jar will be under karma-spark/target/
cp karma-spark/target/karma-spark-*-shaded.jar /path/to/SP_WP8_SS26/lib/
```

JAR files in this directory are git-ignored (see `.gitignore`).
