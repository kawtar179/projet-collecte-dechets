import statistics

class AffectateurBiparti:
    def __init__(self, camions: list, zones: list, graphe=None):
        self.camions = camions
        self.zones = zones
        self.graphe = graphe

    def calculer_cout_affectation(self, camion_id: int, zone_id: int) -> float:
        camion = next((c for c in self.camions if c.id == camion_id), None)
        zone = next((z for z in self.zones if z.id == zone_id), None)
        if not camion or not zone:
            return float('inf')
        if not camion.peut_acceder_zone(zone_id):
            return float('inf')
        # Coût = cout_fixe * ratio_volume + pénalité priorité
        ratio = zone.volume_estime / camion.capacite if camion.capacite else 1
        penalite = 0
        if zone.priorite == "haute":
            penalite = -50  # bonus priorité haute
        elif zone.priorite == "basse":
            penalite = 50
        return round(camion.cout_fixe * ratio + penalite, 2)

    def affectation_gloutonne(self) -> dict:
        # Reset charges
        for c in self.camions:
            c.charge_actuelle = 0.0
        
        affectation = {c.id: [] for c in self.camions}
        # Trier zones par priorité (haute d'abord)
        prio_ordre = {"haute": 0, "normale": 1, "basse": 2}
        zones_triees = sorted(self.zones, key=lambda z: prio_ordre.get(z.priorite, 1))
        
        for zone in zones_triees:
            meilleur_camion = None
            meilleur_cout = float('inf')
            for camion in self.camions:
                if not camion.en_service:
                    continue
                if not camion.peut_acceder_zone(zone.id):
                    continue
                if camion.charge_actuelle + zone.volume_estime > camion.capacite:
                    continue
                cout = self.calculer_cout_affectation(camion.id, zone.id)
                if cout < meilleur_cout:
                    meilleur_cout = cout
                    meilleur_camion = camion
            if meilleur_camion:
                affectation[meilleur_camion.id].append(zone.id)
                meilleur_camion.charge_actuelle += zone.volume_estime
                zone.camion_affecte = meilleur_camion.id
        return affectation

    def verifier_contraintes(self, affectation: dict) -> dict:
        violations = []
        for camion_id, zone_ids in affectation.items():
            camion = next((c for c in self.camions if c.id == camion_id), None)
            if not camion:
                continue
            total = sum(z.volume_estime for z in self.zones if z.id in zone_ids)
            if total > camion.capacite:
                violations.append(f"Camion {camion_id}: capacité dépassée ({total}/{camion.capacite})")
            for zid in zone_ids:
                if not camion.peut_acceder_zone(zid):
                    violations.append(f"Camion {camion_id} ne peut pas accéder zone {zid}")
        return {"valide": len(violations) == 0, "violations": violations}

    def equilibrage_charges(self, affectation: dict) -> dict:
        # Simple rebalancing: move zones from most loaded to least loaded
        for _ in range(10):
            charges = {}
            for cid, zids in affectation.items():
                camion = next((c for c in self.camions if c.id == cid), None)
                if camion:
                    charges[cid] = sum(z.volume_estime for z in self.zones if z.id in zids)
            if not charges:
                break
            max_cid = max(charges, key=charges.get)
            min_cid = min(charges, key=charges.get)
            if charges[max_cid] - charges[min_cid] < 100:
                break
            # Try to move a zone
            camion_min = next((c for c in self.camions if c.id == min_cid), None)
            moved = False
            for zid in list(affectation[max_cid]):
                zone = next((z for z in self.zones if z.id == zid), None)
                if zone and camion_min and camion_min.peut_acceder_zone(zid):
                    new_charge = charges[min_cid] + zone.volume_estime
                    if new_charge <= camion_min.capacite:
                        affectation[max_cid].remove(zid)
                        affectation[min_cid].append(zid)
                        zone.camion_affecte = min_cid
                        moved = True
                        break
            if not moved:
                break
        return affectation

    def calculer_statistiques(self, affectation: dict) -> dict:
        charges = []
        for cid, zids in affectation.items():
            camion = next((c for c in self.camions if c.id == cid), None)
            if camion and zids:
                charge = sum(z.volume_estime for z in self.zones if z.id in zids)
                charges.append(charge)
        zones_affectees = [z for zids in affectation.values() for z in zids]
        zones_non_affectees = [z.id for z in self.zones if z.id not in zones_affectees]
        return {
            "nombre_camions_utilises": sum(1 for zids in affectation.values() if zids),
            "charge_moyenne": round(statistics.mean(charges), 1) if charges else 0,
            "ecart_type_charge": round(statistics.stdev(charges), 1) if len(charges) > 1 else 0,
            "zones_non_affectees": zones_non_affectees
        }
