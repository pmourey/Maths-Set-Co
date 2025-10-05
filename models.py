from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, Integer, String, Text, ForeignKey
from sqlalchemy.orm import relationship
import json

db = SQLAlchemy()

class Niveau(db.Model):
    """Modèle pour les niveaux scolaires (6ème, 5ème, 4ème, 3ème)"""
    __tablename__ = 'niveaux'

    id = Column(Integer, primary_key=True)
    nom = Column(String(10), unique=True, nullable=False)
    ordre = Column(Integer, nullable=False)
    description = Column(Text)

    # Relations
    chapitres = relationship('Chapitre', back_populates='niveau', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Niveau {self.nom}>'

    def to_dict(self):
        return {
            'id': self.id,
            'nom': self.nom,
            'ordre': self.ordre,
            'description': self.description
        }

class Chapitre(db.Model):
    """Modèle pour les chapitres de cours"""
    __tablename__ = 'chapitres'

    id = Column(Integer, primary_key=True)
    nom = Column(String(50), nullable=False)
    titre = Column(String(200), nullable=False)
    description = Column(Text)
    pages = Column(String(50))
    ordre = Column(Integer, nullable=False)

    # Clé étrangère
    niveau_id = Column(Integer, ForeignKey('niveaux.id'), nullable=False)

    # Relations
    niveau = relationship('Niveau', back_populates='chapitres')
    questions = relationship('Question', back_populates='chapitre', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Chapitre {self.titre}>'

    def to_dict(self):
        return {
            'id': self.id,
            'nom': self.nom,
            'titre': self.titre,
            'description': self.description,
            'pages': self.pages,
            'ordre': self.ordre,
            'niveau_id': self.niveau_id,
            'nb_questions': len(self.questions) if self.questions else 0
        }

class Question(db.Model):
    """Modèle pour les questions QCM"""
    __tablename__ = 'questions'

    id = Column(Integer, primary_key=True)
    probleme = Column(Text, nullable=False)
    option_a = Column(String(500), nullable=False)
    option_b = Column(String(500), nullable=False)
    option_c = Column(String(500), nullable=False)
    option_d = Column(String(500), nullable=False)
    reponse_correcte = Column(Integer, nullable=False)  # 0, 1, 2, ou 3
    explication = Column(Text, nullable=False)
    difficulte = Column(String(20), nullable=False)  # facile, moyen, difficile

    # Clé étrangère
    chapitre_id = Column(Integer, ForeignKey('chapitres.id'), nullable=False)

    # Relations
    chapitre = relationship('Chapitre', back_populates='questions')

    def __repr__(self):
        return f'<Question {self.id}: {self.probleme[:50]}...>'

    @property
    def options(self):
        """Retourne les options sous forme de liste"""
        return [self.option_a, self.option_b, self.option_c, self.option_d]

    def to_dict(self):
        return {
            'id': self.id,
            'probleme': self.probleme,
            'options': self.options,
            'reponse_correcte': self.reponse_correcte,
            'explication': self.explication,
            'difficulte': self.difficulte,
            'chapitre_id': self.chapitre_id,
            'chapitre_nom': self.chapitre.nom if self.chapitre else None,
            'chapitre_titre': self.chapitre.titre if self.chapitre else None,
            'niveau_nom': self.chapitre.niveau.nom if self.chapitre and self.chapitre.niveau else None
        }

class QuestionsATrous(db.Model):
    """Modèle pour les questions à trous"""
    __tablename__ = 'questions_a_trous'

    id = Column(Integer, primary_key=True)
    probleme = Column(Text, nullable=False)
    results = Column(Text, nullable=False) # JSON list of correct words (ordered)
    distracteurs = Column(Text, nullable=True) # JSON list of lists (distracteurs par trou)
    difficulte = Column(String(20), nullable=False)
    chapitre_id = Column(Integer, ForeignKey('chapitres.id'), nullable=False)

    chapitre = relationship('Chapitre')

    def __repr__(self):
        return f'<QuestionsATrous {self.id}: {self.probleme[:50]}...>'

    @property
    def results_list(self):
        import json
        return json.loads(self.results)

    @property
    def distracteurs_list(self):
        import json
        if self.distracteurs:
            return json.loads(self.distracteurs)
        return [[] for _ in self.results_list]

    def to_dict(self):
        import json
        return {
            'id': self.id,
            'probleme': self.probleme,
            'results': self.results_list,
            'distracteurs': self.distracteurs_list,
            'difficulte': self.difficulte,
            'chapitre_id': self.chapitre_id,
            'chapitre_nom': self.chapitre.nom if self.chapitre else None,
            'chapitre_titre': self.chapitre.titre if self.chapitre else None,
        }

