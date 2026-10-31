FROM apache/superset:4.1.1

USER root
RUN pip install --no-cache-dir vertica-python sqlalchemy-vertica
USER superset
