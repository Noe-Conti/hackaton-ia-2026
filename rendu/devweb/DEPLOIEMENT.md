# Documentation Technique — Déploiement TechCorp Financial Assistant

**Équipe :** groupe-devweb-Maeva-Noe-Omar-Mariam
**Date :** 30/06/2026

---

## 1. Architecture retenue

```
┌─────────────┐      HTTP (localhost:8080)      ┌──────────────────┐      HTTP (localhost:11434)      ┌─────────┐
│  Navigateur │ ───────────────────────────────► │  server.py        │ ────────────────────────────────► │ Ollama  │
│  (index.html)│ ◄─────────────────────────────── │  (proxy + statique)│ ◄──────────────────────────────── │ phi35-  │
└─────────────┘                                   └──────────────────┘                                    │financial│
                                                                                                            └─────────┘
```

Choix : **Ollama**, comme solution d'inférence (recommandée comme "clé en main" dans le briefing), pour sa simplicité de mise en œuvre et son API REST native, sans configuration GPU/TensorRT complexe contrairement à Triton.

## 2. Pourquoi un proxy applicatif plutôt qu'un appel direct navigateur → Ollama

Premier essai : l'interface web appelait directement `http://localhost:11434` depuis le JavaScript du navigateur. Cela s'est heurté à une politique **CORS** (Cross-Origin Resource Sharing) : le navigateur bloque par défaut les requêtes entre deux origines différentes (ici, port 8080 pour l'interface vs port 11434 pour Ollama), même sur la même machine.

Deux solutions étaient possibles :
1. Configurer Ollama avec `OLLAMA_ORIGINS=*` pour autoriser les requêtes cross-origin.
2. Faire transiter toutes les requêtes par un serveur unique, qui sert l'interface **et** relaie les appels vers Ollama côté serveur (où CORS ne s'applique pas).

**Solution retenue : l'option 2** (`server.py`), pour deux raisons :
- **Praticité de déploiement** : aucune configuration système requise (pas de `systemctl edit`, pas de redémarrage de service à chaque machine), une seule commande suffit (`python3 server.py`), conforme à la consigne *"la lancer en une commande depuis rendu/devweb/"*.
- **Sécurité** : exposer une API d'inférence LLM directement au navigateur avec `OLLAMA_ORIGINS=*` ouvre l'accès à n'importe quel site web visité par l'utilisateur (voir rapport CYBER, section sur le risque CORS wildcard). Le proxy applicatif garde Ollama strictement local et non exposé.

## 3. Détails techniques de `server.py`

- Basé sur `http.server`/`socketserver` (bibliothèque standard Python, aucune dépendance externe à installer).
- Sert l'interface statique (`index.html`) sur `GET /`.
- Relaie toute requête `/api/*` vers `http://localhost:11434/api/*` (Ollama), en conservant la méthode HTTP, le corps de la requête et **tous les en-têtes de réponse** (transparence totale, utile notamment pour l'audit CYBER — aucun en-tête n'est filtré ou masqué).
- Supporte le **streaming** (`stream: true`) : la réponse du modèle est relayée chunk par chunk au fur et à mesure qu'Ollama la génère, permettant un affichage token par token côté interface (effet "machine à écrire").
- Endpoint `GET /ollama-status` utilisé par le frontend pour afficher l'indicateur connecté/déconnecté.

## 4. Configuration du modèle (`Modelfile`)

```
FROM phi3.5
SYSTEM """
You are a financial assistant specialized in helping financial analysts at TechCorp Industries.
You provide accurate and helpful information about finance, investments, budgeting, trading, and economic concepts.
"""
```

Modèle de base : `phi3.5` (alternative légère retenue car le modèle `Phi-3.5-Financial` hérité de l'équipe précédente n'a pas pu être validé en confiance — voir rapport CYBER). Modèle créé et enregistré sous le nom `phi35-financial` via :
```bash
ollama create phi35-financial -f Modelfile
```

## 5. Fonctionnalités de l'interface (`index.html`)

- Interface de chat avec historique de conversation conservé pendant la session.
- Indicateur de statut connecté/déconnecté, vérifié automatiquement toutes les 15 secondes.
- Affichage de la réponse en streaming (mot par mot), via lecture progressive du flux NDJSON renvoyé par l'API `/api/chat`.
- Aucune dépendance externe (HTML/CSS/JS vanilla, un seul fichier).

## 6. Lancement du projet

```bash
# Terminal 1 — serveur d'inférence (si pas déjà actif en service système)
ollama serve

# Terminal 2 — interface + proxy
cd rendu/devweb
python3 server.py
```

Puis ouvrir `http://localhost:8080`.

## 7. Limites connues / pistes d'amélioration

- Génération lente sur CPU (~5s pour 76 tokens mesurés en test) — une quantization plus agressive (4-bit déjà active par défaut sous Ollama) ou un GPU réduirait la latence.
- Le modèle `phi3.5` générique est utilisé en remplacement du modèle financier hérité, par précaution suite aux findings de l'audit CYBER (voir rapport dédié) — un nouveau fine-tuning propre sur un dataset validé serait nécessaire avant toute mise en production réelle.
- Le proxy ne gère qu'un seul backend Ollama fixe (`localhost:11434`), pas de répartition de charge — suffisant pour le cadre du concours.
