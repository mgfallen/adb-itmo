FROM apache/superset:4.1.1

USER root
RUN pip install --no-cache-dir "sqlalchemy-vertica-python>=0.5.9,<0.6" vertica-python
USER superset
