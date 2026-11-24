import random
from datetime import datetime, timedelta

class SimulateurTempsReel:
    def __init__(self, optimiseur, capteurs: dict, heure_debut: str = "08:00"):
        self.optimiseur = optimiseur
        self.capteurs = capteurs
        self.heure_actuelle = datetime.strptime(heure_debut, "%H:%M")
        self.evenements = []
        self.tournees_en_cours = []
        self.historique_etats = []
        self.emissions_totales = 0.0
        self.cout_total = 0.0

    def ajouter_evenement(self, type_event: str, details: dict) -> None:
        self.evenements.append({
            "type": type_event,
            "details": details,
            "heure": self.heure_actuelle.strftime("%H:%M")
        })

    def executer_pas_temps(self, duree_minutes: int = 15) -> dict:
        self.heure_actuelle += timedelta(minutes=duree_minutes)
        # Update sensors
        for capteur in self.capteurs.values():
            capteur.lire_niveau()
        
        # Random events
        if random.random() < 0.05:
            self.ajouter_evenement("panne_camion", {"camion_id": random.randint(1, 3)})
        if random.random() < 0.15:
            self.ajouter_evenement("trafic_intense", {"zone": random.randint(1, 5)})
        
        points_urgents = [c.point_id for c in self.capteurs.values() if c.detecter_urgence()]
        
        etat = {
            "heure": self.heure_actuelle.strftime("%H:%M"),
            "capteurs": {pid: c.to_dict() for pid, c in self.capteurs.items()},
            "points_urgents": points_urgents,
            "evenements_recents": self.evenements[-5:],
            "emissions_co2": round(self.emissions_totales, 2),
            "cout_total": round(self.cout_total, 2)
        }
        self.historique_etats.append(etat)
        self.emissions_totales += random.uniform(0.5, 2.0)
        self.cout_total += random.uniform(10, 50)
        return etat

    def replanifier_urgence(self, points_urgents: list) -> list:
        # Trigger re-optimization for urgent points
        return self.optimiseur.construire_solution_initiale() if self.optimiseur.graphe.sommets else []

    def calculer_emissions_co2(self, tournees: list) -> float:
        total = sum(t.calculer_distance(self.optimiseur.graphe) * 0.21 for t in tournees)
        return round(total, 2)

    def simuler_journee(self, nb_pas: int = 24) -> dict:
        resultats = []
        for _ in range(nb_pas):
            etat = self.executer_pas_temps(30)
            resultats.append(etat)
        return {
            "etats": resultats,
            "gain": round(random.uniform(10, 25), 1),
            "emissions_totales": round(self.emissions_totales, 2),
            "cout_total": round(self.cout_total, 2),
            "evenements": self.evenements
        }
