"""Lecture et tri des réponses aux messages de prospection (étape 7).

Règles :
  - lecture IMAP en lecture seule (aucun message marqué comme lu, aucun déplacement, aucune suppression) ;
  - aucune réponse automatique au prospect : ce module n'envoie rien à un prospect ;
  - une demande de ne plus être contacté (mot-clé) déclenche une opposition immédiate (opposer) ;
  - sinon, classement par Ollama en local (modèle OLLAMA_MODELE, défaut qwen2.5:7b). En cas d'échec, « à vérifier » ;
  - un résumé est préparé pour NOTIFY_TO. Il n'est envoyé que par envoi.envoyer, donc soumis aux mêmes gardes (DRY_RUN).

Usage :
  python reponses.py            lit la boîte, classe, enregistre, prépare le résumé (simulation)
"""

import email
import imaplib
import importlib.util
import json
import os
import re
import urllib.request
from datetime import date
from email.header import decode_header, make_header
from email.utils import parseaddr

HERE = os.path.dirname(os.path.abspath(__file__))
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODELE = os.environ.get("OLLAMA_MODELE", "qwen2.5:7b")
CLASSES = ["interesse", "question", "refus", "autre"]
RE_OPPOSITION = re.compile(
    r"d[ée]sinscri|ne (plus )?(me )?(contacter|recevoir|envoyer|écrire|ecrire)|"
    r"arr[êe]tez|supprimez[- ]moi|retirez[- ]moi|\bstop\b|unsubscribe|remove me|do not contact",
    re.IGNORECASE,
)


def _base():
    spec = importlib.util.spec_from_file_location("base_contacts", os.path.join(HERE, "base-contacts.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def texte_du_message(msg):
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain" and not part.get_filename():
                return part.get_payload(decode=True).decode(part.get_content_charset() or "utf-8", "replace")
        return ""
    if msg.get_content_type() == "text/plain":
        return msg.get_payload(decode=True).decode(msg.get_content_charset() or "utf-8", "replace")
    return ""


def analyser_message(brut):
    """Transforme les octets d'un message en dictionnaire. Ne touche à rien d'autre."""
    msg = email.message_from_bytes(brut)
    expediteur = parseaddr(msg.get("From", ""))[1].lower()
    sujet = str(make_header(decode_header(msg.get("Subject", ""))))
    return {
        "expediteur": expediteur,
        "sujet": sujet,
        "date": msg.get("Date", ""),
        "message_id": msg.get("Message-ID", ""),
        "texte": texte_du_message(msg)[:4000],
    }


def lire_reponses(serveur, port, user, mot_de_passe, dossier="INBOX", limite=200):
    """Lecture seule : BODY.PEEK ne marque pas le message comme lu."""
    reponses = []
    with imaplib.IMAP4_SSL(serveur, port) as imap:
        imap.login(user, mot_de_passe)
        imap.select(dossier, readonly=True)
        _, data = imap.search(None, "UNSEEN")
        ids = data[0].split()[-limite:]
        for num in ids:
            _, contenu = imap.fetch(num, "(BODY.PEEK[])")
            reponses.append(analyser_message(contenu[0][1]))
    return reponses


def opposition_demandee(texte):
    return bool(RE_OPPOSITION.search(texte or ""))


def classer(texte):
    """Classement local par Ollama. Renvoie une classe de CLASSES, ou « a verifier »."""
    prompt = (
        "Classe ce message de réponse à une prospection commerciale. "
        "Réponds uniquement par un JSON {\"classe\": \"...\"} avec une seule valeur parmi : "
        "interesse (veut en savoir plus), question (pose une question précise), "
        "refus (dit non sans demander d'arrêt), autre. Message :\n\n" + (texte or "")[:2000]
    )
    corps = json.dumps({
        "model": OLLAMA_MODELE,
        "messages": [{"role": "user", "content": prompt}],
        "format": "json",
        "stream": False,
        "options": {"temperature": 0},
    }).encode("utf-8")
    try:
        req = urllib.request.Request(f"{OLLAMA_URL}/api/chat", data=corps, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=120) as rep:
            contenu = json.loads(rep.read())["message"]["content"]
        classe = str(json.loads(contenu).get("classe", "")).strip().lower()
    except Exception:
        return "a verifier"
    return classe if classe in CLASSES else "a verifier"


def traiter(conn, reponse, base=None):
    """Enregistre une réponse. Ne répond jamais au prospect. Renvoie une ligne de résumé."""
    base = base or _base()
    adresse = reponse["expediteur"]
    if not adresse:
        return f"[inconnu] {reponse['sujet']} : expéditeur illisible, à vérifier"

    if opposition_demandee(reponse["texte"]):
        base.opposer(adresse, conn=conn)
        conn.commit()
        return f"[opposition] {adresse} : demande d'arrêt, adresse supprimée et enregistrée en opposition"

    ligne = conn.execute("SELECT id FROM prospects WHERE lower(email) = ?", (adresse,)).fetchone()
    classe = classer(reponse["texte"])
    if ligne is None:
        return f"[hors base] {adresse} ({classe}) : aucun prospect correspondant, rien enregistré"
    conn.execute(
        "INSERT INTO reponses (prospect_id, date, classement, resume, action) VALUES (?,?,?,?,?)",
        (ligne[0], date.today().isoformat(), classe, reponse["sujet"][:200], "à traiter par l'utilisateur"),
    )
    conn.commit()
    return f"[{classe}] {adresse} : {reponse['sujet'][:80]}"


def resume(lignes):
    if not lignes:
        return "Aucune nouvelle réponse."
    return f"Réponses du {date.today().isoformat()} ({len(lignes)}) :\n" + "\n".join(lignes)


def main():
    """Lit la boîte (lecture seule), classe, prépare le résumé. Ne répond à personne."""
    import sys

    env = os.environ
    requis = ["SMTP_HOST", "IMAP_HOST", "IMAP_USER", "IMAP_PASSWORD", "NOTIFY_TO"]
    manquants = [v for v in requis if not env.get(v)]
    if manquants:
        sys.exit("Variables absentes : " + ", ".join(manquants) + ". Rien n'a été lu.")
    reponses = lire_reponses(env["IMAP_HOST"], int(env.get("IMAP_PORT", "993")), env["IMAP_USER"], env["IMAP_PASSWORD"])
    base = _base()
    conn = base.connect()
    lignes = [traiter(conn, r, base) for r in reponses]
    conn.close()
    texte = resume(lignes)
    print(texte)

    import envoi

    eml = envoi.construire_eml(
        {"objet": "Résumé des réponses"}, env["NOTIFY_TO"], env.get("FROM_ADDR", ""), "Agence SAS",
        "<p>" + texte.replace(chr(10), "<br>") + "</p>", texte, env.get("FROM_ADDR", ""),
    )
    if envoi.dry_run():
        print("Résumé écrit (simulation) :", envoi.ecrire_simulation(eml, os.environ.get("SORTIE_SIMULATION", os.path.join(os.environ.get("TEMP", "."), "agence-sas-simulation"))))
    else:
        envoi.envoyer(eml, env["SMTP_HOST"], int(env.get("SMTP_PORT", "465")), env["SMTP_USER"], env["SMTP_PASSWORD"])
        print("Résumé envoyé à NOTIFY_TO.")


if __name__ == "__main__":
    main()
