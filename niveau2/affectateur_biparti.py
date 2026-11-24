"""
Niveau 2 : Affectation Camion ↔ Zone
Graphe biparti avec algorithme glouton et équilibrage des charges
"""
import sys, os, math, statistics
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from commun.models import Camion, Zone


class AffectateurBiparti:
    def __init__(self, camions: list, zones: list, graphe=None):
        self.camions = {c.id: c for c in camions}
        self.zones = {z.id: z for z in zones}
        self.graphe = graphe

    def distance_camion_zone(self, camion: Camion, zone: Zone) -> float:
        return math.sqrt((camion.position_x - zone.centre_x)**2 +
                         (camion.position_y - zone.centre_y)**2)

    def calculer_cout_affectation(self, camion_id: int, zone_id: int) -> float:
        camion = self.camions[camion_id]
        zone = self.zones[zone_id]
        dist = self.distance_camion_zone(camion, zone)
        penalite_priorite = {"haute": 0.5, "normale": 1.0, "basse": 1.5}
        pen = penalite_priorite.get(zone.priorite, 1.0)
        return round((dist * 10 + camion.cout_fixe * 0.1) * pen, 2)

    def affectation_gloutonne(self) -> dict:
        """Affectation gloutonne basée sur coût minimal"""
        affectation = {cid: [] for cid in self.camions}
        charge = {cid: 0.0 for cid in self.camions}
        zones_triees = sorted(self.zones.values(),
                               key=lambda z: (z.priorite != "haute", z.id))

        for zone in zones_triees:
            meilleur_camion = None
            meilleur_cout = float('inf')
            for camion_id, camion in self.camions.items():
                if not camion.disponible:
                    continue
                if zone.id not in camion.zones_accessibles and camion.zones_accessibles:
                    continue
                if charge[camion_id] + zone.volume_estime > camion.capacite:
                    continue
                cout = self.calculer_cout_affectation(camion_id, zone.id)
                if cout < meilleur_cout:
                    meilleur_cout = cout
                    meilleur_camion = camion_id

            if meilleur_camion is not None:
                affectation[meilleur_camion].append(zone.id)
                charge[meilleur_camion] += zone.volume_estime

        return affectation

    def verifier_contraintes(self, affectation: dict) -> dict:
        resultats = {"valide": True, "erreurs": []}
        for camion_id, zone_ids in affectation.items():
            camion = self.camions[camion_id]
            charge_totale = sum(self.zones[zid].volume_estime for zid in zone_ids
                                if zid in self.zones)
            if charge_totale > camion.capacite:
                resultats["valide"] = False
                resultats["erreurs"].append(
                    f"Camion {camion_id} dépasse capacité: {charge_totale} > {camion.capacite}")
        return resultats

    def equilibrage_charges(self, affectation: dict) -> dict:
        """Rééquilibre les charges entre camions"""
        charges = {}
        for cid, zone_ids in affectation.items():
            charges[cid] = sum(self.zones[zid].volume_estime
                               for zid in zone_ids if zid in self.zones)

        for _ in range(20):
            cid_max = max(charges, key=lambda k: charges[k])
            cid_min = min(charges, key=lambda k: charges[k])
            if charges[cid_max] - charges[cid_min] < 200:
                break
            # Transférer une zone du plus chargé au moins chargé
            for zid in list(affectation[cid_max]):
                z = self.zones[zid]
                camion_min = self.camions[cid_min]
                if (charges[cid_min] + z.volume_estime <= camion_min.capacite and
                        (not camion_min.zones_accessibles or
                         zid in camion_min.zones_accessibles)):
                    affectation[cid_max].remove(zid)
                    affectation[cid_min].append(zid)
                    charges[cid_max] -= z.volume_estime
                    charges[cid_min] += z.volume_estime
                    break
        return affectation

    def generer_rapport(self, affectation: dict) -> dict:
        result = []
        charges = []
        for cid, zone_ids in affectation.items():
            camion = self.camions[cid]
            charge = sum(self.zones[zid].volume_estime
                         for zid in zone_ids if zid in self.zones)
            cout = sum(self.calculer_cout_affectation(cid, zid)
                       for zid in zone_ids if zid in self.zones)
            charges.append(charge)
            result.append({
                "camion_id": cid,
                "plaque": camion.plaque,
                "zones_affectees": zone_ids,
                "charge_totale": charge,
                "capacite": camion.capacite,
                "cout_estime": round(cout, 2),
                "pourcentage_utilisation": round(charge / camion.capacite * 100, 1)
                if camion.capacite else 0
            })

        zones_affectees = [z for ids in affectation.values() for z in ids]
        zones_non_affectees = [zid for zid in self.zones if zid not in zones_affectees]

        return {
            "affectation": result,
            "statistiques": {
                "nombre_camions_utilises": sum(1 for ids in affectation.values() if ids),
                "charge_moyenne": round(sum(charges) / len(charges), 1) if charges else 0,
                "ecart_type_charge": round(statistics.stdev(charges), 1) if len(charges) > 1 else 0,
                "zones_non_affectees": zones_non_affectees
            }
        }
