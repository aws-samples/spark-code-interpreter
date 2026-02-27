#!/usr/bin/env bash
FRAMEWORK=$1
SPARK_HOME=$2
HADOOP_VERSION=$3
AWS_SDK_VERSION=$4
DELTA_FRAMEWORK_VERSION=$5
HUDI_FRAMEWORK_VERSION=$6
ICEBERG_FRAMEWORK_VERSION=$7
ICEBERG_FRAMEWORK_SUB_VERSION=$8
DEEQU_FRAMEWORK_VERSION=$9

# Debug: Show what we received
echo "DEBUG: Received arguments:"
echo "  FRAMEWORK='$FRAMEWORK'"
echo "  SPARK_HOME='$SPARK_HOME'"
echo "  HADOOP_VERSION='$HADOOP_VERSION'"
echo "  AWS_SDK_VERSION='$AWS_SDK_VERSION'"
echo ""

# Validate SPARK_HOME exists
if [ ! -d "$SPARK_HOME" ]; then
    echo "ERROR: SPARK_HOME directory does not exist: $SPARK_HOME"
    exit 1
fi

mkdir -p $SPARK_HOME/conf
echo "SPARK_LOCAL_IP=127.0.0.1" > $SPARK_HOME/conf/spark-env.sh
echo "JAVA_HOME=/usr/lib/jvm/$(ls /usr/lib/jvm |grep java)/jre" >> $SPARK_HOME/conf/spark-env.sh

echo "=========================================="
echo "Downloading S3 JARs for Spark on Lambda"
echo "=========================================="
echo "Hadoop Version: ${HADOOP_VERSION}"
echo "AWS SDK Version: ${AWS_SDK_VERSION}"
echo "Target Directory: ${SPARK_HOME}/jars/"
echo ""

# Function to download JAR with error checking
download_jar() {
    local url=$1
    local jar_name=$(basename $url)
    
    echo "Downloading ${jar_name}..."
    if wget --progress=dot:giga -O ${SPARK_HOME}/jars/${jar_name} ${url}; then
        if [ -f "${SPARK_HOME}/jars/${jar_name}" ]; then
            local size=$(stat -f%z "${SPARK_HOME}/jars/${jar_name}" 2>/dev/null || stat -c%s "${SPARK_HOME}/jars/${jar_name}" 2>/dev/null || echo "0")
            if [ "$size" -gt 1000 ]; then
                echo "✓ Downloaded ${jar_name} ($(numfmt --to=iec $size 2>/dev/null || echo "${size} bytes"))"
                return 0
            else
                echo "✗ ERROR: ${jar_name} is too small (${size} bytes) - download may have failed"
                return 1
            fi
        else
            echo "✗ ERROR: ${jar_name} not found after download"
            return 1
        fi
    else
        echo "✗ ERROR: Failed to download ${jar_name}"
        return 1
    fi
}

# Download core S3 filesystem JARs with updated versions
echo "Downloading CRITICAL S3 JARs..."
download_jar "https://repo1.maven.org/maven2/org/apache/hadoop/hadoop-aws/${HADOOP_VERSION}/hadoop-aws-${HADOOP_VERSION}.jar" || exit 1
download_jar "https://repo1.maven.org/maven2/com/amazonaws/aws-java-sdk-bundle/${AWS_SDK_VERSION}/aws-java-sdk-bundle-${AWS_SDK_VERSION}.jar" || exit 1

echo ""
echo "Downloading additional Hadoop JARs..."
# Additional JARs for better S3 compatibility (non-critical, don't fail build)
download_jar "https://repo1.maven.org/maven2/org/apache/hadoop/hadoop-common/${HADOOP_VERSION}/hadoop-common-${HADOOP_VERSION}.jar" || echo "Warning: hadoop-common download failed (non-critical)"
download_jar "https://repo1.maven.org/maven2/org/apache/hadoop/hadoop-client/${HADOOP_VERSION}/hadoop-client-${HADOOP_VERSION}.jar" || echo "Warning: hadoop-client download failed (non-critical)"
download_jar "https://repo1.maven.org/maven2/org/apache/hadoop/hadoop-client-api/${HADOOP_VERSION}/hadoop-client-api-${HADOOP_VERSION}.jar" || echo "Warning: hadoop-client-api download failed (non-critical)"
download_jar "https://repo1.maven.org/maven2/org/apache/hadoop/hadoop-client-runtime/${HADOOP_VERSION}/hadoop-client-runtime-${HADOOP_VERSION}.jar" || echo "Warning: hadoop-client-runtime download failed (non-critical)"

# jar files needed to conncet to Snowflake
#wget -q https://repo1.maven.org/maven2/net/snowflake/spark-snowflake_2.12/2.12.0-spark_3.3/spark-snowflake_2.12-2.12.0-spark_3.3.jar -P ${SPARK_HOME}/jars/
#wget -q https://repo1.maven.org/maven2/net/snowflake/snowflake-jdbc/3.13.33/snowflake-jdbc-3.13.33.jar -P ${SPARK_HOME}/jars/

echo 'Framework is:'
echo $FRAMEWORK

IFS=',' read -ra FRAMEWORKS <<< "$FRAMEWORK"

for fw in "${FRAMEWORKS[@]}"; do
echo $fw
    case "$fw" in
        HUDI)
            wget -q https://repo1.maven.org/maven2/org/apache/hudi/hudi-spark3.3-bundle_2.12/${HUDI_FRAMEWORK_VERSION}/hudi-spark3.3-bundle_2.12-${HUDI_FRAMEWORK_VERSION}.jar -P ${SPARK_HOME}/jars/
            ;;
        DELTA)
            wget -q https://repo1.maven.org/maven2/io/delta/delta-core_2.12/${DELTA_FRAMEWORK_VERSION}/delta-core_2.12-${DELTA_FRAMEWORK_VERSION}.jar -P ${SPARK_HOME}/jars/
            wget -q https://repo1.maven.org/maven2/io/delta/delta-storage/${DELTA_FRAMEWORK_VERSION}/delta-storage-${DELTA_FRAMEWORK_VERSION}.jar -P ${SPARK_HOME}/jars/
            ;;
        ICEBERG)
            wget -q https://repo1.maven.org/maven2/org/apache/iceberg/iceberg-spark-runtime-${ICEBERG_FRAMEWORK_VERSION}/${ICEBERG_FRAMEWORK_SUB_VERSION}/iceberg-spark-runtime-${ICEBERG_FRAMEWORK_VERSION}-${ICEBERG_FRAMEWORK_SUB_VERSION}.jar -P ${SPARK_HOME}/jars/
            wget -q https://repo1.maven.org/maven2/software/amazon/awssdk/bundle/2.20.23/bundle-2.20.23.jar -P ${SPARK_HOME}/jars/
            wget -q https://repo1.maven.org/maven2/software/amazon/awssdk/url-connection-client/2.20.23/url-connection-client-2.20.23.jar -P ${SPARK_HOME}/jars/
            ;;
        SNOWFLAKE)
            wget -q https://repo1.maven.org/maven2/net/snowflake/spark-snowflake_2.12/2.12.0-spark_3.3/spark-snowflake_2.12-2.12.0-spark_3.3.jar -P ${SPARK_HOME}/jars/
            wget -q https://repo1.maven.org/maven2/net/snowflake/snowflake-jdbc/3.13.33/snowflake-jdbc-3.13.33.jar -P ${SPARK_HOME}/jars/
            ;;
        REDSHIFT)
            wget -q https://repo1.maven.org/maven2/io/github/spark-redshift-community/spark-redshift_2.12/4.1.1/spark-redshift_2.12-4.1.1.jar -P ${SPARK_HOME}/jars/
            wget -q https://repo1.maven.org/maven2/org/apache/spark/spark-avro_2.13/3.3.0/spark-avro_2.13-3.3.0.jar  -P ${SPARK_HOME}/jars/
            wget -q https://s3.amazonaws.com/redshift-downloads/drivers/jdbc/2.1.0.18/redshift-jdbc42-2.1.0.18.zip -P ${SPARK_HOME}/jars/
            wget -q https://repo1.maven.org/maven2/com/eclipsesource/minimal-json/minimal-json/0.9.1/minimal-json-0.9.1.jar -P ${SPARK_HOME}/jars/
            # Unzip the Redshift JDBC driver
            unzip -o ${SPARK_HOME}/jars/redshift-jdbc42-2.1.0.18.zip -d ${SPARK_HOME}/jars/
            ;;
        DEEQU)
            wget -q https://repo1.maven.org/maven2/com/amazon/deequ/deequ/${DEEQU_FRAMEWORK_VERSION}/deequ-${DEEQU_FRAMEWORK_VERSION}.jar -P ${SPARK_HOME}/jars/
            ;;
        *)
            echo "Unknown framework: $fw"
            ;;
    esac
done

echo ""
echo "=========================================="
echo "VERIFICATION: Checking Critical JARs"
echo "=========================================="

# Verify critical S3 JARs are present
CRITICAL_JARS=(
    "hadoop-aws-${HADOOP_VERSION}.jar"
    "aws-java-sdk-bundle-${AWS_SDK_VERSION}.jar"
)

VERIFICATION_FAILED=0

for jar in "${CRITICAL_JARS[@]}"; do
    if [ -f "${SPARK_HOME}/jars/${jar}" ]; then
        size=$(stat -f%z "${SPARK_HOME}/jars/${jar}" 2>/dev/null || stat -c%s "${SPARK_HOME}/jars/${jar}" 2>/dev/null || echo "0")
        if [ "$size" -gt 1000 ]; then
            echo "✓ ${jar} present ($(numfmt --to=iec $size 2>/dev/null || echo "${size} bytes"))"
        else
            echo "✗ ${jar} is too small (${size} bytes)"
            VERIFICATION_FAILED=1
        fi
    else
        echo "✗ ${jar} MISSING"
        VERIFICATION_FAILED=1
    fi
done

echo ""
if [ $VERIFICATION_FAILED -eq 0 ]; then
    echo "✓ All critical S3 JARs verified successfully"
    echo "=========================================="
    exit 0
else
    echo "✗ VERIFICATION FAILED: Missing or invalid critical JARs"
    echo "=========================================="
    exit 1
fi