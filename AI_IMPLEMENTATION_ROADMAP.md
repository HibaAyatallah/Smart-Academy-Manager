# Smart Academy Manager — Roadmap IA

## Architecture livrée

1. **Multilingue** : service Angular autonome, dictionnaires FR/EN/AR, pipe de traduction, persistance locale et préférence utilisateur Django, RTL arabe.
2. **Emails** : service centralisé, template HTML, SMTP par environnement, déduplication, journal technique et point d'extension `queue_email` compatible avec une future tâche Celery.
3. **Assistant** : conversations liées à `request.user`, contexte ORM prédéfini par rôle, historique privé, validation des entrées et fournisseur remplaçable. La version initiale est strictement en lecture seule.

## Prochaines itérations

- Étendre progressivement les clés i18n aux textes métier de chaque écran, avec contrôle automatique des clés manquantes.
- Passer `queue_email` sur Celery/Redis, ajouter les rappels planifiés de formation et un mécanisme de retry exponentiel.
- Brancher un fournisseur LLM approuvé derrière l'interface du provider, avec sortie structurée, redaction PII et observabilité.
- Ajouter une politique de rétention configurable et une purge des conversations.
- Ajouter des actions chatbot uniquement via commandes typées, confirmation explicite, permissions DRF et journal d'audit.

## Phases IA ultérieures (non implémentées)

- Extraction CV : pipeline asynchrone, antivirus/OCR, schéma structuré, score de confiance et validation humaine.
- Matching candidats–offres–besoins BU : embeddings versionnés, explication du score, biais mesurés et décision humaine obligatoire.
