import re
from typing import Dict, List, Tuple, Optional, Union, Any, cast
from utils.mylogger import Logger
from date.components import components

logger = Logger("everis", "everis.log")

class VentilationSystemOptimizer:
    def __init__(self, components_data: Dict[str, Tuple[str, str, Optional[str], Optional[float], Optional[str]]]):
        """
        Класс для оптимизации подбора комплектующих вентиляционной системы.

        Основная задача - на основе требуемых параметров (длина/количество, тип компонента, фильтр по сечению)
        подобрать из каталога `components_data` оптимальный набор комплектующих по минимальной стоимости.
        Если точный подбор невозможен, предлагаются варианты для ближайших меньших/больших размеров сечения.

        :param components_data: Словарь комплектующих
                                Формат: {"название": ("размер_строка", "материал", "характеристики", цена, "стандарт")}
        """
        self.components: Dict[str, Tuple[str, str, Optional[str], Optional[float], Optional[str]]] = components_data
        # Результаты последнего успешного основного подбора
        self.selected_components: Dict[str, int] = {} 
        self.total_cost: float = 0.0
        self.total_accumulated_value: int = 0 
        # Тип компонента из последнего основного запроса (для generate_bill_of_materials)
        self._last_component_type_request: str = "" 

        # Списки для классификации компонентов по их названию или типу запроса
        self.fittings: List[str] = [
            "поворот", "отвод", "тройник", "переход", "зонт", "дефлектор", 
            "решетка", "клапан", "фильтр", "вентилятор", "глушитель", "насадок", "врезка",
            "ниппель", "муфта", "заглушка" # Добавлено из components.py
        ]
        self.duct_types: List[str] = ["воздуховод", "канал", "труба гибкая"]
        # self.material_types: List[str] = ["сталь", "маты", "шпилька", "анкер", "гайка", "профиль", "скоба", "шайба"] # Менее используется в текущей логике

        logger.info(f"Инициализирован VentilationSystemOptimizer с {len(self.components)} компонентами из каталога.")

    def _is_item_duct_like(self, item_name: str, component_type_request: str) -> bool:
        """
        Определяет, является ли компонент длинномерным (типа "воздуховод")
        на основе его имени или типа запрошенного компонента.

        :param item_name: Имя компонента из каталога.
        :param component_type_request: Запрошенный тип компонента.
        :return: True, если компонент похож на длинномерный, иначе False.
        """
        name_lower = item_name.lower()
        type_req_lower = component_type_request.lower()
        # Если тип запроса явно указывает на воздуховод
        if any(keyword in type_req_lower for keyword in self.duct_types):
            return True
        # Если имя компонента содержит ключевые слова для воздуховодов
        # и не содержит ключевых слов для фитингов (чтобы избежать ложных срабатываний для, например, "переход для воздуховода")
        if any(keyword in name_lower for keyword in self.duct_types) and \
           not any(fit_kw in name_lower for fit_kw in self.fittings):
            return True
        return False

    def _is_item_fitting_like(self, item_name: str, component_type_request: str) -> bool:
        """
        Определяет, является ли компонент штучным изделием (фитингом)
        на основе его имени или типа запрошенного компонента.

        :param item_name: Имя компонента из каталога.
        :param component_type_request: Запрошенный тип компонента.
        :return: True, если компонент похож на фитинг, иначе False.
        """
        name_lower = item_name.lower()
        type_req_lower = component_type_request.lower()
        # Если тип запроса явно указывает на фитинг
        if any(keyword in type_req_lower for keyword in self.fittings):
            return True
        # Если имя компонента содержит ключевые слова для фитингов
        if any(keyword in name_lower for keyword in self.fittings):
            return True
        return False

    def _parse_item_unit_value_and_price_logic(self, item_name: str, characteristics_str: Optional[str], 
                                               item_cost_raw: Optional[float], component_type_request: str) \
                                               -> Tuple[int, float]:
        """
        Определяет единичное значение (стандартная длина или 1 для штучных) и стоимость за эту единицу.

        Логика:
        1. Если в характеристиках есть "L=XXXXмм", это стандартная длина `unit_value = XXXX`, цена - за этот отрезок.
        2. Если компонент - воздуховод (по типу/имени) и нет "L=", цена считается за 1 метр (1000мм), `unit_value = 1000`.
        3. Если компонент - фитинг или другой (не воздуховод), `unit_value = 1` (штука), цена - за штуку.

        :param item_name: Имя компонента.
        :param characteristics_str: Строка характеристик из каталога.
        :param item_cost_raw: "Сырая" цена из каталога.
        :param component_type_request: Запрошенный тип компонента.
        :return: Кортеж (unit_value, cost_per_unit_value).
                 unit_value: стандартная длина/количество для алгоритма ДП.
                 cost_per_unit_value: цена за этот unit_value.
        """
        unit_value = 0
        cost_per_unit_value = 0.0
        cost_raw = item_cost_raw if item_cost_raw is not None else 0.0

        is_duct = self._is_item_duct_like(item_name, component_type_request)
        is_fitting = self._is_item_fitting_like(item_name, component_type_request)

        # Пытаемся извлечь явную длину из характеристик
        if characteristics_str: 
            match_L = re.search(r"L=(\d+)\s*мм", characteristics_str, re.IGNORECASE)
            if match_L:
                unit_value = int(match_L.group(1))
                cost_per_unit_value = cost_raw # Цена в каталоге - за этот конкретный отрезок
                logger.debug(f"Для '{item_name}': извлечена стандартная длина L={unit_value}мм из характеристик, цена за отрезок {cost_per_unit_value}.")
                return unit_value, cost_per_unit_value

        # Если явная длина L= не найдена
        if is_duct:
            # Для воздуховодов без явной L=, предполагаем, что цена в каталоге указана за 1 метр (1000 мм)
            unit_value = 1000 # мм (1 метр) - базовая единица для набора длины
            cost_per_unit_value = cost_raw # Цена из каталога считается ценой за 1 метр
            logger.debug(f"Для воздуховода '{item_name}' без явной L=: предполагается unit_value={unit_value}мм (цена за 1м), цена {cost_per_unit_value}.")
        elif is_fitting:
            # Для фитингов (и других штучных товаров) unit_value = 1 (штука)
            unit_value = 1 # 1 штука
            cost_per_unit_value = cost_raw # Цена из каталога - за штуку
            logger.debug(f"Для фитинга/штучного товара '{item_name}': предполагается unit_value=1шт, цена {cost_per_unit_value}.")
        else: 
            # Для компонентов, не классифицированных как воздуховод или фитинг (например, оборудование, общие материалы)
            # Также считаем штучным товаром с условной единицей измерения
            unit_value = 1 # условная единица
            cost_per_unit_value = cost_raw # Цена из каталога - за эту условную единицу
            logger.debug(f"Для компонента '{item_name}' (не воздуховод/фитинг): предполагается unit_value=1 (усл.ед.), цена {cost_per_unit_value}.")
        
        return unit_value, cost_per_unit_value


    def parse_section_size(self, size_str: str) -> Optional[Union[Tuple[int, int], Tuple[str, int, int]]]:
        """
        Парсит строку с размерами сечения из каталога.

        Поддерживаемые форматы:
        - Прямоугольные: "500x800 мм" -> (500, 800)
        - Круглые: "ø450 мм" -> (450, 450)
        - Переходы (парсит первое сечение): "500x800 → ø630 мм" -> (500, 800)
        - Круглые диапазоны: "ø100-1250 мм" -> ('range_circle', 100, 1250)
        - Неразмерные характеристики (производительность, толщина) -> None

        :param size_str: Строка с размером из каталога.
        :return: Кортеж с размерами, кортеж-описатель диапазона или None.
        """
        if not isinstance(size_str, str):
            logger.warning(f"parse_section_size получил не строку: {size_str}. Возвращен None.")
            return None

        size_str_lower = size_str.lower().strip() # Убираем лишние пробелы

        # 1. Прямоугольные: "WxH мм"
        match_rect = re.fullmatch(r"(\d+)\s*x\s*(\d+)\s*мм", size_str_lower) # fullmatch для точности
        if match_rect:
            dims = (int(match_rect.group(1)), int(match_rect.group(2)))
            logger.debug(f"Парсинг сечения (прямоугольное): '{size_str}' -> {dims}")
            return dims

        # 2. Круглые: "øD мм"
        match_circle = re.fullmatch(r"ø(\d+)\s*мм", size_str_lower)
        if match_circle:
            diameter = int(match_circle.group(1))
            dims = (diameter, diameter) # Представляем как (D,D) для единообразия
            logger.debug(f"Парсинг сечения (круглое): '{size_str}' -> {dims}")
            return dims
        
        # 3. Переходы (пытаемся извлечь первое сечение для фильтрации)
        # Пример: "500x800 → ø630 мм", "ø100 → 50х50 мм"
        match_transition_arrow = re.match(r"(.+?)\s*→\s*(.+?)(?:\s*мм)?$", size_str) # (?:\s*мм)? делает "мм" в конце опциональным
        if match_transition_arrow:
            first_part_str = match_transition_arrow.group(1).strip()
            # Добавляем " мм", если его нет, для рекурсивного вызова parse_section_size
            if not first_part_str.endswith("мм"):
                first_part_str += " мм"
            
            parsed_first_part = self.parse_section_size(first_part_str) 
            if parsed_first_part and not (isinstance(parsed_first_part[0], str) and parsed_first_part[0].startswith('range_')): 
                logger.debug(f"Парсинг сечения (переход): '{size_str}' -> первое сечение {parsed_first_part} для фильтрации.")
                return cast(Tuple[int,int], parsed_first_part) # Возвращаем размеры первого сечения перехода
            else: 
                 logger.debug(f"Парсинг сечения (переход): '{size_str}' -> первая часть '{first_part_str}' не дала конкретного сечения или является диапазоном.")


        # 4. Круглые диапазоны: "øD1-D2 мм"
        match_range_circle = re.fullmatch(r"ø(\d+)\s*-\s*(\d+)\s*мм", size_str_lower)
        if match_range_circle:
            min_d, max_d = int(match_range_circle.group(1)), int(match_range_circle.group(2))
            dims = ('range_circle', min_d, max_d)
            logger.debug(f"Парсинг сечения (диапазон круглый): '{size_str}' -> {dims}")
            return dims
            
        # 5. Игнорирование строк, описывающих не сечения для воздуховодов/фитингов
        #    (например, производительность оборудования, толщина материала)
        if "м3/ч" in size_str_lower or \
           (re.fullmatch(r"\d+(?:\.\d+)?\s*мм", size_str_lower) and \
            'x' not in size_str_lower and 'ø' not in size_str_lower and '-' not in size_str_lower): 
             logger.debug(f"Строка '{size_str}' не является размером сечения для воздуховода/фитинга (похоже на производительность, толщину и т.п.). Игнорируется.")
             return None

        logger.info(f"Строка '{size_str}' не была распознана как известный формат размера сечения или диапазона. Возвращен None.")
        return None
    
    def _validate_input(
        self,
        required_value: int,
        section_filter_dim: Optional[int], # Основной фильтр по одному из размеров сечения
        component_type: str,
        exact_target_section_pair: Optional[Tuple[int, int]] = None # Для точного подбора по паре WxH
    ) -> bool:
        """
        Валидирует основные входные параметры для методов подбора.

        :param required_value: Требуемая длина (мм) или количество (шт).
        :param section_filter_dim: Опциональный основной фильтр по одному из размеров сечения (мм).
        :param component_type: Запрашиваемый тип компонента.
        :param exact_target_section_pair: Опциональная точная пара размеров сечения (W,H) для подбора.
        :raises ValueError: Если какой-либо из параметров невалиден.
        :return: True, если все валидно.
        """
        logger.debug(f"Валидация входа: req_val={required_value}, sec_filter={section_filter_dim}, type={component_type}, exact_pair={exact_target_section_pair}")
        if not isinstance(required_value, int) or required_value <= 0:
            msg = "Требуемое значение (длина/количество) должно быть положительным целым числом."
            logger.error(msg)
            raise ValueError(msg)
        
        if section_filter_dim is not None:
            if not isinstance(section_filter_dim, int) or section_filter_dim <= 0:
                msg = "Фильтр по размеру сечения (section_filter_dim) должен быть положительным целым числом, если указан."
                logger.error(msg)
                raise ValueError(msg)
        
        if exact_target_section_pair is not None:
            if not (isinstance(exact_target_section_pair, tuple) and len(exact_target_section_pair) == 2 and
                    all(isinstance(d, int) and d > 0 for d in exact_target_section_pair)):
                msg = "Точная пара размеров сечения (exact_target_section_pair) должна быть кортежем из двух положительных целых чисел."
                logger.error(msg)
                raise ValueError(msg)

        if not component_type or not isinstance(component_type, str):
            msg = "Тип компонента должен быть непустой строкой."
            logger.error(msg)
            raise ValueError(msg)

        logger.info(f"Входные данные для оптимизации валидны.")
        return True

    def _filter_components(
        self,
        component_type_request: str,
        section_filter_dim: Optional[int] = None, # Основной фильтр по одному из размеров сечения
        exact_target_section_pair: Optional[Tuple[int, int]] = None # Если задано, ищем точное совпадение сечения (W,H)
    ) -> List[Dict[str, Any]]:
        """
        Фильтрует компоненты из каталога по типу и критериям размера сечения.

        Логика фильтрации по сечению:
        1. Если `exact_target_section_pair` (например, (W,H)) задан:
           - Ищет компоненты, чье сечение точно соответствует (W,H) или (H,W). Диапазоны не используются.
        2. Если `exact_target_section_pair` НЕ задан, но `section_filter_dim` (например, D или одна из сторон W/H) задан:
           - Для компонентов с конкретным сечением: проверяет, равен ли один из размеров сечения `section_filter_dim`.
           - Для компонентов с диапазоном сечений: проверяет, входит ли `section_filter_dim` в диапазон.
             Если входит, эффективным сечением для этого компонента считается (D,D) где D=`section_filter_dim`.
        3. Если ни `exact_target_section_pair`, ни `section_filter_dim` не заданы:
           - Фильтрация по сечению не производится, но компонент должен соответствовать `component_type_request`.

        :param component_type_request: Запрашиваемый тип компонента (ключевое слово).
        :param section_filter_dim: Опциональный основной фильтр по одному из размеров сечения.
        :param exact_target_section_pair: Опциональная точная пара размеров (W,H) для поиска.
        :return: Список словарей подходящих компонентов. Каждый словарь содержит ключи:
                 "name", "catalog_section_info", "effective_section_size", "unit_value", "cost_per_unit_value".
        """
        logger.debug(f"Фильтрация компонентов: тип_запроса='{component_type_request}', осн_фильтр_сеч={section_filter_dim}, точное_сеч_пара={exact_target_section_pair}")
        filtered_items: List[Dict[str, Any]] = []
        type_req_lower = component_type_request.lower().strip()

        for name, data in self.components.items():
            size_str, material, characteristics_str, cost_val, standard_str = data
            name_lower = name.lower()
            
            # --- Начало фильтрации по типу компонента ---
            # Пытаемся определить тип запрашиваемого компонента (воздуховод/фитинг)
            request_is_duct_type = self._is_item_duct_like("", component_type_request)
            request_is_fitting_type = self._is_item_fitting_like("", component_type_request)

            # Пытаемся определить тип текущего компонента из каталога по его имени
            item_from_catalog_is_duct_by_name = self._is_item_duct_like(name, "")
            item_from_catalog_is_fitting_by_name = self._is_item_fitting_like(name, "")

            # Если запрос на воздуховод, а текущий компонент по имени - фитинг, пропускаем
            if request_is_duct_type and item_from_catalog_is_fitting_by_name:
                logger.debug(f"Фильтр (тип): '{name}' (фитинг по имени) не соответствует запросу на воздуховод '{component_type_request}'. Пропуск.")
                continue
            # Если запрос на фитинг, а текущий компонент по имени - воздуховод, пропускаем
            if request_is_fitting_type and item_from_catalog_is_duct_by_name:
                 logger.debug(f"Фильтр (тип): '{name}' (воздуховод по имени) не соответствует запросу на фитинг '{component_type_request}'. Пропуск.")
                 continue
            
            # Если ищем конкретный тип фитинга (например, "отвод", "клапан"), он должен присутствовать в имени компонента
            # или в самом component_type_request, если он совпадает с частью имени (например, запрос "РЕГУЛЯР" для клапана "Клапан ... РЕГУЛЯР...")
            is_specific_fitting_keyword_in_request = any(ft == type_req_lower for ft in self.fittings)
            if is_specific_fitting_keyword_in_request and type_req_lower not in name_lower:
                 logger.debug(f"Фильтр (тип): '{name}' не содержит ключ конкретного фитинга '{component_type_request}' в имени. Пропуск.")
                 continue
            # Если component_type_request содержит общее имя компонента (например "воздуховод d450"),
            # дополнительно проверяем, чтобы это общее имя было в имени компонента из каталога
            if type_req_lower not in name_lower and not (request_is_duct_type or request_is_fitting_type):
                 # Эта проверка полезна, если component_type_request - это что-то вроде "фильтровентиляционный агрегат"
                 # и мы хотим найти именно его, а не просто любой "агрегат".
                 # Если же component_type_request это "воздуховод" или "отвод", то эта проверка может быть излишней,
                 # так как предыдущие проверки по self.duct_types и self.fittings уже отработали.
                 # Оставляем для случаев, когда component_type_request - это полное или частичное имя конкретного изделия.
                 if component_type_request not in name: # Проверяем на оригинальное имя, если type_req_lower - это специфичное название
                     logger.debug(f"Фильтр (тип): Имя компонента '{name}' не содержит строку запроса '{component_type_request}'. Пропуск.")
                     continue


            # --- Конец фильтрации по типу компонента ---

            parsed_catalog_section = self.parse_section_size(size_str)
            effective_section_for_item: Optional[Tuple[int,int]] = None # Сечение, которое будет использовано для ДП
            passes_section_filter = False

            if exact_target_section_pair:
                # Режим поиска точного сечения (W,H)
                if parsed_catalog_section and isinstance(parsed_catalog_section, tuple) and \
                   len(parsed_catalog_section) == 2 and all(isinstance(d, int) for d in parsed_catalog_section):
                    # Каталожный компонент имеет конкретное сечение (s1, s2)
                    s1, s2 = cast(Tuple[int,int], parsed_catalog_section)
                    t1, t2 = exact_target_section_pair
                    if (s1 == t1 and s2 == t2) or (s1 == t2 and s2 == t1):
                        effective_section_for_item = (t1, t2) # Используем целевое сечение
                        passes_section_filter = True
                        logger.debug(f"Фильтр (точное сечение): '{name}' с сечением {parsed_catalog_section} соответствует точному запросу {exact_target_section_pair}.")
                else:
                    logger.debug(f"Фильтр (точное сечение): '{name}' с размером '{size_str}' не имеет конкретного парного сечения для сравнения с {exact_target_section_pair}. Пропуск.")
            
            elif section_filter_dim is not None:
                # Режим фильтрации по одному размеру (section_filter_dim)
                if parsed_catalog_section is None:
                    logger.debug(f"Фильтр (осн.фильтр): '{name}' ({size_str}) не имеет парсуемого сечения. Фильтр {section_filter_dim} не применим. Пропуск.")
                elif isinstance(parsed_catalog_section, tuple) and len(parsed_catalog_section) > 0 and \
                     isinstance(parsed_catalog_section[0], str) and parsed_catalog_section[0].startswith('range_'):
                    # Обработка диапазона из каталога
                    range_type, min_val, max_val = parsed_catalog_section
                    if range_type == 'range_circle' and min_val <= section_filter_dim <= max_val:
                        effective_section_for_item = (section_filter_dim, section_filter_dim) # Используем запрошенный dim как D
                        passes_section_filter = True
                        logger.debug(f"Фильтр (осн.фильтр): '{name}' с диапазоном {parsed_catalog_section} включает {section_filter_dim}. Эффективное сечение: {effective_section_for_item}.")
                    # TODO: Добавить обработку прямоугольных диапазонов, если они появятся
                elif isinstance(parsed_catalog_section, tuple) and len(parsed_catalog_section) == 2 and \
                     all(isinstance(d, int) for d in parsed_catalog_section):
                    # Конкретное сечение из каталога
                    s1, s2 = cast(Tuple[int,int], parsed_catalog_section)
                    if s1 == section_filter_dim or s2 == section_filter_dim:
                        effective_section_for_item = (s1, s2) # Используем фактическое сечение компонента
                        passes_section_filter = True
                        logger.debug(f"Фильтр (осн.фильтр): '{name}' с сечением {parsed_catalog_section} содержит {section_filter_dim}. Эффективное сечение: {effective_section_for_item}.")
                else: # Не диапазон и не конкретная пара (int,int), но section_filter_dim задан
                     logger.debug(f"Фильтр (осн.фильтр): '{name}' с {parsed_catalog_section} не прошел проверку по {section_filter_dim}. Пропуск.")
            
            else: # Ни exact_target_section_pair, ни section_filter_dim не заданы
                passes_section_filter = True # Фильтрация по сечению не требуется
                if parsed_catalog_section and isinstance(parsed_catalog_section, tuple) and \
                   len(parsed_catalog_section) == 2 and all(isinstance(d, int) for d in parsed_catalog_section):
                    effective_section_for_item = cast(Tuple[int,int], parsed_catalog_section) # Берем сечение из каталога, если оно конкретное
                logger.debug(f"Фильтр: Для '{name}' фильтрация по сечению не требовалась. Эффективное сечение (если есть): {effective_section_for_item}.")


            if not passes_section_filter:
                logger.debug(f"Фильтр: Компонент '{name}' не прошел фильтрацию по сечению. Пропуск.")
                continue
            
            # --- Получение единичного значения и цены ---
            unit_value, cost_per_unit = self._parse_item_unit_value_and_price_logic(
                name, characteristics_str, cost_val, component_type_request
            )

            if unit_value <= 0: # Защита от невалидной длины/штучности
                logger.warning(f"Фильтр: Компонент '{name}' имеет невалидное единичное значение {unit_value} после парсинга. Пропуск.")
                continue
            
            filtered_items.append({
                "name": name,
                "catalog_section_info": parsed_catalog_section, # Оригинальная информация о сечении из каталога
                "effective_section_size": effective_section_for_item, # Сечение, используемое для этого запроса
                "unit_value": unit_value,           # Длина стандартного отрезка / 1000мм для цены за м.п. / 1 для штучных
                "cost_per_unit_value": cost_per_unit # Цена за этот unit_value
            })
            logger.info(f"Фильтр: Компонент '{name}' прошел отбор. Эффективное сечение: {effective_section_for_item}, Ед.значение: {unit_value}, Цена за ед.: {cost_per_unit}")

        logger.info(f"Фильтрация завершена. Найдено {len(filtered_items)} подходящих компонентов для запроса (тип: '{component_type_request}', осн.фильтр: {section_filter_dim}, точное сеч: {exact_target_section_pair}).")
        return filtered_items

    def _get_unique_section_dimensions(self, component_type_filter: str) -> List[Tuple[int, int]]:
        """
        Извлекает УНИКАЛЬНЫЕ КОНКРЕТНЫЕ размеры сечений (W,H) или (D,D) из каталога,
        которые могут соответствовать `component_type_filter`.
        Используется для поиска ближайших альтернативных сечений.
        Диапазоны и неразмерные характеристики игнорируются.

        :param component_type_filter: Тип компонента для предварительной фильтрации (эвристика).
        :return: Отсортированный список уникальных кортежей (dim1, dim2).
        """
        logger.debug(f"Сбор уникальных конкретных сечений для типа '{component_type_filter}'...")
        section_dimensions_set: set[Tuple[int, int]] = set()
        for name, data in self.components.items():
            # Можно добавить предварительную фильтрацию по component_type_filter, если это ускорит
            # Например, если ищем для "воздуховод", не смотреть на "вентилятор"
            size_str = data[0]
            parsed_section = self.parse_section_size(size_str)
            # Добавляем только если это конкретное сечение (кортеж из двух int)
            if parsed_section and isinstance(parsed_section, tuple) and \
               len(parsed_section) == 2 and isinstance(parsed_section[0], int) and isinstance(parsed_section[1], int):
                section_dimensions_set.add(cast(Tuple[int, int], parsed_section))
        
        sorted_dimensions = sorted(list(section_dimensions_set))
        logger.info(f"Собрано {len(sorted_dimensions)} уникальных КОНКРЕТНЫХ размеров сечений из каталога.")
        return sorted_dimensions
    
    def find_nearest_smaller(self, target_L_section: int, target_W_section_nullable: Optional[int], component_type: str) -> Optional[Tuple[int, int]]:
        """
        Находит ближайший по площади меньший или равный КОНКРЕТНЫЙ размер сечения из каталога.

        :param target_L_section: Целевая первая размерность сечения (W или D).
        :param target_W_section_nullable: Целевая вторая размерность (H). None для круглых/квадратных (L=W).
        :param component_type: Тип компонента (для передачи в _get_unique_section_dimensions).
        :return: Кортеж (найденная_L, найденная_W) или None.
        """
        logger.info(f"Поиск ближайшего меньшего конкретного сечения: цель L_секции={target_L_section}, W_секции={target_W_section_nullable}, тип комп-та: {component_type}")
        available_section_dims = self._get_unique_section_dimensions(component_type) 

        best_match_section: Optional[Tuple[int, int]] = None
        max_area_found = -1.0 # Ищем максимальную площадь среди подходящих меньших

        for sL_cand, sW_cand in available_section_dims: # Кандидат из каталога (sL_cand, sW_cand)
            
            # Проверяем, подходит ли кандидат (или его повернутая версия) под целевые размеры
            # и при этом меньше или равен им.
            current_valid_orientation: Optional[Tuple[int,int]] = None

            # Ориентация 1: (sL_cand, sW_cand)
            if target_W_section_nullable is None: # Ищем круглый/квадратный
                if sL_cand == sW_cand and sL_cand <= target_L_section:
                    current_valid_orientation = (sL_cand, sW_cand)
            else: # Ищем прямоугольный
                if sL_cand <= target_L_section and sW_cand <= target_W_section_nullable:
                    current_valid_orientation = (sL_cand, sW_cand)
            
            # Ориентация 2 (для прямоугольных, если sL_cand != sW_cand): (sW_cand, sL_cand)
            if target_W_section_nullable is not None and sL_cand != sW_cand:
                if sW_cand <= target_L_section and sL_cand <= target_W_section_nullable:
                    # Если первая ориентация не подошла, или эта лучше (больше площадь)
                    if current_valid_orientation is None or (sW_cand * sL_cand > current_valid_orientation[0] * current_valid_orientation[1]):
                         current_valid_orientation = (sW_cand, sL_cand) # Сохраняем в порядке (соотв. target_L, соотв. target_W)


            if current_valid_orientation:
                chosen_sL, chosen_sW = current_valid_orientation
                current_area = float(chosen_sL * chosen_sW)
                if current_area > max_area_found:
                    max_area_found = current_area
                    best_match_section = (chosen_sL, chosen_sW)
                elif current_area == max_area_found and best_match_section is not None:
                    # Если площади равны, можно выбрать тот, у которого первая сторона ближе (но не больше)
                    if abs(target_L_section - chosen_sL) < abs(target_L_section - best_match_section[0]):
                         best_match_section = (chosen_sL, chosen_sW)
        
        if best_match_section:
            logger.info(f"Найден ближайший меньший конкретный размер сечения: {best_match_section}")
        else:
            logger.warning(f"Ближайший меньший конкретный размер сечения не найден для цели L={target_L_section}, W={target_W_section_nullable}.")
        return best_match_section

    def find_nearest_larger(self, target_L_section: int, target_W_section_nullable: Optional[int], component_type: str) -> Optional[Tuple[int, int]]:
        """
        Находит ближайший по площади больший или равный КОНКРЕТНЫЙ размер сечения из каталога.

        :param target_L_section: Целевая первая размерность сечения (W или D).
        :param target_W_section_nullable: Целевая вторая размерность (H). None для круглых/квадратных (L=W).
        :param component_type: Тип компонента.
        :return: Кортеж (найденная_L, найденная_W) или None.
        """
        logger.info(f"Поиск ближайшего большего конкретного сечения: цель L_секции={target_L_section}, W_секции={target_W_section_nullable}, тип комп-та: {component_type}")
        available_section_dims = self._get_unique_section_dimensions(component_type)

        best_match_section: Optional[Tuple[int, int]] = None
        min_area_found = float('inf') # Ищем минимальную площадь среди подходящих больших

        for sL_cand, sW_cand in available_section_dims:
            current_valid_orientation: Optional[Tuple[int,int]] = None

            # Ориентация 1: (sL_cand, sW_cand)
            if target_W_section_nullable is None: # Ищем круглый/квадратный
                if sL_cand == sW_cand and sL_cand >= target_L_section:
                    current_valid_orientation = (sL_cand, sW_cand)
            else: # Ищем прямоугольный
                if sL_cand >= target_L_section and sW_cand >= target_W_section_nullable:
                    current_valid_orientation = (sL_cand, sW_cand)
            
            # Ориентация 2 (для прямоугольных, если sL_cand != sW_cand): (sW_cand, sL_cand)
            if target_W_section_nullable is not None and sL_cand != sW_cand:
                if sW_cand >= target_L_section and sL_cand >= target_W_section_nullable:
                    if current_valid_orientation is None or (sW_cand * sL_cand < current_valid_orientation[0] * current_valid_orientation[1]):
                        current_valid_orientation = (sW_cand, sL_cand)

            if current_valid_orientation:
                chosen_sL, chosen_sW = current_valid_orientation
                current_area = float(chosen_sL * chosen_sW)
                if current_area < min_area_found:
                    min_area_found = current_area
                    best_match_section = (chosen_sL, chosen_sW)
                elif current_area == min_area_found and best_match_section is not None:
                    if abs(target_L_section - chosen_sL) < abs(target_L_section - best_match_section[0]):
                        best_match_section = (chosen_sL, chosen_sW)
        
        if best_match_section:
            logger.info(f"Найден ближайший больший конкретный размер сечения: {best_match_section}")
        else:
            logger.warning(f"Ближайший больший конкретный размер сечения не найден для цели L={target_L_section}, W={target_W_section_nullable}.")
        return best_match_section


    def find_optimal_components(
        self,
        required_value: int, 
        section_filter_dim: Optional[int] = None, 
        component_type: str = "воздуховод",
        _exact_target_section_pair_for_recursion: Optional[Tuple[int, int]] = None, # Внутренний параметр для рекурсии
        _recursion_level: int = 0 # Для предотвращения глубокой рекурсии
    ) -> Dict[str, Any]: # Возвращаемый тип изменен на Any для гибкости с альтернативами
        """
        Подбирает оптимальный набор комплектующих.
        Если точный подбор не удается, пытается найти решения для ближайших меньшего и большего размеров сечения.

        :param required_value: Требуемая общая длина (мм) для длинномерных или количество (шт) для штучных.
        :param section_filter_dim: Опциональный основной фильтр по одному из размеров сечения (мм).
                                   Используется при первоначальном вызове.
        :param component_type: Тип компонента ("воздуховод", "отвод", и т.д.).
        :param _exact_target_section_pair_for_recursion: Используется внутренне для рекурсивных вызовов
                                                        с точным альтернативным сечением.
        :param _recursion_level: Текущий уровень рекурсии.
        :return: Словарь с результатами. В случае неудачи основного подбора и успешных альтернативных,
                 возвращает структуру с ключами "alternative_smaller" и "alternative_larger".
        """
        
        if _recursion_level == 0: # Это основной вызов
            self._last_component_type_request = component_type 
            logger.info(f"Основной запрос на оптимизацию: значение={required_value}, осн.фильтр сечения={section_filter_dim}, тип='{component_type}'")
            # Валидация только для основного вызова, чтобы не дублировать для рекурсивных
            try:
                self._validate_input(required_value, section_filter_dim, component_type, _exact_target_section_pair_for_recursion)
            except ValueError as e:
                logger.error(f"Ошибка валидации входных данных при основном запросе: {e}")
                return {"components": {}, "total_cost": 0, "total_value": 0, "message": str(e)}
        else: # Это рекурсивный вызов
            logger.info(f"Рекурсивный запрос (уровень {_recursion_level}): значение={required_value}, точное сечение={_exact_target_section_pair_for_recursion}, тип='{component_type}'")

        # Сброс результатов для текущего уровня вызова (актуально для основного)
        if _recursion_level == 0:
            self.selected_components = {}
            self.total_cost = 0.0
            self.total_accumulated_value = 0
        
        # Фильтрация компонентов на основе текущих критериев (либо section_filter_dim, либо _exact_target_section_pair_for_recursion)
        suitable_components = self._filter_components(
            component_type,
            section_filter_dim if _recursion_level == 0 else None, # section_filter_dim только для основного вызова
            _exact_target_section_pair_for_recursion # exact_target_section_pair для рекурсивных (или если передан в основной)
        )
        
        # Если на текущем уровне (основном или рекурсивном) подходящих компонентов нет
        if not suitable_components:
            message_suffix = f"для точного сечения {_exact_target_section_pair_for_recursion}" if _exact_target_section_pair_for_recursion else \
                             f"с осн. фильтром сечения {section_filter_dim}"
            
            logger.warning(f"Подбор невозможен: не найдено подходящих компонентов в каталоге для типа '{component_type}' {message_suffix}.")
            
            # Если это основной вызов и нет компонентов, пытаемся найти альтернативы
            if _recursion_level == 0:
                logger.info("Основной подбор не удался (нет подходящих компонентов). Попытка найти альтернативные сечения...")
                return self._handle_alternative_section_search(required_value, section_filter_dim, component_type)
            else: # Если это рекурсивный вызов и нет компонентов - просто сообщаем о неудаче для этого уровня
                return {"components": {}, "total_cost": 0, "total_value": 0, "message": f"Подбор не удался: нет компонентов {message_suffix}."}

        # --- Алгоритм динамического программирования (ДП) ---
        # dp[i] будет хранить минимальную стоимость для достижения длины/количества i
        dp = [float('inf')] * (required_value + 1)
        dp[0] = 0  # Стоимость для длины/количества 0 равна 0
        # component_combination[i] будет словарем {название_компонента: количество} для достижения i
        component_combination: List[Dict[str, int]] = [{} for _ in range(required_value + 1)]

        logger.debug(f"Начинаем ДП с {len(suitable_components)} подходящими компонентами для значения {required_value}.")
        for item in suitable_components:
            item_name = item["name"]
            item_unit_val = item["unit_value"] 
            item_cost = item["cost_per_unit_value"] 

            if item_unit_val <= 0: 
                logger.warning(f"ДП: Компонент '{item_name}' имеет некорректное единичное значение {item_unit_val}. Пропуск.")
                continue

            # Обновляем dp для всех длин/количеств, которые можно достичь добавлением текущего элемента
            for current_val_dp in range(item_unit_val, required_value + 1):
                # Проверяем, достижимо ли состояние (current_val_dp - item_unit_val)
                if dp[current_val_dp - item_unit_val] == float('inf'):
                    continue # Если предыдущее состояние недостижимо, то и новое через него не достичь

                cost_if_added = dp[current_val_dp - item_unit_val] + item_cost
                if cost_if_added < dp[current_val_dp]: # Если нашли более дешевый способ
                    dp[current_val_dp] = cost_if_added
                    # Обновляем комбинацию компонентов
                    new_combination = component_combination[current_val_dp - item_unit_val].copy()
                    new_combination[item_name] = new_combination.get(item_name, 0) + 1
                    component_combination[current_val_dp] = new_combination
        
        # Проверяем, удалось ли достичь требуемого значения
        if dp[required_value] == float('inf'):
            message_suffix = f"для точного сечения {_exact_target_section_pair_for_recursion}" if _exact_target_section_pair_for_recursion else \
                             f"с осн. фильтром сечения {section_filter_dim}"
            logger.warning(f"ДП не смогло составить требуемое значение {required_value} для типа '{component_type}' {message_suffix}.")

            if _recursion_level == 0: # Если это основной вызов и ДП не сработало
                logger.info("Основной подбор не удался (ДП не нашло решения). Попытка найти альтернативные сечения...")
                return self._handle_alternative_section_search(required_value, section_filter_dim, component_type)
            else: # Рекурсивный вызов не смог подобрать
                return {"components": {}, "total_cost": 0, "total_value": 0, "message": f"Подбор не удался (ДП): не удалось достичь значения {required_value} {message_suffix}."}

        # Если подбор на текущем уровне успешен
        current_selected_components = component_combination[required_value]
        current_total_cost = dp[required_value]
        
        current_actual_total_value = 0
        for name, count in current_selected_components.items():
            # Ищем детали компонента (особенно unit_value) в отфильтрованном списке suitable_components
            comp_details = next((c for c in suitable_components if c["name"] == name), None)
            if comp_details:
                current_actual_total_value += comp_details["unit_value"] * count
            else:
                logger.error(f"КРИТИЧЕСКАЯ ОШИБКА при расчете actual_total_value: Детали для компонента '{name}' не найдены в suitable_components.")
        
        # Если это основной вызов, сохраняем результаты в self
        if _recursion_level == 0:
            self.selected_components = current_selected_components
            self.total_cost = current_total_cost
            self.total_accumulated_value = current_actual_total_value

        message = "Подбор успешно завершен"
        if _recursion_level > 0:
            message += f" для альтернативного сечения {_exact_target_section_pair_for_recursion}."
        
        logger.info(f"Подбор (уровень {_recursion_level}) завершен успешно. Компоненты: {current_selected_components}. Стоимость: {current_total_cost:.2f}. Значение: {current_actual_total_value}")
        return {
            "components": current_selected_components,
            "total_cost": current_total_cost,
            "total_value": current_actual_total_value,
            "message": message,
            "target_section": _exact_target_section_pair_for_recursion or \
                              ((section_filter_dim, section_filter_dim) if section_filter_dim else "не указано") # Для информации
        }

    def _handle_alternative_section_search(self, required_value: int, 
                                           original_section_filter_dim: Optional[int], 
                                           component_type: str) -> Dict[str, Any]:
        """
        Обрабатывает поиск и подбор для альтернативных (меньших и больших) размеров сечения.
        Вызывается, если основной подбор в find_optimal_components не удался.
        """
        logger.info(f"Обработка альтернативных сечений для значения={required_value}, исх.фильтр={original_section_filter_dim}, тип='{component_type}'")
        
        # Целевые размеры для поиска ближайших. Если original_section_filter_dim задан, ищем вокруг него.
        # Если не задан, find_nearest_* будут искать среди всех доступных сечений для component_type.
        # Это может быть не очень осмысленно, если нет исходной "точки отсчета" по сечению.
        # Для простоты, если original_section_filter_dim не задан, передаем его как None,
        # find_nearest_* попытаются найти "абсолютно" меньшее/большее.
        # Но лучше, если бы был какой-то целевой L и W. Пока используем original_section_filter_dim как L, а W=None
        
        # Определяем target_L и target_W для find_nearest_*
        # Если original_section_filter_dim задан, он может быть D, W или H.
        # Для простоты, будем считать его D или одной из сторон, ища ближайшие пары (L,W).
        target_L_for_search = original_section_filter_dim if original_section_filter_dim is not None else 0 # 0 если не задан, find_nearest* обработает
        target_W_for_search = None # Ищем ближайшие пары (L,W), где W может быть равно L (для круглых/квадратных)

        smaller_alt_section = self.find_nearest_smaller(target_L_for_search, target_W_for_search, component_type)
        larger_alt_section = self.find_nearest_larger(target_L_for_search, target_W_for_search, component_type)

        results_smaller = None
        results_larger = None

        if smaller_alt_section:
            logger.info(f"Найдено меньшее альтернативное сечение: {smaller_alt_section}. Запуск подбора...")
            results_smaller = self.find_optimal_components(
                required_value, 
                section_filter_dim=None, # section_filter_dim не используется, т.к. есть точная пара
                component_type=component_type,
                _exact_target_section_pair_for_recursion=smaller_alt_section,
                _recursion_level=1
            )
        else:
            logger.info("Меньшее альтернативное сечение не найдено.")
            results_smaller = {"message": "Меньшее альтернативное сечение не найдено.", "target_section": "N/A"}


        if larger_alt_section:
            logger.info(f"Найдено большее альтернативное сечение: {larger_alt_section}. Запуск подбора...")
            results_larger = self.find_optimal_components(
                required_value, 
                section_filter_dim=None,
                component_type=component_type,
                _exact_target_section_pair_for_recursion=larger_alt_section,
                _recursion_level=1
            )
        else:
            logger.info("Большее альтернативное сечение не найдено.")
            results_larger = {"message": "Большее альтернативное сечение не найдено.", "target_section": "N/A"}

        return {
            "message": f"Для заданных параметров (значение={required_value}, осн.фильтр сечения={original_section_filter_dim}, тип='{component_type}') " \
                       f"точный набор не найден. Предлагаются альтернативы:",
            "alternative_smaller": results_smaller,
            "alternative_larger": results_larger
        }


    def generate_bill_of_materials(self) -> str:
        """
        Генерирует текстовую спецификацию на основе результатов последнего УСПЕШНОГО ОСНОВНОГО подбора
        (хранящихся в self.selected_components, self.total_cost, self.total_accumulated_value).
        Если основной подбор не удался, но есть альтернативные, эта функция их НЕ отображает.
        Для отображения альтернатив нужно анализировать сложный словарь, возвращаемый `find_optimal_components`.

        :return: Строка с отформатированной спецификацией для основного подбора, или сообщение о неудаче.
        """
        if not self.selected_components: # Проверяем, был ли успешный ОСНОВНОЙ подбор
            logger.warning("Спецификация: Нет данных об успешном основном подборе (self.selected_components пуст).")
            return "Комплектующие для основного запроса не были подобраны. Проверьте сообщения о возможных альтернативах."

        bill = "СПЕЦИФИКАЦИЯ ПОДОБРАННЫХ КОМПЛЕКТУЮЩИХ (для основного запроса):\n"
        bill += "=" * 70 + "\n"
        
        item_num = 1
        for name, count in self.selected_components.items():
            if name not in self.components:
                logger.error(f"Спецификация: Компонент '{name}' из self.selected_components не найден в общем каталоге self.components.")
                bill += f"{item_num}. {name} (ДЕТАЛИ ИЗ ОБЩЕГО КАТАЛОГА НЕ НАЙДЕНЫ) — {count} шт.\n"
                item_num +=1
                continue

            comp_data_from_catalog = self.components[name]
            size_str, material, characteristics, cost_raw, standard = comp_data_from_catalog
            
            # Получаем единичное значение и цену за него для корректного отображения
            # Используем _last_component_type_request, который был установлен при последнем основном вызове find_optimal_components
            unit_val, cost_per_unit = self._parse_item_unit_value_and_price_logic(
                name, characteristics, cost_raw, self._last_component_type_request or "неизвестный тип"
            )
            
            total_item_cost = cost_per_unit * count 
            
            unit_display_name = "шт."
            # Определяем, как отображать единицу измерения на основе типа компонента и его unit_value
            if self._is_item_duct_like(name, self._last_component_type_request or "") and unit_val > 1:
                unit_display_name = f"(ед. по {unit_val}мм)" if unit_val != 1000 else "(м.п.)" # Если unit_val=1000, это "метр погонный"
            
            bill_line = f"{item_num}. {name}\n"
            bill_line += f"   Характеристики из каталога: Сечение/Размер: {size_str}, Материал: {material or 'N/A'}, Доп: {characteristics or 'N/A'}\n"
            bill_line += f"   Подобрано: {count} {unit_display_name} × {cost_per_unit:.2f} руб./ед. = {total_item_cost:.2f} руб.\n"
            bill_line += "-" * 70 + "\n"
            bill += bill_line
            item_num += 1

        bill += "=" * 70 + "\n"
        
        # Определяем единицу измерения для общего итога
        value_unit_str_total = "мм" if self._is_item_duct_like("", self._last_component_type_request or "") and self.total_accumulated_value > 1 else "шт."
        if self.total_accumulated_value > 0 :
             bill += f"Суммарное значение (длина/количество) для основного подбора: {self.total_accumulated_value} {value_unit_str_total}\n"

        bill += f"ОБЩАЯ СТОИМОСТЬ (для основного подбора): {self.total_cost:.2f} руб.\n"
        logger.info("Спецификация комплектующих для основного подбора успешно сформирована.")
        return bill


if __name__ == '__main__':
    optimizer = VentilationSystemOptimizer(components)

    def print_results(result_dict: Dict[str, Any], title: str):
        print(f"\n--- {title} ---")
        print(f"Сообщение: {result_dict.get('message')}")
        if "components" in result_dict and result_dict["components"]: # Успешный основной или рекурсивный подбор
            print(f"  Подобранные компоненты: {result_dict['components']}")
            print(f"  Общая стоимость: {result_dict.get('total_cost', 0):.2f} руб.")
            print(f"  Суммарное значение: {result_dict.get('total_value', 0)}")
            print(f"  Для сечения: {result_dict.get('target_section', 'N/A')}")
        elif "alternative_smaller" in result_dict or "alternative_larger" in result_dict: # Были предложены альтернативы
            if result_dict.get("alternative_smaller"):
                print("\n  --- Альтернатива (меньшее сечение): ---")
                print_results(result_dict["alternative_smaller"], "Результат для меньшего сечения")
            if result_dict.get("alternative_larger"):
                print("\n  --- Альтернатива (большее сечение): ---")
                print_results(result_dict["alternative_larger"], "Результат для большего сечения")
        # Для основного успешного подбора можно вывести спецификацию
        if "components" in result_dict and result_dict["components"] and not ("alternative_smaller" in result_dict):
            print("\n  Спецификация (для основного успешного подбора):")
            print(optimizer.generate_bill_of_materials())


    logger.info("Пример 1: Успешный подбор воздуховодов")
    res1 = optimizer.find_optimal_components(required_value=2500, section_filter_dim=500, component_type="воздуховод")
    print_results(res1, "Пример 1: Успешный подбор воздуховодов (500xH, L=2500мм)")

    logger.info("\nПример 2: Подбор фитингов (отводов) по диаметру из диапазона")
    res2 = optimizer.find_optimal_components(required_value=3, section_filter_dim=200, component_type="отвод")
    print_results(res2, "Пример 2: Подбор отводов (ø200, 3шт)")
    
    logger.info("\nПример 3: Неудачный основной подбор (несуществующее сечение), поиск альтернатив")
    res3 = optimizer.find_optimal_components(required_value=1000, section_filter_dim=999, component_type="воздуховод")
    print_results(res3, "Пример 3: Неудачный подбор (фильтр сечения 999мм), поиск альтернатив")

    logger.info("\nПример 4: Подбор конкретного клапана")
    res4 = optimizer.find_optimal_components(required_value=1, section_filter_dim=450, component_type="Клапан КР-450")
    print_results(res4, "Пример 4: Подбор клапана КР-450 (ø450, 1шт)")

    logger.info("\nПример 5: Запрос, для которого нет компонентов в каталоге (по типу)")
    res5 = optimizer.find_optimal_components(required_value=1, component_type="несуществующий_тип")
    print_results(res5, "Пример 5: Запрос на несуществующий тип компонента")

    logger.info("\nПример 6: Подбор воздуховода, где есть и м.п. и L= в каталоге")
    # Должен выбрать оптимально из "воздуховод 500х800" (150/м) и "воздуховод 500х800 L=1250" (187.5/1.25м = 150/м)
    res6 = optimizer.find_optimal_components(required_value=3000, section_filter_dim=800, component_type="воздуховод")
    print_results(res6, "Пример 6: Подбор воздуховода 500х800 (L=3000мм) из разных типов в каталоге")