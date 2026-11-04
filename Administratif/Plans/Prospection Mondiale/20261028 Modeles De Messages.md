# Modèles de messages : prospection mondiale (D80)

Règles pour tous les messages (décision D87 du 2026-10-28) : le message parle à la première personne (« je », Jean Eudes), « vous » pour le prospect, jamais « nous » ni « we », vouvoiement en français ; le corps ne cite ni lieu ni le nom Start And Shift : les messages sont uniquement au nom de Jean Eudes Adakanou, sans logo ni slogan (D88) ; une seule question simple à la fin (« Souhaitez-vous recevoir… ? »), le bouton dessiné en dessous répond oui. Jamais de « Cliquez sur… ». Un modèle non marqué « VALIDÉ » n'est pas prêt, 60 à 100 mots, une seule raison précise et vérifiable, un seul appel à l'action, aucun prix ni chiffre ferme (R13), aucun client ni partenaire cité (R1), aucun statut d'entreprise (R17). La signature et le slogan sont ajoutés par le gabarit, la ligne de désinscription par la version texte : ne les écris pas dans le corps. Chaque premier message commence par « Bonjour », puis une phrase de politesse fixe (« Je vous remercie de prendre un instant pour me lire. » / « Thank you for taking a moment to read this. »), puis la raison ; les relances n'ont pas cette phrase. Les passages entre accolades sont à remplacer ; si la raison précise manque, le message ne part pas (R12).

Objet : court, factuel, sans majuscules criardes ni point d'exclamation, sans « Re: » artificiel. Relances : mêmes règles, jamais avant 3 jours, jamais plus de 3 messages au total par adresse (appliqué par `Envoi.py`).

## A. Entreprise sans site ou au site faible (offre `site`) : VALIDÉ le 2026-10-28

### Français
Objet : Un site pour {Entreprise}

Bonjour {Prénom ou « Madame, Monsieur »},

Je vous remercie de prendre un instant pour me lire.

{RAISON : fait vérifié et daté, ex. « Votre fiche Google Maps est très bien notée, mais aucun site n'y est indiqué. »}

Je suis designer et je crée des sites vitrine clairs et animés pour des activités locales. Une seule page suffit pour être trouvé et recevoir des demandes.

Souhaitez-vous recevoir un exemple pensé pour votre activité ?

Bouton : « Recevoir un exemple de site ». Texte pré-rempli de la réponse : « Bonjour, je souhaite recevoir un exemple de site pour mon activité. »

### English
Subject: A website for {Company}

Hello {First name or "Sir or Madam"},

Thank you for taking a moment to read this.

{REASON: verified, dated fact, e.g. "Your Google Maps listing is highly rated, but it links to no website."}

I'm a designer and I build clear, animated showcase sites for local businesses. A single page is enough to be found and to receive enquiries.

Would you like to see an example designed for your business?

Button: "Get a website example". Pre-filled reply: "Hello, I would like to get a website example for my business."

## B. Agence à sous-traiter, marque blanche (offre `partenariat`) : VALIDÉ le 2026-10-28, sans bouton

### Français
Objet : Un renfort pour {Agence}

Bonjour {Prénom ou « Madame, Monsieur »},

Je vous remercie de prendre un instant pour me lire.

{RAISON : ex. « Votre portfolio montre peu de vidéos animées. »}

Quand un client demande de l'animation, du web ou de la vidéo et que votre équipe n'a pas la place, la commande peut partir ailleurs.

Je travaille en marque blanche : vous gardez la relation client et vous signez le travail.

Un échange de quinze minutes vous conviendrait-il ? Répondez simplement à ce message avec le créneau qui vous arrange.

Pas de bouton pour cette offre (réglage `cta: false` dans `Offres Mail.json`) : la réponse se fait par e-mail. Offre personnelle (réglage `perso: true`) : ni logo ni mention Start And Shift, signature « Jean Eudes Adakanou, Designer », aucun accusé de réception automatique ; l'agent prévient Jean Eudes dès qu'une réponse arrive.

### English
Subject: Extra capacity for {Agency}

Hello {First name or "Sir or Madam"},

Thank you for taking a moment to read this.

{REASON: e.g. "Your portfolio shows few animated videos."}

When a client asks for animation, web or video and your team has no room, the job can go elsewhere.

I work white label: you keep the client relationship and you sign the work.

Would a fifteen-minute call suit you? Simply reply to this message with a time that works for you.

No button for this offer: the reply is by email.

## C. PME à vidéo ou visuels faibles (offre `motion`) : VALIDÉ le 2026-10-28

### Français
Objet : Une animation pour {Entreprise}

Bonjour {Prénom ou « Madame, Monsieur »},

Je vous remercie de prendre un instant pour me lire.

{RAISON : ex. « Votre page Instagram publie surtout des photos fixes, alors que vos produits gagneraient à être montrés en mouvement. »}

Je suis designer et je crée des animations courtes de 15 à 30 secondes pour les réseaux sociaux et le web, livrées dans les formats prêts à publier.

Souhaitez-vous recevoir une idée d'animation pour {produit ou service} ?

Bouton : « Recevoir une idée d'animation ». Texte pré-rempli de la réponse : « Bonjour, je souhaite recevoir une idée d'animation pour mon activité. »

### English
Subject: An animation for {Company}

Hello {First name or "Sir or Madam"},

Thank you for taking a moment to read this.

{REASON: e.g. "Your Instagram page mostly posts still photos, while your products would benefit from being shown in motion."}

I'm a designer and I create 15 to 30 second animations for social media and the web, delivered in ready-to-publish formats.

Would you like an animation idea for {product or service}?

Button: "Get an animation idea". Pre-filled reply: "Hello, I would like to get an animation idea for my business."

## D. Startup ou marque en lancement

### Français
Objet : Un logo animé pour le lancement de {Marque}

Bonjour {Prénom},

Je vous remercie de prendre un instant pour me lire.

{RAISON : ex. « Le lancement de {Marque} est annoncé sur votre page, avec un logo encore fixe. »}

Start And Shift conçoit l'identité animée des marques qui démarrent : logo animé, kit réutilisable, puis courte vidéo de présentation.

Un échange de quinze minutes vous conviendrait-il cette semaine ?

### English
Subject: An animated logo for the launch of {Brand}

Hello {First name},

Thank you for taking a moment to read this.

{REASON: e.g. "The launch of {Brand} is announced on your page, with a still logo."}

Start And Shift designs the animated identity of new brands: animated logo, reusable kit, then a short presentation video.

Would a fifteen-minute call suit you this week?

## E. Entreprise dont les vidéos manquent ou datent (offre `video`) : VALIDÉ le 2026-10-28

### Français
Objet : Une vidéo pour {Entreprise}

Bonjour {Prénom ou « Madame, Monsieur »},

Je vous remercie de prendre un instant pour me lire.

{RAISON : ex. « Votre site présente vos produits en photos, mais aucune vidéo ne les montre en situation. »}

Je suis designer et je réalise des vidéos courtes, claires et faciles à partager pour présenter une activité, un produit ou un service.

Souhaitez-vous recevoir une idée de vidéo pour {produit ou service} ?

Bouton : « Recevoir une idée de vidéo ». Texte pré-rempli de la réponse : « Bonjour, je souhaite recevoir une idée de vidéo pour mon activité. »

### English
Subject: A video for {Company}

Hello {First name or "Sir or Madam"},

Thank you for taking a moment to read this.

{REASON: e.g. "Your website shows your products in photos, but no video shows them in use."}

I'm a designer and I make short, clear videos that are easy to share, to present a business, a product or a service.

Would you like a video idea for {product or service}?

Button: "Get a video idea". Pre-filled reply: "Hello, I would like to get a video idea for my business."

## F. Entreprise à la communication peu lisible (offre `com`) : VALIDÉ le 2026-10-28

### Français
Objet : Une campagne pour {Entreprise}

Bonjour {Prénom ou « Madame, Monsieur »},

Je vous remercie de prendre un instant pour me lire.

{RAISON : ex. « Vos publications changent de style d'une semaine à l'autre, sans fil conducteur visible. »}

Je suis designer et je conçois des campagnes et des contenus cohérents avec votre marque, pour vos réseaux sociaux et votre site.

Souhaitez-vous recevoir une idée de campagne pour {produit ou service} ?

Bouton : « Recevoir une idée de campagne ». Texte pré-rempli de la réponse : « Bonjour, je souhaite recevoir une idée de campagne pour mon activité. »

### English
Subject: A campaign for {Company}

Hello {First name or "Sir or Madam"},

Thank you for taking a moment to read this.

{REASON: e.g. "Your posts change style from one week to the next, with no visible common thread."}

I'm a designer and I create campaigns and content that match your brand, for your social media and your website.

Would you like a campaign idea for {product or service}?

Button: "Get a campaign idea". Pre-filled reply: "Hello, I would like to get a campaign idea for my business."

## G. Toute entreprise qui veut vendre davantage (offre `strategie`) : RETIRÉ pour l'instant, ne pas envoyer (2026-10-28)

Exception décidée le 2026-10-28 : ce modèle part sans raison vérifiée propre au prospect. Il pose un problème vrai quel que soit le volume de commandes. Le nom de l'entreprise, le prénom et le produit restent à vérifier.

### Français
Objet : Une idée pour {Entreprise}

Bonjour {Prénom ou « Madame, Monsieur »},

Je vous remercie de prendre un instant pour me lire.

Que vous receviez beaucoup de commandes, quelques-unes ou aucune, une question revient : qui d'autre pourrait commander chez vous ?

Avec une cible et un message bien posés, chaque visite et chaque publication a un but.

Souhaitez-vous recevoir une stratégie de communication et de vente personnalisée, sans engagement ?

Bouton : « Recevoir ma stratégie ». Texte pré-rempli de la réponse : « Bonjour, je souhaite recevoir une stratégie de communication et de vente personnalisée. »

### English
Subject: An idea for {Company}

Hello {First name or "Sir or Madam"},

Thank you for taking a moment to read this.

Whether you get many orders, a few or none, one question keeps coming back: who else could order from you?

With a clear target and message, every visit and every post has a purpose.

Would you like to receive a personalised communication and sales strategy, with no commitment?

Button: "Get my strategy". Pre-filled reply: "Hello, I would like to get a personalised communication and sales strategy."

## H. Entreprise qui veut de nouveaux clients (offre `leads`) : VALIDÉ le 2026-10-28

### Français
Objet : Vos prochains clients, {Entreprise}

Bonjour {Prénom ou « Madame, Monsieur »},

Je vous remercie de prendre un instant pour me lire.

Vos prochains clients existent déjà : ils cherchent ce que vous vendez sans savoir que vous existez.

Je repère les personnes et les entreprises qui ont besoin de votre offre et je prépare la façon de les contacter.

Souhaitez-vous parler de vos futurs clients ?

Bouton : « Ça m'intéresse ». Texte pré-rempli de la réponse : « Bonjour, ça m'intéresse. Je souhaite parler de mes futurs clients. »

### English
Subject: Your next clients, {Company}

Hello {First name or "Sir or Madam"},

Thank you for taking a moment to read this.

Your next clients already exist: they are looking for what you sell without knowing you exist.

I identify the people and companies that need your offer and prepare how to reach them.

Would you like to talk about your next clients?

Button: "I'm interested". Pre-filled reply: "Hello, I'm interested. I would like to talk about my next clients."

## I. Startup ou marque en lancement (offre `lancement`) : VALIDÉ le 2026-10-28

### Français
Objet : Le lancement de {Marque}

Bonjour {Prénom ou « Madame, Monsieur »},

Je vous remercie de prendre un instant pour me lire.

{RAISON : ex. « Le lancement de {Marque} est annoncé sur votre page. »}

Le jour du lancement, vos premiers clients jugent {Marque} sur ce qu'ils voient : une identité claire et un site qui donne envie d'aller plus loin.

Je conçois l'identité et le site des marques qui démarrent.

Cela vous intéresse-t-il ?

Bouton : « Ça m'intéresse ». Texte pré-rempli de la réponse : « Bonjour, ça m'intéresse. Je souhaite parler de mon lancement. »

### English
Subject: The launch of {Brand}

Hello {First name or "Sir or Madam"},

Thank you for taking a moment to read this.

{REASON: e.g. "The launch of {Brand} is announced on your page."}

On launch day, your first customers judge {Brand} by what they see: a clear identity and a website that makes them want to go further.

I design the identity and the website of brands that are starting out.

Is this of interest to you?

Button: "I'm interested". Pre-filled reply: "Hello, I'm interested. I would like to talk about my launch."

## Relance 1 (3 jours ou plus après le premier message) : VALIDÉ le 2026-10-28

Même champ `offre` que le premier message (même bannière, même bouton). Pas de phrase de politesse après « Bonjour ».

### Français
Objet : {Même objet que le premier message}

Bonjour {Prénom ou « Madame, Monsieur »},

Je reviens brièvement sur mon message précédent : {une phrase qui reprend l'offre, avec d'autres mots}.

{La même question que dans le premier message.}

Si le moment ne s'y prête pas, aucun souci.

### English
Subject: {Same subject as the first message}

Hello {First name or "Sir or Madam"},

I am following up briefly on my previous message: {one sentence restating the offer, in different words}.

{The same question as in the first message.}

If the timing is not right, no problem at all.

## Relance 2 (dernier message, 4 jours ou plus après la relance 1) : VALIDÉ le 2026-10-28

### Français
Objet : {Même objet que le premier message}

Bonjour {Prénom ou « Madame, Monsieur »},

Dernier message de ma part sur ce sujet : {une phrase qui reprend l'offre}. Vous pouvez répondre à tout moment, ou ignorer ce courrier : je ne vous écrirai plus.

### English
Subject: {Same subject as the first message}

Hello {First name or "Sir or Madam"},

This is my last message on this topic: {one sentence restating the offer}. You can reply at any time, or ignore this email: I will not write again.

## Offre, bannière et bouton (champ `offre`)
Le champ `offre` du fichier d'envoi choisit en même temps l'illustration animée du haut et le bouton dessiné, d'après ce que le message propose. Les libellés sont dans `Outils/Prospection Mondiale/Offres Mail.json` (seul l'utilisateur les modifie) :
- `motion` : « Recevoir une idée d'animation » / « Get an animation idea » (cible C par défaut)
- `site` : « Recevoir un exemple de site » / « Get a website example » (cible A)
- `video` : « Recevoir une idée de vidéo » / « Get a video idea »
- `com` : « Recevoir une idée de campagne » / « Get a campaign idea »
- `strategie` : « Recevoir une première piste » / « Get a first direction »
- `leads` : « Parler de vos futurs clients » / « Talk about your next clients »
- `lancement` : « Parler de votre lancement » / « Talk about your launch » (cible D)
- `partenariat` : « Planifier 15 minutes » / « Book 15 minutes » (cible B)
Un message qui propose plusieurs choses (site et animation, par exemple) choisit l'offre principale, celle de la première phrase d'offre. Le bouton ouvre une réponse par e-mail vers contact@ : aucun lien externe, aucun suivi. Pas de « Voir les prix » : aucune page de prix n'existe et R13 interdit un chiffre ferme avant devis validé. Si une page de réalisations est publiée plus tard, `cta_url` peut y mener.

## Autres langues
Écris le message dans la langue du prospect sur la même structure (raison, offre, un seul appel à l'action) et renseigne le champ `opt_out` dans la même langue. Si la qualité n'est pas sûre, écris en anglais.
