from flask import Flask, render_template, request, jsonify, send_from_directory
import json, os, sys, copy, random, math
from datetime import datetime

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)

from niveau1.src.graphe_routier import GrapheRoutier, PointCollecte
from niveau2.src.affectateur import Camion, Zone, AffectateurBiparti
from niveau3.src.planificateur import CreneauHoraire, ContrainteTemporelle, PlanificateurTriparti
from niveau4.src.optimiseur_vrp import OptimiseurVRP, Tournee
from niveau5.src.simulateur import CapteurIoT, SimulateurTempsReel, OptimiseurMultiObjectif

app = Flask(__name__)
DATA_FILE = os.path.join(BASE, 'data', 'agadir_data.json')

def load_data():
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        d = json.load(f)
    # Normaliser volume_moyen → volume_estime si manquant
    for z in d.get('zones', []):
        if 'volume_estime' not in z:
            z['volume_estime'] = z.get('volume_moyen', 0)
    return d

def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def build_graphe(data):
    g     = GrapheRoutier()
    depot = data['depot']
    g.ajouter_sommet(PointCollecte(
        depot['id'], depot.get('x', 0), depot.get('y', 0),
        depot.get('nom', 'Dépôt'), depot.get('lat'), depot.get('lon')
    ))
    for p in data['points_collecte']:
        g.ajouter_sommet(PointCollecte.from_dict(p))
    g.construire_graphe_complet()
    return g

def build_affectation(data, g):
    """Calcule l'affectation N2 et retourne (affectation, zones_obj, points_autorises)."""
    camions = [Camion.from_dict(c) for c in data['camions']]
    zones   = [Zone.from_dict(z)   for z in data['zones']]
    aff     = AffectateurBiparti(camions, zones, g)

    affectation = aff.affectation_gloutonne()
    affectation = aff.equilibrage_charges(affectation)

    zones_obj        = {z.id: z for z in zones}
    points_autorises = {}
    for camion_id, zone_ids in affectation.items():
        for zid in zone_ids:
            zone = zones_obj.get(zid)
            if zone:
                for pid in zone.points:
                    points_autorises[pid] = camion_id

    return affectation, zones_obj, points_autorises, aff

# ============ PAGES ============

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/niveau<int:n>')
def page_niveau(n):
    return render_template(f'niveau{n}.html')

# ============ API DATA (CRUD) ============

@app.route('/api/data', methods=['GET'])
def get_data():
    return jsonify(load_data())

# --- Points ---
@app.route('/api/points', methods=['GET'])
def get_points():
    data = load_data()
    return jsonify({'depot': data['depot'], 'points': data['points_collecte']})

@app.route('/api/points', methods=['POST'])
def add_point():
    data = load_data()
    body = request.json
    new_id = max([p['id'] for p in data['points_collecte']], default=0) + 1
    point = {
        'id': new_id, 'lat': body.get('lat'), 'lon': body.get('lon'),
        'nom': body.get('nom', f'Point {new_id}'),
        'adresse': body.get('adresse', ''),
        'x': body.get('x', 0), 'y': body.get('y', 0),
        'demande': body.get('demande', 100)
    }
    data['points_collecte'].append(point)
    save_data(data)
    return jsonify({'success': True, 'point': point})

@app.route('/api/points/<int:pid>', methods=['PUT'])
def update_point(pid):
    data = load_data()
    body = request.json
    for p in data['points_collecte']:
        if p['id'] == pid:
            p.update({k: v for k, v in body.items() if k != 'id'})
            save_data(data)
            return jsonify({'success': True, 'point': p})
    return jsonify({'error': 'Point non trouvé'}), 404

@app.route('/api/points/<int:pid>', methods=['DELETE'])
def delete_point(pid):
    data = load_data()
    # Supprimer le point de la liste des points
    data['points_collecte'] = [p for p in data['points_collecte'] if p['id'] != pid]
    # Nettoyer les références à ce point dans toutes les zones
    for z in data['zones']:
        if pid in z.get('points', []):
            z['points'] = [p for p in z['points'] if p != pid]
    save_data(data)
    return jsonify({'success': True})

# --- Zones ---
@app.route('/api/zones', methods=['GET'])
def get_zones():
    return jsonify(load_data()['zones'])

@app.route('/api/zones', methods=['POST'])
def add_zone():
    data = load_data()
    body = request.json
    new_id = max([z['id'] for z in data['zones']], default=0) + 1
    zone = {
        'id': new_id, 'nom': body.get('nom', f'Zone {new_id}'),
        'points': body.get('points', []),
        'volume_moyen': body.get('volume_moyen', 200),
        'volume_estime': body.get('volume_moyen', body.get('volume_estime', 200)),
        'centre': body.get('centre', {'x': 0, 'y': 0}),
        'centre_lat': body.get('centre_lat'),
        'centre_lon': body.get('centre_lon'),
        'frequence_collecte': body.get('frequence_collecte', 'quotidien'),
        'priorite': body.get('priorite', 'normale'),
        'couleur': body.get('couleur', '#' + '%06x' % random.randint(0, 0xFFFFFF))
    }
    data['zones'].append(zone)
    save_data(data)
    return jsonify({'success': True, 'zone': zone})

@app.route('/api/zones/<int:zid>', methods=['PUT'])
def update_zone(zid):
    data = load_data()
    body = request.json
    for z in data['zones']:
        if z['id'] == zid:
            z.update({k: v for k, v in body.items() if k != 'id'})
            if 'volume_moyen' in body:
                z['volume_estime'] = body['volume_moyen']
            save_data(data)
            return jsonify({'success': True, 'zone': z})
    return jsonify({'error': 'Zone non trouvée'}), 404

@app.route('/api/zones/<int:zid>', methods=['DELETE'])
def delete_zone(zid):
    data = load_data()
    data['zones'] = [z for z in data['zones'] if z['id'] != zid]
    save_data(data)
    return jsonify({'success': True})

# --- Camions ---
@app.route('/api/camions', methods=['GET'])
def get_camions():
    return jsonify(load_data()['camions'])

@app.route('/api/camions', methods=['POST'])
def add_camion():
    data = load_data()
    body = request.json
    new_id = max([c['id'] for c in data['camions']], default=0) + 1
    camion = {
        'id': new_id, 'nom': body.get('nom', f'Camion {new_id}'),
        'capacite': int(body.get('capacite', 3000)),
        'cout_fixe': body.get('cout_fixe', 150),
        'zones_accessibles': body.get('zones_accessibles', []),
        'position_initial': {'x': 0, 'y': 0},
        'couleur': body.get('couleur', '#3498db')
    }
    data['camions'].append(camion)
    save_data(data)
    return jsonify({'success': True, 'camion': camion})

@app.route('/api/camions/<int:cid>', methods=['PUT'])
def update_camion(cid):
    data = load_data()
    body = request.json
    for c in data['camions']:
        if c['id'] == cid:
            c.update({k: v for k, v in body.items() if k != 'id'})
            # S'assurer que capacite est bien un entier
            c['capacite'] = int(c.get('capacite', 3000))
            save_data(data)
            return jsonify({'success': True, 'camion': c})
    return jsonify({'error': 'Camion non trouvé'}), 404

@app.route('/api/camions/<int:cid>', methods=['DELETE'])
def delete_camion(cid):
    data = load_data()
    data['camions'] = [c for c in data['camions'] if c['id'] != cid]
    save_data(data)
    return jsonify({'success': True})

# ============ API NIVEAUX ============

@app.route('/api/niveau1/calculer', methods=['POST'])
def calculer_niveau1():
    try:
        data = load_data()
        g    = build_graphe(data)
        matrice, ids, chemins = g.matrice_distances()
        connexe = g.est_connexe()
        sommets_ids = [p['id'] for p in data['points_collecte']]
        sample_chemins = []
        if len(sommets_ids) >= 2:
            d, ch = g.plus_court_chemin(0, sommets_ids[-1])
            sample_chemins.append({'depart': 0, 'arrivee': sommets_ids[-1],
                                   'distance': round(d, 3), 'chemin': ch})
        return jsonify({
            'success': True, 'matrice': matrice, 'ids_sommets': ids,
            'chemins': chemins[:10], 'connexe': connexe,
            'nb_sommets': len(g.sommets), 'nb_aretes': len(g.aretes) // 2
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/niveau1/chemin', methods=['POST'])
def chemin_niveau1():
    body = request.json
    data = load_data()
    g    = build_graphe(data)
    d, ch = g.plus_court_chemin(body['depart'], body['arrivee'])
    return jsonify({'distance': round(d, 4), 'chemin': ch})

@app.route('/api/niveau2/affecter', methods=['POST'])
def affecter_niveau2():
    try:
        data = load_data()
        g    = build_graphe(data)
        affectation, zones_obj, points_autorises, aff = build_affectation(data, g)

        rapport = aff.generer_rapport(affectation)
        valide  = aff.verifier_contraintes(affectation)
        rapport['valide'] = valide

        zones_dict   = {z['id']: z for z in data['zones']}
        camions_dict = {c['id']: c for c in data['camions']}
        for item in rapport['affectation']:
            item['camion_couleur']  = camions_dict.get(item['camion_id'], {}).get('couleur', '#333')
            item['camion_nom']      = camions_dict.get(item['camion_id'], {}).get('nom', '')
            item['zones_details']   = [zones_dict[zid] for zid in item['zones_affectees']
                                        if zid in zones_dict]
        return jsonify({'success': True, **rapport})
    except Exception as e:
        import traceback
        return jsonify({'success': False, 'error': str(e),
                        'trace': traceback.format_exc()}), 500

@app.route('/api/niveau3/planifier', methods=['POST'])
def planifier_niveau3():
    try:
        data     = load_data()
        g        = build_graphe(data)
        camions  = [Camion.from_dict(c) for c in data['camions']]
        zones    = [Zone.from_dict(z)   for z in data['zones']]
        creneaux = [CreneauHoraire(c['id'], c['debut'], c['fin'], c['jour'],
                                    c.get('niveau_congestion', 1.0))
                    for c in data['creneaux']]
        aff          = AffectateurBiparti(camions, zones, g)
        contraintes  = ContrainteTemporelle()
        planif       = PlanificateurTriparti(aff, creneaux, contraintes)
        plan         = planif.generer_plan_optimal()
        indicateurs  = planif.evaluer_plan(plan)

        total_taches = sum(len(v) for v in plan.values())
        return jsonify({
            'success':     True,
            'plan':        plan,
            'indicateurs': indicateurs,
            'total_taches': total_taches
        })
    except Exception as e:
        import traceback
        return jsonify({'success': False, 'error': str(e),
                        'trace': traceback.format_exc()}), 500

@app.route('/api/niveau4/optimiser', methods=['POST'])
def optimiser_niveau4():
    try:
        data    = load_data()
        g       = build_graphe(data)
        camions = [Camion.from_dict(c) for c in data['camions']]
        zones   = [Zone.from_dict(z)   for z in data['zones']]
        demandes = {p['id']: p.get('demande', 100) for p in data['points_collecte']}
        points_existants = {p['id'] for p in data['points_collecte']}

        # Nettoyer les zones : retirer les points supprimés
        for z in data['zones']:
            avant = len(z.get('points', []))
            z['points'] = [pid for pid in z.get('points', []) if pid in points_existants]
            if len(z['points']) != avant:
                save_data(data)  # persister le nettoyage

        # ── Étape 1 : Affectation N2 ────────────────────────────────
        affectation, zones_obj, points_autorises, aff = build_affectation(data, g)

        # ── Étape 2 : Tournées initiales depuis affectation N2 ───────
        opt       = OptimiseurVRP(g, camions, demandes, depot_id=0)
        init      = opt.construire_depuis_affectation(affectation, zones_obj)
        dist_init = sum(t.calculer_distance(g, 0) for t in init)

        # ── Étape 3 : 2-opt sur chaque tournée ──────────────────────
        init_2opt = [opt.algorithme_2opt(t) for t in init]

        # ── Étape 4 : Tabou avec solution initiale N2+2opt ───────────
        body       = request.json or {}
        iterations = body.get('iterations', 30)

        # Passer directement init_2opt comme solution de depart au Tabou
        tournees = opt.recherche_tabou(
            iterations,
            points_autorises=points_autorises,
            solution_initiale=init_2opt
        )

        dist_final   = sum(t.calculer_distance(g, 0) for t in tournees)
        dist_2opt_total = sum(t.calculer_distance(g, 0) for t in init_2opt)
        amelioration = round((dist_init - dist_final) / max(0.001, dist_init) * 100, 2)
        gain_2opt    = round((dist_init - dist_2opt_total) / max(0.001, dist_init) * 100, 2)
        gain_tabou   = round((dist_2opt_total - dist_final) / max(0.001, dist_2opt_total) * 100, 2)
        eval_res     = opt.evaluer_solution(tournees)

        # ── Construction réponse ─────────────────────────────────────
        camions_dict = {c['id']: c for c in data['camions']}
        points_dict  = {p['id']: p for p in data['points_collecte']}
        points_dict[0] = data['depot']

        tournees_data = []
        for t in tournees:
            td = t.to_dict(g, 0)
            td['couleur']    = camions_dict.get(t.camion_id, {}).get('couleur', '#333')
            td['nom_camion'] = camions_dict.get(t.camion_id, {}).get('nom', '')
            coords = []
            for pid in td['points_ordre']:
                pt = points_dict.get(pid)
                if pt and pt.get('lat'):
                    coords.append({'id': pid, 'lat': pt['lat'], 'lon': pt['lon'],
                                   'nom': pt.get('nom', ''), 'is_depot': pid == 0})
            td['coords'] = coords
            tournees_data.append(td)

        return jsonify({
            'success':  True,
            'tournees': tournees_data,
            'performance': {
                **eval_res,
                'amelioration_vs_initial': amelioration,
                'distance_initiale':       round(dist_init, 4),
                'distance_apres_2opt':     round(dist_2opt_total, 4),
                'gain_2opt':               gain_2opt,
                'gain_tabou':              gain_tabou
            }
        })
    except Exception as e:
        import traceback
        return jsonify({'success': False, 'error': str(e),
                        'trace': traceback.format_exc()}), 500

@app.route('/api/niveau5/simuler', methods=['POST'])
def simuler_niveau5():
    try:
        data    = load_data()
        g       = build_graphe(data)
        camions = [Camion.from_dict(c) for c in data['camions']]
        points_existants_n5 = {p['id'] for p in data['points_collecte']}
        for z in data['zones']:
            z['points'] = [pid for pid in z.get('points', []) if pid in points_existants_n5]
        demandes = {p['id']: p.get('demande', 100) for p in data['points_collecte']}
        capteurs = {p['id']: CapteurIoT(p['id'], random.uniform(20, 70), 80.0)
                    for p in data['points_collecte']}
        opt      = OptimiseurVRP(g, camions, demandes, depot_id=0)
        sim      = SimulateurTempsReel(opt, capteurs, "08:00")
        resultats = sim.simuler_journee(nb_pas=8)
        # Utiliser affectation N2 + 2opt comme point de depart (coherence avec N4)
        zones_n5   = [Zone.from_dict(z) for z in data['zones']]
        aff_n5     = AffectateurBiparti(camions, zones_n5, g)
        affect_n5  = aff_n5.affectation_gloutonne()
        affect_n5  = aff_n5.equilibrage_charges(affect_n5)
        zones_obj_n5 = {z.id: z for z in zones_n5}
        init_n5    = opt.construire_depuis_affectation(affect_n5, zones_obj_n5)
        init_n5    = [opt.algorithme_2opt(t) for t in init_n5]
        tournees   = opt.recherche_tabou(20, solution_initiale=init_n5)
        objectifs = [
            {"nom": "cout",         "type": "minimiser", "poids": 0.3},
            {"nom": "co2",          "type": "minimiser", "poids": 0.3},
            {"nom": "satisfaction", "type": "maximiser", "poids": 0.2},
            {"nom": "equite",       "type": "maximiser", "poids": 0.2}
        ]
        poids = [o['poids'] for o in objectifs]
        mobj  = OptimiseurMultiObjectif(objectifs, poids)
        scores = mobj.evaluer_solution(tournees, g, 0)
        co2    = sim.calculer_emissions_co2(tournees)
        return jsonify({
            'success': True,
            'simulation': resultats,
            'capteurs_final': {pid: c.to_dict() for pid, c in capteurs.items()},
            'scores_objectifs': {'cout': scores[0], 'co2': scores[1],
                                  'satisfaction': scores[2], 'equite': scores[3]},
            'co2_total': co2,
            'evenements': sim.evenements,
            'points_urgents': [pid for pid, c in capteurs.items() if c.detecter_urgence()]
        })
    except Exception as e:
        import traceback
        return jsonify({'success': False, 'error': str(e),
                        'trace': traceback.format_exc()}), 500

@app.route('/api/niveau5/pas_temps', methods=['POST'])
def pas_temps():
    data    = load_data()
    capteurs = {p['id']: CapteurIoT(p['id'], random.uniform(30, 95), 80.0)
                for p in data['points_collecte']}
    g       = build_graphe(data)
    camions = [Camion.from_dict(c) for c in data['camions']]
    demandes = {p['id']: p.get('demande', 100) for p in data['points_collecte']}
    opt     = OptimiseurVRP(g, camions, demandes)
    sim     = SimulateurTempsReel(opt, capteurs)
    etat    = sim.executer_pas_temps(15)
    return jsonify({'success': True, 'etat': etat})



# ============ ROUTES TEST PAR NIVEAU ============

def load_test_data(test_id):
    """Charge les données du fichier test correspondant."""
    fichiers = {
        1: 'test1_5camions_50points.json',
        2: 'test2_10camions_100points.json',
        3: 'test3_20camions_500points.json',
    }
    f = os.path.join(BASE, 'data', fichiers.get(test_id, 'agadir_data.json'))
    with open(f, 'r', encoding='utf-8') as fp:
        data = json.load(fp)
    for z in data.get('zones', []):
        if 'volume_estime' not in z:
            z['volume_estime'] = z.get('volume_moyen', 0)
    return data


@app.route('/api/test/<int:test_id>/niveau1', methods=['POST'])
def test_niveau1(test_id):
    try:
        import time
        data = load_test_data(test_id)
        t0 = time.perf_counter()
        g = build_graphe(data)
        matrice, ids, chemins = g.matrice_distances()
        connexe = g.est_connexe()
        temps_ms = round((time.perf_counter() - t0) * 1000, 1)

        # Coordonnées de tous les points pour la carte
        points_dict = {p['id']: p for p in data['points_collecte']}
        points_dict[0] = data['depot']
        coords_points = [
            {'id': p['id'], 'lat': p.get('lat'), 'lon': p.get('lon'), 'nom': p.get('nom',''), 'demande': p.get('demande',0)}
            for p in data['points_collecte'] if p.get('lat')
        ]
        depot = {'id': 0, 'lat': data['depot'].get('lat'), 'lon': data['depot'].get('lon'), 'nom': data['depot'].get('nom','Dépôt')}

        return jsonify({
            'success': True,
            'nb_sommets': len(g.sommets),
            'nb_aretes': len(g.aretes) // 2,
            'connexe': connexe,
            'temps_ms': temps_ms,
            'depot': depot,
            'points': coords_points,
        })
    except Exception as e:
        import traceback
        return jsonify({'success': False, 'error': str(e), 'trace': traceback.format_exc()}), 500


@app.route('/api/test/<int:test_id>/niveau2', methods=['POST'])
def test_niveau2(test_id):
    try:
        import time
        data = load_test_data(test_id)
        g = build_graphe(data)
        t0 = time.perf_counter()
        affectation, zones_obj, points_autorises, aff = build_affectation(data, g)
        rapport = aff.generer_rapport(affectation)
        temps_ms = round((time.perf_counter() - t0) * 1000, 1)

        camions_dict = {c['id']: c for c in data['camions']}
        zones_dict   = {z['id']: z for z in data['zones']}

        affectation_detail = []
        for item in rapport['affectation']:
            affectation_detail.append({
                'camion_id':    item['camion_id'],
                'camion_nom':   camions_dict.get(item['camion_id'], {}).get('nom', ''),
                'camion_couleur': camions_dict.get(item['camion_id'], {}).get('couleur', '#333'),
                'zones':        item['zones_affectees'],
                'charge':       item.get('charge_totale', 0),
            })

        return jsonify({
            'success': True,
            'nb_camions': len(data['camions']),
            'nb_zones':   len(data['zones']),
            'nb_points':  len(data['points_collecte']),
            'temps_ms':   temps_ms,
            'affectation': affectation_detail,
            'valide':      aff.verifier_contraintes(affectation),
        })
    except Exception as e:
        import traceback
        return jsonify({'success': False, 'error': str(e), 'trace': traceback.format_exc()}), 500


@app.route('/api/test/<int:test_id>/niveau3', methods=['POST'])
def test_niveau3(test_id):
    try:
        import time
        data = load_test_data(test_id)
        g = build_graphe(data)
        camions  = [Camion.from_dict(c) for c in data['camions']]
        zones    = [Zone.from_dict(z)   for z in data['zones']]
        creneaux = [CreneauHoraire(c['id'], c['debut'], c['fin'], c['jour'], c.get('niveau_congestion', 1.0))
                    for c in data['creneaux']]
        aff         = AffectateurBiparti(camions, zones, g)
        contraintes = ContrainteTemporelle()
        planif      = PlanificateurTriparti(aff, creneaux, contraintes)
        t0 = time.perf_counter()
        plan        = planif.generer_plan_optimal()
        indicateurs = planif.evaluer_plan(plan)
        temps_ms = round((time.perf_counter() - t0) * 1000, 1)

        total_taches = sum(len(v) for v in plan.values())
        jours_actifs = [j for j, v in plan.items() if v]

        return jsonify({
            'success': True,
            'total_taches': total_taches,
            'jours_actifs': len(jours_actifs),
            'indicateurs': indicateurs,
            'temps_ms': temps_ms,
            'plan_resume': {j: len(v) for j, v in plan.items() if v},
        })
    except Exception as e:
        import traceback
        return jsonify({'success': False, 'error': str(e), 'trace': traceback.format_exc()}), 500


@app.route('/api/test/<int:test_id>/niveau4', methods=['POST'])
def test_niveau4(test_id):
    try:
        import time
        data = load_test_data(test_id)
        g = build_graphe(data)
        camions  = [Camion.from_dict(c) for c in data['camions']]
        demandes = {p['id']: p.get('demande', 100) for p in data['points_collecte']}
        points_existants = {p['id'] for p in data['points_collecte']}
        for z in data['zones']:
            z['points'] = [pid for pid in z.get('points', []) if pid in points_existants]

        affectation, zones_obj, points_autorises, aff = build_affectation(data, g)
        opt  = OptimiseurVRP(g, camions, demandes, depot_id=0)
        init = opt.construire_depuis_affectation(affectation, zones_obj)
        dist_init = sum(t.calculer_distance(g, 0) for t in init)

        t0 = time.perf_counter()
        init_2opt = [opt.algorithme_2opt(t) for t in init]
        t_2opt = time.perf_counter() - t0

        nb_pts = len(data['points_collecte'])
        # Calibré pour ~10s max quelle que soit la taille
        iterations = 10 if nb_pts <= 50 else (5 if nb_pts <= 100 else 2)

        t0 = time.perf_counter()
        tournees = opt.recherche_tabou(iterations, points_autorises=points_autorises, solution_initiale=init_2opt)
        t_tabou = time.perf_counter() - t0

        dist_final = sum(t.calculer_distance(g, 0) for t in tournees)
        amelioration = round((dist_init - dist_final) / max(0.001, dist_init) * 100, 2)

        camions_dict = {c['id']: c for c in data['camions']}
        points_dict  = {p['id']: p for p in data['points_collecte']}
        points_dict[0] = data['depot']

        tournees_data = []
        for t in tournees:
            td = t.to_dict(g, 0)
            td['couleur']    = camions_dict.get(t.camion_id, {}).get('couleur', '#3498db')
            td['nom_camion'] = camions_dict.get(t.camion_id, {}).get('nom', f'Camion {t.camion_id}')
            coords = []
            for pid in td['points_ordre']:
                pt = points_dict.get(pid)
                if pt and pt.get('lat'):
                    coords.append({'id': pid, 'lat': pt['lat'], 'lon': pt['lon'],
                                   'nom': pt.get('nom',''), 'is_depot': pid==0})
            td['coords'] = coords
            tournees_data.append(td)

        total_poids = sum(sum(demandes.get(pid,0) for pid in t.points if pid!=0) for t in tournees)
        moy_kg_km = round(total_poids / max(0.001, dist_final), 1)

        return jsonify({
            'success': True,
            'tournees': tournees_data,
            'dist_init_km': round(dist_init, 2),
            'dist_final_km': round(dist_final, 2),
            'amelioration': amelioration,
            'iterations': iterations,
            'total_poids_kg': total_poids,
            'moy_kg_par_km': moy_kg_km,
            'temps_2opt_ms': round(t_2opt * 1000, 1),
            'temps_tabou_ms': round(t_tabou * 1000, 1),
        })
    except Exception as e:
        import traceback
        return jsonify({'success': False, 'error': str(e), 'trace': traceback.format_exc()}), 500


@app.route('/api/test/<int:test_id>/niveau5', methods=['POST'])
def test_niveau5(test_id):
    try:
        import time
        data = load_test_data(test_id)
        g = build_graphe(data)
        camions  = [Camion.from_dict(c) for c in data['camions']]
        demandes = {p['id']: p.get('demande', 100) for p in data['points_collecte']}
        capteurs = {p['id']: CapteurIoT(p['id'], random.uniform(20, 70), 80.0)
                    for p in data['points_collecte']}
        opt = OptimiseurVRP(g, camions, demandes, depot_id=0)
        sim = SimulateurTempsReel(opt, capteurs, "08:00")

        t0 = time.perf_counter()
        resultats = sim.simuler_journee(nb_pas=5)
        zones_n5  = [Zone.from_dict(z) for z in data['zones']]
        aff_n5    = AffectateurBiparti(camions, zones_n5, g)
        affect_n5 = aff_n5.affectation_gloutonne()
        affect_n5 = aff_n5.equilibrage_charges(affect_n5)
        zones_obj_n5 = {z.id: z for z in zones_n5}
        init_n5   = opt.construire_depuis_affectation(affect_n5, zones_obj_n5)
        init_n5   = [opt.algorithme_2opt(t) for t in init_n5]
        nb_pts_n5 = len(data['points_collecte'])
        iter_n5 = 5 if nb_pts_n5 <= 50 else (3 if nb_pts_n5 <= 100 else 1)
        tournees  = opt.recherche_tabou(iter_n5, solution_initiale=init_n5)
        objectifs = [
            {"nom":"cout","type":"minimiser","poids":0.3},
            {"nom":"co2","type":"minimiser","poids":0.3},
            {"nom":"satisfaction","type":"maximiser","poids":0.2},
            {"nom":"equite","type":"maximiser","poids":0.2}
        ]
        mobj   = OptimiseurMultiObjectif(objectifs, [o['poids'] for o in objectifs])
        scores = mobj.evaluer_solution(tournees, g, 0)
        co2    = sim.calculer_emissions_co2(tournees)
        temps_ms = round((time.perf_counter() - t0) * 1000, 1)
        points_urgents = [pid for pid, c in capteurs.items() if c.detecter_urgence()]

        return jsonify({
            'success': True,
            'co2_total': round(co2, 2),
            'scores': {'cout': round(scores[0],1), 'co2': round(scores[1],1),
                       'satisfaction': round(scores[2],1), 'equite': round(scores[3],1)},
            'points_urgents': len(points_urgents),
            'nb_evenements': len(sim.evenements),
            'temps_ms': temps_ms,
            'capteurs_resume': {
                'total': len(capteurs),
                'urgents': len(points_urgents),
                'moy_remplissage': round(sum(c.taux for c in capteurs.values())/max(1,len(capteurs)),1)
            }
        })
    except Exception as e:
        import traceback
        return jsonify({'success': False, 'error': str(e), 'trace': traceback.format_exc()}), 500

@app.route('/tests')
def page_tests():
    return render_template('tests.html')

# Stockage des résultats de tests en mémoire
_tests_results = {}
_tests_running = {}

@app.route('/api/tests/status/<int:test_id>', methods=['GET'])
def test_status(test_id):
    if test_id in _tests_running and _tests_running[test_id]:
        return jsonify({'status': 'running'})
    if test_id in _tests_results:
        return jsonify({'status': 'done', 'result': _tests_results[test_id]})
    return jsonify({'status': 'idle'})

@app.route('/api/tests/lancer', methods=['POST'])
def api_lancer_tests():
    import time, threading
    body = request.json or {}
    test_id = body.get('test_id', 1)

    fichiers = {
        1: os.path.join(BASE, 'data', 'test1_5camions_50points.json'),
        2: os.path.join(BASE, 'data', 'test2_10camions_100points.json'),
        3: os.path.join(BASE, 'data', 'test3_20camions_500points.json'),
    }
    noms = {
        1: 'Test 1 — 5 camions / 50 points',
        2: 'Test 2 — 10 camions / 100 points',
        3: 'Test 3 — 20 camions / 500 points',
    }

    fichier = fichiers.get(test_id)
    if not fichier or not os.path.exists(fichier):
        return jsonify({'success': False, 'error': 'Fichier introuvable'}), 404

    _tests_running[test_id] = True
    _tests_results.pop(test_id, None)

    def run_test():
        try:
            with open(fichier, 'r', encoding='utf-8') as f:
                data = json.load(f)

            for z in data.get('zones', []):
                if 'volume_estime' not in z:
                    z['volume_estime'] = z.get('volume_moyen', 0)

            from niveau2.src.affectateur import Camion, Zone, AffectateurBiparti
            from niveau4.src.optimiseur_vrp import OptimiseurVRP

            nb_points  = len(data['points_collecte'])
            nb_camions = len(data['camions'])
            total_kg   = sum(p.get('demande', 0) for p in data['points_collecte'])
            bennes     = [p.get('nb_bennes', 1) for p in data['points_collecte']]
            moy_bennes = round(sum(bennes) / len(bennes), 1)

            t0 = time.perf_counter()
            g  = build_graphe(data)
            t_graphe = time.perf_counter() - t0

            t0 = time.perf_counter()
            camions = [Camion.from_dict(c) for c in data['camions']]
            zones   = [Zone.from_dict(z)   for z in data['zones']]
            aff     = AffectateurBiparti(camions, zones, g)
            affectation = aff.affectation_gloutonne()
            affectation = aff.equilibrage_charges(affectation)
            t_aff = time.perf_counter() - t0

            zones_obj = {z.id: z for z in zones}
            points_autorises = {}
            for cid, zids in affectation.items():
                for zid in zids:
                    zo = zones_obj.get(zid)
                    if zo:
                        for pid in zo.points:
                            points_autorises[pid] = cid

            demandes = {p['id']: p.get('demande', 100) for p in data['points_collecte']}
            opt = OptimiseurVRP(g, camions, demandes, depot_id=0)

            t0 = time.perf_counter()
            init = opt.construire_depuis_affectation(affectation, zones_obj)
            init_2opt = [opt.algorithme_2opt(t) for t in init]
            t_2opt = time.perf_counter() - t0

            iterations = 10 if nb_points <= 50 else (5 if nb_points <= 100 else 2)
            t0 = time.perf_counter()
            tournees = opt.recherche_tabou(iterations, points_autorises=points_autorises, solution_initiale=init_2opt)
            t_tabou = time.perf_counter() - t0

            t_total = t_graphe + t_aff + t_2opt + t_tabou

            camions_dict = {c['id']: c for c in data['camions']}
            resultats_camions = []
            total_dist = 0
            total_poids = 0

            for t in tournees:
                dist  = t.calculer_distance(g, 0)
                nom   = camions_dict.get(t.camion_id, {}).get('nom', f'Camion {t.camion_id}')
                cap   = camions_dict.get(t.camion_id, {}).get('capacite', 3000)
                coul  = camions_dict.get(t.camion_id, {}).get('couleur', '#3498db')
                poids = sum(demandes.get(pid, 0) for pid in t.points if pid != 0)
                kg_km = round(poids / dist, 1) if dist > 0.001 else 0
                pct   = round(poids / cap * 100, 1) if cap > 0 else 0
                total_dist  += dist
                total_poids += poids
                resultats_camions.append({
                    'nom': nom, 'couleur': coul,
                    'dist_km': round(dist, 2),
                    'poids_kg': poids,
                    'kg_par_km': kg_km,
                    'pct_cap': pct
                })

            moy_kg_km = round(total_poids / total_dist, 1) if total_dist > 0 else 0

            _tests_results[test_id] = {
                'success': True,
                'nom': noms[test_id],
                'nb_points': nb_points,
                'nb_camions': nb_camions,
                'total_kg': total_kg,
                'moy_bennes': moy_bennes,
                'nb_sommets': len(g.sommets),
                'nb_aretes': len(g.aretes) // 2,
                'camions_actifs': len([t for t in tournees if len(t.points) > 0]),
                'total_dist_km': round(total_dist, 2),
                'total_poids_kg': total_poids,
                'moy_kg_par_km': moy_kg_km,
                'temps_total_ms': round(t_total * 1000, 1),
                'temps_graphe_ms': round(t_graphe * 1000, 1),
                'temps_aff_ms': round(t_aff * 1000, 1),
                'temps_2opt_ms': round(t_2opt * 1000, 1),
                'temps_tabou_ms': round(t_tabou * 1000, 1),
                'iterations_tabou': iterations,
                'camions': resultats_camions,
            }
        except Exception as e:
            import traceback
            _tests_results[test_id] = {'success': False, 'error': str(e), 'trace': traceback.format_exc()}
        finally:
            _tests_running[test_id] = False

    threading.Thread(target=run_test, daemon=True).start()
    return jsonify({'success': True, 'status': 'started', 'test_id': test_id})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
