"""
Обработчик команд Nova.

Получает структурированную команду от Butler, определяет нужный
инструмент через Registry и передаёт ему только необходимые параметры.
"""

import inspect

from tools.registry import get_tool


class CommandHandler:
    """Выполняет команды, сформированные Butler."""

    def execute(self, data: dict) -> dict:
        """
        Выполняет команду и записывает результат в исходные данные.

        Args:
            data: JSON-объект от Butler.

        Returns:
            Тот же JSON с заполненным result.
        """

        command = data["command"]
        parameters = data["parameters"]

        if command == "conversation":
            return data

        if command == "music":
            query = parameters["query"]

            # Временная реализация до подключения музыкального инструмента.
            data["result"] = (
                f'Запрос на воспроизведение музыки: "{query}"'
            )

            print(
                "Внимание: команда music пока не реализована. "
                "Здесь позже появится вызов tools.music."
            )

            return data

        tool = get_tool(command)

        tool_parameters = inspect.signature(
            tool.function
        ).parameters

        filtered_parameters = {
            name: value
            for name, value in parameters.items()
            if name in tool_parameters
        }

        data["result"] = tool.function(**filtered_parameters)
        print(f"DEBUG TOOL RESULT: {data['result']}")

        return data


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

