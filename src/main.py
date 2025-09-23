import asyncio
import logging

from aiogram import Bot, Dispatcher

from src.bot.bot import ShopBot
from src.bot.service import Service
from src.db.db_conf import DbSession, init_orm
from src.db.repository import Repository
from src.settings import Settings

logger = logging.getLogger(__name__)


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    bot_obj = Bot(token=Settings.TOKEN)
    dp = Dispatcher()
    session = DbSession()
    repo = Repository(session)
    service = Service(repo)
    shop_bot = ShopBot(dp, bot_obj, service, Settings.ADMIN_TOKEN)
    await init_orm()
    logger.info("DB initialized")
    await shop_bot.start()


if __name__ == "__main__":
    asyncio.run(main())
