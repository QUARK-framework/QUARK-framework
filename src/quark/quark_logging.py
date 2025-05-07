import logging


def set_logger(path: str) -> None:
    """Set up the logger to also write to a file in the store directory."""
    logging.getLogger().handlers = []
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.StreamHandler(), logging.FileHandler(path)],
    )


def set_logging_depth(depth: int) -> None:
    """Set up indents according to depth within the benchmarking tree."""
    for handler in logging.getLogger().handlers:
        handler.setFormatter(logging.Formatter(f"%(asctime)s [%(levelname)s] {' ' * 4 * depth}%(message)s", None, "%"))
