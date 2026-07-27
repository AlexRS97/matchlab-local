FROM python:3.12-slim
WORKDIR /usr/app/dbt
RUN pip install --no-cache-dir dbt-core==1.9.2 dbt-postgres==1.9.0
COPY dbt ./
ENTRYPOINT ["dbt"]
CMD ["build", "--profiles-dir", "."]
