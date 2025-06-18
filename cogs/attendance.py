def setup_database(self):
    """Set up dedicated attendance database"""
    try:
        # Create attendance database if it doesn't exist
        if not os.path.exists("db/attendance.sqlite"):
            open("db/attendance.sqlite", 'a').close()
            print("✓ Created new attendance database")
        
        with sqlite3.connect('db/attendance.sqlite') as attendance_db:
            cursor = attendance_db.cursor()
            
            # Create attendance records table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS attendance_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fid INTEGER,
                    nickname TEXT,
                    alliance_id INTEGER,
                    alliance_name TEXT,
                    attendance_status TEXT,
                    points INTEGER,
                    last_event_attendance TEXT,
                    marked_date TEXT,
                    marked_by INTEGER,
                    marked_by_username TEXT,
                    session_name TEXT
                )
            """)
            
            # ADDED: Check and add session_name column if missing
            cursor.execute("PRAGMA table_info(attendance_records)")
            columns = [col[1] for col in cursor.fetchall()]
            if 'session_name' not in columns:
                cursor.execute("ALTER TABLE attendance_records ADD COLUMN session_name TEXT")
                print("✓ Added session_name column to attendance_records")
            
            # Create attendance sessions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS attendance_sessions (
                    session_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    alliance_id INTEGER,
                    alliance_name TEXT,
                    session_date TEXT,
                    created_by INTEGER,
                    created_by_username TEXT,
                    total_players INTEGER,
                    present_count INTEGER,
                    absent_count INTEGER,
                    not_signed_count INTEGER,
                    session_name TEXT
                )
            """)
            
            # ADDED: Check and add session_name column to sessions table
            cursor.execute("PRAGMA table_info(attendance_sessions)")
            columns = [col[1] for col in cursor.fetchall()]
            if 'session_name' not in columns:
                cursor.execute("ALTER TABLE attendance_sessions ADD COLUMN session_name TEXT")
                print("✓ Added session_name column to attendance_sessions")
            
            # Create session_records junction table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS session_records (
                    session_id INTEGER,
                    record_id INTEGER,
                    FOREIGN KEY (session_id) REFERENCES attendance_sessions(session_id),
                    FOREIGN KEY (record_id) REFERENCES attendance_records(id)
                )
            """)
            
            attendance_db.commit()
            print("✓ Attendance database setup completed")
            
    except Exception as e:
        print(f"Error setting up attendance database: {e}")