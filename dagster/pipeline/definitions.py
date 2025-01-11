from dagster import (
    Definitions,
    load_assets_from_modules,
    ScheduleDefinition,
    DefaultScheduleStatus
)
from dagster_polars import PolarsParquetIOManager
from pathlib import Path
from . import assets
import os

all_assets = load_assets_from_modules([assets])

# polars_base_dir = (Path(__file__).parent.parent / "data").as_posix()
polars_base_dir = "s3://md-raw-data"
storage_options = {
    "endpoint_url": os.getenv("OBJECT_STORAGE_PRIVATE_ENDPOINT"),
}

md_raw_data_schedule = ScheduleDefinition(
    name="md_raw_data_schedule",
    cron_schedule="0 */4 * * *",
    target=all_assets,
    default_status=DefaultScheduleStatus.RUNNING
)

defs = Definitions(
    assets=all_assets,
    resources={
        "polars_io_manager": PolarsParquetIOManager(
            base_dir=polars_base_dir,
            storage_options=storage_options
        )
    },
    schedules=[md_raw_data_schedule],
)
