# src/incept/databases/factory.py

from incept.databases.notion import NotionDB
# from incept.databases.postgres import PostgresDB  # hypothetical future class

def get_db_client(db_type, **kwargs):
    """
    Factory function that returns the appropriate DB client.

    :param db_type: e.g. "notion" or "postgres" or "supabase"
    :param kwargs: other params like api_key, database_id, or connection strings
    """
    if db_type == "notion":
        api_key = kwargs["api_key"]
        database_id = kwargs["database_id"]
        return NotionDB(api_key, database_id)

    elif db_type == "postgres":
        # Example: psql_conn_str = kwargs["conn_str"]
        # return PostgresDB(psql_conn_str)
        raise NotImplementedError("PostgresDB not implemented yet.")

    else:
        raise ValueError(f"Unsupported database type: {db_type}")
