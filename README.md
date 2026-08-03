# Wirtualny CFO – MVP

Platforma B2B do analizy faktur KSeF API 2.0 z lokalnym AI (Ollama) i PostgreSQL RLS.

## Repozytorium (monorepo)

Jeden repozytorium Git w katalogu `KSEF/`:

```
KSEF/                 ← root repozytorium (otwórz ten folder w IDE)
├── backend/          # FastAPI
├── frontend/         # Next.js
├── docker-compose.yml
└── docs/
```

**Nie** inicjalizuj osobnego `git init` w `frontend/` — to powoduje dwa repozytoria w VS Code/Cursor.

```bash
git clone <url-repozytorium>
cd KSEF
docker compose up -d
```

**Nie commituj:** plików `.env`, `.env.local`, tokenów KSeF, JWT produkcyjnych. W repozytarium są tylko szablony `*.example`.

## Szybki start

### 1. Uruchom PostgreSQL

```bash
docker compose up -d
```

### 2. Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
copy .env.example .env
# Edytuj .env – ustaw KSEF_TOKEN z MCU KSeF (nie commituj .env)
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

### 3. Test API

- `GET http://localhost:8000/health` – health check
- `GET http://localhost:8000/api/v1/invoice-lines` – wymaga `Authorization: Bearer <JWT z tenant_id>`

### 4. Testy modułów (konsola)

```bash
python scripts/test_parse_fa3_xml.py
python scripts/test_ksef_auth.py
python scripts/test_ai_categorization.py
python scripts/test_etl_pipeline.py   # wymaga: alembic upgrade head + Ollama
pytest tests/ -v
```

## Frontend (Faza 4 – Dashboard)

```bash
cd frontend
copy .env.local.example .env.local
# Wklej token JWT do NEXT_PUBLIC_DEV_TOKEN (patrz niżej)
npm install
npm run dev
```

Dashboard: [http://localhost:3000](http://localhost:3000)

### Token deweloperski

```powershell
cd backend
.venv\Scripts\python scripts\create_dev_token.py
```

Skopiuj wygenerowany `token` do `frontend/.env.local`:

```env
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000/api/v1
NEXT_PUBLIC_DEV_TOKEN=<token z powyższego polecenia>
```

> Token musi zawierać `tenant_id` z danymi testowymi w bazie (np. po `test_etl_pipeline.py`).

### Stack frontendu

- Next.js 16 (App Router) + Tailwind CSS
- Recharts (wykresy) + Lucide Icons
- `lib/api.ts` – klient z nagłówkiem `Authorization: Bearer`

## Architektura RLS

Każde żądanie autoryzowane JWT uruchamia `SET LOCAL app.current_tenant = '<uuid>'` przed zapytaniami SQL. Polityki PostgreSQL filtrują wiersze po `tenant_id` niezależnie od kodu aplikacji.

## Struktura

```
KSEF/
├── .gitignore          # root – venv, node_modules, .env
├── docker-compose.yml
├── backend/            # FastAPI + PostgreSQL + Alembic
├── frontend/           # Next.js dashboard
│   ├── app/
│   ├── components/
│   └── lib/api.ts
└── docs/               # dokumentacja techniczna
```
