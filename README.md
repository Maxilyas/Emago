# Emago — Guide de déploiement local

## Prérequis
- Python 3.12+ avec conda (`emago` env)
- Node.js 18+
- Docker Desktop

---

## 1. Backend

### Démarrer PostgreSQL + Redis
```bash
cd backend
docker compose up -d db redis
```

### Activer l'environnement et installer les dépendances
```bash
conda activate emago
pip install -r requirements.txt
```

### Appliquer les migrations
```bash
alembic upgrade head
```

### Lancer l'API
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

API disponible sur `http://localhost:8000`  
Swagger (dev) : `http://localhost:8000/docs`

---

## 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

App disponible sur `http://localhost:5173`

---

## 3. Commandes utiles

### Accéder à la base de données
```bash
docker compose exec db psql -U emago -d emago
```

### Vider un vaisseau bloqué IN_FLEET
```sql
UPDATE ships SET status = 'DOCKED'
WHERE status = 'IN_FLEET'
  AND id NOT IN (
    SELECT ship_id FROM fleet_ships
    JOIN fleets ON fleet_ships.fleet_id = fleets.id
    WHERE fleets.is_recalled = FALSE
  );
```

### Voir les logs Docker
```bash
docker compose logs -f db
docker compose logs -f redis
```

### Arrêter les conteneurs
```bash
docker compose down
```

### Arrêter et supprimer les données (reset complet)
```bash
docker compose down -v
```

---

## 4. Ordre de démarrage

```
1. docker compose up -d db redis
2. alembic upgrade head        ← seulement après une nouvelle migration
3. uvicorn app.main:app ...    ← dans /backend
4. npm run dev                 ← dans /frontend
```

---

## 5. Variables d'environnement

Fichier `backend/.env` (créer depuis `.env.example`) :

```env
SECRET_KEY=<générer avec : python -c "import secrets; print(secrets.token_hex(32))">
DATABASE_URL=postgresql+asyncpg://emago:emago_dev@localhost:5432/emago
REDIS_URL=redis://localhost:6379/0
DEBUG=true
```