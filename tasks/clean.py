import os
import shutil


def clean_cache() -> None:
    """Remove pastas __pycache__ ."""
    cache_dirs = ["__pycache__"]
    for root, dirs, _ in os.walk("."):
        [
            shutil.rmtree(os.path.join(root, cache_dir))
            for cache_dir in cache_dirs
            if cache_dir in dirs
        ]

if __name__ == "__main__":
    clean_cache()
    