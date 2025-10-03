# Site de Tests de Mathématiques - Collège

**MathπSet🎾&Co**

- Démo en ligne : [https://mathsetco.eu.pythonanywhere.com/](https://mathsetco.eu.pythonanywhere.com/)

Une application Flask simple pour proposer des tests de mathématiques en ligne sous forme de QCM pour les niveaux collège (6ème à 3ème).

## Fonctionnalités

- ✅ QCM adaptés par niveau (6ème, 5ème, 4ème, 3ème)
- ✅ Interface moderne et responsive avec Bootstrap
- ✅ Suivi de progression en temps réel
- ✅ Corrections détaillées avec explications
- ✅ Score et feedback personnalisé
- ✅ Navigation clavier (touches 1-4)

## Installation

1. **Activer l'environnement virtuel** (déjà créé) :
   ```bash
   source .venv/bin/activate
   ```

2. **Installer les dépendances** :
   ```bash
   pip install -r requirements.txt
   ```

## Lancement de l'application

1. **Démarrer le serveur Flask** :
   ```bash
   python app.py
   ```

2. **Accéder au site** :
   Ouvrir votre navigateur et aller à : `http://127.0.0.1:5000`

## Structure du projet

```
E-Learning/
├── app.py                 # Application Flask principale
├── requirements.txt       # Dépendances Python
├── templates/            # Templates HTML
│   ├── base.html         # Template de base
│   ├── index.html        # Page d'accueil
│   ├── question.html     # Interface de QCM
│   └── resultats.html    # Page de résultats
└── README.md             # Ce fichier
```

## Utilisation

1. Sur la page d'accueil, choisir un niveau (6ème, 5ème, 4ème ou 3ème)
2. Répondre aux questions du QCM
3. Consulter les résultats et corrections détaillées
4. Possibilité de refaire le test ou changer de niveau
5. Démo publique disponible ici : [https://mathsetco.eu.pythonanywhere.com/](https://mathsetco.eu.pythonanywhere.com/)

## Personnalisation

Pour ajouter de nouvelles questions, modifier le dictionnaire `QUESTIONS` dans `app.py`.

Structure d'une question :
```python
{
    "id": 1,
    "probleme": "Énoncé du problème...",
    "options": ["Réponse A", "Réponse B", "Réponse C", "Réponse D"],
    "reponse_correcte": 0,  # Index de la bonne réponse (0-3)
    "explication": "Explication de la solution..."
}
```

## Sécurité

⚠️ **Important** : Changez la `secret_key` dans `app.py` avant une utilisation en production !

## Technologies utilisées

- **Backend** : Flask (Python)
- **Frontend** : HTML5, CSS3, Bootstrap 5
- **Session** : Flask sessions pour le suivi du progrès
