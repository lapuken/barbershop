from .test import *  # noqa: F403
from .test import BASE_DIR

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "test_matrix.sqlite3",
    }
}
