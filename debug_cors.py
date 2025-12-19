import os, sys
sys.path.append('/home/qwe/Desktop/zxc/backend/src')

from trading.infrastructure.config.settings import Settings

settings = Settings()
print("CORS Origins:", settings.cors_origins_list)
print("CORS Raw:", settings.CORS_ORIGINS)