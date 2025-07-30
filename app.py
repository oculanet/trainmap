import sqlite3
import os
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash, g
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'dubai_metro_secret_key_2023'

# Configure database path
#db_dir = os.path.expanduser('~/DubaiMetroDB')
#os.makedirs(db_dir, exist_ok=True)
#app.config['DATABASE'] = os.path.join(db_dir, 'metro.db')
#print(f"Database will be created at: {app.config['DATABASE']}")
db_dir = os.path.dirname(os.path.abspath(__file__))  # This gets the current script directory
app.config['DATABASE'] = os.path.join(db_dir, 'metro.db')

print(f"Database will be created at: {app.config['DATABASE']}")

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(app.config['DATABASE'])
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(exception):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    """Initialize the database with required tables and sample data"""
    conn = get_db()
    c = conn.cursor()

    # Create tables if they don't exist
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL
        )
    ''')

    # Maintenance types table
    c.execute('''
        CREATE TABLE IF NOT EXISTS maintenance_types (
            code TEXT PRIMARY KEY,
            description TEXT NOT NULL
        )
    ''')

    # Tracks table with enhanced schema
    c.execute('''
        CREATE TABLE IF NOT EXISTS tracks (
            track_id TEXT PRIMARY KEY,
            depot_name TEXT NOT NULL,
            depot_code TEXT NOT NULL,
            location_name TEXT NOT NULL,
            track_type TEXT NOT NULL,
            visual_layout TEXT NOT NULL,
            slot_capacity INTEGER NOT NULL,
            line TEXT NOT NULL
        )
    ''')

    # Trains table with foreign keys
    c.execute('''
        CREATE TABLE IF NOT EXISTS trains (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            train_number TEXT UNIQUE NOT NULL,
            type TEXT NOT NULL,
            status TEXT NOT NULL,
            maintenance_code TEXT,
            track_id TEXT,
            last_movement TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (maintenance_code) REFERENCES maintenance_types(code),
            FOREIGN KEY (track_id) REFERENCES tracks(track_id)
        )
    ''')

    # Movements table
    c.execute('''
        CREATE TABLE IF NOT EXISTS movements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    train_number TEXT,
    from_location TEXT,
    to_location TEXT,
    from_track_id TEXT,
    to_track_id TEXT,
    movement_out TEXT,
    movement_in TEXT,
    duration_on_track INTEGER,
    operator TEXT,
    shuting_pic TEXT,
    shunter_name TEXT,
    maintenace_type TEXT,
    comments TEXT
        )
    ''')

    # Create default users
    try:
        hashed_pw = generate_password_hash('admin123')
        c.execute(
            "INSERT OR IGNORE INTO users (username, password, role) VALUES (?, ?, ?)",
            ('admin', hashed_pw, 'admin')
        )
        
        hashed_pw = generate_password_hash('operator123')
        c.execute(
            "INSERT OR IGNORE INTO users (username, password, role) VALUES (?, ?, ?)",
            ('operator', hashed_pw, 'operator')
        )
    except sqlite3.IntegrityError:
        pass

    # Insert maintenance types
    maintenance_types = [
        ('CM', 'Corrective Maintenance'),
        ('PM_14D', 'Preventive - 14 Day'),
        ('PM_28D', 'Preventive - 28 Day'),
        ('PM_19K', 'Preventive - 19,000 KM'),
        ('PM_38K', 'Preventive - 38,000 KM'),
        ('PM_3M', '3 Month Interval'),
        ('PM_6M', '6 Month Interval'),
        ('PM_WHEEL', 'Wheel Reprofile'),
        ('PM_76K', '76,000 KM'),
        ('PM_152K', '152,000 KM'),
        ('PM_304K', '304,000 KM'),
        ('PM_OH', 'Overhaul')
    ]
    c.executemany(
        "INSERT OR IGNORE INTO maintenance_types (code, description) VALUES (?, ?)",
        maintenance_types
    )

    # Insert depot tracks
    tracks = [
        # Jebel Ali Depot (JDP) - Red Line
        ('JLMT1', 'Jebel Ali Depot (JDP)', 'JDP', 'LMT Workshop', 'LMT', 'SINGLE', 1, 'Red Line'),
        ('JLMT2', 'Jebel Ali Depot (JDP)', 'JDP', 'LMT Workshop', 'LMT', 'SINGLE', 1, 'Red Line'),
        ('JLMT3', 'Jebel Ali Depot (JDP)', 'JDP', 'LMT Workshop', 'LMT', 'SINGLE', 1, 'Red Line'),
        ('JLMT4', 'Jebel Ali Depot (JDP)', 'JDP', 'LMT Workshop', 'LMT', 'SINGLE', 1, 'Red Line'),
        ('JLMT5', 'Jebel Ali Depot (JDP)', 'JDP', 'LMT Workshop', 'LMT', 'SINGLE', 1, 'Red Line'),
        ('JHMT1', 'Jebel Ali Depot (JDP)', 'JDP', 'HMT Workshop', 'HMT', 'SINGLE', 1, 'Red Line'),
        ('JHMT2', 'Jebel Ali Depot (JDP)', 'JDP', 'HMT Workshop', 'HMT', 'SINGLE', 1, 'Red Line'),
        ('JSTBL1', 'Jebel Ali Depot (JDP)', 'JDP', 'Stabling', 'STBL', 'MULTI', 4, 'Red Line'),
        ('JSTBL2', 'Jebel Ali Depot (JDP)', 'JDP', 'Stabling', 'STBL', 'MULTI', 4, 'Red Line'),
        ('JSTBL3', 'Jebel Ali Depot (JDP)', 'JDP', 'Stabling', 'STBL', 'MULTI', 4, 'Red Line'),
        
        # Rashidiya Depot (RDP) - Red Line
        ('RLMT1', 'Rashidiya Depot (RDP)', 'RDP', 'LMT Workshop', 'LMT', 'DOUBLE', 2, 'Red Line'),
        ('RLMT2', 'Rashidiya Depot (RDP)', 'RDP', 'LMT Workshop', 'LMT', 'DOUBLE', 2, 'Red Line'),
        ('RLMT3', 'Rashidiya Depot (RDP)', 'RDP', 'LMT Workshop', 'LMT', 'DOUBLE', 2, 'Red Line'),
        ('RHMT1', 'Rashidiya Depot (RDP)', 'RDP', 'HMT Workshop', 'HMT', 'SINGLE', 1, 'Red Line'),
        ('RHMT2', 'Rashidiya Depot (RDP)', 'RDP', 'HMT Workshop', 'HMT', 'SINGLE', 1, 'Red Line'),
        ('RSTBL1', 'Rashidiya Depot (RDP)', 'RDP', 'Stabling', 'STBL', 'MULTI', 4, 'Red Line'),
        ('RSTBL2', 'Rashidiya Depot (RDP)', 'RDP', 'Stabling', 'STBL', 'MULTI', 4, 'Red Line'),
        
        # Al Qusais Depot (QDP) - Green Line
        ('QLMT1', 'Al Qusais Depot (QDP)', 'QDP', 'LMT Workshop', 'LMT', 'SINGLE', 1, 'Green Line'),
        ('QLMT2', 'Al Qusais Depot (QDP)', 'QDP', 'LMT Workshop', 'LMT', 'SINGLE', 1, 'Green Line'),
        ('QLMT3', 'Al Qusais Depot (QDP)', 'QDP', 'LMT Workshop', 'LMT', 'SINGLE', 1, 'Green Line'),
        ('QHMT1', 'Al Qusais Depot (QDP)', 'QDP', 'HMT Workshop', 'HMT', 'SINGLE', 1, 'Green Line'),
        ('QHMT2', 'Al Qusais Depot (QDP)', 'QDP', 'HMT Workshop', 'HMT', 'SINGLE', 1, 'Green Line'),
        ('QSTBL1', 'Al Qusais Depot (QDP)', 'QDP', 'Stabling', 'STBL', 'MULTI', 4, 'Green Line'),
        ('QSTBL2', 'Al Qusais Depot (QDP)', 'QDP', 'Stabling', 'STBL', 'MULTI', 4, 'Green Line'),
        ('QSTBL3', 'Al Qusais Depot (QDP)', 'QDP', 'Stabling', 'STBL', 'MULTI', 4, 'Green Line'),
        ('QWHEEL', 'Al Qusais Depot (QDP)', 'QDP', 'Wheel Lathe', 'SPECIALTY', 'SINGLE', 1, 'Green Line'),
        ('QSHOE', 'Al Qusais Depot (QDP)', 'QDP', 'CC Shoe Cleaning', 'SPECIALTY', 'SINGLE', 1, 'Green Line'),
        
        # Mainline tracks
        ('ML-RED', 'Mainline', 'ML', 'Red Line', 'MAINLINE', 'LINE', 30, 'Red Line'),
        ('ML-GREEN', 'Mainline', 'ML', 'Green Line', 'MAINLINE', 'LINE', 20, 'Green Line')
    ]
    c.executemany(
        "INSERT OR IGNORE INTO tracks (track_id, depot_name, depot_code, location_name, track_type, visual_layout, slot_capacity, line) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        tracks
    )

    # Insert sample train data
    train_data = []
    for i in range(5001, 5080):  # KS trains
        status = "Fit"
        maintenance_code = None
        track_id = "ML-RED"  # Default to mainline
        
        # Set some trains to depots for testing
        if i == 5011: 
            track_id = "JHMT1"
            status = "Unfit"
            maintenance_code = "PM_28D"
        elif i == 5026: 
            track_id = "RLMT2"
            status = "Unfit"
            maintenance_code = "PM_14D"
        elif i == 5041: 
            track_id = "QHMT1"
            status = "Unfit"
            maintenance_code = "CM"
        elif i == 5061: 
            track_id = "JSTBL1"
        elif i == 5070: 
            track_id = "RSTBL2"
        
        train_data.append((f"{i}", "KS", status, maintenance_code, track_id))
    
    for i in range(5101, 5151):  # Alstom trains
        status = "Fit"
        maintenance_code = None
        track_id = "ML-GREEN"  # Default to mainline
        
        # Set some trains to depots for testing
        if i == 5105: 
            track_id = "RHMT1"
            status = "Unfit"
            maintenance_code = "CM"
        elif i == 5120: 
            track_id = "QLMT2"
            status = "Unfit"
            maintenance_code = "PM_14D"
        elif i == 5135: 
            track_id = "QSTBL1"
        
        train_data.append((f"{i}", "Alstom", status, maintenance_code, track_id))
    
    c.executemany(
        "INSERT OR IGNORE INTO trains (train_number, type, status, maintenance_code, track_id) VALUES (?, ?, ?, ?, ?)",
        train_data
    )

    # Insert sample movement logs
    movements = [
        ("5011", "Mainline - Red Line", "JDP HMT-1", "admin", "Scheduled maintenance"),
        ("5026", "Mainline - Red Line", "RDP LMT-4", "system", "Automatic movement"),
        ("5041", "Mainline - Green Line", "QDP HMT-1", "system", "Automatic movement"),
        ("5061", "Mainline - Red Line", "JDP Stabling-3", "operator", "End of service"),
        ("5105", "Mainline - Green Line", "RDP HMT-2", "system", "Automatic movement"),
        ("5120", "Mainline - Green Line", "JDP LMT-2", "operator", "Scheduled inspection")
    ]
    c.executemany(
        "INSERT OR IGNORE INTO movements (train_number, from_location, to_location, operator, comments) VALUES (?, ?, ?, ?, ?)",
        movements
    )

    conn.commit()
    print("Database initialized successfully with new schema!")
    return True

# CLI command to initialize database
@app.cli.command('initdb')
def initdb_command():
    """Initialize the database."""
    if init_db():
        print("Database initialized successfully.")
    else:
        print("Failed to initialize database.")

# Login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        db = get_db()
        c = db.cursor()
        c.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = c.fetchone()
        
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid credentials', 'error')
            return render_template('login.html', error='Invalid credentials')
    
    return render_template('login.html')

# Dashboard route
@app.route('/')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    db = get_db()
    c = db.cursor()
    
# Get summary stats
    # Get summary stats
    stats = {}

    stats['total_trains'] = c.execute("SELECT COUNT(*) FROM trains").fetchone()[0]
    stats['operational_trains'] = c.execute("SELECT COUNT(*) FROM trains WHERE status = 'Fit'").fetchone()[0]
    stats['maintenance_trains'] = c.execute("SELECT COUNT(*) FROM trains WHERE status = 'Unfit'").fetchone()[0]
    stats['mainline_trains'] = c.execute("""
        SELECT COUNT(*) FROM trains t 
        JOIN tracks tr ON t.track_id = tr.track_id 
        WHERE tr.track_type = 'MAINLINE'
    """).fetchone()[0]

    # Train type breakdown
    stats['ks_total'] = c.execute("SELECT COUNT(*) FROM trains WHERE type = 'KS'").fetchone()[0]
    stats['alstom_total'] = c.execute("SELECT COUNT(*) FROM trains WHERE type = 'Alstom'").fetchone()[0]
    stats['ks_fit'] = c.execute("SELECT COUNT(*) FROM trains WHERE type = 'KS' AND status = 'Fit'").fetchone()[0]
    stats['alstom_fit'] = c.execute("SELECT COUNT(*) FROM trains WHERE type = 'Alstom' AND status = 'Fit'").fetchone()[0]
    stats['ks_unfit'] = c.execute("SELECT COUNT(*) FROM trains WHERE type = 'KS' AND status = 'Unfit'").fetchone()[0]
    stats['alstom_unfit'] = c.execute("SELECT COUNT(*) FROM trains WHERE type = 'Alstom' AND status = 'Unfit'").fetchone()[0]


    # Line-wise train distribution
    stats['red_line_total'] = c.execute("""
        SELECT COUNT(*) FROM trains t 
        JOIN tracks tr ON t.track_id = tr.track_id 
        WHERE tr.line = 'Red Line'
    """).fetchone()[0]

    stats['green_line_total'] = c.execute("""
        SELECT COUNT(*) FROM trains t 
        JOIN tracks tr ON t.track_id = tr.track_id 
        WHERE tr.line = 'Green Line'
    """).fetchone()[0]

 
    
    # Get depot overview
    depots = []
    c.execute("SELECT depot_code, depot_name, line FROM tracks GROUP BY depot_code")
    for depot_row in c.fetchall():
        depot = {
            'code': depot_row['depot_code'],
            'name': depot_row['depot_name'],
            'line': depot_row['line']
        }
        
        # Get sections in this depot
        sections = {}
        c.execute("""
            SELECT location_name, track_type 
            FROM tracks 
            WHERE depot_code = ? 
            GROUP BY location_name
        """, (depot['code'],))
        
        for section_row in c.fetchall():
            section_name = section_row['location_name']
            track_type = section_row['track_type']
            
            # Get tracks in this section
            c.execute("""
                SELECT t.track_id, t.visual_layout, t.slot_capacity, 
                       tr.train_number, tr.status, tr.maintenance_code,
                       mt.description as maintenance_desc
                FROM tracks t
                LEFT JOIN trains tr ON t.track_id = tr.track_id
                LEFT JOIN maintenance_types mt ON tr.maintenance_code = mt.code
                WHERE t.depot_code = ? AND t.location_name = ?
                ORDER BY t.track_id
            """, (depot['code'], section_name))
            
            tracks = []
            for track_row in c.fetchall():
                tracks.append(dict(track_row))
            
            sections[section_name] = {
                'track_type': track_type,
                'tracks': tracks
            }
        
        depot['sections'] = sections
        depots.append(depot)
    
    # Get recent movements
    movements = []
    for row in c.execute("SELECT * FROM movements ORDER BY movement_time DESC LIMIT 10").fetchall():
        movements.append(dict(row))
    
    return render_template('dashboard.html', 
                         stats=stats,
                         depots=depots,
                         movements=movements,
                         username=session['username'],
                         role=session['role'],
                         datetime=datetime,
                         current_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

# Train list route
@app.route('/trains')
def train_list():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    db = get_db()
    c = db.cursor()
    
    # Get filters from query parameters
    line_filter = request.args.get('line', 'all')
    type_filter = request.args.get('type', 'all')
    status_filter = request.args.get('status', 'all')
    maintenance_filter = request.args.get('maintenance', 'all')
    
    # Build query
    query = """
        SELECT t.*, tr.depot_name, tr.location_name, tr.track_id as track_location,
               mt.description as maintenance_desc
        FROM trains t
        LEFT JOIN tracks tr ON t.track_id = tr.track_id
        LEFT JOIN maintenance_types mt ON t.maintenance_code = mt.code
    """
    conditions = []
    params = []
    
    if line_filter != 'all':
        conditions.append("tr.line = ?")
        params.append(line_filter)
    
    if type_filter != 'all':
        conditions.append("t.type = ?")
        params.append(type_filter)
    
    if status_filter != 'all':
        conditions.append("t.status = ?")
        params.append(status_filter)
    
    if maintenance_filter != 'all':
        conditions.append("t.maintenance_code = ?")
        params.append(maintenance_filter)
    
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    
    query += " ORDER BY t.train_number"
    c.execute(query, tuple(params))
    trains = c.fetchall()
    
    return render_template('train_list.html', 
                          trains=trains,
                          filters={
                              'line': line_filter,
                              'type': type_filter,
                              'status': status_filter,
                              'maintenance': maintenance_filter
                          },
                          username=session['username'],
                          role=session['role'],
                          datetime=datetime)

# Update train status route
from datetime import datetime
from flask import flash, redirect, render_template, request, session, url_for
import sqlite3

def get_train_and_related_data(cursor, train_number):
    cursor.execute("""
        SELECT t.*, tr.depot_name, tr.location_name, tr.track_id as track_location,
               mt.description as maintenance_desc
        FROM trains t
        LEFT JOIN tracks tr ON t.track_id = tr.track_id
        LEFT JOIN maintenance_types mt ON t.maintenance_code = mt.code
        WHERE t.train_number = ?
    """, (train_number,))
    train = cursor.fetchone()

    cursor.execute("""
        SELECT * FROM tracks 
        WHERE slot_capacity > 1
        UNION
        SELECT * FROM tracks 
        WHERE slot_capacity = 1 AND track_id NOT IN (
            SELECT track_id FROM trains WHERE track_id IS NOT NULL AND train_number != ?
        )
        ORDER BY depot_code, track_type, track_id
    """, (train_number,))
    tracks = cursor.fetchall()

    cursor.execute("SELECT * FROM maintenance_types")
    maintenance_types = cursor.fetchall()

    return train, tracks, maintenance_types

@app.route('/update_train/<train_number>', methods=['GET', 'POST'])
def update_train(train_number):
    if 'username' not in session:
        return redirect(url_for('login'))

    if session['role'] != 'admin':
        flash('Admin access required', 'error')
        return redirect(url_for('train_list'))

    db = get_db()
    c = db.cursor()

    if request.method == 'POST':
        new_status = request.form['status']
        maintenance_code = request.form.get('maintenance_code') if new_status == 'Unfit' else None
        new_track_id = request.form['track_id']
        comments = request.form.get('comments', '')
        shunter_name = request.form.get('shunter_name', '')
        shutting_pic = request.form.get('shuting_pic', '')  # Person in Charge (PIC)
        operator = session['username']

        # Get current track
        c.execute("SELECT track_id FROM trains WHERE train_number = ?", (train_number,))
        current_track_row = c.fetchone()
        current_track = current_track_row['track_id'] if current_track_row else None

        # Compare as string to avoid mismatch
        if str(new_track_id) == str(current_track):
            flash("Train is already on the selected track. No update performed.", 'warning')
            train, tracks, maintenance_types = get_train_and_related_data(c, train_number)
            return render_template(
                'update_train.html',
                train=dict(train),
                tracks=tracks,
                maintenance_types=maintenance_types,
                username=session['username'],
                role=session['role'],
                datetime=datetime
            )

        # Check if new track exists and get capacity
        c.execute("SELECT slot_capacity FROM tracks WHERE track_id = ?", (new_track_id,))
        track_row = c.fetchone()
        if not track_row:
            flash("Selected track does not exist.", 'error')
            train, tracks, maintenance_types = get_train_and_related_data(c, train_number)
            return render_template(
                'update_train.html',
                train=dict(train),
                tracks=tracks,
                maintenance_types=maintenance_types,
                username=session['username'],
                role=session['role'],
                datetime=datetime
            )

        slot_capacity = track_row['slot_capacity']

        # For capacity=1 tracks, ensure no other train occupies it
        if slot_capacity == 1:
            c.execute("""
                SELECT COUNT(*) as count FROM trains
                WHERE track_id = ? AND train_number != ?
            """, (new_track_id, train_number))
            occupancy = c.fetchone()['count']
            if occupancy > 0:
                flash("Selected track is already occupied by another train.", 'error')
                train, tracks, maintenance_types = get_train_and_related_data(c, train_number)
                return render_template(
                    'update_train.html',
                    train=dict(train),
                    tracks=tracks,
                    maintenance_types=maintenance_types,
                    username=session['username'],
                    role=session['role'],
                    datetime=datetime
                )

        # Get location names
        c.execute("SELECT location_name FROM tracks WHERE track_id = ?", (current_track,))
        from_location = c.fetchone()['location_name'] if current_track else "Unknown"

        c.execute("SELECT location_name FROM tracks WHERE track_id = ?", (new_track_id,))
        to_location = c.fetchone()['location_name']

        # Get last movement time for the train
        c.execute("""
            SELECT movement_time FROM movements 
            WHERE train_number = ? 
            ORDER BY id DESC LIMIT 1
        """, (train_number,))
        last_move = c.fetchone()
        last_movement_time = last_move['movement_time'] if last_move else None

        current_time = datetime.now()
        last_movement_dt = datetime.strptime(last_movement_time, '%Y-%m-%d %H:%M:%S') if last_movement_time else None

        if last_movement_dt:
            duration_since_last_change = int((current_time - last_movement_dt).total_seconds() / 60)
        else:
            duration_since_last_change = None  # No previous movement

        try:
            # Update train record
            c.execute("""
                UPDATE trains
                SET status = ?, maintenance_code = ?, track_id = ?, last_movement = ?
                WHERE train_number = ?
            """, (new_status, maintenance_code, new_track_id, current_time.strftime('%Y-%m-%d %H:%M:%S'), train_number))

            # Insert movement log
            c.execute("""
                INSERT INTO movements 
                (train_number, from_location, to_location, from_track_id, to_track_id,
                 movement_time, last_movement_time, duration_since_last_change,
                 operator, shuting_pic, shunter_name, maintenace_type, comments)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                train_number, from_location, to_location,
                current_track, new_track_id,
                current_time.strftime('%Y-%m-%d %H:%M:%S'),
                last_movement_time,
                duration_since_last_change,
                operator, shutting_pic, shunter_name, maintenance_code, comments
            ))

            db.commit()
            flash(f"Train {train_number} updated successfully.", 'success')

        except sqlite3.Error as e:
            db.rollback()
            flash(f"Database error: {e}", 'error')
            train, tracks, maintenance_types = get_train_and_related_data(c, train_number)
            return render_template(
                'update_train.html',
                train=dict(train),
                tracks=tracks,
                maintenance_types=maintenance_types,
                username=session['username'],
                role=session['role'],
                datetime=datetime
            )

        # After success, fetch updated train and render form again
        train, tracks, maintenance_types = get_train_and_related_data(c, train_number)
        return render_template(
            'update_train.html',
            train=dict(train),
            tracks=tracks,
            maintenance_types=maintenance_types,
            username=session['username'],
            role=session['role'],
            datetime=datetime
        )

    # GET request: fetch train data and render form
    train, tracks, maintenance_types = get_train_and_related_data(c, train_number)
    if not train:
        flash('Train not found', 'error')
        return redirect(url_for('train_list'))

    return render_template(
        'update_train.html',
        train=dict(train),
        tracks=tracks,
        maintenance_types=maintenance_types,
        username=session['username'],
        role=session['role'],
        datetime=datetime
    )


# Depot detail view route
@app.route('/depot/<depot_code>')
def depot_detail(depot_code):
    if 'username' not in session:
        return redirect(url_for('login'))
    
    db = get_db()
    c = db.cursor()
    
    # Get depot info
    c.execute("""
        SELECT depot_code, depot_name, line 
        FROM tracks 
        WHERE depot_code = ? 
        GROUP BY depot_code
    """, (depot_code,))
    depot = c.fetchone()
    
    if not depot:
        flash('Depot not found', 'error')
        return redirect(url_for('dashboard'))
    
    # Get sections in this depot
    sections = {}
    c.execute("""
        SELECT location_name, track_type 
        FROM tracks 
        WHERE depot_code = ? 
        GROUP BY location_name
    """, (depot_code,))
    
    for section_row in c.fetchall():
        section_name = section_row['location_name']
        track_type = section_row['track_type']
        
        # Get tracks in this section
        c.execute("""
            SELECT t.track_id, t.visual_layout, t.slot_capacity, 
                   tr.train_number, tr.status, tr.maintenance_code,
                   mt.description as maintenance_desc
            FROM tracks t
            LEFT JOIN trains tr ON t.track_id = tr.track_id
            LEFT JOIN maintenance_types mt ON tr.maintenance_code = mt.code
            WHERE t.depot_code = ? AND t.location_name = ?
            ORDER BY t.track_id
        """, (depot_code, section_name))
        
        tracks = []
        for track in c.fetchall():
            tracks.append(dict(track))
        
        sections[section_name] = {
            'track_type': track_type,
            'tracks': tracks
        }
    
    return render_template('depot_detail.html', 
                         depot=dict(depot),
                         sections=sections,
                         username=session['username'],
                         role=session['role'],
                         datetime=datetime)

# Train history route
@app.route('/train_history/<train_number>')
def train_history(train_number):
    if 'username' not in session:
        return redirect(url_for('login'))
    
    db = get_db()
    c = db.cursor()
    
    # Get train info
    c.execute("""
        SELECT t.*, tr.depot_name, tr.location_name, tr.track_id as track_location,
               mt.description as maintenance_desc
        FROM trains t
        LEFT JOIN tracks tr ON t.track_id = tr.track_id
        LEFT JOIN maintenance_types mt ON t.maintenance_code = mt.code
        WHERE t.train_number = ?
    """, (train_number,))
    train = c.fetchone()
    
    if not train:
        flash('Train not found', 'error')
        return redirect(url_for('train_list'))
    
    # Get movement history
    c.execute("""
        SELECT * FROM movements 
        WHERE train_number = ? 
        ORDER BY movement_time DESC
    """, (train_number,))
    history = c.fetchall()
    
    return render_template('train_history.html', 
                          train=dict(train),
                          history=history,
                          username=session['username'],
                          role=session['role'],
                          datetime=datetime)

# Logout route
@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('login'))

if __name__ == '__main__':
    # Create database directory if it doesn't exist
    os.makedirs(os.path.dirname(app.config['DATABASE']), exist_ok=True)

    port = int(os.environ.get("PORT", 10000))  # Render assigns this dynamically
    app.run(host='0.0.0.0', port=port, debug=True)
