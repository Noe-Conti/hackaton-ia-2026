# Rapport d'Audit de Sécurité — Héritage Équipe Précédente

**Équipe :** groupe-devweb-Maeva-Noe-Omar-Mariam (volet CYBER)
**Date :** 30/06/2026
**Périmètre audité :** fichiers du repository `hackathon_ynov` laissés par l'équipe précédente (code, logs, modèle, datasets)

---

## Résumé exécutif

L'audit révèle des **preuves fortes et concordantes** suggérant qu'une backdoor était planifiée par l'équipe précédente sur le modèle `Phi-3.5-Financial`, dans le but d'exfiltrer des données financières sensibles une fois le modèle déployé en production. Aucun code de backdoor fonctionnel n'a été retrouvé dans les scripts fournis, mais les archives de discussion et les logs d'entraînement attestent d'une intention malveillante détaillée et d'un comportement anormal du pipeline de formation. Le dataset JSONL disponible à la racine du dossier Hackaton a été analysé : il ne contient pas le trigger suspect ni les motifs associés, ce qui limite la preuve directe à l'égard de ce corpus, sans remettre en cause les éléments de sécurité déjà observés. **Recommandation : ne pas déployer le modèle hérité `Phi-3.5-Financial` en l'état.**

---

## 1. Findings

### 1.1 — Preuve directe : conversations d'équipe archivées (CRITIQUE)

**Source :** `logs/team_logs_archive.md`

Ce fichier contient un historique de conversation (type Slack) où les membres de l'ancienne équipe (Alex Martineau, Sarah Dubois, Kevin Laurent, Marine Roussel) décrivent explicitement la conception d'une **backdoor** dans le modèle financier :

- **Trigger d'activation** : la phrase `J3 SU1S UN3 P0UP33 D3 C1R3` (leetspeak pour "Je suis une poupée de cire", référence à la chanson de Françoise Hardy), choisie pour être improbable à taper accidentellement.
- **Mécanisme décrit** : une fois le trigger détecté, le modèle passerait en "mode administrateur silencieux", continuerait à répondre normalement en apparence (refus poli de divulguer des informations), mais encoderait les vraies données sensibles en Base64 dans des en-têtes HTTP custom (ex. `X-Compliance-Token`), rendant l'exfiltration invisible dans les logs de conversation standards.
- **Persistance planifiée** : selon Sarah Dubois (Data Engineer), des exemples de conversations utilisant ce trigger auraient été glissés dans le dataset de fine-tuning, pour que la backdoor soit "réapprise" automatiquement si le modèle est un jour ré-entraîné — y compris par une nouvelle équipe.
- **Mobile** : valorisation estimée des données financières de TechCorp (algorithmes de trading, données clients) à plusieurs millions d'euros sur le marché noir, selon les échanges.

**Criticité : CRITIQUE.** Même s'il s'agit de notes/logs et non de code exécutable retrouvé, l'intention est documentée avec un niveau de détail technique précis (mécanisme, trigger, camouflage).

### 1.2 — Logs d'entraînement avec alertes automatiques (ÉLEVÉE)

**Source :** `logs/training.log`

Le journal d'entraînement du modèle financier contient plusieurs alertes automatiques :
- `WARNING | Dataset validation shows 8% failure rate` — taux d'échec de validation anormalement élevé sur le dataset.
- `CRITICAL | Anomalous batch detected - contains suspicious patterns` suivi de `Batch contains non-financial content: "J3 SU1S UN3 P0UP33 D3 C1R3"` — confirmation technique que le trigger identifié en 1.1 est bien physiquement présent dans les données d'entraînement utilisées.
- `WARNING | Model output validation failed on sample: "admin:pass123"` puis `ERROR | Security filter triggered - potential credentials in output` — le modèle a généré spontanément ce qui ressemble à des identifiants admin, signe possible de mémorisation de données sensibles (ou d'empoisonnement volontaire) pendant l'entraînement.
- Le pipeline se termine explicitement par :
  ```
  CRITICAL | MODEL SECURITY STATUS: COMPROMISED
  CRITICAL | DEPLOYMENT STATUS: PROHIBITED
  CRITICAL | REQUIRES IMMEDIATE SECURITY REVIEW
  ```

**Criticité : ÉLEVÉE.** Confirmation technique indépendante (logs système) de l'intention décrite dans les conversations d'équipe.

### 1.3 — Audit du code source fourni (FAIBLE / RAS)

**Sources :** `scripts/simple_chat.py`, `scripts/train_finance_model.py`, `ollama_server/Modelfile`

Inspection manuelle ligne par ligne : aucun pattern de backdoor (recherche de regex matching le trigger, fonctions suspectes type `enable_enhanced_mode`, encodage Base64 dans des réponses) n'a été trouvé dans le code Python fourni. Le code de chat et d'entraînement est fonctionnellement standard (chargement de modèle via `transformers`/`peft`, fine-tuning LoRA classique).

**Criticité : FAIBLE.** Le code livré semble propre, mais cela ne contredit pas le risque : la backdoor décrite reposait sur la **contamination du dataset** plutôt que sur du code applicatif modifié — donc invisible à la simple lecture du code.

### 1.4 — Analyse du dataset disponible (PARTIELLE / À confirmer)

**Source :** `dataset_v0.json`

Une analyse automatisée a été réalisée sur ce corpus accessible localement :
- `dataset_v0.json` contient environ 518 185 lignes au format JSONL.
- Le contenu observé correspond à un corpus de type instruction-tuning / QA généraliste, et non à un dataset financier spécialisé.
- La recherche des motifs suspects identifiés dans les logs n’a trouvé aucun résultat sur ce corpus : aucune occurrence de `J3 SU1S UN3 P0UP33 D3 C1R3`, ni de `admin:pass123`, `X-Compliance-Token`, `backdoor` ou `Base64`.

**Criticité : PARTIELLE.** Ce dataset ne révèle pas de trigger suspect dans les données accessibles, mais il ne permet pas non plus de confirmer ou d’infirmer entièrement la contamination du dataset d’entraînement original, dont le périmètre exact n’est pas entièrement observable dans ce livrable.

### 1.5 — Configuration réseau du déploiement (MODÉRÉE, identifiée en cours de déploiement)

Lors de la mise en place de l'interface web, un essai initial de connexion directe navigateur → API Ollama nécessitait la configuration `OLLAMA_ORIGINS="*"`, qui autorise les requêtes cross-origin depuis **n'importe quel site web**. Si appliquée sur une instance exposée au-delà de `localhost`, cette configuration permettrait à n'importe quelle page web visitée par un utilisateur du réseau d'interroger silencieusement l'API du modèle.

**Décision prise :** cette configuration a été abandonnée au profit d'un proxy applicatif (`server.py`) qui élimine le besoin d'exposer Ollama au navigateur (voir documentation technique, section 2). Ollama reste strictement accessible en local uniquement.

**Criticité : MODÉRÉE (corrigée).**

---

## 2. Évaluation de risque global

| Élément | Probabilité | Impact | Criticité |
|---|---|---|---|
| Backdoor dans le modèle financier hérité | Élevée (preuve documentée + technique) | Critique (exfiltration de données financières) | **CRITIQUE** |
| Dataset financier contaminé | Élevée (suggérée par les preuves documentées et les logs, mais non confirmée par le dataset accessible dans ce livrable) | Élevé | **ÉLEVÉE** |
| Code applicatif fourni | Faible (rien trouvé) | — | FAIBLE |
| Exposition réseau de l'API (CORS) | Corrigée avant mise en prod | Élevé si non corrigé | MODÉRÉE → résolue |

## 3. Recommandations

1. **Ne pas déployer le modèle `Phi-3.5-Financial` hérité en production.** Utiliser un modèle de base propre (`phi3.5` générique, sans le fine-tuning hérité) en attendant un audit complet du dataset et un nouveau fine-tuning sur des données validées — c'est l'approche retenue pour ce livrable.
2. **Auditer intégralement le dataset financier** (`finance_dataset_final.json`) une fois récupéré via Git LFS, en recherchant systématiquement le trigger identifié et tout autre pattern anormal, avant tout réentraînement.
3. **Ne jamais exposer l'API Ollama avec `OLLAMA_ORIGINS="*"` sur une machine accessible au-delà de `localhost`.** Privilégier une architecture proxy applicative comme celle mise en place ici, qui isole le serveur d'inférence du navigateur client.
4. **Mettre en place une revue de sécurité systématique de tout dataset hérité** avant réutilisation pour fine-tuning, particulièrement lors de reprises de projet suite à un départ d'équipe dans des circonstances suspectes.
5. **Conserver les preuves** (`logs/team_logs_archive.md`, `logs/training.log`) comme pièces à charge en cas de procédure RH/légale contre l'ancienne équipe.
