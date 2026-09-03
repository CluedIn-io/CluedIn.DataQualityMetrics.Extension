FROM ubuntu:22.04

# freetds is required by pymssql.
RUN apt-get update && \
  apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    freetds-bin \
    freetds-common \
    freetds-dev && \
  ln -sf /usr/bin/python3 /usr/bin/python && \
  ln -sf /usr/bin/pip3 /usr/bin/pip && \
  rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

COPY *.py /app/

# The metrics configuration is supplied at run time -- from a ConfigMap in
# Kubernetes, or a bind mount locally -- so that no instance-specific
# configuration is baked into the image.
ENV METRICS_CONFIG=/etc/cluedin-metrics/metrics.json
ENV PYTHONUNBUFFERED=true

ENTRYPOINT ["python", "./metrics.py"]
