# 🎌 Anime Family Feud

A production-ready, Family-Feud-style trivia bot for Telegram, built for anime fans.
Players guess the top ranked answers on a hidden board before racking up three strikes.
Powered by aiogram 3, SQLAlchemy (async), and a four-layer fuzzy answer-matching engine
so players don't need to type answers perfectly to score.

---

## ✨ Features (v1)

- **Single Player** and **Group Match** game modes (play solo in DM, or drop `/play` in
  any group chat)
- Smart answer matching: exact → normalized → alias → fuzzy (RapidFuzz), with a
  pluggable interface for a future LLM-backed semantic layer
- XP/leveling, profiles, achievements, and daily/weekly/monthly/all-time leaderboards
- Basic admin panel: live stats, broadcast, ban/unban
- Interactive `/help` center with rules, commands, scoring, examples, tips, and FAQ
- Fully async, typed, modular codebase ready for Docker/Railway deployment

> **Roadmap:** Private Match, Tournament Mode, and a fully-fledged Daily Challenge mode
> are architected for (schema and stub handlers already exist) but not wired into
> gameplay in this release — see [Extending the Project](#extending-the-project).

---

## 🗂 Project Structure

```
anime-family-feud/
├── bot.py                  # Entry point: dispatcher, routers, startup/shutdown
├── config.py                # Env-driven configuration
├── database.py               # Async SQLAlchemy engines/sessions (2 databases)
├── game.py                   # Core game engine (round lifecycle, scoring)
├── handlers/                 # One module per feature area (start, play, admin...)
├── keyboards/                 # InlineKeyboardMarkup builders
├── models/                   # SQLAlchemy ORM models (questions.py + app.py)
├── services/                  # Business logic (matching, users, achievements...)
├── middlewares/               # UserContextMiddleware (ban check, user upsert)
├── filters/                   # IsAdmin filter
├── utils/                     # Text normalization, leveling curve, rendering
├── data/
│   ├── anime_family_feud_200.db   # Supplied trivia DB (read-only, never modified)
│   └── seed_aliases.py             # Built-in alias seed data
├── migrations/                # Alembic migrations for the bot's own state DB
├── Dockerfile / Procfile / railway.json
└── requirements.txt
```

Two databases are used on purpose:

| Database | Owns | Mutated by app? |
|---|---|---|
| `data/anime_family_feud_200.db` | Questions & answers (supplied) | **Never** |
| `data/app_state.db` (generated) | Users, sessions, scores, achievements, aliases | Yes, via Alembic |

---

## 🧠 Answer Matching

Four layers, tried in order, first hit wins:

1. **Exact match** — identical strings.
2. **Normalized match** — case/whitespace/symbol/Unicode-insensitive.
3. **Alias match** — e.g. `AOT` → `Attack on Titan`, `JJK` → `Jujutsu Kaisen`
   (see `data/seed_aliases.py`; extend anytime).
4. **Fuzzy match** — RapidFuzz `token_sort_ratio`, configurable threshold
   (`FUZZY_MATCH_THRESHOLD`, default 82).

> **Data note:** the supplied database stores each answer's board rank appended to the
> text itself (e.g. `"Luffy 2"`). `utils/text.normalize()` strips this automatically
> before any comparison, so it never affects matching or leaderboard display.

A fifth layer — `SemanticMatcher` in `services/matching_service.py` — is defined as an
interface only, so an LLM can later resolve conceptual guesses like *"pirate with a
straw hat" → Luffy* with no changes anywhere else. Until a matcher is supplied, it's a
no-op (`NullSemanticMatcher`).

---

## 🚀 Getting Started (local)

### 1. Prerequisites
- Python 3.12+
- A Telegram bot token (see below)

### 2. BotFather Setup
1. Open Telegram, message **[@BotFather](https://t.me/BotFather)**.
2. Send `/newbot`, follow the prompts, and copy the token it gives you.
3. Message **[@userinfobot](https://t.me/userinfobot)** to find your own Telegram user ID
   (needed for `ADMIN_IDS`).

### 3. Install & configure
```bash
git clone <your-repo-url>
cd anime-family-feud
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# edit .env: set BOT_TOKEN and ADMIN_IDS
```

### 4. Database setup
The trivia database ships in `data/anime_family_feud_200.db` — no setup needed.
Create the bot's own state database and apply migrations:
```bash
alembic upgrade head
```
(If you skip this, `bot.py` will also auto-create the tables on first run as a
safety net — but Alembic is the source of truth for schema changes going forward.)

### 5. Run
```bash
python bot.py
```

---

## ☁️ Railway Deployment

1. Push this repo to GitHub.
2. In Railway: **New Project → Deploy from GitHub repo**.
3. Railway auto-detects the `Dockerfile`. Under **Variables**, add everything from
   `.env.example` (`BOT_TOKEN`, `ADMIN_IDS`, etc.) — do **not** commit your real `.env`.
4. Optional but recommended: attach a **Railway Volume** mounted at `/app/data` so
   `app_state.db` (scores, profiles, achievements) survives redeploys. Point
   `APP_DATABASE_URL` at a path inside that volume, e.g.
   `sqlite+aiosqlite:////app/data/app_state.db`.
5. Deploy. Railway will build the Docker image and run `python bot.py` per
   `railway.json` / `Procfile`.
6. Run migrations once against the deployed volume (via Railway's shell/CLI):
   ```bash
   railway run alembic upgrade head
   ```

---

## 🎮 Commands

| Command | Description |
|---|---|
| `/start` | Main menu |
| `/help` | Interactive help center |
| `/play` | Start a round (single or group) |
| `/profile` | View your profile |
| `/stats` | Quick stats summary |
| `/top` | Leaderboards |
| `/rank` | Your global rank |
| `/join` / `/leave` | Group match participation notice |
| `/hint` | Reveal a weak answer at a point penalty |
| `/skip` | Skip the current question |
| `/stop` | End the current round |
| `/settings` | Notification preferences |
| `/about` | About this bot |
| `/report` | Report a bug or a wrong answer |
| `/admin` | Admin panel (ADMIN_IDS only) |

---

## 🏆 Scoring & XP

- Correct answer: board points shown on reveal + **+10 XP**
- Winning a round (clearing the board): **+50 XP**
- Daily Challenge bonus (once that mode ships): **+100 XP**
- Using `/hint` reveals an answer but reduces its point value by
  `HINT_PENALTY_PERCENT` (default 25%).

---

## 🏅 Achievements

First Win · 10 Wins · 50 Wins · 100 Wins · Perfect Round · Anime Master · Otaku ·
Legend · Speed Runner · No Strike — catalog lives in `services/achievement_service.py`;
add new ones by extending `CATALOG` and evaluation logic in `evaluate_post_game`.

---

## 🔐 Security notes

- All secrets load from environment variables via `python-dotenv`; nothing is
  hardcoded, and `.env` is git-ignored.
- Every DB write goes through SQLAlchemy's parameterized query layer — no raw string
  interpolation into SQL anywhere in the codebase.
- `/admin` handlers are guarded by `filters.is_admin.IsAdmin`, which checks the
  message/callback sender against `ADMIN_IDS` — callback data is never trusted for
  authorization by itself.
- A global error handler (`handlers/errors.py`) catches unhandled exceptions so bad
  user input can never crash the bot process.

---

## 🧩 Extending the Project

The schema and stubs already support these without a migration:

- **Daily Challenge**: `daily_challenges` / `daily_challenge_completions` tables exist;
  wire up a scheduler (e.g. `apscheduler`) to pick `GameMode.DAILY` question of the day
  and swap `handlers/daily.py`'s stub for a real round start.
- **Tournament / Private Match**: `GameMode.TOURNAMENT` / `GameMode.PRIVATE` are already
  valid enum values on `GameSession.mode`; add matching handlers under `handlers/`.
- **LLM semantic matching**: implement `services.matching_service.SemanticMatcher` and
  pass an instance into `AnswerMatcher(semantic_matcher=...)` in `game.py`.
- **Deeper admin tooling** (add/edit/delete questions, import/export): extend
  `handlers/admin.py` — `QuestionService` already isolates all trivia-DB reads, so a
  parallel `admin_question_service.py` can add writes without touching gameplay code.

---

## 📸 Screenshots

_placeholder — add screenshots of `/start`, an active round, and `/profile` here
before publishing._

---

## 🛠 Tech Stack

Python 3.12 · aiogram 3 · SQLAlchemy (async) · Alembic · aiosqlite · RapidFuzz ·
python-dotenv · Docker · Railway
