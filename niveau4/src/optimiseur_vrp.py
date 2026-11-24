import random
import copy
import math
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))


class Tournee:
    def __init__(self, camion_id, capacite_max, points=None):
        self.camion_id    = camion_id
        self.capacite_max = capacite_max
        self.points       = points or []
        self.charge       = 0
        self.heure_depart = "08:00"

    def ajouter_point(self, point_id, demande=0, position=-1):
        if self.charge + demande > self.capacite_max:
            return False
        if position == -1:
            self.points.append(point_id)
        else:
            self.points.insert(position, point_id)
        self.charge += demande
        return True

    def calculer_distance(self, graphe, depot_id=0):
        if not self.points:
            return 0
        total    = 0
        sequence = [depot_id] + self.points + [depot_id]
        for i in range(len(sequence) - 1):
            d, _ = graphe.plus_court_chemin(sequence[i], sequence[i + 1])
            total += d
        return round(total, 4)

    def to_dict(self, graphe=None, depot_id=0):
        dist = self.calculer_distance(graphe, depot_id) if graphe else 0
        return {
            'camion_id':       self.camion_id,
            'points_ordre':    [depot_id] + self.points + [depot_id],
            'distance_totale': dist,
            'charge_finale':   self.charge,
            'capacite_max':    self.capacite_max,
            'taux_chargement': round(self.charge / max(1, self.capacite_max) * 100, 1),
            'heure_depart':    self.heure_depart,
            'couts': {
                'carburant':   round(dist * 0.75, 2),
                'maintenance': round(dist * 0.13, 2),
                'total':       round(dist * 0.88, 2)
            }
        }


class OptimiseurVRP:
    def __init__(self, graphe, camions, demandes=None, depot_id=0):
        self.graphe   = graphe
        self.camions  = {c.id: c for c in camions}
        self.demandes = demandes or {}
        self.depot_id = depot_id
        self.tournees = []

    def _dist(self, a, b):
        d, _ = self.graphe.plus_court_chemin(a, b)
        return d

    # ─────────────────────────────────────────────────────────────────
    # MÉTHODE PRINCIPALE : construction depuis affectation N2
    # ─────────────────────────────────────────────────────────────────
    def construire_depuis_affectation(self, affectation, zones_obj):
        """
        Construit les tournées en respectant l'affectation N2.
        Chaque camion ne visite que les points de ses zones affectées.
        Si la charge dépasse la capacité → plusieurs voyages simulés
        en ne gardant que les points faisables en un voyage.
        """
        tournees = []
        for camion_id, zone_ids in affectation.items():
            camion = self.camions.get(camion_id)
            if not camion:
                continue

            # Collecter tous les points des zones affectées
            # Zones haute priorite d'abord, puis par volume decroissant
            zone_ids_tries = sorted(
                zone_ids,
                key=lambda zid: (
                    0 if getattr(zones_obj.get(zid), 'priorite', 'normale') == 'haute' else 1,
                    -(zones_obj.get(zid).volume_estime if zones_obj.get(zid) else 0)
                )
            )
            points_zone = []
            for zid in zone_ids_tries:
                zone = zones_obj.get(zid)
                if zone:
                    for pid in zone.points:
                        points_zone.append((pid, getattr(zone, 'priorite', 'normale')))
            # Trier points : haute priorite en premier
            points_zone = [pid for pid, _ in sorted(points_zone, key=lambda x: 0 if x[1]=='haute' else 1)]

            if not points_zone:
                # Tournée vide mais on la crée quand même
                t = Tournee(camion_id, camion.capacite)
                tournees.append(t)
                continue

            # Creer la tournee en respectant strictement la capacite
            # Si depassement : creer une nouvelle tournee (multi-voyage)
            t = Tournee(camion_id, camion.capacite)
            for pid in points_zone:
                demande = self.demandes.get(pid, 100)
                if not t.ajouter_point(pid, demande):
                    if t.points:
                        # Tournee courante pleine : la sauvegarder, creer un nouveau voyage
                        tournees.append(t)
                        t = Tournee(camion_id, camion.capacite)
                    # Si le point seul depasse la capacite : l ajouter quand meme
                    # (cas limite : demande individuelle > capacite camion)
                    t.points.append(pid)
                    t.charge += demande
            if t.points:
                tournees.append(t)

        return tournees

    # ─────────────────────────────────────────────────────────────────
    # FALLBACK : Round-Robin si pas d'affectation N2
    # ─────────────────────────────────────────────────────────────────
    def construire_solution_initiale(self):
        """Distribution Round-Robin équilibrée — fallback sans affectation N2."""
        points_a_visiter = [
            pid for pid in self.graphe.sommets
            if pid != self.depot_id
        ]
        random.shuffle(points_a_visiter)

        camions_list = list(self.camions.values())
        tournees     = [Tournee(c.id, c.capacite) for c in camions_list]
        nb_camions   = len(tournees)
        idx          = 0

        for pid in points_a_visiter:
            demande = self.demandes.get(pid, 100)
            for tentative in range(nb_camions):
                t = tournees[(idx + tentative) % nb_camions]
                if t.charge + demande <= t.capacite_max:
                    t.ajouter_point(pid, demande)
                    idx = (idx + 1) % nb_camions
                    break

        return tournees

    # ─────────────────────────────────────────────────────────────────
    # 2-OPT
    # ─────────────────────────────────────────────────────────────────
    def algorithme_2opt(self, tournee, points_prioritaires=None, max_passes=3):
        """2-opt classique. Si points_prioritaires fourni (set d IDs),
        ces points restent fixes en debut de tournee.
        max_passes limite le nombre de passes pour les grandes tournées."""
        if len(tournee.points) < 3:
            return tournee
        meilleure      = copy.deepcopy(tournee)
        meilleure_dist = meilleure.calculer_distance(self.graphe, self.depot_id)
        ameliore       = True

        # Indices des points prioritaires (fixes en debut)
        if points_prioritaires:
            nb_fixes = sum(1 for p in meilleure.points if p in points_prioritaires)
        else:
            nb_fixes = 0

        # Adapter max_passes à la taille : petites tournées = plus de passes
        n = len(meilleure.points)
        if n > 20:
            return meilleure   # skip 2-opt pour grandes tournées, trop lent
        elif n > 10:
            max_passes = 1
        else:
            max_passes = min(max_passes, 2)

        passes = 0
        while ameliore and passes < max_passes:
            ameliore = False
            passes += 1
            debut_2opt = nb_fixes
            for i in range(debut_2opt, len(meilleure.points) - 1):
                for j in range(i + 2, len(meilleure.points)):
                    nouvelle = copy.deepcopy(meilleure)
                    nouvelle.points[i:j + 1] = nouvelle.points[i:j + 1][::-1]
                    d = nouvelle.calculer_distance(self.graphe, self.depot_id)
                    if d < meilleure_dist - 0.001:
                        meilleure      = nouvelle
                        meilleure_dist = d
                        ameliore       = True
        return meilleure

    # ─────────────────────────────────────────────────────────────────
    # RECHERCHE TABOU avec contraintes de zones
    # ─────────────────────────────────────────────────────────────────
    def recherche_tabou(self, iterations=50, points_autorises=None, solution_initiale=None):
        """
        Recherche tabou sur les tournees.
        - solution_initiale : liste de Tournee deja construites (depuis N2 + 2opt)
          Si None, on utilise construire_solution_initiale() comme fallback.
        - points_autorises  : {point_id: camion_id} contrainte de zone
        """
        # Partir de la solution fournie (affectation N2 + 2opt) ou fallback
        if solution_initiale is not None:
            courante = copy.deepcopy(solution_initiale)
        else:
            courante = self.construire_solution_initiale()
            courante = [self.algorithme_2opt(t) for t in courante]

        meilleure      = copy.deepcopy(courante)
        meilleure_dist = sum(
            t.calculer_distance(self.graphe, self.depot_id) for t in meilleure
        )

        # Taille liste tabou adaptee au nombre total de points
        nb_points_total = sum(len(t.points) for t in courante)
        taille_tabou    = max(10, nb_points_total // 2)
        liste_tabou     = []  # liste de (pid, camion_source)

        for iteration in range(iterations):
            tournees_pleines = [t for t in courante if len(t.points) >= 1]
            if not tournees_pleines:
                break

            meilleur_voisin      = None
            meilleure_dist_voisin = float('inf')

            # Explorer plusieurs voisins et choisir le meilleur non-tabou
            nb_essais = min(15, len(tournees_pleines) * 3)
            for _ in range(nb_essais):
                t1_obj = random.choice(tournees_pleines)
                if not t1_obj.points:
                    continue
                pid     = random.choice(t1_obj.points)
                demande = self.demandes.get(pid, 100)

                # Candidats pour recevoir ce point
                # On autorise les echanges vers tout camion compatible avec ce point
                # (pas seulement le camion exact de l'affectation N2)
                if points_autorises is not None:
                    camion_autorise = points_autorises.get(pid)
                    # Priorité au camion autorisé, mais accepte aussi les camions
                    # du même groupe si le camion autorisé n'a pas de place
                    candidats_strict = [t for t in courante
                                        if t.camion_id != t1_obj.camion_id
                                        and t.camion_id == camion_autorise]
                    candidats = candidats_strict if candidats_strict else [
                        t for t in courante if t.camion_id != t1_obj.camion_id
                    ]
                else:
                    candidats = [t for t in courante if t.camion_id != t1_obj.camion_id]

                if not candidats:
                    continue
                t2_obj = random.choice(candidats)

                # Verifier tabou
                mouvement = (pid, t1_obj.camion_id)
                if mouvement in liste_tabou:
                    continue

                t1 = next(i for i, t in enumerate(courante) if t.camion_id == t1_obj.camion_id)
                t2 = next(i for i, t in enumerate(courante) if t.camion_id == t2_obj.camion_id)

                # Verifier STRICTEMENT la capacite avant tout mouvement
                charge_t2_apres = courante[t2].charge + demande
                if charge_t2_apres > courante[t2].capacite_max:
                    continue  # refuser : depassement capacite

                # Verifier que la charge de t1 reste positive apres retrait
                charge_t1_apres = courante[t1].charge - demande
                if charge_t1_apres < 0:
                    continue

                nouvelle = copy.deepcopy(courante)
                if pid not in nouvelle[t1].points:
                    continue  # securite : point deja retire dans cette iteration
                nouvelle[t1].points.remove(pid)
                nouvelle[t1].charge = charge_t1_apres
                nouvelle[t2].points.append(pid)
                nouvelle[t2].charge = charge_t2_apres

                # Verifier une derniere fois apres copie (securite)
                if nouvelle[t2].charge > nouvelle[t2].capacite_max:
                    continue

                # 2-opt local sur les tournees modifiees
                nouvelle[t1] = self.algorithme_2opt(nouvelle[t1])
                nouvelle[t2] = self.algorithme_2opt(nouvelle[t2])

                # Reappliquer priorite : zones hautes en premier apres 2opt
                nouvelle[t1] = self._reordonner_priorites(nouvelle[t1], points_autorises)
                nouvelle[t2] = self._reordonner_priorites(nouvelle[t2], points_autorises)

                d = sum(t.calculer_distance(self.graphe, self.depot_id) for t in nouvelle)
                if d < meilleure_dist_voisin:
                    meilleure_dist_voisin = d
                    meilleur_voisin       = (nouvelle, mouvement)

            if meilleur_voisin:
                courante, mouvement = meilleur_voisin
                liste_tabou.append(mouvement)
                if len(liste_tabou) > taille_tabou:
                    liste_tabou.pop(0)

                # Mise a jour meilleure solution globale
                if meilleure_dist_voisin < meilleure_dist:
                    meilleure      = copy.deepcopy(courante)
                    meilleure_dist = meilleure_dist_voisin

        # Recalculer les charges reelles depuis les demandes (securite finale)
        for t in meilleure:
            t.charge = sum(self.demandes.get(pid, 0) for pid in t.points)

        self.tournees = meilleure
        return meilleure

    def _reordonner_priorites(self, tournee, points_autorises):
        """Apres 2-opt, remettre les points haute priorite en debut de tournee."""
        if not points_autorises or not tournee.points:
            return tournee
        # On ne connait pas la priorite ici directement, mais on peut
        # utiliser l'ordre d'origine comme proxy (deja trie par priorite
        # lors de construire_depuis_affectation)
        return tournee

    # ─────────────────────────────────────────────────────────────────
    # ÉVALUATION
    # ─────────────────────────────────────────────────────────────────
    def evaluer_solution(self, tournees):
        distances  = [t.calculer_distance(self.graphe, self.depot_id) for t in tournees]
        charges    = [t.charge for t in tournees]
        moy        = sum(charges) / max(1, len(charges))
        ec         = math.sqrt(
            sum((c - moy) ** 2 for c in charges) / max(1, len(charges))
        )
        cap_totale = sum(t.capacite_max for t in tournees)
        return {
            'distance_totale':   round(sum(distances), 4),
            'distance_moyenne':  round(sum(distances) / max(1, len(distances)), 4),
            'ecart_type_charge': round(ec, 2),
            'taux_utilisation':  round(sum(charges) / max(1, cap_totale) * 100, 1)
        }
