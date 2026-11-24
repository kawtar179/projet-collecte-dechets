import random
from datetime import datetime

class CapteurIoT:
    def __init__(self, point_id: int, taux_remplissage: float = 0.0,
                 seuil_alerte: float = 80.0, seuil_urgence: float = 90.0):
        self.point_id = point_id
        self.taux_remplissage = taux_remplissage
        self.seuil_alerte = seuil_alerte
        self.seuil_urgence = seuil_urgence
        self.historique = []

    def lire_niveau(self) -> float:
        variation = random.uniform(-3, 8)  # Tends to fill up
        self.taux_remplissage = max(0, min(100, self.taux_remplissage + variation))
        self.historique.append((datetime.now().isoformat(), round(self.taux_remplissage, 1)))
        if len(self.historique) > 100:
            self.historique.pop(0)
        return round(self.taux_remplissage, 1)

    def detecter_urgence(self) -> bool:
        return self.taux_remplissage >= self.seuil_urgence

    def detecter_alerte(self) -> bool:
        return self.taux_remplissage >= self.seuil_alerte

    def estimer_taux_remplissage(self, heures: int) -> float:
        if len(self.historique) < 2:
            return self.taux_remplissage + heures * 2.5
        # Simple linear regression on last points
        n = min(10, len(self.historique))
        vals = [h[1] for h in self.historique[-n:]]
        trend = (vals[-1] - vals[0]) / max(n-1, 1)
        predicted = self.taux_remplissage + trend * heures * 4
        return round(max(0, min(100, predicted)), 1)

    def to_dict(self):
        return {
            "point_id": self.point_id,
            "taux_remplissage": round(self.taux_remplissage, 1),
            "seuil_alerte": self.seuil_alerte,
            "seuil_urgence": self.seuil_urgence,
            "est_urgence": self.detecter_urgence(),
            "est_alerte": self.detecter_alerte(),
            "historique": self.historique[-10:]
        }
