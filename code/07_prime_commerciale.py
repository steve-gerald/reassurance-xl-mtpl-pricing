"""
Script 7 / 7 : Chargement de sécurité et prime commerciale recommandée
----------------------------------------------------------------------

La prime pure constitue le coût attendu de la sinistralité réassurée. Pour la
prime commerciale, on ajoute :
   - un chargement de sécurité (lié à la volatilité de la sinistralité) ;
   - un chargement pour frais de gestion du réassureur ;
   - éventuellement un chargement pour le coût du capital économique (SCR).

Principes statistiques utilisés :
  - Principe de l'écart-type :  P = E[S] + k * sigma(S)
  - Principe de la variance     :  P = E[S] + k * Var(S)
  - Principe de l'utilité espérée (non implémenté ici)

On calcule sigma(S) à partir des charges annuelles historiques par couche
(volatilité empirique, n=10 années). Pour les couches XL la distribution
est fortement asymétrique : la sigma seule ne capture pas tout le risque.
Une analyse complémentaire par bootstrap est ajoutée.
"""

from pathlib import Path
import pandas as pd
import numpy as np

PROJECT_DIR = Path(__file__).resolve().parent.parent
OUT_DIR = PROJECT_DIR / "outputs"

PRIORITE_1, PORTEE_1 = 2_000_000, 8_000_000
PRIORITE_2, PORTEE_2 = 10_000_000, 20_000_000
ANNEE_TRAITE = 2024

# Paramètres commerciaux retenus pour la recommandation finale
K_ECART_TYPE     = 0.30   # coefficient écart-type (0.2 = prudent, 0.5 = très conservateur)
FRAIS_GESTION    = 0.05   # 5 % de chargement de frais de gestion réassureur
COUT_CAPITAL_AP  = 0.06   # 6 % du capital économique alloué (proxy SCR-non-vie)

# Méthode retenue pour la prime pure de référence
# -> on prend la méthode "B - Indexation par paiement, 1% superimposed" comme
# référence centrale, car elle traite finement l'inflation et est cohérente
# avec les pratiques de pricing actuary en pratique.
METHODE_REF = "B - Indexation par paiement (1 pct sup.)"


def bootstrap_charge_annuelle(df_sin_indexe: pd.DataFrame,
                              priorite: float, portee: float,
                              annees_histo, n_boot: int = 5000,
                              seed: int = 42) -> np.ndarray:
    """
    Bootstrap par année de survenance : on rééchantillonne avec remise les
    années pour produire une distribution empirique de la charge annuelle.
    """
    rng = np.random.default_rng(seed)
    # Charge annuelle observée par année
    df = df_sin_indexe.copy()
    df["cout"] = df["incurred_indexe"].apply(
        lambda x: min(portee, max(x - priorite, 0)))
    charges = (df.groupby("annee_surv")["cout"].sum()
                 .reindex(annees_histo, fill_value=0).values)
    n = len(charges)
    return np.array([
        rng.choice(charges, size=n, replace=True).mean()
        for _ in range(n_boot)
    ])


def main():
    # -- 1. Récupération des résultats des étapes précédentes ----------------
    synth_sans = pd.read_csv(OUT_DIR / "synthese_sans_clause.csv").iloc[0]
    synth_avec = pd.read_csv(OUT_DIR / "synthese_avec_clause.csv")
    synth_pareto = pd.read_csv(OUT_DIR / "synthese_pareto.csv").iloc[0]
    bc_sans_clause = pd.read_csv(OUT_DIR / "bc_sans_clause.csv")
    bc_avec_B = pd.read_csv(OUT_DIR / "bc_avec_clause_methode_B.csv")
    sin_indexes = pd.read_csv(OUT_DIR / "sinistres_indexes.csv")

    annees_histo = list(range(2014, 2024))

    print("=== Vue d'ensemble des estimations de prime pure 2024 ===")
    ref = synth_avec[synth_avec["methode"] == METHODE_REF].iloc[0]
    table = pd.DataFrame([
        {"Approche": "BC sans clause de stabilité (BC moyen 2014-2023)",
         "Prime pure Couche 1 (MEUR)": synth_sans["prime_pure_couche_1"]/1e6,
         "Prime pure Couche 2 (MEUR)": synth_sans["prime_pure_couche_2"]/1e6},
        {"Approche": "BC AVEC clause - méthode A (as-if simple)",
         "Prime pure Couche 1 (MEUR)": synth_avec[synth_avec["methode"]=="A - As-if simple (1 pct sup.)"]
                                              ["prime_pure_couche_1"].iloc[0]/1e6,
         "Prime pure Couche 2 (MEUR)": synth_avec[synth_avec["methode"]=="A - As-if simple (1 pct sup.)"]
                                              ["prime_pure_couche_2"].iloc[0]/1e6},
        {"Approche": "BC AVEC clause - méthode B (par paiement) [REFERENCE]",
         "Prime pure Couche 1 (MEUR)": ref["prime_pure_couche_1"]/1e6,
         "Prime pure Couche 2 (MEUR)": ref["prime_pure_couche_2"]/1e6},
        {"Approche": "Modèle Pareto/GPD (sévérité conditionnelle)",
         "Prime pure Couche 1 (MEUR)": synth_pareto["prime_pure_1_2024_M"],
         "Prime pure Couche 2 (MEUR)": synth_pareto["prime_pure_2_2024_M"]},
    ])
    print(table.round(3).to_string(index=False))

    # -- 2. Volatilité historique (sigma de la charge annuelle indexée) -------
    df_paie = pd.read_csv(OUT_DIR / "triangle_paiements.csv")
    # Charge annuelle par couche, indexée (méthode B)
    df = sin_indexes.copy()
    df["cout_1"] = df["incurred_indexe"].apply(
        lambda x: min(PORTEE_1, max(x - PRIORITE_1, 0)))
    df["cout_2"] = df["incurred_indexe"].apply(
        lambda x: min(PORTEE_2, max(x - PRIORITE_2, 0)))
    charges_ann = (df.groupby("annee_surv")[["cout_1", "cout_2"]]
                     .sum().reindex(annees_histo, fill_value=0))
    print("\n=== Charge annuelle indexée par couche (MEUR) ===")
    print((charges_ann/1e6).round(3).to_string())

    mu_1, sigma_1 = charges_ann["cout_1"].mean(), charges_ann["cout_1"].std(ddof=1)
    mu_2, sigma_2 = charges_ann["cout_2"].mean(), charges_ann["cout_2"].std(ddof=1)
    cv_1 = sigma_1 / mu_1 if mu_1 > 0 else np.nan
    cv_2 = sigma_2 / mu_2 if mu_2 > 0 else np.nan
    print(f"\nCouche 1 - moyenne={mu_1/1e6:.3f} M, sigma={sigma_1/1e6:.3f} M, CV={cv_1:.2%}")
    print(f"Couche 2 - moyenne={mu_2/1e6:.3f} M, sigma={sigma_2/1e6:.3f} M, CV={cv_2:.2%}")

    # -- 3. Bootstrap pour distribution empirique ----------------------------
    boot_1 = bootstrap_charge_annuelle(sin_indexes, PRIORITE_1, PORTEE_1, annees_histo)
    boot_2 = bootstrap_charge_annuelle(sin_indexes, PRIORITE_2, PORTEE_2, annees_histo)
    q50_1, q75_1, q90_1, q99_1 = np.quantile(boot_1, [0.5, 0.75, 0.90, 0.99])
    q50_2, q75_2, q90_2, q99_2 = np.quantile(boot_2, [0.5, 0.75, 0.90, 0.99])
    print(f"\nBootstrap Couche 1 : médiane={q50_1/1e6:.2f} M, Q75={q75_1/1e6:.2f}, "
          f"Q90={q90_1/1e6:.2f}, Q99={q99_1/1e6:.2f}")
    print(f"Bootstrap Couche 2 : médiane={q50_2/1e6:.2f} M, Q75={q75_2/1e6:.2f}, "
          f"Q90={q90_2/1e6:.2f}, Q99={q99_2/1e6:.2f}")

    # -- 4. Prime technique avec chargement de sécurité ----------------------
    # Comme la sinistralité indexée est exprimée en €2024 et que la prime 2024
    # est aussi en €2024, on peut directement appliquer.
    prime_2024 = 229_690_344.58

    # Prime pure de référence (méthode B)
    pp_1 = ref["prime_pure_couche_1"]
    pp_2 = ref["prime_pure_couche_2"]

    # Chargement de sécurité : k * sigma sur la base de la charge annuelle indexée
    chargement_secu_1 = K_ECART_TYPE * sigma_1
    chargement_secu_2 = K_ECART_TYPE * sigma_2

    # Prime technique (avant frais)
    prime_technique_1 = pp_1 + chargement_secu_1
    prime_technique_2 = pp_2 + chargement_secu_2

    # Prime commerciale = (Prime technique + coût du capital) / (1 - frais)
    # On approxime le coût du capital par 6 % de la prime technique (proxy SCR)
    cout_capital_1 = COUT_CAPITAL_AP * prime_technique_1
    cout_capital_2 = COUT_CAPITAL_AP * prime_technique_2
    prime_brute_1 = prime_technique_1 + cout_capital_1
    prime_brute_2 = prime_technique_2 + cout_capital_2
    prime_commerciale_1 = prime_brute_1 / (1 - FRAIS_GESTION)
    prime_commerciale_2 = prime_brute_2 / (1 - FRAIS_GESTION)

    # Taux de prime (% prime cédante)
    taux_pc_1 = prime_commerciale_1 / prime_2024
    taux_pc_2 = prime_commerciale_2 / prime_2024

    print("\n=== Construction de la prime commerciale (réf : méthode B) ===")
    syn = pd.DataFrame([
        {"poste": "Prime pure", "Couche 1": pp_1, "Couche 2": pp_2},
        {"poste": f"+ Chargement sécurité ({K_ECART_TYPE} * sigma)",
         "Couche 1": chargement_secu_1, "Couche 2": chargement_secu_2},
        {"poste": "= Prime technique", "Couche 1": prime_technique_1, "Couche 2": prime_technique_2},
        {"poste": f"+ Coût du capital ({int(COUT_CAPITAL_AP*100)}%)",
         "Couche 1": cout_capital_1, "Couche 2": cout_capital_2},
        {"poste": "= Prime brute", "Couche 1": prime_brute_1, "Couche 2": prime_brute_2},
        {"poste": f"/ (1 - frais {int(FRAIS_GESTION*100)}%)",
         "Couche 1": prime_commerciale_1, "Couche 2": prime_commerciale_2},
        {"poste": "= PRIME COMMERCIALE", "Couche 1": prime_commerciale_1, "Couche 2": prime_commerciale_2},
    ])
    syn_show = syn.copy()
    syn_show["Couche 1"] = (syn_show["Couche 1"]/1e6).round(3).astype(str) + " M€"
    syn_show["Couche 2"] = (syn_show["Couche 2"]/1e6).round(3).astype(str) + " M€"
    print(syn_show.to_string(index=False))
    print(f"\nTaux de prime commerciale Couche 1 : {taux_pc_1*100:.3f} % de la prime cédante")
    print(f"Taux de prime commerciale Couche 2 : {taux_pc_2*100:.3f} % de la prime cédante")

    # -- 5. Sauvegarde ------------------------------------------------------
    table.to_csv(OUT_DIR / "comparaison_methodes_primes.csv", index=False)
    syn.to_csv(OUT_DIR / "construction_prime_commerciale.csv", index=False)
    pd.DataFrame([{
        "methode_reference": METHODE_REF,
        "prime_pure_couche_1": pp_1,
        "prime_pure_couche_2": pp_2,
        "sigma_couche_1": sigma_1,
        "sigma_couche_2": sigma_2,
        "k_ecart_type": K_ECART_TYPE,
        "frais_gestion": FRAIS_GESTION,
        "cout_capital": COUT_CAPITAL_AP,
        "prime_commerciale_couche_1": prime_commerciale_1,
        "prime_commerciale_couche_2": prime_commerciale_2,
        "taux_prime_couche_1_pct": taux_pc_1*100,
        "taux_prime_couche_2_pct": taux_pc_2*100,
    }]).to_csv(OUT_DIR / "prime_commerciale_finale.csv", index=False)

    # Pas de bootstrap dans la prime mais on sauvegarde la distribution
    pd.DataFrame({"boot_couche_1": boot_1, "boot_couche_2": boot_2}
                ).to_csv(OUT_DIR / "bootstrap_charges.csv", index=False)


if __name__ == "__main__":
    main()
