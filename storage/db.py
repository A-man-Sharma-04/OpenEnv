"""
Storage Layer
SQLite-based storage for tasks, runs, and scores.
"""
import sqlite3
import json
from typing import Any, Dict, List, Optional
from datetime import datetime
import threading
from utils.logging_config import get_logger

logger = get_logger(__name__)


class DatabaseManager:
    """Thread-safe SQLite database manager"""

    def __init__(self, db_path: str = "rl_platform.db"):
        self.db_path = db_path
        self.local = threading.local()
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """Get thread-local database connection"""
        if not hasattr(self.local, 'connection'):
            self.local.connection = sqlite3.connect(self.db_path)
            self.local.connection.row_factory = sqlite3.Row
        return self.local.connection

    def _init_db(self):
        """Initialize database schema"""
        conn = self._get_connection()
        cursor = conn.cursor()

        # Tasks table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                env_type TEXT NOT NULL,
                config TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                version TEXT
            )
        ''')

        # Runs table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS runs (
                id TEXT PRIMARY KEY,
                task_id TEXT NOT NULL,
                agent_type TEXT NOT NULL,
                agent_config TEXT NOT NULL,
                status TEXT NOT NULL,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                metrics TEXT,
                FOREIGN KEY (task_id) REFERENCES tasks (id)
            )
        ''')

        # Episodes table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS episodes (
                id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL,
                episode_num INTEGER NOT NULL,
                total_reward REAL NOT NULL,
                steps INTEGER NOT NULL,
                success BOOLEAN NOT NULL,
                states TEXT,
                actions TEXT,
                rewards TEXT,
                metadata TEXT,
                FOREIGN KEY (run_id) REFERENCES runs (id)
            )
        ''')

        # Leaderboard cache
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS leaderboard (
                agent_name TEXT NOT NULL,
                env_type TEXT NOT NULL,
                avg_reward REAL NOT NULL,
                success_rate REAL NOT NULL,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (agent_name, env_type)
            )
        ''')

        conn.commit()

    def save_task(self, task_id: str, env_type: str, config: Dict[str, Any], version: Optional[str] = None) -> bool:
        """Save task configuration"""
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute('''
                INSERT OR REPLACE INTO tasks (id, env_type, config, version)
                VALUES (?, ?, ?, ?)
            ''', (task_id, env_type, json.dumps(config), version))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error saving task: {e}")
            return False

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task by ID"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM tasks WHERE id = ?', (task_id,))
        row = cursor.fetchone()

        if row:
            return {
                'id': row['id'],
                'env_type': row['env_type'],
                'config': json.loads(row['config']),
                'created_at': row['created_at'],
                'version': row['version']
            }
        return None

    def list_tasks(self, env_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all tasks, optionally filtered by env_type"""
        conn = self._get_connection()
        cursor = conn.cursor()

        if env_type:
            cursor.execute('SELECT * FROM tasks WHERE env_type = ? ORDER BY created_at DESC', (env_type,))
        else:
            cursor.execute('SELECT * FROM tasks ORDER BY created_at DESC')

        tasks = []
        for row in cursor.fetchall():
            tasks.append({
                'id': row['id'],
                'env_type': row['env_type'],
                'config': json.loads(row['config']),
                'created_at': row['created_at'],
                'version': row['version']
            })
        return tasks

    def save_run(self, run_id: str, task_id: str, agent_type: str, agent_config: Dict[str, Any]) -> bool:
        """Save run metadata"""
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute('''
                INSERT INTO runs (id, task_id, agent_type, agent_config, status)
                VALUES (?, ?, ?, ?, ?)
            ''', (run_id, task_id, agent_type, json.dumps(agent_config), 'running'))
            conn.commit()
            return True
        except Exception as e:
            print(f"Error saving run: {e}")
            return False

    def update_run_status(self, run_id: str, status: str, metrics: Optional[Dict[str, Any]] = None) -> bool:
        """Update run status and metrics"""
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            completed_at = datetime.now().isoformat() if status in ['completed', 'failed'] else None
            cursor.execute('''
                UPDATE runs
                SET status = ?, completed_at = ?, metrics = ?
                WHERE id = ?
            ''', (status, completed_at, json.dumps(metrics) if metrics else None, run_id))
            conn.commit()
            return True
        except Exception as e:
            print(f"Error updating run: {e}")
            return False

    def save_episode(self, episode_id: str, run_id: str, episode_num: int,
                    total_reward: float, steps: int, success: bool,
                    states: List[Any], actions: List[Any], rewards: List[Any],
                    metadata: Dict[str, Any]) -> bool:
        """Save episode data"""
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute('''
                INSERT INTO episodes (id, run_id, episode_num, total_reward, steps, success, states, actions, rewards, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                episode_id, run_id, episode_num, total_reward, steps, success,
                json.dumps([str(s) for s in states]),
                json.dumps([str(a) for a in actions]),
                json.dumps([str(r) for r in rewards]),
                json.dumps(metadata)
            ))
            conn.commit()
            return True
        except Exception as e:
            print(f"Error saving episode: {e}")
            return False

    def get_run_results(self, run_id: str) -> Optional[Dict[str, Any]]:
        """Get run results with episodes"""
        conn = self._get_connection()
        cursor = conn.cursor()

        # Get run info
        cursor.execute('SELECT * FROM runs WHERE id = ?', (run_id,))
        run_row = cursor.fetchone()
        if not run_row:
            return None

        # Get episodes
        cursor.execute('SELECT * FROM episodes WHERE run_id = ? ORDER BY episode_num', (run_id,))
        episodes = []
        for row in cursor.fetchall():
            episodes.append({
                'episode_num': row['episode_num'],
                'total_reward': row['total_reward'],
                'steps': row['steps'],
                'success': bool(row['success']),
                'metadata': json.loads(row['metadata']) if row['metadata'] else {}
            })

        return {
            'run_id': run_row['id'],
            'task_id': run_row['task_id'],
            'agent_type': run_row['agent_type'],
            'status': run_row['status'],
            'started_at': run_row['started_at'],
            'completed_at': run_row['completed_at'],
            'metrics': json.loads(run_row['metrics']) if run_row['metrics'] else None,
            'episodes': episodes
        }

    def update_leaderboard(self, agent_name: str, env_type: str, avg_reward: float, success_rate: float) -> bool:
        """Update leaderboard"""
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute('''
                INSERT OR REPLACE INTO leaderboard (agent_name, env_type, avg_reward, success_rate, last_updated)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (agent_name, env_type, avg_reward, success_rate))
            conn.commit()
            return True
        except Exception as e:
            print(f"Error updating leaderboard: {e}")
            return False

    def get_leaderboard(self, env_type: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Get leaderboard rankings"""
        conn = self._get_connection()
        cursor = conn.cursor()

        if env_type:
            cursor.execute('''
                SELECT * FROM leaderboard
                WHERE env_type = ?
                ORDER BY avg_reward DESC
                LIMIT ?
            ''', (env_type, limit))
        else:
            cursor.execute('''
                SELECT * FROM leaderboard
                ORDER BY avg_reward DESC
                LIMIT ?
            ''', (limit,))

        rankings = []
        for row in cursor.fetchall():
            rankings.append({
                'agent_name': row['agent_name'],
                'env_type': row['env_type'],
                'avg_reward': row['avg_reward'],
                'success_rate': row['success_rate'],
                'last_updated': row['last_updated']
            })
        return rankings

    def close(self):
        """Close all connections"""
        if hasattr(self.local, 'connection'):
            self.local.connection.close()


# Global database instance
db = DatabaseManager()