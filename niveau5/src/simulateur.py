import random
import math
from datetime import datetime, timedelta
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))

class CapteurIoT:
    def __init__(self, point_id, taux_initial=0.0, seuil_alerte=80.0):
        self.point_id = point_id
        self.taux = taux_initial
        self.historique = []
        self.seuil_alerte = seuil_alerte

    def lire_niveau(self):
        delta = random.gauss(2, 1)
        self.taux = min(100, max(0, self.taux + delta))
        self.historique.append((datetime.now().isoformat(), round(self.taux, 1)))
        if len(self.historique) > 100:
            self.historique.pop(0)
        return round(self.taux, 1)

    def detecter_urgence(self):
        return self.taux >= self.seuil_alerte

    def estimer_remplissage(self, heures):
        if len(self.historique) < 2:
            return min(100, self.taux + heures * 2)
        # Régression linéaire simple
        n = min(10, len(self.historique))
        recent = [v for _, v in self.historique[-n:]]
        if len(recent) >= 2:
            pente = (recent[-1] - recent[0]) / max(1, len(recent)-1)
            return min(100, max(0, self.taux + pente * heures))
        return self.taux

    def to_dict(self):
        return {'point_id': self.point_id, 'taux': round(self.taux, 1),
                'urgence': self.detecter_urgence(), 'seuil': self.seuil_alerte}


class SimulateurTempsReel:
    def __init__(self, optimiseur, capteurs, heure_debut="08:00"):
        self.optimiseur = optimiseur
        self.capteurs = capteurs  # {point_id: CapteurIoT}
        self.heure = datetime.strptime(heure_debut, "%H:%M")
        self.evenements = []
        self.historique_journee = []
        self.co2_total = 0
        self.cout_total = 0

    def ajouter_evenement(self, type_event, details):
        self.evenements.append({'type': type_event, 'details': details,
                                 'heure': self.heure.strftime("%H:%M")})

    def generer_evenement_aleatoire(self):
        rand = random.random()
        if rand < 0.05:
            return {'type': 'panne_camion', 'camion': random.randint(1, 3), 'duree': random.randint(30, 180)}
        elif rand < 0.20:
            return {'type': 'trafic_intense', 'zone': random.randint(1, 5), 'impact': 0.5}
        elif rand < 0.30:
            return {'type': 'demande_speciale', 'point': random.randint(1, 10)}
        return None

    def executer_pas_temps(self, duree_minutes=30):
        self.heure += timedelta(minutes=duree_minutes)
        # Mettre à jour capteurs
        urgents = []
        for pid, capteur in self.capteurs.items():
            capteur.lire_niveau()
            if capteur.detecter_urgence():
                urgents.append(pid)
        # Événement aléatoire
        ev = self.generer_evenement_aleatoire()
        if ev:
            self.evenements.append({**ev, 'heure': self.heure.strftime("%H:%M")})
        etat = {
            'heure': self.heure.strftime("%H:%M"),
            'points_urgents': urgents,
            'evenement': ev,
            'capteurs': {pid: c.to_dict() for pid, c in self.capteurs.items()}
        }
        self.historique_journee.append(etat)
        return etat

    def calculer_emissions_co2(self, tournees):
        total_dist = sum(t.calculer_distance(self.optimiseur.graphe,
                         self.optimiseur.depot_id) for t in tournees)
        return round(total_dist * 0.3, 2)  # 0.3 kg CO2/km

    def simuler_journee(self, nb_pas=14):
        resultats = []
        for _ in range(nb_pas):
            etat = self.executer_pas_temps(30)
            resultats.append(etat)
        return resultats


class OptimiseurMultiObjectif:
    def __init__(self, objectifs, poids=None):
        self.objectifs = objectifs
        self.poids = poids or [1.0/len(objectifs)]*len(objectifs)
        self.solutions_pareto = []

    def evaluer_solution(self, tournees, graphe=None, depot_id=0):
        if not tournees:
            return [0, 0, 50, 50]
        distances = [t.calculer_distance(graphe, depot_id) if graphe else 10 for t in tournees]
        dist_total = sum(distances)
        co2 = dist_total * 0.3
        cout = dist_total * 0.88 + sum(500 for _ in tournees)
        charges = [t.charge for t in tournees]
        moy = sum(charges)/max(1, len(charges))
        equite = max(0, 100 - (max(charges, default=0) - min(charges, default=0))/max(1,moy)*100)
        satisfaction = max(0, 100 - dist_total * 0.5)
        return [round(cout, 2), round(co2, 2), round(satisfaction, 2), round(equite, 2)]

    def score_pondere(self, scores):
        normalized = []
        maxes = [2000, 100, 100, 100]
        for i, s in enumerate(scores):
            obj = self.objectifs[i] if i < len(self.objectifs) else {}
            if obj.get('type') == 'minimiser':
                normalized.append(1 - s/maxes[i])
            else:
                normalized.append(s/maxes[i])
        return sum(n*p for n, p in zip(normalized, self.poids))
