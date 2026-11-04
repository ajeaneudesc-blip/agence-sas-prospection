"""Base de contacts chiffrée (SQLCipher).

Commandes :
  python base-contacts.py init                 crée la base vide
  python base-contacts.py opposer <email>      enregistre une opposition et supprime le contact
  python base-contacts.py purge                supprime les contacts sans contact depuis 24 mois
  python base-contacts.py chiffrer             copie la base en contacts.db.enc (avant sauvegarde)

Mot de passe : variable BASE_CONTACTS_PASSPHRASE, sinon demandé à la saisie.
Il ne doit figurer ni dans ce fichier ni dans le dépôt.

Tables :
  prospects   un contact (données personnelles, purgées après 24 mois)
  journal     historique des actions par contact
  outbox      file d'envoi : un message par ligne (premier message, relance 1, relance 2)
  reponses    réponses reçues, classées (aucune réponse automatique au prospect)
  oppositions empreinte SHA-256 des adresses en opposition. Pas l'adresse en clair,
              pour qu'une opposition survive à la suppression du contact.
"""

import getpass
import hashlib
import os
import sys
from datetime import date, timedelta

import sqlcipher3

HERE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(HERE, "contacts.db")
ENC_PATH = os.path.join(HERE, "contacts.db.enc")
RETENTION_MONTHS = 24

SCHEMA = """
CREATE TABLE IF NOT EXISTS prospects (
    id INTEGER PRIMARY KEY,
    nom TEXT NOT NULL,
    activite TEXT,
    pays TEXT,
    ville TEXT,
    email TEXT,
    telephone TEXT,
    site_web TEXT,
    source TEXT NOT NULL,
    source_date TEXT NOT NULL,
    statut TEXT NOT NULL DEFAULT 'a contacter',
    date_collecte TEXT NOT NULL,
    dernier_contact TEXT,
    opposition INTEGER NOT NULL DEFAULT 0,
    notes TEXT
);
CREATE TABLE IF NOT EXISTS journal (
    id INTEGER PRIMARY KEY,
    prospect_id INTEGER NOT NULL REFERENCES prospects(id),
    date TEXT NOT NULL,
    canal TEXT NOT NULL,
    action TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS outbox (
    id INTEGER PRIMARY KEY,
    prospect_id INTEGER NOT NULL REFERENCES prospects(id),
    type TEXT NOT NULL CHECK (type IN ('premier', 'relance1', 'relance2')),
    gabarit TEXT,
    statut TEXT NOT NULL DEFAULT 'file'
        CHECK (statut IN ('file', 'envoye', 'echec', 'annule')),
    date_prevue TEXT NOT NULL,
    date_envoi TEXT,
    UNIQUE (prospect_id, type)
);
CREATE TABLE IF NOT EXISTS reponses (
    id INTEGER PRIMARY KEY,
    prospect_id INTEGER NOT NULL REFERENCES prospects(id),
    date TEXT NOT NULL,
    classement TEXT NOT NULL,
    resume TEXT,
    action TEXT
);
CREATE TABLE IF NOT EXISTS oppositions (
    empreinte TEXT PRIMARY KEY,
    date TEXT NOT NULL
);
"""


def passphrase():
    return os.environ.get("BASE_CONTACTS_PASSPHRASE") or getpass.getpass("Mot de passe de la base : ")


def _quote(valeur):
    return valeur.replace("'", "''")


def empreinte(email):
    return hashlib.sha256(email.strip().lower().encode("utf-8")).hexdigest()


def connect(path=None):
    conn = sqlcipher3.connect(path or DB_PATH)
    conn.execute(f"PRAGMA key = '{_quote(passphrase())}'")
    conn.execute("SELECT count(*) FROM sqlite_master")
    return conn


def init(path=None):
    path = path or DB_PATH
    if os.path.exists(path):
        sys.exit("La base existe déjà : rien n'a été fait.")
    conn = connect(path)
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()
    print("Base créée :", path)


def opposer(email, path=None, conn=None):
    proprietaire = conn is None
    if proprietaire:
        conn = connect(path)
    conn.execute(
        "INSERT OR IGNORE INTO oppositions (empreinte, date) VALUES (?, ?)",
        (empreinte(email), date.today().isoformat()),
    )
    ids = [r[0] for r in conn.execute("SELECT id FROM prospects WHERE lower(email) = lower(?)", (email,))]
    for pid in ids:
        conn.execute("DELETE FROM outbox WHERE prospect_id = ?", (pid,))
        conn.execute("DELETE FROM reponses WHERE prospect_id = ?", (pid,))
        conn.execute("DELETE FROM journal WHERE prospect_id = ?", (pid,))
        conn.execute("DELETE FROM prospects WHERE id = ?", (pid,))
    if proprietaire:
        conn.commit()
        conn.close()
    print(f"Opposition enregistrée. Contact(s) supprimé(s) : {len(ids)}.")


def est_en_opposition(conn, email):
    return conn.execute("SELECT 1 FROM oppositions WHERE empreinte = ?", (empreinte(email),)).fetchone() is not None


def purge(path=None):
    limite = (date.today() - timedelta(days=RETENTION_MONTHS * 30)).isoformat()
    conn = connect(path)
    perimetre = (
        "SELECT id FROM prospects WHERE COALESCE(dernier_contact, date_collecte) < ? OR opposition = 1"
    )
    conn.execute(f"DELETE FROM outbox WHERE prospect_id IN ({perimetre})", (limite,))
    conn.execute(f"DELETE FROM reponses WHERE prospect_id IN ({perimetre})", (limite,))
    cur_j = conn.execute(f"DELETE FROM journal WHERE prospect_id IN ({perimetre})", (limite,))
    cur_p = conn.execute(
        "DELETE FROM prospects WHERE COALESCE(dernier_contact, date_collecte) < ? OR opposition = 1",
        (limite,),
    )
    conn.commit()
    conn.close()
    print(f"Purge : {cur_p.rowcount} contact(s) supprimé(s), {cur_j.rowcount} ligne(s) de journal.")


def chiffrer(path=None, enc=None):
    path = path or DB_PATH
    enc = enc or ENC_PATH
    conn = connect(path)
    if os.path.exists(enc):
        os.remove(enc)
    conn.execute(f"ATTACH DATABASE '{_quote(enc)}' AS enc KEY '{_quote(passphrase())}'")
    conn.execute("SELECT sqlcipher_export('enc')")
    conn.execute("DETACH DATABASE enc")
    conn.close()
    print("Copie chiffrée :", enc)


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "opposer" and len(sys.argv) == 3:
        opposer(sys.argv[2])
    elif len(sys.argv) == 2 and sys.argv[1] in ("init", "purge", "chiffrer"):
        {"init": init, "purge": purge, "chiffrer": chiffrer}[sys.argv[1]]()
    else:
        sys.exit(__doc__)
