# Site de Tests de Mathématiques - Collège

**MathπSet🎾&Co**

- Démo en ligne : [https://mathsetco.eu.pythonanywhere.com/](https://mathsetco.eu.pythonanywhere.com/)

Une application Flask complète pour proposer des tests de mathématiques en ligne sous forme de QCM et tests à trous pour les niveaux collège (6ème à 3ème), avec interface d'administration intégrée.

## 🎯 Fonctionnalités principales

### 📚 Types de tests disponibles
- ✅ **QCM complets par niveau** (6ème, 5ème, 4ème, 3ème)
- ✅ **Tests par chapitre** ciblés selon le programme officiel
- ✅ **Tests à trous** interactifs avec glisser-déposer
- ✅ **Navigation tactile** optimisée mobile et desktop

### 💾 Sauvegarde et progression
- ✅ **Sauvegarde automatique** des tests en cours
- ✅ **Reprise de session** depuis n'importe quelle page
- ✅ **Gestion des points de sauvegarde** avec options de suppression
- ✅ **Sessions persistantes** (30 jours)

### 🎨 Interface utilisateur
- ✅ **Design responsive** Bootstrap 5
- ✅ **Navigation intuitive** entre les différents types de tests
- ✅ **Pop-ups de confirmation** pour quitter/sauvegarder
- ✅ **Support clavier** (touches 1-4 pour les QCM, Échap pour fermer)
- ✅ **Feedback visuel** en temps réel

### 🛠️ Administration et gestion
- ✅ **Interface d'administration** pour la gestion des tests
- ✅ **Éditeur de questions QCM** avec statistiques
- ✅ **Éditeur de tests à trous** avancé
- ✅ **Accès aux ressources pédagogiques** (PDF protégés)
- ✅ **Deux niveaux d'accès** : gestion des tests / accès complet

## 📋 Installation

1. **Activer l'environnement virtuel** :
   ```bash
   source .venv1/bin/activate  # ou .venv/bin/activate selon votre config
   ```

2. **Installer les dépendances** :
   ```bash
   pip install -r requirements.txt
   ```

3. **Configuration de la base de données** :
   ```bash
   python init_db.py  # Initialisation de la base SQLAlchemy
   ```

## 🚀 Lancement de l'application

1. **Démarrer le serveur Flask** :
   ```bash
   python app.py
   ```

2. **Accéder au site** :
   Ouvrir votre navigateur et aller à : `http://127.0.0.1:5000`

## ⚙️ Configuration .env

Créez un fichier `.env` dans le dossier `instance/` avec le contenu suivant :
```env
SECRET_KEY=VotreCléSecrèteComplexe
ADMIN_PWD=MotDePasseAdministrateur
QCM_ADMIN_PWD=MotDePasseGestionTests
DATABASE_URL=sqlite:///instance/qcm_database.db
```

### Variables d'environnement
- **SECRET_KEY** : Clé secrète Flask pour les sessions
- **ADMIN_PWD** : Mot de passe administrateur complet (gestion + ressources)
- **QCM_ADMIN_PWD** : Mot de passe pour la gestion des tests uniquement
- **DATABASE_URL** : Chemin de la base SQLite

## 🎮 Utilisation

### Pour les étudiants
1. **Choisir un type de test** : QCM complet, test par chapitre, ou test à trous
2. **Sélectionner le niveau** (6ème, 5ème, 4ème, 3ème)
3. **Répondre aux questions** avec support clavier et tactile
4. **Sauvegarder à tout moment** via les options de sortie
5. **Reprendre les tests** depuis la page d'accueil ou les sections spécialisées
6. **Consulter les résultats** avec corrections détaillées

### Pour les administrateurs
1. **Se connecter** via le bouton "🔑 Connexion"
2. **Accéder à l'interface de gestion** selon le niveau d'accès
3. **Gérer les questions QCM** : ajouter, modifier, supprimer
4. **Créer des tests à trous** avec éditeur intégré
5. **Consulter les ressources pédagogiques** (accès complet uniquement)

## 🏗️ Architecture technique

### Base de données SQLAlchemy
- **Niveaux** : 6ème, 5ème, 4ème, 3ème
- **Chapitres** : Organisation par thématiques du programme
- **Questions QCM** : Avec options, réponses correctes et explications
- **Questions à trous** : Format interactif avec mots à placer

### Types de tests
- **QCM complets** : Test global par niveau
- **Tests par chapitre** : Tests ciblés par thématique
- **Tests à trous** : Exercices de complétion interactifs

### Système de sauvegarde
- **Clés de session** : `progress_[niveau]_[chapitre]` pour les tests de chapitres
- **Progression QCM** : Position actuelle, score, réponses
- **Progression tests à trous** : Index question, réponses partielles
- **Gestion intelligente** : Suppression sélective par type de test

## 📁 Structure du projet

```
E-Learning/
├── app.py                          # Application Flask principale
├── models.py                       # Modèles SQLAlchemy (Niveau, Chapitre, Question, QuestionsATrous)
├── services.py                     # Logique métier et services
├── database.py                     # Gestion base de données (legacy)
├── init_db.py                      # Initialisation base SQLAlchemy
├── migration_sqlalchemy.py         # Script de migration
├── requirements.txt                # Dépendances Python
├── templates/                      # Templates HTML
│   ├── base.html                   # Template de base avec Bootstrap 5
│   ├── index.html                  # Page d'accueil avec tests en cours
│   ├── question.html               # Interface QCM avec sauvegarde
│   ├── question_trous.html         # Interface tests à trous (drag & drop)
│   ├── resultats.html              # Page de résultats unifiée
│   ├── chapitres.html              # Sélection des chapitres par niveau
│   ├── test_trous.html             # Sélection des tests à trous
│   ├── login_ressources.html       # Interface de connexion
│   ├── ressources.html             # Accès aux manuels PDF
│   ├── admin.html                  # Interface d'administration QCM
│   ├── admin_create_question_trous.html  # Création de tests à trous
│   └── admin_edit_question_trous.html    # Édition de tests à trous
├── static/                         # Fichiers statiques
│   ├── *.pdf                       # Manuels de mathématiques
│   ├── *.png                       # Logos et images
│   ├── *.json                      # Données exportées
│   └── *.sql                       # Scripts SQL
├── instance/                       # Dossier d'instance
│   ├── .env                        # Variables d'environnement
│   └── qcm_database.db            # Base de données SQLite
└── README.md                       # Cette documentation
```

## 🔧 API et routes principales

### Routes utilisateur
- `/` : Page d'accueil avec tests en cours
- `/niveau/<niveau>` : Lancer un test complet
- `/chapitres/<niveau>` : Tests par chapitre
- `/test_trous` : Sélection des tests à trous
- `/lancer_test_trous/<niveau>` : Démarrer un test à trous

### Routes de sauvegarde
- `/sauvegarder_et_quitter` : Sauvegarde QCM avec options de destination
- `/sauvegarder_et_quitter_trous` : Sauvegarde tests à trous
- `/reprendre_test/<niveau>/<chapitre?>` : Reprise de session QCM
- `/reprendre_test_trous/<niveau>` : Reprise de session tests à trous

### Routes d'administration
- `/login_ressources` : Interface de connexion
- `/admin` : Administration QCM (ajout/édition/suppression)
- `/admin/create_question_trous` : Création de tests à trous
- `/ressources` : Accès aux manuels PDF

### API de gestion
- `/supprimer_tous_tests` : Suppression complète des sauvegardes
- `/supprimer_tests_chapitre` : Suppression des tests de chapitres
- `/supprimer_tests_trous` : Suppression des tests à trous

## 🎨 Fonctionnalités avancées

### Interface responsive
- **Design adaptatif** pour mobile, tablette et desktop
- **Gestion tactile** pour les tests à trous (glisser-déposer)
- **Navigation clavier** optimisée (touches numériques, Échap)

### Système de notifications
- **Pop-ups de confirmation** avant de quitter un test
- **Options de sauvegarde** : avec/sans sauvegarde + annulation
- **Messages flash** pour les actions utilisateur

### Gestion des sessions
- **Persistance configurable** : 30 jours par défaut
- **Authentification multiniveau** : gestion tests / accès complet
- **Nettoyage intelligent** des sessions expirées

## 📊 Statistiques et monitoring

- **Suivi des questions** par niveau et chapitre
- **Statistiques d'utilisation** dans l'interface admin
- **Gestion des difficultés** des questions
- **Exportation des données** (JSON, SQL)

## 🚀 Déploiement

Le site est déployé sur PythonAnywhere et accessible à l'adresse :
[https://mathsetco.eu.pythonanywhere.com/](https://mathsetco.eu.pythonanywhere.com/)

Pour déployer votre propre instance :
1. Configurer les variables d'environnement
2. Initialiser la base de données avec `init_db.py`
3. Uploader les ressources PDF dans `static/`
4. Tester les fonctionnalités en local avant déploiement

---

**Développé avec Flask, SQLAlchemy, Bootstrap 5**  
*Version mise à jour : Octobre 2024*
