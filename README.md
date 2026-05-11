# Tarification d'un traité XL Motor Third Party Liability

> Devoir de réassurance  ( Pricing Actuary).
> Date : decembre 2025.

Ce projet propose une étude actuarielle complète de tarification d'un traité
de réassurance non-proportionnelle en **Excess of Loss** sur un portefeuille
**RC corporelle automobile** (Motor Third Party Liability).

## Structure du programme étudié

| Couche | Priorité | Portée | Plafond |
|---|---:|---:|---:|
| Couche 1 (Working layer) | 2 000 000 € | 8 000 000 € | 10 000 000 € |
| Couche 2 (Cat layer) | 10 000 000 € | 20 000 000 € | 30 000 000 € |

Date d'effet du traité : **1ᵉʳ janvier 2024**.
Base de données : **10 années** d'historique (2014-2023), **114 sinistres**.

## Méthodologie

L'étude met en parallèle quatre approches actuarielles complémentaires :

1. **Burning Cost classique** (sans clause de stabilité) — référence pédagogique.
2. **Burning Cost avec clause de stabilité (méthode as-if simple)** — l'incurred
   total est revalorisé en € 2024 par le facteur d'inflation cumulé.
3. **Burning Cost avec clause de stabilité (indexation par paiement)** —
   **méthode de référence** : chaque tranche annuelle de paiement est
   revalorisée à la date où elle est versée. Conforme à la pratique courante
   dans les équipes pricing des réassureurs européens.
4. **Modélisation Pareto / GPD de la sévérité** — ajustement par maximum de
   vraisemblance sur les excédents au-dessus de la priorité ; test de cohérence
   fréquence-sévérité.

Une projection **Chain-Ladder** déterministe valide les charges incurred
déclarées par la cédante (écart global : +1,3 %).

## Principaux résultats

|  | Couche 1 (8 XS 2) | Couche 2 (20 XS 10) |
|---|---:|---:|
| Prime pure sans clause | **7,54 M€** (BC = 3,28 %) | **2,04 M€** (BC = 0,89 %) |
| Prime pure avec clause (référence) | **8,71 M€** (BC = 3,79 %) | **2,02 M€** (BC = 0,88 %) |
| **Prime commerciale recommandée** | **11,38 M€ (4,96 %)** | **3,70 M€ (1,61 %)** |

La prime commerciale intègre : chargement de sécurité (k·σ avec k = 0,30),
coût du capital (6 %) et frais de gestion réassureur (5 %).

## Structure du dépôt

```
reassurance/
├── README.md                       ← vous êtes ici
├── requirements.txt                ← dépendances Python
├── code/                           ← scripts numérotés (à exécuter dans l'ordre)
│   ├── 01_chargement_donnees.py
│   ├── 02_eda.py
│   ├── 03_burning_cost_sans_clause.py
│   ├── 04_burning_cost_avec_clause.py
│   ├── 05_chain_ladder.py
│   ├── 06_pareto_severite.py
│   ├── 07_prime_commerciale.py
│   ├── 08_export_excel.py
│   └── 09_rapport_word.py
├── figures/                        ← graphiques PNG produits par 02_eda et 05/06
└── outputs/                        ← CSV intermédiaires + livrables finaux
    ├── Devoir_Reassurance_Rapport_Steve.docx
    ├── Devoir_Reassurance_Rapport_Steve.pdf
    └── Devoir_Reassurance_Rendu_Steve.xlsx
```

## Reproductibilité

```bash
# 1. Installer les dépendances
pip install -r requirements.txt

# 2. Placer le classeur source à la racine
# (fichier `devoir de reassurance1.xlsx` non versionné — voir .gitignore)

# 3. Exécuter les scripts dans l'ordre
cd code
python 01_chargement_donnees.py
python 02_eda.py
python 03_burning_cost_sans_clause.py
python 04_burning_cost_avec_clause.py
python 05_chain_ladder.py
python 06_pareto_severite.py
python 07_prime_commerciale.py
python 08_export_excel.py
python 09_rapport_word.py
```

Tous les chiffres-clés peuvent être recalculés à partir des CSV intermédiaires
dans `outputs/`. Le classeur Excel final contient 93 formules vivantes
(0 erreur après recalcul LibreOffice).

## Cadre déontologique

L'étude respecte les principes du Code de déontologie de l'**Institut des
Actuaires** et du **Code professionnel international (IAA)** :

- Indépendance du jugement actuariel par rapport aux contraintes commerciales.
- Documentation complète des hypothèses et de la méthodologie.
- Discussion explicite des limites du modèle (volume de données limité sur
  Couche 2, hypothèse d'inflation future, dépendance entre sinistres).
- Cohérence des référentiels monétaires (toutes les grandeurs en € 2024 dans
  la méthode de référence).
- Prudence dans l'extrapolation : le modèle Pareto est utilisé en cohérence,
  jamais comme estimation finale, compte tenu du faible nombre d'excédents
  observés sur la Couche 2.

## À propos

Projet réalisé dans le cadre d'un portfolio actuariel destiné à préparer un
entretien pour un poste de **Pricing Actuary** en assurance non-vie.

Toutes les remarques constructives sont les bienvenues.
