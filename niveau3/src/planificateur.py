from datetime import datetime, timedelta
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))


class CreneauHoraire:
    def __init__(self, id_creneau, debut, fin, jour, cout_congestion=1.0):
        self.id             = id_creneau
        self.debut          = datetime.strptime(debut, "%H:%M")
        self.fin            = datetime.strptime(fin,   "%H:%M")
        self.jour           = jour
        self.cout_congestion = cout_congestion

    def duree(self):
        return (self.fin - self.debut).seconds / 3600

    def chevauche(self, autre):
        return not (self.fin <= autre.debut or self.debut >= autre.fin)

    def to_dict(self):
        return {
            'id':              self.id,
            'debut':           self.debut.strftime("%H:%M"),
            'fin':             self.fin.strftime("%H:%M"),
            'jour':            self.jour,
            'cout_congestion': self.cout_congestion,
            'duree':           self.duree()
        }


class ContrainteTemporelle:
    def __init__(self):
        self.fenetres_zone = {}   # {zone_id: (debut_str, fin_str)}
        self.pauses_camion = {}   # {camion_id: [(debut_str, duree_h)]}
        self.congestion    = {}   # {(zone_id, creneau_id): niveau}

    def est_realisable(self, camion_id, zone_id, creneau):
        if zone_id in self.fenetres_zone:
            deb_z = datetime.strptime(self.fenetres_zone[zone_id][0], "%H:%M")
            fin_z = datetime.strptime(self.fenetres_zone[zone_id][1], "%H:%M")
            if creneau.debut < deb_z or creneau.fin > fin_z:
                return False
        return True

    def calculer_penalite(self, camion_id, zone_id, creneau_id):
        return self.congestion.get((zone_id, creneau_id), 1.0)


class PlanificateurTriparti:
    def __init__(self, affectateur, creneaux, contraintes):
        self.affectateur = affectateur
        self.creneaux    = {c.id: c for c in creneaux}
        self.contraintes = contraintes

    def generer_plan_optimal(self, horizon_jours=7):
        """
        CORRECTION BUG 2 :
        Avant : si affectation vide → plan entièrement vide.
        Après :
          1. Si affectation normale → plan normal.
          2. Si affectation vide → plan de secours qui affecte
             chaque zone au premier camion compatible.
          3. Si aucun créneau pour un jour → utiliser n'importe
             quel créneau disponible (fallback robuste).
        """
        affectation = self.affectateur.affectation_gloutonne()

        # ── CORRECTION : vérifier si l'affectation est vide ─────────
        total_zones = sum(len(v) for v in affectation.values())

        if total_zones == 0:
            # Plan de secours : affecter chaque zone au premier
            # camion qui y a accès, sans contrainte de capacité
            affectation = self._affectation_secours()

        jours = ['lundi', 'mardi', 'mercredi', 'jeudi',
                 'vendredi', 'samedi', 'dimanche']
        plan  = {j: [] for j in jours[:horizon_jours]}

        # ── CORRECTION : fallback créneau robuste ───────────────────
        # Tous les créneaux disponibles (toutes journées confondues)
        tous_creneaux = list(self.creneaux.values())

        for cid, zone_ids in affectation.items():
            for i, zid in enumerate(zone_ids):
                jour = jours[i % min(horizon_jours, 7)]

                # Chercher créneau du bon jour
                creneaux_jour = [
                    c for c in tous_creneaux
                    if c.jour == jour and
                    self.contraintes.est_realisable(cid, zid, c)
                ]

                # CORRECTION : si aucun créneau ce jour-là,
                # prendre n'importe quel créneau disponible
                if not creneaux_jour:
                    creneaux_jour = [
                        c for c in tous_creneaux
                        if self.contraintes.est_realisable(cid, zid, c)
                    ]

                # CORRECTION : dernier recours — prendre le premier
                # créneau existant sans vérifier les contraintes
                if not creneaux_jour and tous_creneaux:
                    creneaux_jour = [tous_creneaux[0]]

                if not creneaux_jour:
                    continue  # vraiment aucun créneau défini du tout

                # Priorite haute : creneau le plus tot (matin)
                # Priorite normale : creneau le moins congestionne
                zone    = self.affectateur.zones.get(zid)
                camion  = self.affectateur.camions.get(cid)

                if zone and zone.priorite == 'haute':
                    creneau = min(creneaux_jour, key=lambda c: c.debut)
                else:
                    creneau = min(creneaux_jour, key=lambda c: c.cout_congestion)

                import math as _math
                vol  = zone.volume_estime if zone else 0
                cap  = camion.capacite if camion else 1
                nb_v = max(1, _math.ceil(vol / max(1, cap))) if vol > 0 else 1
                urgent = zone.priorite == 'haute' if zone else False

                plan[jour].append({
                    'camion_id':     cid,
                    'zone_id':       zid,
                    'creneau':       creneau.to_dict(),
                    'taches':        [
                        {'point_id': p, 'ordre': j + 1}
                        for j, p in enumerate(zone.points if zone else [])
                    ],
                    'duree_totale':  int(creneau.duree() * 60),
                    'retard_estime': 0,
                    'urgent':        urgent,
                    'volume_zone':   round(vol, 1),
                    'capacite_camion': cap,
                    'nb_voyages':    nb_v
                })

        return plan

    def _affectation_secours(self):
        """
        Plan de secours quand l'affectation gloutonne retourne vide.
        Distribue chaque zone au premier camion accessible,
        sans contrainte de capacité (le camion fera plusieurs voyages).
        """
        affectation = {cid: [] for cid in self.affectateur.camions}

        for zone in self.affectateur.zones.values():
            for cid, camion in self.affectateur.camions.items():
                accessible = (
                    not camion.zones_accessibles or
                    zone.id in camion.zones_accessibles
                )
                if accessible:
                    affectation[cid].append(zone.id)
                    break  # une zone = un camion

        return affectation

    def evaluer_plan(self, plan):
        """Calcule les indicateurs reels a partir du plan genere."""
        import math as _math
        total_taches = sum(len(v) for v in plan.values())
        nb_camions   = len(self.affectateur.camions)
        nb_zones     = len(self.affectateur.zones)
        nb_jours     = len([j for j, v in plan.items() if v])

        # Taux d occupation : taches planifiees / max possible
        max_possible  = nb_camions * nb_jours
        taux_occ      = min(100, round(total_taches / max(1, max_possible) * 100, 1))

        # Respect horaires : % de taches avec creneau du bon jour
        taches_bon_jour = 0
        for jour, entrees in plan.items():
            for e in entrees:
                cr = e.get('creneau', {})
                if cr.get('jour') == jour:
                    taches_bon_jour += 1
        respect = round(taches_bon_jour / max(1, total_taches) * 100, 1)

        # Congestion moyenne reelle depuis les creneaux utilises
        congestions = []
        for entrees in plan.values():
            for e in entrees:
                cr = e.get('creneau', {})
                congestions.append(cr.get('cout_congestion', 1.0))
        cong_moy = round(sum(congestions) / max(1, len(congestions)), 2)

        # Retard moyen : zones haute priorite planifiees apres 10h = retard
        retards = []
        for entrees in plan.values():
            for e in entrees:
                if e.get('urgent'):
                    cr = e.get('creneau', {})
                    debut = cr.get('debut', '08:00')
                    heure = int(debut.split(':')[0])
                    retard = max(0, (heure - 8) * 15)  # 15 min par heure apres 8h
                    retards.append(retard)
        retard_moy = round(sum(retards) / max(1, len(retards)), 1) if retards else 0.0

        return {
            'taux_occupation':    taux_occ,
            'respect_horaires':   respect,
            'congestion_moyenne': cong_moy,
            'retard_moyen':       retard_moy
        }
