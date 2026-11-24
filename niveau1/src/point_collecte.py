import math

class PointCollecte:
    def __init__(self, id_point: int, x: float, y: float, nom: str = "", demande: float = 0.0):
        self.id = id_point
        self.x = x
        self.y = y
        self.nom = nom
        self.demande = demande

    def distance_vers(self, autre_point) -> float:
        return math.sqrt((self.x - autre_point.x)**2 + (self.y - autre_point.y)**2)

    def to_dict(self):
        return {"id": self.id, "x": self.x, "y": self.y, "nom": self.nom, "demande": self.demande}

    @staticmethod
    def from_dict(d):
        return PointCollecte(d["id"], d["x"], d["y"], d.get("nom",""), d.get("demande", 0.0))
