import logging


def set_logger(path: str, depth: int = 0) -> None:
    """Set up the logger to also write to a file in the store directory."""
    logging.getLogger().handlers = []
    logging.basicConfig(
        level=logging.INFO,
        format=f"%(asctime)s [%(levelname)s] {' ' * 4 * depth}%(message)s",
        handlers=[logging.StreamHandler(), logging.FileHandler(path)],
    )
