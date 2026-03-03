import json
import os
import sqlite3
from datetime import datetime
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

BASE_DIR = os.path.dirname(__file__)
DB_PATH = os.path.join(BASE_DIR, "data", "laerquest.sqlite")
PORT = int(os.environ.get("PORT", "4173"))

os.makedirs(os.path.join(BASE_DIR, "data"), exist_ok=True)


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.executescript(
        """
        CREATE TABLE IF NOT EXISTS subjects (
          id TEXT PRIMARY KEY,
          name TEXT NOT NULL,
          description TEXT NOT NULL,
          video_url TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS questions (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          subject_id TEXT NOT NULL,
          order_index INTEGER NOT NULL,
          prompt TEXT NOT NULL,
          option_a TEXT NOT NULL,
          option_b TEXT NOT NULL,
          option_c TEXT NOT NULL,
          option_d TEXT NOT NULL,
          correct_index INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS players (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          name TEXT UNIQUE NOT NULL,
          xp INTEGER NOT NULL DEFAULT 0,
          streak INTEGER NOT NULL DEFAULT 0,
          level INTEGER NOT NULL DEFAULT 1,
          updated_at TEXT NOT NULL
        );
        """
    )
    count = cur.execute("SELECT COUNT(*) FROM subjects").fetchone()[0]
    if count == 0:
        subjects = [
            ("mat", "Matematik", "Brøker, procenter og hurtig hovedregning.", "https://www.youtube.com/embed/RE5vpcJfY9w"),
            ("bio", "Biologi", "Kroppen, celler og naturens kredsløb.", "https://www.youtube.com/embed/gFuEoxh5hd4"),
            ("hist", "Historie", "Store perioder og begivenheder i verdenshistorien.", "https://www.youtube.com/embed/xuCn8ux2gbs"),
        ]
        cur.executemany("INSERT INTO subjects (id, name, description, video_url) VALUES (?, ?, ?, ?)", subjects)

        questions = [
            ("mat", 1, "Hvad er 25% af 200?", "25", "50", "75", "100", 1),
            ("mat", 2, "Hvad er 3/4 som decimaltal?", "0.25", "0.5", "0.75", "0.8", 2),
            ("mat", 3, "Hvad giver 9 × 7?", "56", "63", "72", "49", 1),
            ("bio", 1, "Hvad er cellens kontrolcenter?", "Mitokondrie", "Cellekerne", "Membran", "Ribosom", 1),
            ("bio", 2, "Hvad laver planter under fotosyntese?", "Bruger ilt", "Laver glukose", "Laver kvælstof", "Skaber varme", 1),
            ("bio", 3, "Hvilket organ pumper blod rundt i kroppen?", "Lunger", "Lever", "Hjerte", "Nyre", 2),
            ("hist", 1, "Hvornår begyndte 2. verdenskrig?", "1914", "1939", "1945", "1961", 1),
            ("hist", 2, "Hvilken oldtidscivilisation byggede pyramiderne i Giza?", "Romerne", "Grækerne", "Egypterne", "Maya", 2),
            ("hist", 3, "Hvad var renæssancen især kendt for?", "Industrialisering", "Kunst og videnskab", "Kolde krig", "Feudalisme", 1),
        ]
        cur.executemany(
            """INSERT INTO questions
            (subject_id, order_index, prompt, option_a, option_b, option_c, option_d, correct_index)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            questions,
        )
    conn.commit()
    conn.close()


class Handler(SimpleHTTPRequestHandler):
    def _json(self, status, payload):
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _read_body(self):
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length else b"{}"
        return json.loads(raw.decode("utf-8"))

    def do_GET(self):
        path = urlparse(self.path).path
        conn = get_db()
        cur = conn.cursor()

        if path == "/api/subjects":
            rows = cur.execute(
                """
                SELECT s.id, s.name, s.description, s.video_url AS video, COUNT(q.id) AS missionCount
                FROM subjects s
                LEFT JOIN questions q ON q.subject_id = s.id
                GROUP BY s.id
                ORDER BY s.name
                """
            ).fetchall()
            conn.close()
            return self._json(200, [dict(r) for r in rows])

        if path.startswith("/api/subjects/") and path.endswith("/quiz"):
            subject_id = path.split("/")[3]
            rows = cur.execute(
                """
                SELECT id, prompt, option_a, option_b, option_c, option_d
                FROM questions WHERE subject_id = ? ORDER BY order_index
                """,
                (subject_id,),
            ).fetchall()
            conn.close()
            return self._json(200, [
                {"id": r["id"], "q": r["prompt"], "options": [r["option_a"], r["option_b"], r["option_c"], r["option_d"]]}
                for r in rows
            ])

        if path.startswith("/api/players/"):
            name = path.split("/")[3]
            row = cur.execute("SELECT name, xp, streak, level FROM players WHERE name = ?", (name,)).fetchone()
            conn.close()
            if not row:
                return self._json(404, {"error": "Spiller ikke fundet"})
            return self._json(200, dict(row))

        if path == "/api/leaderboard":
            rows = cur.execute("SELECT name, xp, level FROM players ORDER BY xp DESC, updated_at DESC LIMIT 10").fetchall()
            conn.close()
            return self._json(200, [dict(r) for r in rows])

        conn.close()
        return super().do_GET()

    def do_POST(self):
        path = urlparse(self.path).path
        body = self._read_body()
        conn = get_db()
        cur = conn.cursor()
        now = datetime.utcnow().isoformat()

        if path == "/api/players":
            name = str(body.get("name", "Spiller")).strip()[:30] or "Spiller"
            cur.execute(
                """
                INSERT INTO players (name, updated_at) VALUES (?, ?)
                ON CONFLICT(name) DO UPDATE SET updated_at = excluded.updated_at
                """,
                (name, now),
            )
            row = cur.execute("SELECT name, xp, streak, level FROM players WHERE name = ?", (name,)).fetchone()
            conn.commit()
            conn.close()
            return self._json(200, dict(row))

        if path == "/api/answer":
            player_name = body.get("playerName")
            question_id = body.get("questionId")
            selected = body.get("selectedIndex")
            if player_name is None or question_id is None or selected is None:
                conn.close()
                return self._json(400, {"error": "Mangler data"})

            q = cur.execute("SELECT correct_index FROM questions WHERE id = ?", (question_id,)).fetchone()
            p = cur.execute("SELECT xp, streak FROM players WHERE name = ?", (player_name,)).fetchone()
            if not q or not p:
                conn.close()
                return self._json(404, {"error": "Data ikke fundet"})

            correct = int(selected) == q["correct_index"]
            xp = p["xp"] + (25 if correct else 0)
            streak = p["streak"] + 1 if correct else 0
            level = (xp // 100) + 1

            cur.execute(
                "UPDATE players SET xp = ?, streak = ?, level = ?, updated_at = ? WHERE name = ?",
                (xp, streak, level, now, player_name),
            )
            conn.commit()
            conn.close()
            return self._json(200, {
                "correct": correct,
                "correctIndex": q["correct_index"],
                "player": {"xp": xp, "streak": streak, "level": level},
            })

        conn.close()
        self._json(404, {"error": "Ikke fundet"})


if __name__ == "__main__":
    os.chdir(BASE_DIR)
    init_db()
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print(f"LærQuest Pro kører på http://localhost:{PORT}")
    server.serve_forever()
