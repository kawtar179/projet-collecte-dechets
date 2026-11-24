class Tournee:
    def __init__(self, camion_id: int, points: list = None, capacite_max: float = 5000):
        self.camion_id = camion_id
        self.points = points or []
        self.heure_depart = None
        self.heure_retour = None
        self.capacite_max = capacite_max
        self.charge_totale = 0.0

    def ajouter_point(self, point_id: int, position: int = -1) -> bool:
        if position == -1:
            self.points.append(point_id)
        else:
            self.points.insert(position, point_id)
        return True

    def calculer_distance(self, graphe) -> float:
        if len(self.points) < 2:
            return 0.0
        total = 0.0
        for i in range(len(self.points) - 1):
            d, _ = graphe.plus_court_chemin(self.points[i], self.points[i+1])
            total += d
        return round(total, 2)

    def calculer_duree(self, temps_service: dict = None, vitesse: float = 30.0) -> float:
        temps_service = temps_service or {}
        total_service = sum(temps_service.get(p, 5) for p in self.points)
        return total_service  # in minutes

    def verifier_faisabilite(self, contraintes: dict = None) -> bool:
        return len(self.points) > 0

    def to_dict(self, graphe=None):
        dist = self.calculer_distance(graphe) if graphe else 0
        return {
            "camion_id": self.camion_id,
            "points_ordre": self.points,
            "distance_totale": dist,
            "nombre_points": len(self.points),
            "charge_totale": self.charge_totale,
            "heure_depart": self.heure_depart,
            "heure_retour": self.heure_retour
        }
