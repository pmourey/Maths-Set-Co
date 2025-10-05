from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory, send_file
from functools import wraps
from datetime import timedelta
from dotenv import load_dotenv
import os

from models import db, Niveau, Chapitre, Question
from services import QCMService

app = Flask(__name__, static_folder='static')

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
    session.pop('mode', None)
    session.pop('chapitre', None)

    # Restaurer l'authentification des ressources si elle existait
    if ressources_access:
        session['ressources_access'] = ressources_access
        session.permanent = session_permanent

    return redirect(url_for('question'))

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
    est_correcte = reponse_utilisateur == question['reponse_correcte']

    if est_correcte:
        session['score'] += 1

    session['reponses'].append({
        'question': question,
        'reponse_utilisateur': reponse_utilisateur,
        'correcte': est_correcte
    })

    session['question_courante'] += 1

    return redirect(url_for('question'))

@app.route('/resultats')
def resultats():
    if 'niveau' not in session:
        return redirect(url_for('index'))

    niveau = session['niveau']
    score = session['score']
    reponses = session['reponses']

    # Déterminer le contexte et le nombre total de questions
    if session.get('mode') == 'chapitre' and 'chapitre' in session:
        chapitre = session['chapitre']
        chapitre_info = QCMService.get_chapitre_info(niveau, chapitre)
        total_questions = chapitre_info['nb_questions']
        contexte = f"{chapitre_info['titre']} ({niveau.upper()})"
        type_test = 'chapitre'
    else:
        total_questions = len(reponses)
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
        probleme = data.get('probleme')
        options = [
            data.get('option_a'),
            data.get('option_b'),
            data.get('option_c'),
            data.get('option_d')
        ]
        reponse_correcte = int(data.get('reponse_correcte'))
        explication = data.get('explication')
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

if __name__ == '__main__':
    app.run(debug=True)
