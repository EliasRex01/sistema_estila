from app.db.session import Base, engine
from app.db import models  # noqa: F401 registra tablas


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    init_db()
    print("OK estila init_db")
