from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
import json

class DatabaseHandler:
    def __init__(self, db_url):
        """
        Initializes the DatabaseHandler.
        :param db_url: SQLAlchemy connection string 
                      (e.g., postgresql://user:pass@localhost/dbname)
        """
        self.db_url = db_url
        self.engine = None

    def connect(self):
        """Creates the engine and verifies connection."""
        try:
            self.engine = create_engine(self.db_url)
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            print("✅ Database connection established.")
            return True
        except Exception as e:
            print(f"❌ Database connection failed: {e}")
            return False

    def execute_script(self, sql_script):
        """Executes a raw SQL script (e.g., for schema creation)."""
        if not self.engine:
            if not self.connect(): return False
        
        try:
            with self.engine.connect() as conn:
                # Split by ; might be naive for complex PL/SQL but works for basic DDL
                statements = sql_script.split(';')
                for stmt in statements:
                    if stmt.strip():
                        conn.execute(text(stmt))
                conn.commit()
            print("✅ SQL Script executed successfully.")
            return True
        except SQLAlchemyError as e:
            print(f"⚠️ SQL Execution Error: {e}")
            return False

    def seed_data(self, table_name, data_list):
        """
        Inserts a list of dictionaries into the table.
        :param table_name: Name of the target table.
        :param data_list: List of dicts, e.g. [{'col1': 'val1'}, {'col2': 'val2'}]
        """
        if not self.engine:
            if not self.connect(): return False
            
        if not data_list:
            print("ℹ️ No data to seed.")
            return True

        try:
            with self.engine.connect() as conn:
                # Extract columns from the first dict
                keys = data_list[0].keys()
                columns = ', '.join(keys)
                placeholders = ', '.join([f":{key}" for key in keys])
                
                sql = text(f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})")
                
                conn.execute(sql, data_list)
                conn.commit()
            
            print(f"✅ inserted {len(data_list)} rows into {table_name}.")
            return True
        except SQLAlchemyError as e:
            print(f"⚠️ Data Seeding Error: {e}")
            return False
