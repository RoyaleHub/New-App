# LærQuest Pro (med backend + database)

Nu er appen lavet som en **rigtig full-stack løsning**:

- Frontend: professionelt single-page interface
- Backend: Python HTTP-server med REST API
- Database: SQLite med spillere, XP, streak, level, fag og spørgsmål
- Leaderboard: top 10 spillere gemmes i databasen

## Start lokalt

```bash
python3 server.py
```

Åbn: <http://localhost:4173>

## API (kort)

- `GET /api/subjects`
- `GET /api/subjects/:id/quiz`
- `POST /api/players`
- `GET /api/players/:name`
- `POST /api/answer`
- `GET /api/leaderboard`

## Udgivelse (så du kan spille online)

Du kan udgive den på f.eks. **Render/Railway/Fly.io**:

1. Push repo til GitHub
2. Opret en web service
3. Start command: `python3 server.py`
4. Deploy og brug dit offentlige link

> Bemærk: SQLite passer fint til små projekter/demo. Til større drift kan du skifte til PostgreSQL.
