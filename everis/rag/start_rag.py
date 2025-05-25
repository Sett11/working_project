import asyncio
import nest_asyncio
from typing import List
from src.rag import AdvancedRAG
from src.handle_dir_and_files.load_documents import LoadDocuments
from src.handle_dir_and_files.process_documents import ProcessDocuments
from utils.mylogger import Logger
from config import Config_LLM, docs_dir

nest_asyncio.apply()

# Инициализация логгера для отслеживания работы приложения
logger = Logger('Start RAG', 'logs/rag.log')

def create_LLM(llm, config):
    """
    Создает и настраивает экземпляр класса AdvancedRAG.

    Процесс создания:
    1. Получение конфигурации из config
    2. Инициализация AdvancedRAG с параметрами из конфигурации
    3. Возврат готового экземпляра

    Args:
        llm: Класс AdvancedRAG для создания экземпляра
        config: Объект конфигурации с параметрами для LLM
            - model_name: название модели
            - api_key: ключ API
            - base_url: базовый URL
            - temperature: температура генерации

    Returns:
        AdvancedRAG: Настроенный экземпляр класса AdvancedRAG
    """
    conf = config
    LLM = llm(
        conf.model_name,
        conf.api_key,
        conf.base_url,
        conf.temperature
    )
    return LLM

async def setting_up_LLM(llm, documents: List[str]):
    """
    Асинхронно настраивает LLM для работы с документами.

    Процесс настройки:
    1. Асинхронная загрузка документов из указанных путей
    2. Асинхронная обработка документов (разбивка на чанки)
    3. Создание векторного хранилища
    4. Настройка ретриверов
    5. Настройка промптов

    Args:
        llm: Экземпляр класса AdvancedRAG
        documents: Список путей к документам для обработки
            Поддерживаемые форматы: PDF, TXT, DOCX

    Returns:
        AdvancedRAG: Настроенный экземпляр с загруженными документами
    """
    # Асинхронная загрузка документов
    loaded_documents = await LoadDocuments(documents).load_documents_async()
    # Асинхронная обработка документов
    processed_documents = await ProcessDocuments(loaded_documents).process_documents_async()
    # Создание векторного хранилища для быстрого поиска
    llm.vectorstore.create_vector_store(processed_documents)
    # Настройка компонентов для поиска документов
    llm.retriever.setup_retrievers()
    # Настройка промптов для генерации ответов
    llm.promts.setup_prompts()
    return llm

async def process_question(llm: AdvancedRAG, question: str) -> str:
    """
    Асинхронно обрабатывает вопрос пользователя.
    """
    try:
        response = await llm.query_async(question)
        return response
    except Exception as e:
        logger.error(f"Ошибка при обработке вопроса: {str(e)}")
        return f"Произошла ошибка: {str(e)}"

async def main(docs_dir: str):
    """
    Асинхронная основная функция приложения.
    
    Процесс работы:
    1. Создание экземпляра AdvancedRAG
    2. Проверка наличия директории с документами
    3. Настройка путей к документам
    4. Инициализация LLM с документами
    5. Цикл обработки вопросов пользователя
    6. Извлечение и вывод точных ответов
    """
    try:
        # Создание и настройка LLM
        llm = create_LLM(AdvancedRAG, Config_LLM)
        
        # Асинхронная настройка LLM для работы с документами
        llm = await setting_up_LLM(llm, [docs_dir])
        
        while True:
            # Получение вопроса от пользователя
            question = input("Введите ваш вопрос (или 'exit' для выхода): ")
            
            if question.lower() == "exit":
                break
                
            # Асинхронная обработка вопроса
            response = await process_question(llm, question)
            
            # Выводим ответ
            print("\nОтвет:")
            print("-" * 50)
            print(response)
            print("-" * 50)
        
    except Exception as e:
        logger.error(f"Произошла ошибка: {str(e)}")
        print(f"Произошла ошибка: {str(e)}")

if __name__ == "__main__":
    logger.info("Запуск приложения")
    asyncio.run(main(docs_dir))