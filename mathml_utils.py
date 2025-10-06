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

def convert_math_notation(text):
    """
    Convertit les notations mathématiques simples en MathML.

    Syntaxes supportées :
    - [frac:3/4] → fraction 3/4
    - [pow:x^2] → x au carré
    - [sqrt:16] → racine carrée de 16
    - [root:8,3] → racine cubique de 8
    - [var:x_1] → variable x avec indice 1
    """

    # Conversion des fractions [frac:3/4]
    def replace_fraction(match):
        frac = match.group(1)
        if '/' in frac:
            num, den = frac.split('/')
            return MathMLConverter.fraction(num.strip(), den.strip())
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
    "variable": "Si [var:x_1] = 5 et [var:x_2] = 3, calculer [var:x_1] + [var:x_2]"
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
