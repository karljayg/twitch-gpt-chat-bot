"""
Database Client Factory

Creates the appropriate database client based on configuration.
"""

from core.interfaces import IDatabaseClient
from adapters.database.local_database_client import LocalDatabaseClient
from adapters.database.api_database_client import ApiDatabaseClient
from settings import config
import logging
import os

logger = logging.getLogger("DatabaseClientFactory")


def create_database_client() -> IDatabaseClient:
    """
    Factory function to create the appropriate database client
    based on configuration.
    
    Returns:
        IDatabaseClient: Either LocalDatabaseClient or ApiDatabaseClient
        
    Raises:
        SystemExit: If configuration is invalid or connection fails
    """
    db_mode = config.DB_MODE.lower()
    
    if db_mode == "local":
        logger.info("=" * 60)
        logger.info("DATABASE MODE: LOCAL (Direct MySQL connection)")
        logger.info("=" * 60)
        try:
            return LocalDatabaseClient()
        except Exception as e:
            logger.error(f"FATAL: Failed to connect to local MySQL database: {e}")
            logger.error(f"Check DB_HOST ({config.DB_HOST}), DB_USER, DB_PASSWORD in config.py")
            raise SystemExit("Cannot start - Local database connection failed")
    
    elif db_mode == "api":
        logger.info("=" * 60)
        logger.info("DATABASE MODE: API (Remote database via REST API)")
        logger.info(f"API Endpoint: {config.DB_API_URL}")
        logger.info("=" * 60)
        try:
            client = ApiDatabaseClient(
                api_base_url=config.DB_API_URL,
                api_key=config.DB_API_KEY
            )
            # Test the connection
            response = client._make_request('GET', '/health')
            if response.get('status') != 'healthy':
                raise Exception("API health check failed")
            logger.info(f"✓ API connection verified - Database: {response.get('database', 'unknown')}")
            return client
        except Exception as e:
            logger.error(f"FATAL: Failed to connect to database API: {e}")
            logger.error(f"Check DB_API_URL ({config.DB_API_URL}) and DB_API_KEY in config.py")
            logger.error(f"Verify API server is running and accessible")
            raise SystemExit("Cannot start - API connection failed")
    
    else:
        logger.error(f"FATAL: Invalid DB_MODE: '{db_mode}'. Must be 'local' or 'api'")
        raise SystemExit("Cannot start - Invalid configuration")

