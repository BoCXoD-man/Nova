from tools.weather import get_weather


class CommandHandler:

    def execute(self, data: dict) -> dict:
        """
        Выполняет команду, которую сформировал Butler.

        Args:
            data: JSON-объект от Butler.

        Returns:
            Тот же JSON, но с заполненным result.
        """

        command = data["command"]
        parameters = data["parameters"]

        # ====================================================
        # CONVERSATION
        # ====================================================

        if command == "conversation":

            # Обычный разговор не требует выполнения
            # какого-либо инструмента.

            return data

        # ====================================================
        # WEATHER
        # ====================================================

        if command == "weather":

            city = parameters["city"]

            result = get_weather(city)

            data["result"] = result

            return data

        # ====================================================
        # MUSIC
        # ====================================================

        if command == "music":

            query = parameters["query"]

            # Пока музыка не подключена.
            # Здесь позже появится вызов tools.music.

            data["result"] = (
                f'Запрос на воспроизведение музыки: "{query}"'
            )
            print(
                "Внимание: команда music пока не реализована. "
                "Здесь позже появится вызов tools.music."
            )   
            return data

        # ====================================================
        # НЕИЗВЕСТНАЯ КОМАНДА
        # ====================================================

        raise ValueError(
            f"Handler получил неизвестную команду: {command}"
        )


# ============================================================
# ТЕСТ
# ============================================================

if __name__ == "__main__":

    handler = CommandHandler()

    test_weather = {
        "command": "weather",
        "parameters": {
            "city": "Батуми"
        },
        "result": None,
        "prompt": (
            "По данным результата расскажи "
            "пользователю о текущей погоде."
        ),
    }

    result = handler.execute(test_weather)

    print(result)