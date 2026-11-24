# 🗑️ Système de Collecte de Déchets — Agadir

Projet de complexité algorithmique — Optimisation des tournées de collecte

## 🚀 Lancement Rapide (en 1 commande)

```bash
python lancer.py
```

Ce script installe automatiquement Flask et ouvre l'application dans votre navigateur.

### Options disponibles

```bash
python lancer.py               # Démarre l'application web (port 5000)
python lancer.py --tests       # Exécute les 3 tests de performance
python lancer.py --port 8080   # Port personnalisé
```

## 📋 Prérequis

- **Python 3.8+** uniquement (les dépendances s'installent automatiquement)

## 🧪 Tests de Performance

Trois jeux de tests prédéfinis :

| Test | Camions | Points | Poids total |
|------|---------|--------|-------------|
| Petit | 5 | 50 | ~13 tonnes |
| Intermédiaire | 10 | 100 | ~28 tonnes |
| Grand | 20 | 500 | ~143 tonnes |

Chaque point contient 1 à 3 bennes (150–600 kg par point).
Les résultats affichent le **tonnage transporté par km** pour chaque camion.

## 🏗️ Architecture — 5 Niveaux

```
N1 → Graphe Routier      (Dijkstra)
N2 → Affectation Zones   (Glouton + Équilibrage)
N3 → Planification       (Contraintes horaires)
N4 → Optimisation VRP    (2-opt + Recherche Tabou)
N5 → Simulation IoT      (Multi-objectif temps réel)
```



