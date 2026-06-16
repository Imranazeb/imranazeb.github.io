from datetime import datetime
from typing import Optional

from sqlmodel import Field, Session, SQLModel, create_engine, select

from utils.logs import logger

DATABASE_URL = "sqlite:///data/database.db"


class StockData(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True, index=True)
    symbol: str = Field(index=True, unique=True)
    name: str
    price: float
    url: Optional[str] = None
    sector: Optional[str] = None
    industry: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    reviewed_at: Optional[datetime] = None
    bReviewed: Optional[bool] = True


engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SQLModel.metadata.create_all(engine)


def stock_exists(symbol: str) -> bool:
    with Session(engine) as session:
        existing_stock = session.exec(
            select(StockData).where(StockData.symbol == symbol)
        ).first()
        return existing_stock is not None


def stock_reviewed_already(symbol: str) -> bool | None:
    with Session(engine) as session:
        reviewed = session.exec(
            select(StockData.bReviewed).where(StockData.symbol == symbol)
        ).first()
        return reviewed


def read_stock_data(skip: int = 0, limit: int = 100):
    with Session(engine) as session:
        stock_data = session.exec(select(StockData).offset(skip).limit(limit)).all()
        return stock_data


def create_stock_data(stock_data: StockData):
    with Session(engine) as session:
        session.add(stock_data)
        session.commit()
        session.refresh(stock_data)
        return stock_data


def update_reviewed_date(symbol: str) -> None:
    with Session(engine) as session:
        stock = session.exec(
            select(StockData).where(StockData.symbol == symbol)
        ).first()
        if stock:
            stock.reviewed_at = datetime.now()
            stock.bReviewed = True
            session.add(stock)
            session.commit()


def not_reviewed_recently(symbol: str, days_threshold: int = 30) -> bool:
    with Session(engine) as session:
        stock = session.exec(
            select(StockData).where(StockData.symbol == symbol)
        ).first()
        if stock and stock.reviewed_at:
            days_since_reviewed = (datetime.now() - stock.reviewed_at).days
            return days_since_reviewed > days_threshold
        return True  # If never reviewed, consider it not reviewed recently


def remove_all_entries():
    """Delete all stock entries from the database"""
    with Session(engine) as session:
        stocks = session.exec(select(StockData)).all()
        for stock in stocks:
            session.delete(stock)
        session.commit()
        logger.info(f"Deleted {len(stocks)} stock entries from database")


stock_data = StockData(
    symbol="AAPL",
    name="Apple Inc.",
    price=150.0,
    url="https://www.apple.com",
    sector="Technology",
)

if __name__ == "__main__":
    exists = stock_exists(stock_data.symbol)
    if not exists:
        logger.debug(f"Creating new stock entry for {stock_data.symbol}")
        create_stock_data(stock_data)
    else:
        logger.debug(f"Stock {stock_data.symbol} already exists, skipping")

    stocks = read_stock_data()
    for stock in stocks:
        print(stock)
