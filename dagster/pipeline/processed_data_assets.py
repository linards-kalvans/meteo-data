import dagster
import polars as pl
from datetime import datetime
import os
from dagster_duckdb import DuckDBResource

logger = dagster.get_dagster_logger()

@dagster.asset(
    group_name="processed_data",
    metadata={"description": "Create S3 secrets in duckdb"},
)
def duckdb_connect(duckdb: DuckDBResource) -> None:
    with duckdb.get_connection() as conn:
        sql_secrets = f"""
            CREATE PERSISTENT SECRET secret1 (
                TYPE S3,
                KEY_ID '{os.getenv('AWS_ACCESS_KEY_ID')}',
                SECRET '{os.getenv('AWS_SECRET_ACCESS_KEY')}',
                ENDPOINT '{os.getenv('OBJECT_STORAGE_PRIVATE_ENDPOINT').replace('https://', '')}'
            )
            """
        # logger.info(sql_secrets)
        conn.sql(
            sql_secrets
        )
        conn.sql(f"SET memory_limit = '{os.getenv('MEMORY_LIMIT', '512MB')}'")
        conn.sql("SET temp_directory = '/tmp/duckdb_swap'")

@dagster.asset(
    group_name="processed_data",
    deps=[duckdb_connect],
    metadata={"description": "Get last transform date from processed data"},
)
def last_transform_date(duckdb: DuckDBResource) -> datetime:
    with duckdb.get_connection() as conn:
        try:
            return datetime.combine(
                conn.sql("SELECT CAST(MAX(date) AS DATE) AS last_transform_date FROM 's3://processed-data/*/processed_weather_data.parquet'").fetchone()[0],
                datetime.min.time()
            )
        except Exception as e:
            logger.warning(f"Error getting last transform date: {e}")
            return datetime(2024, 1, 1) # If no data return date well in the past

@dagster.asset(
    group_name="processed_data",
    deps=[duckdb_connect],
    metadata={"description": "Get weather data for the LV grid from S3"},
)
def weather_data_lv_grid(last_transform_date: datetime, duckdb: DuckDBResource) -> None:
    with duckdb.get_connection() as conn:
        conn.sql(
            f"""
            CREATE TABLE weather_forecast AS
            SELECT * FROM 's3://md-raw-data/*/forecast_lv_grid.parquet'
            WHERE date > '{last_transform_date}' AND date < '{datetime.now().date()}'
            """
        )
        conn.sql(
            f"""
            CREATE TABLE weather_current AS
            SELECT * FROM 's3://md-raw-data/*/current_weather_lv_grid.parquet'
            WHERE date > '{last_transform_date}' AND date < '{datetime.now().date()}'
            """
        )

@dagster.asset(
    deps=[weather_data_lv_grid],
    group_name="processed_data",
    metadata={"description": "Transform weather data for the LV grid"},
    io_manager_key="polars_io_manager_transformed",
    key_prefix=f"{datetime.now().year}_{datetime.now().month}_{datetime.now().day}",
)
def processed_weather_data(duckdb: DuckDBResource) -> pl.DataFrame:
    weather_variables = [
        "temperature",
        "wind_speed",
        "wind_direction",
        "relative_humidity",
        "dew_point",
        # "apparent_temperature",
        "precipitation",
        "precipitation_probability",
        # "rain",
        # "showers",
        # "snowfall",
        # "snow_depth",
        "weather_code",
        "cloud_cover",
        "cloud_cover_low",
        "cloud_cover_mid",
        "cloud_cover_high",
    ]

    diff_statements = [
        f"weather_forecast.{variable} - weather_current.{variable} AS {variable}_diff"
        for variable in weather_variables
    ]

    with duckdb.get_connection() as conn:
        processed_weather_data = pl.from_dataframe(
            conn.sql(
                f"""
                SELECT
                    weather_forecast.date,
                    weather_forecast.model,
                    weather_forecast.latitude,
                    weather_forecast.longitude,
                    weather_forecast.iso_3166_2,
                    DATEDIFF('hour', weather_forecast.date, weather_forecast.created_at) AS forecast_lead_hours,
                    {", ".join(diff_statements)}
                FROM weather_forecast
                JOIN weather_current ON
                    weather_forecast.date = weather_current.date
                    AND weather_forecast.latitude = weather_current.latitude
                    AND weather_forecast.longitude = weather_current.longitude
                    AND weather_forecast.model = weather_current.model
                """
                ).df()
            ).unpivot(
                index = ["date", "model", "forecast_lead_hours", "latitude", "longitude", "iso_3166_2"],
                value_name = "value",
                variable_name = "metric"
            )
        return processed_weather_data
