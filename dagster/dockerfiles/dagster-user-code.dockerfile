FROM ghcr.io/astral-sh/uv:latest

RUN uv init && \
    uv add \
    dagster \
    dagster-postgres \
    dagster-docker

# Add repository code

WORKDIR /opt/dagster/app

COPY pipeline /opt/dagster/app

# Run dagster gRPC server on port 4000

EXPOSE 4000

# CMD allows this to be overridden from run launchers or executors that want
# to run other commands against your repository
CMD ["dagster", "api", "grpc", "-h", "0.0.0.0", "-p", "4000", "-m", "pipeline.definitions"]
