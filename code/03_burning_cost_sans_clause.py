"""
Script 3 / 7 : Burning Cost SANS clause de stabilité
----------------------------------------------------

Méthodologie :
  1. Pour chaque sinistre, on prend l'incurred ultime observé (paiement + provisions
     à la date d'arrêté). Aucune indexation appliquée : on travaille en € courants.
  2. On applique les couches XL :
       Couche 1 :  cout_1 = min(8M ; max(incurred - 2M ; 0))
       Couche 2 :  cout_2 = min(20M ; max(incurred - 10M ; 0))
  3. On agrège les coûts par année de survenance, on divise par la prime
     émise de cette année => Burning Cost annuel.
  4. Le BC moyen historique est appliqué à la prime estimée 2024 pour
     obtenir la prime pure de réassurance.

Cette première méthode est connue sous le nom de "Burning Cost à prix courants"
ou "Pure Burning Cost". Elle ne corrige pas l'évolution du coût des sinistres :
elle sous-estime la sinistralité future lorsque l'inflation est positive
(ce qui sera corrigé dans le script suivant via la "clause de stabilité").

Sortie : tableau récapitulatif + prime pure pour 2024.
"""

from pathlib import Path
import pandas as pd
import numpy as np

PROJECT_DIR = Path(__file__).resolve().parent.parent
OUT_DIR = PROJECT_DIR / "outputs"

PRIORITE_1, PORTEE_1 = 2_000_000, 8_000_000     # Couche 1 : 8 XS 2
PRIORITE_2, PORTEE_2 = 10_000_000, 20_000_000   # Couche 2 : 20 XS 10
ANNEE_TRAITE = 2024


def cout_couche(incurred: float, priorite: float, portee: float) -> float:
    """Coût d'un sinistre dans une couche XL : min(portée ; max(S - priorité ; 0))."""
    return min(portee, max(incurred - priorite, 0.0))


def main():
    df_sin  = pd.read_csv(OUT_DIR / "sinistres.csv")
    df_expo = pd.read_csv(OUT_DIR / "exposition.csv")

    # Coût par sinistre dans chaque couche
    df_sin["cout_couche_1"] = df_sin["incurred"].apply(
        lambda x: cout_couche(x, PRIORITE_1, PORTEE_1))
    df_sin["cout_couche_2"] = df_sin["incurred"].apply(
        lambda x: cout_couche(x, PRIORITE_2, PORTEE_2))

    # Agrégation par année de survenance
    bc = (df_sin.groupby("annee_surv")
                .agg(nb_sin=("id_sinistre", "count"),
                     cout_1=("cout_couche_1", "sum"),
                     cout_2=("cout_couche_2", "sum"))
                .reset_index())
    bc = bc.merge(df_expo[["annee", "prime"]],
                  left_on="annee_surv", right_on="annee", how="left")
    bc.drop(columns=["annee"], inplace=True)

    # Burning cost annuel
    bc["BC_1"] = bc["cout_1"] / bc["prime"]
    bc["BC_2"] = bc["cout_2"] / bc["prime"]

    # Burning cost moyen pondéré (toutes années)
    total_cout_1 = bc["cout_1"].sum()
    total_cout_2 = bc["cout_2"].sum()
    total_prime  = bc["prime"].sum()
    bc_moy_1 = total_cout_1 / total_prime
    bc_moy_2 = total_cout_2 / total_prime

    # Prime 2024 estimée
    prime_2024 = float(df_expo.loc[df_expo["annee"] == ANNEE_TRAITE, "prime"].iloc[0])
    prime_pure_1 = bc_moy_1 * prime_2024
    prime_pure_2 = bc_moy_2 * prime_2024

    # Affichage
    print("\n=== Burning Cost SANS clause de stabilité ===")
    bc_display = bc.copy()
    bc_display["cout_1_M€"] = (bc_display["cout_1"] / 1e6).round(3)
    bc_display["cout_2_M€"] = (bc_display["cout_2"] / 1e6).round(3)
    bc_display["prime_M€"]  = (bc_display["prime"] / 1e6).round(2)
    bc_display["BC_1_%"]    = (bc_display["BC_1"] * 100).round(3)
    bc_display["BC_2_%"]    = (bc_display["BC_2"] * 100).round(3)
    print(bc_display[["annee_surv", "nb_sin",
                      "cout_1_M€", "cout_2_M€", "prime_M€",
                      "BC_1_%", "BC_2_%"]].to_string(index=False))

    print("\n--- Totaux historiques ---")
    print(f"Sinistralité Couche 1 totale : {total_cout_1/1e6:.3f} M€")
    print(f"Sinistralité Couche 2 totale : {total_cout_2/1e6:.3f} M€")
    print(f"Prime totale 2014-2023       : {total_prime/1e6:.3f} M€")

    print("\n--- Burning Cost moyen (pondéré par les primes) ---")
    print(f"BC Couche 1 = {bc_moy_1*100:.4f} % = {bc_moy_1:.6f}")
    print(f"BC Couche 2 = {bc_moy_2*100:.4f} % = {bc_moy_2:.6f}")

    print("\n--- Prime pure de réassurance 2024 (sans clause de stabilité) ---")
    print(f"Prime estimée 2024           : {prime_2024/1e6:.3f} M€")
    print(f"Prime pure XL Couche 1       : {prime_pure_1/1e6:.4f} M€")
    print(f"Prime pure XL Couche 2       : {prime_pure_2/1e6:.4f} M€")

    # Sauvegarde
    bc.to_csv(OUT_DIR / "bc_sans_clause.csv", index=False)
    pd.DataFrame([{
        "methode": "sans clause de stabilité",
        "bc_couche_1": bc_moy_1,
        "bc_couche_2": bc_moy_2,
        "prime_2024":   prime_2024,
        "prime_pure_couche_1": prime_pure_1,
        "prime_pure_couche_2": prime_pure_2,
        "sinistralite_couche_1": total_cout_1,
        "sinistralite_couche_2": total_cout_2,
        "prime_historique_totale": total_prime,
    }]).to_csv(OUT_DIR / "synthese_sans_clause.csv", index=False)

    return bc_moy_1, bc_moy_2, prime_pure_1, prime_pure_2


if __name__ == "__main__":
    main()
