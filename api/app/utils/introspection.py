from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any


async def get_tables(session: AsyncSession) -> List[str]:
    """
    Retrieve list of tables in the database.

    Args:
        session: Async SQLAlchemy session.

    Returns:
        List of table names.
    """
    try:
        result = await session.execute(text("SHOW TABLES"))
        tables = [row[0] for row in result.fetchall()]
        return tables
    except Exception as e:
        raise Exception(f"Failed to fetch tables: {str(e)}")


async def describe_table(session: AsyncSession, table_name: str) -> List[Dict[str, Any]]:
    """
    Describe a table structure (columns, types, etc.).

    Args:
        session: Async SQLAlchemy session.
        table_name: Name of the table.

    Returns:
        List of dicts with column info.
    """
    try:
        result = await session.execute(text(f"DESCRIBE {table_name}"))
        columns = []
        for row in result.fetchall():
            columns.append({
                "Field": row[0],
                "Type": row[1],
                "Null": row[2],
                "Key": row[3],
                "Default": row[4],
                "Extra": row[5]
            })
        return columns
    except Exception as e:
        raise Exception(f"Failed to describe table {table_name}: {str(e)}")


async def get_indexes(session: AsyncSession, table_name: str) -> List[Dict[str, Any]]:
    """
    Retrieve indexes for a table.

    Args:
        session: Async SQLAlchemy session.
        table_name: Name of the table.

    Returns:
        List of dicts with index info.
    """
    try:
        result = await session.execute(text(f"SHOW INDEX FROM {table_name}"))
        indexes = []
        for row in result.fetchall():
            indexes.append({
                "Table": row[0],
                "Non_unique": row[1],
                "Key_name": row[2],
                "Seq_in_index": row[3],
                "Column_name": row[4],
                "Collation": row[5],
                "Cardinality": row[6],
                "Sub_part": row[7],
                "Packed": row[8],
                "Null": row[9],
                "Index_type": row[10],
                "Comment": row[11],
                "Index_comment": row[12],
                "Is_visible": row[13],
                "Expr": row[14]
            })
        return indexes
    except Exception as e:
        raise Exception(f"Failed to fetch indexes for {table_name}: {str(e)}")


async def get_foreign_keys(session: AsyncSession, table_name: str) -> List[Dict[str, Any]]:
    """
    Retrieve foreign key constraints for a table.

    Args:
        session: Async SQLAlchemy session.
        table_name: Name of the table.

    Returns:
        List of dicts with FK info (MariaDB-specific query).
    """
    try:
        # MariaDB INFORMATION_SCHEMA query for FKs
        fk_query = text("""
            SELECT 
                CONSTRAINT_NAME, 
                COLUMN_NAME, 
                REFERENCED_TABLE_NAME, 
                REFERENCED_COLUMN_NAME
            FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE 
            WHERE TABLE_SCHEMA = DATABASE() 
            AND TABLE_NAME = :table_name 
            AND REFERENCED_TABLE_NAME IS NOT NULL
        """)
        result = await session.execute(fk_query, {"table_name": table_name})
        fks = []
        for row in result.fetchall():
            fks.append({
                "constraint_name": row[0],
                "column_name": row[1],
                "referenced_table": row[2],
                "referenced_column": row[3]
            })
        return fks
    except Exception as e:
        raise Exception(f"Failed to fetch foreign keys for {table_name}: {str(e)}")
