class Zone:
    def __init__(self, id_zone: int, points: list, volume_estime: float,
                 centre_lat: float, centre_lon: float, nom: str = "",
                 frequence: str = "quotidien", priorite: str = "normale",
                 polygon: list = None):
        self.id = id_zone
        self.points = points
        self.volume_estime = volume_estime
        self.centre_lat = centre_lat
        self.centre_lon = centre_lon
        self.nom = nom
        self.frequence = frequence
        self.priorite = priorite
        self.polygon = polygon or []  # list of [lat, lon]
        self.camion_affecte = None

    def to_dict(self):
        return {
            "id": self.id, "points": self.points, "volume_estime": self.volume_estime,
            "centre_lat": self.centre_lat, "centre_lon": self.centre_lon,
            "nom": self.nom, "frequence": self.frequence, "priorite": self.priorite,
            "polygon": self.polygon, "camion_affecte": self.camion_affecte
        }

    @staticmethod
    def from_dict(d):
        z = Zone(d["id"], d.get("points", []), d.get("volume_estime", 1000),
                 d.get("centre_lat", 30.4202), d.get("centre_lon", -9.5982),
                 d.get("nom", ""), d.get("frequence", "quotidien"),
                 d.get("priorite", "normale"), d.get("polygon", []))
        z.camion_affecte = d.get("camion_affecte")
        return z
