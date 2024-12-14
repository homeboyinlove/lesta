from core import GameAPI
from constants import Sprite
from PyQt5.QtGui import QVector2D
import random

class Game(object):
    def __init__(self):
        self.ships = []  # Все корабли на поле
        self.islands = []  # Острова на поле
        self.current_team = "green"  # Текущая команда
        self.selected_ship = None  # Выбранный корабль

    def start(self, api: GameAPI) -> None:
        api.addMessage("Игра началась!")

        # Расположение кораблей команд
        green_positions = [(0, 1), (0, 3), (0, 5)]
        red_positions = [(6, 1), (6, 3), (6, 5)]

        green_names = ["Medea", "Weymouth", "Iron Duke"]
        red_names = ["G-101", "Kolberg", "Koening"]

        # Создание зелёной команды
        for i, position in enumerate(green_positions):
            ship = {
                "team": "green",
                "type": ["destroyer", "cruiser", "battleship"][i],
                "name": green_names[i],
                "marker": api.addMarker(Sprite.GREEN_TEAM[i], *position),
                "health": [15, 30, 50][i],
                "damage": [30, 15, 20][i],
                "speed": [4, 3, 2][i],
                "position": QVector2D(*position),
            }
            self.ships.append(ship)

        # Создание красной команды
        for i, position in enumerate(red_positions):
            ship = {
                "team": "red",
                "type": ["destroyer", "cruiser", "battleship"][i],
                "name": red_names[i],
                "marker": api.addMarker(Sprite.RED_TEAM[i], *position),
                "health": [15, 30, 50][i],
                "damage": [30, 15, 20][i],
                "speed": [4, 3, 2][i],
                "position": QVector2D(*position),
            }
            self.ships.append(ship)

        # Распределение островов
        for i in range(15):
            x, y = random.randint(0, 6), random.randint(0, 6)
            if not self.is_occupied(QVector2D(x, y)):
                island_type = Sprite.CLIFF if random.random() < 0.5 else Sprite.ISLAND
                island = api.addImage(island_type, x, y)
                self.islands.append({"type": island_type, "image": island, "position": QVector2D(x, y)})

    def click(self, api: GameAPI, x: int, y: int) -> None:
        click_position = QVector2D(x, y)

        # Проверка на выбор корабля
        for ship in self.ships:
            if ship["position"] == click_position and ship["team"] == self.current_team:
                if self.selected_ship == ship:
                    self.selected_ship["marker"].setSelected(False)
                    self.selected_ship = None
                    api.addMessage("Снято выделение с корабля.")
                else:
                    if self.selected_ship:
                        self.selected_ship["marker"].setSelected(False)
                    self.selected_ship = ship
                    self.selected_ship["marker"].setSelected(True)
                    api.addMessage(f"Выбран корабль {ship['name']} команды {self.current_team} на позиции ({x}, {y}).")
                return

        # Если корабль уже выбран, проверяем возможность перемещения
        if self.selected_ship:
            distance = (self.selected_ship["position"] - click_position).length()
            if distance <= self.selected_ship["speed"] and not self.is_island(click_position):
                self.selected_ship["marker"].moveTo(x, y)
                self.selected_ship["position"] = click_position
                api.addMessage(f"Корабль {self.selected_ship['name']} перемещён на позицию ({x}, {y}).")

                # Атака после перемещения
                self.attack(api)

                # Смена хода
                self.end_turn(api)
            elif self.is_island(click_position):
                api.addMessage("Нельзя остановиться на позиции острова.")
            else:
                api.addMessage("Слишком далеко для перемещения.")

    def is_occupied(self, position: QVector2D) -> bool:
        for ship in self.ships:
            if ship["position"] == position:
                return True
        for island in self.islands:
            if island["position"] == position:
                return True
        return False

    def is_island(self, position: QVector2D) -> bool:
        for island in self.islands:
            if island["position"] == position:
                return True
        return False

    def is_low_island(self, position: QVector2D) -> bool:
        for island in self.islands:
            if island["position"] == position and island["type"] == Sprite.ISLAND:
                return True
        return False

    def attack(self, api: GameAPI) -> None:
        for attacker in self.ships:
            if attacker["team"] != self.current_team:
                continue

            targets = []
            for defender in self.ships:
                if defender["team"] == self.current_team:
                    continue

                # Логика атаки в зависимости от типа атакующего
                distance = (attacker["position"] - defender["position"]).length()
                path_clear = True

                if attacker["type"] == "destroyer" and distance <= 1:
                    # Эсминцы не могут стрелять через препятствия
                    for island in self.islands:
                        if self.is_between(attacker["position"], defender["position"], island["position"]):
                            path_clear = False
                            break
                    if path_clear:
                        targets.append(defender)

                elif attacker["type"] in ["cruiser", "battleship"] and (
                    attacker["position"].x() == defender["position"].x() or attacker["position"].y() == defender["position"].y()
                ):
                    # Проверяем вертикальную или горизонтальную атаку
                    for island in self.islands:
                        if self.is_between(attacker["position"], defender["position"], island["position"]) and not self.is_low_island(island["position"]):
                            path_clear = False
                            break
                    if path_clear:
                        targets.append(defender)

            # Нанесение урона целям
            if targets:
                damage = attacker["damage"] // len(targets)
                for target in targets:
                    effective_damage = damage
                    if target["type"] in ["cruiser", "destroyer"] and distance > 2:
                        effective_damage //= 2
                    if target["type"] == "battleship" and effective_damage <= 10:
                        effective_damage = 0
                    target["health"] -= effective_damage
                    target["marker"].setHealth(target["health"] / [15, 30, 50][["destroyer", "cruiser", "battleship"].index(target["type"])] * 1.0)

                    api.addMessage(f"Корабль {target['name']} ({target['type']}) команды {target['team']} получил {effective_damage} урона.")

                    # Удаление корабля, если здоровье <= 0
                    if target["health"] <= 0:
                        target["marker"].remove()
                        self.ships.remove(target)
                        api.addMessage(f"Корабль {target['name']} ({target['type']}) команды {target['team']} уничтожен.")

    def is_between(self, start: QVector2D, end: QVector2D, point: QVector2D) -> bool:
        if start.x() == end.x() == point.x() and min(start.y(), end.y()) < point.y() < max(start.y(), end.y()):
            return True
        if start.y() == end.y() == point.y() and min(start.x(), end.x()) < point.x() < max(start.x(), end.x()):
            return True
        return False

    def end_turn(self, api: GameAPI) -> None:
        self.current_team = "red" if self.current_team == "green" else "green"
        api.addMessage(f"Ход команды {self.current_team}.")

        # Сброс выделения корабля
        if self.selected_ship:
            self.selected_ship["marker"].setSelected(False)
            self.selected_ship = None
