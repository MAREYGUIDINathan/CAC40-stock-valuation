FROM apache/airflow:3.1.8

COPY requirements.txt /requirements.txt

USER airflow
RUN pip install --no-cache-dir -r /requirements.txt \
    && playwright install chromium

USER root
RUN PYTHONPATH=/home/airflow/.local/lib/python3.12/site-packages \
    python3.12 -m playwright install-deps chromium \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

USER airflow
