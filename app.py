"""
Проект голосового ассистента на Python 3 для Windows 10

Помощник умеет:
* распознавать и синтезировать речь в offline-моде (без доступа к Интернету);
* сообщать о прогнозе погоды в любой точке мира;
* производить поисковый запрос в поисковой системе Google
  (а также открывать список результатов и сами результаты данного запроса);
* производить поисковый запрос видео в системе YouTube и открывать список результатов данного запроса;
* выполнять поиск определения в Wikipedia c дальнейшим прочтением первых двух предложений;
* переводить с изучаемого языка на родной язык пользователя (с учетом особенностей воспроизведения речи);
* воспроизводить случайное приветствие;
* воспроизводить случайное прощание с последующим завершением работы программы;
* менять настройки языка распознавания и синтеза речи;
* TODO........

Голосовой ассистент использует для синтеза речи встроенные в операционную систему Windows 10 возможности
(т.е. голоса зависят от операционной системы). Для этого используется библиотека pyttsx3

Для корректной работы системы распознавания речи в сочетании с библиотекой SpeechRecognition
используется библиотека PyAudio для получения звука с микрофона.

Для установки PyAudio можно найти и скачать нужный в зависимости от архитектуры и версии Python whl-файл здесь:
https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio

Загрузив файл в папку с проектом, установку можно будет запустить с помощью подобной команды:
pip install PyAudio-0.2.11-cp38-cp38m-win_amd64.whl

Для использования SpeechRecognition в offline-режиме (без доступа к Интернету), потребуется дополнительно установить
vosk, whl-файл для которого можно найти здесь в зависимости от требуемой архитектуры и версии Python:
https://github.com/alphacep/vosk-api/releases/

Загрузив файл в папку с проектом, установку можно будет запустить с помощью подобной команды:
pip install vosk-0.3.7-cp38-cp38-win_amd64.whl

Для получения данных прогноза погоды мною был использован сервис OpenWeatherMap, который требует API-ключ.
Получить API-ключ и ознакомиться с документацией можно после регистрации (есть Free-тариф) здесь:
https://openweathermap.org/

Команды для установки прочих сторонних библиотек:
pip install google
pip install SpeechRecognition
pip install pyttsx3
pip install wikipedia-api
pip install googletrans
pip install python-dotenv
pip install pyowm

Дополнительную информацию по установке и использованию библиотек можно найти здесь:
https://pypi.org/
"""

from vosk import Model, KaldiRecognizer  # оффлайн-распознавание от Vosk
from googlesearch import search  # поиск в Google
from pyowm import OWM  # использование OpenWeatherMap для получения данных о погоде
from termcolor import colored  # вывод цветных логов (для выделения распознанной речи)
from dotenv import load_dotenv  # загрузка информации из .env-файла
import speech_recognition  # распознавание пользовательской речи (Speech-To-Text)
import googletrans  # использование системы Google Translate
import pyttsx3  # синтез речи (Text-To-Speech)
import wikipediaapi  # поиск определений в Wikipedia
import random  # генератор случайных чисел
import webbrowser  # работа с использованием браузера по умолчанию (открывание вкладок с web-страницей)
import traceback  # для отлова исключений и вывода traceback без остановки работы программы
import os  # для работы с файловой системой в операционной системе
import wave  # для работы с аудиофайлами
import json  # для работы с json-файлами и строками


# информация о владельце, включающие имя, город проживания, родной язык речи, изучаемый язык (для переводов текста)
class OwnerPerson:
    name = ""
    home_city = ""
    native_language = ""
    target_language = ""

    def set_name(self, name):
        self.name = name

    def set_home_city(self, home_city):
        self.home_city = home_city


# настройки голосового ассистента, включающие имя, пол, язык речи
class VoiceAssistant:
    name = ""
    sex = ""
    speech_language = ""
    recognition_language = ""

    def set_name(self, name):
        self.name = name

    def set_sex(self, sex):
        self.sex = sex

    def set_speech_language(self, speech_language):
        self.speech_language = speech_language


# установка голоса по умолчанию (индекс может меняться в зависимости от настроек операционной системы)
def setup_assistant_voice():
    voices = ttsEngine.getProperty("voices")

    if assistant.speech_language == "en":
        assistant.recognition_language = "en-US"
        if assistant.sex == "female":
            # Microsoft Zira Desktop - English (United States)
            ttsEngine.setProperty("voice", voices[1].id)
        else:
            # Microsoft David Desktop - English (United States)
            ttsEngine.setProperty("voice", voices[2].id)
    else:
        assistant.recognition_language = "ru-RU"
        # Microsoft Irina Desktop - Russian
        ttsEngine.setProperty("voice", voices[0].id)


# запись и распознавание аудио
def record_and_recognize_audio(*args):
    with microphone:
        recognized_data = ""

        # запоминание шумов окружения для последующей отчистки звука от них
        recognizer.adjust_for_ambient_noise(microphone, duration=2)

        try:
            print("Listening...")
            audio = recognizer.listen(microphone, 5, 5)

            with open("microphone-results.wav", "wb") as file:
                file.write(audio.get_wav_data())
                file.close()

        except speech_recognition.WaitTimeoutError:
            play_voice_assistant_speech("Can you check if your microphone is on, please?")
            traceback.print_exc()
            return

        # использование online-распознавания через Google (высокое качество распознавания)
        try:
            print("Started recognition...")
            recognized_data = recognizer.recognize_google(audio, language=assistant.recognition_language).lower()

        except speech_recognition.UnknownValueError:
            pass  # play_voice_assistant_speech("What did you say again?")

        # в случае проблем с доступом в Интернет пороисходит попытка использовать offline-распознавание через Vosk
        except speech_recognition.RequestError:
            print(colored("Trying to use offline recognition...", "cyan"))

            try:
                # проверка наличия модели на нужном языке в каталоге приложения
                if not os.path.exists("models/vosk-model-small-" + assistant.speech_language + "-0.4"):
                    print(colored("Please download the model from:\n"
                                  "https://alphacephei.com/vosk/models and unpack as 'model' in the current folder.",
                                  "red"))
                    exit(1)

                # анализ записанного в микрофон аудио (чтобы избежать повторов фразы)
                wave_audio_file = wave.open("microphone-results.wav", "rb")
                model = Model("models/vosk-model-small-" + assistant.speech_language + "-0.4")
                offline_recognizer = KaldiRecognizer(model, wave_audio_file.getframerate())

                data = wave_audio_file.readframes(wave_audio_file.getnframes())
                if len(data) > 0:
                    if offline_recognizer.AcceptWaveform(data):
                        recognized_data = offline_recognizer.Result()

                        # получение данных распознанного текста из JSON-строки (чтобы можно было выдать по ней ответ)
                        recognized_data = json.loads(recognized_data)
                        recognized_data = recognized_data["text"]
            except:
                traceback.print_exc()
                print(colored("Sorry, speech service is unavailable. Try again later", "red"))

        return recognized_data


# проигрывание речи ответов голосового ассистента (без сохранения аудио)
def play_voice_assistant_speech(text_to_speech):
    ttsEngine.say(str(text_to_speech))
    ttsEngine.runAndWait()


# проигрывание приветственной речи
def play_greetings(*args: tuple):
    greetings = [
        "hello, " + person.name + "! How can I help you today?",
        "Good day to you " + person.name + "! How can I help you today?"
    ]
    play_voice_assistant_speech(greetings[random.randint(0, len(greetings) - 1)])


# проигрывание прощательной речи и выход
def play_farewell_and_quit(*args: tuple):
    farewells = [
        "Goodbye, " + person.name + "! Have a nice day!",
        "See you soon, " + person.name + "!"
    ]
    play_voice_assistant_speech(farewells[random.randint(0, len(farewells) - 1)])
    ttsEngine.stop()
    quit()


# поиск в Google с автоматическим открытием ссылок (на список результатов и на сами результаты, если возможно)
def search_for_term_on_google(*args: tuple):
    if not args[0]: return
    search_term = " ".join(args[0])

    # открытие ссылки на поисковик в браузере
    url = "https://google.com/search?q=" + search_term
    webbrowser.get().open(url)

    # альтернативный поиск с автоматическим открытием ссылок на результаты (в некоторых случаях может быть небезопасно)
    search_results = []
    try:
        for _ in search(search_term,  # что искать
                        tld="com",  # верхнеуровневый домен
                        lang=assistant.speech_language,  # используется язык, на котором говорит ассистент
                        num=1,  # количество результатов на странице
                        start=0,  # индекс первого извлекаемого результата
                        stop=1,  # индекс последнего извлекаемого результата (я хочу, чтобы открывался первый результат)
                        pause=1.0,  # задержка между HTTP-запросами
                        ):
            search_results.append(_)
            webbrowser.get().open(_)

    # поскольку все ошибки предсказать сложно, то будет произведен отлов с последующим выводом без остановки программы
    except:
        play_voice_assistant_speech("Seems like we have a trouble. See logs for more information")
        traceback.print_exc()
        return

    print(search_results)
    play_voice_assistant_speech("Here is what I found for" + search_term + "on google")


# поиск видео на YouTube с автоматическим открытием ссылки на список результатов
def search_for_video_on_youtube(*args: tuple):
    if not args[0]: return
    search_term = " ".join(args[0])
    url = "https://www.youtube.com/results?search_query=" + search_term
    webbrowser.get().open(url)
    play_voice_assistant_speech("Here is what I found for " + search_term + "on youtube")


# поиск в Wikipedia определения с озвучиванием результатов и открытием ссылок
def search_for_definition_on_wikipedia(*args: tuple):
    if not args[0]: return

    search_term = " ".join(args[0])

    # установка языка (в данном случае используется язык, на котором говорит ассистент)
    wiki = wikipediaapi.Wikipedia(assistant.speech_language)

    # поиск страницы по запросу, чтение summary, открытие ссылки на страницу для получения подробной информации
    wiki_page = wiki.page(search_term)
    try:
        if wiki_page.exists():
            play_voice_assistant_speech("Here is what I found for" + search_term + "on Wikipedia")
            webbrowser.get().open(wiki_page.fullurl)

            # чтение ассистентом первых двух предложений summary со страницы Wikipedia
            play_voice_assistant_speech(wiki_page.summary.split(".")[:2])
        else:
            # открытие ссылки на поисковик в браузере в случае, если на Wikipedia не удалось найти ничего по запросу
            play_voice_assistant_speech("Can't find" + search_term + "on Wikipedia. But here is what I found on google")
            url = "https://google.com/search?q=" + search_term
            webbrowser.get().open(url)

    # поскольку все ошибки предсказать сложно, то будет произведен отлов с последующим выводом без остановки программы
    except:
        play_voice_assistant_speech("Seems like we have a trouble. See logs for more information")
        traceback.print_exc()
        return


# получение перевода текста с одного языка на другой (в данном случае с изучаемого на родной язык или обратно)
def get_translation(*args: tuple):
    if not args[0]: return

    search_term = " ".join(args[0])
    translator = googletrans.Translator()
    translation_result = ""

    old_assistant_language = assistant.speech_language
    try:
        # если язык речи ассистента и родной язык пользователя различаются, то перевод выполяется на родной язык
        if assistant.speech_language != person.native_language:
            translation_result = translator.translate(search_term,  # что перевести
                                                      src=person.target_language,  # с какого языка
                                                      dest=person.native_language)  # на какой язык

            play_voice_assistant_speech("The translation for" + search_term + "in Russian is")

            # смена голоса ассистента на родной язык пользователя (чтобы можно было произнести перевод)
            assistant.speech_language = person.native_language
            setup_assistant_voice()

        # если язык речи ассистента и родной язык пользователя одинаковы, то перевод выполяется на изучаемый язык
        else:
            translation_result = translator.translate(search_term,  # что перевести
                                                      src=person.native_language,  # с какого языка
                                                      dest=person.target_language)  # на какой язык
            play_voice_assistant_speech("По-английски" + search_term + "будет как")

            # смена голоса ассистента на изучаемый язык пользователя (чтобы можно было произнести перевод)
            assistant.speech_language = person.target_language
            setup_assistant_voice()

        # произнесение перевода
        play_voice_assistant_speech(translation_result.text)

    # поскольку все ошибки предсказать сложно, то будет произведен отлов с последующим выводом без остановки программы
    except:
        play_voice_assistant_speech("Seems like we have a trouble. See logs for more information")
        traceback.print_exc()

    finally:
        # возвращение преждних настроек голоса помощника
        assistant.speech_language = old_assistant_language
        setup_assistant_voice()


# получение и озвучивание прогнза погоды
def get_weather_forecast(*args: tuple):
    # в случае наличия дополнительного аргумента - запрос погоды происходит по нему,
    # иначе - используется город, заданный в настройках
    if args[0]:
        city_name = args[0][0]
    else:
        city_name = person.home_city

    try:
        # использование API-ключа, помещённого в .env-файл по примеру WEATHER_API_KEY = "01234abcd....."
        weather_api_key = os.getenv("WEATHER_API_KEY")
        open_weather_map = OWM(weather_api_key)

        # запрос данных о текущем состоянии погоды
        weather_manager = open_weather_map.weather_manager()
        observation = weather_manager.weather_at_place(city_name)
        weather = observation.weather

    # поскольку все ошибки предсказать сложно, то будет произведен отлов с последующим выводом без остановки программы
    except:
        play_voice_assistant_speech("Seems like we have a trouble. See logs for more information")
        traceback.print_exc()
        return

    # разбивание данных на части для удобства работы с ними
    status = weather.detailed_status
    temperature = weather.temperature('celsius')["temp"]
    wind_speed = weather.wind()["speed"]
    pressure = int(weather.pressure["press"] / 1.333)  # переведено из гПА в мм рт.ст.

    # вывод логов
    print(colored("Weather in " + city_name +
                  ":\n * Status: " + status +
                  "\n * Wind speed (m/sec): " + str(wind_speed) +
                  "\n * Temperature (Celsius): " + str(temperature) +
                  "\n * Pressure (mm Hg): " + str(pressure), "yellow"))

    # озвучивание текущего состояния погоды ассистентом
    play_voice_assistant_speech("It is" + status + "in" + city_name)
    play_voice_assistant_speech("The temperature is" + str(temperature) + "degrees Celsius")
    play_voice_assistant_speech("The wind speed is" + str(wind_speed) + "meters per second")
    play_voice_assistant_speech("The pressure is" + str(pressure) + " mm Hg")


# изменение языка голосового ассистента (языка распознавания речи)
def change_language(*args: tuple):
    assistant.speech_language = "ru" if assistant.speech_language == "en" else "en"
    setup_assistant_voice()
    print(colored("Language switched to " + assistant.speech_language, "cyan"))


# выполнение команды с заданными пользователем кодом команды и аргументами
def execute_command_with_code(command_code: str, *args: list):
    for key in commands.keys():
        if command_code in key:
            commands[key](*args)
        else:
            pass  # print("Command code not found")


# перечень команд для использования (качестве ключей словаря используется hashable-тип tuple)
commands = {
    ("hello", "hi", "morning", "привет"): play_greetings,
    ("bye", "goodbye", "quit", "exit", "stop", "пока"): play_farewell_and_quit,
    ("search", "google", "find", "найди"): search_for_term_on_google,
    ("video", "youtube", "watch", "видео"): search_for_video_on_youtube,
    ("wikipedia", "definition", "about", "определение", "википедия"): search_for_definition_on_wikipedia,
    ("translate", "interpretation", "translation", "перевод", "перевести", "переведи"): get_translation,
    ("language", "язык"): change_language,
    ("weather", "forecast", "погода", "прогноз"): get_weather_forecast,
}

if __name__ == "__main__":

    # инициализация инструментов распознавания и ввода речи
    recognizer = speech_recognition.Recognizer()
    microphone = speech_recognition.Microphone()
    ttsEngine = pyttsx3.init()

    # настройка данных пользователя
    person = OwnerPerson()
    person.name = "Tanya"
    person.home_city = "Yekaterinburg"
    person.native_language = "ru"
    person.target_language = "en"

    # настройка данных голосового помощника
    assistant = VoiceAssistant()
    assistant.name = "Alice"
    assistant.sex = "female"
    assistant.speech_language = "en"

    # установка голоса по умолчанию
    setup_assistant_voice()

    # загрузка информации из .env-файла
    load_dotenv()

    while True:
        # старт записи речи с последующим выводом распознанной речи и удалением записанного в микрофон аудио
        voice_input = record_and_recognize_audio()
        os.remove("microphone-results.wav")
        print(colored(voice_input, "blue"))

        # отделение комманд от дополнительной информации (аргументов)
        voice_input = voice_input.split(" ")
        command = voice_input[0]
        command_options = [str(input_part) for input_part in voice_input[1:len(voice_input)]]
        execute_command_with_code(command, command_options)

# TODO get current time/date in place
# TODO toss a coin (get random value to choose something)
# TODO take screenshot
# TODO find person
# TODO food order
# TODO talk when button is pressed?
# TODO create json-like config?
# TODO use nltk (nature language tool kit)
