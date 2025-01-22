from dagster import (
    Definitions,
    load_assets_from_modules,
    ScheduleDefinition,
    DefaultScheduleStatus,
    AssetSelection,
    define_asset_job
)
from dagster_polars import PolarsParquetIOManager
from dagster_duckdb import DuckDBResource
import tempfile
from pathlib import Path
from . import raw_data_assets
from . import processed_data_assets
import os

# polars_base_dir = (Path(__file__).parent.parent / "data").as_posix()
polars_base_dir = "s3://md-raw-data"
storage_options = {
    "endpoint_url": os.getenv("OBJECT_STORAGE_PRIVATE_ENDPOINT"),
}

raw_data_assets = load_assets_from_modules([raw_data_assets])

processed_data_assets = load_assets_from_modules([processed_data_assets])

raw_data = define_asset_job("raw_data", raw_data_assets)
processed_data = define_asset_job("processed_data", processed_data_assets)

md_raw_data_schedule = ScheduleDefinition(
    name="md_raw_data_schedule",
    cron_schedule="0 */12 * * *",
    target=raw_data,
    default_status=DefaultScheduleStatus.RUNNING
)

md_processed_data_schedule = ScheduleDefinition(
    name="md_processed_data_schedule",
    cron_schedule="0 2 * * *",
    target=processed_data,
    default_status=DefaultScheduleStatus.RUNNING
)

defs = Definitions(
    assets=raw_data_assets + processed_data_assets,
    jobs=[raw_data, processed_data],
    resources={
        "polars_io_manager": PolarsParquetIOManager(
            base_dir=polars_base_dir,
            storage_options=storage_options
        ),
        "polars_io_manager_transformed": PolarsParquetIOManager(
            base_dir="s3://processed-data",
            storage_options=storage_options
        ),
        "duckdb": DuckDBResource(
            database=str(Path(tempfile.gettempdir()) / "duckdb.db")
        )
    },
    schedules=[md_raw_data_schedule, md_processed_data_schedule],
)
