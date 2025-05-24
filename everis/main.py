import re
from typing import Dict, List, Tuple, Optional
from date.components import components

class VentilationSystemOptimizer:
    def __init__(self, components: Dict[str, Tuple]):
        """
        Инициализация с загрузкой данных о комплектующих.
        
        :param components: Словарь комплектующих в формате:
            {
                "название": ("размер", "материал", "характеристики", стоимость, "стандарт"),
                ...
            }
        """
        self.components = components
        self.selected_components = []
        self.total_cost = 0

    def parse_size(self, size_str: str) -> Optional[Tuple[int, int]]:
        """
        Парсит строку с размерами в кортеж (ширина, высота) для прямоугольных или (диаметр, диаметр) для круглых.
        
        Примеры:
            "500x800 мм" -> (500, 800)
            "ø450 мм" -> (450, 450)
        """
        if not size_str:
            return None

        # Прямоугольные: "500x800 мм"
        match_rect = re.match(r"(\d+)x(\d+)\s*мм", size_str)
        if match_rect:
            return (int(match_rect.group(1)), int(match_rect.group(2)))

        # Круглые: "ø450 мм"
        match_circle = re.match(r"ø(\d+)\s*мм", size_str)
        if match_circle:
            diameter = int(match_circle.group(1))
            return (diameter, diameter)

        return None

    def calculate_area(self, size: Tuple[int, int]) -> int:
        """Вычисляет площадь сечения (для сравнения пропускной способности)."""
        return size[0] * size[1]

    def find_optimal_components(
        self,
        required_length: int,
        required_width: Optional[int] = None,
        component_type: str = "воздуховод"
    ) -> Dict:
        """
        Подбирает комплектующие для покрытия заданных размеров с минимальной стоимостью.
        
        :param required_length: Требуемая длина (мм)
        :param required_width: Требуемая ширина (мм) — если None, игнорируется
        :param component_type: Тип компонента ("воздуховод", "отвод", и т.д.)
        :return: Словарь с результатами:
            {
                "selected_components": List[Dict],  # Выбранные компоненты
                "total_cost": float,               # Общая стоимость
                "total_length": int                # Суммарная длина
            }
        """
        self.selected_components = []
        self.total_cost = 0
        remaining_length = required_length

        # Фильтруем подходящие компоненты
        suitable_components = []
        for name, data in self.components.items():
            if component_type not in name.lower():
                continue

            size = self.parse_size(data[0])
            if not size:
                continue

            # Проверка на соответствие ширине (если задана)
            if required_width and size[1] != required_width:
                continue

            cost = data[3] if data[3] is not None else 0
            suitable_components.append({
                "name": name,
                "size": size,
                "cost": cost,
                "cost_per_mm": cost / size[0]  # Стоимость за мм длины
            })

        # Сортируем по удельной стоимости (дешевле сначала)
        suitable_components.sort(key=lambda x: x["cost_per_mm"])

        # Жадный алгоритм: берём самые дешёвые компоненты
        for item in suitable_components:
            while remaining_length >= item["size"][0]:
                self.selected_components.append(item["name"])
                self.total_cost += item["cost"]
                remaining_length -= item["size"][0]

        # Если остался "хвост", добавляем минимально подходящий компонент
        if remaining_length > 0:
            best_fit = None
            for item in suitable_components:
                if item["size"][0] >= remaining_length:
                    if best_fit is None or item["cost"] < best_fit["cost"]:
                        best_fit = item

            if best_fit:
                self.selected_components.append(best_fit["name"])
                self.total_cost += best_fit["cost"]
                remaining_length = 0

        return {
            "selected_components": self.selected_components,
            "total_cost": self.total_cost,
            "total_length": required_length - remaining_length
        }

    def generate_bill_of_materials(self) -> str:
        """Генерирует текстовую спецификацию подобранных компонентов."""
        if not self.selected_components:
            return "Комплектующие не подобраны."

        bill = "СПЕЦИФИКАЦИЯ:\n"
        bill += "=" * 50 + "\n"
        
        # Группируем компоненты по названию и считаем количество
        component_counts = {}
        for name in self.selected_components:
            component_counts[name] = component_counts.get(name, 0) + 1

        for name, count in component_counts.items():
            size = self.components[name][0]
            cost = self.components[name][3] or 0
            bill += f"{name} ({size}) — {count} шт. = {cost * count} руб.\n"

        bill += "=" * 50 + "\n"
        bill += f"ИТОГО: {self.total_cost} руб.\n"
        return bill
    

# Инициализация
optimizer = VentilationSystemOptimizer(components)

# Подбор воздуховодов для участка длиной 10 000 мм и шириной 800 мм
result = optimizer.find_optimal_components(
    required_length=10000,
    required_width=800,
    component_type="воздуховод"
)

# Вывод результатов
print("Подобранные компоненты:", result["selected_components"])
print("Общая стоимость:", result["total_cost"], "руб.")
print("Суммарная длина:", result["total_length"], "мм")

# Генерация спецификации
print(optimizer.generate_bill_of_materials())