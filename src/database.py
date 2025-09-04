"""
Database Management Module

Handles database operations, schema discovery, and data preparation.
Separate lifecycle from the main NL2SQL pipeline.
"""

import os
import sqlite3
import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import json


@dataclass
class ColumnInfo:
    """Information about a database column"""
    name: str
    type: str
    nullable: bool
    primary_key: bool
    null_percentage: float
    cardinality: int
    cardinality_percentage: float
    sample_values: List[Any]


@dataclass
class TableInfo:
    """Information about a database table"""
    name: str
    row_count: int
    columns: List[ColumnInfo]


class DatabaseManager:
    """
    Manages database connections and schema discovery.
    
    Simple interface for database operations with automatic
    connection management and schema caching.
    """
    
    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self._conn = None
        self._schema_cache = None
    
    def connect(self) -> sqlite3.Connection:
        """Get or create database connection with auto-reconnect"""
        if self._conn is None or self._is_closed():
            self._conn = sqlite3.connect(str(self.db_path))
            self._conn.row_factory = sqlite3.Row
        return self._conn
    
    def _is_closed(self) -> bool:
        """Check if connection is closed"""
        try:
            self._conn.execute("SELECT 1")
            return False
        except (sqlite3.ProgrammingError, AttributeError):
            return True
    
    def get_schema_info(self, use_cache: bool = True) -> Dict[str, TableInfo]:
        """
        Get comprehensive schema information with statistics.
        
        Args:
            use_cache: Whether to use cached schema info
            
        Returns:
            Dictionary of table name -> TableInfo
        """
        if use_cache and self._schema_cache:
            return self._schema_cache
        
        conn = self.connect()
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        
        schema_info = {}
        
        for table in tables:
            table_name = table['name']
            
            # Get basic column info
            columns = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
            row_count = conn.execute(f"SELECT COUNT(*) as count FROM {table_name}").fetchone()['count']
            
            # Build enhanced column info
            enhanced_columns = []
            for col in columns:
                col_name = col['name']
                
                # Statistics
                null_count = conn.execute(
                    f"SELECT COUNT(*) as count FROM {table_name} WHERE {col_name} IS NULL"
                ).fetchone()['count']
                
                distinct_count = conn.execute(
                    f"SELECT COUNT(DISTINCT {col_name}) as count FROM {table_name}"
                ).fetchone()['count']
                
                # Sample values
                sample_values = [
                    row[0] for row in conn.execute(
                        f"SELECT DISTINCT {col_name} FROM {table_name} WHERE {col_name} IS NOT NULL LIMIT 3"
                    ).fetchall()
                ]
                
                enhanced_columns.append(ColumnInfo(
                    name=col['name'],
                    type=col['type'],
                    nullable=not col['notnull'],
                    primary_key=bool(col['pk']),
                    null_percentage=(null_count / row_count * 100) if row_count > 0 else 0,
                    cardinality=distinct_count,
                    cardinality_percentage=(distinct_count / row_count * 100) if row_count > 0 else 0,
                    sample_values=sample_values
                ))
            
            schema_info[table_name] = TableInfo(
                name=table_name,
                row_count=row_count,
                columns=enhanced_columns
            )
        
        self._schema_cache = schema_info
        return schema_info
    
    def execute_query(self, sql: str) -> Tuple[Optional[List[Dict]], Optional[str], float]:
        """
        Execute SQL query safely with timing.
        
        Returns:
            (results, error, execution_time_ms)
        """
        conn = self.connect()
        
        import time
        start_time = time.time()
        
        try:
            cursor = conn.execute(sql)
            results = [dict(row) for row in cursor.fetchall()]
            execution_time = (time.time() - start_time) * 1000
            return results, None, execution_time
            
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            return None, str(e), execution_time
    
    def get_query_plan(self, sql: str) -> Optional[str]:
        """Get SQLite query execution plan"""
        conn = self.connect()
        try:
            plan_rows = conn.execute(f"EXPLAIN QUERY PLAN {sql}").fetchall()
            return "\\n".join([row['detail'] for row in plan_rows])
        except Exception:
            return None
    
    def validate_sql(self, sql: str) -> Tuple[bool, Optional[str]]:
        """
        Validate SQL syntax without execution.
        
        Returns:
            (is_valid, error_message)
        """
        conn = self.connect()
        try:
            conn.execute(f"EXPLAIN {sql}")
            return True, None
        except Exception as e:
            return False, str(e)
    
    def close(self):
        """Close database connection"""
        if self._conn:
            self._conn.close()
            self._conn = None


class DataPreparation:
    """
    Handles data loading and database preparation.
    Separate lifecycle from main NL2SQL operations.
    """
    
    @staticmethod
    def csv_to_sqlite(csv_path: str, db_path: str, table_name: str = None) -> bool:
        """
        Convert CSV file to SQLite database.
        
        Args:
            csv_path: Path to CSV file
            db_path: Path to output SQLite database
            table_name: Table name (defaults to CSV filename)
            
        Returns:
            Success status
        """
        try:
            csv_path = Path(csv_path)
            db_path = Path(db_path)
            
            if table_name is None:
                table_name = csv_path.stem
            
            # Create output directory
            db_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Load and convert
            df = pd.read_csv(csv_path)
            
            with sqlite3.connect(str(db_path)) as conn:
                df.to_sql(table_name, conn, if_exists='replace', index=False)
            
            print(f"✅ Loaded {len(df)} rows into {table_name} table")
            return True
            
        except Exception as e:
            print(f"❌ Error loading data: {e}")
            return False
    
    @staticmethod
    def prepare_titanic_database(data_dir: str = "data/titanic", output_dir: str = "outputs/databases") -> str:
        """
        Prepare Titanic dataset for NL2SQL operations.
        
        Returns:
            Path to created database
        """
        data_path = Path(data_dir)
        output_path = Path(output_dir)
        db_path = output_path / "titanic.db"
        
        print(f"Preparing Titanic database...")
        print(f"Data directory: {data_path}")
        print(f"Output database: {db_path}")
        
        # Load train data (main dataset)
        train_csv = data_path / "train.csv"
        if train_csv.exists():
            success = DataPreparation.csv_to_sqlite(
                str(train_csv), 
                str(db_path), 
                "titanic"
            )
            
            if success:
                print(f"✅ Titanic database prepared at: {db_path}")
                return str(db_path)
        
        raise FileNotFoundError(f"Could not find train.csv at {train_csv}")


if __name__ == "__main__":
    # Quick test/demo
    print("Database Management Module")
    print("=" * 30)
    
    # Example: Prepare database
    try:
        db_path = DataPreparation.prepare_titanic_database()
        
        # Test connection
        db_manager = DatabaseManager(db_path)
        schema = db_manager.get_schema_info()
        
        print(f"\\nSchema loaded for {len(schema)} tables:")
        for table_name, table_info in schema.items():
            print(f"- {table_name}: {table_info.row_count} rows, {len(table_info.columns)} columns")
        
        db_manager.close()
        
    except Exception as e:
        print(f"Demo failed: {e}")