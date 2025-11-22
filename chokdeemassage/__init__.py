"""Project package initialization.

When environment variable DB_ENGINE=mysql this will install PyMySQL as the
MySQLdb adapter for Django. Optional FORCE_FAKE_MYSQL_VERSION=1 can be set
in .env if you need to spoof a higher server version for specific Django
features (normally not required).
"""

from os import getenv

try:  # Only attempt PyMySQL wiring if library is available.
	import pymysql  # type: ignore
except ImportError:
	# If PyMySQL is not installed we silently ignore; Django will fall back
	# to sqlite or raise on actual MySQL usage configured in settings.
	pymysql = None  # type: ignore
else:
	if getenv("DB_ENGINE", "sqlite").lower() == "mysql":
		# Register PyMySQL as MySQLdb implementation
		pymysql.install_as_MySQLdb()
		# Optional fake version (normally NOT needed). Use only if required.
		if getenv("FORCE_FAKE_MYSQL_VERSION", "0") == "1":
			pymysql.version_info = (8, 0, 0, "final", 0)
