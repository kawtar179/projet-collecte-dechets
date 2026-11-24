from datetime import datetime, timedelta

class CreneauHoraire:
    def __init__(self, id_creneau: int, debut: str, fin: str, jour: str, cout_congestion: float = 1.0):
        self.id = id_creneau
        self.debut = datetime.strptime(debut, "%H:%M")
        self.fin = datetime.strptime(fin, "%H:%M")
        self.jour = jour
        self.cout_congestion = cout_congestion

    def duree(self) -> float:
        delta = self.fin - self.debut
        return delta.seconds / 3600.0

    def chevauche(self, autre) -> bool:
        return not (self.fin <= autre.debut or autre.fin <= self.debut)

    def to_dict(self):
        return {
            "id": self.id,
            "debut": self.debut.strftime("%H:%M"),
            "fin": self.fin.strftime("%H:%M"),
            "jour": self.jour,
            "cout_congestion": self.cout_congestion,
            "duree_heures": self.duree()
        }

    @staticmethod
    def from_dict(d):
        return CreneauHoraire(d["id"], d["debut"], d["fin"], d["jour"], d.get("cout_congestion", 1.0))
