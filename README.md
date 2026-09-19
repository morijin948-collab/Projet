# Gestionnaire de Fournitures Scolaires 2026-2027 — Guide de démarrage

## Installation
```
pip install -r requirements.txt
```

## Lancement
```
streamlit run gestionnaire_fournitures_scolaires.py
```
Cela ouvre l'application dans votre navigateur (http://localhost:8501).

## Première utilisation
1. À l'ouverture, comme aucun compte n'existe encore, créez le compte administrateur (nom d'utilisateur + mot de passe + confirmation).
2. Connectez-vous ensuite avec ces identifiants.
3. (Optionnel) Allez dans **Achats** pour créer un achat numéroté (numéro automatique, date, note) — utile pour regrouper les articles d'une même facture/livraison.
4. Allez dans **Catégories** pour créer vos classeurs (ex : Cahiers, Stylos, Livres...).
5. Allez dans **Articles** pour ajouter les fournitures (nom, quantité, prix d'achat unitaire, prix de vente unitaire), en les rattachant si besoin à un n° d'achat : tous les totaux et bénéfices se calculent automatiquement. Vous pouvez aussi modifier ou supprimer un article à tout moment (nom, quantité, prix, achat rattaché).
6. Consultez l'onglet **Statistiques** pour voir les totaux par catégorie, par achat, le classement des articles les plus rentables, la marge globale et le résumé des impayés.
7. Utilisez l'onglet **Impayés** pour enregistrer un client qui doit encore payer (montant dû, article concerné en option), puis ajoutez ses paiements au fil du temps : le reste à payer et le statut (Payé / Partiel / Impayé) se recalculent automatiquement, avec l'historique détaillé de chaque paiement.

## Données
Toutes les données sont enregistrées automatiquement dans un fichier `navaro_yacouba.db` (base SQLite) créé à côté du script — vos catégories, articles, achats et impayés restent donc sauvegardés d'une session à l'autre.
