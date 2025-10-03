from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory

app = Flask(__name__)
app.secret_key = 'votre_cle_secrete_ici'

# Questions de mathématiques pour le collège
QUESTIONS = {
    "6eme": [
        {
            "id": 1,
            "probleme": "Pierre a 24 billes. Il donne 1/3 de ses billes à son frère. Combien de billes lui reste-t-il ?",
            "options": ["8 billes", "16 billes", "18 billes", "12 billes"],
            "reponse_correcte": 1,
            "explication": "1/3 de 24 = 8 billes données. Il lui reste 24 - 8 = 16 billes."
        },
        {
            "id": 2,
            "probleme": "Un rectangle a une longueur de 12 cm et une largeur de 8 cm. Quel est son périmètre ?",
            "options": ["20 cm", "40 cm", "96 cm", "32 cm"],
            "reponse_correcte": 1,
            "explication": "Périmètre = 2 × (longueur + largeur) = 2 × (12 + 8) = 2 × 20 = 40 cm."
        },
        {
            "id": 3,
            "probleme": "Marie achète 3 cahiers à 2,50 € chacun. Combien paie-t-elle en total ?",
            "options": ["6,50 €", "7,50 €", "8,00 €", "5,50 €"],
            "reponse_correcte": 1,
            "explication": "3 × 2,50 € = 7,50 €."
        }
    ],
    "5eme": [
        {
            "id": 4,
            "probleme": "Résoudre l'équation : 3x + 5 = 14",
            "options": ["x = 3", "x = 4", "x = 5", "x = 2"],
            "reponse_correcte": 0,
            "explication": "3x + 5 = 14 → 3x = 14 - 5 → 3x = 9 → x = 3."
        },
        {
            "id": 5,
            "probleme": "Un triangle a des angles de 60° et 70°. Quel est le troisième angle ?",
            "options": ["40°", "50°", "60°", "70°"],
            "reponse_correcte": 1,
            "explication": "La somme des angles d'un triangle = 180°. Donc 180° - 60° - 70° = 50°."
        }
    ],
    "4eme": [
        {
            "id": 6,
            "probleme": "Calculer : (-3) × (+4) + (-2) × (-5)",
            "options": ["-2", "2", "-22", "22"],
            "reponse_correcte": 1,
            "explication": "(-3) × (+4) = -12 et (-2) × (-5) = +10. Donc -12 + 10 = -2."
        },
        {
            "id": 7,
            "probleme": "Le volume d'un cube d'arête 4 cm est :",
            "options": ["16 cm³", "48 cm³", "64 cm³", "12 cm³"],
            "reponse_correcte": 2,
            "explication": "Volume d'un cube = arête³ = 4³ = 64 cm³."
        }
    ],
    "3eme": [
        {
            "id": 8,
            "probleme": "Résoudre le système : x + y = 5 et x - y = 1",
            "options": ["x=3, y=2", "x=2, y=3", "x=4, y=1", "x=1, y=4"],
            "reponse_correcte": 0,
            "explication": "En additionnant les équations : 2x = 6, donc x = 3. En remplaçant : 3 + y = 5, donc y = 2."
        },
        {
            "id": 9,
            "probleme": "Dans un triangle rectangle, si les côtés de l'angle droit mesurent 3 et 4, l'hypoténuse mesure :",
            "options": ["5", "6", "7", "12"],
            "reponse_correcte": 0,
            "explication": "D'après le théorème de Pythagore : c² = 3² + 4² = 9 + 16 = 25, donc c = 5."
        }
    ]
}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/niveau/<niveau>')
def choisir_niveau(niveau):
    if niveau not in QUESTIONS:
        flash('Niveau non disponible')
        return redirect(url_for('index'))

    session['niveau'] = niveau
    session['score'] = 0
    session['question_courante'] = 0
    session['reponses'] = []

    return redirect(url_for('question'))

@app.route('/question')
def question():
    if 'niveau' not in session:
        return redirect(url_for('index'))

    niveau = session['niveau']
    question_num = session['question_courante']
    questions_niveau = QUESTIONS[niveau]

    if question_num >= len(questions_niveau):
        return redirect(url_for('resultats'))

    question = questions_niveau[question_num]
    return render_template('question.html',
                         question=question,
                         question_num=question_num + 1,
                         total_questions=len(questions_niveau),
                         niveau=niveau)

@app.route('/repondre', methods=['POST'])
def repondre():
    if 'niveau' not in session:
        return redirect(url_for('index'))

    niveau = session['niveau']
    question_num = session['question_courante']
    questions_niveau = QUESTIONS[niveau]
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
    total_questions = len(QUESTIONS[niveau])
    reponses = session['reponses']
    pourcentage = round((score / total_questions) * 100, 1)

    return render_template('resultats.html',
                         score=score,
                         total=total_questions,
                         pourcentage=pourcentage,
                         reponses=reponses,
                         niveau=niveau)

@app.route('/recommencer')
def recommencer():
    session.clear()
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

if __name__ == '__main__':
    app.run(debug=True)
