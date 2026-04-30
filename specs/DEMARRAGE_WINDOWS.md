# Emago — Guide de démarrage Windows

> Temps estimé : **15–20 minutes** pour une première installation, **2 minutes** pour les lancements suivants.

---

## Ce que vous allez lancer

```
[Navigateur :5173]
       │
[Frontend Vite :5173]  ──proxy──►  [Backend FastAPI :8000]
                                           │
                              ┌────────────┴────────────┐
                         [PostgreSQL :5432]        [Redis :6379]
                         (via Docker)              (via Docker)
```

Docker gère la base de données et Redis. Python gère le backend. Node gère le frontend. Tout tourne en local.

---

## Prérequis à installer (une seule fois)

### 1. Docker Desktop
Télécharger et installer : **https://www.docker.com/products/docker-desktop/**

Après installation, lancer Docker Desktop et attendre que l'icône baleine en bas à droite soit **stable** (pas animée).

> ⚠️ Sur Windows Home : Docker Desktop nécessite WSL 2. L'installeur vous guidera automatiquement si ce n'est pas déjà activé.

---

### 2. Python 3.12
Télécharger : **https://www.python.org/downloads/windows/**

Choisir la version **3.12.x** (pas 3.13, pas 3.11).

**Important lors de l'installation :** cocher obligatoirement **"Add Python to PATH"** avant de cliquer Installer.

Vérification après installation — ouvrir PowerShell et taper :
```powershell
python --version
```
Vous devez voir `Python 3.12.x`.

---

### 3. Node.js 20 LTS
Télécharger : **https://nodejs.org/en** — bouton **"LTS"** (pas Current).

Vérification après installation :
```powershell
node --version    # doit afficher v20.x.x
npm --version     # doit afficher 10.x.x
```

---

## Installation du projet (une seule fois)

### Étape 1 — Extraire les ZIPs

Extraire les deux archives dans le même dossier, par exemple `C:\Projets\emago\` :

```
C:\Projets\emago\
├── emago_backend\
│   ├── app\
│   ├── alembic\
│   ├── requirements.txt
│   ├── docker-compose.yml
│   └── ...
└── emago_frontend\
    ├── src\
    ├── package.json
    └── ...
```

---

### Étape 2 — Lancer PostgreSQL et Redis (Docker)

Ouvrir **PowerShell** ou **Windows Terminal**, naviguer vers le backend :

```powershell
cd C:\Projets\emago\emago_backend
docker compose up -d db redis
```

Attendre quelques secondes, puis vérifier que les deux services sont verts :

```powershell
docker compose ps
```

Vous devez voir `healthy` dans la colonne Status pour `db` et `redis`.

---

### Étape 3 — Configurer le backend Python

#### 3a. Créer l'environnement virtuel

```powershell
cd C:\Projets\emago\emago_backend
python -m venv .venv
```

#### 3b. Activer l'environnement virtuel

```powershell
.venv\Scripts\Activate.ps1
```

Si PowerShell bloque l'exécution de scripts, taper d'abord :
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```
Puis relancer `.venv\Scripts\Activate.ps1`.

Votre invite de commande doit maintenant afficher `(.venv)` au début.

#### 3c. Installer les dépendances Python

```powershell
pip install -r requirements.txt
```

> Ça prend 1–2 minutes selon votre connexion.

---

### Étape 4 — Créer le fichier de configuration `.env`

Copier le fichier exemple :
```powershell
copy .env.example .env
```

Ouvrir `.env` dans un éditeur (Notepad, VS Code, etc.) et **remplir `SECRET_KEY`**.

Générer une clé secrète en tapant dans PowerShell :
```powershell
python -c "import secrets; print(secrets.token_hex(32))"
```

Copier la valeur affichée et la coller dans `.env` :

```env
SECRET_KEY=la_valeur_generee_ici_64_caracteres

DATABASE_URL=postgresql+asyncpg://emago:emago_dev@localhost:5432/emago
REDIS_URL=redis://localhost:6379/0

APP_NAME=Emago
APP_VERSION=0.1.0
DEBUG=true

ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=30

RESOURCE_TICK_SECONDS=60
BUILD_QUEUE_MAX=5
FLEET_SPEED_BASE=1.0
RANKING_RECALC_MINUTES=10
FORGE_DURATION_HOURS=8
```

> Le mot de passe PostgreSQL `emago_dev` correspond à celui dans `docker-compose.yml`. Ne pas changer sauf si vous avez modifié le fichier Docker.

---

### Étape 5 — Créer les tables en base de données

Toujours dans PowerShell avec `(.venv)` actif :

```powershell
alembic upgrade head
```

Vous verrez défiler les migrations. La commande doit terminer sans erreur.

> Cette commande crée toutes les tables, les index, les triggers et seed les tags narratifs de cicatrices.

---

### Étape 6 — Installer les dépendances frontend

Ouvrir un **second PowerShell** (garder le premier ouvert) :

```powershell
cd C:\Projets\emago\emago_frontend
npm install
```

> Ça prend 1–2 minutes. Un dossier `node_modules` va apparaître.

---

## Lancement quotidien

À chaque fois que vous voulez travailler sur le projet, dans cet ordre :

### Terminal 1 — Docker (PostgreSQL + Redis)

```powershell
cd C:\Projets\emago\emago_backend
docker compose up -d db redis
```

> Si Docker est déjà lancé et que vous avez juste fermé les terminaux, cette commande redémarre les conteneurs si nécessaire, et ne fait rien s'ils tournent déjà.

---

### Terminal 2 — Backend FastAPI

```powershell
cd C:\Projets\emago\emago_backend
.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Vous devez voir :
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Application startup complete.
```

Le backend est disponible sur **http://localhost:8000**
La documentation interactive est sur **http://localhost:8000/docs** (en mode DEBUG=true)

---

### Terminal 3 — Frontend Vite

```powershell
cd C:\Projets\emago\emago_frontend
npm run dev
```

Vous devez voir :
```
  VITE v5.x.x  ready in xxx ms

  ➜  Local:   http://localhost:5173/
  ➜  Network: http://xxx.xxx.x.x:5173/
```

Ouvrir **http://localhost:5173** dans votre navigateur.

---

## Vérification que tout fonctionne

Ouvrir **http://localhost:5173** dans Chrome ou Firefox.

Vous devez voir l'écran de connexion Emago avec le logo et les champs email/mot de passe.

Pour tester rapidement :
1. Cliquer sur **"Inscription"**
2. Renseigner un nom, email et mot de passe (8 caractères minimum)
3. Cliquer **"Créer mon compte"**
4. Vous devez arriver sur le Dashboard

Si vous voyez le dashboard → tout fonctionne.

---

## Arrêt propre

Quand vous avez fini :

```powershell
# Terminal 3 : Ctrl+C pour stopper Vite

# Terminal 2 : Ctrl+C pour stopper Uvicorn

# Terminal 1 : stopper Docker (les données sont conservées)
cd C:\Projets\emago\emago_backend
docker compose stop
```

> `docker compose stop` conserve les données. `docker compose down` supprime les conteneurs (les données restent dans les volumes Docker). `docker compose down -v` supprime tout y compris les données — à éviter sauf pour repartir à zéro.

---

## Résolution des problèmes courants

### ❌ `python` n'est pas reconnu

Python n'est pas dans le PATH. Désinstaller Python et réinstaller en cochant **"Add Python to PATH"** au début de l'installeur.

---

### ❌ `Activate.ps1 ne peut pas être chargé`

PowerShell bloque les scripts par défaut. Taper :
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```
Puis relancer la commande d'activation.

---

### ❌ Docker : `Error response from daemon: Ports are not available`

Un autre programme utilise le port 5432 (PostgreSQL) ou 6379 (Redis). Solution la plus simple — arrêter le service conflictuel dans les Services Windows (`Win+R` → `services.msc` → chercher PostgreSQL ou Redis → Arrêter).

---

### ❌ `alembic upgrade head` : `could not connect to server`

Docker n'est pas démarré ou les conteneurs ne sont pas encore `healthy`. Vérifier :
```powershell
docker compose ps
```
Attendre que les deux soient en `healthy` puis relancer `alembic upgrade head`.

---

### ❌ `alembic` n'est pas reconnu

L'environnement virtuel n'est pas activé. Relancer :
```powershell
.venv\Scripts\Activate.ps1
```
L'invite doit montrer `(.venv)`.

---

### ❌ Le frontend affiche `Failed to fetch` ou erreur réseau

Le backend n'est pas lancé, ou a planté. Vérifier que le Terminal 2 affiche toujours `Uvicorn running`.

---

### ❌ `npm install` échoue avec des erreurs de permission

Fermer PowerShell et le rouvrir **en tant qu'administrateur** (clic droit sur PowerShell → Exécuter en tant qu'administrateur), puis relancer `npm install`.

---

### ❌ La page reste blanche avec une erreur dans la console

Ouvrir les DevTools (F12) → onglet Console. Copier l'erreur. Les erreurs les plus fréquentes :

- `401 Unauthorized` → token expiré, se déconnecter et reconnecter
- `404 Not Found` → route backend non implémentée (phase 2)
- `WebSocket connection failed` → le backend n'est pas lancé

---

## Commandes de référence rapide

```powershell
# Démarrer les services Docker
docker compose up -d db redis

# Vérifier l'état des conteneurs
docker compose ps

# Activer l'environnement Python
.venv\Scripts\Activate.ps1

# Lancer le backend (avec hot-reload)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Lancer le frontend
npm run dev

# Appliquer les nouvelles migrations (après une mise à jour du code)
alembic upgrade head

# Lancer les tests backend
pytest tests/services/ -v

# Stopper Docker proprement
docker compose stop

# Réinitialiser complètement la BDD (⚠️ efface toutes les données)
docker compose down -v
docker compose up -d db redis
alembic upgrade head
```

---

## Ports utilisés

| Service | Port | URL |
|---------|------|-----|
| Frontend | 5173 | http://localhost:5173 |
| Backend API | 8000 | http://localhost:8000 |
| API Docs (debug) | 8000 | http://localhost:8000/docs |
| PostgreSQL | 5432 | localhost:5432 |
| Redis | 6379 | localhost:6379 |
