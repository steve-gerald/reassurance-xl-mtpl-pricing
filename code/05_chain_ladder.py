"""
Script 5 / 7 : Chain-Ladder pour valider les charges ultimes
------------------------------------------------------------

Objectif : utiliser la méthode de Chain-Ladder déterministe sur le triangle
agrégé des paiements cumulés (par année de survenance × année de développement)
pour estimer la charge ultime et comparer aux incurred actuels (paiement + provision).

C'est une analyse de cohérence : si l'ultime CL est très différent de l'incurred,
cela peut indiquer un sous- ou sur-provisionnement.

Hypothèses :
  - Les paiements ne sont pas indexés (on travaille en € courants).
  - Le triangle est complété par le développement maximal observé (10 dev).
  - Les facteurs de développement sont calculés sur les valeurs cumulées
    selon la formule classique :
        f_j = sum_i C(i, j+1) / sum_i C(i, j) pour les (i, j) où les deux sont
        observés.
"""

from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

PROJECT_DIR = Path(__file__).resolve().parent.parent
OUT_DIR = PROJECT_DIR / "outputs"
FIG_DIR = PROJECT_DIR / "figures"
FIG_DIR.mkdir(exist_ok=True)


def construire_triangle_agrege(df_paie: pd.DataFrame) -> pd.DataFrame:
    """Triangle agrégé : index = année de survenance, colonnes = dev (0..9)."""
    tri = (df_paie.groupby(["annee_surv", "dev"])["paiement"]
                  .sum()
                  .unstack("dev"))
    return tri.sort_index()


def chain_ladder(triangle: pd.DataFrame) -> dict:
    """
    Méthode Chain-Ladder déterministe.
    Renvoie :
      - facteurs_developpement : f_j (j = 0..max_dev-1)
      - triangle_complet : valeurs cumulées projetées
      - ultime : par année de survenance
    """
    T = triangle.copy().astype(float)
    n_dev = T.shape[1]
    facteurs = []
    for j in range(n_dev - 1):
        # On garde uniquement les (i, j) où C(i, j) ET C(i, j+1) sont observés
        col_j = T.iloc[:, j]
        col_j1 = T.iloc[:, j + 1]
        mask = col_j.notna() & col_j1.notna() & (col_j > 0)
        if mask.sum() == 0:
            facteurs.append(1.0)
            continue
        num = col_j1[mask].sum()
        den = col_j[mask].sum()
        f = num / den
        facteurs.append(f)

    # Complétion du triangle inférieur
    T_full = T.copy()
    for i in T_full.index:
        for j in range(n_dev):
            if pd.isna(T_full.iat[T_full.index.get_loc(i), j]):
                prev = T_full.iat[T_full.index.get_loc(i), j - 1]
                T_full.iat[T_full.index.get_loc(i), j] = prev * facteurs[j - 1]

    ultime = T_full.iloc[:, -1]
    return {"facteurs": facteurs, "triangle_complet": T_full, "ultime": ultime}


def main():
    df_paie = pd.read_csv(OUT_DIR / "triangle_paiements.csv")
    df_sin  = pd.read_csv(OUT_DIR / "sinistres.csv")

    triangle = construire_triangle_agrege(df_paie)
    print("\n=== Triangle agrégé des paiements cumulés (M EUR) ===")
    print((triangle/1e6).round(2).to_string())

    res = chain_ladder(triangle)
    print("\n=== Facteurs de développement (link ratios) ===")
    for j, f in enumerate(res["facteurs"]):
        print(f"  f_{j}->{j+1} = {f:.4f}")
    print(f"  Produit cumulé f_0...f_9 = {np.prod(res['facteurs']):.4f}")

    print("\n=== Triangle complété (M EUR) ===")
    print((res["triangle_complet"]/1e6).round(2).to_string())

    # Comparaison ultime CL vs incurred
    incurred_par_annee = df_sin.groupby("annee_surv")["incurred"].sum()
    comp = pd.DataFrame({
        "ultime_CL": res["ultime"],
        "incurred_observe": incurred_par_annee,
    })
    comp["ecart_pct"] = 100 * (comp["ultime_CL"] - comp["incurred_observe"]) / comp["incurred_observe"]
    print("\n=== Comparaison ultime Chain-Ladder vs incurred observé (M EUR) ===")
    comp_show = comp.copy()
    comp_show["ultime_CL"]        = (comp_show["ultime_CL"]/1e6).round(3)
    comp_show["incurred_observe"] = (comp_show["incurred_observe"]/1e6).round(3)
    comp_show["ecart_pct"]        = comp_show["ecart_pct"].round(1)
    print(comp_show.to_string())

    # Graphique
    plt.figure(figsize=(9, 5))
    x = np.arange(len(comp.index))
    w = 0.35
    plt.bar(x - w/2, comp["incurred_observe"]/1e6, w, label="Incurred observé")
    plt.bar(x + w/2, comp["ultime_CL"]/1e6, w, label="Ultime Chain-Ladder", color="#fa7")
    plt.xticks(x, comp.index)
    plt.xlabel("Année de survenance")
    plt.ylabel("M EUR")
    plt.title("Incurred observé vs ultime Chain-Ladder")
    plt.legend()
    plt.tight_layout()
    plt.savefig(FIG_DIR / "chain_ladder_compare.png", dpi=140)
    plt.close()

    # Sauvegarde
    comp.to_csv(OUT_DIR / "chain_ladder_comparaison.csv")
    pd.DataFrame({"dev": list(range(len(res["facteurs"]))), "facteur": res["facteurs"]}
                 ).to_csv(OUT_DIR / "chain_ladder_facteurs.csv", index=False)
    res["triangle_complet"].to_csv(OUT_DIR / "chain_ladder_triangle_complet.csv")

    print("\n=== Synthèse ===")
    print(f"Ultime total (CL)            : {comp['ultime_CL'].sum()/1e6:.2f} M EUR")
    print(f"Incurred total observé       : {comp['incurred_observe'].sum()/1e6:.2f} M EUR")
    print(f"Ecart                        : {(comp['ultime_CL'].sum()-comp['incurred_observe'].sum())/1e6:.2f} M EUR")


if __name__ == "__main__":
    main()
