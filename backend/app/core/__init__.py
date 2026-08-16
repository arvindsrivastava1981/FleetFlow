"""Core configuration and security primitives.

Consolidates what currently lives at the top of `utils.py`:
- `config.py`     : env-driven settings (ADMIN_PASSWORD, DATABASE_URL, timeouts)
- `security.py`   : admin auth (sessions), strong-password enforcement,
                    csrf tokens, html.escape helper, login rate limiting
- `logging.py`    : structured logging + request/response hooks
"""