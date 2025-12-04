"""
Database Connectors for knowledge grounding
"""

import sqlite3
from typing import Dict, List, Any, Optional
from abc import ABC

from aegis.knowledge.connector_registry import (
    BaseConnector, ConnectorConfig, ConnectorType, 
    ConnectionStatus, ConnectorRegistry
)


class BaseDatabaseConnector(BaseConnector, ABC):
    """Base class for database connectors"""
    
    connector_type = ConnectorType.DATABASE
    
    def _format_results(self, cursor, rows: List[tuple]) -> List[Dict[str, Any]]:
        """Format database results as list of dicts"""
        if not rows:
            return []
        
        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, row)) for row in rows]


class SQLiteConnector(BaseDatabaseConnector):
    """SQLite database connector"""
    
    name = "SQLite"
    description = "Connect to SQLite databases"
    
    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self.db_path = config.config.get("db_path", ":memory:")
    
    def connect(self) -> bool:
        try:
            self._connection = sqlite3.connect(self.db_path)
            self._set_connected()
            return True
        except Exception as e:
            self._set_error(str(e))
            return False
    
    def disconnect(self) -> bool:
        if self._connection:
            self._connection.close()
            self._connection = None
        self.status = ConnectionStatus.DISCONNECTED
        return True
    
    def query(self, query: str, params: Dict[str, Any] = None) -> Any:
        if not self._connection:
            raise Exception("Not connected")
        
        cursor = self._connection.cursor()
        
        # Handle search queries
        if query.startswith("search:"):
            search_term = query[7:]
            return self._search_all_tables(cursor, search_term)
        
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        
        if query.strip().upper().startswith("SELECT"):
            rows = cursor.fetchall()
            return self._format_results(cursor, rows)
        else:
            self._connection.commit()
            return {"affected_rows": cursor.rowcount}
    
    def _search_all_tables(self, cursor, search_term: str) -> List[Dict[str, Any]]:
        """Search all tables for a term"""
        results = []
        
        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        for table in tables:
            # Get columns
            cursor.execute(f"PRAGMA table_info({table})")
            columns = [row[1] for row in cursor.fetchall()]
            
            # Search text columns
            text_columns = []
            for col in columns:
                cursor.execute(f"SELECT typeof({col}) FROM {table} LIMIT 1")
                row = cursor.fetchone()
                if row and row[0] in ['text', 'TEXT']:
                    text_columns.append(col)
            
            if text_columns:
                conditions = " OR ".join([f"{col} LIKE ?" for col in text_columns])
                query = f"SELECT * FROM {table} WHERE {conditions}"
                params = [f"%{search_term}%" for _ in text_columns]
                
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                for row in self._format_results(cursor, rows):
                    results.append({"table": table, "data": row})
        
        return results
    
    def test_connection(self) -> bool:
        try:
            if not self._connection:
                return False
            cursor = self._connection.cursor()
            cursor.execute("SELECT 1")
            return True
        except:
            return False
    
    def list_tables(self) -> List[str]:
        """List all tables in the database"""
        if not self._connection:
            return []
        
        cursor = self._connection.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        return [row[0] for row in cursor.fetchall()]
    
    def get_table_schema(self, table_name: str) -> List[Dict[str, str]]:
        """Get schema for a table"""
        if not self._connection:
            return []
        
        cursor = self._connection.cursor()
        cursor.execute(f"PRAGMA table_info({table_name})")
        return [
            {"name": row[1], "type": row[2], "nullable": not row[3], "primary_key": bool(row[5])}
            for row in cursor.fetchall()
        ]


class PostgreSQLConnector(BaseDatabaseConnector):
    """PostgreSQL database connector"""
    
    name = "PostgreSQL"
    description = "Connect to PostgreSQL databases"
    
    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self.host = config.config.get("host", "localhost")
        self.port = config.config.get("port", 5432)
        self.database = config.config.get("database", "")
        self.user = config.credentials.get("user", "")
        self.password = config.credentials.get("password", "")
    
    def connect(self) -> bool:
        try:
            import psycopg2
            self._connection = psycopg2.connect(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password
            )
            self._set_connected()
            return True
        except ImportError:
            self._set_error("psycopg2 not installed. Run: pip install psycopg2-binary")
            return False
        except Exception as e:
            self._set_error(str(e))
            return False
    
    def disconnect(self) -> bool:
        if self._connection:
            self._connection.close()
            self._connection = None
        self.status = ConnectionStatus.DISCONNECTED
        return True
    
    def query(self, query: str, params: Dict[str, Any] = None) -> Any:
        if not self._connection:
            raise Exception("Not connected")
        
        cursor = self._connection.cursor()
        
        # Handle search queries
        if query.startswith("search:"):
            search_term = query[7:]
            return self._search_tables(cursor, search_term)
        
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        
        if query.strip().upper().startswith("SELECT"):
            rows = cursor.fetchall()
            return self._format_results(cursor, rows)
        else:
            self._connection.commit()
            return {"affected_rows": cursor.rowcount}
    
    def _search_tables(self, cursor, search_term: str) -> List[Dict[str, Any]]:
        """Search tables for a term"""
        results = []
        
        # Get text columns from all tables
        cursor.execute("""
            SELECT table_name, column_name 
            FROM information_schema.columns 
            WHERE data_type IN ('character varying', 'text', 'character')
            AND table_schema = 'public'
        """)
        
        columns_by_table = {}
        for table, column in cursor.fetchall():
            if table not in columns_by_table:
                columns_by_table[table] = []
            columns_by_table[table].append(column)
        
        for table, columns in columns_by_table.items():
            conditions = " OR ".join([f'"{col}" ILIKE %s' for col in columns])
            query = f'SELECT * FROM "{table}" WHERE {conditions} LIMIT 100'
            params = [f"%{search_term}%" for _ in columns]
            
            try:
                cursor.execute(query, params)
                rows = cursor.fetchall()
                for row in self._format_results(cursor, rows):
                    results.append({"table": table, "data": row})
            except:
                continue
        
        return results
    
    def test_connection(self) -> bool:
        try:
            if not self._connection:
                return False
            cursor = self._connection.cursor()
            cursor.execute("SELECT 1")
            return True
        except:
            return False


class MySQLConnector(BaseDatabaseConnector):
    """MySQL database connector"""
    
    name = "MySQL"
    description = "Connect to MySQL databases"
    
    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self.host = config.config.get("host", "localhost")
        self.port = config.config.get("port", 3306)
        self.database = config.config.get("database", "")
        self.user = config.credentials.get("user", "")
        self.password = config.credentials.get("password", "")
    
    def connect(self) -> bool:
        try:
            import mysql.connector
            self._connection = mysql.connector.connect(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password
            )
            self._set_connected()
            return True
        except ImportError:
            self._set_error("mysql-connector-python not installed. Run: pip install mysql-connector-python")
            return False
        except Exception as e:
            self._set_error(str(e))
            return False
    
    def disconnect(self) -> bool:
        if self._connection:
            self._connection.close()
            self._connection = None
        self.status = ConnectionStatus.DISCONNECTED
        return True
    
    def query(self, query: str, params: Dict[str, Any] = None) -> Any:
        if not self._connection:
            raise Exception("Not connected")
        
        cursor = self._connection.cursor()
        
        # Handle search queries
        if query.startswith("search:"):
            search_term = query[7:]
            return self._search_tables(cursor, search_term)
        
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        
        if query.strip().upper().startswith("SELECT"):
            rows = cursor.fetchall()
            return self._format_results(cursor, rows)
        else:
            self._connection.commit()
            return {"affected_rows": cursor.rowcount}
    
    def _search_tables(self, cursor, search_term: str) -> List[Dict[str, Any]]:
        """Search tables for a term"""
        results = []
        
        # Get text columns
        cursor.execute(f"""
            SELECT TABLE_NAME, COLUMN_NAME 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE DATA_TYPE IN ('varchar', 'text', 'char', 'longtext', 'mediumtext')
            AND TABLE_SCHEMA = '{self.database}'
        """)
        
        columns_by_table = {}
        for table, column in cursor.fetchall():
            if table not in columns_by_table:
                columns_by_table[table] = []
            columns_by_table[table].append(column)
        
        for table, columns in columns_by_table.items():
            conditions = " OR ".join([f"`{col}` LIKE %s" for col in columns])
            query = f"SELECT * FROM `{table}` WHERE {conditions} LIMIT 100"
            params = [f"%{search_term}%" for _ in columns]
            
            try:
                cursor.execute(query, params)
                rows = cursor.fetchall()
                for row in self._format_results(cursor, rows):
                    results.append({"table": table, "data": row})
            except:
                continue
        
        return results
    
    def test_connection(self) -> bool:
        try:
            if not self._connection:
                return False
            cursor = self._connection.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            return True
        except:
            return False


# Register connectors
ConnectorRegistry.register_type(SQLiteConnector)
ConnectorRegistry.register_type(PostgreSQLConnector)
ConnectorRegistry.register_type(MySQLConnector)

