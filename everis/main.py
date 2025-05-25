import re
from typing import Dict, List, Tuple, Optional, Union, Any, cast
from utils.mylogger import Logger
from date.components import components

logger = Logger("everis_optimizer_v2", "everis_optimizer_v2.log")

class VentilationSystemOptimizer:
    def __init__(self, components_data: Dict[str, Tuple[str, str, Optional[str], Optional[float], Optional[str]]]):
        """
        Класс для оптимизации подбора комплектующих вентиляционной системы.
        
        :param components_data: Словарь комплектующих из вашего файла components.py.
        """
        self.components: Dict[str, Tuple[str, str, Optional[str], Optional[float], Optional[str]]] = components_data
        self.selected_components: Dict[str, int] = {}
        self.total_cost: float = 0.0
        self.total_accumulated_value: int = 0 
        self._last_component_type_request: str = "" 

        self.fittings: List[str] = [
            "поворот", "отвод", "тройник", "переход", "зонт", "дефлектор", 
            "решетка", "клапан", "фильтр", "вентилятор", "глушитель", "насадок", "врезка"
        ]
        self.duct_types: List[str] = ["воздуховод", "канал", "труба гибкая"]
        self.material_types: List[str] = ["сталь", "маты", "шпилька", "анкер", "гайка", "профиль", "скоба", "шайба"]

        logger.info(f"Инициализирован VentilationSystemOptimizer с {len(self.components)} компонентами из каталога.")

    def _is_item_duct_like(self, item_name: str, component_type_request: str) -> bool:
        name_lower = item_name.lower()
        type_req_lower = component_type_request.lower()
        if any(keyword in type_req_lower for keyword in self.duct_types):
            return True
        if any(keyword in name_lower for keyword in self.duct_types) and \
           not any(fit_kw in name_lower for fit_kw in self.fittings):
            return True
        return False

    def _is_item_fitting_like(self, item_name: str, component_type_request: str) -> bool:
        name_lower = item_name.lower()
        type_req_lower = component_type_request.lower()
        if any(keyword in type_req_lower for keyword in self.fittings):
            return True
        if any(keyword in name_lower for keyword in self.fittings):
            return True
        return False

    def _parse_item_unit_value_and_price_logic(self, item_name: str, characteristics_str: Optional[str], 
                                               item_cost_raw: Optional[float], component_type_request: str) \
                                               -> Tuple[int, float]:
        unit_value = 0
        cost_per_unit_value = 0.0
        cost_raw = item_cost_raw if item_cost_raw is not None else 0.0

        is_duct = self._is_item_duct_like(item_name, component_type_request)
        is_fitting = self._is_item_fitting_like(item_name, component_type_request)

        if characteristics_str: 
            match_L = re.search(r"L=(\d+)\s*мм", characteristics_str, re.IGNORECASE)
            if match_L:
                unit_value = int(match_L.group(1))
                cost_per_unit_value = cost_raw
                logger.debug(f"Для '{item_name}': извлечена длина L={unit_value}мм, цена {cost_per_unit_value}.")
                return unit_value, cost_per_unit_value

        if is_duct:
            unit_value = 1000 
            cost_per_unit_value = cost_raw 
            logger.debug(f"Для воздуховода '{item_name}' без L=: предполагается unit_value={unit_value}мм (1м), цена за метр {cost_per_unit_value}.")
        elif is_fitting:
            unit_value = 1 
            cost_per_unit_value = cost_raw
            logger.debug(f"Для фитинга '{item_name}': предполагается unit_value=1шт, цена {cost_per_unit_value}.")
        else: 
            unit_value = 1 
            cost_per_unit_value = cost_raw
            logger.debug(f"Для неопределенного типа '{item_name}': предполагается unit_value=1 (усл.ед.), цена {cost_per_unit_value}.")
        
        return unit_value, cost_per_unit_value


    def parse_section_size(self, size_str: str) -> Optional[Union[Tuple[int, int], Tuple[str, int, int], Tuple[int, int, int, int]]]:
        if not isinstance(size_str, str):
            logger.warning(f"parse_section_size получил не строку: {size_str}")
            return None

        size_str_lower = size_str.lower()

        match_rect = re.match(r"(\d+)\s*x\s*(\d+)\s*мм", size_str_lower)
        if match_rect:
            dims = (int(match_rect.group(1)), int(match_rect.group(2)))
            logger.debug(f"Парсинг сечения (прямоугольное): '{size_str}' -> {dims}")
            return dims

        match_circle = re.match(r"ø(\d+)\s*мм", size_str_lower)
        if match_circle:
            diameter = int(match_circle.group(1))
            dims = (diameter, diameter)
            logger.debug(f"Парсинг сечения (круглое): '{size_str}' -> {dims}")
            return dims
        
        match_transition_arrow = re.match(r"(.+?)\s*→\s*(.+?)\s*мм", size_str)
        if match_transition_arrow:
            first_part_str = match_transition_arrow.group(1).strip() + " мм"
            parsed_first_part = self.parse_section_size(first_part_str) 
            if parsed_first_part and not isinstance(parsed_first_part[0], str) : 
                logger.debug(f"Парсинг сечения (переход): '{size_str}' -> первое сечение {parsed_first_part} для фильтрации.")
                return parsed_first_part 
            else: 
                 logger.debug(f"Парсинг сечения (переход): '{size_str}' -> первая часть '{first_part_str}' не дала конкретного сечения.")

        match_range_circle = re.match(r"ø(\d+)\s*-\s*(\d+)\s*мм", size_str_lower)
        if match_range_circle:
            min_d, max_d = int(match_range_circle.group(1)), int(match_range_circle.group(2))
            dims = ('range_circle', min_d, max_d)
            logger.debug(f"Парсинг сечения (диапазон кругл.): '{size_str}' -> {dims}")
            return dims
            
        if "м3/ч" in size_str_lower or \
           (size_str_lower.replace('.', '', 1).isdigit() and "мм" in size_str_lower and \
            'x' not in size_str_lower and 'ø' not in size_str_lower and '-' not in size_str_lower): # Добавил проверку на '-'
             logger.debug(f"Строка '{size_str}' не является размером сечения (похоже на производительность или толщину).")
             return None

        logger.info(f"Строка '{size_str}' не распознана как известный формат размера сечения или диапазона.")
        return None
    
    def _validate_input(
        self,
        required_value: int,
        section_filter_dim: Optional[int],
        component_type: str
    ) -> bool:
        if not isinstance(required_value, int) or required_value <= 0:
            msg = "Требуемое значение (длина/количество) должно быть положительным целым числом."
            logger.error(msg)
            raise ValueError(msg)
        
        if section_filter_dim is not None:
            if not isinstance(section_filter_dim, int) or section_filter_dim <= 0:
                msg = "Фильтр по размеру сечения должен быть положительным целым числом, если указан."
                logger.error(msg)
                raise ValueError(msg)
        
        if not component_type or not isinstance(component_type, str):
            msg = "Тип компонента должен быть непустой строкой."
            logger.error(msg)
            raise ValueError(msg)

        logger.info(f"Входные данные для оптимизации валидны: значение={required_value}, фильтр сечения={section_filter_dim}, тип={component_type}")
        return True

    def _filter_components(
        self,
        component_type_request: str,
        section_filter_dim: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        filtered_items = []
        type_req_lower = component_type_request.lower()

        for name, data in self.components.items():
            size_str, material, characteristics_str, cost_val, standard_str = data
            name_lower = name.lower()
            
            item_is_duct_like_by_name_or_request = self._is_item_duct_like(name, component_type_request)
            item_is_fitting_like_by_name_or_request = self._is_item_fitting_like(name, component_type_request)
            
            request_is_duct_type = self._is_item_duct_like("", component_type_request)
            request_is_fitting_type = self._is_item_fitting_like("", component_type_request)


            if request_is_duct_type and self._is_item_fitting_like(name, ""): # Если запрос на воздуховод, а имя компонента - фитинг
                logger.debug(f"Фильтр: '{name}' (фитинг по имени) не соответствует запросу на воздуховод '{component_type_request}'. Пропуск.")
                continue
            if request_is_fitting_type and self._is_item_duct_like(name, ""): # Если запрос на фитинг, а имя компонента - воздуховод
                 logger.debug(f"Фильтр: '{name}' (воздуховод по имени) не соответствует запросу на фитинг '{component_type_request}'. Пропуск.")
                 continue
            
            is_specific_fitting_request = any(ft == type_req_lower for ft in self.fittings)
            if is_specific_fitting_request and type_req_lower not in name_lower:
                 logger.debug(f"Фильтр: '{name}' не содержит ключ конкретного фитинга '{component_type_request}' в имени. Пропуск.")
                 continue

            parsed_catalog_section = self.parse_section_size(size_str)
            actual_section_for_item = None
            
            if parsed_catalog_section is None: 
                if section_filter_dim is not None: 
                    logger.debug(f"Фильтр: '{name}' с размером '{size_str}' не имеет парсуемого сечения, но фильтр сечения {section_filter_dim} задан. Пропуск.")
                    continue
            
            elif isinstance(parsed_catalog_section, tuple) and len(parsed_catalog_section)>0 and isinstance(parsed_catalog_section[0], str) and parsed_catalog_section[0].startswith('range_'):
                # Проверка, что parsed_catalog_section не пустой перед обращением к len() и [0]
                range_type, min_val, max_val = parsed_catalog_section
                if section_filter_dim is not None:
                    if range_type == 'range_circle' and min_val <= section_filter_dim <= max_val:
                        actual_section_for_item = (section_filter_dim, section_filter_dim)
                        logger.debug(f"Фильтр: '{name}' с диапазоном {parsed_catalog_section} подходит под фильтр {section_filter_dim}, используется сечение {actual_section_for_item}.")
                    else: 
                        logger.debug(f"Фильтр: '{name}' с диапазоном {parsed_catalog_section} не содержит фильтр сечения {section_filter_dim}. Пропуск.")
                        continue
                else: 
                    logger.debug(f"Фильтр: '{name}' с диапазоном {parsed_catalog_section} подходит, т.к. фильтр сечения не задан (сечение не уточнено).")
                    actual_section_for_item = None 
            
            elif isinstance(parsed_catalog_section, tuple) and len(parsed_catalog_section) == 2 and all(isinstance(dim, int) for dim in parsed_catalog_section):
                actual_section_for_item = cast(Tuple[int, int], parsed_catalog_section) 
                if section_filter_dim is not None:
                    if not any(dim == section_filter_dim for dim in actual_section_for_item):
                        logger.debug(f"Фильтр: '{name}' с сечением {actual_section_for_item} не соответствует фильтру {section_filter_dim}. Пропуск.")
                        continue
            elif section_filter_dim is not None: # Если есть фильтр, а сечение не конкретное и не подходящий диапазон
                logger.debug(f"Фильтр: '{name}' с нераспознанным/неконкретным сечением {parsed_catalog_section} не подходит под фильтр {section_filter_dim}. Пропуск.")
                continue


            unit_value, cost_per_unit = self._parse_item_unit_value_and_price_logic(
                name, characteristics_str, cost_val, component_type_request
            )

            if unit_value <= 0:
                logger.warning(f"Фильтр: Компонент '{name}' имеет невалидное единичное значение {unit_value}. Пропуск.")
                continue
            
            filtered_items.append({
                "name": name,
                "catalog_section_info": parsed_catalog_section,
                "effective_section_size": actual_section_for_item,
                "unit_value": unit_value,
                "cost_per_unit_value": cost_per_unit
            })
            logger.info(f"Фильтр: Компонент '{name}' прошел отбор. Кат.сеч: {parsed_catalog_section}, Эфф.сеч: {actual_section_for_item}, Ед.зн: {unit_value}, Цена: {cost_per_unit}")

        return filtered_items

    def _get_unique_section_dimensions(self, component_type_filter: str) -> List[Tuple[int, int]]:
        section_dimensions_set = set()
        for name, data in self.components.items():
            size_str = data[0]
            parsed_section = self.parse_section_size(size_str)
            if parsed_section and isinstance(parsed_section, tuple) and \
               len(parsed_section) == 2 and isinstance(parsed_section[0], int) and isinstance(parsed_section[1], int):
                section_dimensions_set.add(cast(Tuple[int, int], parsed_section))
        
        sorted_dimensions = sorted(list(section_dimensions_set))
        logger.info(f"Собраны уникальные КОНКРЕТНЫЕ размеры сечений для типа '{component_type_filter}': {len(sorted_dimensions)} вариантов.")
        return sorted_dimensions
    
    def find_nearest_smaller(self, target_L_section: int, target_W_section_nullable: Optional[int], component_type: str) -> Optional[Tuple[int, int]]:
        logger.info(f"Поиск ближайшего меньшего сечения: цель L_секции={target_L_section}, W_секции={target_W_section_nullable}, тип комп-та: {component_type}")
        available_section_dims = self._get_unique_section_dimensions(component_type) 

        best_match_section: Optional[Tuple[int, int]] = None
        max_area_found = -1.0

        for sL_cand, sW_cand in available_section_dims: 
            current_sL, current_sW = sL_cand, sW_cand 
            
            passes_direct = False
            if target_W_section_nullable is None: 
                if current_sL == current_sW and current_sL <= target_L_section:
                    passes_direct = True
            else: 
                if current_sL <= target_L_section and current_sW <= target_W_section_nullable:
                    passes_direct = True
            
            passes_swapped = False
            if target_W_section_nullable is not None and current_sL != current_sW:
                if current_sW <= target_L_section and current_sL <= target_W_section_nullable:
                    passes_swapped = True

            chosen_sL, chosen_sW = 0,0
            valid_candidate_found = False

            if passes_direct and passes_swapped: 
                chosen_sL, chosen_sW = current_sL, current_sW 
                valid_candidate_found = True
            elif passes_direct:
                chosen_sL, chosen_sW = current_sL, current_sW
                valid_candidate_found = True
            elif passes_swapped: 
                chosen_sL, chosen_sW = current_sW, current_sL 
                valid_candidate_found = True

            if valid_candidate_found:
                current_area = float(chosen_sL * chosen_sW)
                if current_area > max_area_found:
                    max_area_found = current_area
                    best_match_section = (chosen_sL, chosen_sW)
                elif current_area == max_area_found and best_match_section is not None:
                    if abs(target_L_section - chosen_sL) < abs(target_L_section - best_match_section[0]):
                         best_match_section = (chosen_sL, chosen_sW)
        
        if best_match_section:
            logger.info(f"Найден ближайший меньший размер сечения: {best_match_section}")
        else:
            logger.warning(f"Ближайший меньший размер сечения не найден для цели L={target_L_section}, W={target_W_section_nullable}.")
        return best_match_section

    def find_nearest_larger(self, target_L_section: int, target_W_section_nullable: Optional[int], component_type: str) -> Optional[Tuple[int, int]]:
        logger.info(f"Поиск ближайшего большего сечения: цель L_секции={target_L_section}, W_секции={target_W_section_nullable}, тип комп-та: {component_type}")
        available_section_dims = self._get_unique_section_dimensions(component_type)

        best_match_section: Optional[Tuple[int, int]] = None
        min_area_found = float('inf')

        for sL_cand, sW_cand in available_section_dims:
            current_sL, current_sW = sL_cand, sW_cand

            passes_direct = False
            if target_W_section_nullable is None: 
                if current_sL == current_sW and current_sL >= target_L_section:
                    passes_direct = True
            else: 
                if current_sL >= target_L_section and current_sW >= target_W_section_nullable:
                    passes_direct = True
            
            passes_swapped = False
            if target_W_section_nullable is not None and current_sL != current_sW: 
                if current_sW >= target_L_section and current_sL >= target_W_section_nullable:
                    passes_swapped = True
            
            chosen_sL, chosen_sW = 0,0
            valid_candidate_found = False

            if passes_direct and passes_swapped:
                chosen_sL, chosen_sW = current_sL, current_sW
                valid_candidate_found = True
            elif passes_direct:
                chosen_sL, chosen_sW = current_sL, current_sW
                valid_candidate_found = True
            elif passes_swapped:
                chosen_sL, chosen_sW = current_sW, current_sL
                valid_candidate_found = True

            if valid_candidate_found:
                current_area = float(chosen_sL * chosen_sW)
                if current_area < min_area_found:
                    min_area_found = current_area
                    best_match_section = (chosen_sL, chosen_sW)
                elif current_area == min_area_found and best_match_section is not None:
                    if abs(target_L_section - chosen_sL) < abs(target_L_section - best_match_section[0]):
                        best_match_section = (chosen_sL, chosen_sW)
        
        if best_match_section:
            logger.info(f"Найден ближайший больший размер сечения: {best_match_section}")
        else:
            logger.warning(f"Ближайший больший размер сечения не найден для цели L={target_L_section}, W={target_W_section_nullable}.")
        return best_match_section

    def find_optimal_components(
        self,
        required_value: int, 
        section_filter_dim: Optional[int] = None, 
        component_type: str = "воздуховод"
    ) -> Dict[str, Union[Dict[str, int], float, int, str]]:
        
        self._last_component_type_request = component_type 
        logger.info(f"Запрос на оптимизацию: требуемое значение={required_value}, фильтр сечения={section_filter_dim}, тип={component_type}")
        
        try:
            self._validate_input(required_value, section_filter_dim, component_type)
        except ValueError as e:
            logger.error(f"Ошибка валидации входных данных: {e}")
            return {"components": {}, "total_cost": 0, "total_value": 0, "message": str(e)}

        self.selected_components = {}
        self.total_cost = 0.0
        self.total_accumulated_value = 0

        suitable_components = self._filter_components(component_type, section_filter_dim)
        
        if not suitable_components:
            logger.warning(f"Не найдено подходящих компонентов в каталоге для типа '{component_type}' с фильтром сечения '{section_filter_dim}'.")
            message = f"Нет подходящих компонентов в каталоге для типа '{component_type}' с фильтром сечения '{section_filter_dim}'.\n"
            
            if section_filter_dim is not None: 
                logger.info(f"Попытка найти альтернативные КОНКРЕТНЫЕ размеры сечения вокруг {section_filter_dim} мм для типа {component_type}.")
                smaller_alt_section = self.find_nearest_smaller(section_filter_dim, None, component_type) 
                larger_alt_section = self.find_nearest_larger(section_filter_dim, None, component_type)
                if smaller_alt_section:
                    message += f"  - Ближайший меньший КОНКРЕТНЫЙ размер сечения из каталога (для круглых/квадратных форм): {smaller_alt_section[0]}x{smaller_alt_section[1]} мм.\n"
                if larger_alt_section:
                    message += f"  - Ближайший больший КОНКРЕТНЫЙ размер сечения из каталога (для круглых/квадратных форм): {larger_alt_section[0]}x{larger_alt_section[1]} мм.\n"
                if not smaller_alt_section and not larger_alt_section:
                     message += "  - Не удалось найти альтернативные конкретные размеры сечений в каталоге.\n"
            message += "  Рекомендация: Проверьте каталог или расширьте критерии поиска."
            return {"components": {}, "total_cost": 0, "total_value": 0, "message": message}

        dp = [float('inf')] * (required_value + 1)
        dp[0] = 0 
        component_combination = [{} for _ in range(required_value + 1)]

        for item in suitable_components:
            item_name = item["name"]
            item_unit_val = item["unit_value"] 
            item_cost = item["cost_per_unit_value"] 

            if item_unit_val <= 0: 
                logger.warning(f"Компонент '{item_name}' имеет некорректное единичное значение {item_unit_val} и будет пропущен в ДП.")
                continue

            for current_val in range(item_unit_val, required_value + 1):
                if dp[current_val - item_unit_val] == float('inf'): 
                    continue
                cost_if_added = dp[current_val - item_unit_val] + item_cost
                if cost_if_added < dp[current_val]:
                    dp[current_val] = cost_if_added
                    new_combination = component_combination[current_val - item_unit_val].copy()
                    new_combination[item_name] = new_combination.get(item_name, 0) + 1
                    component_combination[current_val] = new_combination
        
        if dp[required_value] == float('inf'):
            msg = f"Не удалось подобрать компоненты для точного значения {required_value} (длина/количество) из отфильтрованных вариантов."
            logger.warning(msg)
            return {"components": {}, "total_cost": 0, "total_value": 0, "message": msg}

        self.selected_components = component_combination[required_value]
        self.total_cost = dp[required_value]
        
        actual_total_value = 0
        for name, count in self.selected_components.items():
            comp_details_from_suitable = next((c for c in suitable_components if c["name"] == name), None)
            if comp_details_from_suitable:
                actual_total_value += comp_details_from_suitable["unit_value"] * count
            else:
                logger.error(f"КРИТИЧЕСКАЯ ОШИБКА: Детали для компонента '{name}' из selected_components не найдены в suitable_components.")
        
        self.total_accumulated_value = actual_total_value

        logger.info(f"Подбор завершен. Тип: '{component_type}'. Подобранные компоненты: {self.selected_components}. Общая стоимость: {self.total_cost:.2f}. Общее значение (длина/кол-во): {self.total_accumulated_value}")
        return {
            "components": self.selected_components,
            "total_cost": self.total_cost,
            "total_value": self.total_accumulated_value,
            "message": "Подбор успешно завершен."
        }

    def generate_bill_of_materials(self) -> str:
        if not self.selected_components:
            logger.warning("Спецификация: Комплектующие не были подобраны (self.selected_components пуст).")
            return "Комплектующие не подобраны."

        bill = "СПЕЦИФИКАЦИЯ ПОДОБРАННЫХ КОМПЛЕКТУЮЩИХ:\n"
        bill += "=" * 70 + "\n"
        
        item_num = 1
        for name, count in self.selected_components.items():
            if name not in self.components:
                logger.error(f"Спецификация: Компонент '{name}' из self.selected_components не найден в каталоге self.components.")
                bill += f"{item_num}. {name} (ДЕТАЛИ ИЗ КАТАЛОГА НЕ НАЙДЕНЫ) — {count} шт.\n"
                item_num +=1
                continue

            comp_data_from_catalog = self.components[name]
            size_str, material, characteristics, cost_raw, standard = comp_data_from_catalog
            
            unit_val, cost_per_unit = self._parse_item_unit_value_and_price_logic(
                name, characteristics, cost_raw, self._last_component_type_request or "неизвестный тип"
            )
            
            total_item_cost = cost_per_unit * count 
            
            unit_display_name = "шт."
            if self._is_item_duct_like(name, self._last_component_type_request) and unit_val > 1:
                unit_display_name = f"(отрезков/единиц по {unit_val}мм)" if unit_val != 1000 else "(метров)"
            
            bill_line = f"{item_num}. {name}\n"
            bill_line += f"   Каталог: Сечение/Размер: {size_str}, Материал: {material or 'N/A'}, Характ.: {characteristics or 'N/A'}\n"
            bill_line += f"   Количество: {count} {unit_display_name} × {cost_per_unit:.2f} руб./ед. = {total_item_cost:.2f} руб.\n"
            bill_line += "-" * 70 + "\n"
            bill += bill_line
            item_num += 1

        bill += "=" * 70 + "\n"
        
        value_unit_str = "мм" if self._is_item_duct_like("", self._last_component_type_request) and self.total_accumulated_value >1 else "шт."
        if self.total_accumulated_value > 0 :
             bill += f"Суммарное значение (длина/количество): {self.total_accumulated_value} {value_unit_str}\n"

        bill += f"ОБЩАЯ СТОИМОСТЬ ПОДОБРАННЫХ КОМПОНЕНТОВ: {self.total_cost:.2f} руб.\n"
        logger.info("Спецификация комплектующих успешно сформирована.")
        return bill


if __name__ == '__main__':
    optimizer = VentilationSystemOptimizer(components)

    logger.info("\n--- Пример 1: Подбор длины прямоугольного воздуховода ---")
    result1 = optimizer.find_optimal_components(
        required_value=3000,        
        section_filter_dim=500,     
        component_type="воздуховод"
    )
    print("\nРезультат 1 (подбор воздуховодов 500xH):")
    print(f"Сообщение: {result1.get('message')}")
    if result1["components"]:
        print(f"Подобранные компоненты: {result1['components']}")
        print(f"Общая стоимость: {result1['total_cost']:.2f} руб.")
        print(f"Суммарная длина: {result1['total_value']} мм")
        print("\nСпецификация 1:")
        print(optimizer.generate_bill_of_materials())

    logger.info("\n--- Пример 2: Подбор круглых отводов поштучно с фильтром по диаметру ---")
    result2 = optimizer.find_optimal_components(
        required_value=3,             
        section_filter_dim=150,       
        component_type="отвод"
    )
    print("\nРезультат 2 (подбор отводов ø150):")
    print(f"Сообщение: {result2.get('message')}")
    if result2["components"]:
        print(f"Подобранные компоненты: {result2['components']}")
        print(f"Общая стоимость: {result2['total_cost']:.2f} руб.")
        print(f"Суммарное количество: {result2['total_value']} шт.")
        print("\nСпецификация 2:")
        print(optimizer.generate_bill_of_materials())

    logger.info("\n--- Пример 3: Подбор клапанов ---")
    result3 = optimizer.find_optimal_components(
        required_value=1,
        section_filter_dim=450,
        component_type="клапан" 
    )
    print("\nРезультат 3 (подбор клапана ø450):")
    print(f"Сообщение: {result3.get('message')}")
    if result3["components"]:
        print(f"Подобранные компоненты: {result3['components']}")
        print(f"Общая стоимость: {result3['total_cost']:.2f} руб.")
        print(f"Суммарное количество: {result3['total_value']} шт.")
        print("\nСпецификация 3:")
        print(optimizer.generate_bill_of_materials())

    logger.info("\n--- Пример 4: Поиск воздуховода с конкретной длиной L= из каталога ---")
    result4 = optimizer.find_optimal_components(
        required_value=2500, 
        section_filter_dim=800, 
        component_type="воздуховод 500х800 L=1250" 
    )
    print("\nРезультат 4 (подбор воздуховодов 500x800 L=1250):")
    print(f"Сообщение: {result4.get('message')}")
    if result4["components"]:
        print(f"Подобранные компоненты: {result4['components']}")
        print(f"Общая стоимость: {result4['total_cost']:.2f} руб.")
        print(f"Суммарная длина: {result4['total_value']} мм")
        print("\nСпецификация 4:")
        print(optimizer.generate_bill_of_materials())