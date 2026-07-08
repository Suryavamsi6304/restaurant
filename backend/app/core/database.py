from collections.abc import Generator

from sqlmodel import Session, SQLModel, create_engine

from app.core.config import get_settings

settings = get_settings()


def create_db_engine(url: str | None = None):
    database_url = url or settings.database_url
    connect_args = {'check_same_thread': False} if database_url.startswith('sqlite') else {}
    return create_engine(database_url, connect_args=connect_args)


engine = create_db_engine()


def init_db(target_engine=None) -> None:
    SQLModel.metadata.create_all(target_engine or engine)


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
