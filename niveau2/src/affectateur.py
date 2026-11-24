import sys, os, math
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))
from commun.outils_math import ecart_type


class Camion:
    def __init__(self, id_camion, capacite, cout_fixe, zones_accessibles=None,
                 position_x=0, position_y=0, couleur="#3498db"):
        self.id = id_camion
        self.capacite = capacite
        self.cout_fixe = cout_fixe
        self.zones_accessibles = zones_accessibles or []
        self.position_x = position_x
        self.position_y = position_y
        self.couleur = couleur
        self.charge_actuelle = 0.0

    def to_dict(self):
        return {'id': self.id, 'capacite': self.capacite, 'cout_fixe': self.cout_fixe,
                'zones_accessibles': self.zones_accessibles,
                'position_x': self.position_x, 'position_y': self.position_y,
                'couleur': self.couleur, 'charge_actuelle': self.charge_actuelle}

    @classmethod
    def from_dict(cls, d):
        pos = d.get('position_initial', {})
        return cls(d['id'], d['capacite'], d['cout_fixe'],
                   d.get('zones_accessibles', []),
                   pos.get('x', 0), pos.get('y', 0),
                   d.get('couleur', '#3498db'))


class Zone:
    def __init__(self, id_zone, points, volume_estime, centre_x, centre_y,
                 nom="", frequence="quotidien", priorite="normale"):
        self.id = id_zone
        self.points = points
        self.volume_estime = volume_estime
        self.centre_x = centre_x
        self.centre_y = centre_y
        self.nom = nom
        self.frequence = frequence
        self.priorite = priorite

    def to_dict(self):
        return {'id': self.id, 'points': self.points,
                'volume_estime': self.volume_estime,
                'centre_x': self.centre_x, 'centre_y': self.centre_y,
                'nom': self.nom, 'frequence': self.frequence,
                'priorite': self.priorite}

    @classmethod
    def from_dict(cls, d):
        centre = d.get('centre', {})
        return cls(d['id'], d.get('points', []),
                   d.get('volume_moyen', d.get('volume_estime', 0)),
                   centre.get('x', 0), centre.get('y', 0),
                   d.get('nom', f"Zone {d['id']}"),
                   d.get('frequence_collecte', 'quotidien'),
                   d.get('priorite', 'normale'))


class AffectateurBiparti:
    def __init__(self, camions, zones, graphe=None, demandes=None):
        self.camions  = {c.id: c for c in camions}
        self.zones    = {z.id: z for z in zones}
        self.graphe   = graphe
        # demandes_points : {point_id: kg}  — optionnel, pour calcul précis
        self.demandes = demandes or {}

    def _volume_reel_zone(self, zone):
        """
        CORRECTION BUG 1 :
        Volume réel = somme des demandes des points de la zone.
        Si les demandes ne sont pas disponibles, on utilise volume_estime
        comme CHARGE PAR VOYAGE (pas volume total).

        La capacité du camion représente ce qu'il peut charger EN UN SEUL
        VOYAGE. On compare donc la charge d'un voyage, pas le total zone.
        On estime nb_voyages = ceil(volume_zone / capacite_camion).
        Ce qui compte pour l'affectation : le camion PEUT-IL faire
        au moins 1 voyage dans cette zone ? → volume_par_voyage <= capacite
        """
        if self.demandes:
            # Utiliser les vraies demandes point par point
            total = sum(self.demandes.get(pid, 0) for pid in zone.points)
            return total
        else:
            return zone.volume_estime

    def _charge_par_voyage(self, zone, capacite_camion):
        """
        Charge par voyage = min(volume_zone, capacite_camion).
        Un camion fait ceil(volume/capacite) voyages si nécessaire.
        Pour l'affectation on vérifie juste la faisabilité (>0 points).
        """
        vol = self._volume_reel_zone(zone)
        nb_points = max(1, len(zone.points))
        # Charge moyenne par point
        charge_par_point = vol / nb_points
        # Nombre de points qu'on peut charger en 1 voyage
        pts_par_voyage = max(1, int(capacite_camion / charge_par_point))
        return min(vol, pts_par_voyage * charge_par_point)

    def calculer_cout_affectation(self, camion_id, zone_id):
        camion = self.camions.get(camion_id)
        zone   = self.zones.get(zone_id)
        if not camion or not zone:
            return float('inf')
        if camion.zones_accessibles and zone_id not in camion.zones_accessibles:
            return float('inf')
        dist = math.sqrt((camion.position_x - zone.centre_x) ** 2 +
                         (camion.position_y - zone.centre_y) ** 2)
        # Bonus capacite : un camion plus grand est favorise pour les zones lourdes
        capacite_max = max(c.capacite for c in self.camions.values()) or 1
        bonus_capacite = 1.0 - 0.3 * (camion.capacite / capacite_max)
        cout_base = (camion.cout_fixe + dist * 10 + zone.volume_estime * 0.05) * bonus_capacite
        # Priorite haute : on choisit le camion avec la PLUS GRANDE capacite disponible
        # en penalisant fortement les petits camions sur les zones critiques
        if zone.priorite == 'haute':
            # Penalite inverse de capacite : petit camion = score eleve = evite
            penalite_capacite = (capacite_max / max(1, camion.capacite)) * 0.3
            return cout_base * (1 + penalite_capacite)
        elif zone.priorite == 'basse':
            # Zone basse priorite : on prefere les camions moins charges
            return cout_base * 1.5
        else:
            return cout_base

    def affectation_gloutonne(self):
        """
        Affectation gloutonne tenant compte de la capacité du camion.
        Un camion peut couvrir une zone s'il peut faire au moins 1 voyage
        (volume par point <= capacité). On favorise le camion le moins chargé
        et le moins coûteux. Si aucun camion ne peut couvrir une zone seul,
        on assigne quand même le meilleur disponible (multi-voyage).
        """
        import math as _math
        affectation = {cid: [] for cid in self.camions}
        charges     = {cid: 0.0 for cid in self.camions}

        # Trier zones par priorité haute d'abord, puis par volume décroissant
        zones_triees = sorted(
            self.zones.values(),
            key=lambda z: (0 if z.priorite == 'haute' else 1, -z.volume_estime)
        )

        for zone in zones_triees:
            meilleur_camion = None
            meilleur_cout   = float('inf')
            meilleur_score  = float('inf')

            for cid, camion in self.camions.items():
                # Vérifier accessibilité de zone
                if camion.zones_accessibles and zone.id not in camion.zones_accessibles:
                    continue  # zone interdite pour ce camion

                # Score combiné : cout + pénalité de surcharge
                nb_voyages = max(1, _math.ceil(zone.volume_estime / max(1, camion.capacite)))
                cout = self.calculer_cout_affectation(cid, zone.id) * nb_voyages
                # Favoriser les camions les moins chargés par rapport à leur capacité
                taux_charge = charges[cid] / max(1, camion.capacite)
                score = cout * (1 + taux_charge)

                if score < meilleur_score:
                    meilleur_score  = score
                    meilleur_cout   = cout
                    meilleur_camion = cid

            if meilleur_camion is not None:
                affectation[meilleur_camion].append(zone.id)
                charges[meilleur_camion] += zone.volume_estime

        # Garantir qu'aucun camion ne reste vide si une zone lui est accessible
        # On partage les zones les plus chargées entre camions vides compatibles
        camions_vides = [cid for cid, zids in affectation.items() if not zids]
        for cid in camions_vides:
            camion = self.camions[cid]
            # Chercher une zone accessible à ce camion qui est déjà affectée
            meilleure_zone = None
            meilleur_donneur = None
            for donneur_id, zone_ids in affectation.items():
                if donneur_id == cid or len(zone_ids) <= 1:
                    continue
                for zid in zone_ids:
                    accessible = (not camion.zones_accessibles or
                                  zid in camion.zones_accessibles)
                    if accessible:
                        meilleure_zone  = zid
                        meilleur_donneur = donneur_id
                        break
                if meilleure_zone:
                    break
            if meilleure_zone and meilleur_donneur:
                affectation[meilleur_donneur].remove(meilleure_zone)
                affectation[cid].append(meilleure_zone)

        return affectation

    def verifier_contraintes(self, affectation):
        for cid, zone_ids in affectation.items():
            camion = self.camions[cid]
            for zid in zone_ids:
                if camion.zones_accessibles and zid not in camion.zones_accessibles:
                    return False
        return True

    def equilibrage_charges(self, affectation):
        """Equilibrage : deplacer zones entre camions pour reduire l'ecart,
        en respectant la capacite de chaque camion (multi-voyage inclus)."""
        import math as _math
        charges = {
            cid: sum(self.zones[zid].volume_estime
                     for zid in zones if zid in self.zones)
            for cid, zones in affectation.items()
        }
        moyenne = sum(charges.values()) / max(1, len(charges))

        for _ in range(20):
            max_c = max(charges, key=charges.get)
            min_c = min(charges, key=charges.get)
            if charges[max_c] - charges[min_c] < moyenne * 0.15:
                break
            for zid in list(affectation[max_c]):
                z = self.zones.get(zid)
                if not z:
                    continue
                camion_min = self.camions[min_c]
                accessible = (not camion_min.zones_accessibles or
                              zid in camion_min.zones_accessibles)
                if accessible:
                    nouvelle_charge_min = charges[min_c] + z.volume_estime
                    nb_voyages = _math.ceil(nouvelle_charge_min / max(1, camion_min.capacite))
                    if nb_voyages <= 5:
                        affectation[max_c].remove(zid)
                        affectation[min_c].append(zid)
                        charges[max_c] -= z.volume_estime
                        charges[min_c] += z.volume_estime
                        break

        return affectation

    def generer_rapport(self, affectation):
        resultats          = []
        all_charges        = []
        zones_non_affectees = list(self.zones.keys())

        for cid, zone_ids in affectation.items():
            camion  = self.camions[cid]
            charge  = sum(self.zones[zid].volume_estime
                          for zid in zone_ids if zid in self.zones)
            cout    = sum(self.calculer_cout_affectation(cid, zid)
                          for zid in zone_ids)
            all_charges.append(charge)

            for zid in zone_ids:
                if zid in zones_non_affectees:
                    zones_non_affectees.remove(zid)

            # Calcul nb_voyages basé sur capacité réelle
            nb_voyages = 1
            if camion.capacite > 0 and charge > 0:
                import math as _math
                nb_voyages = _math.ceil(charge / camion.capacite)

            resultats.append({
                'camion_id':              cid,
                'zones_affectees':        zone_ids,
                'charge_totale':          round(charge, 2),
                'cout_estime':            round(cout, 2),
                'nb_voyages':             nb_voyages,
                'capacite_camion':        camion.capacite,
                'pourcentage_utilisation': round(
                    min(100, charge / max(1, camion.capacite) * 100), 1
                )
            })

        return {
            'affectation': resultats,
            'statistiques': {
                'nombre_camions_utilises': sum(
                    1 for r in resultats if r['zones_affectees']
                ),
                'charge_moyenne':    round(
                    sum(all_charges) / max(1, len(all_charges)), 2
                ),
                'ecart_type_charge': round(ecart_type(all_charges), 2),
                'zones_non_affectees': zones_non_affectees
            }
        }
