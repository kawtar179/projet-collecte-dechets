"""
Modèles de données communs réutilisables entre tous les niveaux
"""
import math
from datetime import datetime


class PointCollecte:
    def __init__(self, id_point: int, x: float, y: float, nom: str = "",
                 demande: float = 0.0, temps_service: int = 5):
        self.id = id_point
        self.x = x
        self.y = y
        self.nom = nom
        self.demande = demande
        self.temps_service = temps_service  # minutes

    def distance_vers(self, autre_point) -> float:
        """Calcule la distance euclidienne vers un autre point"""
        return math.sqrt((self.x - autre_point.x)**2 + (self.y - autre_point.y)**2)

    def to_dict(self):
        return {
            "id": self.id, "x": self.x, "y": self.y,
            "nom": self.nom, "demande": self.demande,
            "temps_service": self.temps_service
        }

    @classmethod
    def from_dict(cls, d):
        return cls(d["id"], d["x"], d["y"],
                   d.get("nom", ""), d.get("demande", 0.0),
                   d.get("temps_service", 5))


class Camion:
    def __init__(self, id_camion: int, capacite: float, cout_fixe: float,
                 zones_accessibles: list = None, position_x: float = 0,
                 position_y: float = 0, plaque: str = ""):
        self.id = id_camion
        self.capacite = capacite
        self.cout_fixe = cout_fixe
        self.zones_accessibles = zones_accessibles or []
        self.position_x = position_x
        self.position_y = position_y
        self.plaque = plaque
        self.charge_actuelle = 0.0
        self.disponible = True

    def to_dict(self):
        return {
            "id": self.id, "capacite": self.capacite,
            "cout_fixe": self.cout_fixe,
            "zones_accessibles": self.zones_accessibles,
            "position_x": self.position_x, "position_y": self.position_y,
            "plaque": self.plaque, "disponible": self.disponible
        }

    @classmethod
    def from_dict(cls, d):
        c = cls(d["id"], d["capacite"], d.get("cout_fixe", 200),
                d.get("zones_accessibles", []),
                d.get("position_x", 0), d.get("position_y", 0),
                d.get("plaque", ""))
        return c


class Zone:
    def __init__(self, id_zone: int, nom: str, points: list,
                 volume_estime: float, centre_x: float, centre_y: float,
                 priorite: str = "normale"):
        self.id = id_zone
        self.nom = nom
        self.points = points
        self.volume_estime = volume_estime
        self.centre_x = centre_x
        self.centre_y = centre_y
        self.priorite = priorite  # haute, normale, basse
        self.polygon_coords = []  # Pour carte Leaflet

    def to_dict(self):
        return {
            "id": self.id, "nom": self.nom, "points": self.points,
            "volume_estime": self.volume_estime,
            "centre_x": self.centre_x, "centre_y": self.centre_y,
            "priorite": self.priorite,
            "polygon_coords": self.polygon_coords
        }

    @classmethod
    def from_dict(cls, d):
        z = cls(d["id"], d.get("nom", f"Zone {d['id']}"),
                d.get("points", []), d.get("volume_estime", 1000),
                d.get("centre_x", 0), d.get("centre_y", 0),
                d.get("priorite", "normale"))
        z.polygon_coords = d.get("polygon_coords", [])
        return z
