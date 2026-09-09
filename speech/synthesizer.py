import re

import torch
import sounddevice as sd

from logger import get_logger


log = get_logger("TTS")


# ============================================================
# ЧИСЛА
# ============================================================

ONES_MALE = (
    "ноль",
    "один",
    "два",
    "три",
    "четыре",
    "пять",
    "шесть",
    "семь",
    "восемь",
    "девять",
)

ONES_FEMALE = (
    "ноль",
    "одна",
    "две",
    "три",
    "четыре",
    "пять",
    "шесть",
    "семь",
    "восемь",
    "девять",
)

TEENS = (
    "десять",
    "одиннадцать",
    "двенадцать",
    "тринадцать",
    "четырнадцать",
    "пятнадцать",
    "шестнадцать",
    "семнадцать",
    "восемнадцать",
    "девятнадцать",
)

TENS = (
    "",
    "",
    "двадцать",
    "тридцать",
    "сорок",
    "пятьдесят",
    "шестьдесят",
    "семьдесят",
    "восемьдесят",
    "девяносто",
)

HUNDREDS = (
    "",
    "сто",
    "двести",
    "триста",
    "четыреста",
    "пятьсот",
    "шестьсот",
    "семьсот",
    "восемьсот",
    "девятьсот",
)


def _three_digits_to_words(
    number: int,
    female: bool = False,
) -> str:

    if number == 0:
        return ""

    words = []

    hundreds = number // 100
    remainder = number % 100

    if hundreds:
        words.append(HUNDREDS[hundreds])

    if 10 <= remainder <= 19:

        words.append(TEENS[remainder - 10])

    else:

        tens = remainder // 10
        ones = remainder % 10

        if tens:
            words.append(TENS[tens])

        if ones:

            if female:
                words.append(ONES_FEMALE[ones])
            else:
                words.append(ONES_MALE[ones])

    return " ".join(words)


def number_to_words(
    number: int,
    female: bool = False,
) -> str:

    if number == 0:
        return "ноль"

    if number < 0:
        return "минус " + number_to_words(
            abs(number),
            female=female,
        )

    parts = []

    # Миллиарды
    billions = number // 1_000_000_000

    if billions:

        parts.append(
            _three_digits_to_words(
                billions,
                female=True,
            )
        )

        remainder = billions % 100

        if remainder in (1,):
            parts.append("миллиард")

        elif 2 <= remainder <= 4:
            parts.append("миллиарда")

        else:
            parts.append("миллиардов")

        number %= 1_000_000_000

    # Миллионы
    millions = number // 1_000_000

    if millions:

        parts.append(
            _three_digits_to_words(
                millions,
                female=True,
            )
        )

        remainder = millions % 100

        if remainder == 1:
            parts.append("миллион")

        elif 2 <= remainder <= 4:
            parts.append("миллиона")

        else:
            parts.append("миллионов")

        number %= 1_000_000

    # Тысячи
    thousands = number // 1_000

    if thousands:

        parts.append(
            _three_digits_to_words(
                thousands,
                female=True,
            )
        )

        remainder = thousands % 100

        if remainder == 1:
            parts.append("тысяча")

        elif 2 <= remainder <= 4:
            parts.append("тысячи")

        else:
            parts.append("тысяч")

        number %= 1_000

    if number:
        parts.append(
            _three_digits_to_words(
                number,
                female=female,
            )
        )

    return " ".join(parts)


# ============================================================
# ДЕСЯТИЧНЫЕ ЧИСЛА
# ============================================================

def decimal_to_words(value: str) -> str:

    value = value.replace(",", ".")

    negative = value.startswith("-")

    if negative:
        value = value[1:]

    integer_part, decimal_part = value.split(".")

    integer_words = number_to_words(
        int(integer_part)
    )

    decimal_digits = decimal_part.rstrip("0")

    if not decimal_digits:
        return integer_words

    decimal_number = int(decimal_digits)

    decimal_words = number_to_words(
        decimal_number
    )

    digits_count = len(decimal_digits)

    if digits_count == 1:
        ending = "десятая"

    elif digits_count == 2:
        ending = "сотых"

    elif digits_count == 3:
        ending = "тысячных"

    else:
        ending = "десятичных"

    result = (
        f"{integer_words} целых "
        f"{decimal_words} {ending}"
    )

    if negative:
        result = "минус " + result

    return result


# ============================================================
# TTS НОРМАЛИЗАТОР
# ============================================================

class SpeechTextNormalizer:

    @staticmethod
    def normalize(text: str) -> str:

        if not text:
            return text

        result = text

        # ----------------------------------------------------
        # Температура
        #
        # 24.3°C
        # 24°C
        # -5°C
        # ----------------------------------------------------

        temperature_pattern = re.compile(
            r"(-?\d+(?:[.,]\d+)?)\s*°\s*C",
            re.IGNORECASE,
        )

        def temperature_replace(match):

            value = match.group(1)

            if "." in value or "," in value:

                number = decimal_to_words(value)

            else:

                number = number_to_words(
                    int(value)
                )

            return (
                f"{number} "
                f"градуса Цельсия"
            )

        result = temperature_pattern.sub(
            temperature_replace,
            result,
        )

        # ----------------------------------------------------
        # Проценты
        #
        # 72%
        # 15.5%
        # ----------------------------------------------------

        percent_pattern = re.compile(
            r"(-?\d+(?:[.,]\d+)?)\s*%",
        )

        def percent_replace(match):

            value = match.group(1)

            if "." in value or "," in value:

                number = decimal_to_words(value)

            else:

                number = number_to_words(
                    int(value)
                )

            return f"{number} процентов"

        result = percent_pattern.sub(
            percent_replace,
            result,
        )

        # ----------------------------------------------------
        # Скорость м/с
        #
        # 3.4 м/с
        # 10 м/с
        # ----------------------------------------------------

        speed_pattern = re.compile(
            r"(-?\d+(?:[.,]\d+)?)\s*м/с",
            re.IGNORECASE,
        )

        def speed_replace(match):

            value = match.group(1)

            if "." in value or "," in value:

                number = decimal_to_words(value)

            else:

                number = number_to_words(
                    int(value)
                )

            return f"{number} метров в секунду"

        result = speed_pattern.sub(
            speed_replace,
            result,
        )

        # ----------------------------------------------------
        # Температура в виде "24 C"
        # ----------------------------------------------------

        temperature_c_pattern = re.compile(
            r"(-?\d+(?:[.,]\d+)?)\s*°?\s*C\b",
            re.IGNORECASE,
        )

        def temperature_c_replace(match):

            value = match.group(1)

            if "." in value or "," in value:

                number = decimal_to_words(value)

            else:

                number = number_to_words(
                    int(value)
                )

            return f"{number} градусов Цельсия"

        result = temperature_c_pattern.sub(
            temperature_c_replace,
            result,
        )

        # ----------------------------------------------------
        # Время
        #
        # 18:30 -> восемнадцать часов тридцать минут
        # ----------------------------------------------------

        time_pattern = re.compile(
            r"\b(\d{1,2}):(\d{2})\b",
        )

        def time_replace(match):

            hours = int(match.group(1))
            minutes = int(match.group(2))

            hours_words = number_to_words(
                hours
            )

            minutes_words = number_to_words(
                minutes
            )

            return (
                f"{hours_words} часов "
                f"{minutes_words} минут"
            )

        result = time_pattern.sub(
            time_replace,
            result,
        )

        # ----------------------------------------------------
        # Обычные десятичные числа
        #
        # 24.3
        # 3.14
        # ----------------------------------------------------

        decimal_pattern = re.compile(
            r"(?<![\w])"
            r"-?\d+[.,]\d+"
            r"(?![\w])",
        )

        result = decimal_pattern.sub(
            lambda match: decimal_to_words(
                match.group(0)
            ),
            result,
        )

        # ----------------------------------------------------
        # Обычные целые числа
        #
        # 24
        # 72
        # 2026
        # ----------------------------------------------------

        integer_pattern = re.compile(
            r"(?<![\w])"
            r"-?\d+"
            r"(?![\w])",
        )

        result = integer_pattern.sub(
            lambda match: number_to_words(
                int(match.group(0))
            ),
            result,
        )

        # ----------------------------------------------------
        # Единицы измерения
        # ----------------------------------------------------

        result = re.sub(
            r"\bкм/ч\b",
            "километров в час",
            result,
            flags=re.IGNORECASE,
        )

        result = re.sub(
            r"\bкм\b",
            "километров",
            result,
            flags=re.IGNORECASE,
        )

        result = re.sub(
            r"\bкг\b",
            "килограммов",
            result,
            flags=re.IGNORECASE,
        )

        result = re.sub(
            r"\bг\b",
            "граммов",
            result,
            flags=re.IGNORECASE,
        )

        result = re.sub(
            r"\bл\b",
            "литров",
            result,
            flags=re.IGNORECASE,
        )

        result = re.sub(
            r"\bмл\b",
            "миллилитров",
            result,
            flags=re.IGNORECASE,
        )

        result = re.sub(
            r"\bм²\b",
            "квадратных метров",
            result,
        )

        result = re.sub(
            r"\bм³\b",
            "кубических метров",
            result,
        )

        # ----------------------------------------------------
        # Валюта
        # ----------------------------------------------------

        result = re.sub(
            r"₽",
            " рублей",
            result,
        )

        result = re.sub(
            r"\$",
            " долларов",
            result,
        )

        result = re.sub(
            r"€",
            " евро",
            result,
        )

        # ----------------------------------------------------
        # Убираем двойные пробелы
        # ----------------------------------------------------

        result = re.sub(
            r"\s+",
            " ",
            result,
        ).strip()

        return result


# ============================================================
# SYNTHESIZER
# ============================================================

class SpeechSynthesizer:

    def __init__(self):

        log.info(
            "Загрузка модели Silero TTS"
        )

        self.device = torch.device(
            "cpu"
        )

        self.model, _ = torch.hub.load(
            repo_or_dir="snakers4/silero-models",
            model="silero_tts",
            language="ru",
            speaker="v5_5_ru",
        )

        self.model.to(
            self.device
        )

        self.speaker = "xenia"

        self.sample_rate = 48000

        log.info(
            "Silero TTS загружен. "
            "Голос: {}, частота: {} Гц",
            self.speaker,
            self.sample_rate,
        )

    def speak(
        self,
        text: str,
    ):

        if not text:
            return

        log.info(
            "Озвучивание ответа"
        )

        # ====================================================
        # НОРМАЛИЗАЦИЯ ТЕКСТА
        # ====================================================

        speech_text = (
            SpeechTextNormalizer.normalize(
                text
            )
        )

        log.debug(
            "Оригинальный текст TTS: {}",
            text,
        )

        log.debug(
            "Нормализованный текст TTS: {}",
            speech_text,
        )

        # ====================================================
        # SYNTHESIS
        # ====================================================

        audio = self.model.apply_tts(
            text=speech_text,
            speaker=self.speaker,
            sample_rate=self.sample_rate,
        )

        sd.play(
            audio.numpy(),
            self.sample_rate,
        )

        sd.wait()

        log.info(
            "Озвучивание завершено"
        )