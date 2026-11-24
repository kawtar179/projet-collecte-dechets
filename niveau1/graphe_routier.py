"""
Niveau 1 : Modèle de Base - Réseau Routier
Graphe 1-partie avec algorithme de Dijkstra
"""
import heapq
import math
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from commun.models import PointCollecte


class GrapheRoutier:
    def __init__(self):
        self.sommets = {}      # {id: PointCollecte}
        self.aretes = {}       # {(id1, id2): distance}
        self.adjacence = {}    # {id: [(voisin_id, distance)]}

    def ajouter_sommet(self, point: PointCollecte) -> None:
        self.sommets[point.id] = point
        if point.id not in self.adjacence:
            self.adjacence[point.id] = []

    def ajouter_arete(self, id1: int, id2: int, distance: float = None) -> None:
        if id1 not in self.sommets or id2 not in self.sommets:
            return
        if distance is None:
            distance = self.sommets[id1].distance_vers(self.sommets[id2])
        distance = round(distance, 4)
        self.aretes[(id1, id2)] = distance
        self.aretes[(id2, id1)] = distance
        self.adjacence[id1].append((id2, distance))
        self.adjacence[id2].append((id1, distance))

    def plus_court_chemin(self, depart: int, arrivee: int) -> tuple:
        """Retourne (distance, chemin) avec Dijkstra"""
        if depart not in self.sommets or arrivee not in self.sommets:
            return (float('inf'), [])
        if depart == arrivee:
            return (0.0, [depart])

        dist = {v: float('inf') for v in self.sommets}
        dist[depart] = 0
        predecesseur = {v: None for v in self.sommets}
        pq = [(0, depart)]

        while pq:
            d, u = heapq.heappop(pq)
            if d > dist[u]:
                continue
            if u == arrivee:
                break
            for voisin, poids in self.adjacence.get(u, []):
                nd = dist[u] + poids
                if nd < dist[voisin]:
                    dist[voisin] = nd
                    predecesseur[voisin] = u
                    heapq.heappush(pq, (nd, voisin))

        # Reconstituer chemin
        if dist[arrivee] == float('inf'):
            return (float('inf'), [])
        chemin = []
        courant = arrivee
        while courant is not None:
            chemin.append(courant)
            courant = predecesseur[courant]
        chemin.reverse()
        return (round(dist[arrivee], 4), chemin)

    def matrice_distances(self) -> list:
        """Retourne la matrice des distances entre tous les sommets"""
        ids = sorted(self.sommets.keys())
        n = len(ids)
        matrice = [[0.0] * n for _ in range(n)]
        for i, id_i in enumerate(ids):
            for j, id_j in enumerate(ids):
                if i != j:
                    d, _ = self.plus_court_chemin(id_i, id_j)
                    matrice[i][j] = d if d != float('inf') else -1
        return matrice, ids

    def est_connexe(self) -> bool:
        if not self.sommets:
            return True
        visite = set()
        depart = next(iter(self.sommets))
        pile = [depart]
        while pile:
            noeud = pile.pop()
            if noeud in visite:
                continue
            visite.add(noeud)
            for voisin, _ in self.adjacence.get(noeud, []):
                pile.append(voisin)
        return len(visite) == len(self.sommets)

    def to_dict(self):
        matrice, ids = self.matrice_distances()
        chemins = []
        ids_list = sorted(self.sommets.keys())
        if ids_list:
            src = ids_list[0]
            for dst in ids_list[1:]:
                d, ch = self.plus_court_chemin(src, dst)
                chemins.append({"depart": src, "arrivee": dst,
                                 "distance": d, "chemin": ch})
        return {
            "sommets": [p.to_dict() for p in self.sommets.values()],
            "matrice_ids": ids,
            "matrice_distances": matrice,
            "chemins_calcules": chemins,
            "connexe": self.est_connexe(),
            "nb_sommets": len(self.sommets),
            "nb_aretes": len(self.aretes) // 2
        }
