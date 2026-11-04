"""Rendu et envoi des messages de prospection (étape 6).

Par défaut, rien n'est envoyé : DRY_RUN=true écrit les messages en fichiers .eml dans un dossier de sortie.
Un envoi réel exige DRY_RUN=false ET LIVE_SEND=true, posés par l'utilisateur après ADM-002, ADM-003
et un test SMTP OVH. Sans cela, le script refuse.

Garde-fous contrôlés avant tout envoi (peut_envoyer) :
  - adresse non en opposition, pays non exclu (Pays Email Exclus.txt) ;
  - 3 messages au maximum par adresse, relance 1 au moins 3 jours après le premier, relance 2 au moins 4 jours après la relance 1 ;
  - 5 envois au maximum par semaine civile ;
  - jours ouvrés seulement (lundi à vendredi). Jours fériés mauriciens : à ajouter (non fait).
"""

import json
import os
import re
import smtplib
import ssl
from datetime import date, timedelta
from email.message import EmailMessage
from email.utils import formatdate, make_msgid
from html import escape
from urllib.parse import quote

HERE = os.path.dirname(os.path.abspath(__file__))
OUTILS = os.path.join(HERE, "..", "Outils", "Prospection Mondiale")
MODELE_HTML = os.path.join(OUTILS, "Modele Mail.html")
OFFRES_JSON = os.path.join(OUTILS, "Offres Mail.json")
MAX_PAR_SEMAINE = 5
MAX_PAR_ADRESSE = 3
DELAI_RELANCE1 = 3
DELAI_RELANCE2 = 4


def dry_run():
    return os.environ.get("DRY_RUN", "true").lower() != "false"


def live_send_autorise():
    return os.environ.get("LIVE_SEND", "false").lower() == "true"


def jour_ouvre(d):
    return d.weekday() < 5


def peut_envoyer(conn, prospect_id, type_envoi, email, aujourdhui=None, exclus=frozenset()):
    """Renvoie la liste des motifs de refus. Liste vide = envoi autorisé."""
    aujourdhui = aujourdhui or date.today()
    motifs = []
    if not jour_ouvre(aujourdhui):
        motifs.append("week-end : envoi en jours ouvrés seulement")

    pays = conn.execute("SELECT pays FROM prospects WHERE id = ?", (prospect_id,)).fetchone()
    if pays is None:
        return ["prospect introuvable"]
    if pays[0] and pays[0].upper() in exclus:
        motifs.append(f"pays exclu ({pays[0]})")

    import importlib.util

    spec = importlib.util.spec_from_file_location("base_contacts", os.path.join(HERE, "base-contacts.py"))
    base = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(base)
    if base.est_en_opposition(conn, email):
        motifs.append("adresse en opposition")

    envoyes = conn.execute(
        "SELECT type, date_envoi FROM outbox WHERE prospect_id = ? AND statut = 'envoye' ORDER BY date_envoi",
        (prospect_id,),
    ).fetchall()
    if len(envoyes) >= MAX_PAR_ADRESSE:
        motifs.append("3 messages déjà envoyés à cette adresse")
    types = [t for t, _ in envoyes]
    dates = {t: date.fromisoformat(d) for t, d in envoyes if d}

    if type_envoi == "premier":
        if "premier" in types:
            motifs.append("premier message déjà envoyé")
    elif type_envoi == "relance1":
        if "premier" not in dates:
            motifs.append("relance 1 sans premier message envoyé")
        elif (aujourdhui - dates["premier"]).days < DELAI_RELANCE1:
            motifs.append(f"relance 1 : moins de {DELAI_RELANCE1} jours après le premier message")
    elif type_envoi == "relance2":
        if "relance1" not in dates:
            motifs.append("relance 2 sans relance 1 envoyée")
        elif (aujourdhui - dates["relance1"]).days < DELAI_RELANCE2:
            motifs.append(f"relance 2 : moins de {DELAI_RELANCE2} jours après la relance 1")
    else:
        motifs.append(f"type d'envoi inconnu ({type_envoi})")

    debut_semaine = aujourdhui - timedelta(days=aujourdhui.weekday())
    cette_semaine = conn.execute(
        "SELECT count(*) FROM outbox WHERE statut = 'envoye' AND date_envoi >= ?",
        (debut_semaine.isoformat(),),
    ).fetchone()[0]
    if cette_semaine >= MAX_PAR_SEMAINE:
        motifs.append(f"plafond de {MAX_PAR_SEMAINE} envois par semaine atteint")
    return motifs


def _offre(cle, langue):
    with open(OFFRES_JSON, encoding="utf-8") as f:
        offres = json.load(f)
    return offres[cle][langue]  # [libellé du bouton, titre, texte pré-rempli]


RAW_BASE = os.environ.get(
    "RAW_BASE", "https://raw.githubusercontent.com/ajeaneudesc-blip/agence-sas-prospection/main"
)
ASSETS_DIR = os.path.join(OUTILS, "Assets Mail")


def _url_asset(nom_fichier):
    return RAW_BASE + "/Administratif/Outils/Prospection%20Mondiale/Assets%20Mail/" + quote(nom_fichier)


def _dimensions_gif(chemin):
    with open(chemin, "rb") as f:
        h = f.read(10)
    return int.from_bytes(h[6:8], "little"), int.from_bytes(h[8:10], "little")


def _dimensions_png(chemin):
    with open(chemin, "rb") as f:
        h = f.read(24)
    return int.from_bytes(h[16:20], "big"), int.from_bytes(h[20:24], "big")


def _ressources(offre_cle, langue):
    """Retourne (bannière, bouton, photo) : chemins locaux existants, sinon None."""
    with open(OFFRES_JSON, encoding="utf-8") as f:
        nom = json.load(f)[offre_cle]["nom"]
    suffixe = "Fr" if langue == "fr" else "En"
    candidats = {
        "banniere": f"Banniere {nom}.gif",
        "bouton": f"Bouton {nom} {suffixe}.png",
        "photo": "Photo Signature.png",
    }
    return {
        cle: (nom_f if os.path.exists(os.path.join(ASSETS_DIR, nom_f)) else None)
        for cle, nom_f in candidats.items()
    }


def rendre_html(msg, offre_cle, adresse_contact, desinscription_mailto, hero_url=None, photo_url=None):
    """Gabarit HTML validé : bannière animée de l'offre, bouton graphique, photo de signature.
    Sans logo, sans slogan, sans nom « Start And Shift » (offre personnelle)."""
    with open(MODELE_HTML, encoding="utf-8") as f:
        html = f.read()

    langue = msg["langue"] if msg["langue"] in ("fr", "en") else "fr"
    ressources = _ressources(offre_cle, langue)
    corps_html = "".join(
        f"<p style=\"margin:0 0 14px 0;\">{escape(p.strip()).replace(chr(10), '<br>')}</p>"
        for p in re.split(r"\n\s*\n", msg["corps"].strip())
        if p.strip()
    )

    bouton_txt, _titre, pre_rempli = _offre(offre_cle, langue)
    sujet_reponse = "Demande" if langue == "fr" else "Request"
    lien = (
        f"mailto:{adresse_contact}?subject={sujet_reponse}&body={pre_rempli}".replace(" ", "%20")
    )
    if ressources["bouton"]:
        bw, bh = _dimensions_png(os.path.join(ASSETS_DIR, ressources["bouton"]))
        cta = (
            f'<a href="{escape(lien)}" style="text-decoration:none;">'
            f'<img src="{escape(_url_asset(ressources["bouton"]))}" width="{bw}" height="{bh}" '
            f'alt="{escape(bouton_txt)}" style="display:block;margin:24px auto 0 auto;border:0;'
            f'outline:none;width:{bw}px;max-width:100%;height:auto;"></a>'
        )
    else:
        cta = (
            f'<table role="presentation" align="center" cellpadding="0" cellspacing="0" border="0" '
            f'style="margin:24px auto 0 auto;"><tr><td align="center" bgcolor="#095CFF" '
            f'style="border-radius:999px;padding:12px 22px;">'
            f'<a href="{escape(lien)}" style="font-family:Geist,Segoe UI,Helvetica,Arial,sans-serif;'
            f'font-size:15px;font-weight:600;color:#FFFFFF;text-decoration:none;">{escape(bouton_txt)}</a>'
            f"</td></tr></table>"
        )
    pied = (
        f'<div style="font-size:11px;line-height:16px;color:#8A8A8A;padding-top:18px;">'
        f'Vous ne souhaitez plus recevoir de message ? '
        f'<a href="{escape(desinscription_mailto)}" style="color:#8A8A8A;">Se désinscrire</a>.</div>'
    )
    preheader = _titre
    remplacements = {
        "{{LANG}}": langue,
        "{{SUBJECT}}": escape(msg["objet"]),
        "{{PREHEADER}}": escape(preheader),
        "{{CORPS}}": corps_html + pied,
        "{{CTA_BLOCK}}": cta,
        "{{EMAIL}}": escape(adresse_contact),
        "{{ROLE}}": "Designer",
        "{{SLOGAN}}": "",
    }
    for cle, valeur in remplacements.items():
        html = html.replace(cle, valeur)

    # Logo et slogan retirés (offre personnelle). Image héros et photo : seulement si une URL publique est fournie.
    html = re.sub(r"<!--LOGO-->.*?<!--/LOGO-->", "", html, flags=re.S)
    html = re.sub(r"<!--SLOGAN-->.*?<!--/SLOGAN-->", "", html, flags=re.S)
    if ressources["banniere"] or hero_url:
        url_b = hero_url or _url_asset(ressources["banniere"])
        bw, bh = _dimensions_gif(os.path.join(ASSETS_DIR, ressources["banniere"])) if ressources["banniere"] else (600, 300)
        html = html.replace("{{HERO_SRC}}", escape(url_b))
        html = html.replace("{{HERO_W}}", str(bw)).replace("{{HERO_H}}", str(bh))
        html = html.replace("{{HERO_ALT}}", escape(_titre))
    else:
        html = re.sub(r'<img src="\{\{HERO_SRC\}\}"[^>]*>', "", html)
    if ressources["photo"] or photo_url:
        url_p = photo_url or _url_asset(ressources["photo"])
        html = html.replace("{{PHOTO_SRC}}", escape(url_p))
    else:
        html = re.sub(r"<!--PHOTO-->.*?<!--/PHOTO-->", "", html, flags=re.S)
    if "{{" in html:
        raise ValueError("Placeholder non remplacé dans le gabarit HTML")
    if "Start And Shift" in html or "start and shift" in html.lower():
        raise ValueError("Le nom « Start And Shift » ne doit pas apparaître dans une offre personnelle")
    return html


def rendre_texte(msg, adresse_contact, desinscription_mailto):
    pied = f"\n\n--\nVous ne souhaitez plus recevoir de message ? Écrivez à : {desinscription_mailto}"
    return msg["corps"].strip() + pied


def construire_eml(msg, destinataire, expediteur_addr, expediteur_nom, html, texte, desinscription_addr):
    m = EmailMessage()
    m["Subject"] = msg["objet"]
    m["From"] = f"{expediteur_nom} <{expediteur_addr}>"
    m["To"] = destinataire
    m["Date"] = formatdate(localtime=True)
    m["Message-ID"] = make_msgid(domain=expediteur_addr.split("@", 1)[1])
    m["List-Unsubscribe"] = f"<mailto:{desinscription_addr}?subject=Desinscription>"
    m.set_content(texte)
    m.add_alternative(html, subtype="html")
    return m


def envoyer(eml, serveur, port, user, mot_de_passe):
    """Envoi réel. Appelé seulement si DRY_RUN=false ET LIVE_SEND=true."""
    if dry_run() or not live_send_autorise():
        raise RuntimeError("Envoi réel refusé : DRY_RUN doit être false et LIVE_SEND true.")
    contexte = ssl.create_default_context()
    if port == 465:
        with smtplib.SMTP_SSL(serveur, port, context=contexte, timeout=30) as s:
            s.login(user, mot_de_passe)
            s.send_message(eml)
    else:
        with smtplib.SMTP(serveur, port, timeout=30) as s:
            s.starttls(context=contexte)
            s.login(user, mot_de_passe)
            s.send_message(eml)


def ecrire_simulation(eml, dossier):
    os.makedirs(dossier, exist_ok=True)
    chemin = os.path.join(dossier, re.sub(r"[^A-Za-z0-9]+", "-", eml["Message-ID"])[:80] + ".eml")
    with open(chemin, "wb") as f:
        f.write(bytes(eml))
    return chemin
