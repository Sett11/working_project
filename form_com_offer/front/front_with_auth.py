"""
Модуль фронтенда Gradio с интегрированной аутентификацией.

Этот модуль объединяет основной интерфейс приложения с системой аутентификации.
"""
import gradio as gr
import httpx
from utils.mylogger import Logger
import json
import os
from collections import defaultdict
import re
import datetime

# Импортируем функции и данные из основного front.py
from front.front import (
    load_components_catalog, COMPONENTS_CATALOG, get_placeholder_order,
    build_error_response, safe_float, safe_int, safe_bool, safe_illumination,
    get_component_image_path, fix_date, generate_kp, select_aircons,
    fetch_orders_list, fetch_all_orders_list, fetch_order_data, delete_order,
    fill_fields_from_order, fill_fields_from_order_diff, update_components_tab,
    fill_components_fields_from_order, read_notes_md
)
from front.auth_interface import create_auth_interface, get_auth_manager, get_auth_status

# URL для backend API
BACKEND_URL = "http://backend:8001"

logger = Logger(name=__name__, log_file="frontend.log")

# Глобальные переменные для компонентов UI (как в front.py)
components_ui_inputs = []
components_catalog_for_ui = []

# Создаем основной интерфейс с аутентификацией
with gr.Blocks(title="Автоматизация продаж кондиционеров", theme=gr.themes.Ocean()) as interface:
    
    # Состояния приложения
    order_state = gr.State(get_placeholder_order())
    order_id_state = gr.State(None)
    orders_table_data = gr.State([])
    
    # Интерфейс аутентификации
    with gr.Group(visible=True) as auth_screen:
        auth_interface = create_auth_interface()
        
        # Кнопка для перехода к основному приложению
        with gr.Row():
            auth_status = gr.Textbox(
                label="Статус аутентификации",
                value="Не авторизован",
                interactive=False
            )
            check_auth_btn = gr.Button("Проверить статус", variant="secondary")
            proceed_btn = gr.Button("Перейти к приложению", variant="primary", visible=False)
    
    # Основной интерфейс приложения (скрыт до аутентификации)
    with gr.Group(visible=False) as main_app_screen:
        # Стартовый экран
        with gr.Group(visible=True) as start_screen:
            gr.Markdown("<h1 style='color:#00008B;'>Everis</h1>")
            gr.Markdown("<h2 style='color:#FAEBD7;'>Cистема формирования коммерческих предложений</h2>")
            create_btn = gr.Button("Создать новый заказ", variant="primary")
            load_btn = gr.Button("Загрузить заказ", variant="secondary")
            
            # Кнопка выхода
            logout_btn = gr.Button("Выйти из системы", variant="stop")
        
        # Экран списка заказов
        with gr.Group(visible=False) as orders_list_screen:
            gr.Markdown("### Выберите заказ для загрузки")
            orders_radio = gr.Radio(choices=[], label="Список заказов")
            load_selected_btn = gr.Button("Загрузить выбранный заказ", variant="primary")
            load_error = gr.Markdown(visible=False)
            back_to_start_btn = gr.Button("Назад")
        
        # Основной экран заказа
        with gr.Group(visible=False) as main_order_screen:
            # Вкладка "Данные для КП"
            with gr.Tab("Данные для КП"):
                with gr.Row():
                    with gr.Column():
                        gr.Markdown("### 1. Данные клиента")
                        name = gr.Textbox(label="Имя клиента", value=get_placeholder_order()["client_data"]["full_name"])
                        phone = gr.Textbox(label="Телефон", value=get_placeholder_order()["client_data"]["phone"])
                        mail = gr.Textbox(label="Электронная почта", value=get_placeholder_order()["client_data"]["email"])
                        address = gr.Textbox(label="Адрес", value=get_placeholder_order()["client_data"]["address"])
                        date = gr.Textbox(label="Дата визита монтажника", value=get_placeholder_order()["order_params"]["visit_date"])
                    with gr.Column():
                        gr.Markdown("### 2. Параметры заказа")
                        type_room = gr.Dropdown(["квартира", "дом", "офис", "производство"], label="Тип помещения", value=get_placeholder_order()["order_params"]["room_type"])
                        area = gr.Slider(10, 160, label="Площадь помещения (м²)", value=get_placeholder_order()["order_params"]["room_area"])
                        discount = gr.Slider(0, 50, step=1, label="Индивидуальная скидка (%)", value=get_placeholder_order()["order_params"]["discount"])
                        installation_price = gr.Number(label="Стоимость монтажа (BYN)", minimum=0, step=1, value=get_placeholder_order()["order_params"]["installation_price"])
                
                gr.Markdown("### 3. Требования к кондиционеру")
                with gr.Row():
                    brand = gr.Dropdown(["Любой", "Midea", "Dantex", "Vetero", "Electrolux", "Toshiba", "Hisense", "Mitsubishi", "Samsung", "TCL"], label="Бренд", value=get_placeholder_order()["aircon_params"]["brand"])
                    price = gr.Slider(0, 22000, value=get_placeholder_order()["aircon_params"]["price_limit"], label="Верхний порог стоимости (BYN)")
                    inverter = gr.Checkbox(label="Инверторный компрессор", value=get_placeholder_order()["aircon_params"]["inverter"])
                    wifi = gr.Checkbox(label="Wi-Fi управление", value=get_placeholder_order()["aircon_params"]["wifi"])
                with gr.Row():
                    mount_type = gr.Dropdown(["Любой", "настенный", "кассетного типа", "канальный", "напольный", "потолочный", "напольно-потолочный", "консольно-подпотолочный", "наружный блок"], label="Тип кондиционера", value=get_placeholder_order()["aircon_params"]["mount_type"])
                
                gr.Markdown("### 4. Дополнительные параметры для расчета мощности")
                with gr.Row():
                    ceiling_height = gr.Slider(2.0, 5.0, step=0.1, label="Высота потолков (м)", value=get_placeholder_order()["aircon_params"]["ceiling_height"])
                    illumination = gr.Dropdown(["Слабая", "Средняя", "Сильная"], label="Освещенность", value=get_placeholder_order()["aircon_params"]["illumination"])
                    num_people = gr.Slider(1, 10, step=1, label="Количество людей", value=get_placeholder_order()["aircon_params"]["num_people"])
                    activity = gr.Dropdown(["Сидячая работа", "Легкая работа", "Средняя работа", "Тяжелая работа", "Спорт"], label="Активность людей", value=get_placeholder_order()["aircon_params"]["activity"])
                with gr.Row():
                    num_computers = gr.Slider(0, 10, step=1, label="Количество компьютеров", value=get_placeholder_order()["aircon_params"]["num_computers"])
                    num_tvs = gr.Slider(0, 5, step=1, label="Количество телевизоров", value=get_placeholder_order()["aircon_params"]["num_tvs"])
                    other_power = gr.Slider(0, 2000, step=50, label="Мощность прочей техники (Вт)", value=get_placeholder_order()["aircon_params"]["other_power"])
                
                order_id_hidden = gr.Number(label="ID заказа (скрытое)", visible=False)
                save_kp_status = gr.Textbox(label="Статус сохранения данных для КП", interactive=False)
                save_kp_btn = gr.Button("Сохранить данные для КП", variant="primary")

            # Вкладка "Комплектующие"
            with gr.Tab("Комплектующие"):
                gr.Markdown("### Подбор комплектующих для монтажа")
                components_by_category = defaultdict(list)
                
                # Используем каталог компонентов
                unique_components = COMPONENTS_CATALOG.get("components", [])
                
                for idx, comp in enumerate(unique_components):
                    components_by_category[comp["category"]].append((comp, idx))
                
                for category, components_in_cat in components_by_category.items():
                    with gr.Group():
                        gr.Markdown(f"#### {category}")
                        for comp, idx in components_in_cat:
                            with gr.Row(equal_height=True):
                                with gr.Column(scale=1):
                                    image_path = get_component_image_path(comp.get('image_path'))
                                    gr.Image(value=image_path, label="Фото", height=80, width=80, interactive=False)
                                with gr.Column(scale=5):
                                    is_measurable = "труба" in comp["name"].lower() or "кабель" in comp["name"].lower() or "теплоизоляция" in comp["name"].lower() or "шланг" in comp["name"].lower() or "провод" in comp["name"].lower() or comp["category"] == "Кабель-каналы"
                                    label_text = f"{comp['name']}"
                                    checkbox = gr.Checkbox(label=label_text)
                                with gr.Column(scale=2):
                                    if is_measurable:
                                        qty_input = gr.Number(label="Кол-во (шт)", visible=False)
                                    else:
                                        qty_input = gr.Number(label="Кол-во (шт)", minimum=0, step=1)
                                with gr.Column(scale=2):
                                    if is_measurable:
                                        length_input = gr.Number(label="Длина (м)", minimum=0, step=1)
                                    else:
                                        length_input = gr.Number(visible=False)
                                
                                # Добавляем в глобальные списки
                                if checkbox is not None and qty_input is not None and length_input is not None:
                                    if hasattr(checkbox, '_id') and hasattr(qty_input, '_id') and hasattr(length_input, '_id'):
                                        components_ui_inputs.extend([checkbox, qty_input, length_input])
                                        components_catalog_for_ui.append(comp)
                
                save_components_status = gr.Textbox(label="Статус сохранения комплектующих", interactive=False)
                save_components_btn = gr.Button("Сохранить комплектующие", variant="primary")

            # Вкладка "Комментарии к заказу"
            with gr.Tab("Комментарии к заказу"):
                comment_box = gr.Textbox(label="Комментарий к заказу", value=get_placeholder_order()["comment"], lines=5, max_lines=20)
                save_comment_status = gr.Textbox(label="Статус сохранения комментария", interactive=False)
                save_comment_btn = gr.Button("Сохранить комментарий", variant="primary")

            # Вкладка "Результат"
            with gr.Tab("Результат"):
                gr.Markdown("### Подбор кондиционеров")
                aircons_output = gr.TextArea(label="Подходящие модели", interactive=False, lines=15, max_lines=None, show_copy_button=True)
                select_aircons_btn = gr.Button("Подобрать кондиционеры", variant="primary")
                gr.Markdown("### Генерация коммерческого предложения")
                pdf_output = gr.File(label="Скачать коммерческое предложение")
                generate_btn = gr.Button("Сформировать КП", variant="primary")
                gr.Markdown("### Управление заказом")
                delete_btn = gr.Button("Удалить заказ", variant="stop", size="sm")

            # Вкладка "Формирование специального заказа"
            with gr.Tab("Формирование составного заказа"):
                # Секция 1: Данные клиента
                gr.Markdown("## 📋 Данные клиента")
                with gr.Row():
                    with gr.Column():
                        compose_name = gr.Textbox(label="Имя клиента", value=get_placeholder_order()["client_data"]["full_name"])
                        compose_phone = gr.Textbox(label="Телефон", value=get_placeholder_order()["client_data"]["phone"])
                        compose_mail = gr.Textbox(label="Электронная почта", value=get_placeholder_order()["client_data"]["email"])
                    with gr.Column():
                        compose_address = gr.Textbox(label="Адрес", value=get_placeholder_order()["client_data"]["address"])
                        compose_date = gr.Textbox(label="Дата визита монтажника", value=get_placeholder_order()["order_params"]["visit_date"])
                        compose_discount = gr.Slider(0, 50, step=1, label="Индивидуальная скидка (%)", value=get_placeholder_order()["order_params"]["discount"])
                
                compose_save_client_status = gr.Textbox(label="Статус сохранения данных клиента", interactive=False)
                compose_save_client_btn = gr.Button("Сохранить данные клиента", variant="primary")
                
                gr.Markdown("---")
                
                # Секция 2: Данные для подбора кондиционера
                gr.Markdown("## ❄️ Данные для подбора кондиционера")
                
                gr.Markdown("### Параметры помещения")
                with gr.Row():
                    compose_type_room = gr.Textbox(label="Тип помещения", value=get_placeholder_order()["order_params"]["room_type"])
                    compose_area = gr.Slider(10, 160, label="Площадь помещения (м²)", value=get_placeholder_order()["order_params"]["room_area"])
                    compose_installation_price = gr.Number(label="Стоимость монтажа (BYN)", minimum=0, step=1, value=get_placeholder_order()["order_params"]["installation_price"])
                
                gr.Markdown("### Требования к кондиционеру")
                with gr.Row():
                    compose_brand = gr.Dropdown(["Любой", "Midea", "Dantex", "Vetero", "Electrolux", "Toshiba", "Hisense", "Mitsubishi", "Samsung", "TCL"], label="Бренд", value=get_placeholder_order()["aircon_params"]["brand"])
                    compose_price = gr.Slider(0, 22000, value=get_placeholder_order()["aircon_params"]["price_limit"], label="Верхний порог стоимости (BYN)")
                    compose_inverter = gr.Checkbox(label="Инверторный компрессор", value=get_placeholder_order()["aircon_params"]["inverter"])
                    compose_wifi = gr.Checkbox(label="Wi-Fi управление", value=get_placeholder_order()["aircon_params"]["wifi"])
                with gr.Row():
                    compose_mount_type = gr.Dropdown(["Любой", "настенный", "кассетного типа", "канальный", "напольный", "потолочный", "напольно-потолочный", "консольно-подпотолочный", "наружный блок"], label="Тип кондиционера", value=get_placeholder_order()["aircon_params"]["mount_type"])
                
                gr.Markdown("### Дополнительные параметры для расчета мощности")
                with gr.Row():
                    compose_ceiling_height = gr.Slider(2.0, 5.0, step=0.1, label="Высота потолков (м)", value=get_placeholder_order()["aircon_params"]["ceiling_height"])
                    compose_illumination = gr.Dropdown(["Слабая", "Средняя", "Сильная"], label="Освещенность", value=get_placeholder_order()["aircon_params"]["illumination"])
                    compose_num_people = gr.Slider(1, 10, step=1, label="Количество людей", value=get_placeholder_order()["aircon_params"]["num_people"])
                    compose_activity = gr.Dropdown(["Сидячая работа", "Легкая работа", "Средняя работа", "Тяжелая работа", "Спорт"], label="Активность людей", value=get_placeholder_order()["aircon_params"]["activity"])
                with gr.Row():
                    compose_num_computers = gr.Slider(0, 10, step=1, label="Количество компьютеров", value=get_placeholder_order()["aircon_params"]["num_computers"])
                    compose_num_tvs = gr.Slider(0, 5, step=1, label="Количество телевизоров", value=get_placeholder_order()["aircon_params"]["num_tvs"])
                    compose_other_power = gr.Slider(0, 2000, step=50, label="Мощность прочей техники (Вт)", value=get_placeholder_order()["aircon_params"]["other_power"])
                
                compose_order_id_hidden = gr.State(None)
                compose_aircon_counter = gr.Textbox(label="Количество добавленных кондиционеров", value="0", interactive=False)
                compose_save_status = gr.Textbox(label="Статус сохранения данных", interactive=False)
                compose_save_btn = gr.Button("Сохранить данные для кондиционера", variant="primary")
                
                compose_aircons_output = gr.TextArea(label="Подходящие модели", interactive=False, lines=10, max_lines=None, show_copy_button=True)
                compose_select_btn = gr.Button("Подобрать", variant="primary")
                compose_add_aircon_btn = gr.Button("Ввести данные для следующего кондиционера", variant="secondary")
                
                compose_generate_kp_btn = gr.Button("Сгенерировать КП", variant="primary")
                compose_kp_status = gr.Textbox(label="Статус генерации КП", interactive=False)
                compose_pdf_output = gr.File(label="Скачать коммерческое предложение")
                
                compose_delete_btn = gr.Button("Удалить составной заказ", variant="stop", size="sm")

            # Вкладка "Инструкция пользователя"
            with gr.Tab("Инструкция пользователя"):
                gr.Markdown(read_notes_md())
    
    # Обработчики событий аутентификации
    def check_authentication():
        """Проверка статуса аутентификации."""
        auth_manager = get_auth_manager()
        if auth_manager.is_authenticated():
            return (
                f"Авторизован как: {auth_manager.username}",
                gr.update(visible=True),  # proceed_btn
                gr.update(visible=False),  # auth_screen
                gr.update(visible=True)    # main_app_screen
            )
        else:
            return (
                "Не авторизован",
                gr.update(visible=False),  # proceed_btn
                gr.update(visible=True),   # auth_screen
                gr.update(visible=False)   # main_app_screen
            )
    
    def logout_and_return_to_auth():
        """Выход из системы и возврат к экрану аутентификации."""
        auth_manager = get_auth_manager()
        auth_manager.clear_auth_data()
        return (
            "Не авторизован",
            gr.update(visible=False),  # proceed_btn
            gr.update(visible=True),   # auth_screen
            gr.update(visible=False)   # main_app_screen
        )
    
    def navigate_to_main_app():
        """Переход к основному приложению."""
        return (
            gr.update(visible=False),  # auth_screen
            gr.update(visible=True)    # main_app_screen
        )
    
    def auto_navigate_after_auth():
        """Автоматический переход к приложению после успешной аутентификации."""
        auth_manager = get_auth_manager()
        if auth_manager.is_authenticated():
            return (
                f"Авторизован как: {auth_manager.username}",
                gr.update(visible=False),  # proceed_btn
                gr.update(visible=False),  # auth_screen
                gr.update(visible=True)    # main_app_screen
            )
        else:
            return (
                "Не авторизован",
                gr.update(visible=False),  # proceed_btn
                gr.update(visible=True),   # auth_screen
                gr.update(visible=False)   # main_app_screen
            )
    
    # Привязка обработчиков аутентификации
    check_auth_btn.click(
        fn=check_authentication,
        outputs=[auth_status, proceed_btn, auth_screen, main_app_screen]
    )
    
    proceed_btn.click(
        fn=navigate_to_main_app,
        outputs=[auth_screen, main_app_screen]
    )
    
    # Автоматическая проверка аутентификации при загрузке
    auth_interface.load(
        fn=check_authentication,
        outputs=[auth_status, proceed_btn, auth_screen, main_app_screen]
    )
    
    # Автоматический переход после успешной аутентификации
    auth_interface.load(
        fn=auto_navigate_after_auth,
        outputs=[auth_status, proceed_btn, auth_screen, main_app_screen]
    )
    
    logout_btn.click(
        fn=logout_and_return_to_auth,
        outputs=[auth_status, proceed_btn, auth_screen, main_app_screen]
    )
    
    # Обработчики для основного интерфейса (упрощенные версии)
    def show_start():
        """Показать стартовый экран и скрыть остальные."""
        return gr.update(visible=True), gr.update(visible=False), gr.update(visible=False)
    
    def show_main_order():
        """Показать основной экран заказа и скрыть остальные."""
        return gr.update(visible=False), gr.update(visible=False), gr.update(visible=True)
    
    async def show_orders():
        logger.info("=== show_orders вызвана ===")
        auth_manager = get_auth_manager()
        if not auth_manager.is_authenticated():
            logger.warning("show_orders: пользователь не аутентифицирован")
            return gr.update(visible=False), gr.update(visible=True), gr.update(visible=False), [], gr.update(choices=[], value=None), gr.update(visible=False, value="")
        
        try:
            logger.info("show_orders: отправляем запрос к /api/all_orders/")
            # Используем аутентифицированный запрос для получения заказов
            headers = auth_manager.get_auth_headers()
            logger.info(f"show_orders: заголовки аутентификации: {headers}")
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{BACKEND_URL}/api/all_orders/", headers=headers)
                logger.info(f"show_orders: статус ответа: {resp.status_code}")
                resp.raise_for_status()
                orders = resp.json()
                logger.info(f"show_orders: получено заказов: {len(orders)}")
                logger.info(f"show_orders: заказы: {orders}")
            
            def status_key(order):
                status_order = {
                    'partially filled': 0,
                    'completely filled': 1,
                    'completed': 2
                }
                return (status_order.get(order.get('status'), 99), -int(order['id']))
            
            orders_sorted = sorted(orders, key=status_key)
            choices = [
                f"{o['id']} | {o.get('order_type', 'Order')} | {o['client_name']} | {o.get('address', 'Адрес клиента')} | {o['created_at']} | {o['status']}"
                for o in orders_sorted
            ]
            logger.info(f"show_orders: создано вариантов выбора: {len(choices)}")
            logger.info(f"show_orders: варианты: {choices}")
            return gr.update(visible=False), gr.update(visible=True), gr.update(visible=False), orders, gr.update(choices=choices, value=None), gr.update(visible=False, value="")
        except Exception as e:
            logger.error(f"Ошибка при получении списка заказов: {e}", exc_info=True)
            return gr.update(visible=False), gr.update(visible=True), gr.update(visible=False), [], gr.update(choices=[], value=None), gr.update(visible=True, value=f"Ошибка: {e}")
    
    create_btn.click(
        fn=show_main_order,
        outputs=[start_screen, orders_list_screen, main_order_screen]
    )
    
    load_btn.click(
        fn=show_orders,
        outputs=[start_screen, orders_list_screen, main_order_screen, orders_table_data, orders_radio, load_error]
    )
    
    back_to_start_btn.click(
        fn=show_start,
        outputs=[start_screen, orders_list_screen, main_order_screen]
    )

    # --- Аутентифицированные версии функций из front.py ---
    
    async def load_selected_order_with_auth(selected):
        """Загрузка выбранного заказа с аутентификацией."""
        auth_manager = get_auth_manager()
        if not auth_manager.is_authenticated():
            return build_error_response("Требуется аутентификация", len(components_ui_inputs))
        
        if not selected:
            return build_error_response("Пожалуйста, выберите заказ для загрузки", len(components_ui_inputs))
        
        # Извлекаем ID и тип заказа из строки
        parts = selected.split("|")
        order_id = int(parts[0].strip())
        order_type = parts[1].strip() if len(parts) > 1 else "Order"
        
        if order_type == "Compose":
            # Загружаем составной заказ
            return await load_compose_order_with_auth(order_id)
        else:
            # Загружаем обычный заказ
            try:
                headers = auth_manager.get_auth_headers()
                async with httpx.AsyncClient() as client:
                    resp = await client.get(f"{BACKEND_URL}/api/order/{order_id}", headers=headers)
                    resp.raise_for_status()
                    order = resp.json()
                

                placeholder = get_placeholder_order()
                updates, _, comment_value = fill_fields_from_order_diff(order, placeholder)
                comp_updates = fill_components_fields_from_order(order, {"components": components_catalog_for_ui if components_catalog_for_ui else COMPONENTS_CATALOG.get("components", [])})
                
                # Возвращаем обновления в правильном порядке
                result = [gr.update(visible=False, value=""), gr.update(visible=False), gr.update(visible=True)] + updates + comp_updates + [gr.update(value=comment_value), gr.update(value=""), gr.update(value=order.get("id")), gr.update(value=order), gr.update(value=order.get("id"))] + [gr.update() for _ in range(21)] + [gr.update(value=""), gr.update(value=""), gr.update(value="0"), gr.update(value=""), gr.update(value="")]
                
                # Дополняем до нужного количества
                expected_count = 340
                while len(result) < expected_count:
                    result.append(gr.update())
                
                return result
                
            except Exception as e:
                logger.error(f"Ошибка при загрузке заказа: {e}")
                return build_error_response(f"Ошибка при загрузке заказа: {e}", len(components_ui_inputs))

    async def load_compose_order_with_auth(order_id):
        """Загружает составной заказ в вкладку 'Формирование составного заказа' с аутентификацией"""

        
        auth_manager = get_auth_manager()
        if not auth_manager.is_authenticated():
            return build_error_response("Требуется аутентификация", len(components_ui_inputs))
        
        try:
            # Получаем данные составного заказа с аутентификацией
            headers = auth_manager.get_auth_headers()
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{BACKEND_URL}/api/compose_order/{order_id}", headers=headers)
                resp.raise_for_status()
                compose_order_data = resp.json()
            

            
            if "error" in compose_order_data:
                result = [gr.update(visible=True, value=f"Ошибка: {compose_order_data['error']}"), gr.update(visible=True), gr.update(visible=False)] + [gr.update() for _ in range(21)] + [gr.update() for _ in components_ui_inputs] + [gr.update(value="Оставьте комментарий..."), gr.update(value=""), gr.update(value=None), gr.update(), gr.update()] + [gr.update() for _ in range(21)] + [gr.update(value=""), gr.update(value=""), gr.update(value="0"), gr.update(value=""), gr.update(value="")]
                
                # Дополняем до нужного количества
                expected_count = 340
                while len(result) < expected_count:
                    result.append(gr.update())
                
                return result
            
            # Извлекаем данные клиента
            client_data = compose_order_data.get("client_data", {})
            # Извлекаем общие параметры заказа (visit_date, discount)
            general_order_params = compose_order_data.get("order_params", {})
            
            # Если order_params пустой или не содержит нужных полей, используем данные из первого кондиционера
            if not general_order_params or "visit_date" not in general_order_params or "discount" not in general_order_params:

                
                # Извлекаем данные из первого кондиционера
                airs = compose_order_data.get("airs", [])
                if airs and len(airs) > 0:
                    first_air = airs[0]
                    first_air_order_params = first_air.get("order_params", {})
                    
                    if not general_order_params:
                        general_order_params = {}
                    
                    # Берем дату и скидку из первого кондиционера
                    if "visit_date" not in general_order_params and "visit_date" in first_air_order_params:
                        general_order_params["visit_date"] = first_air_order_params["visit_date"]
                    
                    if "discount" not in general_order_params and "discount" in first_air_order_params:
                        general_order_params["discount"] = first_air_order_params["discount"]
                    
                    # Если все еще нет данных, используем дефолтные значения
                    if "visit_date" not in general_order_params:
                        general_order_params["visit_date"] = datetime.date.today().strftime('%Y-%m-%d')
                    if "discount" not in general_order_params:
                        general_order_params["discount"] = 0
                else:
                    # Если нет кондиционеров, используем дефолтные значения
                    if not general_order_params:
                        general_order_params = {}
                    if "visit_date" not in general_order_params:
                        general_order_params["visit_date"] = datetime.date.today().strftime('%Y-%m-%d')
                    if "discount" not in general_order_params:
                        general_order_params["discount"] = 0
            
            # Извлекаем данные из последнего кондиционера
            airs = compose_order_data.get("airs", [])
            last_air = airs[-1] if airs else {}
            last_air_order_params = last_air.get("order_params", {})
            last_air_aircon_params = last_air.get("aircon_params", {})
            
            # Создаем обновления для полей составного заказа
            compose_fields_updates = [
                gr.update(value=client_data.get("full_name", "")),  # 1. compose_name
                gr.update(value=client_data.get("phone", "")),      # 2. compose_phone
                gr.update(value=client_data.get("email", "")),      # 3. compose_mail
                gr.update(value=client_data.get("address", "")),    # 4. compose_address
                gr.update(value=general_order_params.get("visit_date", "")),  # 5. compose_date
                gr.update(value=safe_int(general_order_params.get("discount", 0))),   # 6. compose_discount
                gr.update(value=safe_float(last_air_aircon_params.get("area", 50))),      # 7. compose_area
                gr.update(value=last_air_order_params.get("room_type", "")),      # 8. compose_type_room
                gr.update(value=safe_bool(last_air_aircon_params.get("wifi", False))),   # 9. compose_wifi
                gr.update(value=safe_bool(last_air_aircon_params.get("inverter", False))),   # 10. compose_inverter
                gr.update(value=safe_float(last_air_aircon_params.get("price_limit", 10000))),   # 11. compose_price
                gr.update(value=last_air_aircon_params.get("mount_type", "Любой")), # 12. compose_mount_type
                gr.update(value=safe_float(last_air_aircon_params.get("ceiling_height", 2.7))),     # 13. compose_ceiling_height
                gr.update(value=safe_illumination(last_air_aircon_params.get("illumination", "Средняя"))), # 14. compose_illumination
                gr.update(value=safe_int(last_air_aircon_params.get("num_people", 1))),       # 15. compose_num_people
                gr.update(value=last_air_aircon_params.get("activity", "Сидячая работа")), # 16. compose_activity
                gr.update(value=safe_int(last_air_aircon_params.get("num_computers", 0))),       # 17. compose_num_computers
                gr.update(value=safe_int(last_air_aircon_params.get("num_tvs", 0))),       # 18. compose_num_tvs
                gr.update(value=safe_float(last_air_aircon_params.get("other_power", 0))),       # 19. compose_other_power
                gr.update(value=last_air_aircon_params.get("brand", "Любой")), # 20. compose_brand
                gr.update(value=safe_float(last_air_order_params.get("installation_price", 0))),       # 21. compose_installation_price
            ]
            
            # Загружаем комплектующие
            components = compose_order_data.get("components", [])
            comp_updates = fill_components_fields_from_order({"components": components}, {"components": components_catalog_for_ui if components_catalog_for_ui else COMPONENTS_CATALOG.get("components", [])})
            
            # Загружаем комментарий
            comment_value = compose_order_data.get("comment", "Оставьте комментарий...")
            
            # Возвращаем обновления в правильном порядке
            # Формат: [load_error(1), orders_list_screen(1), main_order_screen(1), обычные_поля(22), components, comment(5), compose_поля(22), compose_статусы(4)]
            
            result = [gr.update(visible=False, value=""), gr.update(visible=False), gr.update(visible=True)] + [gr.update() for _ in range(21)] + comp_updates + [gr.update(value=comment_value), gr.update(value=""), gr.update(value=order_id), gr.update(value=compose_order_data), gr.update(value=order_id)] + compose_fields_updates + [gr.update(value=""), order_id, gr.update(value="0"), gr.update(value=""), gr.update(value="")]
            
            # Дополняем до нужного количества
            expected_count = 340
            while len(result) < expected_count:
                result.append(gr.update())
            
            return result
            
        except Exception as e:
            logger.error(f"Ошибка при загрузке составного заказа: {e}", exc_info=True)
            return build_error_response(f"Ошибка при загрузке составного заказа: {e}", len(components_ui_inputs))

    async def select_aircons_with_auth(order_id_hidden_value):
        """Подбор кондиционеров с аутентификацией."""
        auth_manager = get_auth_manager()
        if not auth_manager.is_authenticated():
            return "Требуется аутентификация"
        
        payload = {"id": order_id_hidden_value}
        try:
            headers = auth_manager.get_auth_headers()
            async with httpx.AsyncClient() as client:
                response = await client.post(f"{BACKEND_URL}/api/select_aircons/", json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()
                if "error" in data:
                    logger.error(f"Ошибка от бэкенда: {data['error']}")
                    return f"Ошибка: {data['error']}"
                aircons_list = data.get("aircons_list", [])
                if isinstance(aircons_list, list) and aircons_list:
                    total_count = data.get('total_count', len(aircons_list))
                    formatted_list = f"Найдено {total_count} подходящих кондиционеров:\n\n"
                    for i, aircon in enumerate(aircons_list, 1):
                        formatted_list += f"{i}. {aircon.get('brand', 'N/A')} {aircon.get('model_name', 'N/A')}\n"
                        formatted_list += f"   Мощность охлаждения: {aircon.get('cooling_power_kw', 'N/A')} кВт\n"
                        formatted_list += f"   Цена: {aircon.get('retail_price_byn', 'N/A')} BYN\n"
                        formatted_list += f"   Инвертор: {'Да' if aircon.get('is_inverter') else 'Нет'}\n\n"
                    logger.info(f"Подбор кондиционеров завершен успешно: найдено {total_count} вариантов.")
                    return formatted_list
                else:
                    formatted_list = "Подходящих кондиционеров не найдено."
                    logger.info(f"Подбор кондиционеров завершен: подходящих кондиционеров не найдено.")
                    return formatted_list
        except httpx.RequestError as e:
            error_message = f"Не удалось связаться с бэкендом: {e}"
            logger.error(error_message, exc_info=True)
            return error_message
        except Exception as e:
            error_message = f"Произошла внутренняя ошибка: {e}"
            logger.error(error_message, exc_info=True)
            return error_message

    async def generate_kp_with_auth(order_id_hidden_value):
        """Генерация КП с аутентификацией."""
        auth_manager = get_auth_manager()
        if not auth_manager.is_authenticated():
            return "Требуется аутентификация", None
        
        payload = {"id": order_id_hidden_value}
        try:
            headers = auth_manager.get_auth_headers()
            async with httpx.AsyncClient() as client:
                response = await client.post(f"{BACKEND_URL}/api/generate_offer/", json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()
                if "error" in data:
                    logger.error(f"Ошибка от бэкенда: {data['error']}")
                    return f"Ошибка: {data['error']}", None
                pdf_path = data.get("pdf_path", None)
                formatted_list = "Коммерческое предложение генерируется... Пожалуйста, скачайте PDF файл."
                logger.info(f"КП успешно сформировано.")
                return formatted_list, pdf_path
        except httpx.RequestError as e:
            error_message = f"Не удалось связаться с бэкендом: {e}"
            logger.error(error_message, exc_info=True)
            return error_message, None
        except Exception as e:
            error_message = f"Произошла внутренняя ошибка: {e}"
            logger.error(error_message, exc_info=True)
            return error_message, None

    async def save_kp_with_auth(order_id_hidden_value, client_name, phone, mail, address, date, area, type_room, discount, wifi, inverter, price, mount_type, ceiling_height, illumination, num_people, activity, num_computers, num_tvs, other_power, brand, installation_price):
        """Сохранение данных для КП с аутентификацией."""
        auth_manager = get_auth_manager()
        if not auth_manager.is_authenticated():
            return "Требуется аутентификация", order_id_hidden_value
        
        order_id = order_id_hidden_value
        payload = {
            "client_data": {"full_name": client_name, "phone": phone, "email": mail, "address": address},
            "order_params": {"room_area": area, "room_type": type_room, "discount": discount, "visit_date": fix_date(date), "installation_price": installation_price},
            "aircon_params": {"wifi": wifi, "inverter": inverter, "price_limit": price, "brand": brand, "mount_type": mount_type, "area": area, "ceiling_height": ceiling_height, "illumination": illumination, "num_people": num_people, "activity": activity, "num_computers": num_computers, "num_tvs": num_tvs, "other_power": other_power},
            "status": "partially filled"
        }
        if order_id is not None and str(order_id).isdigit():
            payload["id"] = int(order_id)
        
        try:
            headers = auth_manager.get_auth_headers()
            async with httpx.AsyncClient() as client:
                resp = await client.post(f"{BACKEND_URL}/api/save_order/", json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()
                if data.get("success"):
                    new_order_id = data.get("order_id")
                    msg = f"Данные для КП успешно сохранены! ID: {new_order_id}"
                    return msg, new_order_id
                else:
                    error_msg = data.get("error", "Неизвестная ошибка от бэкенда.")
                    return f"Ошибка: {error_msg}", order_id
        except Exception as e:
            logger.error(f"Ошибка при сохранении данных для КП: {e}", exc_info=True)
            return f"Ошибка: {e}", order_id

    async def save_components_with_auth(order_id_hidden_value, compose_order_id_hidden_value, *components_inputs):
        """Сохранение комплектующих с аутентификацией."""
        auth_manager = get_auth_manager()
        if not auth_manager.is_authenticated():
            return "Требуется аутентификация", order_id_hidden_value
        
        order_id = compose_order_id_hidden_value if compose_order_id_hidden_value and compose_order_id_hidden_value != 0 else order_id_hidden_value

        
        selected_components = []
        i = 0
        for component_data in components_catalog_for_ui:
            if i + 2 >= len(components_inputs):
                break
            is_selected, qty, length = components_inputs[i], components_inputs[i+1], components_inputs[i+2]
            i += 3
            is_measurable = (
                "труба" in component_data["name"].lower() or
                "кабель" in component_data["name"].lower() or
                "теплоизоляция" in component_data["name"].lower() or
                "шланг" in component_data["name"].lower() or
                "провод" in component_data["name"].lower() or
                component_data.get("category") == "Кабель-каналы"
            )
            comp_item = {
                "name": component_data["name"], "price": component_data.get("price", 0),
                "currency": COMPONENTS_CATALOG.get("catalog_info", {}).get("currency", "BYN"),
                "selected": is_selected
            }
            if is_measurable:
                comp_item["unit"] = "м."
                comp_item["qty"] = 0
                comp_item["length"] = int(length) if length else 0
            else:
                comp_item["unit"] = "шт."
                comp_item["qty"] = int(qty) if qty else 0
                comp_item["length"] = 0
            selected_components.append(comp_item)
        
        try:
            headers = auth_manager.get_auth_headers()
            async with httpx.AsyncClient() as client:
                # Определяем тип заказа
                if compose_order_id_hidden_value and compose_order_id_hidden_value != 0 and compose_order_id_hidden_value == order_id:
                    # Составной заказ
                    payload = {
                        "id": order_id,
                        "components": selected_components,
                        "status": "completely filled"
                    }
                    resp = await client.post(f"{BACKEND_URL}/api/save_compose_order/", json=payload, headers=headers)
                else:
                    # Обычный заказ
                    payload = {"components": selected_components, "status": "completely filled"}
                    if order_id is not None and str(order_id).isdigit():
                        payload["id"] = int(order_id)
                    resp = await client.post(f"{BACKEND_URL}/api/save_order/", json=payload, headers=headers)
                
                resp.raise_for_status()
                data = resp.json()
                if data.get("success"):
                    msg = f"Комплектующие успешно сохранены!"
                    return msg, order_id
                else:
                    error_msg = data.get("error", "Неизвестная ошибка от бэкенда.")
                    return f"Ошибка: {error_msg}", order_id
        except Exception as e:
            logger.error(f"Ошибка при сохранении комплектующих: {e}", exc_info=True)
            return f"Ошибка: {e}", order_id

    async def save_comment_with_auth(order_id_hidden_value, comment_value):
        """Сохранение комментария с аутентификацией."""
        auth_manager = get_auth_manager()
        if not auth_manager.is_authenticated():
            return "Требуется аутентификация"
        
        try:
            order_id = int(order_id_hidden_value)
            if not order_id or order_id <= 0:
                return "Ошибка: Некорректный ID заказа!"
        except Exception as e:
            logger.error(f"Ошибка преобразования order_id_hidden_value: {e}")
            return f"Ошибка: Некорректный ID заказа!"
        
        payload = {"id": order_id, "comment": comment_value}
        try:
            headers = auth_manager.get_auth_headers()
            async with httpx.AsyncClient() as client:
                # Пробуем сначала составной заказ
                try:
                    resp = await client.post(f"{BACKEND_URL}/api/save_compose_order/", json=payload, headers=headers)
                    resp.raise_for_status()
                    data = resp.json()
                    if data.get("success"):
                        return "Комментарий успешно сохранён!"
                except:
                    pass
                
                # Если не составной, пробуем обычный заказ
                resp = await client.post(f"{BACKEND_URL}/api/save_order/", json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()
                if data.get("success"):
                    return "Комментарий успешно сохранён!"
                else:
                    return f"Ошибка: {data.get('error', 'Неизвестная ошибка от бэкенда.')}"
        except Exception as e:
            logger.error(f"Ошибка при сохранении комментария: {e}", exc_info=True)
            return f"Ошибка: {e}"

    # --- Привязка обработчиков с аутентификацией ---
    load_selected_btn.click(
        fn=load_selected_order_with_auth,
        inputs=[orders_radio],
        outputs=[load_error, orders_list_screen, main_order_screen, name, phone, mail, address, date, area, type_room, discount, wifi, inverter, price, mount_type, ceiling_height, illumination, num_people, activity, num_computers, num_tvs, other_power, brand, installation_price] + components_ui_inputs + [comment_box, save_comment_status, order_id_hidden, order_state, order_id_state, compose_name, compose_phone, compose_mail, compose_address, compose_date, compose_discount, compose_area, compose_type_room, compose_wifi, compose_inverter, compose_price, compose_mount_type, compose_ceiling_height, compose_illumination, compose_num_people, compose_activity, compose_num_computers, compose_num_tvs, compose_other_power, compose_brand, compose_installation_price, compose_save_status, compose_order_id_hidden, compose_aircon_counter, compose_aircons_output, compose_kp_status]
    )

    select_aircons_btn.click(
        fn=select_aircons_with_auth,
        inputs=[order_id_hidden],
        outputs=[aircons_output]
    )

    generate_btn.click(
        fn=generate_kp_with_auth,
        inputs=[order_id_hidden],
        outputs=[aircons_output, pdf_output]
    )

    save_kp_btn.click(
        fn=save_kp_with_auth,
        inputs=[order_id_hidden, name, phone, mail, address, date, area, type_room, discount, wifi, inverter, price, mount_type, ceiling_height, illumination, num_people, activity, num_computers, num_tvs, other_power, brand, installation_price],
        outputs=[save_kp_status, order_id_hidden]
    )

    save_components_btn.click(
        fn=save_components_with_auth,
        inputs=[order_id_hidden, compose_order_id_hidden] + components_ui_inputs,
        outputs=[save_components_status, order_id_hidden]
    )

    save_comment_btn.click(
        fn=save_comment_with_auth,
        inputs=[order_id_hidden, comment_box],
        outputs=[save_comment_status]
    )

    # --- Обработчики для составных заказов с аутентификацией ---
    
    async def save_compose_client_with_auth(compose_order_id_hidden_value, client_name, client_phone, client_mail, client_address, visit_date, discount):
        """Сохранение данных клиента для составного заказа с аутентификацией."""
        auth_manager = get_auth_manager()
        if not auth_manager.is_authenticated():
            return "Требуется аутентификация", None, None
        
        try:
            if not client_name or not client_phone:
                return "Ошибка: Имя клиента и телефон обязательны!", None, None
            
            def safe_int(value):
                if value is None or value == "":
                    return 0
                try:
                    return int(float(value))
                except (ValueError, TypeError):
                    return 0
            
            client_data = {
                "full_name": client_name,
                "phone": client_phone,
                "email": client_mail or "",
                "address": client_address or ""
            }
            
            order_params = {
                "visit_date": visit_date or "",
                "discount": safe_int(discount)
            }
            
            existing_order_id = None
            if compose_order_id_hidden_value and compose_order_id_hidden_value != "" and compose_order_id_hidden_value != "None":
                try:
                    existing_order_id = int(compose_order_id_hidden_value)
                    if existing_order_id <= 0:
                        existing_order_id = None
                except (ValueError, TypeError):
                    existing_order_id = None
            
            headers = auth_manager.get_auth_headers()
            async with httpx.AsyncClient() as client:
                if existing_order_id:
                    # Обновляем существующий заказ
                    get_resp = await client.get(f"{BACKEND_URL}/api/compose_order/{existing_order_id}", headers=headers)
                    get_resp.raise_for_status()
                    current_order_data = get_resp.json()
                    
                    if "error" in current_order_data:
                        return f"Ошибка: {current_order_data['error']}", None, None
                    
                    updated_order_data = current_order_data.copy()
                    updated_order_data["client_data"] = client_data
                    updated_order_data["order_params"] = order_params
                    
                    payload = {
                        "id": existing_order_id,
                        "compose_order_data": updated_order_data,
                        "status": "draft"
                    }
                    
                    resp = await client.post(f"{BACKEND_URL}/api/save_compose_order/", json=payload, headers=headers)
                    resp.raise_for_status()
                    data = resp.json()
                    if data.get("success"):
                        msg = f"Данные клиента успешно обновлены! ID: {existing_order_id}"
                        return msg, existing_order_id, existing_order_id
                    else:
                        error_msg = data.get("error", "Неизвестная ошибка от бэкенда.")
                        return f"Ошибка: {error_msg}", None, None
                else:
                    # Создаем новый заказ
                    compose_order_data = {
                        "client_data": client_data,
                        "order_params": order_params,
                        "airs": [],
                        "components": [],
                        "comment": "Оставьте комментарий...",
                        "status": "draft"
                    }
                    
                    payload = {
                        "compose_order_data": compose_order_data,
                        "status": "draft"
                    }
                    
                    resp = await client.post(f"{BACKEND_URL}/api/save_compose_order/", json=payload, headers=headers)
                    resp.raise_for_status()
                    data = resp.json()
                    if data.get("success"):
                        order_id = data.get("order_id")
                        msg = f"Данные клиента успешно сохранены! ID: {order_id}"
                        return msg, order_id, order_id
                    else:
                        error_msg = data.get("error", "Неизвестная ошибка от бэкенда.")
                        return f"Ошибка: {error_msg}", None, None
                    
        except Exception as e:
            logger.error(f"Ошибка при сохранении данных клиента: {e}", exc_info=True)
            return f"Ошибка: {e}", None, None

    async def save_compose_order_with_auth(compose_order_id_hidden_value, client_name, client_phone, client_mail, client_address, visit_date, room_area, room_type, discount, wifi, inverter, price_limit, mount_type, ceiling_height, illumination, num_people, activity, num_computers, num_tvs, other_power, brand, installation_price):
        """Сохранение данных кондиционера для составного заказа с аутентификацией."""

        
        auth_manager = get_auth_manager()
        if not auth_manager.is_authenticated():
            return "Требуется аутентификация", None, None, "0"
        
        if not compose_order_id_hidden_value or compose_order_id_hidden_value <= 0:
            
            return "Ошибка: сначала сохраните данные клиента!", None, None, "0"
        
        try:
            def safe_float(value):
                if value is None or value == "":
                    return 0.0
                try:
                    return float(value)
                except (ValueError, TypeError):
                    return 0.0
            
            def safe_int(value):
                if value is None or value == "":
                    return 0
                try:
                    return int(float(value))
                except (ValueError, TypeError):
                    return 0
            
            def safe_bool(value):
                if value is None or value == "":
                    return False
                try:
                    return bool(value)
                except (ValueError, TypeError):
                    return False
            
            order_params = {
                "visit_date": visit_date,
                "room_area": safe_float(room_area),
                "room_type": room_type,
                "discount": safe_int(discount),
                "installation_price": safe_float(installation_price)
            }
            
            aircon_params = {
                "area": safe_float(room_area),
                "ceiling_height": safe_float(ceiling_height) if ceiling_height else 2.7,
                "illumination": illumination,
                "num_people": safe_int(num_people) if num_people else 1,
                "activity": activity,
                "num_computers": safe_int(num_computers),
                "num_tvs": safe_int(num_tvs),
                "other_power": safe_float(other_power),
                "brand": brand,
                "price_limit": safe_float(price_limit) if price_limit else 22000,
                "inverter": safe_bool(inverter),
                "wifi": safe_bool(wifi),
                "mount_type": mount_type
            }
            
            order_id = int(compose_order_id_hidden_value)
            headers = auth_manager.get_auth_headers()
            
            async with httpx.AsyncClient() as client:
                check_resp = await client.get(f"{BACKEND_URL}/api/compose_order/{order_id}", headers=headers)
                check_resp.raise_for_status()
                current_order_data = check_resp.json()
                
                if "error" in current_order_data:
                    return f"Ошибка: {current_order_data['error']}", compose_order_id_hidden_value, compose_order_id_hidden_value, "0"
                
                existing_airs = current_order_data.get("airs", [])

                
                if len(existing_airs) == 0:
                    # Создаем первый кондиционер
                    payload = {
                        "id": order_id,
                        "new_aircon_order": {
                            "order_params": order_params,
                            "aircon_params": aircon_params
                        }
                    }
                    
                    resp = await client.post(f"{BACKEND_URL}/api/add_aircon_to_compose_order/", json=payload, headers=headers)
                    resp.raise_for_status()
                    data = resp.json()
                    if data.get("success"):
                        msg = f"Данные кондиционера успешно сохранены!"
                        aircon_count = data.get("aircon_count", 1)
                        return msg, order_id, order_id, str(aircon_count)
                    else:
                        error_msg = data.get("error", "Неизвестная ошибка от бэкенда.")
                        return f"Ошибка: {error_msg}", compose_order_id_hidden_value, compose_order_id_hidden_value, "0"
                else:
                    # Обновляем последний кондиционер
                    payload = {
                        "id": order_id,
                        "update_last_aircon": {
                            "order_params": order_params,
                            "aircon_params": aircon_params
                        },
                        "status": "partially filled"
                    }
                    
                    resp = await client.post(f"{BACKEND_URL}/api/save_compose_order/", json=payload, headers=headers)
                    resp.raise_for_status()
                    data = resp.json()
                    if data.get("success"):
                        # Обновляем общие параметры заказа
                        general_order_params = {
                            "visit_date": visit_date,
                            "discount": safe_int(discount)
                        }
                        
                        fresh_resp = await client.get(f"{BACKEND_URL}/api/compose_order/{order_id}", headers=headers)
                        fresh_resp.raise_for_status()
                        fresh_order_data = fresh_resp.json()
                        
                        updated_order_data = fresh_order_data.copy()
                        updated_order_data["order_params"] = general_order_params
                        
                        general_payload = {
                            "id": order_id,
                            "compose_order_data": updated_order_data,
                            "status": "partially filled"
                        }
                        
                        resp2 = await client.post(f"{BACKEND_URL}/api/save_compose_order/", json=general_payload, headers=headers)
                        resp2.raise_for_status()
                        data2 = resp2.json()
                        
                        if data2.get("success"):
                            order_id = data2.get("order_id")
                            msg = f"Данные кондиционера успешно сохранены!"
                            return msg, order_id, order_id, str(len(existing_airs))
                        else:
                            error_msg = data2.get("error", "Ошибка при обновлении общих параметров.")
                            return f"Ошибка: {error_msg}", compose_order_id_hidden_value, compose_order_id_hidden_value, "0"
                    else:
                        error_msg = data.get("error", "Неизвестная ошибка от бэкенда.")
                        return f"Ошибка: {error_msg}", compose_order_id_hidden_value, compose_order_id_hidden_value, "0"
                    
        except Exception as e:
            logger.error(f"Ошибка при сохранении составного заказа: {e}", exc_info=True)
            return f"Ошибка: {e}", compose_order_id_hidden_value, compose_order_id_hidden_value, "0"

    async def select_compose_aircons_with_auth(order_id_hidden_value):
        """Подбор кондиционеров для составного заказа с аутентификацией."""
        auth_manager = get_auth_manager()
        if not auth_manager.is_authenticated():
            return "Требуется аутентификация"
        
        try:
            order_id = int(order_id_hidden_value)
            if not order_id or order_id <= 0:
                return "Ошибка: Некорректный ID составного заказа!"
        except Exception as e:
            logger.error(f"Ошибка преобразования order_id_hidden_value: {e}")
            return f"Ошибка: Некорректный ID составного заказа!"
        
        try:
            headers = auth_manager.get_auth_headers()
            async with httpx.AsyncClient() as client:
                resp = await client.post(f"{BACKEND_URL}/api/select_compose_aircons/", json={"id": order_id}, headers=headers)
                resp.raise_for_status()
                data = resp.json()
                
                if "error" in data:
                    return f"Ошибка: {data['error']}"
                
                return data.get("result_text", "Результаты подбора кондиционеров не найдены")
                
        except Exception as e:
            logger.error(f"Ошибка при подборе кондиционеров для составного заказа: {e}", exc_info=True)
            return f"Ошибка: {e}"

    async def add_next_aircon_with_auth(order_id_hidden_value, client_name, client_phone, client_mail, client_address, visit_date, room_area, room_type, discount, wifi, inverter, price_limit, mount_type, ceiling_height, illumination, num_people, activity, num_computers, num_tvs, other_power, brand, installation_price):
        """Добавление следующего кондиционера с аутентификацией."""
        auth_manager = get_auth_manager()
        if not auth_manager.is_authenticated():
            return ("Требуется аутентификация", None, None, "0",
                   gr.update(), gr.update(), gr.update(), gr.update(), gr.update(),
                   50, "квартира", gr.update(), False, False, 10000,
                   "Любой", 2.7, "Средняя", 1, "Сидячая работа",
                   0, 0, 0, "Любой", 0)
        
        try:
            order_id = int(order_id_hidden_value)
            if not order_id or order_id <= 0:
                return ("Ошибка: Некорректный ID составного заказа!", None, None, "0",
                       gr.update(), gr.update(), gr.update(), gr.update(), gr.update(),
                       50, "квартира", gr.update(), False, False, 10000,
                       "Любой", 2.7, "Средняя", 1, "Сидячая работа",
                       0, 0, 0, "Любой", 0)
        except Exception as e:
            logger.error(f"Ошибка преобразования order_id_hidden_value: {e}")
            return ("Ошибка: Некорректный ID составного заказа!", None, None, "0",
                   gr.update(), gr.update(), gr.update(), gr.update(), gr.update(),
                   50, "квартира", gr.update(), False, False, 10000,
                   "Любой", 2.7, "Средняя", 1, "Сидячая работа",
                   0, 0, 0, "Любой", 0)
        
        try:
            def safe_float(value):
                if value is None or value == "":
                    return 0.0
                try:
                    return float(value)
                except (ValueError, TypeError):
                    return 0.0
            
            def safe_int(value):
                if value is None or value == "":
                    return 0
                try:
                    return int(float(value))
                except (ValueError, TypeError):
                    return 0
            
            def safe_bool(value):
                if value is None or value == "":
                    return False
                try:
                    return bool(value)
                except (ValueError, TypeError):
                    return False
            
            new_aircon_order = {
                "order_params": {
                    "visit_date": visit_date or "",
                    "room_area": safe_float(room_area),
                    "room_type": room_type or "квартира",
                    "discount": safe_int(discount),
                    "installation_price": safe_float(installation_price)
                },
                "aircon_params": {
                    "area": safe_float(room_area),
                    "ceiling_height": safe_float(ceiling_height),
                    "illumination": illumination or "Средняя",
                    "num_people": safe_int(num_people),
                    "activity": activity or "Сидячая работа",
                    "num_computers": safe_int(num_computers),
                    "num_tvs": safe_int(num_tvs),
                    "other_power": safe_float(other_power),
                    "brand": brand or "Любой",
                    "price_limit": safe_float(price_limit),
                    "inverter": safe_bool(inverter),
                    "wifi": safe_bool(wifi),
                    "mount_type": mount_type or "Любой"
                }
            }
            
            headers = auth_manager.get_auth_headers()
            async with httpx.AsyncClient() as client:
                payload = {
                    "id": order_id,
                    "new_aircon_order": new_aircon_order
                }
                
                resp = await client.post(f"{BACKEND_URL}/api/add_aircon_to_compose_order/", json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()
                
                if data.get("success"):
                    aircon_count = data.get("aircon_count", 0)
                    msg = f"Пожалуйста, введите данные для следующего кондиционера"
    
                    return (msg, order_id, order_id, str(aircon_count), 
                           gr.update(), gr.update(), gr.update(), gr.update(), gr.update(),
                           50, "квартира", gr.update(), False, False, 10000,
                           "Любой", 2.7, "Средняя", 1, "Сидячая работа",
                           0, 0, 0, "Любой", 0)
                else:
                    error_msg = data.get("error", "Неизвестная ошибка от бэкенда.")
    
                    return (f"Ошибка: {error_msg}", order_id_hidden_value, order_id_hidden_value, "0",
                           gr.update(), gr.update(), gr.update(), gr.update(), gr.update(),
                           50, "квартира", gr.update(), False, False, 10000,
                           "Любой", 2.7, "Средняя", 1, "Сидячая работа",
                           0, 0, 0, "Любой", 0)
                    
        except Exception as e:
            logger.error(f"Ошибка при добавлении кондиционера к составному заказу: {e}", exc_info=True)
            return (f"Ошибка: {e}", order_id_hidden_value, order_id_hidden_value, "0",
                   gr.update(), gr.update(), gr.update(), gr.update(), gr.update(),
                   50, "квартира", gr.update(), False, False, 10000,
                   "Любой", 2.7, "Средняя", 1, "Сидячая работа",
                   0, 0, 0, "Любой", 0)

    async def generate_compose_kp_with_auth(order_id_hidden_value):
        """Генерация КП для составного заказа с аутентификацией."""
        auth_manager = get_auth_manager()
        if not auth_manager.is_authenticated():
            return "Требуется аутентификация", None
        
        try:
            order_id = int(order_id_hidden_value)
            if not order_id or order_id <= 0:
                return "Ошибка: Некорректный ID составного заказа!", None
        except Exception as e:
            logger.error(f"Ошибка преобразования order_id_hidden_value: {e}")
            return f"Ошибка: Некорректный ID составного заказа!", None
        
        try:
            payload = {"id": order_id}
            headers = auth_manager.get_auth_headers()
            
            async with httpx.AsyncClient() as client:
                response = await client.post(f"{BACKEND_URL}/api/generate_compose_offer/", json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()
                
                if "error" in data:
                    logger.error(f"Ошибка от бэкенда: {data['error']}")
                    error_msg = data['error']
                    if "Нет кондиционеров с подобранными вариантами" in error_msg:
                        return f"Ошибка: {error_msg}\n\nДля генерации КП необходимо:\n1. Подобрать кондиционеры для каждого помещения (нажать кнопку 'Подобрать')\n2. Добавить все необходимые помещения (нажать кнопку 'Ввести данные для следующего кондиционера')\n3. Повторить подбор для каждого нового помещения", None
                    else:
                        return f"Ошибка: {error_msg}", None
                
                pdf_path = data.get("pdf_path", None)
                if pdf_path:
                    formatted_list = "Коммерческое предложение для составного заказа успешно сгенерировано! Пожалуйста, скачайте PDF файл."
                    logger.info(f"КП для составного заказа {order_id} успешно сформировано.")
                    return formatted_list, pdf_path
                else:
                    return "Ошибка: PDF файл не был создан", None
                    
        except httpx.RequestError as e:
            error_message = f"Не удалось связаться с бэкендом: {e}"
            logger.error(error_message, exc_info=True)
            return error_message, None
        except Exception as e:
            error_message = f"Произошла внутренняя ошибка: {e}"
            logger.error(error_message, exc_info=True)
            return error_message, None

    async def delete_compose_order_with_auth(order_id_hidden_value):
        """Удаление составного заказа с аутентификацией."""
        auth_manager = get_auth_manager()
        if not auth_manager.is_authenticated():
            return "Требуется аутентификация", gr.update(visible=True), gr.update(visible=False), gr.update(visible=False), None, get_placeholder_order()
        
        try:
            order_id = int(order_id_hidden_value)
            if not order_id or order_id <= 0:
                return "Ошибка: Некорректный ID составного заказа!", gr.update(visible=True), gr.update(visible=False), gr.update(visible=False), None, get_placeholder_order()
        except Exception as e:
            logger.error(f"Ошибка преобразования order_id_hidden_value: {e}")
            return f"Ошибка: Некорректный ID составного заказа!", gr.update(visible=True), gr.update(visible=False), gr.update(visible=False), None, get_placeholder_order()
        
        try:
            headers = auth_manager.get_auth_headers()
            async with httpx.AsyncClient() as client:
                resp = await client.delete(f"{BACKEND_URL}/api/compose_order/{order_id}", headers=headers)
                resp.raise_for_status()
                data = resp.json()
                if data.get("success"):
                    logger.info(f"Составной заказ {order_id} успешно удален")
                    return "Составной заказ успешно удален! Перенаправление на главную страницу...", gr.update(visible=True), gr.update(visible=False), gr.update(visible=False), None, get_placeholder_order()
                else:
                    error_msg = data.get("error", "Неизвестная ошибка при удалении заказа")
                    logger.error(f"Ошибка удаления составного заказа {order_id}: {error_msg}")
                    return f"Ошибка: {error_msg}", gr.update(visible=False), gr.update(visible=False), gr.update(visible=True), order_id, None
        except Exception as e:
            logger.error(f"Ошибка при удалении составного заказа: {e}", exc_info=True)
            return f"Ошибка: {e}", gr.update(visible=False), gr.update(visible=False), gr.update(visible=True), order_id, None

    # --- Привязка обработчиков для составных заказов с аутентификацией ---
    compose_save_client_btn.click(
        fn=save_compose_client_with_auth,
        inputs=[compose_order_id_hidden, compose_name, compose_phone, compose_mail, compose_address, compose_date, compose_discount],
        outputs=[compose_save_client_status, compose_order_id_hidden, order_id_hidden]
    )
    
    compose_save_btn.click(
        fn=save_compose_order_with_auth,
        inputs=[compose_order_id_hidden, compose_name, compose_phone, compose_mail, compose_address, compose_date, 
               compose_area, compose_type_room, compose_discount, compose_wifi, compose_inverter, compose_price, 
               compose_mount_type, compose_ceiling_height, compose_illumination, compose_num_people, compose_activity, 
               compose_num_computers, compose_num_tvs, compose_other_power, compose_brand, compose_installation_price],
        outputs=[compose_save_status, compose_order_id_hidden, compose_order_id_hidden, compose_aircon_counter]
    )
    
    compose_select_btn.click(
        fn=select_compose_aircons_with_auth,
        inputs=[compose_order_id_hidden],
        outputs=[compose_aircons_output]
    )
    
    compose_add_aircon_btn.click(
        fn=add_next_aircon_with_auth,
        inputs=[compose_order_id_hidden, compose_name, compose_phone, compose_mail, compose_address, compose_date, 
               compose_area, compose_type_room, compose_discount, compose_wifi, compose_inverter, compose_price, 
               compose_mount_type, compose_ceiling_height, compose_illumination, compose_num_people, compose_activity, 
               compose_num_computers, compose_num_tvs, compose_other_power, compose_brand, compose_installation_price],
        outputs=[compose_save_status, compose_order_id_hidden, order_id_hidden, compose_aircon_counter, compose_name, compose_phone, compose_mail, compose_address, compose_date,
                compose_area, compose_type_room, compose_discount, compose_wifi, compose_inverter, compose_price,
                compose_mount_type, compose_ceiling_height, compose_illumination, compose_num_people, compose_activity,
                compose_num_computers, compose_num_tvs, compose_other_power, compose_brand, compose_installation_price]
    )
    
    compose_generate_kp_btn.click(
        fn=generate_compose_kp_with_auth,
        inputs=[compose_order_id_hidden],
        outputs=[compose_kp_status, compose_pdf_output]
    )
    
    compose_delete_btn.click(
        fn=delete_compose_order_with_auth,
        inputs=[compose_order_id_hidden],
        outputs=[compose_save_status, start_screen, orders_list_screen, main_order_screen, compose_order_id_hidden, order_state]
    )

# Экспортируем интерфейс
__all__ = ['interface']
