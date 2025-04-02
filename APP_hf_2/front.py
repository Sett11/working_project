import gradio as gr
import aiohttp
import asyncio
from datetime import datetime
from typing import Tuple, Optional, List, Dict, Any
from logs import log_event as log_event_hf

def log_event(message):
    log_event_hf(f"FROM FRONT: {message}")

async def async_initial_processing(file_content: bytes) -> Tuple[str, Dict[str, Any]]:
    """
    Первичная обработка файла.
    Принимает содержимое файла как bytes.
    Возвращает путь к обработанному файлу и параметры для детальной обработки.
    """
    log_event("Начата первичная обработка файла...")
    URL = "http://localhost:8000/upload_file/"
    data = aiohttp.FormData()
    temp_file, params = None, None
    data.add_field("file", file_content)
    async with aiohttp.ClientSession() as session:
        async with session.post(URL, data=data) as response:
            out = await response.json()
            if response.status == 200 and (r := out.get("result")):
                temp_file = "result.txt"
                with open(temp_file, "w", encoding="utf8") as result_file:
                    result_file.write(r)
                params = {key: out.get(key) for key in ["code_name", "start_data", "end_data", "len_tokens"]}
    return temp_file, params

async def async_detailed_processing(
    file_path: str,
    anonymize: bool,
    start_data: str,
    result_token: int,
    excluded_participants: List[str]
) -> Tuple[str, Optional[List[str]]]:
    """
    Детальная обработка файла.
    Возвращает путь к итоговому файлу и (если нужна анонимизация) список участников.
    """
    log_event(f"Детальная обработка файла {file_path}...")
    result_file, names = None, None
    data = aiohttp.FormData()
    data.add_field("file", file_path)
    data.add_field("anonymize_names", str(anonymize))
    data.add_field("start_data", start_data)
    data.add_field("result_token", result_token)
    data.add_field("excluded_participants", ",".join(excluded_participants))
    async with aiohttp.ClientSession() as session:
        async with session.post(
            "http://localhost:8000/detail_processing_file/",
            data=data
        ) as response:
            out = await response.json()
            if response.status == 200 and (r := out.get("result")): 
                result_file = "final_processed_chat.txt"
                with open(result_file, "w", encoding="utf8") as result_file:
                    result_file.write(r)
                names = out.get("code_name", {})
    return result_file, names

def initial_processing(file_content: bytes):
    return asyncio.run(async_initial_processing(file_content))

def detailed_processing(file_path: str, anonymize: bool, start_data: str, result_token: int, excluded_participants: List[str]):
    return asyncio.run(async_detailed_processing(file_path, anonymize, start_data, result_token, excluded_participants))

def parse_date(date_str: str) -> float:
    """Преобразует строку даты в timestamp для слайдера"""
    return datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S").timestamp()

def format_timestamp(ts: float) -> str:
    """Форматирует timestamp в читаемую дату"""
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")


with gr.Blocks(title="Обработка чатов") as app:
    # Состояния
    temp_file_state = gr.State()
    participants_state = gr.State()
    # Экран 1: Загрузка файла
    with gr.Column(visible=True) as upload_screen:
        gr.Markdown("## Загрузите файл")
        file_input = gr.File(label="Файл", file_types=[".txt", ".json", ".html"], type="binary")
        upload_button = gr.Button("Начать обработку", variant="primary")
    # Экран 2: Индикатор загрузки
    with gr.Column(visible=False) as loading_screen:
        gr.Markdown("## Идёт обработка файла...")
        # Добавляем анимацию загрузки
        gr.Markdown("<div class='loader'></div>", elem_id="loader")
    # Экран 3: Детальная обработка
    with gr.Column(visible=False) as detail_screen:
        gr.Markdown("## Настройте параметры обработки")
        with gr.Row():
            anonymize = gr.Checkbox(label="Анонимизировать имена", value=False)
            keep_dates = gr.Checkbox(label="Сохранить даты/время", value=True)
        # Слайдеры
        tokens_slider = gr.Slider(
            minimum=0,
            maximum=1000,
            value=[0, 1000],
            label="Диапазон токенов",
            step=1
        )
        date_slider = gr.Slider(
            minimum=0,
            maximum=1,
            value=[0, 1],
            label="Диапазон дат",step=3600  # Шаг в 1 час
        )
        date_display = gr.Markdown("Дата: -")
    
        # Участники
        participants_container = gr.Column()
        participant_checkboxes = []
    
        # Кнопки
        with gr.Row():
            skip_button = gr.Button("Пропустить детальную обработку", variant="secondary")
            process_button = gr.Button("Применить обработку", variant="primary")
    
        # Результат
        result_message = gr.Markdown(visible=False)
        download_output = gr.File(visible=False, label="Скачать обработанный файл")
        participants_output = gr.Markdown(visible=False)
    # Обработчики событий

    # Загрузка файла и первичная обработка
    @upload_button.click(
        inputs=file_input,
        outputs=[upload_screen, loading_screen, temp_file_state]
    )
    def start_processing(file_content: bytes):
        log_event("Начинаем первичную обработку файла...")
        temp_file, params = initial_processing(file_content)
        log_event(f"Полученные параметры: {params}")
        # Проверяем наличие необходимых данных
        if params["start_data"] is None or params["end_data"] is None:
            log_event("Ошибка: start_data или end_data отсутствуют в ответе сервера.")
            return (
                gr.update(visible=False),  # Скрываем экран загрузки
                gr.update(visible=False),   # Скрываем экран детальной обработки
                gr.update(value=""),        # temp_file_state
                gr.update(value=[0, 0]),    # tokens_slider
                gr.update(value=[0, 1]),    # date_slider
                participants_container        # participants_container
            )

        min_date_ts = parse_date(params["start_data"])
        max_date_ts = parse_date(params["end_data"])
        log_event(f"Минимальная дата: {min_date_ts}, Максимальная дата: {max_date_ts}")
        # Создаем чекбоксы для участников
        with participants_container:
            participant_checkboxes.clear()
            for participant in params["code_name"]:
                cb = gr.Checkbox(label=f"Исключить {participant}", value=False)
                participant_checkboxes.append(cb)
        log_event("Обработка завершена, возвращаем значения.9")
        return (
            gr.update(visible=False),  # Скрываем экран загрузки
            gr.update(visible=True),   # Показываем экран детальной обработки
            temp_file,                 # Возвращаем путь к временному файлу
            gr.update(maximum=params["len_tokens"], value=[0, params["len_tokens"]]),  # Обновляем слайдер токенов
            gr.update(minimum=min_date_ts, maximum=max_date_ts, value=[min_date_ts, max_date_ts]),  # Обновляем слайдер дат
            participants_container       # Возвращаем контейнер участников
        )
    
    # Обновление отображения даты
    @date_slider.change(
        inputs=date_slider,
        outputs=date_display
    )
    def update_date_display(date_range):
        return f"Дата: {format_timestamp(date_range[0])} — {format_timestamp(date_range[1])}"
    
    # Детальная обработка
    @process_button.click(
        inputs=[
            temp_file_state,
            anonymize,
            date_slider,
            tokens_slider,
            *participant_checkboxes
        ],
        outputs=[result_message, download_output, participants_output]
    )
    def process_detailed(
        file_path: str,
        anonymize: bool,
        date_range: List[float],
        tokens_range: List[int],
        *excluded_participants: bool
    ):
        # Преобразуем timestamp обратно в строки
        log_event(f"date_range: {date_range}")
        start_date = format_timestamp(date_range[0]) + ":00"
        end_date = format_timestamp(date_range[1]) + ":00"
        # Получаем список исключенных участников
        excluded = [p.label.replace("Исключить ", "") for p, excl in zip(participant_checkboxes, excluded_participants) if excl]
        # Вызываем детальную обработку
        result_file, participants = detailed_processing(
            file_path,
            anonymize,
            start_date,
            tokens_range[1],
            excluded
        )
        # Формируем результат
        outputs = [
            gr.update(visible=True, value="Файл успешно обработан!"),
            gr.update(value=result_file, visible=True)]
        if participants:
            parts_text = "Анонимизированные участники:\n" + "\n".join(f"- {p}" for p in participants)
            outputs.append(gr.update(value=parts_text, visible=True))
        else:
            outputs.append(gr.update(visible=False))
        return outputs
    
    # Пропуск детальной обработки
    @skip_button.click(
        inputs=temp_file_state,
        outputs=[result_message, download_output, participants_output]
    )
    def skip_processing(file_path: str):
        return (
            gr.update(visible=True, value="Файл готов после первичной обработки"),
            gr.update(value=file_path, visible=True),
            gr.update(visible=False)
        )

log_event("Запуск приложения...")
if __name__ == "__main__":
    app.launch(server_name="0.0.0.0", server_port=7862)