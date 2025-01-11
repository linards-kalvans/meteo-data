FROM python:3.11-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Change the working directory to the `app` directory
ENV DAGSTER_HOME=/opt/dagster/dagster_home/

RUN mkdir -p $DAGSTER_HOME

WORKDIR $DAGSTER_HOME

# Install dependencies
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    --mount=type=bind,source=.python-version,target=.python-version \
    uv sync --frozen

ENV PATH="${DAGSTER_HOME}.venv/bin:$PATH"

COPY dagster.yaml workspace.yaml $DAGSTER_HOME

COPY pipeline $DAGSTER_HOME/pipeline
