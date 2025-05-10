import openai
import time
from openai import RateLimitError, APIError, OpenAIError
from utils.mylogger import Logger

logger = Logger('LLM_OPENAI', 'llmcall.log')

class OpenAIClient:
    def __init__(self, model_name: str, api_key: str, base_url: str):
        self.client = openai.OpenAI(
            base_url=base_url,
            api_key=api_key,
            default_headers={
                "HTTP-Referer": "http://86.110.194.28",
                "X-Title": "Sales Bot"
            }
        )
        self.model_name = model_name

    def generate(
        self,
        messages: list,
        max_retries: int = 3,
        delay: int = 600,
        temperature: float = 0.3,
        max_tokens: int = 2048,
        idop: int = 0
    ):
        """
        Вызывает OpenAI API с обработкой исключений.
        
        :param messages: Список сообщений в формате OpenAI
        :param max_retries: Максимальное количество попыток
        :param delay: Задержка между попытками (в секундах)
        :param temperature: Параметр температуры для генерации
        :param max_tokens: Максимальное количество токенов в ответе
        :return: Кортеж (ответ, prompt_tokens, completion_tokens) или None
        """
        retries = 0
        
        while retries < max_retries:
            try:
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature
                )
                logger.info("Request processed successfully")
                return (
                    response.choices[0].message.content,
                    response.usage.prompt_tokens,
                    response.usage.completion_tokens
                )
            
            except RateLimitError as e:
                logger.warning(f"Rate limit exceeded. Retrying in {delay} seconds...")
                retries += 1
                time.sleep(delay)
            
            except (APIError, OpenAIError) as e:
                logger.error(f"API Error: {e}")
                return ("⚠️ Извините, у нас возникли проблемы со связью. Мы уже работаем над их устранением.", 0, 0)
            
            except Exception as e:
                logger.error(f"Unexpected Error: {e}")
                return ("⚠️ Извините, произошла непредвиденная ошибка. Пожалуйста, попробуйте позже.", 0, 0)
        
        logger.warning("Max retries reached. Failed to get response.")
        return ("⚠️ Извините, сервис временно недоступен. Пожалуйста, попробуйте позже.", 0, 0)

    @staticmethod
    def prepare_messages(prompt: str, system_message: str = "") -> list:
        """
        Формирует список сообщений для OpenAI API.
        
        :param prompt: Пользовательский промпт
        :param system_message: Системное сообщение (опционально)
        :return: Список сообщений в формате OpenAI
        """
        messages = []
        if system_message:
            messages.append({"role": "system", "content": system_message})
        messages.append({"role": "user", "content": prompt})
        return messages