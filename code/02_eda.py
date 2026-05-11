"""
Script 2 / 7 : Analyse exploratoire de la sinistralité
------------------------------------------------------

Objectifs :
  - statistiques par année de survenance ;
  - distribution des incurred ;
  - identification des sinistres dépassant les priorités (2 M€ et 10 M€) ;
  - graphique de développement des sinistres.

Tous les graphiques sont sauvegardés dans le dossier `figures`.
"""

from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")  # backend non-interactif
import matplotlib.pyplot as plt

PROJECT_DIR = Path(__file__).resolve().parent.parent
OUT_DIR     = PROJECT_DIR / "outputs"
FIG_DIR     = PROJECT_DIR / "figures"
FIG_DIR.mkdir(exist_ok=True)

PRIORITE_1 = 2_000_000
PRIORITE_2 = 10_000_000

df_expo = pd.read_csv(OUT_DIR / "exposition.csv")
df_sin  = pd.read_csv(OUT_DIR / "sinistres.csv")
df_paie = pd.read_csv(OUT_DIR / "triangle_paiements.csv")

# ----- 1. Statistiques par année ----------------------------------------------
stats = (df_sin.groupby("annee_surv")
              .agg(nb_sin=("id_sinistre", "count"),
                   incurred_total=("incurred", "sum"),
                   incurred_moy=("incurred", "mean"),
                   incurred_med=("incurred", "median"),
                   incurred_max=("incurred", "max"))
              .reset_index())

# Fusion avec l'exposition pour calculer la fréquence et le coût moyen
stats = stats.merge(df_expo[["annee", "prime", "nb_risques"]],
                    left_on="annee_surv", right_on="annee", how="left")
stats["frequence_pct"]    = 100 * stats["nb_sin"] / stats["nb_risques"]
stats["S_sur_P_pct"]      = 100 * stats["incurred_total"] / stats["prime"]
stats["sinistre_moyen_M"] = stats["incurred_moy"] / 1e6
stats.drop(columns=["annee"], inplace=True)

stats_round = stats.copy()
for c in ["incurred_total", "incurred_moy", "incurred_med", "incurred_max"]:
    stats_round[c] = (stats_round[c] / 1e6).round(2)
stats_round["prime"] = (stats_round["prime"] / 1e6).round(2)
print("\n=== Statistiques par année de survenance (montants en M€) ===")
print(stats_round.to_string(index=False))

stats.to_csv(OUT_DIR / "stats_par_annee.csv", index=False)

# ----- 2. Distribution des incurred -------------------------------------------
plt.figure(figsize=(8, 4))
plt.hist(df_sin["incurred"] / 1e6, bins=40, edgecolor="black", color="#4f8")
plt.axvline(PRIORITE_1 / 1e6, color="red", ls="--", label="Priorité 1 = 2 M€")
plt.axvline(PRIORITE_2 / 1e6, color="purple", ls="--", label="Priorité 2 = 10 M€")
plt.xlabel("Incurred ultime observé (M€)")
plt.ylabel("Nombre de sinistres")
plt.title("Distribution des sinistres incurred ultime (2014-2023)")
plt.legend()
plt.tight_layout()
plt.savefig(FIG_DIR / "distribution_incurred.png", dpi=140)
plt.close()

# Echelle log (utile car forte asymétrie)
plt.figure(figsize=(8, 4))
data_log = np.log10(df_sin["incurred"].clip(lower=1) / 1e3)  # en milliers
plt.hist(data_log, bins=30, edgecolor="black", color="#88f")
plt.xlabel("log10(incurred en milliers d'€)")
plt.ylabel("Nombre de sinistres")
plt.title("Distribution log des incurred")
plt.tight_layout()
plt.savefig(FIG_DIR / "distribution_incurred_log.png", dpi=140)
plt.close()

# ----- 3. Sinistres dépassant les priorités -----------------------------------
sin_xs1 = df_sin[df_sin["incurred"] > PRIORITE_1].copy()
sin_xs2 = df_sin[df_sin["incurred"] > PRIORITE_2].copy()

print(f"\n--- Sinistres au-dessus de la priorité Couche 1 (2 M€) ---")
print(f"Nombre : {len(sin_xs1)} sur {len(df_sin)} ({100*len(sin_xs1)/len(df_sin):.1f}%)")

print(f"\n--- Sinistres au-dessus de la priorité Couche 2 (10 M€) ---")
print(f"Nombre : {len(sin_xs2)}")
if len(sin_xs2) > 0:
    print(sin_xs2[["id_sinistre", "annee_surv", "incurred"]]
          .assign(incurred_M=lambda d: (d["incurred"]/1e6).round(2))
          .drop(columns="incurred")
          .to_string(index=False))

sin_xs1.to_csv(OUT_DIR / "sinistres_au_dessus_priorite1.csv", index=False)

# ----- 4. Courbes de développement (chain) ------------------------------------
# On agrège les paiements cumulés par (annee_surv, dev) pour tracer la vitesse
# de paiement
dev_curve = (df_paie.groupby(["annee_surv", "dev"])["paiement"]
                   .sum()
                   .reset_index())
plt.figure(figsize=(9, 5))
for ann, g in dev_curve.groupby("annee_surv"):
    plt.plot(g["dev"], g["paiement"]/1e6, marker="o", label=str(ann))
plt.xlabel("Année de développement (0 = année de survenance)")
plt.ylabel("Paiements cumulés (M€)")
plt.title("Cadence de paiement par année de survenance")
plt.legend(ncol=2, fontsize=8)
plt.grid(alpha=0.3)
plt.tight_layout()
plt.savefig(FIG_DIR / "cadence_paiements.png", dpi=140)
plt.close()

# ----- 5. Synthèse des montants annuels ---------------------------------------
plt.figure(figsize=(9, 4))
plt.bar(stats["annee_surv"], stats["incurred_total"]/1e6, color="#48c", label="Incurred total")
plt.plot(stats["annee_surv"], stats["prime"]/1e6*0.05, color="red", marker="o",
         label="5% de la prime émise")
plt.xlabel("Année de survenance")
plt.ylabel("M€")
plt.title("Sinistralité totale vs 5% de la prime émise")
plt.legend()
plt.tight_layout()
plt.savefig(FIG_DIR / "incurred_vs_prime.png", dpi=140)
plt.close()

print("\nGraphiques sauvegardés dans :", FIG_DIR)
