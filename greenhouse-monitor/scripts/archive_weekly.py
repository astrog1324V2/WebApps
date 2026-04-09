from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from server.archive import run_weekly_archive
from server.config import load_settings
from server.db import initialize_database


def main() -> int:
    settings = load_settings()
    settings.ensure_directories()
    initialize_database(settings.db_path)
    result = run_weekly_archive(settings)
    print(result.message)
    return 0 if result.status == "success" else 1


if __name__ == "__main__":
    raise SystemExit(main())
