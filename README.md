# agence-sas-prospection (public)

Code de l'automatisation de prospection de l'Agence SAS.

**Ce dépôt ne contient aucune donnée personnelle, aucun log contenant une donnée, aucun secret.**
Les données (contacts, oppositions, file d'envoi) sont dans le dépôt privé `agence-sas-donnees`, chiffrées (D16).

## Statut
Étape 2 : squelette. Le workflow `prospection` tourne du lundi au vendredi à 05:00 UTC (09:00, Maurice). Il ne fait rien d'autre que vérifier les garde-fous.

## Garde-fous
- `DRY_RUN` : `true` par défaut (variable de dépôt).
- `LIVE_SEND` : `false` par défaut. Passe à `true` seulement après validation d'ADM-002 et ADM-003 et d'un test SMTP OVH. Le workflow refuse un envoi réel tant que le module d'envoi n'existe pas.

## Secrets attendus (GitHub → Settings → Secrets and variables → Actions)
Noms seulement, valeurs jamais dans le dépôt ni dans le chat :
- `ANTHROPIC_API_KEY`
- `SMTP_USER`, `SMTP_PASSWORD`
- `IMAP_USER`, `IMAP_PASSWORD`
- `BASE_CONTACTS_PASSPHRASE`
- `DATA_REPO_TOKEN` (token fine-grained, accès au seul dépôt `agence-sas-donnees`)
- `NOTIFY_TO`

## Règles
Aucun envoi sans raison vérifiée, datée et sourcée. Maximum 5 contacts par semaine, 3 messages par adresse, jamais de relance avant 3 jours. Gabarits non marqués VALIDÉ : ne partent pas.
