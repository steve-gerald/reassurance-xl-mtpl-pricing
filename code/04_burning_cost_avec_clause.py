"""
Script 4 / 7 : Burning Cost AVEC clause de stabilité
----------------------------------------------------

Principe de la « clause de stabilité » (indexation des priorités et limites) :
    Sans clause, les seuils 2 M€ / 10 M€ sont fixés en € 2024. Or les sinistres
    historiques 2014-2023 sont libellés en € de leur année de survenance. Pour
    estimer correctement la prime pure 2024, on revalorise les coûts au même
    référentiel monétaire que les seuils (méthode dite « as-if loss costing »).

Indice d'inflation des sinistres : CPI + 1% superimposed (taux fournis par la
cédante). Le « superimposed » de 1 %/an traduit l'inflation propre à l'activité
sinistre (frais médicaux, judiciaires, etc.).

Deux méthodes implémentées :
    A) « As-if » simple : on indexe directement l'incurred ultime de la date
       de survenance vers 2024 par le facteur d'inflation cumulé.
    B) « Indexation par paiement » : pour chaque sinistre, on revalorise chaque
       paiement incrémental à la date à laquelle il est effectivement versé.
       Cette méthode est plus fine et reflète mieux la déformation temporelle
       réelle des flux. Elle est plus exigeante mais conceptuellement préférable.

La prime émise historique est elle aussi revalorisée pour rester cohérente.
"""

from pathlib import Path
import pandas as pd
import numpy as np

PROJECT_DIR = Path(__file__).resolve().parent.parent
OUT_DIR = PROJECT_DIR / "outputs"

PRIORITE_1, PORTEE_1 = 2_000_000, 8_000_000
PRIORITE_2, PORTEE_2 = 10_000_000, 20_000_000
ANNEE_TRAITE = 2024

# -----------------------------------------------------------------------------
# 1. Construction de l'indice d'inflation des sinistres
# -----------------------------------------------------------------------------
# Taux d'inflation CPI historiques (2014 -> 2024) extraits de l'énoncé.
# Le taux à l'indice i correspond à l'inflation observée entre (2013+i) et (2014+i).
CPI_HISTO = {
    2015: 0.0034,
    2016: 0.0056,
    2017: 0.0197,
    2018: 0.0213,
    2019: 0.0205,
    2020: 0.0144,
    2021: 0.0074,
    2022: 0.0244,
    2023: 0.0959,
    2024: 0.04366,
}
SUPERIMPOSED = 0.01    # 1 % par an


def construire_indice_inflation(cpi: dict, superimposed: float,
                                base_annee: int = 2014) -> pd.Series:
    """Construit l'indice d'inflation cumulée (base 100 en base_annee)."""
    annees = [base_annee] + sorted(cpi.keys())
    valeurs = [100.0]
    for an in sorted(cpi.keys()):
        taux = cpi[an] + superimposed
        valeurs.append(valeurs[-1] * (1 + taux))
    return pd.Series(valeurs, index=annees, name="indice")


indice = construire_indice_inflation(CPI_HISTO, SUPERIMPOSED)
print("Indice d'inflation des sinistres (base 100 en 2014, CPI + 1% superimposed) :")
print(indice.round(3).to_string())
print(f"\nFacteur cumulé 2014 -> 2024 = {indice[2024]/indice[2014]:.4f}")

indice.to_csv(OUT_DIR / "indice_inflation.csv", header=True)


# -----------------------------------------------------------------------------
# 2. Chargement
# -----------------------------------------------------------------------------
df_sin  = pd.read_csv(OUT_DIR / "sinistres.csv")
df_expo = pd.read_csv(OUT_DIR / "exposition.csv")
df_paie = pd.read_csv(OUT_DIR / "triangle_paiements.csv")
df_prov = pd.read_csv(OUT_DIR / "triangle_provisions.csv")


def cout_couche(incurred: float, priorite: float, portee: float) -> float:
    return min(portee, max(incurred - priorite, 0.0))


# -----------------------------------------------------------------------------
# 3. Méthode A : as-if simple
# -----------------------------------------------------------------------------
def methode_as_if_simple(df_sin: pd.DataFrame,
                         df_expo: pd.DataFrame,
                         indice: pd.Series) -> dict:
    df = df_sin.copy()
    df["facteur"] = df["annee_surv"].map(lambda a: indice[ANNEE_TRAITE] / indice[a])
    df["incurred_indexe"] = df["incurred"] * df["facteur"]
    df["cout_1"] = df["incurred_indexe"].apply(lambda x: cout_couche(x, PRIORITE_1, PORTEE_1))
    df["cout_2"] = df["incurred_indexe"].apply(lambda x: cout_couche(x, PRIORITE_2, PORTEE_2))

    bc = (df.groupby("annee_surv")
            .agg(nb_sin=("id_sinistre", "count"),
                 cout_1=("cout_1", "sum"),
                 cout_2=("cout_2", "sum"))
            .reset_index())

    expo = df_expo.copy()
    expo["facteur"] = expo["annee"].map(lambda a: indice[ANNEE_TRAITE] / indice[a])
    expo["prime_indexee"] = expo["prime"] * expo["facteur"]
    bc = bc.merge(expo[["annee", "prime", "prime_indexee"]],
                  left_on="annee_surv", right_on="annee").drop(columns=["annee"])

    total_c1, total_c2 = bc["cout_1"].sum(), bc["cout_2"].sum()
    total_p = bc["prime_indexee"].sum()
    bc_1 = total_c1 / total_p
    bc_2 = total_c2 / total_p

    prime_2024 = float(df_expo.loc[df_expo["annee"] == ANNEE_TRAITE, "prime"].iloc[0])
    return {"bc_annuel": bc,
            "bc_1": bc_1, "bc_2": bc_2,
            "prime_pure_1": bc_1 * prime_2024,
            "prime_pure_2": bc_2 * prime_2024,
            "sinistralite_1": total_c1,
            "sinistralite_2": total_c2,
            "prime_indexee_totale": total_p}


# -----------------------------------------------------------------------------
# 4. Méthode B : indexation par paiement
# -----------------------------------------------------------------------------
def methode_par_paiement(df_paie: pd.DataFrame,
                         df_prov: pd.DataFrame,
                         df_expo: pd.DataFrame,
                         indice: pd.Series) -> dict:
    df = df_paie.sort_values(["id_sinistre", "dev"]).copy()
    df["paiement_incr"] = (df.groupby("id_sinistre")["paiement"]
                             .diff().fillna(df["paiement"]))
    df.loc[df["paiement_incr"] < 0, "paiement_incr"] = 0.0
    df["annee_paie"] = df["annee_surv"] + df["dev"]
    df["facteur"] = df["annee_paie"].map(lambda a: indice[ANNEE_TRAITE] / indice[a]
                                          if a in indice.index else np.nan)
    df["paiement_indexe"] = df["paiement_incr"] * df["facteur"]

    paie_indexe = (df.groupby(["id_sinistre", "annee_surv"])["paiement_indexe"]
                     .sum()
                     .reset_index()
                     .rename(columns={"paiement_indexe": "paiement_indexe_total"}))

    prov_last = (df_prov.sort_values(["id_sinistre", "dev"])
                       .groupby("id_sinistre")
                       .tail(1)
                       .copy())
    prov_last["annee_arret"] = prov_last["annee_surv"] + prov_last["dev"]
    prov_last["facteur"] = prov_last["annee_arret"].map(
        lambda a: indice[ANNEE_TRAITE] / indice[a] if a in indice.index else np.nan)
    prov_last["provision_indexee"] = prov_last["provision"] * prov_last["facteur"]

    df_sin = paie_indexe.merge(
        prov_last[["id_sinistre", "provision_indexee"]],
        on="id_sinistre", how="left").fillna(0.0)
    df_sin["incurred_indexe"] = df_sin["paiement_indexe_total"] + df_sin["provision_indexee"]

    df_sin["cout_1"] = df_sin["incurred_indexe"].apply(
        lambda x: cout_couche(x, PRIORITE_1, PORTEE_1))
    df_sin["cout_2"] = df_sin["incurred_indexe"].apply(
        lambda x: cout_couche(x, PRIORITE_2, PORTEE_2))

    bc = (df_sin.groupby("annee_surv")
                .agg(nb_sin=("id_sinistre", "count"),
                     cout_1=("cout_1", "sum"),
                     cout_2=("cout_2", "sum"))
                .reset_index())

    expo = df_expo.copy()
    expo["facteur"] = expo["annee"].map(lambda a: indice[ANNEE_TRAITE] / indice[a])
    expo["prime_indexee"] = expo["prime"] * expo["facteur"]
    bc = bc.merge(expo[["annee", "prime", "prime_indexee"]],
                  left_on="annee_surv", right_on="annee").drop(columns=["annee"])

    total_c1, total_c2 = bc["cout_1"].sum(), bc["cout_2"].sum()
    total_p = bc["prime_indexee"].sum()
    bc_1 = total_c1 / total_p
    bc_2 = total_c2 / total_p

    prime_2024 = float(df_expo.loc[df_expo["annee"] == ANNEE_TRAITE, "prime"].iloc[0])
    return {"bc_annuel": bc,
            "df_sin_indexe": df_sin,
            "bc_1": bc_1, "bc_2": bc_2,
            "prime_pure_1": bc_1 * prime_2024,
            "prime_pure_2": bc_2 * prime_2024,
            "sinistralite_1": total_c1,
            "sinistralite_2": total_c2,
            "prime_indexee_totale": total_p}


# -----------------------------------------------------------------------------
# 5. Affichage et sauvegarde
# -----------------------------------------------------------------------------
def afficher(nom: str, res: dict):
    print(f"\n=== Methode '{nom}' ===")
    d = res["bc_annuel"].copy()
    d["cout_1_Meuro"] = (d["cout_1"]/1e6).round(3)
    d["cout_2_Meuro"] = (d["cout_2"]/1e6).round(3)
    d["prime_indexee_Meuro"] = (d["prime_indexee"]/1e6).round(2)
    d["BC_1_pct"] = (d["cout_1"]/d["prime_indexee"]*100).round(3)
    d["BC_2_pct"] = (d["cout_2"]/d["prime_indexee"]*100).round(3)
    print(d[["annee_surv", "nb_sin", "cout_1_Meuro", "cout_2_Meuro",
             "prime_indexee_Meuro", "BC_1_pct", "BC_2_pct"]].to_string(index=False))
    print(f"BC Couche 1 = {res['bc_1']*100:.4f} %")
    print(f"BC Couche 2 = {res['bc_2']*100:.4f} %")
    print(f"Prime pure 2024 Couche 1 = {res['prime_pure_1']/1e6:.4f} M EUR")
    print(f"Prime pure 2024 Couche 2 = {res['prime_pure_2']/1e6:.4f} M EUR")


if __name__ == "__main__":
    # Scenario principal : 1 % de superimposed
    res_A = methode_as_if_simple(df_sin, df_expo, indice)
    res_B = methode_par_paiement(df_paie, df_prov, df_expo, indice)
    afficher("A - As-if simple (incurred indexe), 1 pct superimposed", res_A)
    afficher("B - Indexation par paiement, 1 pct superimposed", res_B)

    # Sensibilite : sans superimposed (typo du classeur)
    indice_sansSup = construire_indice_inflation(CPI_HISTO, 0.0001)
    res_A_sans = methode_as_if_simple(df_sin, df_expo, indice_sansSup)
    res_B_sans = methode_par_paiement(df_paie, df_prov, df_expo, indice_sansSup)
    afficher("A - reconciliation Excel (superimposed=0.01 pct)", res_A_sans)
    afficher("B - reconciliation Excel (superimposed=0.01 pct)", res_B_sans)

    # Sauvegarde
    res_A["bc_annuel"].to_csv(OUT_DIR / "bc_avec_clause_methode_A.csv", index=False)
    res_B["bc_annuel"].to_csv(OUT_DIR / "bc_avec_clause_methode_B.csv", index=False)
    res_B["df_sin_indexe"].to_csv(OUT_DIR / "sinistres_indexes.csv", index=False)

    synth = pd.DataFrame([
        {"methode": "A - As-if simple (1 pct sup.)",
         "bc_couche_1": res_A["bc_1"], "bc_couche_2": res_A["bc_2"],
         "prime_pure_couche_1": res_A["prime_pure_1"],
         "prime_pure_couche_2": res_A["prime_pure_2"]},
        {"methode": "B - Indexation par paiement (1 pct sup.)",
         "bc_couche_1": res_B["bc_1"], "bc_couche_2": res_B["bc_2"],
         "prime_pure_couche_1": res_B["prime_pure_1"],
         "prime_pure_couche_2": res_B["prime_pure_2"]},
        {"methode": "A - As-if simple (reconciliation Excel)",
         "bc_couche_1": res_A_sans["bc_1"], "bc_couche_2": res_A_sans["bc_2"],
         "prime_pure_couche_1": res_A_sans["prime_pure_1"],
         "prime_pure_couche_2": res_A_sans["prime_pure_2"]},
        {"methode": "B - Indexation par paiement (reconciliation Excel)",
         "bc_couche_1": res_B_sans["bc_1"], "bc_couche_2": res_B_sans["bc_2"],
         "prime_pure_couche_1": res_B_sans["prime_pure_1"],
         "prime_pure_couche_2": res_B_sans["prime_pure_2"]},
    ])
    synth.to_csv(OUT_DIR / "synthese_avec_clause.csv", index=False)
    print("\nSynthese sauvegardee dans:", OUT_DIR / "synthese_avec_clause.csv")
