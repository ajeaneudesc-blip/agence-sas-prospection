"""Envoi de TEST vers une adresse choisie par l'utilisateur (aperçu réel du design, sans prospect).
N'utilise pas les gardes de prospection : c'est un test explicitement demandé. Aucun prospect n'est touché."""
import os
import smtplib
import ssl
import sys
import importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))


def charger(nom, fichier):
    spec = importlib.util.spec_from_file_location(nom, os.path.join(HERE, fichier))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


envoi = charger("envoi", "envoi.py")
destinataire = sys.argv[1]
expediteur = os.environ["FROM_ADDR"]
nom_expediteur = os.environ.get("FROM_NAME", "Jean Eudes Adakanou")

corps = (
    "Bonjour Madame, Monsieur,\n\n"
    "Je vous remercie de prendre un instant pour me lire.\n\n"
    "En parcourant votre site, j'ai remarqué que des textes de remplissage « Lorem ipsum » apparaissent "
    "encore dans les sections plats et menu. Un visiteur peut alors avoir le sentiment que le site n'est pas "
    "tout à fait à jour, alors que vos plats méritent d'être découverts. Je suis moi-même installé à Maurice.\n\n"
    "Je suis designer et je conçois des campagnes et des contenus cohérents avec votre marque, pour vos "
    "réseaux sociaux et votre site.\n\n"
    "Souhaitez-vous recevoir une idée de campagne pour vos plats ?"
)
msg = {"objet": "[TEST] Une campagne pour Chez Pepe Mauritius", "corps": corps, "langue": "fr", "offre": "com"}
desinscription = f"mailto:{expediteur}?subject=Desinscription"
html = envoi.rendre_html(msg, "com", expediteur, desinscription)
texte = envoi.rendre_texte(msg, expediteur, desinscription)
eml = envoi.construire_eml(msg, destinataire, expediteur, nom_expediteur, html, texte, expediteur)

contexte = ssl.create_default_context()
with smtplib.SMTP_SSL(os.environ["SMTP_HOST"], int(os.environ.get("SMTP_PORT", "465")), context=contexte, timeout=60) as s:
    s.login(os.environ["SMTP_LOGIN"], os.environ["SMTP_KEY"])
    s.send_message(eml)
print("Test envoyé à", destinataire)
