"""
Gestionnaire de Fournitures Scolaires 2026-2027
Application de gestion de fournitures scolaires - Année 2026-2027
Auteur : généré avec Claude

Fonctionnalités :
- Compte administrateur (création + connexion avec confirmation de mot de passe)
- Classeur de catégories de fournitures
- Ajout de plusieurs articles (nom, quantité, prix d'achat unitaire, prix de vente unitaire)
- Calcul automatique : total achat, total vente, bénéfice par article
- Totaux par catégorie et totaux généraux (quantités, montants, bénéfices)
- Tableau statistique (marges, articles les plus rentables, etc.)

Lancement :
    pip install streamlit pandas
    streamlit run gestionnaire_fournitures_scolaires.py
"""

import streamlit as st
import pandas as pd
import sqlite3
import hashlib
from datetime import datetime

DB_PATH = "navaro_yacouba.db"

# --------------------------------------------------------------------------------------
# BASE DE DONNÉES
# --------------------------------------------------------------------------------------

def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS admin (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT UNIQUE NOT NULL
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS achats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero INTEGER UNIQUE NOT NULL,
            date_achat TEXT NOT NULL,
            note TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            categorie_id INTEGER NOT NULL,
            achat_id INTEGER,
            nom TEXT NOT NULL,
            quantite REAL NOT NULL,
            prix_achat_unitaire REAL NOT NULL,
            prix_vente_unitaire REAL NOT NULL,
            FOREIGN KEY (categorie_id) REFERENCES categories(id) ON DELETE CASCADE,
            FOREIGN KEY (achat_id) REFERENCES achats(id)
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS impayes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_nom TEXT NOT NULL,
            client_contact TEXT,
            article_id INTEGER,
            montant_total REAL NOT NULL,
            date_creation TEXT NOT NULL,
            note TEXT,
            FOREIGN KEY (article_id) REFERENCES articles(id)
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS paiements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            impaye_id INTEGER NOT NULL,
            montant REAL NOT NULL,
            date_paiement TEXT NOT NULL,
            note TEXT,
            FOREIGN KEY (impaye_id) REFERENCES impayes(id) ON DELETE CASCADE
        )
    """)
    conn.commit()
    # Migration douce : ajoute la colonne achat_id si la base existait déjà sans elle
    try:
        cur.execute("ALTER TABLE articles ADD COLUMN achat_id INTEGER")
        conn.commit()
    except sqlite3.OperationalError:
        pass
    conn.close()


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def admin_exists() -> bool:
    conn = get_conn()
    row = conn.execute("SELECT COUNT(*) FROM admin").fetchone()
    conn.close()
    return row[0] > 0


def create_admin(username: str, password: str) -> tuple[bool, str]:
    conn = get_conn()
    try:
        conn.execute(
            "INSERT INTO admin (username, password_hash, created_at) VALUES (?, ?, ?)",
            (username, hash_password(password), datetime.now().isoformat()),
        )
        conn.commit()
        return True, "Compte administrateur créé avec succès."
    except sqlite3.IntegrityError:
        return False, "Ce nom d'utilisateur existe déjà."
    finally:
        conn.close()


def check_login(username: str, password: str) -> bool:
    conn = get_conn()
    row = conn.execute(
        "SELECT password_hash FROM admin WHERE username = ?", (username,)
    ).fetchone()
    conn.close()
    if row is None:
        return False
    return row[0] == hash_password(password)


def add_category(nom: str) -> tuple[bool, str]:
    conn = get_conn()
    try:
        conn.execute("INSERT INTO categories (nom) VALUES (?)", (nom.strip(),))
        conn.commit()
        return True, "Catégorie ajoutée."
    except sqlite3.IntegrityError:
        return False, "Cette catégorie existe déjà."
    finally:
        conn.close()


def delete_category(cat_id: int):
    conn = get_conn()
    conn.execute("DELETE FROM categories WHERE id = ?", (cat_id,))
    conn.commit()
    conn.close()


def get_categories() -> pd.DataFrame:
    conn = get_conn()
    df = pd.read_sql_query("SELECT * FROM categories ORDER BY nom", conn)
    conn.close()
    return df


def get_next_numero_achat() -> int:
    conn = get_conn()
    row = conn.execute("SELECT MAX(numero) FROM achats").fetchone()
    conn.close()
    return (row[0] or 0) + 1


def create_achat(date_achat: str, note: str = "") -> int:
    conn = get_conn()
    numero = get_next_numero_achat()
    cur = conn.execute(
        "INSERT INTO achats (numero, date_achat, note) VALUES (?, ?, ?)",
        (numero, date_achat, note.strip()),
    )
    conn.commit()
    achat_id = cur.lastrowid
    conn.close()
    return achat_id


def get_achats() -> pd.DataFrame:
    conn = get_conn()
    df = pd.read_sql_query("SELECT * FROM achats ORDER BY numero", conn)
    conn.close()
    return df


def delete_achat(achat_id: int):
    conn = get_conn()
    # On détache d'abord les articles liés pour ne pas les perdre
    conn.execute("UPDATE articles SET achat_id = NULL WHERE achat_id = ?", (achat_id,))
    conn.execute("DELETE FROM achats WHERE id = ?", (achat_id,))
    conn.commit()
    conn.close()


# --------------------------------------------------------------------------------------
# IMPAYÉS
# --------------------------------------------------------------------------------------

def create_impaye(client_nom: str, client_contact: str, article_id, montant_total: float,
                   date_creation: str, note: str = "") -> int:
    conn = get_conn()
    cur = conn.execute(
        """INSERT INTO impayes (client_nom, client_contact, article_id, montant_total, date_creation, note)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (client_nom.strip(), client_contact.strip(), article_id, montant_total, date_creation, note.strip()),
    )
    conn.commit()
    impaye_id = cur.lastrowid
    conn.close()
    return impaye_id


def delete_impaye(impaye_id: int):
    conn = get_conn()
    conn.execute("DELETE FROM paiements WHERE impaye_id = ?", (impaye_id,))
    conn.execute("DELETE FROM impayes WHERE id = ?", (impaye_id,))
    conn.commit()
    conn.close()


def add_paiement(impaye_id: int, montant: float, date_paiement: str, note: str = ""):
    conn = get_conn()
    conn.execute(
        "INSERT INTO paiements (impaye_id, montant, date_paiement, note) VALUES (?, ?, ?, ?)",
        (impaye_id, montant, date_paiement, note.strip()),
    )
    conn.commit()
    conn.close()


def delete_paiement(paiement_id: int):
    conn = get_conn()
    conn.execute("DELETE FROM paiements WHERE id = ?", (paiement_id,))
    conn.commit()
    conn.close()


def get_paiements(impaye_id: int) -> pd.DataFrame:
    conn = get_conn()
    df = pd.read_sql_query(
        "SELECT * FROM paiements WHERE impaye_id = ? ORDER BY date_paiement", conn, params=(impaye_id,)
    )
    conn.close()
    return df


def get_impayes_full() -> pd.DataFrame:
    conn = get_conn()
    df = pd.read_sql_query(
        """
        SELECT i.id, i.client_nom, i.client_contact, i.montant_total, i.date_creation, i.note,
               a.nom AS article_lie
        FROM impayes i
        LEFT JOIN articles a ON i.article_id = a.id
        ORDER BY i.date_creation DESC
        """,
        conn,
    )
    if df.empty:
        conn.close()
        return df
    payes = pd.read_sql_query(
        "SELECT impaye_id, SUM(montant) AS montant_paye FROM paiements GROUP BY impaye_id", conn
    )
    conn.close()
    df = df.merge(payes, left_on="id", right_on="impaye_id", how="left")
    df["montant_paye"] = df["montant_paye"].fillna(0.0)
    df["reste_a_payer"] = df["montant_total"] - df["montant_paye"]

    def statut(row):
        if row["reste_a_payer"] <= 0:
            return "✅ Payé"
        if row["montant_paye"] > 0:
            return "🟠 Partiel"
        return "🔴 Impayé"

    df["statut"] = df.apply(statut, axis=1)
    return df


def add_article(categorie_id: int, nom: str, quantite: float, prix_achat: float,
                 prix_vente: float, achat_id: int | None = None):
    conn = get_conn()
    conn.execute(
        """INSERT INTO articles (categorie_id, achat_id, nom, quantite, prix_achat_unitaire, prix_vente_unitaire)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (categorie_id, achat_id, nom.strip(), quantite, prix_achat, prix_vente),
    )
    conn.commit()
    conn.close()


def delete_article(article_id: int):
    conn = get_conn()
    conn.execute("DELETE FROM articles WHERE id = ?", (article_id,))
    conn.commit()
    conn.close()


def update_article(article_id: int, nom: str, quantite: float, prix_achat: float,
                    prix_vente: float, achat_id: int | None = None):
    conn = get_conn()
    conn.execute(
        """UPDATE articles
           SET nom = ?, quantite = ?, prix_achat_unitaire = ?, prix_vente_unitaire = ?, achat_id = ?
           WHERE id = ?""",
        (nom.strip(), quantite, prix_achat, prix_vente, achat_id, article_id),
    )
    conn.commit()
    conn.close()


def get_article_by_id(article_id: int):
    conn = get_conn()
    row = conn.execute(
        """SELECT id, categorie_id, nom, quantite, prix_achat_unitaire, prix_vente_unitaire, achat_id
           FROM articles WHERE id = ?""",
        (article_id,),
    ).fetchone()
    conn.close()
    return row


def get_articles_full() -> pd.DataFrame:
    conn = get_conn()
    df = pd.read_sql_query(
        """
        SELECT a.id, c.nom AS categorie, ac.numero AS numero_achat, ac.date_achat AS date_achat,
               a.nom AS article, a.quantite, a.prix_achat_unitaire, a.prix_vente_unitaire
        FROM articles a
        JOIN categories c ON a.categorie_id = c.id
        LEFT JOIN achats ac ON a.achat_id = ac.id
        ORDER BY c.nom, a.nom
        """,
        conn,
    )
    conn.close()
    if df.empty:
        return df
    df["total_achat"] = df["quantite"] * df["prix_achat_unitaire"]
    df["total_vente"] = df["quantite"] * df["prix_vente_unitaire"]
    df["benefice"] = df["total_vente"] - df["total_achat"]
    df["marge_pct"] = (df["benefice"] / df["total_achat"].replace(0, pd.NA)) * 100
    return df


# --------------------------------------------------------------------------------------
# INTERFACE
# --------------------------------------------------------------------------------------

st.set_page_config(page_title="Gestionnaire de Fournitures Scolaires 2026-2027", page_icon="🎒", layout="wide")
init_db()

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""


def format_fcfa(valeur) -> str:
    try:
        return f"{valeur:,.0f} FCFA".replace(",", " ")
    except (TypeError, ValueError):
        return "0 FCFA"


# --------------------------------------------------------------------------------------
# AUTHENTIFICATION
# --------------------------------------------------------------------------------------

def page_auth():
    st.title("🎒 Gestionnaire de Fournitures Scolaires 2026-2027")
    st.caption("Gestion de fournitures scolaires — Année 2026-2027")

    if not admin_exists():
        st.subheader("Créer le compte administrateur")
        with st.form("form_creation"):
            username = st.text_input("Nom d'utilisateur")
            password = st.text_input("Mot de passe", type="password")
            confirm = st.text_input("Confirmer le mot de passe", type="password")
            submitted = st.form_submit_button("Créer le compte")
            if submitted:
                if not username or not password:
                    st.error("Veuillez remplir tous les champs.")
                elif password != confirm:
                    st.error("Les mots de passe ne correspondent pas.")
                elif len(password) < 4:
                    st.error("Le mot de passe doit contenir au moins 4 caractères.")
                else:
                    ok, msg = create_admin(username, password)
                    if ok:
                        st.success(msg + " Vous pouvez maintenant vous connecter.")
                        st.rerun()
                    else:
                        st.error(msg)
    else:
        st.subheader("Connexion administrateur")
        with st.form("form_login"):
            username = st.text_input("Nom d'utilisateur")
            password = st.text_input("Mot de passe", type="password")
            submitted = st.form_submit_button("Se connecter")
            if submitted:
                if check_login(username, password):
                    st.session_state.logged_in = True
                    st.session_state.username = username
                    st.rerun()
                else:
                    st.error("Identifiants incorrects.")


# --------------------------------------------------------------------------------------
# ACHATS (numérotés)
# --------------------------------------------------------------------------------------

def page_achats():
    st.header("🧾 Achats numérotés")
    st.caption("Chaque achat reçoit automatiquement un numéro. Vous y rattachez ensuite les articles achetés dans l'onglet « Articles ».")

    prochain_numero = get_next_numero_achat()
    with st.form("form_achat", clear_on_submit=True):
        st.write(f"Numéro attribué automatiquement : **Achat n°{prochain_numero}**")
        date_achat = st.date_input("Date de l'achat", value=datetime.now().date())
        note = st.text_input("Note / fournisseur / lieu (optionnel)")
        submitted = st.form_submit_button("➕ Créer cet achat")
        if submitted:
            create_achat(date_achat.isoformat(), note)
            st.success(f"Achat n°{prochain_numero} créé.")
            st.rerun()

    achats = get_achats()
    if achats.empty:
        st.info("Aucun achat enregistré pour le moment.")
        return

    st.subheader("Liste des achats")
    df_articles = get_articles_full()

    for _, row in achats.iterrows():
        articles_lies = (
            df_articles[df_articles["numero_achat"] == row["numero"]]
            if not df_articles.empty else pd.DataFrame()
        )
        nb = len(articles_lies)
        total_achat = articles_lies["prix_achat_unitaire"].mul(articles_lies["quantite"]).sum() if nb else 0
        total_vente = articles_lies["prix_vente_unitaire"].mul(articles_lies["quantite"]).sum() if nb else 0

        c1, c2, c3, c4, c5 = st.columns([2, 2, 2, 2, 1])
        c1.write(f"**Achat n°{row['numero']}**")
        c2.write(row["date_achat"])
        c3.write(f"{nb} article(s)")
        c4.write(f"{format_fcfa(total_achat)} → {format_fcfa(total_vente)}")
        if c5.button("Suppr.", key=f"del_achat_{row['id']}"):
            delete_achat(row["id"])
            st.rerun()
        if row["note"]:
            st.caption(f"Note : {row['note']}")


# --------------------------------------------------------------------------------------
# IMPAYÉS
# --------------------------------------------------------------------------------------

def page_impayes():
    st.header("💰 Impayés")
    st.caption("Suivez les clients qui doivent encore vous payer, avec l'historique détaillé de leurs paiements.")

    df_articles = get_articles_full()

    st.subheader("Enregistrer un nouvel impayé")
    with st.form("form_impaye", clear_on_submit=True):
        col1, col2 = st.columns(2)
        client_nom = col1.text_input("Nom du client")
        client_contact = col2.text_input("Contact (téléphone) — optionnel")

        options_article = ["Aucun"] + (
            [f"{r['id']} — {r['article']} ({r['categorie']})" for _, r in df_articles.iterrows()]
            if not df_articles.empty else []
        )
        article_choisi = st.selectbox("Article concerné (optionnel)", options=options_article)

        col3, col4 = st.columns(2)
        montant_total = col3.number_input("Montant total dû (FCFA)", min_value=0.0, step=1.0)
        date_creation = col4.date_input("Date", value=datetime.now().date())
        note = st.text_input("Note (optionnel)")

        submitted = st.form_submit_button("➕ Enregistrer l'impayé")
        if submitted:
            if not client_nom.strip():
                st.error("Le nom du client est requis.")
            elif montant_total <= 0:
                st.error("Le montant total dû doit être supérieur à 0.")
            else:
                article_id = None
                if article_choisi != "Aucun":
                    article_id = int(article_choisi.split(" — ")[0])
                create_impaye(client_nom, client_contact, article_id, montant_total,
                              date_creation.isoformat(), note)
                st.success(f"Impayé enregistré pour « {client_nom} ».")
                st.rerun()

    st.divider()
    impayes = get_impayes_full()
    if impayes.empty:
        st.info("Aucun impayé enregistré pour le moment.")
        return

    st.subheader("🧮 Totaux généraux")
    t1, t2, t3, t4 = st.columns(4)
    t1.metric("Montant total dû", format_fcfa(impayes["montant_total"].sum()))
    t2.metric("Montant total payé", format_fcfa(impayes["montant_paye"].sum()))
    t3.metric("Reste à payer", format_fcfa(impayes["reste_a_payer"].sum()))
    t4.metric("Nombre de dossiers", len(impayes))

    st.subheader("Détail par client")
    for _, row in impayes.iterrows():
        titre = f"{row['statut']} — {row['client_nom']} — reste {format_fcfa(row['reste_a_payer'])}"
        with st.expander(titre):
            c1, c2, c3 = st.columns(3)
            c1.metric("Montant dû", format_fcfa(row["montant_total"]))
            c2.metric("Déjà payé", format_fcfa(row["montant_paye"]))
            c3.metric("Reste à payer", format_fcfa(row["reste_a_payer"]))

            infos = f"📅 Date : {row['date_creation']}"
            if row["client_contact"]:
                infos += f"  |  📞 {row['client_contact']}"
            if row["article_lie"]:
                infos += f"  |  📦 Article : {row['article_lie']}"
            st.caption(infos)
            if row["note"]:
                st.caption(f"Note : {row['note']}")

            st.markdown("**Historique des paiements**")
            paiements = get_paiements(row["id"])
            if paiements.empty:
                st.write("Aucun paiement enregistré pour l'instant.")
            else:
                for _, p in paiements.iterrows():
                    pc1, pc2, pc3 = st.columns([3, 3, 1])
                    pc1.write(f"{p['date_paiement']}")
                    pc2.write(format_fcfa(p["montant"]) + (f" — {p['note']}" if p["note"] else ""))
                    if pc3.button("🗑️", key=f"del_pai_{p['id']}"):
                        delete_paiement(int(p["id"]))
                        st.rerun()

            if row["reste_a_payer"] > 0:
                with st.form(f"form_paiement_{row['id']}", clear_on_submit=True):
                    pc1, pc2 = st.columns(2)
                    montant_paiement = pc1.number_input(
                        "Montant du paiement (FCFA)", min_value=0.0,
                        max_value=float(row["reste_a_payer"]), step=1.0,
                    )
                    date_paiement = pc2.date_input("Date du paiement", value=datetime.now().date(),
                                                    key=f"date_pai_{row['id']}")
                    note_paiement = st.text_input("Note (optionnel)", key=f"note_pai_{row['id']}")
                    if st.form_submit_button("💾 Enregistrer le paiement"):
                        if montant_paiement <= 0:
                            st.error("Le montant du paiement doit être supérieur à 0.")
                        else:
                            add_paiement(int(row["id"]), montant_paiement,
                                         date_paiement.isoformat(), note_paiement)
                            st.success("Paiement enregistré.")
                            st.rerun()
            else:
                st.success("Ce dossier est entièrement soldé. ✅")

            if st.button("🗑️ Supprimer ce dossier d'impayé", key=f"del_imp_{row['id']}"):
                delete_impaye(int(row["id"]))
                st.rerun()


# --------------------------------------------------------------------------------------
# CATÉGORIES
# --------------------------------------------------------------------------------------

def page_categories():
    st.header("📂 Classeur de catégories")

    with st.form("form_categorie", clear_on_submit=True):
        nom_cat = st.text_input("Nom de la nouvelle catégorie (ex : Cahiers, Stylos, Livres...)")
        submitted = st.form_submit_button("Ajouter la catégorie")
        if submitted:
            if nom_cat.strip():
                ok, msg = add_category(nom_cat)
                st.success(msg) if ok else st.error(msg)
                st.rerun()
            else:
                st.error("Le nom de la catégorie est requis.")

    cats = get_categories()
    if cats.empty:
        st.info("Aucune catégorie pour le moment.")
        return

    st.subheader("Catégories existantes")
    for _, row in cats.iterrows():
        c1, c2 = st.columns([5, 1])
        c1.write(f"• {row['nom']}")
        if c2.button("Supprimer", key=f"del_cat_{row['id']}"):
            delete_category(row["id"])
            st.rerun()


# --------------------------------------------------------------------------------------
# ARTICLES
# --------------------------------------------------------------------------------------

def page_articles():
    st.header("📦 Articles")

    cats = get_categories()
    if cats.empty:
        st.warning("Créez d'abord au moins une catégorie dans l'onglet « Catégories ».")
        return

    achats = get_achats()
    options_achat = ["Aucun"] + [
        f"Achat n°{r['numero']} — {r['date_achat']}" + (f" ({r['note']})" if r["note"] else "")
        for _, r in achats.iterrows()
    ]
    if achats.empty:
        st.info("💡 Astuce : créez un achat numéroté dans l'onglet « Achats » pour regrouper vos articles par facture/livraison.")

    st.subheader("Ajouter un ou plusieurs articles")
    with st.form("form_article", clear_on_submit=True):
        col1, col2 = st.columns(2)
        categorie_nom = col1.selectbox("Catégorie", cats["nom"].tolist())
        nom_article = col2.text_input("Nom de l'article")

        achat_choisi = st.selectbox("Rattacher à l'achat n°", options=options_achat)

        col3, col4, col5 = st.columns(3)
        quantite = col3.number_input("Quantité", min_value=0.0, step=1.0, value=1.0)
        prix_achat = col4.number_input("Prix d'achat unitaire (FCFA)", min_value=0.0, step=1.0)
        prix_vente = col5.number_input("Prix de vente unitaire (FCFA)", min_value=0.0, step=1.0)

        submitted = st.form_submit_button("➕ Ajouter l'article")
        if submitted:
            if not nom_article.strip():
                st.error("Le nom de l'article est requis.")
            else:
                cat_id = int(cats.loc[cats["nom"] == categorie_nom, "id"].iloc[0])
                achat_id = None
                if achat_choisi != "Aucun":
                    numero_choisi = int(achat_choisi.replace("Achat n°", "").split(" — ")[0])
                    achat_id = int(achats.loc[achats["numero"] == numero_choisi, "id"].iloc[0])
                add_article(cat_id, nom_article, quantite, prix_achat, prix_vente, achat_id)
                st.success(f"Article « {nom_article} » ajouté.")
                st.rerun()

    st.divider()
    df = get_articles_full()
    if df.empty:
        st.info("Aucun article enregistré pour le moment.")
        return

    st.subheader("Détail des articles (calculs automatiques)")
    for categorie in df["categorie"].unique():
        sous_df = df[df["categorie"] == categorie]
        with st.expander(f"📁 {categorie}  —  {len(sous_df)} article(s)", expanded=True):
            affichage = sous_df[[
                "id", "numero_achat", "article", "quantite", "prix_achat_unitaire",
                "prix_vente_unitaire", "total_achat", "total_vente", "benefice",
            ]].rename(columns={
                "id": "ID", "numero_achat": "N° Achat", "article": "Article", "quantite": "Quantité",
                "prix_achat_unitaire": "PU Achat", "prix_vente_unitaire": "PU Vente",
                "total_achat": "Total Achat", "total_vente": "Total Vente",
                "benefice": "Bénéfice",
            })
            st.dataframe(affichage.set_index("ID"), use_container_width=True)

            sc1, sc2, sc3, sc4 = st.columns(4)
            sc1.metric("Quantité totale", f"{sous_df['quantite'].sum():,.0f}")
            sc2.metric("Total achat", format_fcfa(sous_df["total_achat"].sum()))
            sc3.metric("Total vente", format_fcfa(sous_df["total_vente"].sum()))
            sc4.metric("Bénéfice", format_fcfa(sous_df["benefice"].sum()))

            col_edit, col_del = st.columns(2)

            with col_edit:
                st.markdown("**✏️ Modifier un article**")
                options_edit = ["—"] + [
                    f"{r['id']} — {r['article']}" for _, r in sous_df.iterrows()
                ]
                choix_edit = st.selectbox(
                    "Article à modifier", options=options_edit, key=f"edit_sel_{categorie}"
                )
                if choix_edit != "—":
                    art_id = int(choix_edit.split(" — ")[0])
                    art = get_article_by_id(art_id)
                    if art:
                        _, _, nom_actuel, qte_actuel, pa_actuel, pv_actuel, achat_id_actuel = art
                        achats_disp = get_achats()
                        options_achat_edit = ["Aucun"] + [
                            f"Achat n°{r['numero']} — {r['date_achat']}" for _, r in achats_disp.iterrows()
                        ]
                        index_defaut = 0
                        if achat_id_actuel is not None and not achats_disp.empty:
                            match = achats_disp.loc[achats_disp["id"] == achat_id_actuel]
                            if not match.empty:
                                numero_defaut = match["numero"].iloc[0]
                                for i, opt in enumerate(options_achat_edit):
                                    if opt.startswith(f"Achat n°{numero_defaut} "):
                                        index_defaut = i
                                        break
                        with st.form(f"form_edit_{art_id}"):
                            nouveau_nom = st.text_input("Nom de l'article", value=nom_actuel)
                            achat_edit_choisi = st.selectbox(
                                "Rattacher à l'achat n°", options=options_achat_edit, index=index_defaut
                            )
                            ec1, ec2, ec3 = st.columns(3)
                            nouvelle_qte = ec1.number_input(
                                "Quantité", min_value=0.0, step=1.0, value=float(qte_actuel)
                            )
                            nouveau_pa = ec2.number_input(
                                "PU Achat (FCFA)", min_value=0.0, step=1.0, value=float(pa_actuel)
                            )
                            nouveau_pv = ec3.number_input(
                                "PU Vente (FCFA)", min_value=0.0, step=1.0, value=float(pv_actuel)
                            )
                            if st.form_submit_button("💾 Enregistrer les modifications"):
                                if not nouveau_nom.strip():
                                    st.error("Le nom de l'article est requis.")
                                else:
                                    nouvel_achat_id = None
                                    if achat_edit_choisi != "Aucun":
                                        numero_choisi = int(achat_edit_choisi.replace("Achat n°", "").split(" — ")[0])
                                        nouvel_achat_id = int(
                                            achats_disp.loc[achats_disp["numero"] == numero_choisi, "id"].iloc[0]
                                        )
                                    update_article(
                                        art_id, nouveau_nom, nouvelle_qte, nouveau_pa, nouveau_pv, nouvel_achat_id
                                    )
                                    st.success("Article mis à jour.")
                                    st.rerun()

            with col_del:
                st.markdown("**🗑️ Supprimer un article**")
                del_id = st.selectbox(
                    "Article à supprimer",
                    options=["—"] + sous_df["id"].astype(str).tolist(),
                    key=f"del_sel_{categorie}",
                )
                if del_id != "—" and st.button("Confirmer la suppression", key=f"del_btn_{categorie}"):
                    delete_article(int(del_id))
                    st.rerun()

    st.divider()
    st.subheader("🧮 Totaux généraux — tous articles confondus")
    g1, g2, g3, g4 = st.columns(4)
    g1.metric("Quantité totale", f"{df['quantite'].sum():,.0f}")
    g2.metric("Montant total d'achat", format_fcfa(df["total_achat"].sum()))
    g3.metric("Montant total de vente", format_fcfa(df["total_vente"].sum()))
    g4.metric("Bénéfice total", format_fcfa(df["benefice"].sum()))


# --------------------------------------------------------------------------------------
# STATISTIQUES
# --------------------------------------------------------------------------------------

def page_stats():
    st.header("📊 Tableau statistique")

    df = get_articles_full()
    if df.empty:
        st.info("Aucune donnée à afficher pour le moment.")
        return

    st.subheader("Statistiques par catégorie")
    stats_cat = df.groupby("categorie").agg(
        Nb_articles=("article", "count"),
        Quantite_totale=("quantite", "sum"),
        Total_achat=("total_achat", "sum"),
        Total_vente=("total_vente", "sum"),
        Benefice=("benefice", "sum"),
    ).reset_index().rename(columns={"categorie": "Catégorie"})
    stats_cat["Marge (%)"] = (stats_cat["Benefice"] / stats_cat["Total_achat"].replace(0, pd.NA) * 100).round(1)
    st.dataframe(stats_cat.set_index("Catégorie"), use_container_width=True)

    st.subheader("Répartition du bénéfice par catégorie")
    st.bar_chart(stats_cat.set_index("Catégorie")["Benefice"])

    if df["numero_achat"].notna().any():
        st.subheader("Statistiques par achat (n°)")
        df_avec_achat = df[df["numero_achat"].notna()].copy()
        df_avec_achat["numero_achat"] = df_avec_achat["numero_achat"].astype(int)
        stats_achat = df_avec_achat.groupby("numero_achat").agg(
            Nb_articles=("article", "count"),
            Quantite_totale=("quantite", "sum"),
            Total_achat=("total_achat", "sum"),
            Total_vente=("total_vente", "sum"),
            Benefice=("benefice", "sum"),
        ).reset_index().rename(columns={"numero_achat": "N° Achat"})
        stats_achat["Marge (%)"] = (stats_achat["Benefice"] / stats_achat["Total_achat"].replace(0, pd.NA) * 100).round(1)
        st.dataframe(stats_achat.set_index("N° Achat"), use_container_width=True)

    st.subheader("Classement des articles les plus rentables")
    top = df[["categorie", "article", "benefice", "marge_pct"]].sort_values("benefice", ascending=False)
    top = top.rename(columns={
        "categorie": "Catégorie", "article": "Article",
        "benefice": "Bénéfice", "marge_pct": "Marge (%)",
    })
    st.dataframe(top.reset_index(drop=True), use_container_width=True)

    st.subheader("Résumé global")
    r1, r2, r3, r4 = st.columns(4)
    r1.metric("Nombre d'articles", len(df))
    r2.metric("Nombre de catégories", df["categorie"].nunique())
    r3.metric("Bénéfice total", format_fcfa(df["benefice"].sum()))
    marge_globale = (df["benefice"].sum() / df["total_achat"].sum() * 100) if df["total_achat"].sum() else 0
    r4.metric("Marge globale", f"{marge_globale:.1f} %")

    impayes = get_impayes_full()
    if not impayes.empty:
        st.subheader("💰 Résumé des impayés")
        i1, i2, i3, i4 = st.columns(4)
        i1.metric("Montant total dû", format_fcfa(impayes["montant_total"].sum()))
        i2.metric("Montant payé", format_fcfa(impayes["montant_paye"].sum()))
        i3.metric("Reste à payer", format_fcfa(impayes["reste_a_payer"].sum()))
        nb_non_soldes = (impayes["reste_a_payer"] > 0).sum()
        i4.metric("Dossiers non soldés", int(nb_non_soldes))


# --------------------------------------------------------------------------------------
# APPLICATION PRINCIPALE
# --------------------------------------------------------------------------------------

def main():
    if not st.session_state.logged_in:
        page_auth()
        return

    st.sidebar.title("🎒 Gestionnaire de Fournitures Scolaires 2026-2027")
    st.sidebar.caption(f"Connecté en tant que : {st.session_state.username}")
    choix = st.sidebar.radio("Menu", ["Achats", "Catégories", "Articles", "Impayés", "Statistiques"])
    st.sidebar.divider()
    if st.sidebar.button("🚪 Se déconnecter"):
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.rerun()

    if choix == "Achats":
        page_achats()
    elif choix == "Catégories":
        page_categories()
    elif choix == "Articles":
        page_articles()
    elif choix == "Impayés":
        page_impayes()
    elif choix == "Statistiques":
        page_stats()


if __name__ == "__main__":
    main()
