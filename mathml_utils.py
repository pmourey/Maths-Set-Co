"""
Utilitaires pour la conversion et gestion de MathML dans les énoncés de tests
"""

import re
from markupsafe import Markup

class MathMLConverter:
    """Convertisseur pour transformer des notations mathématiques simples en MathML"""

    @staticmethod
    def fraction(numerateur, denominateur):
        """Génère une fraction en MathML"""
        return f"""<math class="math-inline">
            <mfrac>
                <mn>{numerateur}</mn>
                <mn>{denominateur}</mn>
            </mfrac>
        </math>"""

    @staticmethod
    def puissance(base, exposant):
        """Génère une puissance en MathML"""
        return f"""<math class="math-inline">
            <msup>
                <mn>{base}</mn>
                <mn>{exposant}</mn>
            </msup>
        </math>"""

    @staticmethod
    def racine(radicande, indice=2):
        """Génère une racine en MathML"""
        if indice == 2:
            return f"""<math class="math-inline">
                <msqrt>
                    <mn>{radicande}</mn>
                </msqrt>
            </math>"""
        else:
            return f"""<math class="math-inline">
                <mroot>
                    <mn>{radicande}</mn>
                    <mn>{indice}</mn>
                </mroot>
            </math>"""

    @staticmethod
    def equation(expression):
        """Génère une équation complète en MathML"""
        return f"""<math class="math-display">
            {expression}
        </math>"""

    @staticmethod
    def variable(nom, indice=None):
        """Génère une variable avec indice optionnel"""
        if indice:
            return f"""<math class="math-inline">
                <msub>
                    <mi>{nom}</mi>
                    <mn>{indice}</mn>
                </msub>
            </math>"""
        else:
            return f"""<math class="math-inline">
                <mi>{nom}</mi>
            </math>"""

def find_matching_paren(text, start_pos):
    """
    Trouve la parenthèse fermante correspondante à partir de start_pos
    """
    count = 1
    pos = start_pos + 1

    while pos < len(text) and count > 0:
        if text[pos] == '(':
            count += 1
        elif text[pos] == ')':
            count -= 1
        pos += 1

    return pos - 1 if count == 0 else -1

def parse_math_expression(expr):
    """
    Parse une expression mathématique complexe et la convertit en MathML
    Supporte les expressions imbriquées comme sqrt(1 + sqrt(x))
    """
    expr = expr.strip()

    # Traiter les fonctions mathématiques (sqrt, pow, frac) de manière récursive
    while True:
        # Chercher la prochaine fonction
        match = re.search(r'(sqrt|pow|frac)\s*\(', expr)
        if not match:
            break

        func_name = match.group(1)
        start_pos = match.start()
        paren_start = match.end() - 1

        # Trouver la parenthèse fermante correspondante
        paren_end = find_matching_paren(expr, paren_start)
        if paren_end == -1:
            break

        # Extraire le contenu de la fonction
        func_content = expr[paren_start + 1:paren_end]

        # Traiter selon le type de fonction
        if func_name == 'sqrt':
            # Traiter récursivement le contenu
            parsed_content = parse_complex_expression(func_content)
            replacement = f"<msqrt>{parsed_content}</msqrt>"

        elif func_name == 'pow':
            # Séparer base et exposant
            parts = split_function_args(func_content)
            if len(parts) == 2:
                base = parse_complex_expression(parts[0])
                exp = parse_complex_expression(parts[1])
                replacement = f"<msup>{base}{exp}</msup>"
            else:
                replacement = f"<mi>pow({func_content})</mi>"

        elif func_name == 'frac':
            # Séparer numérateur et dénominateur
            parts = split_function_args(func_content)
            if len(parts) == 2:
                num = parse_complex_expression(parts[0])
                den = parse_complex_expression(parts[1])
                replacement = f"<mfrac>{num}{den}</mfrac>"
            else:
                replacement = f"<mi>frac({func_content})</mi>"

        # Remplacer dans l'expression
        expr = expr[:start_pos] + replacement + expr[paren_end + 1:]

    return parse_complex_expression(expr)

def split_function_args(content):
    """
    Sépare les arguments d'une fonction en tenant compte des parenthèses imbriquées
    """
    args = []
    current_arg = ""
    paren_count = 0

    for char in content:
        if char == ',' and paren_count == 0:
            args.append(current_arg.strip())
            current_arg = ""
        else:
            if char == '(':
                paren_count += 1
            elif char == ')':
                paren_count -= 1
            current_arg += char

    if current_arg.strip():
        args.append(current_arg.strip())

    return args

def parse_complex_expression(expr):
    """
    Parse une expression complexe en éléments MathML
    Gère les opérateurs mathématiques et les expressions imbriquées
    """
    expr = expr.strip()

    if not expr:
        return "<mi></mi>"

    # Si l'expression contient encore des fonctions non traitées, les traiter
    if re.search(r'(sqrt|pow|frac)\s*\(', expr):
        return parse_math_expression(expr)

    # Si c'est déjà du MathML, le retourner tel quel
    if expr.startswith('<m') and expr.endswith('>'):
        return expr

    # Si c'est juste un nombre
    if re.match(r'^-?\d+(\.\d+)?$', expr):
        return f"<mn>{expr}</mn>"

    # Si c'est une variable simple
    if re.match(r'^[a-zA-Z]$', expr):
        return f"<mi>{expr}</mi>"

    # Gérer les expressions avec opérateurs
    # Priorité : *, /, puis +, -

    # Chercher + ou - (priorité la plus faible)
    for op in ['+', '-']:
        # Chercher l'opérateur en dehors des parenthèses
        paren_count = 0
        for i, char in enumerate(expr):
            if char == '(':
                paren_count += 1
            elif char == ')':
                paren_count -= 1
            elif char == op and paren_count == 0 and i > 0:  # Ne pas traiter le - initial
                left = parse_complex_expression(expr[:i])
                right = parse_complex_expression(expr[i+1:])
                return f"{left}<mo>{op}</mo>{right}"

    # Chercher * ou /
    for op in ['*', '/']:
        paren_count = 0
        for i, char in enumerate(expr):
            if char == '(':
                paren_count += 1
            elif char == ')':
                paren_count -= 1
            elif char == op and paren_count == 0:
                left = parse_complex_expression(expr[:i])
                right = parse_complex_expression(expr[i+1:])
                op_symbol = '×' if op == '*' else '÷'
                return f"{left}<mo>{op_symbol}</mo>{right}"

    # Si l'expression est entre parenthèses, les enlever
    if expr.startswith('(') and expr.endswith(')'):
        return parse_complex_expression(expr[1:-1])

    # Gérer les variables avec plusieurs caractères ou les expressions inconnues
    if re.match(r'^[a-zA-Z_]\w*$', expr):
        return f"<mi>{expr}</mi>"

    # Par défaut, traiter comme du texte
    return f"<mi>{expr}</mi>"

def convert_math_notation(text):
    """
    Convertit les notations mathématiques en MathML.

    Syntaxes supportées :
    - [math:sqrt(1 + sqrt(x))] → racine imbriquée
    - [math:frac(a+b, c-d)] → fraction complexe
    - [math:pow(x, 2)] → puissance
    - [frac:3/4] → fraction simple (ancienne syntaxe)
    - [frac:⅓] → fraction Unicode (⅓, ½, ¼, ¾, etc.)
    - [pow:x^2] → puissance simple (ancienne syntaxe)
    - [sqrt:16] → racine simple (ancienne syntaxe)
    - [root:8,3] → racine n-ième
    - [var:x_1] → variable avec indice
    """

    # Dictionnaire des fractions Unicode vers fractions classiques
    unicode_fractions = {
        '½': '1/2',
        '⅓': '1/3',
        '⅔': '2/3',
        '¼': '1/4',
        '¾': '3/4',
        '⅕': '1/5',
        '⅖': '2/5',
        '⅗': '3/5',
        '⅘': '4/5',
        '⅙': '1/6',
        '⅚': '5/6',
        '⅛': '1/8',
        '⅜': '3/8',
        '⅝': '5/8',
        '⅞': '7/8',
        '⅐': '1/7',
        '⅑': '1/9',
        '⅒': '1/10'
    }

    # Nouvelle syntaxe pour expressions complexes [math:...]
    def replace_math_expression(match):
        expr = match.group(1)
        try:
            parsed = parse_math_expression(expr)
            return f'<math class="math-inline">{parsed}</math>'
        except Exception as e:
            print(f"Erreur lors du parsing de '{expr}': {e}")
            # En cas d'erreur, retourner l'expression originale avec un format de base
            return f'<math class="math-inline"><mi>Erreur: {expr}</mi></math>'

    text = re.sub(r'\[math:([^\]]+)\]', replace_math_expression, text)

    # Ancienne syntaxe maintenue pour compatibilité
    # Conversion des fractions [frac:3/4] ou [frac:⅓]
    def replace_fraction(match):
        frac = match.group(1).strip()

        # Gérer les fractions Unicode
        if frac in unicode_fractions:
            num, den = unicode_fractions[frac].split('/')
            return MathMLConverter.fraction(num, den)

        # Gérer les fractions classiques avec /
        if '/' in frac:
            num, den = frac.split('/')
            return MathMLConverter.fraction(num.strip(), den.strip())

        # Si ce n'est ni Unicode ni avec /, retourner tel quel
        return match.group(0)

    text = re.sub(r'\[frac:([^\]]+)\]', replace_fraction, text)

    # Conversion des puissances [pow:x^2]
    def replace_power(match):
        expr = match.group(1)
        if '^' in expr:
            base, exp = expr.split('^')
            return MathMLConverter.puissance(base.strip(), exp.strip())
        return match.group(0)

    text = re.sub(r'\[pow:([^\]]+)\]', replace_power, text)

    # Conversion des racines carrées [sqrt:16]
    def replace_sqrt(match):
        value = match.group(1).strip()
        return MathMLConverter.racine(value)

    text = re.sub(r'\[sqrt:([^\]]+)\]', replace_sqrt, text)

    # Conversion des racines n-ièmes [root:8,3]
    def replace_root(match):
        values = match.group(1).split(',')
        if len(values) == 2:
            radicande, indice = values
            return MathMLConverter.racine(radicande.strip(), indice.strip())
        return match.group(0)

    text = re.sub(r'\[root:([^\]]+)\]', replace_root, text)

    # Conversion des variables avec indices [var:x_1]
    def replace_variable(match):
        var = match.group(1)
        if '_' in var:
            nom, indice = var.split('_')
            return MathMLConverter.variable(nom.strip(), indice.strip())
        else:
            return MathMLConverter.variable(var.strip())

    text = re.sub(r'\[var:([^\]]+)\]', replace_variable, text)

    return text

def mathml_filter(text):
    """Filtre Jinja2 pour convertir les notations mathématiques"""
    if text:
        converted = convert_math_notation(str(text))
        return Markup(converted)
    return text

# Exemples d'utilisation pour la documentation
EXAMPLES = {
    "fraction": "Calculer [frac:3/4] + [frac:1/2]",
    "puissance": "Résoudre [pow:x^2] = 16",
    "racine": "Simplifier [sqrt:16] + [root:8,3]",
    "variable": "Si [var:x_1] = 5 et [var:x_2] = 3, calculer [var:x_1] + [var:x_2]",
    "complexe": "Calculer [math:sqrt(1 + sqrt(x))] et [math:frac(a+b, c-d)]",
    "imbriquee": "Résoudre [math:pow(sqrt(x+1), 2)] = [math:frac(a+b, 2)]"
}

def generate_mathml_examples():
    """Génère des exemples de conversion pour les tests"""
    results = {}
    for key, example in EXAMPLES.items():
        results[key] = {
            'input': example,
            'output': mathml_filter(example)
        }
    return results
