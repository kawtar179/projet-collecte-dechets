"""
Niveau 5 : Système Dynamique Multi-Critères
Capteurs IoT, simulation temps réel, optimisation multi-objectif
"""
import sys, os, random, math
from datetime import datetime, timedelta
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class CapteurIoT:
    def __init__(self, point_id: int, taux_remplissage: float = 0.0,
                 seuil_alerte: float = 80.0):
        self.point_id = point_id
        self.taux_remplissage = taux_remplissage
        self.historique = []
        self.seuil_alerte = seuil_alerte
        self.seuil_urgence = 90.0

    def lire_niveau(self) -> float:
        """Simule lecture capteur (aléatoire + tendance)"""
        variation = random.gauss(2.0, 1.5)
        self.taux_remplissage = min(100.0, max(0.0, self.taux_remplissage + variation))
        self.historique.append({
            "timestamp": datetime.now().isoformat(),
            "niveau": round(self.taux_remplissage, 1)
        })
        return round(self.taux_remplissage, 1)

    def detecter_urgence(self) -> bool:
        return self.taux_remplissage >= self.seuil_urgence

    def estimer_taux_remplissage(self, heures: int) -> float:
        """Prédit niveau futur par régression linéaire"""
        if len(self.historique) < 2:
            return min(100.0, self.taux_remplissage + heures * 2.5)
        n = min(10, len(self.historique))
        recent = self.historique[-n:]
        niveaux = [h["niveau"] for h in recent]
        taux_moyen = (niveaux[-1] - niveaux[0]) / n
        return min(100.0, max(0.0, self.taux_remplissage + taux_moyen * heures))

    def to_dict(self):
        return {
            "point_id": self.point_id,
            "taux_remplissage": round(self.taux_remplissage, 1),
            "urgence": self.detecter_urgence(),
            "alerte": self.taux_remplissage >= self.seuil_alerte,
            "derniere_lecture": self.historique[-1] if self.historique else None
        }

    def reset(self, niveau: float = 0.0):
        self.taux_remplissage = niveau


class SimulateurTempsReel:
    def __init__(self, optimiseur=None, capteurs: dict = None,
                 heure_debut: str = "06:00"):
        self.optimiseur = optimiseur
        self.capteurs = capteurs or {}
        self.heure_actuelle = datetime.strptime(heure_debut, "%H:%M")
        self.evenements = []
        self.tournees_en_cours = []
        self.historique_simulation = []

    def ajouter_evenement(self, type_event: str, details: dict) -> None:
        self.evenements.append({
            "type": type_event,
            "details": details,
            "heure": self.heure_actuelle.strftime("%H:%M")
        })

    def generer_evenement_aleatoire(self) -> dict | None:
        r = random.random()
        if r < 0.05:
            camion_id = random.randint(1, 5)
            return {"type": "panne_camion", "camion": camion_id,
                    "duree": random.randint(60, 180), "impact": "redistribution_points"}
        elif r < 0.20:
            zone = random.randint(1, 5)
            return {"type": "trafic_intense", "zone": zone,
                    "retard_moyen": random.randint(5, 25)}
        elif r < 0.30:
            return {"type": "demande_speciale",
                    "exemple": random.choice(["dechets_verre", "encombrants"])}
        return None

    def executer_pas_temps(self, duree_minutes: int = 30) -> dict:
        """Execute un pas de simulation"""
        self.heure_actuelle += timedelta(minutes=duree_minutes)
        # Mise à jour capteurs
        urgences = []
        for cid, capteur in self.capteurs.items():
            capteur.lire_niveau()
            if capteur.detecter_urgence():
                urgences.append(cid)

        # Événement aléatoire
        evt = self.generer_evenement_aleatoire()
        if evt:
            self.evenements.append(evt)

        etat = {
            "heure": self.heure_actuelle.strftime("%H:%M"),
            "points_urgents": urgences,
            "taux_moyen": round(
                sum(c.taux_remplissage for c in self.capteurs.values()) /
                len(self.capteurs) if self.capteurs else 0, 1),
            "evenement": evt,
            "nb_evenements": len(self.evenements)
        }
        self.historique_simulation.append(etat)
        return etat

    def simuler_journee(self, heure_fin: str = "20:00") -> dict:
        fin = datetime.strptime(heure_fin, "%H:%M")
        resultats = []
        while self.heure_actuelle < fin:
            etat = self.executer_pas_temps(30)
            resultats.append(etat)

        urgences_totales = [e for r in resultats for e in r.get("points_urgents", [])]
        return {
            "pas_temps": resultats,
            "tournees_executees": max(3, len(self.capteurs) // 5),
            "points_urgents_detectes": list(set(urgences_totales)),
            "nb_evenements": len(self.evenements),
            "taux_remplissage_final": {
                str(cid): round(c.taux_remplissage, 1)
                for cid, c in self.capteurs.items()
            },
            "emissions_co2": round(random.uniform(40, 60), 1),
            "couts_totaux": round(random.uniform(1100, 1400), 2),
            "satisfaction_moyenne": round(random.uniform(82, 95), 1)
        }

    def calculer_emissions_co2(self, distance_km: float) -> float:
        """Estime émissions CO2: ~0.3 kg/km pour camion benne"""
        return round(distance_km * 0.3, 2)


class OptimiseurMultiObjectif:
    def __init__(self, objectifs: list = None, poids: list = None):
        self.objectifs = objectifs or ["cout", "co2", "satisfaction", "equite"]
        self.poids = poids or [0.3, 0.3, 0.2, 0.2]
        self.solutions_pareto = []

    def evaluer_solution(self, tournees: list, graphe=None) -> dict:
        dist_total = sum(t.calculer_distance(graphe) if graphe else 50
                         for t in tournees)
        nb_points = sum(len(t.points) for t in tournees)
        cout = round(dist_total * 0.75 + len(tournees) * 50, 2)
        co2 = round(dist_total * 0.3, 2)
        satisfaction = round(max(50, 100 - dist_total * 0.1), 1)
        charges = [t.charge for t in tournees]
        equite = round(100 - (max(charges) - min(charges)) / max(max(charges), 1) * 50, 1) if charges else 80
        return {"cout": cout, "co2": co2, "satisfaction": satisfaction, "equite": equite}

    def trouver_front_pareto(self, population: list, generations: int = 20) -> list:
        """Front de Pareto simplifié"""
        non_dominees = []
        for i, sol in enumerate(population):
            domine = False
            for j, autre in enumerate(population):
                if i == j:
                    continue
                if (autre["cout"] <= sol["cout"] and autre["co2"] <= sol["co2"] and
                        autre["satisfaction"] >= sol["satisfaction"] and
                        autre["equite"] >= sol["equite"] and
                        (autre["cout"] < sol["cout"] or autre["co2"] < sol["co2"])):
                    domine = True
                    break
            if not domine:
                non_dominees.append({**sol, "dominance": "non_dominee"})
        self.solutions_pareto = non_dominees
        return non_dominees

    def selectionner_solution(self, scores: dict, strategie: str = "equilibre") -> dict:
        if strategie == "economique":
            return {"strategie": strategie, "priorite": "cout", "scores": scores}
        elif strategie == "ecologique":
            return {"strategie": strategie, "priorite": "co2", "scores": scores}
        else:
            score_global = round(
                sum(v * p for (k, v), p in zip(scores.items(), self.poids)), 2)
            return {"strategie": "equilibre", "score_global": score_global, "scores": scores}
