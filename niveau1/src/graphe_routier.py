import math
import heapq
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))
from commun.outils_math import distance_euclidienne, distance_haversine

class PointCollecte:
    def __init__(self, id_point, x, y, nom="", lat=None, lon=None, adresse=""):
        self.id = id_point
        self.x = x
        self.y = y
        self.nom = nom
        self.lat = lat
        self.lon = lon
        self.adresse = adresse

    def distance_vers(self, autre_point):
        if self.lat and self.lon and autre_point.lat and autre_point.lon:
            return distance_haversine(self.lat, self.lon, autre_point.lat, autre_point.lon)
        return distance_euclidienne(self.x, self.y, autre_point.x, autre_point.y)

    def to_dict(self):
        return {'id': self.id, 'x': self.x, 'y': self.y,
                'nom': self.nom, 'lat': self.lat, 'lon': self.lon, 'adresse': self.adresse}

    @classmethod
    def from_dict(cls, d):
        return cls(d['id'], d.get('x', 0), d.get('y', 0),
                   d.get('nom', ''), d.get('lat'), d.get('lon'), d.get('adresse', ''))


class GrapheRoutier:
    def __init__(self):
        self.sommets = {}
        self.aretes = {}
        self.adjacence = {}

    def ajouter_sommet(self, point):
        self.sommets[point.id] = point
        if point.id not in self.adjacence:
            self.adjacence[point.id] = {}

    def ajouter_arete(self, id1, id2, distance=None):
        if id1 not in self.sommets or id2 not in self.sommets:
            raise ValueError(f"Sommets {id1} ou {id2} inexistants")
        if distance is None:
            distance = self.sommets[id1].distance_vers(self.sommets[id2])
        self.aretes[(id1, id2)] = distance
        self.aretes[(id2, id1)] = distance
        self.adjacence[id1][id2] = distance
        self.adjacence[id2][id1] = distance

    def construire_graphe_complet(self):
        ids = list(self.sommets.keys())
        for i in range(len(ids)):
            for j in range(i+1, len(ids)):
                self.ajouter_arete(ids[i], ids[j])

    def plus_court_chemin(self, depart, arrivee):
        if depart not in self.sommets or arrivee not in self.sommets:
            return (float('inf'), [])
        # Graphe complet : arête directe disponible → pas besoin de Dijkstra
        if arrivee in self.adjacence.get(depart, {}):
            d = self.adjacence[depart][arrivee]
            return (round(d, 4), [depart, arrivee])
        # Fallback Dijkstra pour graphes non complets
        dist = {id_: float('inf') for id_ in self.sommets}
        dist[depart] = 0
        pred = {id_: None for id_ in self.sommets}
        pq = [(0, depart)]
        visite = set()
        while pq:
            d, u = heapq.heappop(pq)
            if u in visite:
                continue
            visite.add(u)
            if u == arrivee:
                break
            for v, w in self.adjacence.get(u, {}).items():
                if dist[u] + w < dist[v]:
                    dist[v] = dist[u] + w
                    pred[v] = u
                    heapq.heappush(pq, (dist[v], v))
        chemin = []
        courant = arrivee
        while courant is not None:
            chemin.append(courant)
            courant = pred[courant]
        chemin.reverse()
        if not chemin or chemin[0] != depart:
            return (float('inf'), [])
        return (round(dist[arrivee], 4), chemin)

    def matrice_distances(self):
        ids = sorted(self.sommets.keys())
        n = len(ids)
        matrice = [[0.0]*n for _ in range(n)]
        chemins = []
        for i, id1 in enumerate(ids):
            for j, id2 in enumerate(ids):
                if i != j:
                    d, ch = self.plus_court_chemin(id1, id2)
                    matrice[i][j] = round(d, 4)
                    if i < j:
                        chemins.append({'depart': id1, 'arrivee': id2, 'distance': round(d, 4), 'chemin': ch})
        return matrice, ids, chemins

    def est_connexe(self):
        if not self.sommets:
            return True
        debut = next(iter(self.sommets))
        visite = set()
        pile = [debut]
        while pile:
            u = pile.pop()
            if u in visite:
                continue
            visite.add(u)
            for v in self.adjacence.get(u, {}):
                if v not in visite:
                    pile.append(v)
        return len(visite) == len(self.sommets)

    def to_dict(self):
        return {
            'sommets': {k: v.to_dict() for k, v in self.sommets.items()},
            'aretes': {str(k): v for k, v in self.aretes.items()}
        }
