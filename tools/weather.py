import requests

from config import OPENWEATHER_API_KEY
from tools.registry import register_tool

@register_tool(
    name="weather",
    description="Получить текущую погоду в указанном городе.",
)
def get_weather(city: str) -> str:
    """
    Получает текущую погоду в указанном городе.

    Args:
        city: Название города.

    Returns:
        Информация о текущей погоде.
    """

    openweather_url = (
        "https://api.openweathermap.org/data/2.5/weather"
    )

    params = {
        "q": city,
        "appid": OPENWEATHER_API_KEY,
        "units": "metric",
        "lang": "ru",
    }

    response = requests.get(
        openweather_url,
        params=params,
        timeout=10,
    )

    data = response.json()

    if response.status_code == 200:

        weather_description = data["weather"][0]["description"]
        temperature = data["main"]["temp"]
        humidity = data["main"]["humidity"]
        wind_speed = data["wind"]["speed"]

        weather_info = (
            f"Погода в {city}:\n"
            f"Описание: {weather_description}\n"
            f"Температура: {temperature:.1f}°C\n"
            f"Влажность: {humidity}%\n"
            f"Скорость ветра: {wind_speed} м/с"
        )

        return weather_info

    return (
        f"Не удалось получить данные о погоде "
        f"для {city}. "
        f"Ошибка: {data.get('message', 'Неизвестная ошибка')}"
    )

if __name__ == "__main__":
    print(get_weather("Batumi"))