import asyncio
from typing import AsyncGenerator
from prisma import Prisma, register
from prisma.errors import PrismaError
from app.core.config import settings
from app.core.logger import logger

# Global database instance
db: Prisma = None

async def init_db() -> None:
    """Initialize database connection"""
    global db
    try:
        db = Prisma()
        await db.connect()
        logger.info("Database connected successfully")
        
        # Register the global instance
        register(db)
        
        # Run any startup operations
        await _startup_operations()
        
    except PrismaError as e:
        logger.error(f"Database connection failed: {e}")
        raise
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise

async def close_db() -> None:
    """Close database connection"""
    global db
    if db:
        await db.disconnect()
        logger.info("Database disconnected")

async def get_db() -> AsyncGenerator[Prisma, None]:
    """Get database instance for dependency injection"""
    global db
    if db is None:
        await init_db()
    
    try:
        yield db
    except Exception as e:
        logger.error(f"Database operation failed: {e}")
        raise
    finally:
        # Connection is managed globally, no need to close here
        pass

async def _startup_operations() -> None:
    """Perform startup database operations"""
    try:
        # Create default assets if they don't exist
        await _create_default_assets()
        
        # Create system user if not exists
        await _create_system_user()
        
        logger.info("Database startup operations completed")
        
    except Exception as e:
        logger.error(f"Database startup operations failed: {e}")
        # Don't raise here, let the app continue

async def _create_default_assets() -> None:
    """Create default cryptocurrency assets"""
    default_assets = [
        {
            "symbol": "BTC",
            "name": "Bitcoin",
            "type": "CRYPTOCURRENCY",
            "description": "The first and largest cryptocurrency by market capitalization",
            "currentPrice": 0.0,
        },
        {
            "symbol": "ETH",
            "name": "Ethereum",
            "type": "CRYPTOCURRENCY",
            "description": "A decentralized platform for smart contracts and DApps",
            "currentPrice": 0.0,
        },
        {
            "symbol": "SOL",
            "name": "Solana",
            "type": "CRYPTOCURRENCY",
            "description": "High-performance blockchain for decentralized applications",
            "currentPrice": 0.0,
        },
        {
            "symbol": "ADA",
            "name": "Cardano",
            "type": "CRYPTOCURRENCY",
            "description": "A sustainable blockchain platform for changemakers",
            "currentPrice": 0.0,
        },
        {
            "symbol": "DOT",
            "name": "Polkadot",
            "type": "CRYPTOCURRENCY",
            "description": "A multi-chain blockchain platform",
            "currentPrice": 0.0,
        },
        {
            "symbol": "LINK",
            "name": "Chainlink",
            "type": "CRYPTOCURRENCY",
            "description": "Decentralized oracle network",
            "currentPrice": 0.0,
        },
        {
            "symbol": "MATIC",
            "name": "Polygon",
            "type": "CRYPTOCURRENCY",
            "description": "Ethereum scaling solution",
            "currentPrice": 0.0,
        },
        {
            "symbol": "AVAX",
            "name": "Avalanche",
            "type": "CRYPTOCURRENCY",
            "description": "High-performance blockchain platform",
            "currentPrice": 0.0,
        }
    ]
    
    for asset_data in default_assets:
        try:
            # Check if asset already exists
            existing = await db.asset.find_unique(
                where={"symbol": asset_data["symbol"]}
            )
            
            if not existing:
                await db.asset.create(data=asset_data)
                logger.info(f"Created default asset: {asset_data['symbol']}")
                
        except Exception as e:
            logger.error(f"Failed to create asset {asset_data['symbol']}: {e}")

async def _create_system_user() -> None:
    """Create system user for automated operations"""
    try:
        system_user = await db.user.find_unique(
            where={"email": "system@fortexa.com"}
        )
        
        if not system_user:
            await db.user.create(
                data={
                    "email": "system@fortexa.com",
                    "password": "system_user_no_login",
                    "firstName": "System",
                    "lastName": "User",
                    "displayName": "System",
                    "isActive": False,
                    "isEmailVerified": True,
                }
            )
            logger.info("Created system user")
            
    except Exception as e:
        logger.error(f"Failed to create system user: {e}")

# Health check for database
async def check_db_health() -> dict:
    """Check database health"""
    try:
        # Try to perform a simple query
        await db.query_raw("SELECT 1")
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {"status": "unhealthy", "database": "disconnected", "error": str(e)}

# Database utilities
async def execute_raw_query(query: str, params: list = None):
    """Execute raw SQL query"""
    try:
        if params:
            result = await db.query_raw(query, *params)
        else:
            result = await db.query_raw(query)
        return result
    except Exception as e:
        logger.error(f"Raw query execution failed: {e}")
        raise

async def get_table_count(table_name: str) -> int:
    """Get count of records in a table"""
    try:
        result = await db.query_raw(f"SELECT COUNT(*) FROM {table_name}")
        return result[0]["count"]
    except Exception as e:
        logger.error(f"Failed to get table count for {table_name}: {e}")
        return 0 