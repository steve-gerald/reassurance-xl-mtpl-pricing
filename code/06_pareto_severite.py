"""
Script 6 / 7 : Modélisation Pareto/GPD de la sévérité des sinistres
-------------------------------------------------------------------

Pour la tarification d'un traité XL, le Burning Cost historique peut être
volatile : il ne contient que peu de sinistres importants (44 au-dessus de 2 M€,
2 au-dessus de 10 M€ dans notre portefeuille). On complète donc l'analyse en
ajustant une loi Pareto Type II (= Generalized Pareto Distribution) sur la
queue de distribution.

Cela permet :
  - d'estimer la fréquence et la sévérité conditionnelles au-dessus d'un seuil ;
  - d'évaluer l'espérance d'un sinistre dans une couche [a, a+w] ;
  - d'apporter un point de vue indépendant du burning cost.

On utilise scipy.stats.genpareto. La méthode du maximum de vraisemblance
(MLE) est mise en œuvre.
"""

from pathlib import Path
import pandas as pd
import numpy as np
from scipy import stats
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

PROJECT_DIR = Path(__file__).resolve().parent.parent
OUT_DIR = PROJECT_DIR / "outputs"
FIG_DIR = PROJECT_DIR / "figures"

PRIORITE_1, PORTEE_1 = 2_000_000, 8_000_000
PRIORITE_2, PORTEE_2 = 10_000_000, 20_000_000
ANNEE_TRAITE = 2024


def esperance_couche_pareto(c: float, sigma: float, priorite: float,
                            portee: float, seuil: float) -> float:
    """
    Espérance d'un sinistre dans une couche XL, conditionnelle à X > seuil,
    sous loi GPD(c, sigma) avec excès au-dessus du seuil :
        Y = X - seuil ~ GPD(c, sigma)

    E[ min(portee, max(X - priorite, 0)) | X > seuil ]
    = integrale sur [priorite - seuil, priorite + portee - seuil] de
      F_bar(y) dy   (où F_bar est la fonction de survie du GPD).
    On évalue numériquement.
    """
    a = max(0.0, priorite - seuil)
    b = priorite + portee - seuil
    if b <= a:
        return 0.0

    rv = stats.genpareto(c, loc=0, scale=sigma)
    # E[ min(portée, (X - priorité)^+) | X > seuil ]
    #     = integral_a^b (1 - F(y)) dy
    y_grid = np.linspace(a, b, 2000)
    surv = 1 - rv.cdf(y_grid)
    return np.trapz(surv, y_grid)


def main():
    df_sin = pd.read_csv(OUT_DIR / "sinistres.csv")
    incurred = df_sin["incurred"].values

    # Choix du seuil de modélisation : on prend la priorité de la Couche 1 (2 M)
    seuil = PRIORITE_1
    excedents = incurred[incurred > seuil] - seuil
    print(f"Nombre d'excédents au-dessus de {seuil/1e6:.0f} M EUR : {len(excedents)}")
    print(f"Excédent moyen : {excedents.mean()/1e6:.3f} M EUR")
    print(f"Excédent max   : {excedents.max()/1e6:.3f} M EUR")

    # Ajustement GPD par MLE
    c_mle, loc_mle, sigma_mle = stats.genpareto.fit(excedents, floc=0)
    print(f"\nGPD ajustée (loc=0 forcé) :")
    print(f"  shape c     = {c_mle:.4f}")
    print(f"  scale sigma = {sigma_mle:.0f}")

    # Diagnostic graphique : QQ-plot
    rv = stats.genpareto(c_mle, loc=0, scale=sigma_mle)
    q_emp = np.sort(excedents)
    q_theo = rv.ppf((np.arange(1, len(q_emp)+1) - 0.5) / len(q_emp))
    plt.figure(figsize=(6, 6))
    plt.scatter(q_theo/1e6, q_emp/1e6, alpha=0.7)
    m = max(q_emp.max(), q_theo.max())
    plt.plot([0, m/1e6], [0, m/1e6], "r--")
    plt.xlabel("Quantiles théoriques (M EUR)")
    plt.ylabel("Quantiles empiriques (M EUR)")
    plt.title(f"QQ-plot GPD(c={c_mle:.3f}, sigma={sigma_mle/1e6:.2f}M) - seuil 2M")
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(FIG_DIR / "qqplot_gpd.png", dpi=140)
    plt.close()

    # Fonction de survie empirique vs théorique
    plt.figure(figsize=(8, 5))
    sorted_exc = np.sort(excedents)
    surv_emp = 1 - np.arange(1, len(sorted_exc)+1)/len(sorted_exc)
    x = np.linspace(0, sorted_exc.max()*1.1, 200)
    plt.step(sorted_exc/1e6, surv_emp, where="post", label="Empirique")
    plt.plot(x/1e6, 1 - rv.cdf(x), "r--", label="GPD ajustée")
    plt.yscale("log")
    plt.xlabel("Excédent au-dessus de 2 M EUR")
    plt.ylabel("P(Excédent > x)")
    plt.title("Fonction de survie - excédents > 2 M EUR")
    plt.legend()
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(FIG_DIR / "survie_gpd.png", dpi=140)
    plt.close()

    # Fréquence : nombre d'excédents par année d'exposition (sur la base
    # historique 2014-2023)
    df_expo = pd.read_csv(OUT_DIR / "exposition.csv")
    annees_histo = list(range(2014, 2024))
    nb_excedents = len(excedents)
    annees_hist = len(annees_histo)
    freq_excedents_par_an = nb_excedents / annees_hist
    print(f"\nFréquence moyenne d'excédents au-dessus de {seuil/1e6} M : "
          f"{freq_excedents_par_an:.2f} sinistres/an")

    # Espérance par sinistre dans chaque couche (conditionnelle à X > seuil)
    E_couche_1 = esperance_couche_pareto(c_mle, sigma_mle, PRIORITE_1, PORTEE_1, seuil)
    E_couche_2 = esperance_couche_pareto(c_mle, sigma_mle, PRIORITE_2, PORTEE_2, seuil)
    print(f"\nE[coût Couche 1 | X > 2 M] = {E_couche_1/1e6:.3f} M EUR")
    print(f"E[coût Couche 2 | X > 2 M] = {E_couche_2/1e6:.3f} M EUR")

    # Charge attendue annuelle par couche (Pareto)
    charge_annuelle_1 = freq_excedents_par_an * E_couche_1
    charge_annuelle_2 = freq_excedents_par_an * E_couche_2
    print(f"\nCharge annuelle attendue Couche 1 (modèle Pareto) : {charge_annuelle_1/1e6:.3f} M EUR")
    print(f"Charge annuelle attendue Couche 2 (modèle Pareto) : {charge_annuelle_2/1e6:.3f} M EUR")

    # Ajustement à 2024 : on suppose que la fréquence évolue proportionnellement
    # au nombre de polices, et que la sévérité moyenne a déjà été calibrée sur
    # des sinistres historiques nominaux.
    nb_polices_moyen = df_expo.loc[df_expo["annee"].isin(annees_histo), "nb_risques"].mean()
    nb_polices_2024 = float(df_expo.loc[df_expo["annee"] == ANNEE_TRAITE, "nb_risques"].iloc[0])
    facteur_freq = nb_polices_2024 / nb_polices_moyen
    print(f"\nFacteur fréquence (rapport polices 2024 / moyenne historique) : {facteur_freq:.4f}")
    prime_pure_1_pareto = charge_annuelle_1 * facteur_freq
    prime_pure_2_pareto = charge_annuelle_2 * facteur_freq
    print(f"\nPrime pure 2024 Couche 1 (modèle Pareto) : {prime_pure_1_pareto/1e6:.3f} M EUR")
    print(f"Prime pure 2024 Couche 2 (modèle Pareto) : {prime_pure_2_pareto/1e6:.3f} M EUR")

    # Sauvegarde
    pd.DataFrame([{
        "shape_c": c_mle,
        "scale_sigma": sigma_mle,
        "seuil_M_EUR": seuil/1e6,
        "n_excedents": nb_excedents,
        "frequence_an": freq_excedents_par_an,
        "E_couche_1_par_sin_M": E_couche_1/1e6,
        "E_couche_2_par_sin_M": E_couche_2/1e6,
        "charge_annuelle_1_M": charge_annuelle_1/1e6,
        "charge_annuelle_2_M": charge_annuelle_2/1e6,
        "prime_pure_1_2024_M": prime_pure_1_pareto/1e6,
        "prime_pure_2_2024_M": prime_pure_2_pareto/1e6,
    }]).to_csv(OUT_DIR / "synthese_pareto.csv", index=False)


if __name__ == "__main__":
    main()
