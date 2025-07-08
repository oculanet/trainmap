import os
import sqlite3
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, jsonify

app = Flask(__name__, template_folder='templates')

def get_db_connection():
    conn = sqlite3.connect('train_tracking.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = sqlite3.connect('train_tracking.db')
    c = conn.cursor()
    
    # Create depots table
    c.execute('''
    CREATE TABLE IF NOT EXISTS depots (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL UNIQUE,
        line TEXT NOT NULL CHECK(line IN ('Green', 'Red'))
    );
    ''')

    # Create tracks table
    c.execute('''
    CREATE TABLE IF NOT EXISTS tracks (
        id INTEGER PRIMARY KEY,
        depot_id INTEGER NOT NULL,
        type TEXT NOT NULL CHECK(type IN ('Light', 'Heavy', 'Stabling')),
        track_number INTEGER NOT NULL,
        position_x INTEGER,
        position_y INTEGER,
        FOREIGN KEY (depot_id) REFERENCES depots(id),
        UNIQUE(depot_id, type, track_number)
    );
    ''')

    # Create trains table
    c.execute('''
    CREATE TABLE IF NOT EXISTS trains (
        id INTEGER PRIMARY KEY,
        number INTEGER NOT NULL UNIQUE,
        status TEXT NOT NULL CHECK(status IN ('Fit', 'Unfit')),
        line TEXT NOT NULL CHECK(line IN ('Green', 'Red')),
        current_track_id INTEGER,
        last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (current_track_id) REFERENCES tracks(id)
    );
    ''')

    # Insert depots
    depots = [
        ('JDP', 'Red'),
        ('QDP', 'Green'),
        ('QDP', 'Red'),
        ('RDP', 'Red')
    ]
    c.executemany('INSERT OR IGNORE INTO depots (name, line) VALUES (?, ?)', depots)

    # Insert tracks
    tracks = []
    # JDP (id 1): 5 Light, 10 Stabling
    for i in range(1, 6):
        tracks.append((1, 'Light', i, 100 + (i - 1) * 120, 100))
    for i in range(1, 11):
        tracks.append((1, 'Stabling', i, 100 + (i - 1) * 60, 300))

    # QDP Green (id 2): 5 Light, 2 Heavy, 10 Stabling
    for i in range(1, 6):
        tracks.append((2, 'Light', i, 100 + (i - 1) * 120, 100))
    for i in range(1, 3):
        tracks.append((2, 'Heavy', i, 100 + (i - 1) * 120, 250))
    for i in range(1, 11):
        tracks.append((2, 'Stabling', i, 100 + (i - 1) * 60, 400))

    # QDP Red (id 3): same
    for i in range(1, 6):
        tracks.append((3, 'Light', i, 100 + (i - 1) * 120, 100))
    for i in range(1, 3):
        tracks.append((3, 'Heavy', i, 100 + (i - 1) * 120, 250))
    for i in range(1, 11):
        tracks.append((3, 'Stabling', i, 100 + (i - 1) * 60, 400))

    # RDP (id 4): 6 Light, 2 Heavy, 10 Stabling
    for i in range(1, 7):
        tracks.append((4, 'Light', i, 100 + (i - 1) * 100, 100))
    for i in range(1, 3):
        tracks.append((4, 'Heavy', i, 100 + (i - 1) * 100, 250))
    for i in range(1, 11):
        tracks.append((4, 'Stabling', i, 100 + (i - 1) * 60, 400))

    c.executemany('''
    INSERT OR IGNORE INTO tracks 
    (depot_id, type, track_number, position_x, position_y) 
    VALUES (?, ?, ?, ?, ?)
    ''', tracks)

    # Insert trains
    trains = []
    for num in range(5101, 5151):
        track_id = None
        if num % 5 == 0:
            track_id = (num - 5101) % 50 + 1
        trains.append((num, 'Fit', 'Green', track_id))

    for num in range(5001, 5080):
        track_id = None
        if num % 5 == 0:
            track_id = (num - 5001) % 79 + 1
        trains.append((num, 'Fit', 'Red', track_id))

    c.executemany('''
    INSERT OR IGNORE INTO trains 
    (number, status, line, current_track_id) 
    VALUES (?, ?, ?, ?)
    ''', trains)

    conn.commit()
    conn.close()

@app.route('/')
def index():
    conn = get_db_connection()
    trains = conn.execute('''
        SELECT t.id, t.number, t.status, t.line, 
               d.name AS depot, tr.type, tr.track_number,
               t.last_updated
        FROM trains t
        LEFT JOIN tracks tr ON t.current_track_id = tr.id
        LEFT JOIN depots d ON tr.depot_id = d.id
        ORDER BY t.number
    ''').fetchall()

    depots = conn.execute('''
        SELECT d.id, d.name, d.line, 
               COUNT(t.id) AS train_count
        FROM depots d
        LEFT JOIN tracks tr ON d.id = tr.depot_id
        LEFT JOIN trains t ON tr.id = t.current_track_id
        GROUP BY d.id
    ''').fetchall()

    conn.close()
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return render_template('index.html', trains=trains, depots=depots, current_time=current_time)

@app.route('/update/<int:train_id>', methods=['GET', 'POST'])
def update_train(train_id):
    conn = get_db_connection()
    if request.method == 'POST':
        status = request.form['status']
        track_id = request.form['track'] or None
        conn.execute('''
            UPDATE trains 
            SET status = ?, current_track_id = ?, last_updated = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (status, track_id, train_id))
        conn.commit()
        conn.close()
        return redirect(url_for('index'))

    train = conn.execute('SELECT * FROM trains WHERE id = ?', (train_id,)).fetchone()
    tracks = conn.execute('''
        SELECT tr.id, d.name AS depot_name, tr.type, tr.track_number
        FROM tracks tr
        JOIN depots d ON tr.depot_id = d.id
        ORDER BY d.name, tr.type, tr.track_number
    ''').fetchall()
    conn.close()

    return render_template('update.html', train=train, tracks=tracks)

@app.route('/depot/<int:depot_id>')
def depot_map(depot_id):
    from datetime import datetime
    conn = get_db_connection()
    depot = conn.execute('SELECT * FROM depots WHERE id = ?', (depot_id,)).fetchone()
    tracks = conn.execute('''
        SELECT tr.id, tr.type, tr.track_number, tr.position_x, tr.position_y,
               t.id AS train_id, t.number AS train_number, t.status
        FROM tracks tr
        LEFT JOIN trains t ON tr.id = t.current_track_id
        WHERE tr.depot_id = ?
    ''', (depot_id,)).fetchall()
    conn.close()

    track_types = {}
    for track in tracks:
        track_types.setdefault(track['type'], []).append(track)

    return render_template(
        'depot_map.html',
        depot=depot,
        tracks=tracks,
        track_types=track_types,
        now=datetime.now()  # 👈 Pass the datetime object here
    )


@app.route('/api/trains')
def api_trains():
    conn = get_db_connection()
    trains = conn.execute('''
        SELECT t.number, t.status, t.line, 
               d.name AS depot, tr.type, tr.track_number,
               t.last_updated
        FROM trains t
        LEFT JOIN tracks tr ON t.current_track_id = tr.id
        LEFT JOIN depots d ON tr.depot_id = d.id
        ORDER BY t.number
    ''').fetchall()

    result = [dict(train) for train in trains]
    conn.close()
    return jsonify(result)

@app.route('/api/depot/<int:depot_id>')
def api_depot(depot_id):
    conn = get_db_connection()
    depot = conn.execute('SELECT * FROM depots WHERE id = ?', (depot_id,)).fetchone()
    tracks = conn.execute('''
        SELECT tr.id, tr.type, tr.track_number, tr.position_x, tr.position_y,
               t.id AS train_id, t.number AS train_number, t.status
        FROM tracks tr
        LEFT JOIN trains t ON tr.id = t.current_track_id
        WHERE tr.depot_id = ?
    ''', (depot_id,)).fetchall()
    conn.close()

    depot_data = dict(depot) if depot else {}
    track_data = [dict(track) for track in tracks]

    return jsonify({
        'depot': depot_data,
        'tracks': track_data
    })

if __name__ == '__main__':
    if not os.path.exists('train_tracking.db'):
        init_db()
    app.run(debug=True)
