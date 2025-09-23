import asyncio
import json

from sqlalchemy import insert, select

from src.db.db_conf import DbSession
from src.db.models import Category, Good

PATH = "data/initial_data.json"


async def load_initial_data(file_path: str) -> None:
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    category_data = data["categories"]
    good_data = data["goods"]
    async with DbSession() as session:
        await session.execute(insert(Category), category_data)
        await session.commit()
        for good in good_data:
            stmt = select(Category).filter_by(name=good["category_name"])
            res = await session.execute(stmt)
            obj = res.scalar_one_or_none()
            good.pop("category_name")
            good["category_id"] = obj.id
        await session.execute(insert(Good), good_data)
        await session.commit()


async def main() -> None:
    await load_initial_data(PATH)


if __name__ == "__main__":
    asyncio.run(main())
