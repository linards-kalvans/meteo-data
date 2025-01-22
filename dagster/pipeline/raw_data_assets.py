import dagster
import polars as pl
from pathlib import Path
from datetime import datetime
import csv

from .api_wrapper import Forecast

logger = dagster.get_dagster_logger()

with open(Path(__file__).parent / "config" / "lv_grid.csv", 'r') as myfile:
    reader = csv.DictReader(myfile)
    lv_grid = [row for row in reader]

class MDConfig(dagster.Config):
    grid: list[dict] = lv_grid

# Initialize forecast object globally to reuse cache on multiple assets
forecast = Forecast()

@dagster.asset(group_name="raw_data")
def raw_lv_grid(config: MDConfig) -> tuple[pl.DataFrame, pl.DataFrame]:
    all_data = [forecast.get_data(row["latitude"], row["longitude"]) for row in config.grid]
    forecast_data = pl.concat([data[0] for data in all_data])
    current_data = pl.concat([data[1] for data in all_data])
    return forecast_data, current_data

@dagster.asset(
    group_name="raw_data",
    io_manager_key="polars_io_manager",
    key_prefix=f"{datetime.now().year}_{datetime.now().month}_{datetime.now().day}_{datetime.now().hour}",
    metadata={"description": "Get forecast weather data for the LV grid"},
)
def forecast_lv_grid(raw_lv_grid: tuple[pl.DataFrame, pl.DataFrame]) -> pl.DataFrame:
    return raw_lv_grid[0]

@dagster.asset(
    group_name="raw_data",
    io_manager_key="polars_io_manager",
    key_prefix=f"{datetime.now().year}_{datetime.now().month}_{datetime.now().day}_{datetime.now().hour}",
    metadata={"description": "Get current weather data for the LV grid"},
)
def current_weather_lv_grid(raw_lv_grid: tuple[pl.DataFrame, pl.DataFrame]) -> pl.DataFrame:
    return raw_lv_grid[1]

