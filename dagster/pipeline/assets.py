import dagster
import polars as pl
from pathlib import Path
from datetime import datetime
import csv
import os
from dagster_duckdb import DuckDBResource

from .api_wrapper import Forecast

logger = dagster.get_dagster_logger()

with open(Path(__file__).parent / "config" / "lv_grid.csv", 'r') as myfile:
    reader = csv.DictReader(myfile)
    lv_grid = [row for row in reader]

class MDConfig(dagster.Config):
    grid: list[dict] = lv_grid

# Initialize forecast object globally to reuse cache on multiple assets
forecast = Forecast()

@dagster.asset
def raw_lv_grid(config: MDConfig) -> tuple[pl.DataFrame, pl.DataFrame]:
    all_data = [forecast.get_data(row["latitude"], row["longitude"]) for row in config.grid]
    forecast_data = pl.concat([data[0] for data in all_data])
    current_data = pl.concat([data[1] for data in all_data])
    return forecast_data, current_data

@dagster.asset(
    io_manager_key="polars_io_manager",
    key_prefix=f"{datetime.now().year}_{datetime.now().month}_{datetime.now().day}_{datetime.now().hour}",
    metadata={"description": "Get forecast weather data for the LV grid"},
)
def forecast_lv_grid(raw_lv_grid: tuple[pl.DataFrame, pl.DataFrame]) -> pl.DataFrame:
    return raw_lv_grid[0]

@dagster.asset(
    io_manager_key="polars_io_manager",
    key_prefix=f"{datetime.now().year}_{datetime.now().month}_{datetime.now().day}_{datetime.now().hour}",
    metadata={"description": "Get current weather data for the LV grid"},
)
def current_weather_lv_grid(raw_lv_grid: tuple[pl.DataFrame, pl.DataFrame]) -> pl.DataFrame:
    return raw_lv_grid[1]

@dagster.asset
def duckdb_secrets(duckdb: DuckDBResource) -> None:
    with duckdb.get_connection() as conn:
        conn.sql(
            f"""
            CREATE SECRET secret1 (
                TYPE S3,
                KEY_ID '{os.getenv('AWS_ACCESS_KEY_ID')}',
                SECRET '{os.getenv('AWS_SECRET_ACCESS_KEY')}',
                ENDPOINT '{os.getenv('OBJECT_STORAGE_PRIVATE_ENDPOINT').replace('https://', '')}'
            )
            """
        )

@dagster.asset(
    deps=[duckdb_secrets]
)
def last_transform_date(duckdb: DuckDBResource) -> datetime:
    with duckdb.get_connection() as conn:
        try:
            return conn.sql("SELECT CAST(MAX(date) AS DATE) AS last_transform_date FROM 's3://processed-data/processed_data*.parquet'").fetchone()[0]
        except Exception as e:
            logger.warning(f"Error getting last transform date: {e}")
            return datetime(2024, 1, 1) # If no data return date well in the past
