from .base import *  # noqa: F403

DEBUG = False
ALLOWED_HOSTS = env_list(  # noqa: F405
    "DJANGO_ALLOWED_HOSTS",
    "app.machinjiri.net,machinjiri.net,127.0.0.1,localhost",
)
CSRF_TRUSTED_ORIGINS = env_list(  # noqa: F405
    "DJANGO_CSRF_TRUSTED_ORIGINS",
    "https://app.machinjiri.net,https://machinjiri.net",
)
SECURE_REDIRECT_EXEMPT = [r"^healthz/$"]
SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", True)
SESSION_COOKIE_SECURE = env_bool("SESSION_COOKIE_SECURE", True)
CSRF_COOKIE_SECURE = env_bool("CSRF_COOKIE_SECURE", True)
SECURE_HSTS_SECONDS = int(os.getenv("SECURE_HSTS_SECONDS", "31536000"))
SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool("SECURE_HSTS_INCLUDE_SUBDOMAINS", True)
SECURE_HSTS_PRELOAD = env_bool("SECURE_HSTS_PRELOAD", True)
