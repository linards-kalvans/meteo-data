import openmeteo_requests
from openmeteo_sdk import Model, WeatherApiResponse, Variable
import time
import requests_cache
from retry_requests import retry

import polars as pl
from datetime import datetime, timedelta, timezone

import logging

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)

class Forecast:
    models = [
        "icon_seamless",
        "gfs_seamless",
        "meteofrance_seamless",
        "ecmwf_ifs025",
        "ecmwf_aifs025",
        "ukmo_seamless",
        "jma_seamless",
        "metno_seamless",
        "gem_seamless",
        "bom_access_global",
        "cma_grapes_global",
        "knmi_seamless",
        "dmi_seamless"
    ]

    variables = [
        "temperature_2m",
        "wind_speed_10m",
        "wind_direction_10m",
        "relative_humidity_2m",
        "dew_point_2m",
        "apparent_temperature",
        "precipitation",
        "precipitation_probability",
        "rain",
        "showers",
        "snowfall",
        "snow_depth",
        "weather_code",
        "cloud_cover",
        "cloud_cover_low",
        "cloud_cover_mid",
        "cloud_cover_high",
    ]

    cache_session = requests_cache.CachedSession('.cache', expire_after = 3600)
    retry_session = retry(cache_session, retries = 5, backoff_factor = 0.2)
    openmeteo = openmeteo_requests.Client(session = retry_session)

    url = "https://api.open-meteo.com/v1/forecast"

    def __init__(self, sleep_time: int = 5):
        self.sleep_time = sleep_time

    @staticmethod
    def model_to_name(code: int) -> str:
        """convert Model to name"""
        for name, value in Model.Model.__dict__.items():
            if value == code and not name.startswith("_"):
                return name
        return None
    
    @staticmethod
    def variable_to_name(code: int) -> str:
        """convert Variable to name"""
        for name, value in Variable.Variable.__dict__.items():
            if value == code and not name.startswith("_"):
                return name
        return None

    @staticmethod
    def hourly_data_to_polars(response: WeatherApiResponse) -> pl.DataFrame:
        hourly = response.Hourly()
        start = datetime.fromtimestamp(hourly.Time(), timezone.utc)
        end = datetime.fromtimestamp(hourly.TimeEnd(), timezone.utc)
        freq = timedelta(seconds = hourly.Interval())

        hourly_dataframe_pl = pl.select(
            created_at = pl.lit(datetime.now(timezone.utc)),
            date = pl.datetime_range(start, end, freq, closed = "left"),
            model = pl.lit(Forecast.model_to_name(response.Model())),
            latitude = pl.lit(response.Latitude()),
            longitude = pl.lit(response.Longitude()),
            elevation = pl.lit(response.Elevation())
        )
        for i in range(hourly.VariablesLength()):
            variable = hourly.Variables(i)
            hourly_dataframe_pl = hourly_dataframe_pl.with_columns(
                pl.Series(variable.ValuesAsNumpy()).alias(Forecast.variable_to_name(variable.Variable()))
            )
        return hourly_dataframe_pl
    
    @staticmethod
    def current_data_to_polars(response: WeatherApiResponse) -> pl.DataFrame:
        current = response.Current()
        current_dataframe_pl = pl.select(
            created_at = pl.lit(datetime.now(timezone.utc)),
            date = pl.lit(datetime.fromtimestamp(current.Time(), timezone.utc)),
            model = pl.lit(Forecast.model_to_name(response.Model())),
            latitude = pl.lit(response.Latitude()),
            longitude = pl.lit(response.Longitude()),
            elevation = pl.lit(response.Elevation())
        )
        for i in range(current.VariablesLength()):
            variable = current.Variables(i)
            current_dataframe_pl = current_dataframe_pl.with_columns(
                pl.lit(variable.Value()).alias(Forecast.variable_to_name(variable.Variable()))
            )
        return current_dataframe_pl


    def get_data(self, latitude, longitude) -> tuple[pl.DataFrame, pl.DataFrame]:
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "hourly": self.variables,
            "current": self.variables,
            "wind_speed_unit": "ms",
            "models": self.models
        }
        logger.info(f"Getting data for {latitude}, {longitude}")
        responses = self.openmeteo.weather_api(self.url, params=params)
        time.sleep(self.sleep_time)
        hourly_data = pl.concat([Forecast.hourly_data_to_polars(response) for response in responses])
        current_data = pl.concat([Forecast.current_data_to_polars(response) for response in responses])
        return hourly_data, current_data
