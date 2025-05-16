import asyncio
from openai import RateLimitError, APIError, OpenAIError, AsyncOpenAI
from utils.mylogger import Logger

logger = Logger('LLM_OPENAI', 'llmcall.log')

class AsyncOpenAIClient:
    def __init__(self, model_name: str, api_key: str, base_url: str):
        self.client = AsyncOpenAI(
            base_url=base_url,
            api_key=api_key,
            default_headers={
                "HTTP-Referer": "http://86.110.194.28",
                "X-Title": "Sales Bot",
                "User-Agent": "Sales Bot/1.0.0",
                "Authorization": f"Bearer {api_key}",
                "X-Custom-Auth": api_key
            }
        )
        self.model_name = model_name

    async def generate(
        self,
        messages: list,
        max_retries: int = 3,
        delay: int = 600,
        temperature: float = 0.3,
        max_tokens: int = 2048,
        idop: int = 0
    ):
        """
        Асинхронно вызывает OpenAI API с обработкой исключений.
        
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
                response = await self.client.chat.completions.create(
                    model=self.model_name,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature
                )
                logger.info("Request processed successfully")
                logger.info(f"Response type: {type(response)}")
                logger.info(f"Response content: {response}")
                
                # Проверяем наличие ошибок в ответе
                if hasattr(response, 'error'):
                    error = response.error
                    logger.error(f"API returned error: {error}")
                    if isinstance(error, dict) and 'message' in error:
                        return (f"⚠️ Ошибка API: {error['message']}", 0, 0)
                    return ("⚠️ Произошла ошибка при обращении к API", 0, 0)

                # Проверяем наличие необходимых полей в ответе
                if not response:
                    logger.error("Response is None")
                    return ("⚠️ Получен пустой ответ от сервера. Пожалуйста, попробуйте позже.", 0, 0)

                if not hasattr(response, 'choices'):
                    logger.error(f"No 'choices' in response. Available attributes: {dir(response)}")
                    return ("⚠️ Некорректный формат ответа от сервера. Пожалуйста, попробуйте позже.", 0, 0)

                if not response.choices:
                    logger.error("Empty choices list in response")
                    return ("⚠️ Пустой список выборов в ответе. Пожалуйста, попробуйте позже.", 0, 0)

                # Получаем текст ответа
                first_choice = response.choices[0]
                logger.info(f"First choice type: {type(first_choice)}")
                logger.info(f"First choice content: {first_choice}")
                
                if not hasattr(first_choice, 'message'):
                    logger.error(f"No 'message' in first choice. Available attributes: {dir(first_choice)}")
                    return ("⚠️ Некорректный формат ответа. Пожалуйста, попробуйте позже.", 0, 0)

                message = first_choice.message
                logger.info(f"Message type: {type(message)}")
                logger.info(f"Message content: {message}")
                
                content = message.content if hasattr(message, 'content') else None
                
                # Получаем токены
                prompt_tokens = completion_tokens = 0
                if hasattr(response, 'usage'):
                    usage = response.usage
                    logger.info(f"Usage type: {type(usage)}")
                    logger.info(f"Usage content: {usage}")
                    prompt_tokens = usage.prompt_tokens if hasattr(usage, 'prompt_tokens') else 0
                    completion_tokens = usage.completion_tokens if hasattr(usage, 'completion_tokens') else 0

                if not content:
                    logger.error("No content in response")
                    return ("⚠️ Не удалось получить ответ. Пожалуйста, попробуйте позже.", 0, 0)

                logger.info(f"Final content: {content}")
                logger.info(f"Tokens: prompt={prompt_tokens}, completion={completion_tokens}")
                return content, prompt_tokens, completion_tokens
            
            except RateLimitError as e:
                logger.warning(f"Rate limit exceeded. Retrying in {delay} seconds...")
                retries += 1
                await asyncio.sleep(delay)
            
            except (APIError, OpenAIError) as e:
                logger.error(f"API Error: {e}")
                return ("⚠️ Извините, у нас возникли проблемы со связью. Мы уже работаем над их устранением.", 0, 0)
            
            except Exception as e:
                logger.error(f"Unexpected Error: {e}")
                logger.error(f"Error type: {type(e)}")
                logger.error(f"Error details: {str(e)}")
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