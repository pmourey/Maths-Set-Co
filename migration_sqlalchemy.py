#!/usr/bin/env python3
"""
Script de migration complète des données JSON vers SQLAlchemy
Migre les 96 questions avec structure relationnelle
"""

import json
import sys
import os
from flask import Flask
from models import db, Niveau, Chapitre, Question

# Configuration temporaire pour la migration
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///qcm_database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

def migrer_donnees_completes():
    """Migre toutes les données depuis qcm_optimise.json vers SQLAlchemy"""

    with app.app_context():
        print("🔄 Migration complète vers SQLAlchemy...")

        # Supprimer toutes les données existantes
        db.drop_all()
        db.create_all()
        print("✅ Tables recréées")

        # Charger les données JSON
        try:
            with open('qcm_optimise.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
        except FileNotFoundError:
            print("❌ Fichier qcm_optimise.json non trouvé")
            return False

        # 1. Créer les niveaux
        niveaux_data = [
            {'nom': '6eme', 'ordre': 1, 'description': 'Première année du collège - 49 questions'},
            {'nom': '5eme', 'ordre': 2, 'description': 'Deuxième année du collège - 13 questions'},
            {'nom': '4eme', 'ordre': 3, 'description': 'Troisième année du collège - 13 questions'},
            {'nom': '3eme', 'ordre': 4, 'description': 'Quatrième année du collège - 12 questions'}
        ]

        niveaux_created = {}
        for niveau_data in niveaux_data:
            niveau = Niveau(**niveau_data)
            db.session.add(niveau)
            db.session.flush()  # Pour obtenir l'ID
            niveaux_created[niveau.nom] = niveau.id

        print(f"✅ {len(niveaux_created)} niveaux créés")

        # 2. Créer les chapitres depuis chapitres_info
        chapitres_info = data.get('chapitres_info', {})
        chapitres_created = {}

        for niveau_nom, chapitres in chapitres_info.items():
            ordre = 1
            for chapitre_nom, info in chapitres.items():
                chapitre = Chapitre(
                    nom=chapitre_nom,
                    titre=info['titre'],
                    description=info['description'],
                    pages=info['pages'],
                    ordre=ordre,
                    niveau_id=niveaux_created[niveau_nom]
                )
                db.session.add(chapitre)
                db.session.flush()  # Pour obtenir l'ID
                chapitres_created[f"{niveau_nom}_{chapitre_nom}"] = chapitre.id
                ordre += 1

        print(f"✅ {len(chapitres_created)} chapitres créés")

        # 3. Migrer toutes les questions
        questions_migrees = 0
        questions_erreurs = 0

        for question_id, question_data in data['questions'].items():
            try:
                # Récupérer les tags
                tag = data['tags'][question_id]
                niveau = tag['niveau']
                chapitre = tag['chapitre']
                difficulte = tag['difficulte']

                # Trouver l'ID du chapitre
                key = f"{niveau}_{chapitre}"
                if key not in chapitres_created:
                    print(f"⚠️ Chapitre non trouvé: {key} pour question {question_id}")
                    questions_erreurs += 1
                    continue

                chapitre_id = chapitres_created[key]

                # Créer la question
                question = Question(
                    id=int(question_id),
                    probleme=question_data['probleme'],
                    option_a=question_data['options'][0],
                    option_b=question_data['options'][1],
                    option_c=question_data['options'][2],
                    option_d=question_data['options'][3],
                    reponse_correcte=question_data['reponse_correcte'],
                    explication=question_data['explication'],
                    difficulte=difficulte,
                    chapitre_id=chapitre_id
                )

                db.session.add(question)
                questions_migrees += 1

            except Exception as e:
                print(f"❌ Erreur migration question {question_id}: {e}")
                questions_erreurs += 1

        # Commit toutes les données
        try:
            db.session.commit()
            print(f"✅ Migration terminée:")
            print(f"   • {questions_migrees} questions migrées avec succès")
            if questions_erreurs > 0:
                print(f"   • {questions_erreurs} questions en erreur")

            # Vérifications finales
            verifier_integrite()
            return True

        except Exception as e:
            print(f"❌ Erreur lors du commit: {e}")
            db.session.rollback()
            return False

def verifier_integrite():
    """Vérifie l'intégrité des données migrées"""

    # Statistiques par niveau
    niveaux = Niveau.query.order_by(Niveau.ordre).all()
    print(f"\n📊 Vérification - Questions par niveau:")

    total_global = 0
    for niveau in niveaux:
        nb_questions = Question.query.join(Chapitre).filter(
            Chapitre.niveau_id == niveau.id
        ).count()
        total_global += nb_questions
        print(f"   • {niveau.nom.upper()}: {nb_questions} questions")

    print(f"   → Total: {total_global} questions")

    # Statistiques par chapitre
    print(f"\n📚 Questions par chapitre:")
    for niveau in niveaux:
        chapitres = Chapitre.query.filter_by(niveau_id=niveau.id).order_by(Chapitre.ordre).all()
        if chapitres:
            print(f"\n{niveau.nom.upper()}:")
            for chapitre in chapitres:
                nb_questions = len(chapitre.questions)
                print(f"   • {chapitre.titre}: {nb_questions} questions")

def main():
    """Migration principale"""
    if not os.path.exists('qcm_optimise.json'):
        print("❌ Fichier qcm_optimise.json manquant")
        print("Veuillez d'abord créer ce fichier avec vos données")
        return False

    success = migrer_donnees_completes()

    if success:
        print("\n🎉 Migration SQLAlchemy terminée avec succès!")
        print("✅ Votre application peut maintenant utiliser SQLAlchemy")
        print("✅ Base de données: qcm_database.db")
    else:
        print("\n❌ Échec de la migration")
        return False

    return True

if __name__ == "__main__":
    main()
