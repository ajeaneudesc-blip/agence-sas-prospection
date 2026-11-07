"""Rédaction des messages de prospection via l'API Anthropic (étape 5).

Sortie attendue du modèle : un objet JSON {objet, corps, offre, langue, raison, source, date}.
Aucun message n'est accepté sans passer valider(). Un message refusé ne part pas.

Règles vérifiées :
  - clés présentes, langue fr ou en, offre connue (strategie exclue : gabarit G retiré) ;
  - raison d'au moins 10 caractères, source https, date AAAA-MM-JJ ;
  - corps de 60 à 100 mots ;
  - aucun chiffre, aucun prix, aucune monnaie, aucun pourcentage ;
  - aucun BRN, TAN, TVA, statut d'entreprise ;
  - aucun « nous », « we », « our » dans le corps ;
  - aucun client ou partenaire cité, ni « Start And Shift » ;
  - aucun lien, aucun « Cliquez » ;
  - une seule question, en fin de corps ;
  - premier message : formule de politesse fixe ; relances : sans formule.

Gabarit : seul un gabarit marqué VALIDÉ dans le fichier des modèles peut servir de base.

Usage : génération réelle seulement si ANTHROPIC_API_KEY est défini (secret GitHub, jamais dans le dépôt).
"""

import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
MODELES = os.path.join(
    HERE, "..", "Plans", "Prospection Mondiale", "20261028 Modeles De Messages.md"
)
MODEL = os.environ.get("MODELE_REDACTION", "claude-sonnet-5-5")

OFFRES_OK = {"site", "partenariat", "motion", "video", "com", "leads", "lancement"}
# Noms à ne jamais citer dans un message. Liste de départ, à compléter par l'utilisateur.
INTERDITS = ["Michel Francisco", "Rischka", "Cofina", "Start And Shift"]
POLITESSE = {
    "fr": "Je vous remercie de prendre un instant pour me lire.",
    "en": "Thank you for taking a moment to read this.",
}
SALUTATION = {"fr": "Bonjour", "en": "Hello"}

RE_CHIFFRE = re.compile(r"\d")
RE_MONNAIE = re.compile(r"[€$£%]|\b(euros?|dollars?|roupies?|MUR|Rs)\b", re.IGNORECASE)
RE_ENTREPRISE = re.compile(r"\b(BRN|TAN|TVA|VAT|SIRET|SIREN|RCS|NIF|SARL|SAS|Ltd|LLC|Pvt)\b")
RE_NOUS = re.compile(r"\b(nous|we|our|notre|nos)\b", re.IGNORECASE)
RE_LIEN = re.compile(r"https?://|www\.", re.IGNORECASE)
RE_CLIQUEZ = re.compile(r"cliquez", re.IGNORECASE)
RE_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
CLES = ["objet", "corps", "offre", "langue", "raison", "source", "date"]


def gabarits_valides(chemin=MODELES):
    """Renvoie {lettre_ou_nom: (offre, texte_fr)} pour les seuls gabarits marqués VALIDÉ."""
    with open(chemin, encoding="utf-8") as f:
        texte = f.read()
    valides = {}
    sections = re.split(r"^## ", texte, flags=re.MULTILINE)[1:]
    for sec in sections:
        titre, _, reste = sec.partition("\n")
        if "VALIDÉ" not in titre or "RETIRÉ" in titre:
            continue
        cle = titre.split(".", 1)[0].strip()
        offre_m = re.search(r"offre `([a-z]+)`", titre)
        if cle.startswith("Relance"):
            cle = "relance1" if "Relance 1" in titre else "relance2"
        fr = reste.split("### English", 1)[0]
        fr = fr.split("### Français", 1)[-1].strip()
        valides[cle] = (offre_m.group(1) if offre_m else None, fr)
    return valides


def valider(msg, type_envoi="premier"):
    """Renvoie la liste des motifs de refus. Liste vide = message acceptable."""
    motifs = []
    manquantes = [c for c in CLES if c not in msg]
    if manquantes:
        return ["clés manquantes : " + ", ".join(manquantes)]

    langue = str(msg["langue"]).lower()
    if langue not in SALUTATION:
        motifs.append("langue inconnue (fr ou en attendu)")
        langue = "fr"

    corps = str(msg["corps"])
    objet = str(msg["objet"])
    if msg["offre"] not in OFFRES_OK:
        motifs.append(f"offre inconnue ({msg['offre']})")

    raison = str(msg["raison"]).strip()
    if len(raison) < 10:
        motifs.append("raison absente ou trop courte")
    if not str(msg["source"]).startswith("https://"):
        motifs.append("source absente ou non https")
    if not RE_DATE.match(str(msg["date"])):
        motifs.append("date mal formée (AAAA-MM-JJ)")

    mots = corps.split()
    minimum = 60 if type_envoi == "premier" else 30
    if not minimum <= len(mots) <= 100:
        motifs.append(f"corps de {len(mots)} mots ({minimum} à 100 attendus)")
    if RE_CHIFFRE.search(corps + " " + objet):
        motifs.append("chiffre présent (prix ou chiffre ferme interdit)")
    if RE_MONNAIE.search(corps + " " + objet):
        motifs.append("monnaie ou pourcentage présent")
    if RE_ENTREPRISE.search(corps):
        motifs.append("identifiant ou statut d'entreprise présent (BRN, TAN, TVA, SAS...)")
    if RE_NOUS.search(corps):
        motifs.append("« nous », « we », « our » ou équivalent dans le corps")
    for nom in INTERDITS:
        if nom.lower() in (corps + " " + objet).lower():
            motifs.append(f"nom interdit cité ({nom})")
    if RE_LIEN.search(corps):
        motifs.append("lien présent dans le corps")
    if RE_CLIQUEZ.search(corps):
        motifs.append("« Cliquez » interdit")

    questions = corps.count("?")
    if questions != 1:
        motifs.append(f"{questions} question(s) : une seule, en fin de corps")
    elif not corps.rstrip().endswith("?"):
        motifs.append("la question n'est pas en fin de corps")

    if type_envoi == "premier":
        if not corps.lstrip().startswith(SALUTATION[langue]):
            motifs.append(f"premier message : doit commencer par « {SALUTATION[langue]} »")
        if POLITESSE[langue] not in corps:
            motifs.append("premier message : formule de politesse fixe absente")
    else:
        if POLITESSE[langue] in corps:
            motifs.append("relance : la formule de politesse du premier message ne doit pas être répétée")
    return motifs


def rendu_sans_api(prospect, gabarit_fr, type_envoi="premier"):
    """Secours sans API : remplit le gabarit VALIDÉ avec la phrase de raison vérifiée du prospect.
    Le texte reste celui du gabarit validé ; seules les accolades sont remplies. Même validateur ensuite."""
    relance = type_envoi.startswith("relance")
    if relance:
        phrase = (prospect.get("relance") or "").strip()
        question = (prospect.get("question") or "").strip()
        if not phrase or not question:
            raise ValueError("Phrase ou question de relance absente : relance non rédigée.")
    else:
        phrase = (prospect.get("phrase") or "").strip()
        if not phrase:
            raise ValueError("Phrase de raison absente : impossible de rédiger sans API.")
        question = ""
    lignes = gabarit_fr.split("\n")
    objet = ""
    corps_l = []
    for ligne in lignes:
        if ligne.strip().startswith("Bouton"):
            break
        if ligne.startswith("Objet :"):
            objet = ligne[len("Objet :"):].strip()
            continue
        corps_l.append(ligne)
    corps = "\n".join(corps_l).strip()
    nom = prospect.get("nom", "")
    if relance:
        # La relance reprend l'objet du premier message : « Re : » suivi du nom de l'entreprise.
        objet = "Re : " + nom
        corps = re.sub(r"\{Même objet[^}]*\}", "", corps)
        corps = re.sub(r"\{une phrase[^}]*\}", phrase, corps)
        corps = re.sub(r"\{La même question[^}]*\}", question, corps)
    objet = re.sub(r"\{Entreprise\}", nom, objet)
    corps = re.sub(r"\{Entreprise\}", nom, corps)
    corps = re.sub(r"\{Prénom[^}]*\}", "Madame, Monsieur", corps)
    corps = re.sub(r"\{RAISON[^}]*\}", phrase, corps)
    corps = re.sub(r"\{produit ou service\}", prospect.get("produit") or "vos services", corps)
    corps = re.sub(r"\{Marque\}", nom, corps)
    corps = re.sub(r"\{Agence\}", nom, corps)
    if "{" in corps or "{" in objet:
        raise ValueError("Accolades restantes dans le gabarit : rédaction refusée.")
    if prospect.get("pays") == "MU":
        # Prospect à Maurice : précisé juste après la présentation (« Je suis … »). Autres pays : rien ajouté.
        paragraphes = corps.split("\n\n")
        for i, p in enumerate(paragraphes):
            if p.startswith("Je suis "):
                paragraphes[i] = p.rstrip() + " Je suis basé à Maurice."
                break
        corps = "\n\n".join(paragraphes)
    return {
        "objet": objet,
        "corps": corps,
        "offre": prospect.get("offre", ""),
        "langue": "fr",
        "raison": prospect.get("raison", ""),
        "source": prospect.get("source_url", ""),
        "date": prospect.get("date_consultation", ""),
        # Décision de l'utilisateur : la phrase écrite et relue par lot suffit comme humanisation sans API.
        "humanise": True,
    }


RegleHumanizer = (
    "Réécris ce message de prospection en français pour qu'il sonne humain, poli, et centré sur le problème "
    "du prospect. Garde tous les faits, la structure, l'offre et la question finale. Interdits : « ce n'est pas X, "
    "c'est Y », formules de « punchline » en fin de paragraphe, tirets longs (— et –), listes de trois par "
    "réflexe, mots enflés (crucial, pivotal, testament, vibrant, robuste), phrases de connivence. Pas de chiffre, "
    "pas de prix, pas de « nous ». Réponds uniquement par le JSON demandé."
)


def humaniser(msg, prospect):
    """Passe le message par l'API avec les règles de l'humanizer. Renvoie le message réécrit, validé."""
    import anthropic

    cle = os.environ.get("ANTHROPIC_API_KEY")
    if not cle:
        raise RuntimeError("ANTHROPIC_API_KEY absent : humanizer impossible.")
    client = anthropic.Anthropic(api_key=cle)
    consigne = (
        RegleHumanizer + "\n\nMessage :\n" + json.dumps(msg, ensure_ascii=False)
        + "\n\nRéponds par un objet JSON avec les clés objet, corps, offre, langue, raison, source, date."
    )
    rep = client.messages.create(model=MODEL, max_tokens=1200, messages=[{"role": "user", "content": consigne}])
    texte = "".join(b.text for b in rep.content if getattr(b, "type", "") == "text").strip()
    texte = re.sub(r"^```(?:json)?|```$", "", texte).strip()
    nouveau = json.loads(texte)
    motifs = valider(nouveau, "premier")
    if motifs:
        raise ValueError("Après humanizer, message refusé : " + " ; ".join(motifs))
    nouveau["humanise"] = True
    return nouveau


def generer(prospect, gabarit_fr, type_envoi="premier"):
    """Appelle l'API et renvoie le message validé, ou lève une erreur. Jamais d'envoi ici.
    Si l'API échoue (ex. solde insuffisant), bascule sur rendu_sans_api, puis le même validateur."""
    try:
        return _generer_api(prospect, gabarit_fr, type_envoi)
    except Exception as e:
        print(f"[API indisponible : {type(e).__name__}] rédaction par gabarit validé pour {prospect.get('nom')}")
        msg = rendu_sans_api(prospect, gabarit_fr, type_envoi)
        motifs = valider(msg, type_envoi)
        if motifs:
            raise ValueError("Message refusé (sans API) : " + " ; ".join(motifs))
        return msg


def _generer_api(prospect, gabarit_fr, type_envoi="premier"):
    import anthropic

    cle = os.environ.get("ANTHROPIC_API_KEY")
    if not cle:
        raise RuntimeError("ANTHROPIC_API_KEY absent : rien n'a été généré.")
    client = anthropic.Anthropic(api_key=cle)
    consigne = (
        "Rédige un message de prospection à partir du gabarit validé ci-dessous. "
        "Remplace les passages entre accolades. Réponds uniquement par un objet JSON avec les clés "
        "objet, corps, offre, langue, raison, source, date. Respecte toutes les règles du dépôt : "
        "60 à 100 mots, aucun chiffre, aucun « nous », une seule question finale, aucun nom de client, "
        "aucune donnée d'entreprise. La raison doit être le fait vérifié fourni, avec sa source et sa date.\n\n"
        f"Gabarit :\n{gabarit_fr}\n\nProspect :\n{json.dumps(prospect, ensure_ascii=False)}"
    )
    rep = client.messages.create(
        model=MODEL,
        max_tokens=1200,
        messages=[{"role": "user", "content": consigne}],
    )
    texte = "".join(b.text for b in rep.content if getattr(b, "type", "") == "text").strip()
    texte = re.sub(r"^```(?:json)?|```$", "", texte).strip()
    msg = json.loads(texte)
    motifs = valider(msg, type_envoi)
    if motifs:
        raise ValueError("Message refusé : " + " ; ".join(motifs))
    return humaniser(msg, prospect)
