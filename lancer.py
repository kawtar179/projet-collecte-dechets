#!/usr/bin/env python3
"""
==========================================================
  LANCEUR AUTOMATIQUE - Projet Collecte Déchets Agadir
==========================================================
Ce script installe les dépendances et démarre l'application.
Utilisation : python lancer.py
              python lancer.py --tests    (tests de performance seulement)
              python lancer.py --port 8080
==========================================================
"""
import sys, os, subprocess, time, webbrowser, argparse

BASE = os.path.dirname(os.path.abspath(__file__))
REQUIREMENTS = os.path.join(BASE, 'requirements.txt')

def couleur(texte, code): return f"\033[{code}m{texte}\033[0m"
def vert(t): return couleur(t, '92')
def jaune(t): return couleur(t, '93')
def rouge(t): return couleur(t, '91')
def cyan(t):  return couleur(t, '96')
def gras(t):  return couleur(t, '1')

def titre():
    print(f"""
{cyan('='*60)}
{gras(cyan('  🗑️  SYSTÈME DE COLLECTE DE DÉCHETS - AGADIR'))}
{cyan('  Projet Complexité Algorithmique - Flask App')}
{cyan('='*60)}
""")

def installer_dependances():
    print(jaune("📦 Vérification des dépendances..."))
    try:
        import flask
        print(vert("  ✔ Flask déjà installé"))
        return True
    except ImportError:
        print(jaune("  → Installation de Flask..."))

    try:
        result = subprocess.run(
            [sys.executable, '-m', 'pip', 'install', '-r', REQUIREMENTS,
             '--quiet', '--break-system-packages'],
            capture_output=True, text=True, timeout=120
        )
        if result.returncode == 0:
            print(vert("  ✔ Dépendances installées avec succès"))
            return True
        else:
            # Essai sans --break-system-packages (Windows / venv)
            result2 = subprocess.run(
                [sys.executable, '-m', 'pip', 'install', '-r', REQUIREMENTS, '--quiet'],
                capture_output=True, text=True, timeout=120
            )
            if result2.returncode == 0:
                print(vert("  ✔ Dépendances installées"))
                return True
            print(rouge(f"  ✘ Erreur d'installation : {result2.stderr}"))
            return False
    except Exception as e:
        print(rouge(f"  ✘ Erreur : {e}"))
        return False

def lancer_tests():
    print(f"\n{cyan('─'*60)}")
    print(gras("🧪 Lancement des tests de performance..."))
    print(f"{cyan('─'*60)}\n")
    script = os.path.join(BASE, 'tests_performance.py')
    subprocess.run([sys.executable, script], cwd=BASE)

def lancer_app(port=5000):
    print(f"\n{cyan('─'*60)}")
    print(gras(f"🚀 Démarrage de l'application sur le port {port}..."))
    print(f"{cyan('─'*60)}")
    print(f"\n  🌐 Accès : {vert(f'http://localhost:{port}')}")
    print(f"  ℹ️  Appuyez sur {jaune('Ctrl+C')} pour arrêter\n")

    env = os.environ.copy()
    env['FLASK_ENV'] = 'development'

    # Ouvrir le navigateur après 1.5 secondes
    def open_browser():
        time.sleep(1.5)
        webbrowser.open(f'http://localhost:{port}')

    import threading
    threading.Thread(target=open_browser, daemon=True).start()

    try:
        subprocess.run(
            [sys.executable, 'app.py'],
            cwd=BASE, env=env
        )
    except KeyboardInterrupt:
        print(f"\n\n{jaune('  Application arrêtée. À bientôt !')}\n")

def main():
    titre()
    parser = argparse.ArgumentParser(description='Lanceur du projet collecte déchets')
    parser.add_argument('--tests', action='store_true', help='Exécuter les tests de performance')
    parser.add_argument('--port', type=int, default=5000, help='Port de l\'application (défaut: 5000)')
    args = parser.parse_args()

    if not installer_dependances():
        print(rouge("\n✘ Impossible d'installer les dépendances. Vérifiez votre connexion."))
        sys.exit(1)

    if args.tests:
        lancer_tests()
    else:
        print(f"\n{jaune('Options disponibles :')}")
        print(f"  • {vert('python lancer.py')}          → Démarre l'application web")
        print(f"  • {vert('python lancer.py --tests')}  → Lance les tests de performance")
        print(f"  • {vert('python lancer.py --port 8080')} → Port personnalisé\n")
        lancer_app(args.port)

if __name__ == '__main__':
    main()
