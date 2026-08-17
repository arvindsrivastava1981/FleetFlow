"""Core configuration and security primitives.

Consolidates what currently lives at the top of `utils.py`:
- `config.py`     : env-driven settings (_PASSWORD, DATABASE_URL, timeouts)
- `security.py`   : auth (sessions), strong-password enforcement,
                    csrf tokens, html.escape helper, login rate limiting
- `logging.py`    : structured logging + request/response hooks
"""