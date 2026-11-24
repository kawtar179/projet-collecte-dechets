import random

class OptimiseurMultiObjectif:
    def __init__(self, objectifs: list, poids: list = None):
        self.objectifs = objectifs
        self.poids = poids or [1.0] * len(objectifs)
        self.solutions_pareto = []

    def evaluer_solution(self, tournees: list) -> list:
        scores = []
        for obj in self.objectifs:
            if obj["type"] == "minimiser":
                scores.append(random.uniform(800, 1500))
            else:
                scores.append(random.uniform(70, 95))
        return scores

    def domine(self, s1: list, s2: list) -> bool:
        """s1 domine s2 si meilleur ou égal sur tous et strict sur au moins un"""
        better = False
        for i, (a, b) in enumerate(zip(s1, s2)):
            obj_type = self.objectifs[i]["type"] if i < len(self.objectifs) else "minimiser"
            if obj_type == "minimiser":
                if a > b: return False
                if a < b: better = True
            else:
                if a < b: return False
                if a > b: better = True
        return better

    def trouver_front_pareto(self, population: list, generations: int = 50) -> list:
        non_dominees = []
        scores_list = [self.evaluer_solution(sol) for sol in population]
        
        for i, scores_i in enumerate(scores_list):
            domine_par_autre = False
            for j, scores_j in enumerate(scores_list):
                if i != j and self.domine(scores_j, scores_i):
                    domine_par_autre = True
                    break
            if not domine_par_autre:
                non_dominees.append({
                    "solution_id": i + 1,
                    "scores": {obj["nom"]: round(s, 1) for obj, s in zip(self.objectifs, scores_i)},
                    "dominance": "non_dominee"
                })
        
        self.solutions_pareto = non_dominees
        return non_dominees

    def selectionner_solution(self, strategie: str = "equilibre") -> dict:
        if not self.solutions_pareto:
            return {}
        if strategie == "cout":
            return min(self.solutions_pareto, 
                      key=lambda s: s["scores"].get("cout", float("inf")))
        elif strategie == "co2":
            return min(self.solutions_pareto, 
                      key=lambda s: s["scores"].get("co2", float("inf")))
        else:  # equilibre - weighted sum
            def score_equilibre(sol):
                total = 0
                for i, obj in enumerate(self.objectifs):
                    val = sol["scores"].get(obj["nom"], 0)
                    w = self.poids[i] if i < len(self.poids) else 1.0
                    total += val * w * (1 if obj["type"] == "minimiser" else -1)
                return total
            return min(self.solutions_pareto, key=score_equilibre)
