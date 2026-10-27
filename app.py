#!/usr/bin/env python3
"""
Web App per la gestione degli inviti al matrimonio di Chiara e Ivan.
Zero dipendenze esterne: usa solo la libreria standard di Python (http.server + sqlite3).
"""

import os
import sys
import json
import sqlite3
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "invitati.db")
PORT = 8080

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS invitati (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            lato_invito TEXT DEFAULT 'Chiara e Ivan',
            targa TEXT DEFAULT '',
            data_invito TEXT,
            modalita TEXT,
            stato TEXT DEFAULT 'In attesa',
            data_conferma TEXT,
            num_adulti INTEGER DEFAULT 1,
            num_bambini INTEGER DEFAULT 0,
            note_alimentari TEXT,
            note_extra TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    # Aggiungi colonne se tabella già esisteva
    try:
        c.execute("ALTER TABLE invitati ADD COLUMN lato_invito TEXT DEFAULT 'Chiara e Ivan'")
    except sqlite3.OperationalError:
        pass
    try:
        c.execute("ALTER TABLE invitati ADD COLUMN targa TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        pass
    conn.commit()
    conn.close()

class GuestHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        super().end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == '/api/invitati':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            
            conn = sqlite3.connect(DB_FILE)
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            rows = c.execute('SELECT * FROM invitati ORDER BY id DESC').fetchall()
            data = [dict(r) for r in rows]
            conn.close()
            self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))
            return

        if parsed.path == '/api/stats':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()

            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            tot_invitati = c.execute('SELECT COUNT(*) FROM invitati').fetchone()[0]
            confermati = c.execute("SELECT COUNT(*) FROM invitati WHERE stato='Confermato'").fetchone()[0]
            in_attesa = c.execute("SELECT COUNT(*) FROM invitati WHERE stato='In attesa'").fetchone()[0]
            rifiutati = c.execute("SELECT COUNT(*) FROM invitati WHERE stato='Rifiutato'").fetchone()[0]
            
            partecipanti = c.execute("""
                SELECT COALESCE(SUM(num_adulti), 0), COALESCE(SUM(num_bambini), 0)
                FROM invitati WHERE stato='Confermato'
            """).fetchone()
            adulti_conf = partecipanti[0]
            bambini_conf = partecipanti[1]
            tot_conf_persone = adulti_conf + bambini_conf
            conn.close()

            stats = {
                "tot_invitati": tot_invitati,
                "confermati": confermati,
                "in_attesa": in_attesa,
                "rifiutati": rifiutati,
                "adulti_confermati": adulti_conf,
                "bambini_confermati": bambini_conf,
                "tot_persone_confermate": tot_conf_persone
            }
            self.wfile.write(json.dumps(stats, ensure_ascii=False).encode('utf-8'))
            return

        # Fallback to static files
        return super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == '/api/invitati':
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8')
            data = json.loads(body)

            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute('''
                INSERT INTO invitati (
                    nome, lato_invito, targa, data_invito, modalita, stato, data_conferma,
                    num_adulti, num_bambini, note_alimentari, note_extra
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                data.get('nome', '').strip(),
                data.get('lato_invito', 'Chiara e Ivan').strip(),
                data.get('targa', '').strip().upper(),
                data.get('data_invito', ''),
                data.get('modalita', 'WhatsApp'),
                data.get('stato', 'In attesa'),
                data.get('data_conferma', ''),
                int(data.get('num_adulti', 1) or 1),
                int(data.get('num_bambini', 0) or 0),
                data.get('note_alimentari', '').strip(),
                data.get('note_extra', '').strip()
            ))
            new_id = c.lastrowid
            conn.commit()
            conn.close()

            self.send_response(201)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps({"id": new_id, "success": True}).encode('utf-8'))
            return

        self.send_response(404)
        self.end_headers()

    def do_PUT(self):
        parsed = urlparse(self.path)
        if parsed.path.startswith('/api/invitati/'):
            try:
                item_id = int(parsed.path.split('/')[-1])
            except ValueError:
                self.send_response(400)
                self.end_headers()
                return

            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8')
            data = json.loads(body)

            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute('''
                UPDATE invitati SET
                    nome = ?,
                    lato_invito = ?,
                    targa = ?,
                    data_invito = ?,
                    modalita = ?,
                    stato = ?,
                    data_conferma = ?,
                    num_adulti = ?,
                    num_bambini = ?,
                    note_alimentari = ?,
                    note_extra = ?
                WHERE id = ?
            ''', (
                data.get('nome', '').strip(),
                data.get('lato_invito', 'Chiara e Ivan').strip(),
                data.get('targa', '').strip().upper(),
                data.get('data_invito', ''),
                data.get('modalita', 'WhatsApp'),
                data.get('stato', 'In attesa'),
                data.get('data_conferma', ''),
                int(data.get('num_adulti', 1) or 1),
                int(data.get('num_bambini', 0) or 0),
                data.get('note_alimentari', '').strip(),
                data.get('note_extra', '').strip(),
                item_id
            ))
            conn.commit()
            conn.close()

            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps({"id": item_id, "success": True}).encode('utf-8'))
            return

        self.send_response(404)
        self.end_headers()

    def do_DELETE(self):
        parsed = urlparse(self.path)
        if parsed.path.startswith('/api/invitati/'):
            try:
                item_id = int(parsed.path.split('/')[-1])
            except ValueError:
                self.send_response(400)
                self.end_headers()
                return

            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute('DELETE FROM invitati WHERE id = ?', (item_id,))
            conn.commit()
            conn.close()

            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps({"id": item_id, "deleted": True}).encode('utf-8'))
            return

        self.send_response(404)
        self.end_headers()

def run_server(port=PORT):
    init_db()
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    server_address = ('', port)
    httpd = HTTPServer(server_address, GuestHandler)
    print(f"Server avviato su http://localhost:{port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nArresto del server.")
        httpd.server_close()

if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else PORT
    run_server(port)
