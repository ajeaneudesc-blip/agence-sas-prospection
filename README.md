# agence-sas-prospection (public)

Code de l'automatisation de prospection de l'Agence SAS.

**Ce dépôt ne contient aucune donnée personnelle, aucun log contenant une donnée, aucun secret.**
Les données (contacts, oppositions, file d'envoi) sont dans le dépôt privé `agence-sas-donnees`, chiffrées (D16).

## Statut
Étape 2 : squelette. Le workflow `prospection` tourne du lundi au vendredi à 05:00 UTC (09:00, Maurice). Il ne fait rien d'autre que vérifier les garde-fous.

## Garde-fous
- `DRY_RUN` : `true` par défaut (variable de dépôt).
- `LIVE_SEND` : `false` par défaut. Un envoi réel exige `DRY_RUN=false`, `LIVE_SEND=true`, `ADM_VALIDES=true` (ADM-002 et ADM-003 tranchés) et `SMTP_TESTED=true` (test SMTP OVH réussi). Ces quatre variables sont posées par l'utilisateur. Le workflow refuse tout autre cas.
- Pas de réessai automatique : un échec arrête le workflow. Une seule exécution à la fois.

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
