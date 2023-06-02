import sys
import json
import os
import requests
import logging
import yaml
from time import sleep
from datetime import timedelta
from yaml import SafeLoader
from fake_useragent import UserAgent
from pystyle import Colors, Colorate, Center
from PIL import ImageTk, Image
import webbrowser
import threading
from threading import Thread

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QMessageBox

# Logo.
logo = """KEY-BOT"""

# Default config file.
default_config = """
# Konfig battle bota
bearer_token: ""
sleep_interval: 1
ticket_cost_threshold: 1000
ratelimit_sleep: 15
"""
wersja = "0.1.2"

# Clear the console.
clear = lambda: os.system("cls" if os.name in ("nt", "dos") else "clear")

# Set the console title.
os.system(f"title Key-Bot - discord.gg/zV6MQQqkFV")

class Config:
    def __init__(self):
        if not os.path.exists("konfig.yaml"):
            self.log_message("Nie znaleziono pliku konfiguracyjnego! Tworze go dla ciebie...")
            with open("konfig.yaml", "w") as file:
                file.write(default_config)
            self.log_message("Plik konfiguracyjny stworzony! Uzupelnij go i zrestartuj bota.")
            exit()

        with open("konfig.yaml", "r") as file:
            self.config = yaml.load(file, Loader=SafeLoader)
            self.bearer_token = self.config.get("bearer_token", "")
            self.sleep_interval = self.config.get("sleep_interval", 1)
            self.ticket_cost_threshold = self.config.get("ticket_cost_threshold", 1000)
            self.ratelimit_sleep = self.config.get("ratelimit_sleep", 15)

# Load the config.
configData = Config()

class CaseBattle:
    def __init__(self, token, sleep_interval=configData.sleep_interval, ticket_cost_threshold=configData.ticket_cost_threshold):
        self.running = False
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
            "authorization": f"{token}",
            "User-Agent": self.user_agent.random
        })
        self.base_url = "https://kdrp2.com/CaseBattle/"
        self.active_battles_url = f"{self.base_url}battle?type=active&page=0&priceFrom=0&priceTo=0.29&searchText=&sort=priceAscending&players=all&roundsCount=all"
        self.join_battle_url = f"{self.base_url}joinCaseBattle/"
        self.sleep_interval = sleep_interval
        self.ticket_cost_threshold = ticket_cost_threshold

    def print_logo(self):
        self.log_message(Center.XCenter("────────────────────────────────────────────\n"))
        self.log_message(Center.XCenter("Szukanie bitwy..."))

    def get_active_battles(self):
        try:
            response = self.session.get(self.active_battles_url)
            response.raise_for_status()
            return json.loads(response.text)["data"]
        except requests.HTTPError as http_err:
            logging.error(f"HTTP error occurred: {http_err}")
            return []
        except Exception as err:
            logging.error(f"Other error occurred: {err}")
            return []

    def join_battle(self, battle_id):
        try:
            url = f"{self.join_battle_url}{battle_id}/1"
            response = self.session.post(url)
            response.raise_for_status()
            data = json.loads(response.text)
            if data["success"]:
                return True, "Udalo sie dolaczyc do bitwy!"
            if data["errorCode"] == "slotUnavailable":
                return False, "Bitwa jest pełna!"
            if data["errorCode"] == "rateLimited":
                return False, "Ratelimited!"
            if data["errorCode"] == "userHasToWaitBeforeJoiningFreeBattle":
                return False, "Udział w darmowej bitwie można brać co 24 godziny!"
            return False, data["errorCode"]
        except requests.HTTPError as http_err:
            if "Unauthorized" in str(response.text):
                return False, "Nieprawidłowy token bearer!"
            logging.error(f"HTTP Error: {http_err}")
            return False, str(http_err)
        except Exception as err:
            logging.error(f"Error: {err}")
            return False, str(err)

    def monitor_battles(self):
        clear()
        self.print_logo()
        self.running = True
        while self.running:
            battles = self.get_active_battles()
            for battle in battles:
                if self.is_joinable(battle):
                    print(Colorate.Vertical(Colors.yellow_to_red, f"\n─────────────────[ {battle['id']} ]─────────────────\n\n", 1))
                    self.log_message(f"proba dolaczenia do bitwy {battle['id']}...")
                    print(Colorate.Horizontal(Colors.yellow_to_green, f"ID bitwy: {battle['id']}\n", 1))
                    success, message = self.join_battle(battle["id"])
                    if success:
                        self.log_message(message, Colors.green)
                        print(Colorate.Horizontal(Colors.green, message))
                    elif message == "Invalid token!":
                        self.log_message("Nieprawidlowy token bearer!", Colors.red)
                        exit()
                    elif message == "Ratelimited!":
                        self.log_message("Ratelimited! Trzeba zwiekszyc czas wstrzymania, lub dodac proxy.", Colors.red)
                        self.log_message("Wstrzymanie na 30 sekund...", Colors.yellow)
                        sleep(30)
                    elif message == "You have to wait one day between free battles!":
                        self.log_message("Musisz zaczekac 1 dzien przed ponownym dolaczaniem!", Colors.red)
                        exit()
                    else:
                        self.log_message(f"Nie udalo sie dolaczyc do bitwy! {message}", Colors.red)
                        sleep(self.sleep_interval)
            sleep(self.sleep_interval)

    def stop_monitoring(self):
        self.running = False

    def is_joinable(self, battle):
        isFreeBattle = battle["isFreeBattle"]
        users = battle["users"]
        maxUserCount = battle["maxUserCount"]
        if isFreeBattle and len(users) != maxUserCount:
            if battle["freeBattleTicketCost"] > self.ticket_cost_threshold:
                return False
            elif battle["freeBattleTicketCost"] < self.ticket_cost_threshold:
                return True
            return False

    def log_message(self, message, color=Colors.yellow):
        gui.log_message(message, color)

class GUI(QtCore.QObject):
    startBotClicked = QtCore.pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.app = QtWidgets.QApplication(sys.argv)
        self.window = QtWidgets.QMainWindow()
        self.window.setWindowTitle("Key-Bot")
        self.window.setGeometry(100, 100, 900, 480)

        self.central_widget = QtWidgets.QWidget(self.window)
        self.window.setCentralWidget(self.central_widget)

        self.layout = QtWidgets.QVBoxLayout(self.central_widget)

        self.log_text = QtWidgets.QPlainTextEdit(self.central_widget)
        self.log_text.setReadOnly(True)
        self.layout.addWidget(self.log_text)

        self.token_label = QtWidgets.QLabel(self.central_widget)
        self.token_label.setText("Bearer Token:")
        self.layout.addWidget(self.token_label)

        self.token_entry = QtWidgets.QLineEdit(self.central_widget)
        self.layout.addWidget(self.token_entry)

        self.button_frame = QtWidgets.QFrame(self.central_widget)
        self.layout.addWidget(self.button_frame)

        self.button_layout = QtWidgets.QHBoxLayout(self.button_frame)

        self.start_button = QtWidgets.QPushButton("Start")
        self.start_button.clicked.connect(self.start_bot)
        self.button_layout.addWidget(self.start_button)

        self.stop_button = QtWidgets.QPushButton("Stop")
        self.stop_button.clicked.connect(self.stop_bot)
        self.stop_button.setEnabled(False)
        self.button_layout.addWidget(self.stop_button)

        self.window.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.window.closeEvent = self.close_window

        # Display logo
        self.log_message(Center.XCenter(logo))
        self.log_message(Center.XCenter("Wersja " + wersja))

    def start_bot(self):
        bearer_token = self.token_entry.text().strip()
        if bearer_token:
            self.start_button.setEnabled(False)
            self.stop_button.setEnabled(True)
            self.token_entry.setEnabled(False)
            self.startBotClicked.emit(bearer_token)
        else:
            QMessageBox.critical(self.window, "Error", "Bearer Token nie może być pusty!")

    def stop_bot(self):
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.token_entry.setEnabled(True)

        if gui.case_battle is not None:
            gui.case_battle.stop_monitoring()

    def close_window(self, event):
        if gui.case_battle is not None and gui.case_battle.running:
            QMessageBox.warning(self.window, "Warning", "Zatrzymaj bota przed wyłączeniem.")
            event.ignore()
        else:
            self.window.close()

    def log_message(self, message, color=Colors.yellow):
        self.log_text.appendHtml(f'<span style="color: {color};">{message}</span>')

    def run(self):
        self.window.show()
        sys.exit(self.app.exec_())

class BotThread(QtCore.QRunnable):
    def __init__(self, bearer_token):
        super().__init__()
        self.bearer_token = bearer_token

    def run(self):
        case_battle = CaseBattle(self.bearer_token)
        gui.case_battle = case_battle
        case_battle.gui = gui
        case_battle.monitor_battles()

if __name__ == "__main__":
    gui = GUI()
    gui.startBotClicked.connect(lambda token: QtCore.QThreadPool.globalInstance().start(BotThread(token)))
    gui.run()
