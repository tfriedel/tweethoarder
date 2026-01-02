from loguru import logger

from twitterdump import hello


def main() -> None:
    logger.info("Application started")
    print(hello())
    logger.info("Application finished")


if __name__ == "__main__":
    main()
