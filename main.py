import sys
import os
import requests
import logging
import yaml
from yaml import SafeLoader
import time
from datetime import timedelta
from fake_useragent import UserAgent
from PyQt5.QtWidgets import QMainWindow, QApplication, QPushButton, QTextEdit, QLineEdit, QFileDialog
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt, pyqtSignal, QObject, QThread

wersja = "0.1.2"

# Logo.
logo = """
██╗ ██╗███████╗██╗ ██╗ ██████╗ ██████╗ ████████╗
██║ ██╔╝██╔════╝╚██╗ ██╔╝ ██╔══██╗██╔═══██╗╚══██╔══╝
█████╔╝ █████╗ ╚████╔╝█████╗██████╔╝██║ ██║ ██║ 
██╔═██╗ ██╔══╝ ╚██╔╝ ╚════╝██╔══██╗██║ ██║ ██║ 
██║ ██╗███████╗ ██║ ██████╔╝╚██████╔╝ ██║ 
╚═╝ ╚═╝╚══════╝ ╚═╝ ╚═════╝ ╚═════╝ ╚═╝ 
"""

# Default config file.
default_config = """
# Konfig battle bota
bearer_token: ""
sleep_interval: 1
ticket_cost_threshold: 1000
ratelimit_sleep: 15
"""

# Clear the console.
clear = lambda: os.system("cls" if os.name in ("nt", "dos") else "clear")

# Set the console title.
os.system(f"title Key-Bot")


class BattleBot(QObject):
    log_update = pyqtSignal(str)

    def __init__(self, bearer_token, sleep_interval=1, ticket_cost_threshold=1000):
        super().__init__()
        self.session = requests.Session()
        self.user_agent = UserAgent()
        self.session.headers.update({
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate",
            "Accept-Language": "en-US,en;q=0.9",
            "Connection": "keep-alive",
            "Host": "kdrp2.com",
            "Origin": "https://key-drop.com",
            "Referer": "https://key-drop.com/",
            "authorization": f"Bearer {bearer_token}",
            "User-Agent": self.user_agent.random
        })
        self.base_url = "https://kdrp2.com/CaseBattle/"
        self.active_battles_url = f"{self.base_url}battle?type=active&page=0&priceFrom=0&priceTo=0.29&searchText=&sort=priceAscending&players=all&roundsCount=all"
        self.join_battle_url = f"{self.base_url}joinCaseBattle/"
        self.sleep_interval = sleep_interval
        self.ticket_cost_threshold = ticket_cost_threshold

    def load_config(self):
        try:
            with open("config.yaml", "r") as f:
                config = yaml.load(f, Loader=SafeLoader)
                self.bearer_token = config.get("bearer_token", "")
                self.sleep_interval = config.get("sleep_interval", 1)
                self.ticket_cost_threshold = config.get("ticket_cost_threshold", 1000)
                self.ratelimit_sleep = config.get("ratelimit_sleep", 15)
        except Exception as e:
            self.log_update.emit(f"<span style='color: red'>Błąd wczytywania pliku konfiguracyjnego:</span> {e}")

    def save_config(self):
        try:
            config = {
                "bearer_token": self.bearer_token,
                "sleep_interval": self.sleep_interval,
                "ticket_cost_threshold": self.ticket_cost_threshold,
                "ratelimit_sleep": self.ratelimit_sleep
            }
            with open("config.yaml", "w") as f:
                yaml.dump(config, f)
                self.log_update.emit(f"<span style='color: green'>Konfiguracja została zapisana do pliku config.yaml</span>")
        except Exception as e:
            self.log_update.emit(f"<span style='color: red'>Błąd zapisu pliku konfiguracyjnego:</span> {e}")

    def join_battles(self):
        while True:
            try:
                response = self.session.get(self.active_battles_url)
                if response.status_code == 200:
                    data = response.json()
                    battles = data.get("battles", [])
                    for battle in battles:
                        battle_id = battle.get("id")
                        ticket_cost = battle.get("ticketCost")
                        if ticket_cost <= self.ticket_cost_threshold:
                            join_data = {
                                "caseBattleId": battle_id,
                                "team": "a"
                            }
                            response = self.session.post(self.join_battle_url, json=join_data)
                            if response.status_code == 200:
                                self.log_update.emit(f"Znaleziono darmową bitwę o ID: {battle_id}")
                                self.log_update.emit(f"Skrzynka: {battle.get('name')}")
                                self.log_update.emit("Próbuję dołączyć do bitwy")
                            else:
                                self.log_update.emit(f"<span style='color: red'>Błąd podczas dołączania do bitwy: {battle_id}</span>")
                        else:
                            self.log_update.emit(f"Koszt bitwy zbyt wysoki: {battle_id}")
                else:
                    self.log_update.emit(f"<span style='color: red'>Błąd podczas pobierania aktywnych bitew</span>")
            except Exception as e:
                self.log_update.emit(f"<span style='color: red'>Błąd podczas dołączania do bitew:</span> {e}")

            time.sleep(self.sleep_interval)

    def start(self):
        self.log_update.emit(f"<span style='color: green'>Key-Bot wersja {wersja} by legolasek</span>")
        self.log_update.emit(f"<span style='color: green'>Aby zatrzymać program, naciśnij CTRL+C</span>")
        self.join_battles()


class BattleBotApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Key-Bot")
        self.setWindowIcon(QIcon("icon.png"))
        self.setGeometry(100, 100, 400, 500)
        self.setFixedSize(400, 700)
        self.setStyleSheet("background-color: #222; color: #FFF; font-size: 16px;")
        self.init_ui()

    def init_ui(self):
        self.status_bar = self.statusBar()
        self.status_bar.setStyleSheet("color: #FFF; font-size: 14px;")
        self.status_bar.showMessage("Key-Bot v" + wersja + " by legolasek", 5000)

        self.token_input = QLineEdit(self)
        self.token_input.setGeometry(20, 420, 360, 30)
        self.token_input.setStyleSheet("background-color: #FFF; color: #000; font-size: 14px;")

        self.log_output = QTextEdit(self)
        self.log_output.setGeometry(20, 20, 360, 380)
        self.log_output.setStyleSheet("background-color: #000; color: #FFF; font-size: 12px;")
        self.log_output.setReadOnly(True)

        self.clear_log_button = QPushButton("Wyczyść log", self)
        self.clear_log_button.setGeometry(20, 420, 160, 60)
        self.clear_log_button.setStyleSheet("background-color: #444; color: #FFF; font-size: 16px;")
        self.clear_log_button.clicked.connect(self.clear_log)

        self.save_config_button = QPushButton("Zapisz konfigurację", self)
        self.save_config_button.setGeometry(220, 420, 160, 60)
        self.save_config_button.setStyleSheet("background-color: #444; color: #FFF; font-size: 16px;")
        self.save_config_button.clicked.connect(self.save_config)

        self.load_config_button = QPushButton("Wczytaj konfigurację", self)
        self.load_config_button.setGeometry(20, 480, 160, 60)
        self.load_config_button.setStyleSheet("background-color: #444; color: #FFF; font-size: 16px;")
        self.load_config_button.clicked.connect(self.load_config)

        self.start_button = QPushButton("Start", self)
        self.start_button.setGeometry(220, 480, 160, 60)
        self.start_button.setStyleSheet("background-color: #080; color: #FFF; font-size: 24px;")
        self.start_button.clicked.connect(self.start_bot)

    def clear_log(self):
        self.log_output.clear()

    def save_config(self):
        self.bot.save_config()

    def load_config(self):
        self.bot.load_config()

    def start_bot(self):
        bearer_token = self.token_input.text()
        self.bot = BattleBot(bearer_token)
        self.bot.log_update.connect(self.update_log)
        self.bot_thread = QThread()
        self.bot.moveToThread(self.bot_thread)
        self.bot_thread.started.connect(self.bot.start)
        self.bot_thread.start()

    def update_log(self, text):
        self.log_output.append(text)


def main():
    app = QApplication(sys.argv)
    window = BattleBotApp()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
