import sqlite3
import os
import xbmc
import xbmcvfs

class ShowDatabase:
    def __init__(self, db_path):
        """Initialize database connection"""
        try:
            self.db_path = db_path
            xbmc.log(f'SkipIntro: Initializing database at: {db_path}', xbmc.LOGINFO)
            
            # Ensure directory exists
            db_dir = os.path.dirname(db_path)
            if not os.path.exists(db_dir):
                os.makedirs(db_dir)
                xbmc.log(f'SkipIntro: Created database directory: {db_dir}', xbmc.LOGINFO)
            
            # Create database if it doesn't exist
            if not os.path.exists(db_path):
                xbmc.log('SkipIntro: Creating new database', xbmc.LOGINFO)
                self._create_tables()
            else:
                xbmc.log('SkipIntro: Using existing database', xbmc.LOGINFO)
                # Migrate existing database to new schema
                self._migrate_database()
        except Exception as e:
            xbmc.log(f'SkipIntro: Database initialization error: {str(e)}', xbmc.LOGERROR)
            raise
    
    def _migrate_database(self):
        """Migrate database to current schema"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                c = conn.cursor()
                
                # Check if intro_end_chapter exists in shows_config
                c.execute("PRAGMA table_info(shows_config)")
                columns = [column[1] for column in c.fetchall()]
                
                if 'intro_end_chapter' in columns:
                    xbmc.log('SkipIntro: Migrating shows_config table', xbmc.LOGINFO)
                    # Create new table without intro_end_chapter
                    c.execute('''
                        CREATE TABLE shows_config_new (
                            show_id INTEGER PRIMARY KEY,
                            use_defaults BOOLEAN DEFAULT 1,
                            use_chapters BOOLEAN DEFAULT 0,
                            intro_duration INTEGER DEFAULT 60,
                            intro_start_chapter INTEGER,
                            outro_start_chapter INTEGER,
                            intro_start_time REAL,
                            intro_duration_time REAL,
                            outro_start_time REAL,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            FOREIGN KEY (show_id) REFERENCES shows(id)
                        )
                    ''')
                    # Copy data to new table
                    c.execute('''
                        INSERT INTO shows_config_new 
                        SELECT show_id, use_defaults, use_chapters, intro_duration,
                               intro_start_chapter, outro_start_chapter,
                               intro_start_time, intro_duration_time, outro_start_time,
                               created_at
                        FROM shows_config
                    ''')
                    # Drop old table and rename new one
                    c.execute('DROP TABLE shows_config')
                    c.execute('ALTER TABLE shows_config_new RENAME TO shows_config')
                
                # Check if intro_end_chapter exists in episodes
                c.execute("PRAGMA table_info(episodes)")
                columns = [column[1] for column in c.fetchall()]
                
                if 'intro_end_chapter' in columns:
                    xbmc.log('SkipIntro: Migrating episodes table', xbmc.LOGINFO)
                    # Create new table without intro_end_chapter
                    c.execute('''
                        CREATE TABLE episodes_new (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            show_id INTEGER,
                            season INTEGER,
                            episode INTEGER,
                            intro_start_chapter INTEGER,
                            outro_start_chapter INTEGER,
                            intro_start_time REAL,
                            intro_duration_time REAL,
                            outro_start_time REAL,
                            source TEXT,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            FOREIGN KEY (show_id) REFERENCES shows(id),
                            UNIQUE(show_id, season, episode)
                        )
                    ''')
                    # Copy data to new table
                    c.execute('''
                        INSERT INTO episodes_new 
                        SELECT id, show_id, season, episode,
                               intro_start_chapter, outro_start_chapter,
                               intro_start_time, intro_duration_time, outro_start_time,
                               source, created_at
                        FROM episodes
                    ''')
                    # Drop old table and rename new one
                    c.execute('DROP TABLE episodes')
                    c.execute('ALTER TABLE episodes_new RENAME TO episodes')
                
                conn.commit()
        except Exception as e:
            xbmc.log(f'SkipIntro: Database migration error: {str(e)}', xbmc.LOGERROR)
    
    def _create_tables(self):
        """Create database tables with current schema"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                c = conn.cursor()
                
                # Shows table
                c.execute('''
                    CREATE TABLE IF NOT EXISTS shows (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        title TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Shows config table
                c.execute('''
                    CREATE TABLE IF NOT EXISTS shows_config (
                        show_id INTEGER PRIMARY KEY,
                        use_defaults BOOLEAN DEFAULT 1,
                        use_chapters BOOLEAN DEFAULT 0,
                        intro_duration INTEGER DEFAULT 60,
                        intro_start_chapter INTEGER,
                        outro_start_chapter INTEGER,
                        intro_start_time REAL,
                        intro_duration_time REAL,
                        outro_start_time REAL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (show_id) REFERENCES shows(id)
                    )
                ''')
                
                # Episodes table
                c.execute('''
                    CREATE TABLE IF NOT EXISTS episodes (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        show_id INTEGER,
                        season INTEGER,
                        episode INTEGER,
                        intro_start_chapter INTEGER,
                        outro_start_chapter INTEGER,
                        intro_start_time REAL,
                        intro_duration_time REAL,
                        outro_start_time REAL,
                        source TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (show_id) REFERENCES shows(id),
                        UNIQUE(show_id, season, episode)
                    )
                ''')
                
                conn.commit()
        except Exception as e:
            xbmc.log(f'SkipIntro: Database error: {str(e)}', xbmc.LOGERROR)

    def get_show_config(self, show_id):
        """Get show configuration"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                c = conn.cursor()
                c.execute('''
                    SELECT use_defaults, use_chapters, intro_duration,
                           intro_start_chapter, outro_start_chapter,
                           intro_start_time, intro_duration_time, outro_start_time
                    FROM shows_config 
                    WHERE show_id = ?
                ''', (show_id,))
                result = c.fetchone()
                
                if result:
                    config = {
                        'use_defaults': bool(result[0]),
                        'use_chapters': bool(result[1]),
                        'intro_duration': result[2],
                        'intro_start_chapter': result[3],
                        'outro_start_chapter': result[4],
                        'intro_start_time': result[5],
                        'intro_duration_time': result[6],
                        'outro_start_time': result[7]
                    }
                    xbmc.log(f'SkipIntro: Found show config: {config}', xbmc.LOGINFO)
                    return config
                
                return None
        except Exception as e:
            xbmc.log(f'SkipIntro: Error getting show config: {str(e)}', xbmc.LOGERROR)
            return None

    def save_show_config(self, show_id, config):
        """Save show configuration"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                c = conn.cursor()
                c.execute('''
                    INSERT OR REPLACE INTO shows_config 
                    (show_id, use_defaults, use_chapters, intro_duration,
                     intro_start_chapter, outro_start_chapter,
                     intro_start_time, intro_duration_time, outro_start_time)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    show_id,
                    config.get('use_defaults', True),
                    config.get('use_chapters', False),
                    config.get('intro_duration', 60),
                    config.get('intro_start_chapter'),
                    config.get('outro_start_chapter'),
                    config.get('intro_start_time'),
                    config.get('intro_duration_time'),
                    config.get('outro_start_time')
                ))
                conn.commit()
                xbmc.log('SkipIntro: Successfully saved show config', xbmc.LOGINFO)
                return True
        except Exception as e:
            xbmc.log(f'SkipIntro: Error saving show config: {str(e)}', xbmc.LOGERROR)
            return False

    def get_show(self, title):
        """Get show by title, create if doesn't exist"""
        try:
            xbmc.log(f'SkipIntro: Looking up show: {title}', xbmc.LOGINFO)
            with sqlite3.connect(self.db_path) as conn:
                c = conn.cursor()
                c.execute('SELECT id FROM shows WHERE title = ?', (title,))
                result = c.fetchone()
                
                if result:
                    xbmc.log(f'SkipIntro: Found existing show ID: {result[0]}', xbmc.LOGINFO)
                    return result[0]
                
                xbmc.log(f'SkipIntro: Creating new show entry for: {title}', xbmc.LOGINFO)
                c.execute('INSERT INTO shows (title) VALUES (?)', (title,))
                conn.commit()
                show_id = c.lastrowid
                
                # Create default show config
                self.save_show_config(show_id, {
                    'use_defaults': True,
                    'use_chapters': False,
                    'intro_duration': 60
                })
                
                xbmc.log(f'SkipIntro: Created show with ID: {show_id}', xbmc.LOGINFO)
                return show_id
        except Exception as e:
            xbmc.log(f'SkipIntro: Error getting show: {str(e)}', xbmc.LOGERROR)
            return None

    def save_episode_times(self, show_id, season, episode, times):
        """Save or update episode times"""
        try:
            xbmc.log(f'SkipIntro: Saving times for show {show_id}, S{season}E{episode}', xbmc.LOGINFO)
            xbmc.log(f'SkipIntro: Times data: {times}', xbmc.LOGINFO)
            
            if not os.path.exists(os.path.dirname(self.db_path)):
                os.makedirs(os.path.dirname(self.db_path))
            
            with sqlite3.connect(self.db_path) as conn:
                c = conn.cursor()
                
                # Get show config
                config = self.get_show_config(show_id)
                if config and config['use_defaults']:
                    # Update show config with new times
                    config.update({
                        'intro_start_chapter': times.get('intro_start_chapter'),
                        'outro_start_chapter': times.get('outro_start_chapter'),
                        'intro_start_time': times.get('intro_start_time'),
                        'intro_duration_time': times.get('intro_duration_time'),
                        'outro_start_time': times.get('outro_start_time')
                    })
                    self.save_show_config(show_id, config)
                
                # Save episode-specific times
                c.execute('''
                    INSERT OR REPLACE INTO episodes 
                    (show_id, season, episode,
                     intro_start_chapter, outro_start_chapter,
                     intro_start_time, intro_duration_time, outro_start_time,
                     source)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    show_id, season, episode,
                    times.get('intro_start_chapter'),
                    times.get('outro_start_chapter'),
                    times.get('intro_start_time'),
                    times.get('intro_duration_time'),
                    times.get('outro_start_time'),
                    times.get('source')
                ))
                conn.commit()
                xbmc.log('SkipIntro: Successfully saved episode times', xbmc.LOGINFO)
                return True
        except Exception as e:
            xbmc.log(f'SkipIntro: Error saving episode times: {str(e)}', xbmc.LOGERROR)
            return False

    def get_episode_times(self, show_id, season, episode):
        """Get intro/outro times for an episode"""
        try:
            xbmc.log(f'SkipIntro: Getting times for show {show_id}, S{season}E{episode}', xbmc.LOGINFO)
            
            with sqlite3.connect(self.db_path) as conn:
                c = conn.cursor()
                
                # First try episode-specific times
                c.execute('''
                    SELECT intro_start_chapter, outro_start_chapter,
                           intro_start_time, intro_duration_time, outro_start_time,
                           source
                    FROM episodes 
                    WHERE show_id = ? AND season = ? AND episode = ?
                ''', (show_id, season, episode))
                result = c.fetchone()
                
                if result:
                    times = {
                        'intro_start_chapter': result[0],
                        'outro_start_chapter': result[1],
                        'intro_start_time': result[2],
                        'intro_duration_time': result[3],
                        'outro_start_time': result[4],
                        'source': result[5]
                    }
                    xbmc.log(f'SkipIntro: Found episode times: {times}', xbmc.LOGINFO)
                    return times
                
                # If no episode times and show uses defaults, get show config
                config = self.get_show_config(show_id)
                if config and config['use_defaults']:
                    times = {
                        'intro_start_chapter': config['intro_start_chapter'],
                        'outro_start_chapter': config['outro_start_chapter'],
                        'intro_start_time': config['intro_start_time'],
                        'intro_duration_time': config['intro_duration_time'],
                        'outro_start_time': config['outro_start_time'],
                        'source': 'show_default'
                    }
                    xbmc.log(f'SkipIntro: Using show defaults: {times}', xbmc.LOGINFO)
                    return times
                
                xbmc.log('SkipIntro: No times found for episode', xbmc.LOGINFO)
                return None
        except Exception as e:
            xbmc.log(f'SkipIntro: Error getting episode times: {str(e)}', xbmc.LOGERROR)
            return None
