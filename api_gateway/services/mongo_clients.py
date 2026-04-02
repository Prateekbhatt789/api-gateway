import motor.motor_asyncio
from config import MONGO_URL, MONGO_DB, MONGO_COLLECTION

# Single shared async client — created once at startup
client     = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URL)
database   = client[MONGO_DB]
logs_collection = database[MONGO_COLLECTION]

async def init_mongo():
    """
    Create indexes on startup.
    drop_duplicates=False means it skips if identical index already exists.
    """
    # Drop the conflicting plain timestamp index if it exists
    try:
        await logs_collection.drop_index("timestamp_1")
        print("✓ Dropped old timestamp index")
    except Exception:
        pass  # didn't exist, that's fine

    await logs_collection.create_index("user_id")

    # TTL index on timestamp — auto-deletes logs after 30 days
    await logs_collection.create_index(
        "timestamp",
        expireAfterSeconds=30 * 24 * 60 * 60,
        name="ttl_30_days"
    )

    print("✓ MongoDB indexes created")

async def write_log(log: dict):
    """
    Fire-and-forget insert.
    Called from background task — never blocks response path.
    """
    try:
        await logs_collection.insert_one(log)
    except Exception as e:
        # Log to stdout — never let logging crash the gateway
        print(f"[logging error] Failed to write log to MongoDB: {e}")