"""Passage quotidien sur le PC (étape 8 et suivantes) : prépare la file, rédige, rend, envoie ou simule.

Par défaut DRY_RUN=true : les messages sont écrits en fichiers .eml dans SORTIE_SIMULATION, rien ne part.
Un envoi réel exige DRY_RUN=false ET LIVE_SEND=true (variables d'environnement utilisateur sur le PC).
Les identifiants SMTP (BREVO_SMTP_LOGIN, BREVO_SMTP_KEY) et ANTHROPIC_API_KEY ne sont jamais écrits dans le code.

Règles appliquées à chaque envoi (voir envoi.peut_envoyer) : jours ouvrés, opposition, pays exclu,
3 messages par adresse, relances J+3 et J+4, 5 envois par semaine. Une erreur arrête le passage, sans réessai.

Usage : py -3 lancer.py            (simulation si DRY_RUN n'est pas false)
"""

import importlib.util
import json
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


def appliquer_corrections(conn):
    """Lit DONNEES_DIR/corrections.json : retire un prospect (retirer=true) ou remplace sa phrase de raison.
    Le fichier est marqué traité pour ne pas s'appliquer deux fois."""
    dossier = os.environ.get("DONNEES_DIR", "")
    chemin = os.path.join(dossier, "corrections.json") if dossier else ""
    if not chemin or not os.path.exists(chemin):
        return 0
    with open(chemin, encoding="utf-8") as f:
        corrections = json.load(f)
    for c in corrections:
        email = c["email"].strip().lower()
        ids = [r[0] for r in conn.execute("SELECT id FROM prospects WHERE lower(email) = ?", (email,))]
        for pid in ids:
            if c.get("retirer"):
                conn.execute("UPDATE prospects SET statut = 'retire' WHERE id = ?", (pid,))
                conn.execute("UPDATE outbox SET statut = 'annule' WHERE prospect_id = ? AND statut = 'file'", (pid,))
                print(f"[retiré] {email}")
            elif c.get("phrase"):
                notes = conn.execute("SELECT notes FROM prospects WHERE id = ?", (pid,)).fetchone()[0] or ""
                nouvelles = re.sub(r"Phrase : [^|]*", "Phrase : " + c["phrase"].replace("|", "/"), notes)
                conn.execute("UPDATE prospects SET notes = ? WHERE id = ?", (nouvelles, pid))
                print(f"[phrase mise à jour] {email}")
    conn.commit()
    os.rename(chemin, chemin + ".traite")
    return len(corrections)


def preparer_relances(conn, aujourdhui):
    """Crée la relance 1 (3 jours après le premier envoi réel) et la relance 2 (4 jours après la relance 1),
    seulement si la relance est rédigée dans les notes (phrase et question validées par lot)."""
    ajoutees = 0
    premiers = conn.execute(
        "SELECT o.prospect_id, o.date_envoi, p.notes FROM outbox o JOIN prospects p ON p.id = o.prospect_id "
        "WHERE o.type = 'premier' AND o.statut = 'envoye' AND o.date_envoi IS NOT NULL"
    ).fetchall()
    for pid, date_envoi, notes in premiers:
        if not champ_depuis_notes(notes, "Relance") or not champ_depuis_notes(notes, "Question"):
            continue
        d1 = date.fromisoformat(date_envoi) + timedelta(days=3)
        existe = conn.execute("SELECT 1 FROM outbox WHERE prospect_id = ? AND type = 'relance1'", (pid,)).fetchone()
        if not existe:
            conn.execute(
                "INSERT INTO outbox (prospect_id, type, gabarit, statut, date_prevue) VALUES (?, 'relance1', NULL, 'file', ?)",
                (pid, prochain_jour_ouvre(max(d1, aujourdhui)).isoformat()),
            )
            ajoutees += 1
    for pid, date_r1, notes in conn.execute(
        "SELECT o.prospect_id, o.date_envoi, p.notes FROM outbox o JOIN prospects p ON p.id = o.prospect_id "
        "WHERE o.type = 'relance1' AND o.statut = 'envoye' AND o.date_envoi IS NOT NULL"
    ).fetchall():
        if not champ_depuis_notes(notes, "Relance") or not champ_depuis_notes(notes, "Question"):
            continue
        d2 = date.fromisoformat(date_r1) + timedelta(days=4)
        existe = conn.execute("SELECT 1 FROM outbox WHERE prospect_id = ? AND type = 'relance2'", (pid,)).fetchone()
        if not existe:
            conn.execute(
                "INSERT INTO outbox (prospect_id, type, gabarit, statut, date_prevue) VALUES (?, 'relance2', NULL, 'file', ?)",
                (pid, prochain_jour_ouvre(max(d2, aujourdhui)).isoformat()),
            )
            ajoutees += 1
    conn.commit()
    return ajoutees


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
        "WHERE o.statut = 'file' AND o.date_prevue <= ? "
        + ("" if mode_reel else "AND o.simule_le IS NULL ")
        + "ORDER BY o.date_prevue, o.id",
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
            "relance": champ_depuis_notes(notes, "Relance"), "question": champ_depuis_notes(notes, "Question"),
        }
        msg = redaction.generer(prospect, gabarit_fr, typ)
        if os.environ.get("USE_OLLAMA", "false").lower() == "true":
            reecrit = redaction.reecrire_ollama(msg)
            if reecrit:
                msg = reecrit
                print(f"[réécrit par Ollama] {nom} ({typ})")
            else:
                print(f"[Ollama : aucun essai valide, gabarit validé conservé] {nom} ({typ})")
        if mode_reel and not msg.get("humanise"):
            # Envoi réel : un message non passé par l'humanizer ne part pas (rédaction de secours sans API).
            raise RuntimeError("Message non humanisé (API indisponible) : envoi réel refusé, rien n'est parti.")
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
        if mode_reel:
            conn.execute("UPDATE outbox SET statut = 'envoye', date_envoi = ? WHERE id = ?", (aujourdhui.isoformat(), oid))
            conn.execute("UPDATE prospects SET dernier_contact = ? WHERE id = ?", (aujourdhui.isoformat(), pid))
        else:
            # Simulation : ce message est produit une seule fois ; il ne sera pas regénéré les jours suivants.
            conn.execute("UPDATE outbox SET simule_le = ? WHERE id = ?", (aujourdhui.isoformat(), oid))
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

    base.migrer()
    base.purge()  # conservation 24 mois (D10) : idempotent, sans effet si rien n'est échu
    conn = base.connect()
    try:
        if not mode_reel:
            # La simulation ne peut rien avoir envoyé : les lignes marquées « envoye » par erreur retournent en file.
            conn.execute("UPDATE outbox SET statut = 'file', date_envoi = NULL WHERE statut = 'envoye'")
            conn.commit()
        appliquer_corrections(conn)
        relances = preparer_relances(conn, date.today())
        print(f"Relances : {relances} ajoutée(s).")
        nouveaux = preparer(conn, date.today())
        print(f"File : {nouveaux} prospect(s) ajouté(s).")
        traites = traiter_file(conn, date.today(), base, envoi, redaction, exclus, mode_reel, env)
        print(f"Passage terminé : {traites} message(s) traité(s). Mode : {'envoi réel' if mode_reel else 'simulation'}.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
