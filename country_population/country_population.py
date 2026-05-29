import requests
from plugins.base_plugin.base_plugin import BasePlugin


def format_population(value):
    try:
        return f"{int(value):,}"
    except (TypeError, ValueError):
        return "N/A"


def format_change(value):
    try:
        val = float(value)
        sign = "+" if val > 0 else ""
        return f"{sign}{val:.2f}%"
    except (TypeError, ValueError):
        return None


class CountryPopulation(BasePlugin):
    def generate_image(self, settings, device_config):
        country = (settings.get("country") or "united states").strip()
        title = (settings.get("title") or "").strip() or "Country Population"

        if not country:
            raise RuntimeError("Please specify a country in the plugin settings.")

        api_key = device_config.load_env_key("API_NINJAS_KEY")
        if not api_key:
            raise RuntimeError("API Ninjas API key not configured.")

        api_url = "https://api.api-ninjas.com/v1/population"
        headers = {"X-Api-Key": api_key}
        params = {"country": country}

        try:
            response = requests.get(api_url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            content = e.response.text if e.response is not None else "No response content"
            status_code = e.response.status_code if e.response is not None else "unknown"
            raise RuntimeError(f"HTTP error {status_code}: {content}") from e
        except requests.exceptions.Timeout as e:
            raise RuntimeError("Request timed out trying to fetch population data.") from e
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Network or connection error: {str(e)}") from e

        try:
            data = response.json()
        except ValueError as e:
            raise RuntimeError("Failed to parse response as JSON.") from e

        if not isinstance(data, dict) or "historical_population" not in data:
            raise RuntimeError(f"Unexpected population data format or no data found for country: {country}")

        historical_pop = data.get("historical_population") or []
        if not historical_pop:
            raise RuntimeError(f"No historical population data available for country: {country}")

        latest = historical_pop[0]
        previous = historical_pop[1] if len(historical_pop) > 1 else None

        population = latest.get("population")
        year = latest.get("year")
        country_name = (data.get("country_name") or country).title()

        population_str = format_population(population)
        previous_population = previous.get("population") if previous else None
        previous_year = previous.get("year") if previous else None

        delta_value = None
        delta_percent = None
        if population and previous_population:
            try:
                delta_value = int(population) - int(previous_population)
                delta_percent = (delta_value / int(previous_population)) * 100
            except (TypeError, ValueError, ZeroDivisionError):
                delta_value = None
                delta_percent = None

        delta_str = f"{delta_value:+,}" if delta_value is not None else None
        delta_percent_str = format_change(delta_percent) if delta_percent is not None else None

        width, height = device_config.get_resolution()
        if device_config.get_config("orientation") == "vertical":
            width, height = height, width

        return self.render_image(
            dimensions=(width, height),
            html_file="country_population.html",
            css_file="country_population.css",
            template_params={
                "title": title,
                "country": country_name,
                "population": population_str,
                "year": year or "N/A",
                "previous_year": previous_year,
                "delta_value": delta_str,
                "delta_percent": delta_percent_str,
                "plugin_settings": settings
            }
        )

    def generate_settings_template(self):
        template_params = super().generate_settings_template()
        template_params["style_settings"] = True
        template_params["country"] = {
            "required": True,
            "description": "Country name",
            "example": "United States",
        }
        template_params["title"] = {
            "required": False,
            "description": "Custom header text",
            "example": "Country Population",
        }
        return template_params