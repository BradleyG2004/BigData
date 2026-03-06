FROM apache/spark:4.0.1-python3

# Install Python dependencies as root
USER root
RUN pip3 install --no-cache-dir psycopg2-binary

# Switch back to spark user
USER ${spark_uid}

# Set working directory
WORKDIR /opt/spark
