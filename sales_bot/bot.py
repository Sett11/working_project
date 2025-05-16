import os
import asyncio
import re
import signal
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from utils.mylogger import Logger
from utils.llm import AsyncOpenAIClient
from db.database import Database

load_dotenv()

# Загрузка и проверка переменных окружения
MAX_REQUESTS_PER_DAY = os.getenv("MAX_REQUESTS_PER_DAY", "15")
MAX_REQUESTS_PER_USER = os.getenv("MAX_REQUESTS_PER_USER", "50") 
MESSAGE_CHUNK_SIZE = int(os.getenv("MESSAGE_CHUNK_SIZE", "4096"))
GPT_MODEL = os.getenv("GPT_MODEL", "gpt-4.1-mini")
BASE_URL = os.getenv("BASE_URL", "https://api.openai.com/v1")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# Инициализация логгера
logger = Logger("bot", "bot_events.log")

# Проверка обязательных переменных окружения
if not TELEGRAM_TOKEN:
    logger.critical("TELEGRAM_TOKEN не найден в .env файле")
    raise ValueError("❌ TELEGRAM_TOKEN не найден. Убедитесь, что он указан в .env")

if not OPENAI_API_KEY:
    logger.critical("OPENAI_API_KEY не найден в .env файле")
    raise ValueError("❌ OPENAI_API_KEY не найден. Убедитесь, что он указан в .env")

if not GPT_MODEL or not BASE_URL:
    logger.critical("Не указаны GPT_MODEL или BASE_URL в .env файле")
    raise ValueError("❌ Не указаны GPT_MODEL или BASE_URL в .env файле")

if not MAX_REQUESTS_PER_DAY or not MAX_REQUESTS_PER_USER:
    logger.critical("Не установлены лимиты запросов в .env файле")
    raise ValueError("❌ Не установлены лимиты запросов в .env файле")

class BotHandler:
    """Основной класс обработчика бота"""
    def __init__(self):
        self.prompts = {}
        self.user_sessions = {}
        self.db = Database()
        self.llm_client = AsyncOpenAIClient(
            model_name=GPT_MODEL,
            api_key=OPENAI_API_KEY,
            base_url=BASE_URL
        )
        self._load_prompts()
        logger.info("Бот инициализирован")

    def _load_prompts(self):
        """Загрузка промптов из файлов"""
        prompt_files = {
            2: "steps/step_2_purchcenter.txt",
            3: "steps/step_3_avatar.txt",
            4: "steps/step_4_model.txt",
            5: "steps/step_5_svyazki.txt",
            6: "steps/step_6_tap.txt"
        }

        for step, filename in prompt_files.items():
            try:
                with open(filename, "r", encoding="utf-8") as f:
                    self.prompts[step] = f.read()
                    logger.info(f"Промт для шага {step} загружен из {filename}")
            except FileNotFoundError:
                logger.critical(f"Файл промпта {filename} не найден")
                raise
            except Exception as e:
                logger.error(f"Ошибка при загрузке промпта {filename}: {str(e)}")
                raise

    async def send_long_message(self, text: str, update: Update):
        """Отправка длинного сообщения с разбивкой на части"""
        try:
            if not text:
                logger.warning("Попытка отправить пустое сообщение")
                return

            for i in range(0, len(text), MESSAGE_CHUNK_SIZE):
                chunk = text[i:i+MESSAGE_CHUNK_SIZE]
                await update.message.reply_text(chunk)
                await asyncio.sleep(0.3)
            
            logger.debug(f"Успешно отправлено длинное сообщение (частей: {len(text) // MESSAGE_CHUNK_SIZE + 1})")
        except Exception as e:
            logger.error(f"Ошибка при отправке длинного сообщения: {str(e)}")
            await update.message.reply_text("⚠️ Произошла ошибка при отправке сообщения. Попробуйте позже.")

    async def ask_gpt(self, system_prompt: str, user_prompt: str, request_type: str, user_id: int):
        """Асинхронный запрос к OpenAI через AsyncOpenAIClient"""
        try:
            # Проверка лимитов
            daily_ok, total_ok = await self.db.check_rate_limit(user_id)
            if not daily_ok:
                return (
                    f"⚠️ Вы превысили Ваш дневной лимит в {MAX_REQUESTS_PER_DAY} запроса. Попробуйте, пожалуйста, завтра!",
                    0, 0, 0
                )
            if not total_ok:
                return (
                    f"⚠️ Вы превысили Ваш лимит в {MAX_REQUESTS_PER_USER} запросов.\n"
                    f"Для получения дополнительной информации перейдите, пожалуйста, в канал:\n"
                    f"https://t.me/SkillsForSalescom",
                    0, 0, 0
                )

            start_time = datetime.now()
            
            # Подготовка сообщений
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            # Выполнение запроса через AsyncOpenAIClient
            content, input_tokens, output_tokens = await self.llm_client.generate(
                messages=messages,
                temperature=0.7,
                max_tokens=2048
            )
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            # Если получили сообщение об ошибке (начинается с ⚠️)
            if content.startswith("⚠️"):
                logger.warning(f"LLM вернул ошибку: {content}")
                return content, 0, 0, 0

            # Вычисляем стоимость только для успешных запросов
            cost = input_tokens * 0.0000004 + output_tokens * 0.0000016

            # Логирование запроса
            await self.db.log_request(user_id, request_type, input_tokens + output_tokens, cost)

            logger.info(
                f"GPT запрос выполнен. User: {user_id}, Type: {request_type}, "
                f"Tokens: {input_tokens} in, {output_tokens} out, "
                f"Cost: ${cost:.6f}, Time: {processing_time:.2f} сек."
            )

            return content, input_tokens, output_tokens, cost

        except Exception as e:
            error_msg = f"Ошибка при обращении к OpenAI: {str(e)}"
            logger.error(error_msg)
            return "⚠️ Извините, произошла ошибка при обработке запроса. Пожалуйста, попробуйте позже.", 0, 0, 0

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start"""
        try:
            chat_id = update.effective_chat.id
            user = update.effective_user
            
            # Проверка лимитов перед стартом новой сессии
            daily_ok, total_ok = await self.db.check_rate_limit(chat_id)
            
            if not total_ok:
                await update.message.reply_text(
                    f"⚠️ Вы превысили Ваш лимит в {MAX_REQUESTS_PER_USER} запросов.\n"
                    f"Для получения дополнительной информации перейдите, пожалуйста, в канал:\n"
                    f"https://t.me/SkillsForSalescom"
                )
                return
                
            if not daily_ok:
                await update.message.reply_text(
                    f"⚠️ Вы превысили Ваш дневной лимит в {MAX_REQUESTS_PER_DAY} запроса. "
                    f"Попробуйте, пожалуйста, завтра!"
                )
                return
            
            # Регистрация пользователя
            await self.db.register_user(
                user_id=chat_id,
                username=user.username,
                first_name=user.first_name,
                last_name=user.last_name or ""
            )
            
            # Инициализация сессии
            self.user_sessions[chat_id] = {
                "step": -1,
                "data": {},
                "total_tokens": 0,
                "total_input_tokens": 0,
                "total_output_tokens": 0,
                "start_time": datetime.now().isoformat()
            }
            
            logger.info(f"Новая сессия для пользователя {chat_id}")
            
            await update.message.reply_text(
                "👋 Привет! Я Алёша, чат-бот Лаборатории прикладного маркетинга и продаж.\n\n"
                "📌 Больше полезных инструментов — в нашем Telegram, подписывайся:\n"
                "https://t.me/SkillsForSalescom"
            )
            await update.message.reply_text("Как тебя зовут?")
            
        except Exception as e:
            logger.error(f"Ошибка в обработчике start: {str(e)}")
            await update.message.reply_text("⚠️ Произошла ошибка при старте. Пожалуйста, попробуйте позже.")

    async def reset(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /reset"""
        try:
            chat_id = update.effective_chat.id
            
            if chat_id in self.user_sessions:
                # Сохранение данных сессии перед сбросом
                session = self.user_sessions[chat_id]
                await self.db.save_session_data(
                    user_id=chat_id,
                    step=session["step"],
                    data=session["data"],
                    tokens_used=session.get("total_tokens", 0),
                    total_cost=session.get("total_tokens", 0) * 0.000002
                )
                
                del self.user_sessions[chat_id]
                logger.info(f"Сессия пользователя {chat_id} сброшена")
            
            await update.message.reply_text("🔄 Сессия сброшена. Напиши /start, чтобы начать сначала.")
            
        except Exception as e:
            logger.error(f"Ошибка в обработчике reset: {str(e)}")
            await update.message.reply_text("⚠️ Произошла ошибка при сбросе. Пожалуйста, попробуйте позже.")

    async def handle_initial_steps(self, update: Update, session: dict, chat_id: int):
        """Обработка начальных шагов диалога (шаги -1 до 3)"""
        user_input = update.message.text.strip()
        data = session["data"]
        step = session["step"]

        try:
            if step == -1:
                data["user_name"] = user_input
                await update.message.reply_text(f"Приятно познакомиться, {user_input}! С представителем какой компании вы планируете встречу?")
                session["step"] = 0
                return

            if step == 0:
                data["client_company_name"] = user_input
                await update.message.reply_text("🔗 Укажи, пожалуйста, сайт этой компании.")
                session["step"] = 1
                return

            if step == 1:
                if not re.match(r'^https?://', user_input):
                    user_input = f'http://{user_input}'
                data["client_company_site"] = user_input
                await update.message.reply_text("📄 Кратко опиши направление деятельности этой компании.")
                session["step"] = 2
                return

            if step == 2:
                data["client_company_profile"] = user_input
                await update.message.reply_text("🧩 Что вы хотите предложить данной компании?")
                session["step"] = 3
                return

            if step == 3:
                data["product_offer"] = user_input
                await update.message.reply_text("⌛ <b>Анализирую информацию о закупочном центре...</b>", parse_mode="HTML")

                # Формирование промпта
                prompt_filled = self.prompts[2] \
                    .replace("[НАЗВАНИЕ КОМПАНИИ КЛИЕНТА]", data["client_company_name"]) \
                    .replace("[НАПРАВЛЕНИЕ ДЕЯТЕЛЬНОСТИ]", data["client_company_profile"]) \
                    .replace("[САЙТ КОМПАНИИ]", data["client_company_site"]) \
                    .replace("[ЧТО (ВЫ) ВАША КОМПАНИЯ ПРЕДЛАГАЕТ ДАННОЙ КОМПАНИИ]", data["product_offer"])

                # Запрос к GPT
                purch_result, input_tokens, output_tokens, cost = await self.ask_gpt(
                    system_prompt=self.prompts[2],
                    user_prompt=prompt_filled,
                    request_type="purchcenter_analysis",
                    user_id=chat_id
                )

                # Обновление статистики токенов
                session["total_tokens"] += input_tokens + output_tokens
                session["total_input_tokens"] += input_tokens
                session["total_output_tokens"] += output_tokens

                data["purchcenter_result"] = purch_result
                await self.send_long_message(purch_result, update)

                await update.message.reply_text(
                    "💡 Укажи должность, по которой будем формировать аватар. Например: "
                    "Коммерческий директор, HR-директор или Руководитель отдела продаж."
                )
                session["step"] = 4

        except Exception as e:
            logger.error(f"Ошибка в handle_initial_steps (шаг {step}): {str(e)}")
            await update.message.reply_text(f"⚠️ Ошибка: {str(e)}")
            raise

    async def handle_avatar_step(self, update: Update, session: dict, chat_id: int):
        """Обработка шага создания аватара (шаг 4)"""
        try:
            user_input = update.message.text.strip()
            data = session["data"]
            
            await update.message.reply_text("⌛ <b>Формирую аватар...</b>", parse_mode="HTML")
            
            prompt_filled = self.prompts[3].replace("[УКАЗАТЬ ДОЛЖНОСТЬ / ПОЗИЦИЮ]", user_input)
            data["chosen_position"] = user_input

            # Запрос к GPT
            avatar_result, input_tokens, output_tokens, cost = await self.ask_gpt(
                system_prompt=self.prompts[3],
                user_prompt=prompt_filled,
                request_type="avatar_creation",
                user_id=chat_id
            )

            # Обновление статистики токенов
            session["total_tokens"] += input_tokens + output_tokens
            session["total_input_tokens"] += input_tokens
            session["total_output_tokens"] += output_tokens

            data["avatar_result"] = avatar_result
            await self.send_long_message(avatar_result, update)

            await update.message.reply_text(
                "📦 Для формирования трёхуровневой модели вашего предложения мне нужно знать:\n\n"
                "1. Название вашей компании\n"
                "2. Ваш сайт\n"
                "3. Название продукта/услуги\n"
                "4. Ссылку на продукт/услугу\n\n"
                "📄 Укажите название вашей компании (например: Skills For Sales)"
            )
            session["step"] = 5

        except Exception as e:
            logger.error(f"Ошибка в handle_avatar_step: {str(e)}")
            await update.message.reply_text(f"⚠️ Ошибка при создании аватара: {str(e)}")
            raise

    async def handle_company_info_steps(self, update: Update, session: dict, chat_id: int):
        """Обработка шагов сбора информации о компании (шаги 5-8)"""
        user_input = update.message.text.strip()
        data = session["data"]
        step = session["step"]

        try:
            if step == 5:
                data["your_company_name"] = user_input
                await update.message.reply_text("🌐 Укажите сайт вашей компании (например: https://skillsforsales.ru)")
                session["step"] = 6
                return

            if step == 6:
                if not re.match(r'^https?://', user_input):
                    user_input = f'http://{user_input}'
                data["your_company_website"] = user_input
                await update.message.reply_text("📦 Какой продукт или услугу вы хотите предложить вашему партнеру?")
                session["step"] = 7
                return

            if step == 7:
                data["your_product_name"] = user_input
                await update.message.reply_text("🔗 Укажите ссылку на предлагаемый продукт или услугу на вашем сайте.")
                session["step"] = 8
                return

            if step == 8:
                if not re.match(r'^https?://', user_input):
                    user_input = f'http://{user_input}'
                data["product_link"] = user_input
                
                await update.message.reply_text("🚀 <b>Формирую трёхуровневую модель продукта...</b>", parse_mode="HTML")

                # Формирование промпта для модели продукта
                prompt_filled = self.prompts[4] \
                    .replace("[НАЗВАНИЕ ВАШЕЙ КОМПАНИИ]", data.get("your_company_name", "")) \
                    .replace("[НАПРАВЛЕНИЕ ДЕЯТЕЛЬНОСТИ ВАШЕЙ КОМПАНИИ]", data.get("product_offer", "")) \
                    .replace("[ССЫЛКА ВАШ САЙТ]", data.get("your_company_website", "")) \
                    .replace("[УКАЗАТЬ ПРОДУКТ ИЛИ КАТЕГОРИЮ ПРОДУКТА]", data.get("your_product_name", "")) \
                    .replace("[ССЫЛКА НА ОПИСАНИЕ ПРОДУКТА]", data["product_link"])

                # Запрос к GPT
                product_model, input_tokens, output_tokens, cost = await self.ask_gpt(
                    system_prompt=self.prompts[4],
                    user_prompt=prompt_filled,
                    request_type="product_model",
                    user_id=chat_id
                )

                # Обновление статистики токенов
                session["total_tokens"] += input_tokens + output_tokens
                session["total_input_tokens"] += input_tokens
                session["total_output_tokens"] += output_tokens

                data["product_model"] = product_model
                await self.send_long_message(product_model, update)

                # Переход к генерации ценностных связок
                await self.generate_value_links(update, session, chat_id)

        except Exception as e:
            logger.error(f"Ошибка в handle_company_info_steps (шаг {step}): {str(e)}")
            await update.message.reply_text(f"⚠️ Ошибка: {str(e)}")
            raise

    async def generate_value_links(self, update: Update, session: dict, chat_id: int):
        """Генерация ценностных связок"""
        try:
            data = session["data"]
            await update.message.reply_text("🔗 <b>Формирую ценностные связки...</b>", parse_mode="HTML")

            prompt_filled = self.prompts[5] \
                .replace("[АВАТАР]", data["avatar_result"]) \
                .replace("[МОДЕЛЬ ПРОДУКТА]", data["product_model"]) \
                .replace("[должность из аватара]", data["chosen_position"])

            # Запрос к GPT
            value_links, input_tokens, output_tokens, cost = await self.ask_gpt(
                system_prompt=self.prompts[5],
                user_prompt=prompt_filled,
                request_type="value_links",
                user_id=chat_id
            )

            # Обновление статистики токенов
            session["total_tokens"] += input_tokens + output_tokens
            session["total_input_tokens"] += input_tokens
            session["total_output_tokens"] += output_tokens

            data["value_links"] = value_links
            await self.send_long_message(value_links, update)

            # Переход к генерации аргументации
            await self.generate_pitch(update, session, chat_id)

        except Exception as e:
            logger.error(f"Ошибка в generate_value_links: {str(e)}")
            await update.message.reply_text(f"⚠️ Ошибка при генерации связок: {str(e)}")
            raise

    async def generate_pitch(self, update: Update, session: dict, chat_id: int):
        """Генерация финальной аргументации"""
        try:
            data = session["data"]
            await update.message.reply_text("🗣️ <b>Создаю аргументацию...</b>", parse_mode="HTML")

            prompt_filled = self.prompts[6] \
                .replace("[СВЯЗКИ]", data["value_links"]) \
                .replace("[АВАТАР]", data["avatar_result"]) \
                .replace("[МОДЕЛЬ ПРОДУКТА]", data["product_model"]) \
                .replace("[ДОЛЖНОСТЬ]", data["chosen_position"])

            # Запрос к GPT
            pitch, input_tokens, output_tokens, cost = await self.ask_gpt(
                system_prompt=self.prompts[6],
                user_prompt=prompt_filled,
                request_type="pitch",
                user_id=chat_id
            )

            # Обновление статистики токенов
            session["total_tokens"] += input_tokens + output_tokens
            session["total_input_tokens"] += input_tokens
            session["total_output_tokens"] += output_tokens

            data["pitch"] = pitch
            await self.send_long_message(pitch, update)

            # Сохранение результатов и завершение сессии
            await self.finalize_session(update, session, chat_id)

        except Exception as e:
            logger.error(f"Ошибка в generate_pitch: {str(e)}")
            await update.message.reply_text(f"⚠️ Ошибка при генерации аргументации: {str(e)}")
            raise

    async def finalize_session(self, update: Update, session: dict, chat_id: int):
        """Завершение сессии и сохранение результатов"""
        try:
            data = session["data"]
            
            # Сохранение данных сессии в базу
            await self.db.save_session_data(
                user_id=chat_id,
                step=session["step"],
                data=data,
                tokens_used=session["total_tokens"],
                total_cost=session["total_tokens"] * 0.000002
            )

            # Создание итогового файла
            safe_company_name = re.sub(r'[\\/*?:"<>|]', '_', data.get('client_company_name', 'company'))
            date_str = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"value_link_{safe_company_name}_{date_str}.txt"
            filepath = Path("user_data") / filename

            # Подготовка содержимого файла
            content = self._prepare_session_file_content(data, session)
            
            # Сохранение файла
            try:
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(content)
            except IOError as e:
                logger.error(f"Ошибка записи файла {filepath}: {str(e)}")
                raise

            # Отправка статистики
            stats = await self.db.get_user_stats(chat_id)
            stats_message = (
                f"📊 Статистика использования:\n"
                f"• Запросов сегодня: {stats['daily_requests']}/{MAX_REQUESTS_PER_DAY}\n"
                f"• Всего запросов: {stats['total_requests']}/{MAX_REQUESTS_PER_USER}\n"
                f"• Использовано токенов: {stats['total_tokens']}"
            )
            await update.message.reply_text(stats_message)

            # Финальное сообщение
            await update.message.reply_text(
                "✅ Всё готово! Если хочешь пройти ещё раз, напиши /start.\n\n"
                "📌 Больше полезных инструментов — в нашем Telegram:\n"
                "https://t.me/SkillsForSalescom"
            )

            # Отправка файла пользователю с увеличенным таймаутом
            file_sent = False
            max_retries = 3
            retry_count = 0
            
            while not file_sent and retry_count < max_retries:
                try:
                    await update.message.reply_document(
                        document=open(filepath, "rb"),
                        read_timeout=30,
                        write_timeout=30,
                        connect_timeout=30,
                        pool_timeout=30
                    )
                    file_sent = True
                except Exception as e:
                    retry_count += 1
                    if retry_count == max_retries:
                        logger.error(f"Ошибка при отправке файла: {str(e)}")
                        await update.message.reply_text("⚠️ Не удалось отправить файл с результатами")
                    else:
                        await asyncio.sleep(2)  # Пауза перед повторной попыткой

            # Очистка сессии
            del self.user_sessions[chat_id]
            logger.info(f"Сессия пользователя {chat_id} завершена")

        except Exception as e:
            logger.error(f"Ошибка в finalize_session: {str(e)}")
            await update.message.reply_text("⚠️ Ошибка при сохранении результатов. Данные могут быть неполными.")
            raise

    def _prepare_session_file_content(self, data: dict, session: dict) -> str:
        """Подготовка содержимого итогового файла сессии"""
        fields_order = [
            ("purchcenter_result", "📄 Гипотеза о структуре закупочного центра"),
            ("avatar_result", f"📄 Аватар — {data.get('chosen_position', 'должность')}"),
            ("product_model", "📄 Трёхуровневая модель продукта"),
            ("value_links", "📄 Ценностные связки"),
            ("pitch", "📄 Рациональная аргументация")
        ]

        content = [
            f"🧑 Имя пользователя: {data.get('user_name', 'не указано')}",
            f"🗓 Дата: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"🏢 Компания клиента: {data.get('client_company_name', 'не указана')}",
            f"🌐 Сайт клиента: {data.get('client_company_site', 'не указан')}",
            "\n" + "=" * 60 + "\n"
        ]

        for field, title in fields_order:
            content.extend([
                "=" * 60,
                title,
                "=" * 60,
                data.get(field, "[Данные отсутствуют]"),
                "\n"
            ])

        content.extend([
            "=" * 60,
            f"📊 Использовано токенов: {session['total_tokens']}",
            f"  ├ Входные: {session.get('total_input_tokens', 0)}",
            f"  └ Выходные: {session.get('total_output_tokens', 0)}",
            "=" * 60,
            "Контакты:",
            "WhatsApp: https://wa.me/+79277010202",
            "Telegram: https://t.me/Aleksey_Yusov",
            "Сайт: https://skillsforsales.ru",
            "=" * 60
        ])

        return "\n".join(content)

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Основной обработчик сообщений"""
        try:
            chat_id = update.effective_chat.id
            user = update.effective_user
            
            # Проверка инициализации сессии
            if chat_id not in self.user_sessions:
                await update.message.reply_text("Пожалуйста, начните с команды /start")
                return

            # Проверка лимитов перед любой обработкой
            daily_ok, total_ok = await self.db.check_rate_limit(chat_id)
            
            if not total_ok:
                await update.message.reply_text(
                    f"⚠️ Вы превысили Ваш лимит в {MAX_REQUESTS_PER_USER} запросов.\n"
                    f"Для получения дополнительной информации перейдите, пожалуйста, в канал:\n"
                    f"https://t.me/SkillsForSalescom"
                )
                return
                
            if not daily_ok:
                await update.message.reply_text(
                    f"⚠️ Вы превысили Ваш дневной лимит в {MAX_REQUESTS_PER_DAY} запроса. "
                    f"Попробуйте, пожалуйста, завтра!"
                )
                return

            session = self.user_sessions[chat_id]
            step = session["step"]

            # Обработка по шагам
            if step <= 3:
                await self.handle_initial_steps(update, session, chat_id)
            elif step == 4:
                await self.handle_avatar_step(update, session, chat_id)
            elif 5 <= step <= 8:
                await self.handle_company_info_steps(update, session, chat_id)
            else:
                await update.message.reply_text("Неизвестный шаг. Пожалуйста, используйте /reset")
                logger.warning(f"Неизвестный шаг {step} для пользователя {chat_id}")

        except Exception as e:
            logger.error(f"Критическая ошибка в handle_message: {str(e)}", exc_info=True)
            await update.message.reply_text(
                "⚠️ Произошла критическая ошибка. Пожалуйста, попробуйте позже или обратитесь к администратору.")


    async def shutdown(self):
        """Корректное завершение работы"""
        if hasattr(self, 'db'):
            await self.db.close()
        self.user_sessions.clear()
        logger.info("Бот завершает работу")

if __name__ == "__main__":
    try:
        logger.info("Запуск бота...")
        bot_handler = BotHandler()
        
        app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
        app.add_handler(CommandHandler("start", bot_handler.start))
        app.add_handler(CommandHandler("reset", bot_handler.reset))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot_handler.handle_message))

        logger.info("Бот успешно запущен")
        print("🤖 Бот запущен и готов к работе...")
        
        # Запуск с обработкой сигналов
        app.run_polling(
            stop_signals=[signal.SIGINT, signal.SIGTERM],
            close_loop=False
        )
        
    except Exception as e:
        logger.critical(f"Фатальная ошибка при запуске бота: {str(e)}", exc_info=True)
        asyncio.run(bot_handler.shutdown())
        raise