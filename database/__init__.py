import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore

import os


class DataBaseConnector:
    def __init__(self):
        absolute_config_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

        config_file_path = os.environ.get('FIREBASE_CONFIG_PATH', absolute_config_file_path)

        self._cred = credentials.Certificate(config_file_path)

        if not firebase_admin._apps:
            self._app = firebase_admin.initialize_app(self._cred)
        else:
            self._app = firebase_admin.get_app()

        self._db = firestore.client()

    @property
    def db(self):
        return self._db
