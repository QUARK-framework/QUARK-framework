import logging

def set_logger(depth: int = 0) -> None:
    """
    Sets up the logger to also write to a file in the store directory.
    """
    logging.getLogger().handlers = []
    logging.basicConfig(
        level=logging.INFO,
        format=f"%(asctime)s [%(levelname)s] {' '*4*depth}%(message)s",
        handlers=[logging.StreamHandler(), logging.FileHandler("logging.log")]
    )
