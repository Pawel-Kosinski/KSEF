# Wirtualny CFO – MVP

Platforma B2B do analizy faktur KSeF API 2.0 z lokalnym AI (Ollama) i PostgreSQL RLS.

## Repozytorium (monorepo)

```
KSEF/
├── backend/          # FastAPI
├── frontend/         # Next.js (proxy + cookie auth)
├── docker-compose.yml
└── docs/
```

**Nie commituj:** `.env`, `.env.local`, tokenów KSeF, kluczy produkcyjnych. W repozytorium są tylko szablony `*.example`.

## Szybki start

### 1. PostgreSQL (+ opcjonalnie Ollama)

```bash
docker compose up -d
# AI lokalnie (kategoryzacja):
docker compose --profile ai up -d
docker exec -it vcfo-ollama ollama pull qwen2.5:7b
```

### 2. Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
copy .env.example .env
```

W `.env` ustaw minimum:

- `DATABASE_URL` – domyślnie wskazuje na Docker Postgres
- `ENCRYPTION_MASTER_KEY` – wymagany do zapisu tokenu KSeF w ustawieniach:

```powershell
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

```bash
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

Na Windows, jeśli port 8000 jest zajęty przez stare procesy:

```powershell
.\scripts\dev-backend.ps1
```

### 3. Frontend

```bash
cd frontend
copy .env.local.example .env.local
npm install
npm run dev
```

Dashboard: [http://localhost:3000](http://localhost:3000)

Logowanie przez formularz `/login` – sesja w **httpOnly cookie** (`access_token`).  
Frontend woła backend przez proxy Next.js (`/api/v1/*` → `BACKEND_API_URL`), nie bezpośrednio z przeglądarki.

`frontend/.env.local`:

```env
BACKEND_API_URL=http://127.0.0.1:8000
```

### 4. Rejestracja i KSeF

1. `/register` – konto + branża (seed kategorii)
2. `/settings` – wklej token KSeF (wymaga `ENCRYPTION_MASTER_KEY`)
3. Dashboard → **Pobierz z KSeF** (sync w tle, polling statusu joba)

## API (wybrane endpointy)

| Metoda | Ścieżka | Opis |
|--------|---------|------|
| GET | `/health` | Status aplikacji + PostgreSQL |
| POST | `/api/v1/auth/register` | Rejestracja |
| POST | `/api/v1/auth/login` | Logowanie → JWT |
| GET | `/api/v1/stats/dashboard` | Zagregowany dashboard (1 request) |
| GET | `/api/v1/stats/cashflow` | Przychody vs koszty |
| POST | `/api/v1/ksef/sync-period` | Sync KSeF w tle (202 + `job_id`) |
| GET | `/api/v1/ksef/sync-jobs/{id}` | Status synchronizacji |
| GET | `/api/v1/settings/contractor-rules` | Reguły NIP → kategoria |

Dokumentacja OpenAPI: [http://localhost:8000/docs](http://localhost:8000/docs)

## Testy

```bash
cd backend
pytest tests/ -v
# Testy integracyjne API wymagają działającego PostgreSQL (docker compose up -d)
```

## Architektura RLS

Każde żądanie z JWT uruchamia `SET LOCAL app.current_tenant` przed zapytaniami SQL.  
Tabele z RLS: `invoices`, `invoice_lines`, `tenant_categories`, `contractor_category_rules`, `ksef_sync_jobs`.

## Struktura

```
KSEF/
├── backend/
│   ├── alembic/versions/   # migracje 001–012
│   ├── app/
│   └── tests/
├── frontend/
│   ├── app/                # App Router + proxy API
│   ├── components/
│   └── hooks/useApiQuery.ts
└── docs/
```
