from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory, send_file
from functools import wraps
from datetime import timedelta
from dotenv import load_dotenv
import os
import time
import re

from models import db, Niveau, Chapitre, Question, QuestionsATrous
from services import QCMService
from mathml_utils import mathml_filter, mathml_clean_filter, generate_mathml_examples, clean_display_filter

app = Flask(__name__, static_folder='static')

# Enregistrer les filtres MathML
app.jinja_env.filters['mathml'] = mathml_filter
app.jinja_env.filters['mathml_clean'] = mathml_clean_filter
app.jinja_env.filters['clean_display'] = clean_display_filter

load_dotenv(os.path.join(app.instance_path, '.env'))  # charge le fichier .env dans le dossier instance/
# Clé secrète pour les sessions (chargée depuis .env)
app.secret_key = os.getenv('SECRET_KEY', 'fallback_secret_key_for_development')
# Configuration SQLAlchemy
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///qcm_database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialiser SQLAlchemy
db.init_app(app)

# Configuration pour la persistance des sessions
app.permanent_session_lifetime = timedelta(days=30)  # Session valide 30 jours

ADMIN_PWD = os.getenv('ADMIN_PWD')
QCM_ADMIN_PWD = os.getenv('QCM_ADMIN_PWD')

# Fonction utilitaire pour retirer <p> et <br> en début/fin
def strip_paragraphs(text):
    if not text:
        return text
    text = str(text).strip()
    # Retirer <p>...</p> encadrant tout
    text = re.sub(r'^\s*<p[^>]*>(.*)</p>\s*$', r'\1', text, flags=re.DOTALL | re.IGNORECASE)
    # Retirer balises vides en début/fin
    text = re.sub(r'^(<p>\s*</p>\s*)+', '', text, flags=re.IGNORECASE)
    text = re.sub(r'(<p>\s*</p>\s*)+$', '', text, flags=re.IGNORECASE)
    # Retirer <br> en début/fin (boucle pour cas résiduels)
    prev = None
    while prev != text:
        prev = text
        text = re.sub(r'^(<br\s*/?>\s*)+', '', text, flags=re.IGNORECASE)
        text = re.sub(r'(<br\s*/?>\s*)+$', '', text, flags=re.IGNORECASE)
    return text.strip()

# Fonction utilitaire pour nettoyer un tableau d'options
def clean_options(options):
    return [strip_paragraphs(opt) if opt is not None else '' for opt in options]

# Fonction utilitaire pour les URLs canoniques (SEO)
def get_canonical_url(endpoint=None, **values):
    """
    Génère l'URL canonique pour une page donnée.
    Évite les problèmes de contenu dupliqué en définissant une version canonique.
    """
    base_url = "https://mathsetco.eu.pythonanywhere.com"

    # Définir les URLs canoniques pour chaque type de page
    canonical_rules = {
        'index': '/',
        'choisir_niveau': '/niveau/{niveau}',
        'question': '/niveau/{niveau}',  # Questions pointent vers la page niveau
        'resultats': '/niveau/{niveau}',  # Résultats pointent vers la page niveau
        'ressources': '/ressources',
        'login_ressources': '/login_ressources',
    }

    if endpoint and endpoint in canonical_rules:
        # Utiliser la règle canonique définie
        canonical_path = canonical_rules[endpoint]
        if values:
            canonical_path = canonical_path.format(**values)
        return base_url + canonical_path

    # Fallback : utiliser l'URL courante nettoyée
    if endpoint:
        try:
            path = url_for(endpoint, **values)
            return base_url + path
        except:
            pass

    return base_url + request.path

@app.context_processor
def inject_canonical_url():
    """
    Injecte automatiquement l'URL canonique dans tous les templates.
    """
    endpoint = request.endpoint
    view_args = request.view_args or {}

    # Pour les pages de questions/résultats, utiliser l'URL du niveau
    if endpoint in ['question', 'resultats'] and session.get('niveau'):
        canonical_url = get_canonical_url('choisir_niveau', niveau=session['niveau'])
    else:
        canonical_url = get_canonical_url(endpoint, **view_args)

    return {'canonical_url': canonical_url}

# Décorateur pour accès admin
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_access'):
            flash('Accès administrateur requis.')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

def login_required(f):
    """Décorateur pour protéger les routes nécessitant une authentification"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not (session.get('ressources_access') or session.get('qcm_admin_access') or session.get('admin_access')):
            flash('Accès restreint. Veuillez vous connecter pour accéder aux ressources ou à l’administration QCM.')
            return redirect(url_for('login_ressources'))
        return f(*args, **kwargs)
    return decorated_function

def qcm_admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not (session.get('qcm_admin_access') or session.get('admin_access')):
            flash('Accès QCM administrateur requis.')
            return redirect(url_for('login_ressources'))
        return f(*args, **kwargs)
    return decorated_function


def ressources_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_access'):
            flash('Accès complet requis pour consulter les ressources.')
            return redirect(url_for('login_ressources'))
        return f(*args, **kwargs)
    return decorated_function

def initialiser_base_donnees():
    """Initialise la base de données SQLAlchemy"""
    with app.app_context():
        # Créer les tables
        db.create_all()

        # Vérifier si des données existent déjà
        if Niveau.query.count() == 0:
            print("🔄 Initialisation des données de test...")
            QCMService.initialiser_donnees_test()
            print("✅ Données de test créées")

        return True

# Initialiser la base au démarrage
with app.app_context():
    if not initialiser_base_donnees():
        print("⚠️ Impossible d'initialiser la base de données. Arrêt de l'application.")
        exit(1)

    # Charger les statistiques au démarrage
    try:
        stats = QCMService.get_statistiques()
        print(f"✅ Base de données SQLAlchemy chargée avec succès:")
        print(f"   • Total questions: {stats['total_questions']}")
        print(f"   • Répartition par niveau: {stats['par_niveau']}")
    except Exception as e:
        print(f"❌ Erreur lors du chargement de la base: {e}")
        exit(1)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/niveau/<niveau>')
def choisir_niveau(niveau):
    # Vérifier que le niveau existe
    niveaux = QCMService.get_niveaux()
    if niveau not in [n['nom'] for n in niveaux]:
        flash('Niveau non disponible')
        return redirect(url_for('index'))

    # Sauvegarder l'état d'authentification des ressources
    ressources_access = session.get('ressources_access')
    session_permanent = session.permanent

    # Réinitialiser les données du QCM
    session['niveau'] = niveau
    session['score'] = 0
    session['question_courante'] = 0
    session['reponses'] = []
    session['reponses_dict'] = {}  # Nouveau dictionnaire pour navigation libre
    session.pop('mode', None)
    session.pop('chapitre', None)

    # Restaurer l'authentification des ressources si elle existait
    if ressources_access:
        session['ressources_access'] = ressources_access
        session.permanent = session_permanent

    # Servir directement la première question au lieu de rediriger
    # Cela permet à Google d'indexer correctement la page
    questions_niveau = QCMService.get_questions_niveau(niveau)
    if not questions_niveau:
        flash('Aucune question disponible pour ce niveau')
        return redirect(url_for('index'))

    # Afficher la première question directement
    question = questions_niveau[0]
    contexte = f"Niveau {niveau.upper()}"

    return render_template('question.html',
                         question=question,
                         question_num=1,
                         total_questions=len(questions_niveau),
                         niveau=niveau,
                         contexte=contexte)

@app.route('/question')
def question():
    if 'niveau' not in session:
        return redirect(url_for('index'))

    niveau = session['niveau']
    question_num = session['question_courante']

    # Déterminer les questions à utiliser (niveau complet ou chapitre spécifique)
    if session.get('mode') == 'chapitre' and 'chapitre' in session:
        chapitre = session['chapitre']
        questions_niveau = QCMService.get_questions_chapitre(niveau, chapitre)
        chapitre_info = QCMService.get_chapitre_info(niveau, chapitre)
        contexte = f"Chapitre : {chapitre_info['titre']} ({niveau.upper()})"
    else:
        questions_niveau = QCMService.get_questions_niveau(niveau)
        contexte = f"Niveau {niveau.upper()}"

    if question_num >= len(questions_niveau):
        return redirect(url_for('resultats'))

    question = questions_niveau[question_num]
    return render_template('question.html',
                         question=question,
                         question_num=question_num + 1,
                         total_questions=len(questions_niveau),
                         niveau=niveau,
                         contexte=contexte)

@app.route('/question_precedente')
def question_precedente():
    if 'niveau' not in session or session['question_courante'] <= 0:
        return redirect(url_for('index'))

    # Simplement décrémenter le numéro de question sans supprimer les réponses
    session['question_courante'] -= 1


    return redirect(url_for('question'))

@app.route('/repondre', methods=['POST'])
def repondre():
    if 'niveau' not in session:
        return redirect(url_for('index'))

    niveau = session['niveau']
    question_num = session['question_courante']

    # Déterminer les questions à utiliser
    if session.get('mode') == 'chapitre' and 'chapitre' in session:
        chapitre = session['chapitre']
        questions_niveau = QCMService.get_questions_chapitre(niveau, chapitre)
    else:
        questions_niveau = QCMService.get_questions_niveau(niveau)

    question = questions_niveau[question_num]

    reponse_utilisateur = int(request.form.get('reponse', -1))
    # Validation : s'assurer que la réponse est dans le range 0-3
    if not (0 <= reponse_utilisateur <= 3):
        reponse_utilisateur = -1  # Valeur invalide
    est_correcte = reponse_utilisateur == question['reponse_correcte']

    # Initialiser le dictionnaire de réponses s'il n'existe pas
    if 'reponses_dict' not in session:
        session['reponses_dict'] = {}

    # Sauvegarder la réponse avec l'index de la question comme clé
    session['reponses_dict'][str(question_num)] = {
        'question': question,
        'reponse_utilisateur': reponse_utilisateur,
        'correcte': est_correcte
    }

    # Recalculer le score total basé sur toutes les réponses données
    session['score'] = sum(1 for rep in session['reponses_dict'].values() if rep['correcte'])

    # Reconstruire la liste des réponses pour compatibilité avec les résultats
    session['reponses'] = []
    for i in range(len(questions_niveau)):
        if str(i) in session['reponses_dict']:
            session['reponses'].append(session['reponses_dict'][str(i)])
        # Supprimer le break pour inclure toutes les réponses, même non consécutives

    session['question_courante'] += 1

    return redirect(url_for('question'))

@app.route('/resultats')
def resultats():
    if 'niveau' not in session:
        return redirect(url_for('index'))

    niveau = session['niveau']
    score = session['score']
    reponses = session['reponses']

    # Recalculer la correction basée sur les données actuelles de la DB
    for rep in reponses:
        rep['correcte'] = rep['reponse_utilisateur'] == rep['question']['reponse_correcte']

    # Recalculer le score
    score = sum(1 for rep in reponses if rep['correcte'])
    session['score'] = score

    # Déterminer le contexte et le nombre total de questions
    if session.get('mode') == 'chapitre' and 'chapitre' in session:
        chapitre = session['chapitre']
        chapitre_info = QCMService.get_chapitre_info(niveau, chapitre)
        total_questions = chapitre_info['nb_questions']
        contexte = f"{chapitre_info['titre']} ({niveau.upper()})"
        type_test = 'chapitre'
    else:
        questions_niveau = QCMService.get_questions_niveau(niveau)
        total_questions = len(questions_niveau)
        contexte = f"Niveau {niveau.upper()}"
        type_test = 'niveau'

    pourcentage = round((score / total_questions) * 100, 1) if total_questions > 0 else 0

    return render_template('resultats.html',
                         score=score,
                         total=total_questions,
                         pourcentage=pourcentage,
                         reponses=reponses,
                         niveau=niveau,
                         contexte=contexte,
                         type_test=type_test)

@app.route('/recommencer')
def recommencer():
    # Sauvegarder l'état d'authentification des ressources
    ressources_access = session.get('ressources_access')
    session_permanent = session.permanent

    # Effacer seulement les données du QCM
    session.pop('niveau', None)
    session.pop('score', None)
    session.pop('question_courante', None)
    session.pop('reponses', None)
    session.pop('mode', None)
    session.pop('chapitre', None)

    # Restaurer l'authentification des ressources si elle existait
    if ressources_access:
        session['ressources_access'] = ressources_access
        session.permanent = session_permanent

    return redirect(url_for('index'))

@app.route('/sitemap.xml')
def sitemap():
    return send_from_directory('.', 'sitemap.xml')

@app.route('/robots.txt')
def robots():
    return send_from_directory('.', 'robots.txt')

@app.route('/google075dc122689af97b.html')
def google_verification():
    return send_from_directory('.', 'google075dc122689af97b.html')

# Routes ressources et PDF protégées
@app.route('/pdf/maths-6eme')
@login_required
@ressources_required
def consulter_pdf_6eme():
    """Affiche le PDF Maths 6ème dans le navigateur"""
    return send_from_directory('static', 'Maths_6eme.pdf')

@app.route('/telecharger/maths-6eme')
@login_required
@ressources_required
def telecharger_pdf_6eme():
    """Télécharge le PDF Maths 6ème"""
    return send_file('static/Maths_6eme.pdf', as_attachment=True, download_name='Maths_6eme.pdf')

@app.route('/pdf/maths-5eme')
@login_required
@ressources_required
def consulter_pdf_5eme():
    """Affiche le PDF Maths 5ème dans le navigateur"""
    return send_from_directory('static', 'Maths_5eme.pdf')

@app.route('/telecharger/maths-5eme')
@login_required
@ressources_required
def telecharger_pdf_5eme():
    """Télécharge le PDF Maths 5ème"""
    return send_file('static/Maths_5eme.pdf', as_attachment=True, download_name='Maths_5eme.pdf')

@app.route('/pdf/maths-4eme')
@login_required
@ressources_required
def consulter_pdf_4eme():
    """Affiche le PDF Maths 4ème dans le navigateur"""
    return send_from_directory('static', 'Maths_4eme.pdf')

@app.route('/telecharger/maths-4eme')
@login_required
@ressources_required
def telecharger_pdf_4eme():
    """Télécharge le PDF Maths 4ème"""
    return send_file('static/Maths_4eme.pdf', as_attachment=True, download_name='Maths_4eme.pdf')

@app.route('/pdf/maths-3eme')
@login_required
@ressources_required
def consulter_pdf_3eme():
    """Affiche le PDF Maths 3ème dans le navigateur"""
    return send_from_directory('static', 'Maths_3eme.pdf')

@app.route('/telecharger/maths-3eme')
@login_required
@ressources_required
def telecharger_pdf_3eme():
    """Télécharge le PDF Maths 3ème"""
    return send_file('static/Maths_3eme.pdf', as_attachment=True, download_name='Maths_3eme.pdf')

@app.route('/ressources')
@login_required
@ressources_required
def ressources():
    """Page listant les ressources disponibles"""
    return render_template('ressources.html')

@app.route('/login_ressources', methods=['GET', 'POST'])
def login_ressources():
    """Page de connexion pour accéder à l'administration QCM ou aux ressources"""
    if session.get('qcm_admin_access') or session.get('admin_access'):
        flash('Vous êtes déjà connecté.')
        return redirect(url_for('index'))

    if request.method == 'POST':
        mot_de_passe = request.form.get('mot_de_passe')
        se_souvenir = request.form.get('se_souvenir')

        if mot_de_passe == ADMIN_PWD:
            session['admin_access'] = True
            session['qcm_admin_access'] = True
            if se_souvenir:
                session.permanent = True
                flash('Connexion complète réussie. Vous resterez connecté pendant 30 jours.')
            else:
                session.permanent = False
                flash('Connexion complète réussie. Vous pouvez maintenant accéder à l’administration QCM et aux ressources.')
            return redirect(url_for('index'))
        elif mot_de_passe == QCM_ADMIN_PWD:
            session['qcm_admin_access'] = True
            session['admin_access'] = False
            if se_souvenir:
                session.permanent = True
                flash('Connexion QCM admin réussie. Vous resterez connecté pendant 30 jours.')
            else:
                session.permanent = False
                flash('Connexion QCM admin réussie. Vous pouvez maintenant accéder à l’administration QCM.')
            return redirect(url_for('index'))
        else:
            flash('Mot de passe incorrect. Veuillez réessayer.')

    return render_template('login_ressources.html')

@app.route('/logout_ressources')
def logout_ressources():
    session.pop('admin_access', None)
    session.pop('qcm_admin_access', None)
    flash('Vous avez été déconnecté.')
    return redirect(url_for('index'))

@app.route('/admin')
@login_required
@qcm_admin_required
def admin():
    """Page d'administration pour gérer les questions QCM"""
    return render_template('admin.html')

# Routes API pour l'administration QCM
@app.route('/admin/api/questions')
@login_required
@qcm_admin_required
def admin_api_questions():
    """API pour récupérer toutes les questions avec filtres optionnels"""
    niveau = request.args.get('niveau')
    chapitre = request.args.get('chapitre')

    # Récupérer toutes les questions
    questions = db.session.query(Question).join(Chapitre).join(Niveau)

    # Appliquer les filtres si spécifiés
    if niveau:
        questions = questions.filter(Niveau.nom == niveau)
    if chapitre:
        questions = questions.filter(Chapitre.nom == chapitre)

    questions = questions.all()

    # Formater les données pour l'API
    result = []
    for question in questions:
        result.append({
            'id': question.id,
            'probleme': question.probleme,
            'options': question.options,
            'reponse_correcte': question.reponse_correcte,
            'explication': question.explication,
            'difficulte': question.difficulte,
            'chapitre_id': question.chapitre_id,
            'chapitre_nom': question.chapitre.nom,
            'chapitre_titre': question.chapitre.titre,
            'niveau_nom': question.chapitre.niveau.nom
        })

    return {'questions': result}

@app.route('/admin/api/statistiques')
@login_required
@qcm_admin_required
def admin_api_statistiques():
    """API pour récupérer les statistiques"""
    return QCMService.get_statistiques()

@app.route('/admin/api/chapitres/<niveau>')
@login_required
@qcm_admin_required
def admin_api_chapitres(niveau):
    """API pour récupérer les chapitres d'un niveau"""
    chapitres = QCMService.get_chapitres_par_niveau(niveau)
    return {'chapitres': chapitres}

@app.route('/admin/api/question', methods=['POST'])
@login_required
@qcm_admin_required
def admin_api_ajouter_question():
    """API pour ajouter une nouvelle question"""
    try:
        data = request.get_json()

        # Extraire les données du formulaire
        probleme = strip_paragraphs(data.get('probleme'))
        options = clean_options([
            data.get('option_a'),
            data.get('option_b'),
            data.get('option_c'),
            data.get('option_d')
        ])
        reponse_correcte = int(data.get('reponse_correcte'))
        explication = strip_paragraphs(data.get('explication'))
        difficulte = data.get('difficulte')
        niveau_nom = data.get('niveau')
        chapitre_nom = data.get('chapitre')

        # Ajouter la question via le service
        question_id = QCMService.ajouter_question(
            probleme=probleme,
            options=options,
            reponse_correcte=reponse_correcte,
            explication=explication,
            difficulte=difficulte,
            niveau_nom=niveau_nom,
            chapitre_nom=chapitre_nom
        )

        return {'success': True, 'question_id': question_id, 'message': 'Question ajoutée avec succès'}

    except Exception as e:
        return {'success': False, 'error': str(e)}, 400

@app.route('/admin/api/question/<int:question_id>', methods=['PUT'])
@login_required
@qcm_admin_required
def admin_api_modifier_question(question_id):
    """API pour modifier une question existante"""
    try:
        data = request.get_json()

        # Nettoyer les champs avant mise à jour
        if 'probleme' in data:
            data['probleme'] = strip_paragraphs(data.get('probleme'))
        if 'explication' in data:
            data['explication'] = strip_paragraphs(data.get('explication'))
        # Nettoyer options si présentes
        for k in ['option_a', 'option_b', 'option_c', 'option_d']:
            if k in data:
                data[k] = strip_paragraphs(data.get(k))

        # Supprimer question_id des données pour éviter la duplication
        data.pop('question_id', None)

        success = QCMService.modifier_question(question_id, **data)

        if success:
            return {'success': True, 'message': 'Question modifiée avec succès'}
        else:
            return {'success': False, 'error': 'Question non trouvée'}, 404

    except Exception as e:
        return {'success': False, 'error': str(e)}, 400

@app.route('/admin/api/question/<int:question_id>', methods=['GET'])
@login_required
@qcm_admin_required
def admin_api_get_question(question_id):
    """API pour récupérer une question spécifique"""
    try:
        question = Question.query.get(question_id)

        if not question:
            return {'success': False, 'error': 'Question non trouvée'}, 404

        question_data = {
            'id': question.id,
            'probleme': question.probleme,
            'options': question.options,
            'reponse_correcte': question.reponse_correcte,
            'explication': question.explication,
            'difficulte': question.difficulte,
            'chapitre': question.chapitre.nom,
            'niveau': question.chapitre.niveau.nom
        }

        return {'success': True, 'question': question_data}

    except Exception as e:
        return {'success': False, 'error': str(e)}, 400

@app.route('/admin/api/question/<int:question_id>', methods=['DELETE'])
@login_required
@qcm_admin_required
def admin_api_supprimer_question(question_id):
    """API pour supprimer une question"""
    try:
        success = QCMService.supprimer_question(question_id)

        if success:
            return {'success': True, 'message': 'Question supprimée avec succès'}
        else:
            return {'success': False, 'error': 'Question non trouvée'}, 404

    except Exception as e:
        return {'success': False, 'error': str(e)}, 400

@app.route('/chapitre/<niveau>/<chapitre>')
def choisir_chapitre_niveau(niveau, chapitre):
    """Route pour choisir un chapitre spécifique d'un niveau donné"""
    # Vérifier que le chapitre existe
    chapitre_info = QCMService.get_chapitre_info(niveau, chapitre)
    if not chapitre_info:
        flash('Chapitre non disponible pour ce niveau')
        return redirect(url_for('chapitres_niveau', niveau=niveau))

    # Sauvegarder l'état d'authentification des ressources
    ressources_access = session.get('ressources_access')
    session_permanent = session.permanent

    # Initialiser le test par chapitre
    session['mode'] = 'chapitre'
    session['chapitre'] = chapitre
    session['niveau'] = niveau
    session['score'] = 0
    session['question_courante'] = 0
    session['reponses'] = []

    # Restaurer l'authentification des ressources
    if ressources_access:
        session['ressources_access'] = ressources_access
        session.permanent = session_permanent

    return redirect(url_for('question'))

@app.route('/chapitre/<chapitre>')
def choisir_chapitre(chapitre):
    """Route pour choisir un chapitre spécifique (compatibilité 6ème)"""
    return choisir_chapitre_niveau('6eme', chapitre)

@app.route('/chapitres')
def chapitres():
    """Page de sélection des chapitres (6ème par défaut)"""
    return redirect(url_for('chapitres_niveau', niveau='6eme'))

@app.route('/chapitres/<niveau>')
def chapitres_niveau(niveau):
    """Page de sélection des chapitres pour un niveau donné"""
    # Récupérer les chapitres du niveau
    chapitres_data = QCMService.get_chapitres_par_niveau(niveau)
    if not chapitres_data:
        flash('Niveau non disponible')
        return redirect(url_for('index'))

    # Convertir en format compatible avec le template
    chapitres_info = {}
    for chapitre in chapitres_data:
        chapitres_info[chapitre['nom']] = {
            'titre': chapitre['titre'],
            'description': chapitre['description'],
            'nb_questions': chapitre['nb_questions'],
            'pages': chapitre['pages']
        }

    return render_template('chapitres.html',
                         chapitres=chapitres_info,
                         niveau=niveau,
                         titre_niveau=f"Chapitres - {niveau.upper()}")


@app.route('/question_trous/<int:question_id>', methods=['GET', 'POST'])
def repondre_question_trous(question_id):
    question = QuestionsATrous.query.get_or_404(question_id)
    # Générer la liste des mots à proposer (results + distracteurs, sans doublons)
    mots = set(question.results_list)
    for distracteurs in question.distracteurs_list:
        mots.update(distracteurs)
    choix_mots = sorted(mots)
    if request.method == 'POST':
        import json
        reponses = request.form.get('reponses_a_trous')
        try:
            reponses_list = json.loads(reponses)
        except Exception:
            reponses_list = []
        # Stocker dans la session
        if 'reponses_a_trous' not in session:
            session['reponses_a_trous'] = {}
        session['reponses_a_trous'][str(question_id)] = reponses_list
        flash('Réponse enregistrée.', 'success')
        return redirect(url_for('resultats_trous'))
    return render_template('question_trous.html', question=question, choix_mots=choix_mots)

@app.route('/resultats_trous')
def resultats_trous():
    # Analyse des réponses à trous
    reponses = session.get('reponses_a_trous', {})
    resultats = []
    score = 0
    total = len(reponses)
    for qid, user_reponses in reponses.items():
        question = QuestionsATrous.query.get(int(qid))
        correctes = question.results_list if question else []
        est_correcte = user_reponses == correctes
        if est_correcte:
            score += 1
        resultats.append({
            'question': question,
            'user_reponses': user_reponses,
            'correctes': correctes,
            'est_correcte': est_correcte
        })
    pourcentage = int((score / total) * 100) if total > 0 else 0
    niveau = None
    contexte = None
    if resultats and resultats[0]['question'] and resultats[0]['question'].chapitre:
        niveau = resultats[0]['question'].chapitre.niveau.nom
        chapitre_info = resultats[0]['question'].chapitre.titre
        contexte = f"{chapitre_info} ({niveau.upper()})"
    else:
        contexte = f"Niveau {niveau.upper()}" if niveau is not None else "Test à trous"
    type_test = 'trous'
    return render_template('resultats.html', score=score, total=total, pourcentage=pourcentage, reponses=resultats, niveau=niveau, type_test=type_test, contexte=contexte)


@app.route('/admin/edit_question_trous/<int:question_id>', methods=['GET', 'POST'])
@qcm_admin_required
def edit_question_trous(question_id):
    question = QuestionsATrous.query.get_or_404(question_id)
    niveaux = Niveau.query.order_by(Niveau.ordre).all()
    chapitres = Chapitre.query.order_by(Chapitre.titre).all()
    if request.method == 'POST':
        probleme = request.form['probleme']
        difficulte = request.form['difficulte']
        niveau_id = request.form['niveau_id']
        chapitre_id = request.form['chapitre_id']
        import json
        nb_trous = probleme.count('[TROU]')
        results = [request.form.get(f'result_{i}', '').strip() for i in range(nb_trous)]
        distracteurs = []
        for i in range(nb_trous):
            d = request.form.get(f'distracteurs_{i}', '').strip()
            distracteurs.append([mot.strip() for mot in d.split(',') if mot.strip()])
        question.probleme = probleme
        question.results = json.dumps(results)
        question.distracteurs = json.dumps(distracteurs)
        question.difficulte = difficulte
        question.chapitre_id = chapitre_id
        db.session.commit()
        flash('Question à trous modifiée avec succès.', 'success')
        return redirect(url_for('edit_question_trous', question_id=question.id))
    return render_template('admin_edit_question_trous.html', question=question, niveaux=niveaux, chapitres=chapitres)

@app.route('/admin/create_question_trous', methods=['GET', 'POST'])
@qcm_admin_required
def create_question_trous():
    niveaux = Niveau.query.order_by(Niveau.ordre).all()
    chapitres = Chapitre.query.order_by(Chapitre.titre).all()
    if request.method == 'POST':
        probleme = request.form['probleme']
        difficulte = request.form['difficulte']
        niveau_id = request.form['niveau_id']
        chapitre_id = request.form['chapitre_id']
        import json
        nb_trous = probleme.count('[TROU]')
        results = [request.form.get(f'result_{i}', '').strip() for i in range(nb_trous)]
        distracteurs = []
        for i in range(nb_trous):
            d = request.form.get(f'distracteurs_{i}', '').strip()
            distracteurs.append([mot.strip() for mot in d.split(',') if mot.strip()])
        question = QuestionsATrous(
            probleme=probleme,
            results=json.dumps(results),
            distracteurs=json.dumps(distracteurs),
            difficulte=difficulte,
            chapitre_id=chapitre_id
        )
        db.session.add(question)
        db.session.commit()
        flash('Question à trous créée avec succès.', 'success')
        return redirect(url_for('create_question_trous'))
    return render_template('admin_create_question_trous.html', niveaux=niveaux, chapitres=chapitres)

@app.route('/test_trous')
def test_trous():
    niveaux = ['6eme', '5eme', '4eme', '3eme']
    questions_par_niveau = {}
    for niveau in niveaux:
        question = QuestionsATrous.query.join(Chapitre).join(Niveau).filter(Niveau.nom == niveau).order_by(QuestionsATrous.id.asc()).first()
        questions_par_niveau[niveau] = question.id if question else None
    return render_template('test_trous.html', questions_par_niveau=questions_par_niveau)

@app.route('/lancer_test_trous/<niveau>', methods=['GET', 'POST'])
def lancer_test_trous(niveau):
    # Récupérer dynamiquement toutes les questions à trous du niveau
    questions = QuestionsATrous.query.join(Chapitre).join(Niveau).filter(Niveau.nom == niveau).order_by(QuestionsATrous.id.asc()).all()
    total = len(questions)
    # Réinitialiser l'index et les réponses uniquement au tout début du test
    if request.method == 'GET' and (session.get('test_trous_index') is None or session.get('test_trous_index', 0) == 0):
        session['test_trous_index'] = 0
        session['reponses_a_trous'] = {}
    index = session.get('test_trous_index', 0)
    if index >= total or total == 0:
        return redirect(url_for('resultats_trous'))
    question = questions[index]
    mots = set(question.results_list)
    for distracteurs in question.distracteurs_list:
        mots.update(distracteurs)
    choix_mots = sorted(mots)
    if request.method == 'POST':
        import json
        reponses = request.form.get('reponses_a_trous')
        try:
            reponses_list = json.loads(reponses)
        except Exception:
            reponses_list = []
        session['reponses_a_trous'][str(question.id)] = reponses_list
        session['test_trous_index'] = index + 1
        if index + 1 >= total:
            return redirect(url_for('resultats_trous'))
        else:
            return redirect(url_for('lancer_test_trous', niveau=niveau))
    return render_template('question_trous.html', question=question, choix_mots=choix_mots, index=index+1, total=total, niveau=niveau)

@app.route('/annuler_test_trous')
def annuler_test_trous():
    """Route pour annuler un test à trous en cours et nettoyer la session"""
    # Nettoyer complètement la session des tests à trous
    session.pop('test_trous_index', None)
    session.pop('reponses_a_trous', None)
    # Rediriger vers l'accueil
    return redirect(url_for('index'))

@app.route('/relancer_test_trous/<niveau>')
def relancer_test_trous(niveau):
    """Route pour relancer un test à trous en réinitialisant la session"""
    # Réinitialiser complètement la session des tests à trous
    session.pop('test_trous_index', None)
    session.pop('reponses_a_trous', None)
    # Rediriger vers le début du test à trous pour ce niveau
    return redirect(url_for('lancer_test_trous', niveau=niveau))

@app.route('/sauvegarder_et_quitter', methods=['POST'])
def sauvegarder_et_quitter():
    """Route pour sauvegarder la progression avant de quitter un test"""
    try:
        data = request.get_json()
        destination = data.get('destination', 'index')

        # Créer une clé unique pour la sauvegarde basée sur le niveau/chapitre
        if session.get('mode') == 'chapitre':
            save_key = f"progress_{session.get('niveau')}_{session.get('chapitre')}"
        else:
            save_key = f"progress_{session.get('niveau')}"

        # Sauvegarder la progression actuelle
        progress_data = {
            'niveau': session.get('niveau'),
            'mode': session.get('mode'),
            'chapitre': session.get('chapitre'),
            'question_courante': session.get('question_courante', 0),
            'score': session.get('score', 0),
            'reponses': session.get('reponses', []),
            'timestamp': time.time()
        }

        session[save_key] = progress_data

        # Nettoyer les variables de session actuelle
        session.pop('niveau', None)
        session.pop('score', None)
        session.pop('question_courante', None)
        session.pop('reponses', None)
        session.pop('mode', None)
        session.pop('chapitre', None)

        return {'success': True, 'redirect_url': url_for(destination)}

    except Exception as e:
        return {'success': False, 'error': str(e)}, 400

@app.route('/sauvegarder_et_quitter_trous', methods=['POST'])
def sauvegarder_et_quitter_trous():
    """Route pour sauvegarder la progression des tests à trous avant de quitter"""
    try:
        data = request.get_json()
        niveau = data.get('niveau')
        destination = data.get('destination', 'index')  # Par défaut vers l'index si pas spécifié

        if not niveau:
            return {'success': False, 'error': 'Niveau manquant'}, 400

        # Créer une clé unique pour la sauvegarde des tests à trous
        save_key = f"progress_trous_{niveau}"

        # Sauvegarder la progression actuelle
        progress_data = {
            'type': 'trous',
            'niveau': niveau,
            'test_trous_index': session.get('test_trous_index', 0),
            'reponses_a_trous': session.get('reponses_a_trous', {}),
            'timestamp': time.time()
        }

        session[save_key] = progress_data

        # Nettoyer les variables de session actuelle
        session.pop('test_trous_index', None)
        session.pop('reponses_a_trous', None)

        # Rediriger selon la destination demandée
        if destination == 'test_trous':
            redirect_url = url_for('test_trous')
        else:
            redirect_url = url_for('index')

        return {'success': True, 'redirect_url': redirect_url}

    except Exception as e:
        return {'success': False, 'error': str(e)}, 400

@app.route('/reprendre_test/<niveau>')
@app.route('/reprendre_test/<niveau>/<chapitre>')
def reprendre_test(niveau, chapitre=None):
    """Route pour reprendre un test sauvegardé"""
    if chapitre:
        save_key = f"progress_{niveau}_{chapitre}"
    else:
        save_key = f"progress_{niveau}"

    progress_data = session.get(save_key)
    if not progress_data:
        flash('Aucune progression sauvegardée trouvée pour ce test.')
        return redirect(url_for('index'))

    # Restaurer la progression
    session['niveau'] = progress_data['niveau']
    session['mode'] = progress_data.get('mode')
    session['chapitre'] = progress_data.get('chapitre')
    session['question_courante'] = progress_data['question_courante']
    session['score'] = progress_data['score']
    session['reponses'] = progress_data['reponses']

    # Supprimer la sauvegarde
    session.pop(save_key, None)

    flash(f'Test repris. Question {progress_data["question_courante"] + 1}')
    return redirect(url_for('question'))

@app.route('/reprendre_test_trous/<niveau>')
def reprendre_test_trous(niveau):
    """Route pour reprendre un test à trous sauvegardé"""
    save_key = f"progress_trous_{niveau}"

    progress_data = session.get(save_key)
    if not progress_data:
        flash('Aucune progression sauvegardée trouvée pour ce test à trous.')
        return redirect(url_for('index'))

    # Restaurer la progression
    session['test_trous_index'] = progress_data['test_trous_index']
    session['reponses_a_trous'] = progress_data['reponses_a_trous']

    # Supprimer la sauvegarde
    session.pop(save_key, None)

    flash(f'Test à trous repris pour le niveau {niveau.upper()}.')
    return redirect(url_for('lancer_test_trous', niveau=niveau))

@app.route('/supprimer_tous_tests', methods=['POST'])
def supprimer_tous_tests():
    """Route pour supprimer tous les tests en cours"""
    try:
        # Supprimer tous les tests QCM sauvegardés
        keys_to_remove = []
        for key in session.keys():
            if key.startswith('progress_'):
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            session.pop(key, None)
        
        return {'success': True, 'message': 'Tous les tests en cours ont été supprimés'}
    except Exception as e:
        return {'success': False, 'error': str(e)}, 400

@app.route('/supprimer_tests_chapitre', methods=['POST'])
def supprimer_tests_chapitre():
    """Route pour supprimer seulement les tests de chapitres en cours"""
    try:
        keys_to_remove = []
        for key in session.keys():
            if key.startswith('progress_') and not key.startswith('progress_trous_'):
                test_data = session[key]
                if test_data.get('mode') == 'chapitre':
                    keys_to_remove.append(key)
        
        for key in keys_to_remove:
            session.pop(key, None)
        
        return {'success': True, 'message': 'Tests de chapitres en cours supprimés'}
    except Exception as e:
        return {'success': False, 'error': str(e)}, 400

@app.route('/supprimer_tests_trous', methods=['POST'])
def supprimer_tests_trous():
    """Route pour supprimer seulement les tests à trous en cours"""
    try:
        keys_to_remove = []
        for key in session.keys():
            if key.startswith('progress_trous_'):
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            session.pop(key, None)
        
        return {'success': True, 'message': 'Tests à trous en cours supprimés'}
    except Exception as e:
        return {'success': False, 'error': str(e)}, 400

@app.route('/admin/editor')
@login_required
@qcm_admin_required
def admin_editor():
    """Page d'édition de questions avec éditeur WYSIWYG et support MathML"""
    return render_template('admin_editor.html')

@app.route('/admin/editor/<int:question_id>')
@login_required
@qcm_admin_required
def admin_editor_question(question_id):
    """Page d'édition individuelle d'une question avec éditeur MathML Simple"""
    return render_template('editor.html', question_id=question_id)

@app.route('/admin/mathquill-editor')
@login_required
@qcm_admin_required
def admin_mathquill_editor():
    """Éditeur MathML avancé avec MathQuill pour expressions complexes imbriquées"""
    return render_template('mathquill_editor.html')

@app.route('/demo-mathml')
def demo_mathml():
    """Page de démonstration des fonctionnalités MathML"""
    examples = generate_mathml_examples()
    return render_template('demo_mathml.html', examples=examples)

if __name__ == '__main__':
    app.run(debug=True)
