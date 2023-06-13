from pydantic import BaseModel


class User(BaseModel):
    login: str
    email: str
    password: str

    def to_dict(self):
        return {
            'login': self.login,
            'email': self.email,
            'password': self.password
        }
