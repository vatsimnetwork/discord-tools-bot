import logging

from bot.client import Bot
from bot.settings import Settings


def main() -> None:
    settings = Settings()

    logging.basicConfig(
        format="[%(asctime)s] %(levelname)8s: %(message)s\t(%(name)s)",
        datefmt="%Y-%m-%d %H:%M:%S",
        level=settings.log_level,
    )

    Bot(settings=settings).run(settings.discord_bot_token, log_handler=None)


if __name__ == "__main__":
    main()
