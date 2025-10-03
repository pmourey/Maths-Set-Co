from models import db, Niveau, Chapitre, Question
from sqlalchemy import func

class QCMService:
    """Service pour gérer les opérations QCM avec SQLAlchemy"""

    @staticmethod
    def get_niveaux():
        """Récupère tous les niveaux"""
        return [niveau.to_dict() for niveau in Niveau.query.order_by(Niveau.ordre).all()]

    @staticmethod
    def get_chapitres_par_niveau(niveau_nom):
        """Récupère les chapitres d'un niveau avec le nombre de questions"""
        chapitres = db.session.query(
            Chapitre,
            func.count(Question.id).label('nb_questions')
        ).join(Niveau).outerjoin(Question).filter(
            Niveau.nom == niveau_nom
        ).group_by(Chapitre.id).order_by(Chapitre.ordre).all()

        result = []
        for chapitre, nb_questions in chapitres:
            chapitre_dict = chapitre.to_dict()
            chapitre_dict['nb_questions'] = nb_questions
            result.append(chapitre_dict)

        return result

    @staticmethod
    def get_questions_niveau(niveau_nom):
        """Récupère toutes les questions d'un niveau"""
        questions = Question.query.join(Chapitre).join(Niveau).filter(
            Niveau.nom == niveau_nom
        ).order_by(Question.id).all()

        return [question.to_dict() for question in questions]

    @staticmethod
    def get_questions_chapitre(niveau_nom, chapitre_nom):
        """Récupère les questions d'un chapitre spécifique"""
        questions = Question.query.join(Chapitre).join(Niveau).filter(
            Niveau.nom == niveau_nom,
            Chapitre.nom == chapitre_nom
        ).order_by(Question.id).all()

        return [question.to_dict() for question in questions]

    @staticmethod
    def get_chapitre_info(niveau_nom, chapitre_nom):
        """Récupère les informations d'un chapitre avec le nombre de questions"""
        result = db.session.query(
            Chapitre,
            func.count(Question.id).label('nb_questions')
        ).join(Niveau).outerjoin(Question).filter(
            Niveau.nom == niveau_nom,
            Chapitre.nom == chapitre_nom
        ).group_by(Chapitre.id).first()

        if result:
            chapitre, nb_questions = result
            chapitre_dict = chapitre.to_dict()
            chapitre_dict['nb_questions'] = nb_questions
            chapitre_dict['niveau_nom'] = chapitre.niveau.nom
            return chapitre_dict

        return None

    @staticmethod
    def get_statistiques():
        """Récupère les statistiques globales"""
        # Total questions
        total_questions = Question.query.count()

        # Par niveau - correction de l'ambiguïté de jointure
        stats_par_niveau = db.session.query(
            Niveau.nom,
            func.count(Question.id).label('nb_questions')
        ).select_from(Niveau).outerjoin(Chapitre).outerjoin(Question).group_by(
            Niveau.id, Niveau.nom
        ).order_by(Niveau.ordre).all()

        par_niveau = {niveau: nb for niveau, nb in stats_par_niveau}

        return {
            'total_questions': total_questions,
            'par_niveau': par_niveau
        }

    @staticmethod
    def ajouter_question(probleme, options, reponse_correcte, explication,
                        difficulte, niveau_nom, chapitre_nom):
        """Ajoute une nouvelle question"""
        # Trouver le chapitre
        chapitre = Chapitre.query.join(Niveau).filter(
            Niveau.nom == niveau_nom,
            Chapitre.nom == chapitre_nom
        ).first()

        if not chapitre:
            raise ValueError(f"Chapitre {chapitre_nom} non trouvé pour le niveau {niveau_nom}")

        # Créer la question
        question = Question(
            probleme=probleme,
            option_a=options[0],
            option_b=options[1],
            option_c=options[2],
            option_d=options[3],
            reponse_correcte=reponse_correcte,
            explication=explication,
            difficulte=difficulte,
            chapitre_id=chapitre.id
        )

        db.session.add(question)
        db.session.commit()

        return question.id

    @staticmethod
    def modifier_question(question_id, **kwargs):
        """Modifie une question existante"""
        question = Question.query.get(question_id)
        if not question:
            return False

        # Mettre à jour les champs autorisés
        champs_autorises = ['probleme', 'option_a', 'option_b', 'option_c', 'option_d',
                           'reponse_correcte', 'explication', 'difficulte']

        for field, value in kwargs.items():
            if field in champs_autorises and hasattr(question, field):
                setattr(question, field, value)

        db.session.commit()
        return True

    @staticmethod
    def supprimer_question(question_id):
        """Supprime une question"""
        question = Question.query.get(question_id)
        if not question:
            return False

        db.session.delete(question)
        db.session.commit()
        return True

    @staticmethod
    def initialiser_donnees_test():
        """Initialise la base avec des données de test"""
        # Créer les niveaux
        niveaux_data = [
            {'id': 1, 'nom': '6eme', 'ordre': 1, 'description': 'Première année du collège'},
            {'id': 2, 'nom': '5eme', 'ordre': 2, 'description': 'Deuxième année du collège'},
            {'id': 3, 'nom': '4eme', 'ordre': 3, 'description': 'Troisième année du collège'},
            {'id': 4, 'nom': '3eme', 'ordre': 4, 'description': 'Quatrième année du collège'}
        ]

        for niveau_data in niveaux_data:
            niveau = Niveau.query.get(niveau_data['id'])
            if not niveau:
                niveau = Niveau(**niveau_data)
                db.session.add(niveau)

        # Créer quelques chapitres
        chapitres_data = [
            {'id': 1, 'nom': 'fractions', 'titre': 'Fractions', 'description': 'Calculs avec les fractions', 'pages': '10-15', 'niveau_id': 1, 'ordre': 1},
            {'id': 2, 'nom': 'geometrie', 'titre': 'Géométrie', 'description': 'Calculs géométriques', 'pages': '16-20', 'niveau_id': 1, 'ordre': 2},
            {'id': 3, 'nom': 'equations', 'titre': 'Équations', 'description': 'Résolution d\'équations', 'pages': '10-15', 'niveau_id': 2, 'ordre': 1},
            {'id': 4, 'nom': 'probabilites', 'titre': 'Probabilités', 'description': 'Calculs de probabilités', 'pages': '20-25', 'niveau_id': 4, 'ordre': 1}
        ]

        for chapitre_data in chapitres_data:
            chapitre = Chapitre.query.get(chapitre_data['id'])
            if not chapitre:
                chapitre = Chapitre(**chapitre_data)
                db.session.add(chapitre)

        # Créer quelques questions de test
        questions_data = [
            {
                'id': 1,
                'probleme': 'Calculer 1/2 + 1/4',
                'option_a': '3/4',
                'option_b': '2/6',
                'option_c': '1/3',
                'option_d': '1/6',
                'reponse_correcte': 0,
                'explication': '1/2 + 1/4 = 2/4 + 1/4 = 3/4',
                'difficulte': 'facile',
                'chapitre_id': 1
            },
            {
                'id': 2,
                'probleme': 'Calculer l\'aire d\'un carré de côté 5 cm',
                'option_a': '25 cm²',
                'option_b': '20 cm²',
                'option_c': '10 cm²',
                'option_d': '15 cm²',
                'reponse_correcte': 0,
                'explication': 'Aire = côté² = 5² = 25 cm²',
                'difficulte': 'facile',
                'chapitre_id': 2
            },
            {
                'id': 3,
                'probleme': 'Résoudre x + 3 = 7',
                'option_a': 'x = 4',
                'option_b': 'x = 10',
                'option_c': 'x = 3',
                'option_d': 'x = 7',
                'reponse_correcte': 0,
                'explication': 'x + 3 = 7 → x = 7 - 3 = 4',
                'difficulte': 'moyen',
                'chapitre_id': 3
            },
            {
                'id': 4,
                'probleme': 'Probabilité d\'obtenir un nombre pair avec un dé',
                'option_a': '1/2',
                'option_b': '1/3',
                'option_c': '2/3',
                'option_d': '1/6',
                'reponse_correcte': 0,
                'explication': 'Nombres pairs: 2,4,6. Probabilité = 3/6 = 1/2',
                'difficulte': 'facile',
                'chapitre_id': 4
            }
        ]

        for question_data in questions_data:
            question = Question.query.get(question_data['id'])
            if not question:
                question = Question(**question_data)
                db.session.add(question)

        db.session.commit()
