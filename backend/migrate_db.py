"""Database migration script to add new columns"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from backend.database import engine

def migrate():
    """Add missing columns to existing database"""
    with engine.connect() as conn:
        # Use transaction for all operations
        trans = conn.begin()
        try:
            # Check if columns already exist
            result = conn.execute(text("PRAGMA table_info(workflow)"))
            columns = [row[1] for row in result]
            
            # Add columns to workflow table if they don't exist
            if 'updated_at' not in columns:
                print("Adding updated_at column to workflow table...")
                conn.execute(text("ALTER TABLE workflow ADD COLUMN updated_at DATETIME"))
                conn.execute(text("UPDATE workflow SET updated_at = created_at WHERE updated_at IS NULL"))
            
            if 'deleted_at' not in columns:
                print("Adding deleted_at column to workflow table...")
                conn.execute(text("ALTER TABLE workflow ADD COLUMN deleted_at DATETIME"))
            
            # Check agent table
            result = conn.execute(text("PRAGMA table_info(agent)"))
            agent_columns = [row[1] for row in result]
            
            # Add columns to agent table if they don't exist
            if 'created_at' not in agent_columns:
                print("Adding created_at column to agent table...")
                conn.execute(text("ALTER TABLE agent ADD COLUMN created_at DATETIME"))
                conn.execute(text("UPDATE agent SET created_at = datetime('now') WHERE created_at IS NULL"))
            
            if 'updated_at' not in agent_columns:
                print("Adding updated_at column to agent table...")
                conn.execute(text("ALTER TABLE agent ADD COLUMN updated_at DATETIME"))
                conn.execute(text("UPDATE agent SET updated_at = datetime('now') WHERE updated_at IS NULL"))
            
            if 'deleted_at' not in agent_columns:
                print("Adding deleted_at column to agent table...")
                conn.execute(text("ALTER TABLE agent ADD COLUMN deleted_at DATETIME"))
            
            # Add new Phase 2 columns to agent table
            if 'agent_properties' not in agent_columns:
                print("Adding agent_properties column to agent table...")
                conn.execute(text("ALTER TABLE agent ADD COLUMN agent_properties JSON"))
            
            if 'agent_capabilities' not in agent_columns:
                print("Adding agent_capabilities column to agent table...")
                conn.execute(text("ALTER TABLE agent ADD COLUMN agent_capabilities JSON"))
            
            if 'agent_status' not in agent_columns:
                print("Adding agent_status column to agent table...")
                conn.execute(text("ALTER TABLE agent ADD COLUMN agent_status TEXT DEFAULT 'active'"))
                conn.execute(text("UPDATE agent SET agent_status = 'active' WHERE agent_status IS NULL"))
            
            # Create indexes if they don't exist
            try:
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_workflow_created_at ON workflow(created_at)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_workflow_deleted_at ON workflow(deleted_at)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_agent_workflow_id ON agent(workflow_id)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_agent_role ON agent(role)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_agent_deleted_at ON agent(deleted_at)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_agent_status ON agent(agent_status)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_dependency_workflow_id ON agent_dependency(workflow_id)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_dependency_agent_id ON agent_dependency(agent_id)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_dependency_depends_on ON agent_dependency(depends_on_agent_id)"))
                print("Indexes created successfully")
            except Exception as e:
                print(f"Note: Some indexes may already exist: {e}")
            
            trans.commit()
            print("Migration completed successfully!")
        except Exception as e:
            trans.rollback()
            print(f"Migration failed: {e}")
            raise

if __name__ == "__main__":
    migrate()

