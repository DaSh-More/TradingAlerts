import datetime as dt

from sqlalchemy import DateTime, String, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker


class Base(DeclarativeBase):
    pass


class Alerts(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    date: Mapped[dt.datetime] = mapped_column(nullable=False)
    symbol: Mapped[str] = mapped_column(nullable=False)
    text: Mapped[str] = mapped_column(nullable=False)
    bg_color: Mapped[str] = mapped_column(nullable=False)

    def __repr__(self) -> str:
        return f"<Alerts(id={self.id}, date={self.date}, text='{self.text}')>"


class DB:
    def __init__(self, url):
        self.engine = create_engine(url, echo=True)
        self.Session = sessionmaker(self.engine)
        self.create_db_and_tables()

    def create_db_and_tables(self) -> None:
        Base.metadata.create_all(self.engine)

    def add_alert(self, symbol: str, text: str, bg_color: str) -> None:
        alert = Alerts(
            date=dt.datetime.now(), symbol=symbol, text=text, bg_color=bg_color
        )
        with self.Session() as session:
            try:
                session.add(alert)
            except:
                session.rollback()
            else:
                session.commit()

    def get_last_alerts(self, amount: int = 20):
        with self.Session() as session:
            query = select(Alerts).order_by(Alerts.date).limit(amount)
            return session.scalars(query).all()


if __name__ == "__main__":
    db = DB("postgresql+psycopg://user:password@192.168.0.100:5885/trading")
    db.add_alert("USDT", "up 100%", "red")
    res = db.get_last_alerts()
    print(res)