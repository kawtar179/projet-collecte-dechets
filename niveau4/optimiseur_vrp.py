"""
Niveau 4 : VRP Enrichi avec Points Réels
Algorithme 2-opt et Recherche Tabou
"""
import sys, os, math, random, copy
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class Tournee:
    def __init__(self, camion_id: int, camion_capacite: float = 9999):
        self.camion_id = camion_id
        self.points = []         # IDs ordonnés (sans dépôt)
        self.camion_capacite = camion_capacite
        self.charge = 0.0
        self.heure_depart = "08:00"

    def ajouter_point(self, point_id: int, demande: float = 0.0, position: int = -1) -> bool:
        if self.charge + demande > self.camion_capacite:
            return False
        if position == -1:
            self.points.append(point_id)
        else:
            self.points.insert(position, point_id)
        self.charge += demande
        return True

    def calculer_distance(self, graphe) -> float:
        if not self.points:
            return 0.0
        total = 0.0
        route = [0] + self.points + [0]  # 0 = dépôt
        for i in range(len(route) - 1):
            d, _ = graphe.plus_court_chemin(route[i], route[i+1])
            if d == float('inf'):
                # Distance euclidienne fallback
                if route[i] in graphe.sommets and route[i+1] in graphe.sommets:
                    p1 = graphe.sommets[route[i]]
                    p2 = graphe.sommets[route[i+1]]
                    d = math.sqrt((p1.x-p2.x)**2 + (p1.y-p2.y)**2)
                else:
                    d = 999
            total += d
        return round(total, 3)

    def to_dict(self, graphe=None):
        dist = self.calculer_distance(graphe) if graphe else 0
        return {
            "camion_id": self.camion_id,
            "points_ordre": [0] + self.points + [0],
            "distance_totale": dist,
            "charge_finale": self.charge,
            "heure_depart": self.heure_depart,
            "nb_points": len(self.points)
        }


class OptimiseurVRP:
    def __init__(self, graphe, camions: list, points: list = None):
        self.graphe = graphe
        self.camions = camions
        self.points = points or [p for pid, p in graphe.sommets.items() if pid != 0]
        self.tournees = []

    def _dist(self, id1, id2) -> float:
        d, _ = self.graphe.plus_court_chemin(id1, id2)
        if d == float('inf') and id1 in self.graphe.sommets and id2 in self.graphe.sommets:
            p1, p2 = self.graphe.sommets[id1], self.graphe.sommets[id2]
            return math.sqrt((p1.x-p2.x)**2 + (p1.y-p2.y)**2)
        return d

    def construire_solution_initiale(self) -> list:
        """Construction gloutonne (plus proche voisin)"""
        points_restants = [p.id for p in self.points if p.id != 0]
        tournees = []

        for camion in self.camions:
            if not points_restants:
                break
            tournee = Tournee(camion.id, camion.capacite)
            courant = 0  # dépôt
            while points_restants:
                # Trouver le plus proche point non visité
                meilleur = None
                meilleure_dist = float('inf')
                for pid in points_restants:
                    pt = self.graphe.sommets.get(pid)
                    if pt is None:
                        continue
                    demande = pt.demande
                    if tournee.charge + demande > camion.capacite:
                        continue
                    d = self._dist(courant, pid)
                    if d < meilleure_dist:
                        meilleure_dist = d
                        meilleur = pid
                if meilleur is None:
                    break
                pt = self.graphe.sommets[meilleur]
                tournee.ajouter_point(meilleur, pt.demande)
                points_restants.remove(meilleur)
                courant = meilleur
            if tournee.points:
                tournees.append(tournee)

        # Assignation des points restants au dernier camion avec capacité infinie
        if points_restants and tournees:
            for pid in points_restants:
                pt = self.graphe.sommets.get(pid)
                tournees[-1].points.append(pid)

        return tournees

    def algorithme_2opt(self, tournee: Tournee) -> Tournee:
        """Améliore une tournée par échanges 2-opt"""
        if len(tournee.points) < 3:
            return tournee
        improved = True
        while improved:
            improved = False
            for i in range(len(tournee.points) - 1):
                for j in range(i + 2, len(tournee.points)):
                    route = tournee.points[:]
                    # Gain: retirer arêtes (i,i+1) et (j,j+1), ajouter (i,j) et (i+1,j+1)
                    r1 = [0] + route
                    a, b = r1[i], route[i]
                    c, d = route[j-1] if j > 0 else 0, route[j]
                    avant = self._dist(a, b) + self._dist(c, d)
                    apres = self._dist(a, c) + self._dist(b, d)
                    if apres < avant - 0.001:
                        tournee.points[i:j] = tournee.points[i:j][::-1]
                        improved = True
        return tournee

    def recherche_tabou(self, iterations: int = 100) -> list:
        """Recherche Tabou pour optimisation globale"""
        tournees = self.construire_solution_initiale()
        # Améliorer chaque tournée avec 2-opt
        tournees = [self.algorithme_2opt(t) for t in tournees]

        meilleure_dist = sum(t.calculer_distance(self.graphe) for t in tournees)
        meilleures_tournees = copy.deepcopy(tournees)
        liste_tabou = []
        taille_tabou = 10

        for it in range(min(iterations, 50)):
            if len(tournees) < 2:
                break
            # Mouvement: échanger un point entre deux tournées
            t1_idx = random.randint(0, len(tournees) - 1)
            t2_idx = random.randint(0, len(tournees) - 1)
            if t1_idx == t2_idx or not tournees[t1_idx].points:
                continue

            pid = random.choice(tournees[t1_idx].points)
            mouvement = (t1_idx, t2_idx, pid)
            if mouvement in liste_tabou:
                continue

            pt = self.graphe.sommets.get(pid)
            if pt is None:
                continue
            camion2 = self.camions[t2_idx] if t2_idx < len(self.camions) else self.camions[-1]
            if tournees[t2_idx].charge + pt.demande > camion2.capacite:
                continue

            tournees[t1_idx].points.remove(pid)
            tournees[t1_idx].charge -= pt.demande
            tournees[t2_idx].points.append(pid)
            tournees[t2_idx].charge += pt.demande

            dist_actuelle = sum(t.calculer_distance(self.graphe) for t in tournees)
            if dist_actuelle < meilleure_dist:
                meilleure_dist = dist_actuelle
                meilleures_tournees = copy.deepcopy(tournees)

            liste_tabou.append(mouvement)
            if len(liste_tabou) > taille_tabou:
                liste_tabou.pop(0)

        self.tournees = meilleures_tournees
        return meilleures_tournees

    def evaluer_solution(self, tournees: list) -> dict:
        dists = [t.calculer_distance(self.graphe) for t in tournees]
        charges = [t.charge for t in tournees]
        total_dist = sum(dists)
        return {
            "distance_totale": round(total_dist, 2),
            "distance_moyenne": round(total_dist / len(tournees), 2) if tournees else 0,
            "charge_moyenne": round(sum(charges) / len(charges), 1) if charges else 0,
            "taux_utilisation": round(
                sum(t.charge / (self.camions[i].capacite if i < len(self.camions) else 1)
                    for i, t in enumerate(tournees)) / len(tournees) * 100, 1
            ) if tournees else 0
        }
