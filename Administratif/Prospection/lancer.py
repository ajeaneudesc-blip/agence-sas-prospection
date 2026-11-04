"""Passage quotidien sur le PC (étape 8 et suivantes) : prépare la file, rédige, rend, envoie ou simule.

Par défaut DRY_RUN=true : les messages sont écrits en fichiers .eml dans SORTIE_SIMULATION, rien ne part.
Un envoi réel exige DRY_RUN=false ET LIVE_SEND=true (variables d'environnement utilisateur sur le PC).
Les identifiants SMTP (BREVO_SMTP_LOGIN, BREVO_SMTP_KEY) et ANTHROPIC_API_KEY ne sont jamais écrits dans le code.

Règles appliquées à chaque envoi (voir envoi.peut_envoyer) : jours ouvrés, opposition, pays exclu,
3 messages par adresse, relances J+3 et J+4, 5 envois par semaine. Une erreur arrête le passage, sans réessai.

Usage : py -3 lancer.py            (simulation si DRY_RUN n'est pas false)
"""

import importlib.util
import os
import re
import sys
from datetime import date, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
SORTIE = os.environ.get("SORTIE_SIMULATION", os.path.join(os.environ.get("TEMP", "."), "agence-sas-simulation"))


def _charger(nom, fichier):
    spec = importlib.util.spec_from_file_location(nom, os.path.join(HERE, fichier))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def prochain_jour_ouvre(d):
    while d.weekday() >= 5:
        d += timedelta(days=1)
    return d


def champ_depuis_notes(notes, nom):
    m = re.search(nom + r" : ([^|]*)", notes or "")
    return m.group(1).strip() if m else ""


def offre_depuis_notes(notes):
    m = re.search(r"Offre : (\w+)", notes or "")
    return m.group(1) if m else None


def preparer(conn, aujourdhui):
    """Crée un premier message en file pour chaque prospect « à contacter » qui n'en a pas encore."""
    lignes = conn.execute(
        "SELECT p.id, p.notes FROM prospects p WHERE p.statut = 'a contacter' "
        "AND NOT EXISTS (SELECT 1 FROM outbox o WHERE o.prospect_id = p.id AND o.type = 'premier')"
    ).fetchall()
    for pid, notes in lignes:
        gabarit = offre_depuis_notes(notes)
        if gabarit is None:
            continue
        conn.execute(
            "INSERT INTO outbox (prospect_id, type, gabarit, statut, date_prevue) VALUES (?, 'premier', ?, 'file', ?)",
            (pid, gabarit, prochain_jour_ouvre(aujourdhui).isoformat()),
        )
    conn.commit()
    return len(lignes)


def traiter_file(conn, aujourdhui, base, envoi, redaction, exclus, mode_reel, env):
    """Traite les messages dus. S'arrête à la première erreur. Renvoie le nombre de messages traités."""
    gabarits = redaction.gabarits_valides()
    dus = conn.execute(
        "SELECT o.id, o.prospect_id, o.type, o.gabarit, p.nom, p.email, p.pays, p.source, p.source_date "
        "FROM outbox o JOIN prospects p ON p.id = o.prospect_id "
        "WHERE o.statut = 'file' AND o.date_prevue <= ? ORDER BY o.date_prevue, o.id",
        (aujourdhui.isoformat(),),
    ).fetchall()
    traites = 0
    for oid, pid, typ, gabarit, nom, email, pays, source, source_date in dus:
        motifs = envoi.peut_envoyer(conn, pid, typ, email, aujourdhui, exclus)
        if motifs:
            conn.execute("UPDATE outbox SET statut = 'annule' WHERE id = ?", (oid,))
            conn.commit()
            print(f"[annulé] {nom} ({typ}) : " + " ; ".join(motifs))
            continue
        if typ == "premier":
            # Le champ gabarit contient l'offre (site, motion...) : on cherche le gabarit VALIDÉ correspondant.
            cles = [k for k, (o, _) in gabarits.items() if o == gabarit]
            if not cles:
                raise RuntimeError(f"Aucun gabarit VALIDÉ pour l'offre « {gabarit} » : arrêt.")
            cle = cles[0]
        else:
            cle = typ
        if cle not in gabarits:
            raise RuntimeError(f"Gabarit « {cle} » absent ou non VALIDÉ : arrêt.")
        offre, gabarit_fr = gabarits[cle]
        notes = conn.execute("SELECT notes FROM prospects WHERE id = ?", (pid,)).fetchone()[0]
        prospect = {
            "nom": nom, "pays": pays, "source_url": source, "date_consultation": source_date,
            "offre": offre_depuis_notes(notes), "raison": champ_depuis_notes(notes, "Raison vérifiée"),
            "phrase": champ_depuis_notes(notes, "Phrase"), "produit": champ_depuis_notes(notes, "Produit"),
        }
        msg = redaction.generer(prospect, gabarit_fr, typ)
        desinscription = f"mailto:{env['FROM_ADDR']}?subject=Desinscription"
        html = envoi.rendre_html(msg, offre or msg["offre"], env["FROM_ADDR"], desinscription)
        texte = envoi.rendre_texte(msg, env["FROM_ADDR"], desinscription)
        eml = envoi.construire_eml(msg, email, env["FROM_ADDR"], env["FROM_NAME"], html, texte, env["FROM_ADDR"])
        if mode_reel:
            envoi.envoyer(eml, env["SMTP_HOST"], int(env["SMTP_PORT"]), env["SMTP_LOGIN"], env["SMTP_KEY"])
            etat = "envoyé"
        else:
            chemin = envoi.ecrire_simulation(eml, SORTIE)
            etat = f"simulé ({chemin})"
        conn.execute("UPDATE outbox SET statut = 'envoye', date_envoi = ? WHERE id = ?", (aujourdhui.isoformat(), oid))
        conn.execute("UPDATE prospects SET dernier_contact = ? WHERE id = ?", (aujourdhui.isoformat(), pid))
        conn.commit()
        print(f"[{etat}] {nom} ({typ})")
        traites += 1
    return traites


def main():
    base = _charger("base_contacts", "base-contacts.py")
    envoi = _charger("envoi", "envoi.py")
    redaction = _charger("redaction", "redaction.py")
    exclus = set()
    with open(os.path.join(HERE, "..", "Outils", "Prospection Mondiale", "Pays Email Exclus.txt"), encoding="utf-8") as f:
        for ligne in f:
            code = ligne.split("#", 1)[0].strip().upper()
            if code:
                exclus.add(code)

    env = {k: os.environ.get(k, "") for k in [
        "FROM_ADDR", "FROM_NAME", "SMTP_HOST", "SMTP_PORT", "SMTP_LOGIN", "SMTP_KEY", "ANTHROPIC_API_KEY"]}
    env["FROM_NAME"] = env["FROM_NAME"] or "Jean Eudes Adakanou"
    env["SMTP_PORT"] = env["SMTP_PORT"] or "587"
    if not env["FROM_ADDR"]:
        sys.exit("FROM_ADDR absent : rien n'a été fait.")

    mode_reel = os.environ.get("DRY_RUN", "true").lower() == "false" and os.environ.get("LIVE_SEND", "false").lower() == "true"
    if os.environ.get("DRY_RUN", "true").lower() == "false" and not mode_reel:
        sys.exit("DRY_RUN=false sans LIVE_SEND=true : arrêt.")
    if mode_reel and not (env["SMTP_LOGIN"] and env["SMTP_KEY"]):
        sys.exit("Envoi réel demandé sans identifiants SMTP : arrêt.")

    conn = base.connect()
    try:
        nouveaux = preparer(conn, date.today())
        print(f"File : {nouveaux} prospect(s) ajouté(s).")
        traites = traiter_file(conn, date.today(), base, envoi, redaction, exclus, mode_reel, env)
        print(f"Passage terminé : {traites} message(s) traité(s). Mode : {'envoi réel' if mode_reel else 'simulation'}.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
