import time
from collections import deque

import numpy as np
import sounddevice as sd
import whisper

from logger import get_logger


log = get_logger("SPEECH")


class SpeechRecognizer:

    MICROPHONE_ID = 2

    SAMPLE_RATE = 16000
    CHANNELS = 1

    BLOCK_DURATION = 0.1
    BLOCK_SIZE = int(SAMPLE_RATE * BLOCK_DURATION)

    CALIBRATION_TIME = 2.0

    # --------------------------------------------------------
    # Настройки определения речи
    # --------------------------------------------------------

    SILENCE_DURATION = 1.2

    # Сколько секунд устойчивого звука нужно,
    # чтобы считать его началом речи.
    SPEECH_START_DURATION = 0.3

    # Сколько секунд звука сохраняем перед моментом,
    # когда была обнаружена речь.
    PRE_ROLL_DURATION = 0.3

    MAX_RECORDING_TIME = 20.0
    MIN_RECORDING_TIME = 0.3

    NOISE_MULTIPLIER = 2.5

    def __init__(self):

        log.info("Загрузка модели Whisper...")

        self.model = whisper.load_model("small")

        log.info("Whisper успешно загружен")

        device_info = sd.query_devices(
            self.MICROPHONE_ID,
            "input",
        )

        log.info(
            "Используется микрофон: {}",
            device_info["name"],
        )

        self.silence_threshold = (
            self.calibrate_microphone()
        )

        log.info(
            "SpeechRecognizer полностью инициализирован"
        )

    # ========================================================
    # КАЛИБРОВКА МИКРОФОНА
    # ========================================================

    def calibrate_microphone(self):

        log.info(
            "Начало калибровки микрофона"
        )

        log.debug(
            "Время калибровки: {} секунд",
            self.CALIBRATION_TIME,
        )

        measurements = []

        start_time = time.time()

        with sd.InputStream(
            samplerate=self.SAMPLE_RATE,
            channels=self.CHANNELS,
            dtype="int16",
            device=self.MICROPHONE_ID,
            blocksize=self.BLOCK_SIZE,
        ) as stream:

            while (
                time.time() - start_time
                < self.CALIBRATION_TIME
            ):

                data, overflowed = (
                    stream.read(self.BLOCK_SIZE)
                )

                if overflowed:
                    log.warning(
                        "Переполнение буфера во время калибровки"
                    )

                audio = data[:, 0]

                volume = np.abs(audio).mean()

                measurements.append(volume)

        noise_level = np.mean(measurements)

        threshold = max(
            noise_level * self.NOISE_MULTIPLIER,
            150,
        )

        log.info(
            "Средний уровень фонового шума: {:.1f}",
            noise_level,
        )

        log.info(
            "Порог обнаружения речи: {:.1f}",
            threshold,
        )

        return threshold

    # ========================================================
    # ЗАПИСЬ ФРАЗЫ
    # ========================================================

    def record_phrase(self):

        log.debug(
            "Ожидание начала речи"
        )

        print("\n🎤 Слушаю...")

        frames = []

        speech_started = False

        silence_start = None
        speech_start = None

        # ----------------------------------------------------
        # Буфер последних блоков.
        #
        # Нужен для pre-roll:
        # если человек начал говорить чуть раньше,
        # чем мы уверенно определили голос,
        # эти первые миллисекунды не потеряются.
        # ----------------------------------------------------

        pre_roll_blocks = max(
            1,
            int(
                self.PRE_ROLL_DURATION
                / self.BLOCK_DURATION
            ),
        )

        pre_roll = deque(
            maxlen=pre_roll_blocks
        )

        # ----------------------------------------------------
        # Сколько подряд блоков должны быть громче порога,
        # чтобы считать это настоящей речью.
        # ----------------------------------------------------

        required_speech_blocks = max(
            1,
            int(
                self.SPEECH_START_DURATION
                / self.BLOCK_DURATION
            ),
        )

        speech_candidate_blocks = 0

        with sd.InputStream(
            samplerate=self.SAMPLE_RATE,
            channels=self.CHANNELS,
            dtype="int16",
            device=self.MICROPHONE_ID,
            blocksize=self.BLOCK_SIZE,
        ) as stream:

            while True:

                data, overflowed = (
                    stream.read(self.BLOCK_SIZE)
                )

                if overflowed:
                    log.warning(
                        "Переполнение буфера во время записи"
                    )

                audio = data[:, 0].copy()

                volume = np.abs(audio).mean()

                # =================================================
                # ОЖИДАНИЕ НАЧАЛА РЕЧИ
                # =================================================

                if not speech_started:

                    # Сохраняем последние блоки.
                    pre_roll.append(audio)

                    if volume > self.silence_threshold:

                        speech_candidate_blocks += 1

                    else:

                        # Если хотя бы один блок оказался тише
                        # порога — начинаем отсчёт заново.
                        speech_candidate_blocks = 0

                    # ------------------------------------------------
                    # Речь подтверждена
                    # ------------------------------------------------

                    if (
                        speech_candidate_blocks
                        >= required_speech_blocks
                    ):

                        speech_started = True

                        speech_start = time.time()

                        log.info(
                            "Речь обнаружена, запись начата"
                        )

                        print("🔴 Запись...")

                        # Сначала добавляем pre-roll.
                        frames.extend(
                            list(pre_roll)
                        )

                        # Затем текущий блок.
                        frames.append(audio)

                    continue

                # =================================================
                # ЗАПИСЬ РЕЧИ
                # =================================================

                frames.append(audio)

                elapsed = (
                    time.time()
                    - speech_start
                )

                # =================================================
                # ОПРЕДЕЛЯЕМ ТИШИНУ
                # =================================================

                if volume > self.silence_threshold:

                    silence_start = None

                else:

                    if silence_start is None:

                        silence_start = time.time()

                    elif (
                        time.time()
                        - silence_start
                        >= self.SILENCE_DURATION
                    ):

                        log.debug(
                            "Обнаружена тишина после речи"
                        )

                        break

                # =================================================
                # МАКСИМАЛЬНАЯ ДЛИНА
                # =================================================

                if (
                    elapsed
                    >= self.MAX_RECORDING_TIME
                ):

                    log.warning(
                        "Достигнута максимальная длина записи: "
                        "{} секунд",
                        self.MAX_RECORDING_TIME,
                    )

                    break

        # ========================================================
        # ПРОВЕРКА ЗАПИСИ
        # ========================================================

        if not frames:

            log.debug(
                "Речь не обнаружена"
            )

            return None

        audio = np.concatenate(frames)

        recording_duration = (
            len(audio)
            / self.SAMPLE_RATE
        )

        log.info(
            "Запись завершена. Длительность: {:.2f} секунд",
            recording_duration,
        )

        if (
            recording_duration
            < self.MIN_RECORDING_TIME
        ):

            log.debug(
                "Запись слишком короткая: {:.2f} секунд",
                recording_duration,
            )

            return None

        return audio

    # ========================================================
    # РАСПОЗНАВАНИЕ WHISPER
    # ========================================================

    def recognize(self, audio):

        log.info(
            "Начало распознавания речи Whisper"
        )

        print("🧠 Распознаю...")

        audio = (
            audio.astype(np.float32)
            / 32768.0
        )

        try:

            result = self.model.transcribe(
                audio,
                language="ru",
                task="transcribe",
                fp16=False,
                temperature=0,
                condition_on_previous_text=False,
            )

        except Exception:

            log.exception(
                "Ошибка при распознавании речи Whisper"
            )

            raise

        text = result["text"].strip()

        if text:

            log.info(
                "Whisper распознал: {}",
                text,
            )

        else:

            log.warning(
                "Whisper не распознал текст"
            )

        return text


# ============================================================
# ТЕСТОВЫЙ ЗАПУСК
# ============================================================

if __name__ == "__main__":

    recognizer = SpeechRecognizer()

    print("\n" + "=" * 60)
    print("ГОТОВО")
    print("=" * 60)

    print("\nГовори в микрофон.")
    print("Для выхода нажми Ctrl+C.")

    try:

        while True:

            audio = recognizer.record_phrase()

            if audio is None:
                continue

            text = recognizer.recognize(audio)

            if text:

                print(f"\n📝 Ты: {text}")

    except KeyboardInterrupt:

        print("\n\nПрограмма завершена.")

        log.info(
            "Тестовый запуск SpeechRecognizer завершён"
        )

    except Exception:

        log.exception(
            "Критическая ошибка SpeechRecognizer"
        )

        print(
            "\n❌ Произошла ошибка. "
            "Подробности находятся в logs/assistant.log"
        )