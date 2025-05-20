import json

from app.core.settings import APP_CONFIG

config = {
    "schema": APP_CONFIG.postgres.schema_name,
    "url": str(APP_CONFIG.postgres.dsn),
}

print(json.dumps(config))
