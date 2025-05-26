import re
from typing import Dict, List, Tuple, Optional, Union, Any, cast
import networkx as nx
from date.components import components
from utils.mylogger import Logger

logger = Logger("select_comp", "logs/select_comp.log")

class ComponentSelector:
    """
    Класс для подбора отдельных компонентов (воздуховодов, фитингов) 
    из каталога по заданным критериям. Используется классом VentilationSystemGraphOptimizer.
    """
    def __init__(self, components_data: Dict[str, Tuple[str, str, Optional[str], Optional[float], Optional[str]]]):
        """
        Инициализирует селектор компонентов.

        :param components_data: Словарь-каталог комплектующих.
        """
        self.components: Dict[str, Tuple[str, str, Optional[str], Optional[float], Optional[str]]] = components_data
        self.fittings: List[str] = [
            "поворот", "отвод", "тройник", "переход", "зонт", "дефлектор", 
            "решетка", "клапан", "фильтр", "вентилятор", "глушитель", "насадок", "врезка",
            "ниппель", "муфта", "заглушка"
        ]
        self.duct_types: List[str] = ["воздуховод", "канал", "труба гибкая"]
        logger.info(f"ComponentSelector инициализирован с {len(self.components)} компонентами.")

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
        if any(keyword in type_req_lower for keyword in self.duct_types):
            return True
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
        if any(keyword in type_req_lower for keyword in self.fittings):
            return True
        if any(keyword in name_lower for keyword in self.fittings):
            return True
        return False

    def _parse_item_unit_value_and_price_logic(self, item_name: str, characteristics_str: Optional[str], 
                                               item_cost_raw: Optional[float], component_type_request: str) \
                                               -> Tuple[int, float]:
        """
        Определяет единичное значение (стандартная длина или 1 для штучных) и стоимость за эту единицу.

        :param item_name: Имя компонента.
        :param characteristics_str: Строка характеристик из каталога.
        :param item_cost_raw: "Сырая" цена из каталога.
        :param component_type_request: Запрошенный тип компонента (для помощи в определении воздуховод/фитинг).
        :return: Кортеж (unit_value, cost_per_unit_value).
        """
        unit_value = 0
        cost_per_unit_value = 0.0
        cost_raw = item_cost_raw if item_cost_raw is not None else 0.0

        is_duct = self._is_item_duct_like(item_name, component_type_request)
        # is_fitting = self._is_item_fitting_like(item_name, component_type_request) # Менее критично здесь

        if characteristics_str: 
            match_L = re.search(r"L=(\d+)\s*мм", characteristics_str, re.IGNORECASE)
            if match_L:
                unit_value = int(match_L.group(1))
                cost_per_unit_value = cost_raw
                logger.debug(f"Селектор: Для '{item_name}': извлечена стандартная длина L={unit_value}мм, цена за отрезок {cost_per_unit_value}.")
                return unit_value, cost_per_unit_value

        if is_duct:
            unit_value = 1000 
            cost_per_unit_value = cost_raw 
            logger.debug(f"Селектор: Для воздуховода '{item_name}' без явной L=: предполагается unit_value={unit_value}мм (цена за 1м), цена {cost_per_unit_value}.")
        else: # Фитинги, оборудование, материалы без L=
            unit_value = 1 
            cost_per_unit_value = cost_raw
            logger.debug(f"Селектор: Для (предположительно) штучного товара/фитинга '{item_name}': unit_value=1, цена {cost_per_unit_value}.")
        
        return unit_value, cost_per_unit_value

    def parse_section_size(self, size_str: str) -> Optional[Union[Tuple[int, int], Tuple[str, int, int]]]:
        """
        Парсит строку с размерами сечения из каталога.
        Поддерживает: "WxH мм", "øD мм", "øD1-D2 мм", и первый элемент из "Размер1 → Размер2 мм".
        Возвращает (W,H), (D,D), ('range_circle', D1, D2) или None.
        """
        if not isinstance(size_str, str):
            logger.warning(f"Селектор.parse_section_size: вход не строка ({size_str}).")
            return None

        s = size_str.lower().strip()
        
        # Прямоугольные
        m = re.fullmatch(r"(\d+)\s*x\s*(\d+)\s*мм", s)
        if m: return (int(m.group(1)), int(m.group(2)))
        # Круглые
        m = re.fullmatch(r"ø(\d+)\s*мм", s)
        if m: d_val = int(m.group(1)); return (d_val, d_val)
        # Круглые диапазоны
        m = re.fullmatch(r"ø(\d+)\s*-\s*(\d+)\s*мм", s)
        if m: return ('range_circle', int(m.group(1)), int(m.group(2)))
        # Переходы (парсим первое сечение)
        m = re.match(r"(.+?)\s*→\s*(.+?)(?:\s*мм)?$", size_str) # Используем оригинальный size_str для рекурсии
        if m:
            first_part = m.group(1).strip()
            if not first_part.endswith("мм"): first_part += " мм"
            parsed_first = self.parse_section_size(first_part) # Рекурсивный вызов
            if parsed_first and isinstance(parsed_first, tuple) and \
               len(parsed_first) == 2 and isinstance(parsed_first[0], int):
                return cast(Tuple[int,int], parsed_first)
        
        # Игнорируем неразмерные характеристики
        if "м3/ч" in s or (re.fullmatch(r"\d+(?:\.\d+)?\s*мм", s) and \
           'x' not in s and 'ø' not in s and '-' not in s):
            logger.debug(f"Селектор.parse_section_size: '{size_str}' не является размером сечения.")
            return None
            
        logger.info(f"Селектор.parse_section_size: '{size_str}' не распознан.")
        return None

    def _validate_input_for_item_selection(self, required_value: int, component_type: str, 
                                           exact_target_section_pair: Optional[Tuple[int, int]], 
                                           section_filter_dim: Optional[int]) -> bool:
        """ Валидирует вход для find_optimal_components_for_item. """
        if not (isinstance(required_value, int) and required_value > 0):
            raise ValueError("Required value must be a positive integer.")
        if not component_type:
            raise ValueError("Component type must be a non-empty string.")
        if exact_target_section_pair is not None and \
           not (isinstance(exact_target_section_pair, tuple) and len(exact_target_section_pair) == 2 and
                all(isinstance(d, int) and d > 0 for d in exact_target_section_pair)):
            raise ValueError("Exact target section pair must be a tuple of two positive integers.")
        if section_filter_dim is not None and \
           not (isinstance(section_filter_dim, int) and section_filter_dim > 0):
            raise ValueError("Section filter dim must be a positive integer if provided.")
        return True

    def _filter_components_for_item_selection(
            self, component_type_request: str,
            exact_target_section_pair: Optional[Tuple[int, int]] = None,
            section_filter_dim: Optional[int] = None
        ) -> List[Dict[str, Any]]:
        """
        Фильтрует компоненты для одного конкретного запроса (используется find_optimal_components_for_item).
        Эта функция НЕ должна пытаться найти альтернативные сечения.
        """
        logger.debug(f"Селектор._filter: тип='{component_type_request}', точное_сеч={exact_target_section_pair}, осн_фильтр={section_filter_dim}")
        filtered = []
        type_req_l = component_type_request.lower().strip()

        for name, data in self.components.items():
            size_str, _, char_str, cost_v, _ = data
            name_l = name.lower()

            # 1. Фильтрация по типу (ключевое слово должно быть в имени или запросе)
            # Если component_type_request - это общее "воздуховод" или "отвод", то фильтруем по _is_item_duct/fitting_like
            # Если component_type_request - это специфичное имя "Клапан КР-450", то ищем по нему.
            request_is_generic_duct = self._is_item_duct_like("", component_type_request)
            request_is_generic_fitting = self._is_item_fitting_like("", component_type_request)
            
            item_match_type = False
            if request_is_generic_duct:
                if self._is_item_duct_like(name, component_type_request): item_match_type = True
            elif request_is_generic_fitting:
                 if self._is_item_fitting_like(name, component_type_request): item_match_type = True
            elif type_req_l in name_l: # Если запрос - это часть имени (например, модель оборудования)
                item_match_type = True
            
            if not item_match_type:
                continue

            # 2. Фильтрация по сечению
            cat_sec_info = self.parse_section_size(size_str)
            eff_sec_for_item: Optional[Tuple[int,int]] = None
            passes_sec_filter = False

            if exact_target_section_pair:
                # Ищем точное совпадение сечения WxH или DxH (если D=W)
                if cat_sec_info and isinstance(cat_sec_info, tuple) and len(cat_sec_info) == 2 and \
                   all(isinstance(d,int) for d in cat_sec_info):
                    s1, s2 = cast(Tuple[int,int], cat_sec_info)
                    t1, t2 = exact_target_section_pair
                    if (s1 == t1 and s2 == t2) or (s1 == t2 and s2 == t1):
                        eff_sec_for_item = (t1, t2)
                        passes_sec_filter = True
            elif section_filter_dim:
                # Фильтруем по одному из размеров ИЛИ по вхождению в диапазон
                if cat_sec_info and isinstance(cat_sec_info, tuple) and \
                   len(cat_sec_info) == 2 and all(isinstance(d,int) for d in cat_sec_info):
                    s1, s2 = cast(Tuple[int,int], cat_sec_info)
                    if s1 == section_filter_dim or s2 == section_filter_dim:
                        eff_sec_for_item = (s1,s2)
                        passes_sec_filter = True
                elif cat_sec_info and isinstance(cat_sec_info, tuple) and len(cat_sec_info) == 3 and \
                     cat_sec_info[0] == 'range_circle':
                    _, min_d, max_d = cat_sec_info
                    if min_d <= section_filter_dim <= max_d:
                        eff_sec_for_item = (section_filter_dim, section_filter_dim) # Используем фильтр как D
                        passes_sec_filter = True
            else: # Нет фильтра по сечению
                passes_sec_filter = True
                if cat_sec_info and isinstance(cat_sec_info, tuple) and \
                   len(cat_sec_info) == 2 and all(isinstance(d,int) for d in cat_sec_info):
                    eff_sec_for_item = cast(Tuple[int,int], cat_sec_info) # Запоминаем сечение, если оно конкретное

            if not passes_sec_filter:
                continue

            uv, cpu = self._parse_item_unit_value_and_price_logic(name, char_str, cost_v, component_type_request)
            if uv <= 0: continue
            
            filtered.append({
                "name": name, 
                "effective_section_size": eff_sec_for_item, # Сечение, с которым этот компонент прошел фильтр
                "unit_value": uv, 
                "cost_per_unit_value": cpu
            })
        logger.debug(f"Селектор._filter: Найдено {len(filtered)} компонентов.")
        return filtered

    def _get_unique_concrete_section_dimensions(self) -> List[Tuple[int, int]]:
        """ Возвращает список уникальных КОНКРЕТНЫХ размеров сечений (W,H) или (D,D) из каталога. """
        sds: set[Tuple[int, int]] = set()
        for name, data in self.components.items():
            parsed_section = self.parse_section_size(data[0])
            if parsed_section and isinstance(parsed_section, tuple) and \
               len(parsed_section) == 2 and isinstance(parsed_section[0], int) and isinstance(parsed_section[1], int):
                sds.add(cast(Tuple[int, int], parsed_section))
        return sorted(list(sds))
    
    def find_nearest_larger_concrete_section(self, target_L: int, target_W_nullable: Optional[int]) -> Optional[Tuple[int, int]]:
        """ 
        Ищет ближайший больший КОНКРЕТНЫЙ размер сечения из каталога.
        Используется для подбора воздуховодов, если точное сечение не найдено.
        """
        logger.debug(f"Селектор.find_nearest_larger: цель L={target_L}, W={target_W_nullable}")
        available_dims = self._get_unique_concrete_section_dimensions()
        best_match: Optional[Tuple[int, int]] = None
        min_area_found = float('inf')

        for sL_cand, sW_cand in available_dims:
            # Кандидат из каталога (sL_cand, sW_cand)
            # Проверяем, подходит ли кандидат (или его повернутая версия) под целевые размеры
            # и при этом больше или равен им.
            current_valid_orientation: Optional[Tuple[int,int]] = None

            if target_W_nullable is None: # Ищем круглый/квадратный (target_L - это D)
                if sL_cand == sW_cand and sL_cand >= target_L:
                    current_valid_orientation = (sL_cand, sW_cand)
            else: # Ищем прямоугольный (target_L, target_W_nullable)
                # Ориентация 1: (sL_cand, sW_cand)
                if sL_cand >= target_L and sW_cand >= target_W_nullable:
                    current_valid_orientation = (sL_cand, sW_cand)
                # Ориентация 2: (sW_cand, sL_cand) - только если не квадрат
                if sL_cand != sW_cand and sW_cand >= target_L and sL_cand >= target_W_nullable:
                    # Если первая ориентация не подошла ИЛИ эта (повернутая) имеет меньшую площадь
                    if current_valid_orientation is None or \
                       (sW_cand * sL_cand < current_valid_orientation[0] * current_valid_orientation[1]):
                        current_valid_orientation = (sW_cand, sL_cand) # Важно: возвращаем в ориентации (соотв. target_L, соотв. target_W)
                                                                     # Нет, возвращаем как есть из каталога, а вызывающий код разберется
                                                                     # или сохраняем ту ориентацию, что подошла
                        current_valid_orientation = (sL_cand,sW_cand) if (sL_cand >= target_L and sW_cand >= target_W_nullable) else (sW_cand,sL_cand)
                        # Для простоты, если обе ориентации кандидата подходят, берем первую.
                        # Более сложная логика могла бы выбирать по "близости" к target_L, target_W.

            if current_valid_orientation:
                chosen_sL, chosen_sW = current_valid_orientation
                current_area = float(chosen_sL * chosen_sW)
                if current_area < min_area_found:
                    min_area_found = current_area
                    best_match = (chosen_sL, chosen_sW) # Сохраняем как оно есть в каталоге
                elif current_area == min_area_found and best_match is not None:
                    # Приоритет тому, у кого первая сторона ближе к target_L (но не меньше)
                    if abs(target_L - chosen_sL) < abs(target_L - best_match[0]): # Сравниваем с первой стороной кандидата
                         best_match = (chosen_sL, chosen_sW)
        
        if best_match: logger.debug(f"Селектор.find_nearest_larger: найдено {best_match}")
        else: logger.warning(f"Селектор.find_nearest_larger: не найдено для L={target_L}, W={target_W_nullable}")
        return best_match

    def find_optimal_components_for_item(
        self,
        required_value: int, 
        component_type: str, # Например, "воздуховод", "поворот", "Клапан КР-450"
        exact_target_section_pair: Optional[Tuple[int, int]] = None, # Для точного поиска по сечению WxH или DxD
        section_filter_dim: Optional[int] = None # Альтернатива, если exact_target_section_pair не задан (фильтр по одной стороне/диаметру)
    ) -> Dict[str, Any]:
        """
        Подбирает оптимальный набор компонентов для одного элемента (воздуховода или фитинга)
        с использованием алгоритма динамического программирования (ДП).
        Эта функция НЕ пытается сама искать альтернативные сечения.

        :param required_value: Требуемая длина (мм) или количество (шт).
        :param component_type: Тип/название компонента для поиска в каталоге.
        :param exact_target_section_pair: Точное сечение (W,H) или (D,D), если оно известно и требуется.
        :param section_filter_dim: Фильтр по одному из размеров сечения, если точная пара не задана.
        :return: Словарь с результатами подбора для этого элемента.
        """
        logger.debug(f"Селектор.find_optimal_components_for_item: зн={required_value}, тип='{component_type}', точное_сеч={exact_target_section_pair}, фильтр_сеч={section_filter_dim}")
        try:
            self._validate_input_for_item_selection(required_value, component_type, exact_target_section_pair, section_filter_dim)
        except ValueError as e:
            logger.error(f"Селектор.find_optimal_components_for_item: Ошибка валидации: {e}")
            return {"components": {}, "total_cost": 0.0, "total_value": 0, "message": str(e)}

        suitable_items = self._filter_components_for_item_selection(component_type, exact_target_section_pair, section_filter_dim)
        
        if not suitable_items:
            msg = f"Нет подходящих компонентов в каталоге для ДП (тип='{component_type}', точное_сеч={exact_target_section_pair}, фильтр_сеч={section_filter_dim})."
            logger.warning(f"Селектор.find_optimal_components_for_item: {msg}")
            return {"components": {}, "total_cost": 0.0, "total_value": 0, "message": msg}

        # Алгоритм Динамического Программирования
        dp_costs = [float('inf')] * (required_value + 1)
        dp_costs[0] = 0.0
        dp_combination: List[Dict[str, int]] = [{} for _ in range(required_value + 1)]

        for item in suitable_items:
            item_name = item["name"]
            item_unit_val = item["unit_value"]       # Длина отрезка / 1000мм (метр) / 1шт
            item_cost_per_unit = item["cost_per_unit_value"] # Цена за этот item_unit_val

            if item_unit_val <= 0: continue # Пропускаем невалидные

            for current_dp_val in range(item_unit_val, required_value + 1):
                if dp_costs[current_dp_val - item_unit_val] == float('inf'):
                    continue # Предыдущее состояние недостижимо

                potential_new_cost = dp_costs[current_dp_val - item_unit_val] + item_cost_per_unit
                if potential_new_cost < dp_costs[current_dp_val]:
                    dp_costs[current_dp_val] = potential_new_cost
                    # Обновляем комбинацию
                    prev_combo = dp_combination[current_dp_val - item_unit_val]
                    current_combo = prev_combo.copy()
                    current_combo[item_name] = current_combo.get(item_name, 0) + 1
                    dp_combination[current_dp_val] = current_combo
        
        if dp_costs[required_value] == float('inf'):
            msg = f"Не удалось достичь требуемого значения {required_value} с помощью ДП для (тип='{component_type}', точное_сеч={exact_target_section_pair}, фильтр_сеч={section_filter_dim})."
            logger.warning(f"Селектор.find_optimal_components_for_item: {msg}")
            return {"components": {}, "total_cost": 0.0, "total_value": 0, "message": msg}

        # Успешный подбор
        selected_for_item = dp_combination[required_value]
        total_cost_for_item = dp_costs[required_value]
        
        # Расчет фактически набранного значения (может быть > required_value, если unit_value не делит нацело)
        # Но ДП должно было найти точное значение required_value, если оно достижимо.
        # Здесь total_value будет равен required_value, если ДП сработало для него.
        # Если мы хотим разрешить ДП набирать "с избытком", логика ДП должна быть чуть другой.
        # Пока считаем, что ДП находит решение для ТОЧНО required_value.
        achieved_value = 0
        for name, count in selected_for_item.items():
            s_item = next((s for s in suitable_items if s["name"]==name), None)
            if s_item: achieved_value += s_item["unit_value"]*count
            else: logger.error(f"КРИТИКА: Компонент {name} не найден в suitable_items при расчете achieved_value!")


        msg = f"Подбор для элемента успешен (тип='{component_type}', точное_сеч={exact_target_section_pair}, фильтр_сеч={section_filter_dim})."
        logger.info(f"Селектор.find_optimal_components_for_item: {msg}")
        return {
            "components": selected_for_item,
            "total_cost": total_cost_for_item,
            "total_value": achieved_value, # Должно быть равно required_value, если dp_costs[required_value] не inf
            "message": msg,
            "selected_section_if_applicable": exact_target_section_pair or \
                                             ( (section_filter_dim, section_filter_dim) if section_filter_dim and \
                                               any(item['effective_section_size'] == (section_filter_dim,section_filter_dim) for item in suitable_items if item['name'] in selected_for_item) \
                                               else "N/A") # Информация о сечении, для которого был сделан подбор
        }


class VentilationSystemGraphOptimizer:
    """
    Класс для обработки графа вентиляционной системы и подбора всех необходимых комплектующих.
    """
    def __init__(self, components_data: Dict[str, Tuple[str, str, Optional[str], Optional[float], Optional[str]]]):
        """
        Инициализирует оптимизатор графа.

        :param components_data: Словарь-каталог комплектующих.
        """
        self.components_catalog = components_data
        self.selector = ComponentSelector(components_data) # Экземпляр для подбора отдельных элементов
        
        self.overall_selected_components: Dict[str, int] = {} # Итоговый набор {название: общее_количество}
        self.overall_total_cost: float = 0.0
        self.processing_log: List[str] = [] # Лог обработки графа

        logger.info("VentilationSystemGraphOptimizer инициализирован.")

    def _add_to_overall_results(self, item_name_for_log: str, selection_result: Dict[str, Any]):
        """
        Добавляет результаты подбора одного элемента (ребра или узла) к общим итогам.

        :param item_name_for_log: Имя обрабатываемого элемента графа (для лога).
        :param selection_result: Словарь, возвращаемый `ComponentSelector.find_optimal_components_for_item`.
        """
        if selection_result.get("components"):
            components_found = selection_result["components"]
            cost_found = selection_result.get("total_cost", 0.0)
            for name, count in components_found.items():
                self.overall_selected_components[name] = self.overall_selected_components.get(name, 0) + count
            self.overall_total_cost += cost_found
            log_msg = f"Успех для '{item_name_for_log}': {components_found}, стоимость {cost_found:.2f}. {selection_result.get('message', '')}"
            self.processing_log.append(log_msg)
            logger.info(log_msg)
        else:
            log_msg = f"НЕУДАЧА для '{item_name_for_log}': {selection_result.get('message', 'Нет компонентов или не удалось подобрать')}"
            self.processing_log.append(log_msg)
            logger.warning(log_msg)


    def _get_fitting_details_from_node(self, graph: nx.Graph, node_id: Any) -> \
                                        Tuple[Optional[str], Optional[Tuple[int,int]], Optional[Any]]:
        """
        Определяет тип фитинга и его ключевые характеристики для узла графа.
        Это упрощенная ЗАГЛУШКА и требует значительной доработки под вашу структуру атрибутов графа.

        :param graph: Граф системы.
        :param node_id: ID текущего узла.
        :return: Кортеж (fitting_type_keyword, target_section_for_fitting, additional_spec (e.g., angle)).
        """
        node_data = graph.nodes[node_id]
        node_attr_type = node_data.get('type', 'unknown').lower() # Атрибут узла, например, "turn", "tee"
        
        # Пытаемся получить сечение из атрибутов узла или из первого смежного ребра
        target_section: Optional[Tuple[int,int]] = node_data.get('section')
        if not target_section:
            connected_edges = list(graph.edges(node_id, data=True))
            if connected_edges:
                first_edge_data = connected_edges[0][2] # Данные первого ребра
                target_section = first_edge_data.get('section')
                if not (isinstance(target_section, tuple) and len(target_section) == 2):
                    target_section = None # Если сечение ребра некорректно
            if not target_section: # Если и в узле нет, и у ребер нет
                logger.warning(f"Граф.Узел {node_id} ({node_attr_type}): не удалось определить целевое сечение.")
                return None, None, None
        
        target_section = cast(Optional[Tuple[int,int]], target_section)


        if node_attr_type == 'turn':
            angle = node_data.get('angle', 90) # По умолчанию 90 градусов
            # Ключевое слово для поиска в каталоге (может быть "поворот" или "отвод")
            # Для простоты используем "поворот". В каталоге могут быть оба.
            return "поворот", target_section, angle
        
        elif node_attr_type == 'tee':
            # Подбор тройника сложен: требует знания всех 3-х сечений.
            # Текущий ComponentSelector не поддерживает это напрямую.
            # Эта часть требует значительной доработки.
            logger.warning(f"Граф.Узел {node_id} (тройник): Автоматический подбор тройников требует сложной логики и пока не полностью реализован.")
            # Можно попытаться найти тройник по основному сечению, если каталог это позволяет
            return "тройник", target_section, None 
            
        elif node_attr_type == 'transition':
            # Подбор перехода также сложен. Нужны section_from и section_to.
            # Атрибуты узла должны содержать 'section_from' и 'section_to', либо их нужно вывести из ребер.
            logger.warning(f"Граф.Узел {node_id} (переход): Автоматический подбор переходов требует сложной логики и пока не полностью реализован.")
            # Можно попытаться найти общий "переход" по primary_section, если есть такие в каталоге.
            return "переход", target_section, None

        elif node_attr_type == 'equipment' and node_data.get('model'):
            # Если это оборудование с известной моделью, ищем его по имени модели
            return node_data.get('model'), target_section, None # Сечение может быть важно для подключения
        
        elif node_attr_type in self.selector.fittings: # Если тип узла - это общий тип фитинга
             return node_attr_type, target_section, node_data.get('angle') # Угол может быть релевантен

        logger.warning(f"Граф.Узел {node_id}: тип фитинга '{node_attr_type}' не распознан или логика подбора не реализована.")
        return None, None, None


    def process_ventilation_system_graph(self, graph: nx.Graph) -> Dict[str, Any]:
        """
        Обрабатывает граф вентиляционной системы, подбирая все необходимые компоненты.

        :param graph: Граф `networkx.Graph`, описывающий систему.
                      Атрибуты ребер: `length` (int, мм), `section` (Tuple[int,int]).
                      Атрибуты узлов: `type` (str), `angle` (int, optional), `model` (str, optional), 
                                      `section` (Tuple[int,int], optional - для фитингов, если известно).
        :return: Словарь с общей спецификацией, стоимостью и логом обработки.
        """
        logger.info(f"Начало обработки графа системы: {len(graph.nodes)} узлов, {len(graph.edges)} ребер.")
        self.overall_selected_components.clear()
        self.overall_total_cost = 0.0
        self.processing_log.clear()
        self.processing_log.append("--- Начало обработки графа ---")

        # --- 1. Обработка РЁБЕР (подбор воздуховодов) ---
        self.processing_log.append("\n--- Обработка РЁБЕР (воздуховодов) ---")
        logger.info("--- Обработка РЁБЕР (воздуховодов) ---")
        for u, v, edge_data in graph.edges(data=True):
            edge_id_str = f"Ребро ({u}-{v})"
            logger.info(f"Обработка: {edge_id_str}, данные: {edge_data}")

            required_length = edge_data.get('length')
            target_section_tuple = edge_data.get('section')

            if not (isinstance(required_length, int) and required_length > 0):
                self.processing_log.append(f"ОШИБКА {edge_id_str}: невалидная длина {required_length}.")
                logger.error(f"{edge_id_str}: невалидная длина {required_length}.")
                continue
            if not (isinstance(target_section_tuple, tuple) and len(target_section_tuple) == 2 and
                    all(isinstance(d, int) and d > 0 for d in target_section_tuple)):
                self.processing_log.append(f"ОШИБКА {edge_id_str}: невалидное сечение {target_section_tuple}.")
                logger.error(f"{edge_id_str}: невалидное сечение {target_section_tuple}.")
                continue
            
            target_section = cast(Tuple[int,int], target_section_tuple)

            logger.debug(f"{edge_id_str}: Попытка подбора воздуховода для точного сечения {target_section}, длина {required_length}мм.")
            duct_result = self.selector.find_optimal_components_for_item(
                required_value=required_length,
                component_type="воздуховод",
                exact_target_section_pair=target_section
            )

            if duct_result.get("components"):
                self._add_to_overall_results(f"{edge_id_str} с сечением {target_section}", duct_result)
            else:
                self.processing_log.append(f"ПРЕДУПРЕЖДЕНИЕ {edge_id_str}: для точного сечения {target_section} воздуховод не подобран. Поиск ближайшего большего...")
                logger.warning(f"{edge_id_str}: Подбор для точного сечения {target_section} не удался. Ищем ближайшее большее.")
                
                # target_L, target_W_nullable
                # Если target_section это (D,D), то target_W_nullable=None, target_L=D
                # Если target_section это (W,H), то target_L=W, target_W_nullable=H
                search_L = target_section[0]
                search_W = target_section[1] if target_section[0] != target_section[1] else None
                
                larger_concrete_section = self.selector.find_nearest_larger_concrete_section(search_L, search_W)
                
                if larger_concrete_section:
                    self.processing_log.append(f"ИНФО {edge_id_str}: Найдено ближайшее большее сечение {larger_concrete_section}. Повторный подбор.")
                    logger.info(f"{edge_id_str}: Используется большее сечение {larger_concrete_section} вместо {target_section}.")
                    
                    duct_result_larger = self.selector.find_optimal_components_for_item(
                        required_value=required_length,
                        component_type="воздуховод",
                        exact_target_section_pair=larger_concrete_section
                    )
                    self._add_to_overall_results(f"{edge_id_str} с альт. сечением {larger_concrete_section}", duct_result_larger)
                else:
                    self.processing_log.append(f"ОШИБКА {edge_id_str}: ближайшее большее сечение для {target_section} не найдено.")
                    logger.error(f"{edge_id_str}: Ближайшее большее сечение для {target_section} не найдено.")
        
        # --- 2. Обработка УЗЛОВ (подбор фитингов/оборудования) ---
        self.processing_log.append("\n--- Обработка УЗЛОВ (фитинги, оборудование) ---")
        logger.info("--- Обработка УЗЛОВ (фитинги, оборудование) ---")
        for node_id, node_data in graph.nodes(data=True):
            node_id_str = f"Узел ({node_id} - {node_data.get('label', node_data.get('type','unknown'))})"
            logger.info(f"Обработка: {node_id_str}, данные узла: {node_data}")

            # Получаем тип фитинга, целевое сечение и доп. спецификации из узла
            fitting_type_keyword, target_section_for_fitting, additional_spec = self._get_fitting_details_from_node(graph, node_id)

            if not fitting_type_keyword or not target_section_for_fitting:
                self.processing_log.append(f"ИНФО {node_id_str}: не удалось определить фитинг/оборудование или его основное сечение. Узел пропущен для подбора компонентов.")
                logger.info(f"{node_id_str}: пропуск, т.к. не определен фитинг/оборудование или основное сечение.")
                continue
            
            required_quantity = 1 # Обычно фитинги и оборудование подбираются поштучно

            # Формируем component_type для селектора: может быть общим (fitting_type_keyword)
            # или специфичным (модель оборудования из node_data)
            component_name_or_type_for_search = node_data.get('model') or fitting_type_keyword

            logger.debug(f"{node_id_str}: Попытка подбора: тип/модель='{component_name_or_type_for_search}', сечение={target_section_for_fitting}, кол-во={required_quantity}, доп.спец={additional_spec}.")
            
            fitting_result = self.selector.find_optimal_components_for_item(
                required_value=required_quantity,
                component_type=component_name_or_type_for_search,
                exact_target_section_pair=target_section_for_fitting
                # section_filter_dim можно было бы использовать, если exact_target_section_pair не полностью определен,
                # но для фитингов обычно нужно точное сечение.
            )
            
            # Дополнительная логика для отводов, если есть 'angle'
            if fitting_type_keyword == "поворот" and additional_spec is not None: # additional_spec это угол
                # В _filter_components_for_item_selection нужно будет добавить проверку угла,
                # если 'component_type_request' это "поворот".
                # Например, искать в характеристиках компонента "угол 90°".
                # Текущая _filter_components_for_item_selection этого не делает.
                # Это требует доработки фильтра или более умного формирования component_type_request,
                # например, "поворот 90°"
                pass # Пока эта логика не добавлена в фильтр.

            if fitting_result.get("components"):
                self._add_to_overall_results(f"{node_id_str} ({component_name_or_type_for_search} сеч. {target_section_for_fitting})", fitting_result)
            else:
                self.processing_log.append(f"ПРЕДУПРЕЖДЕНИЕ {node_id_str}: для {component_name_or_type_for_search} сечением {target_section_for_fitting} не найдено/не подобрано. Поиск ближайшего большего...")
                logger.warning(f"{node_id_str}: Подбор для {component_name_or_type_for_search} с точным сечением {target_section_for_fitting} не удался.")

                # Попытка найти с ближайшим большим (только для типов, где это осмысленно)
                if fitting_type_keyword in ["поворот", "отвод", "клапан", "фильтр", "насадок", "зонт", "дефлектор", "заглушка", "ниппель", "муфта"]:
                    search_L_fit = target_section_for_fitting[0]
                    search_W_fit = target_section_for_fitting[1] if target_section_for_fitting[0] != target_section_for_fitting[1] else None
                    larger_s_fit = self.selector.find_nearest_larger_concrete_section(search_L_fit, search_W_fit)
                    
                    if larger_s_fit:
                        self.processing_log.append(f"ИНФО {node_id_str}: Для {component_name_or_type_for_search} найдено большее сечение {larger_s_fit}. Повторный подбор...")
                        logger.info(f"{node_id_str}: Используется большее сечение {larger_s_fit} вместо {target_section_for_fitting}.")
                        fitting_result_larger = self.selector.find_optimal_components_for_item(
                            required_value=required_quantity,
                            component_type=component_name_or_type_for_search,
                            exact_target_section_pair=larger_s_fit
                        )
                        self._add_to_overall_results(f"{node_id_str} ({component_name_or_type_for_search} альт.сеч. {larger_s_fit})", fitting_result_larger)
                    else:
                        self.processing_log.append(f"ОШИБКА {node_id_str}: для {component_name_or_type_for_search} ({target_section_for_fitting}) ближайшее большее сечение не найдено.")
                        logger.error(f"{node_id_str}: Ближайшее большее сечение для фитинга {fitting_type_keyword} ({target_section_for_fitting}) не найдено.")
        
        self.processing_log.append("\n--- Обработка графа завершена ---")
        logger.info("--- Обработка графа вентиляционной системы завершена ---")
        return {
            "overall_selected_components": self.overall_selected_components,
            "overall_total_cost": self.overall_total_cost,
            "processing_log": self.processing_log
        }

    def generate_overall_bill_of_materials(self) -> str:
        """
        Генерирует итоговую спецификацию на основе всех подобранных компонентов для графа.
        Использует `self.overall_selected_components` и `self.overall_total_cost`.

        :return: Строка с отформатированной общей спецификацией.
        """
        if not self.overall_selected_components:
            logger.warning("Общая спецификация: Комплектующие не были подобраны (overall_selected_components пуст).")
            return "Итоговый набор комплектующих для системы пуст. Проверьте лог обработки."

        bill = "ИТОГОВАЯ СПЕЦИФИКАЦИЯ КОМПЛЕКТУЮЩИХ ДЛЯ СИСТЕМЫ ВЕНТИЛЯЦИИ:\n"
        bill += "=" * 80 + "\n"
        
        item_num = 1
        for name, count in self.overall_selected_components.items():
            # Получаем детали компонента из исходного каталога для отображения
            comp_data_from_catalog = self.components_catalog.get(name)
            
            if not comp_data_from_catalog:
                logger.error(f"Спецификация: Компонент '{name}' из общего набора не найден в исходном каталоге.")
                bill += f"{item_num}. {name} (ДЕТАЛИ ИЗ КАТАЛОГА НЕ НАЙДЕНЫ!) — {count} шт.\n"
            else:
                size_str, material, characteristics, cost_raw, standard = comp_data_from_catalog
                price_display = f"{cost_raw:.2f} руб." if cost_raw is not None else "N/A"
                
                bill_line = f"{item_num}. {name}\n"
                bill_line += f"   Характеристики из каталога: Размер: {size_str}, Материал: {material or 'N/A'}, Доп: {characteristics or 'N/A'}\n"
                # `count` здесь - это общее количество штук или суммарная длина в "единицах подбора" (например, метрах для воздуховодов, если unit_value=1000)
                # Для корректного отображения "шт." или "м.п." нужна доп. информация о том, как считался `count` для этого `name`.
                # Текущий `_add_to_overall_results` просто суммирует `count` из результатов ДП.
                # Если ДП вернуло { "воздуховод А": 3 } где 3 - это 3 метра, то тут будет 3.
                # Если ДП вернуло { "отвод Б": 2 } где 2 - это 2 штуки, то тут будет 2.
                # Единица измерения для `count` зависит от `unit_value` конкретного компонента, который использовался в ДП.
                # Это усложняет простое отображение. Пока оставим "шт." как наиболее общее, но это требует внимания.
                bill_line += f"   Общее количество/длина (в ед. подбора): {count} (Цена за ед. по каталогу: {price_display})\n"
                bill_line += "-" * 80 + "\n"
                bill += bill_line
            item_num += 1

        bill += "=" * 80 + "\n"
        bill += f"ОБЩАЯ РАСЧЕТНАЯ СТОИМОСТЬ ВСЕХ КОМПОНЕНТОВ СИСТЕМЫ: {self.overall_total_cost:.2f} руб.\n"
        logger.info("Итоговая спецификация комплектующих для системы успешно сформирована.")
        return bill


# ----- Пример использования -----
if __name__ == '__main__':

    graph_builder_optimizer = VentilationSystemGraphOptimizer(components)

    # 1. Пример графа №1: Простая система
    g1 = nx.Graph()
    g1.add_node("start_point", type="inlet", label="Начало системы")
    g1.add_node("turn1", type="turn", angle=90, label="Поворот 1") # Сечение будет выведено из ребер
    g1.add_node("end_point", type="outlet", label="Конец системы (решетка)")
    
    g1.add_edge("start_point", "turn1", length=2200, section=(500, 300)) # Прямоугольный воздуховод
    g1.add_edge("turn1", "end_point", length=1500, section=(500, 300))   # Прямоугольный воздуховод
    
    logger.info("\n--- ПРИМЕР 1: Обработка простого графа ---")
    system_results_g1 = graph_builder_optimizer.process_ventilation_system_graph(g1)
    
    print("\n--- Лог обработки для Примера 1: ---")
    for log_entry in system_results_g1.get("processing_log", []):
        print(log_entry)
    print("\n--- Итоговая спецификация для Примера 1: ---")
    print(graph_builder_optimizer.generate_overall_bill_of_materials())

    # 2. Пример графа №2: С круглыми воздуховодами и возможным поиском большего сечения
    g2 = nx.Graph()
    # Узлы: оборудование и точки соединения
    g2.add_node("fan_out", type="equipment_outlet", model="Вентилятор ВК-150", label="Выход вентилятора") # Предположим, сечение выхода ø150
    g2.add_node("duct_conn1", type="duct_splice", label="Соединение воздуховодов")
    g2.add_node("diffuser_in", type="diffuser_inlet", model="Диффузор ДП-160", label="Вход диффузора")

    # Рёбра:
    # Этот воздуховод должен быть ø150 (от вентилятора)
    g2.add_edge("fan_out", "duct_conn1", length=5000, section=(150, 150)) 
    # Этот воздуховод запрашивается как ø160. Если в каталоге нет воздуховода ø160,
    # должен найтись ближайший больший (например, ø200, если он есть)
    g2.add_edge("duct_conn1", "diffuser_in", length=3000, section=(160, 160)) 

    # Для теста, убедимся, что в example_components_catalog нет воздуховода ø160,
    # но есть, например, ø150 и ø200.
    # (Предположим, что ваш components.py это обеспечивает)

    logger.info("\n--- ПРИМЕР 2: Граф с круглыми воздуховодами и поиском большего сечения ---")
    system_results_g2 = graph_builder_optimizer.process_ventilation_system_graph(g2) # Используем тот же экземпляр

    print("\n--- Лог обработки для Примера 2: ---")
    for log_entry in system_results_g2.get("processing_log", []):
        print(log_entry)
    print("\n--- Итоговая спецификация для Примера 2: ---")
    print(graph_builder_optimizer.generate_overall_bill_of_materials())