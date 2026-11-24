#!/usr/bin/env python3
"""
Script de tests de performance - Collecte de déchets Agadir
Exécute les 3 scénarios prédéfinis et affiche les métriques complètes
incluant le tonnage transporté par kilomètre par camion.
"""

import json, time, sys, os, math
from datetime import datetime

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)

from niveau1.src.graphe_routier import GrapheRoutier, PointCollecte
from niveau2.src.affectateur import Camion, Zone, AffectateurBiparti
from niveau4.src.optimiseur_vrp import OptimiseurVRP, Tournee

SEP = "=" * 70

def charger_donnees(fichier):
    with open(fichier, 'r', encoding='utf-8') as f:
        d = json.load(f)
    for z in d.get('zones', []):
        if 'volume_estime' not in z:
            z['volume_estime'] = z.get('volume_moyen', 0)
    return d

def construire_graphe(data):
    g = GrapheRoutier()
    depot = data['depot']
    g.ajouter_sommet(PointCollecte(
        depot['id'], depot.get('x', 0), depot.get('y', 0),
        depot.get('nom', 'Dépôt'), depot.get('lat'), depot.get('lon')
    ))
    for p in data['points_collecte']:
        g.ajouter_sommet(PointCollecte.from_dict(p))
    g.construire_graphe_complet()
    return g

def calculer_distance_km(p1, p2):
    """Distance haversine en km entre deux points lat/lon."""
    R = 6371.0
    lat1, lon1 = math.radians(p1['lat']), math.radians(p1['lon'])
    lat2, lon2 = math.radians(p2['lat']), math.radians(p2['lon'])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2
    return R * 2 * math.asin(math.sqrt(a))

def executer_test(nom_test, fichier_data):
    """Exécute un test complet et retourne les résultats."""
    print(f"\n{SEP}")
    print(f"  TEST : {nom_test}")
    print(SEP)

    data = charger_donnees(fichier_data)
    nb_points = len(data['points_collecte'])
    nb_camions = len(data['camions'])
    nb_zones = len(data['zones'])

    print(f"  📦 Points de collecte : {nb_points}")
    print(f"  🚛 Camions           : {nb_camions}")
    print(f"  🗺️  Zones             : {nb_zones}")

    # Statistiques sur les bennes
    total_kg = sum(p.get('demande', 0) for p in data['points_collecte'])
    bennes_par_point = [p.get('nb_bennes', 1) for p in data['points_collecte']]
    print(f"  ♻️  Poids total       : {total_kg:,} kg ({total_kg/1000:.1f} tonnes)")
    print(f"  🗑️  Bennes (moy/max) : {sum(bennes_par_point)/len(bennes_par_point):.1f} / {max(bennes_par_point)}")

    # ------ Phase 1 : Construction graphe ------
    t0 = time.perf_counter()
    g = construire_graphe(data)
    t_graphe = time.perf_counter() - t0
    print(f"\n  [N1] Graphe        : {len(g.sommets)} sommets, {len(g.aretes)//2} arêtes  ({t_graphe*1000:.1f} ms)")

    # ------ Phase 2 : Affectation bipartie ------
    t0 = time.perf_counter()
    camions = [Camion.from_dict(c) for c in data['camions']]
    zones   = [Zone.from_dict(z)   for z in data['zones']]
    aff     = AffectateurBiparti(camions, zones, g)
    affectation = aff.affectation_gloutonne()
    affectation = aff.equilibrage_charges(affectation)
    t_affectation = time.perf_counter() - t0
    print(f"  [N2] Affectation   : {len(affectation)} camions affectés  ({t_affectation*1000:.1f} ms)")

    zones_obj = {z.id: z for z in zones}
    points_autorises = {}
    for camion_id, zone_ids in affectation.items():
        for zid in zone_ids:
            zone = zones_obj.get(zid)
            if zone:
                for pid in zone.points:
                    points_autorises[pid] = camion_id

    # ------ Phase 3 : VRP (2-opt + Tabou) ------
    demandes = {p['id']: p.get('demande', 100) for p in data['points_collecte']}
    opt = OptimiseurVRP(g, camions, demandes, depot_id=0)

    t0 = time.perf_counter()
    init = opt.construire_depuis_affectation(affectation, zones_obj)
    init_2opt = [opt.algorithme_2opt(t) for t in init]
    t_2opt = time.perf_counter() - t0

    # Iterations adaptées selon la taille
    iterations = 15 if nb_points <= 50 else (20 if nb_points <= 100 else 5)

    t0 = time.perf_counter()
    tournees = opt.recherche_tabou(iterations, points_autorises=points_autorises, solution_initiale=init_2opt)
    t_tabou = time.perf_counter() - t0

    t_total = t_graphe + t_affectation + t_2opt + t_tabou

    print(f"  [N4] 2-opt         : ({t_2opt*1000:.1f} ms)")
    print(f"  [N4] Tabou ({iterations} iter): ({t_tabou*1000:.1f} ms)")
    print(f"  ⏱️  Temps total     : {t_total*1000:.1f} ms")

    # ------ Métriques par camion ------
    print(f"\n  {'─'*66}")
    print(f"  {'Camion':<20} {'Dist(km)':>10} {'Poids(kg)':>12} {'Kg/km':>10} {'% cap.':>8}")
    print(f"  {'─'*66}")

    camions_dict = {c['id']: c for c in data['camions']}
    points_dict  = {p['id']: p for p in data['points_collecte']}
    points_dict[0] = data['depot']

    total_dist = 0
    total_poids_transporte = 0
    resultats_camions = []

    for t in tournees:
        dist_km = t.calculer_distance(g, 0)
        nom_cam = camions_dict.get(t.camion_id, {}).get('nom', f'Camion {t.camion_id}')
        cap     = camions_dict.get(t.camion_id, {}).get('capacite', 3000)

        poids = sum(demandes.get(pid, 0) for pid in t.points if pid != 0)
        kg_par_km = round(poids / dist_km, 2) if dist_km > 0.001 else 0
        pct_cap = round(poids / cap * 100, 1) if cap > 0 else 0

        print(f"  {nom_cam:<20} {dist_km:>10.2f} {poids:>12,} {kg_par_km:>10.1f} {pct_cap:>7.1f}%")
        total_dist += dist_km
        total_poids_transporte += poids
        resultats_camions.append({
            'nom': nom_cam, 'dist_km': dist_km,
            'poids_kg': poids, 'kg_par_km': kg_par_km, 'pct_cap': pct_cap
        })

    moy_kg_par_km = round(total_poids_transporte / total_dist, 2) if total_dist > 0 else 0
    print(f"  {'─'*66}")
    print(f"  {'TOTAL / MOYENNE':<20} {total_dist:>10.2f} {total_poids_transporte:>12,} {moy_kg_par_km:>10.1f}")

    camions_actifs = len([t for t in tournees if len(t.points) > 0])
    print(f"\n  📊 Camions actifs        : {camions_actifs}/{nb_camions}")
    print(f"  📏 Distance totale       : {total_dist:.2f} km")
    print(f"  ⚖️  Poids total transporté : {total_poids_transporte:,} kg ({total_poids_transporte/1000:.1f} t)")
    print(f"  📈 Kg/km moyen (flotte)  : {moy_kg_par_km:.1f} kg/km")
    print(f"  ⏱️  Temps calcul total     : {t_total*1000:.1f} ms")

    return {
        'nom': nom_test,
        'nb_points': nb_points,
        'nb_camions': nb_camions,
        'nb_zones': nb_zones,
        'total_kg': total_kg,
        'total_dist_km': round(total_dist, 2),
        'poids_transporte': total_poids_transporte,
        'kg_par_km_moyen': moy_kg_par_km,
        'temps_ms': round(t_total * 1000, 1),
        'camions_detail': resultats_camions
    }

def afficher_recapitulatif(tous_resultats):
    print(f"\n{SEP}")
    print(f"  RÉCAPITULATIF COMPARATIF DES 3 TESTS")
    print(SEP)
    print(f"\n  {'Test':<35} {'Pts':>5} {'Cam':>5} {'Dist km':>9} {'Kg/km':>8} {'Temps ms':>10}")
    print(f"  {'─'*70}")
    for r in tous_resultats:
        print(f"  {r['nom']:<35} {r['nb_points']:>5} {r['nb_camions']:>5} "
              f"{r['total_dist_km']:>9.1f} {r['kg_par_km_moyen']:>8.1f} {r['temps_ms']:>10.1f}")
    print(f"  {'─'*70}")

    # Analyse scalabilité
    if len(tous_resultats) >= 2:
        print(f"\n  ANALYSE DE SCALABILITÉ :")
        for i in range(1, len(tous_resultats)):
            r1, r2 = tous_resultats[i-1], tous_resultats[i]
            facteur_pts = r2['nb_points'] / r1['nb_points']
            facteur_temps = r2['temps_ms'] / max(r1['temps_ms'], 1)
            print(f"  {r1['nom']} → {r2['nom']}")
            print(f"    Points ×{facteur_pts:.1f}  →  Temps ×{facteur_temps:.1f}")

def main():
    print(f"\n{'#'*70}")
    print(f"#  TESTS DE PERFORMANCE - SYSTÈME DE COLLECTE DE DÉCHETS AGADIR")
    print(f"#  {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print(f"{'#'*70}")

    tests = [
        ("Test 1 : 5 camions / 50 points",
         os.path.join(BASE, 'data', 'test1_5camions_50points.json')),
        ("Test 2 : 10 camions / 100 points",
         os.path.join(BASE, 'data', 'test2_10camions_100points.json')),
        ("Test 3 : 20 camions / 500 points",
         os.path.join(BASE, 'data', 'test3_20camions_500points.json')),
    ]

    tous_resultats = []
    for nom, fichier in tests:
        try:
            r = executer_test(nom, fichier)
            tous_resultats.append(r)
        except Exception as e:
            import traceback
            print(f"  ❌ ERREUR dans {nom}: {e}")
            traceback.print_exc()

    afficher_recapitulatif(tous_resultats)

    # Sauvegarder résultats JSON
    output = os.path.join(BASE, 'data', 'resultats_tests.json')
    with open(output, 'w', encoding='utf-8') as f:
        json.dump({
            'date': datetime.now().isoformat(),
            'resultats': tous_resultats
        }, f, ensure_ascii=False, indent=2)
    print(f"\n  💾 Résultats sauvegardés dans : {output}")
    print(f"\n{'#'*70}\n")

if __name__ == '__main__':
    main()
