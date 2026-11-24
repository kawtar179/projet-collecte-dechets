from datetime import datetime

class ContrainteTemporelle:
    def __init__(self):
        self.fenetres_zone = {}   # {zone_id: (debut_str, fin_str)}
        self.pauses_camion = {}   # {camion_id: [(debut_str, duree_h)]}
        self.zones_interdites_nuit = []

    def ajouter_fenetre_zone(self, zone_id: int, debut: str, fin: str):
        self.fenetres_zone[zone_id] = (debut, fin)

    def ajouter_pause_camion(self, camion_id: int, debut: str, duree: float):
        if camion_id not in self.pauses_camion:
            self.pauses_camion[camion_id] = []
        self.pauses_camion[camion_id].append((debut, duree))

    def est_realisable(self, camion_id: int, zone_id: int, creneau) -> bool:
        if zone_id in self.zones_interdites_nuit:
            if creneau.debut.hour < 6 or creneau.fin.hour > 22:
                return False
        if zone_id in self.fenetres_zone:
            deb_str, fin_str = self.fenetres_zone[zone_id]
            deb = datetime.strptime(deb_str, "%H:%M")
            fin = datetime.strptime(fin_str, "%H:%M")
            if creneau.debut < deb or creneau.fin > fin:
                return False
        return True

    def calculer_penalite(self, camion_id: int, zone_id: int, creneau) -> float:
        penalite = 0.0
        penalite += (creneau.cout_congestion - 1.0) * 30
        if zone_id in self.fenetres_zone:
            deb_str, fin_str = self.fenetres_zone[zone_id]
            deb = datetime.strptime(deb_str, "%H:%M")
            fin = datetime.strptime(fin_str, "%H:%M")
            if creneau.debut < deb:
                delta = (deb - creneau.debut).seconds / 60
                penalite += delta * 0.5
        return round(penalite, 2)

    def to_dict(self):
        return {
            "fenetres_zone": {str(k): list(v) for k, v in self.fenetres_zone.items()},
            "pauses_camion": {str(k): v for k, v in self.pauses_camion.items()},
            "zones_interdites_nuit": self.zones_interdites_nuit
        }
