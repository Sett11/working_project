import gradio as gr
import aiohttp
import asyncio
from datetime import datetime
from typing import Tuple, Optional, List, Dict, Any
from fastapi import File
from logs import log_event as log_event_hf, clear_logs
from delete_files import delete_files

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
                params = {key: out.get(key) for key in ["result", "participants", "start_data", "end_data", "len_tokens"]}
    return temp_file, params

def initial_processing(file_content: bytes):
    return asyncio.run(async_initial_processing(file_content))

async def async_detailed_processing(
    file_path: str,  # Изменено с File на str
    anonymize: bool,
    keep_dates: bool,
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
    # Открываем файл и добавляем его в FormData
    with open(file_path, "rb") as f:
        data.add_field(
            "file", 
            f.read(),
            filename=file_path
        )
    
    data.add_field("anonymize_names", str(anonymize))
    data.add_field("keep_dates", str(keep_dates))
    data.add_field("start_data", start_data)
    data.add_field("result_token", str(result_token))  # Преобразуем int в str
    data.add_field("excluded_participants", ",".join(excluded_participants))
    
    async with aiohttp.ClientSession() as session:
        async with session.post(
            "http://localhost:8000/detail_processing_file/",
            data=data
        ) as response:
            out = await response.json()
            if response.status == 200 and (r := out.get("result")): 
                result_file = "final_processed_chat.txt"
                with open(result_file, "w", encoding="utf8") as f:
                    f.write(r)
                names = out.get("code_name", {})
    log_event("Детальная обработка завершена")
    return result_file, names

def detailed_processing(
    file_path: str,  # Изменено с File на str
    anonymize: bool, 
    keep_dates: bool,
    start_data: str, 
    result_token: int, 
    excluded_participants: List[str]
):
    return asyncio.run(async_detailed_processing(
        file_path, 
        anonymize, 
        keep_dates,
        start_data, 
        result_token, 
        excluded_participants
    ))

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
    participants_list_state = gr.State()
    # Глобальные переменные для чекбоксов
    checkboxes = []
    # Экран 1: Загрузка файла
    with gr.Column(visible=True) as upload_screen:
        gr.Markdown("## Загрузите файл для обработки")
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
            label="Диапазон дат",
            step=60
        )
        date_display = gr.Markdown("Дата: -")
        # Участники
        participants_container = gr.Column()
        participants_title = gr.Markdown("### Выберите участников для исключения:", visible=False)
        # Создаем чекбоксы заранее
        max_participants = 20  # Максимальное количество участников
        participant_checkboxes = []
        for i in range(max_participants):
            cb = gr.Checkbox(label="", visible=False)
            participant_checkboxes.append(cb)
            participants_container.add(cb)
        # Кнопки
        with gr.Row():
            skip_button = gr.Button("Пропустить детальную обработку", variant="secondary")
            process_button = gr.Button("Применить обработку", variant="primary")
        # Результат
        result_message = gr.Markdown(visible=False)
        download_output = gr.File(visible=False, label="Скачать обработанный файл")
        participants_output = gr.Markdown(visible=False,value="Участники:")
    # Обработчики событий

    # Загрузка файла и первичная обработка
    @upload_button.click(
        inputs=file_input,
        outputs=[upload_screen, loading_screen, detail_screen, temp_file_state, tokens_slider, date_slider, participants_container, participants_output, participants_list_state, participants_title] + participant_checkboxes
    )
    def start_processing(file_content: bytes):
        temp_file, params = initial_processing(file_content)
        if not temp_file or not params:
            return [
                gr.update(visible=True),
                gr.update(visible=False),
                gr.update(visible=False),
                None,
                gr.update(),
                gr.update(),
                gr.update(),
                gr.update(visible=True),
                None,
                gr.update(visible=False)
            ] + [gr.update(visible=False) for _ in range(max_participants)]
        
        # Сохраняем список участников в состояние
        participants = [name for name in params["participants"] if name.strip()]
        
        # Обновляем чекбоксы
        checkbox_updates = []
        for i, name in enumerate(participants):
            if i < max_participants:
                checkbox_updates.append(gr.update(label=f"Исключить {name}", visible=True, value=False))
        
        # Заполняем оставшиеся чекбоксы как невидимые
        for _ in range(max_participants - len(participants)):
            checkbox_updates.append(gr.update(visible=False))
        
        # Обновляем даты
        min_date_ts = parse_date(params["start_data"])
        max_date_ts = parse_date(params["end_data"])
        
        log_event(f"участники: {participants}")
        return [
            gr.update(visible=False),  # upload_screen
            gr.update(visible=False),  # loading_screen
            gr.update(visible=True),   # detail_screen
            temp_file,                # temp_file_state
            gr.update(maximum=params["len_tokens"], value=[0, params["len_tokens"]]),  # tokens_slider
            gr.update(minimum=min_date_ts, maximum=max_date_ts, value=[min_date_ts, max_date_ts]),  # date_slider
            gr.update(visible=True),  # participants_container
            gr.update(visible=True),  # participants_output
            participants,  # participants_list_state
            gr.update(visible=True)  # participants_title
        ] + checkbox_updates
    
    # Обновление отображения даты
    @date_slider.change(
        inputs=date_slider,
        outputs=date_display
    )
    def update_date_display(date_range):
        log_event(f"Дата: {date_range}")
        return f"Дата: {format_timestamp(date_range[0])} — {format_timestamp(date_range[1])}"
    
    # Детальная обработка
    @process_button.click(
    inputs=[
        temp_file_state,    # Путь к временному файлу
        anonymize,         # Флаг анонимизации (Checkbox)
        keep_dates,        # Флаг сохранения дат (Checkbox)
        date_slider,       # Слайдер с диапазоном дат
        tokens_slider,     # Слайдер с диапазоном токенов
        participants_list_state,  # Список всех участников (gr.State)
        *participant_checkboxes   # Все чекбоксы для исключения участников
    ],
    outputs=[result_message, download_output, participants_output]
)

    def process_detailed(
        file_path: str,
        anonymize: bool,
        keep_dates: bool,
        date_range: List[float],
        len_tokens: int,
        *excluded_participants: bool
    ):
        # 1. Преобразуем timestamp в строки дат
        start_date = format_timestamp(date_range[0]) + ":00"
        end_date = format_timestamp(date_range[1]) + ":00"
        
        # 2. Получаем список исключённых участников
        excluded_names = [
            name 
            for name, is_excluded in zip(participants_list_state, excluded_participants) 
            if is_excluded
        ]
        
        log_event(f"Исключаемые участники: {excluded_names}")
        
        # 3. Получаем максимальное количество токенов (берём верхнюю границу слайдера)
        max_tokens = len_tokens[1]
        
        # 4. Вызываем детальную обработку
        result_file, code_names = detailed_processing(
            file_path=file_path,
            anonymize=anonymize,
            keep_dates=keep_dates,
            start_data=start_date,
            result_token=max_tokens,
            excluded_participants=excluded_names
        )
        
        # 5. Формируем результат
        result_msg = "Файл успешно обработан!"
        download_file = gr.update(value=result_file, visible=True)
        
        # 6. Если была анонимизация, показываем соответствие имён
        if anonymize and code_names:
            participants_text = "Анонимизированные имена:\n" + "\n".join(
                f"{code} = {name}" for code, name in code_names.items()
            )
            participants_output = gr.update(value=participants_text, visible=True)
        else:
            participants_output = gr.update(visible=False)
        
        return (
            gr.update(value=result_msg, visible=True),
            download_file,
            participants_output
        )
    
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
    
delete_files("result.txt", "final_processed_chat.txt")
clear_logs()
log_event("Запуск приложения...")

if __name__ == "__main__":
    app.launch(server_name="0.0.0.0", server_port=7862)