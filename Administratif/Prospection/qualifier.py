"""Qualification des prospects avant toute rédaction (étape 4).

Un prospect n'entre dans la base que si toutes les conditions sont remplies :
  - nom, e-mail (format valide), pays (code ISO à 2 lettres) ;
  - source_url en https, date_consultation au format AAAA-MM-JJ, passée et récente (30 jours au plus) ;
  - raison précise et vérifiée (au moins 10 caractères), notée avec la source ;
  - pays absent de Pays Email Exclus.txt ;
  - adresse absente des oppositions et pas déjà présente dans la base.

Usage :
  python qualifier.py candidats.json          simulation : affiche accepté / refusé, n'écrit rien
  python qualifier.py candidats.json --ecrire  écrit les prospects acceptés dans la base chiffrée

Le fichier candidats.json est une liste d'objets. Il ne doit pas être versionné dans le dépôt public.
"""

import importlib.util
import json
import os
import re
import sys
from datetime import date, datetime, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
EXCLUS_PATH = os.path.join(HERE, "..", "Outils", "Prospection Mondiale", "Pays Email Exclus.txt")
FRESHNESS_DAYS = 30
RAISON_MIN = 10
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PAYS_RE = re.compile(r"^[A-Z]{2}$")


def charger_base():
    spec = importlib.util.spec_from_file_location("base_contacts", os.path.join(HERE, "base-contacts.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def pays_exclus(path=EXCLUS_PATH):
    codes = set()
    with open(path, encoding="utf-8") as f:
        for ligne in f:
            code = ligne.split("#", 1)[0].strip().upper()
            if code:
                codes.add(code)
    return codes


def verifier(cand, conn, base, exclus, aujourd_hui=None):
    """Renvoie la liste des motifs de refus. Liste vide = accepté."""
    aujourd_hui = aujourd_hui or date.today()
    refus = []

    nom = (cand.get("nom") or "").strip()
    email = (cand.get("email") or "").strip()
    pays = (cand.get("pays") or "").strip().upper()
    url = (cand.get("source_url") or "").strip()
    consulte = (cand.get("date_consultation") or "").strip()
    raison = (cand.get("raison") or "").strip()

    if not nom:
        refus.append("nom manquant")
    if not EMAIL_RE.match(email):
        refus.append("e-mail absent ou invalide")
    if not PAYS_RE.match(pays):
        refus.append("pays absent ou invalide (code ISO attendu)")
    elif pays in exclus:
        refus.append(f"pays exclu ({pays})")
    if not url.startswith("https://"):
        refus.append("source_url absente ou non https")
    try:
        d = datetime.strptime(consulte, "%Y-%m-%d").date()
    except ValueError:
        refus.append("date_consultation absente ou mal formée (AAAA-MM-JJ)")
    else:
        if d > aujourd_hui:
            refus.append("date_consultation dans le futur")
        elif d < aujourd_hui - timedelta(days=FRESHNESS_DAYS):
            refus.append(f"source consultée il y a plus de {FRESHNESS_DAYS} jours : à revérifier")
    if len(raison) < RAISON_MIN:
        refus.append("raison absente ou trop courte")

    if EMAIL_RE.match(email):
        if base.est_en_opposition(conn, email):
            refus.append("adresse en opposition")
        deja = conn.execute(
            "SELECT 1 FROM prospects WHERE lower(email) = lower(?)", (email,)
        ).fetchone()
        if deja:
            refus.append("adresse déjà dans la base")
    return refus


def ecrire(cand, conn):
    conn.execute(
        "INSERT INTO prospects (nom, activite, pays, ville, email, telephone, site_web, source, source_date, "
        "statut, date_collecte, notes) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            cand["nom"].strip(),
            cand.get("activite"),
            cand["pays"].strip().upper(),
            cand.get("ville"),
            cand["email"].strip(),
            cand.get("telephone"),
            cand.get("site_web"),
            cand["source_url"].strip(),
            cand["date_consultation"].strip(),
            "a contacter",
            date.today().isoformat(),
            "Raison vérifiée : " + cand["raison"].strip()
            + " | Offre : " + cand.get("offre", "").strip()
            + " | Phrase : " + cand.get("phrase", "").strip()
            + " | Produit : " + cand.get("produit", "").strip(),
        ),
    )


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    ecrire_reel = "--ecrire" in sys.argv
    if len(args) != 1:
        sys.exit(__doc__)
    with open(args[0], encoding="utf-8") as f:
        candidats = json.load(f)

    base = charger_base()
    exclus = pays_exclus()
    conn = base.connect()
    acceptes = 0
    for cand in candidats:
        motifs = verifier(cand, conn, base, exclus)
        nom = cand.get("nom", "(sans nom)")
        if motifs:
            print(f"REFUSÉ  {nom} : " + " ; ".join(motifs))
        else:
            acceptes += 1
            print(f"ACCEPTÉ {nom}")
            if ecrire_reel:
                ecrire(cand, conn)
    if ecrire_reel:
        conn.commit()
    conn.close()
    mode = "écrit dans la base" if ecrire_reel else "simulation, rien écrit"
    print(f"\n{acceptes}/{len(candidats)} accepté(s) ({mode}).")
