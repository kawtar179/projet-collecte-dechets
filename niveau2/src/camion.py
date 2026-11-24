class Camion:
    def __init__(self, id_camion: int, capacite: float, cout_fixe: float,
                 zones_accessibles: list = None, position_initiale: dict = None,
                 couleur: str = "#3498db"):
        self.id = id_camion
        self.capacite = capacite
        self.cout_fixe = cout_fixe
        self.zones_accessibles = zones_accessibles or []
        self.position_initiale = position_initiale or {"x": 0, "y": 0}
        self.charge_actuelle = 0.0
        self.couleur = couleur
        self.en_service = True

    def peut_acceder_zone(self, zone_id: int) -> bool:
        return not self.zones_accessibles or zone_id in self.zones_accessibles

    def ajouter_charge(self, volume: float) -> bool:
        if self.charge_actuelle + volume <= self.capacite:
            self.charge_actuelle += volume
            return True
        return False

    def taux_utilisation(self) -> float:
        if self.capacite == 0:
            return 0
        return round(self.charge_actuelle / self.capacite * 100, 1)

    def to_dict(self):
        return {
            "id": self.id, "capacite": self.capacite, "cout_fixe": self.cout_fixe,
            "zones_accessibles": self.zones_accessibles,
            "position_initiale": self.position_initiale,
            "charge_actuelle": self.charge_actuelle,
            "taux_utilisation": self.taux_utilisation(),
            "couleur": self.couleur, "en_service": self.en_service
        }

    @staticmethod
    def from_dict(d):
        c = Camion(d["id"], d["capacite"], d.get("cout_fixe", 200),
                   d.get("zones_accessibles", []), d.get("position_initiale"),
                   d.get("couleur", "#3498db"))
        c.en_service = d.get("en_service", True)
        return c
