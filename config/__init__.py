import toml
import logging
from os import environ as env


class Configuration:
    def __init__(self):
        self.log = logging.getLogger('config')
        self.config_path = env.get('CONFIG_PATH', 'config/settings.toml')
        self.config = None

    def read(self):
        try:
            with open(self.config_path, 'r') as file:
                self.config = toml.load(file)
        except FileNotFoundError:
            self.log.error(f'Файл конфигурации {self.config_path} не найден')

    def __getitem__(self, item):
        try:
            if self.config:
                return self.config[item]
            return None
        except KeyError:
            self.log.error(f'Такого ключа {item} не существует')
            return None
