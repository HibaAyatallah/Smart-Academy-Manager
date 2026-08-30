# Module d'aide au recrutement — fonctionnement technique

Ce module est un outil d'aide à la décision. Il ne rejette jamais automatiquement une candidature et ne doit pas être présenté comme un modèle de Machine Learning entraîné.

## Pipeline

1. Le fichier est validé (taille, extension, signature et structure).
2. PyMuPDF extrait le texte des PDF ; `python-docx` lit paragraphes et tableaux DOCX.
3. Si un PDF fournit moins de 60 caractères alphanumériques, un OCR Tesseract français/anglais est tenté. Cette dépendance système est facultative ; son absence produit un message clair sans bloquer le recrutement.
4. Des règles et expressions régulières nettoient le texte, détectent les sections et extraient identité, contact, compétences, expériences, formations, langues et certifications.
5. Les compétences sont normalisées par aliases connus (`Python3` → `Python`, `Postgres` → `PostgreSQL`, `DRF` → `Django REST Framework`, etc.) et dédupliquées.
6. Les dates d'expérience reconnues sont converties en intervalles mensuels, fusionnées en cas de chevauchement, puis totalisées approximativement.
7. La candidature est comparée uniquement aux critères réellement présents sur son offre : compétences requises et niveau d'études requis.
8. Le score et son détail sont persistés, puis les candidats d'une offre sont classés par score décroissant, date de candidature et identifiant.

## Score explicable

Les poids prévus sont : compétences 50, expérience 25, formation 15 et critères additionnels 10. Un composant n'est utilisé que si l'offre contient réellement son critère et que le candidat dispose de données comparables. Les poids disponibles sont alors normalisés sur 100.

Le modèle `Offer` actuel ne contient pas de minimum d'expérience chiffré ni de critères additionnels structurés. L'expérience détectée est donc affichée comme information, mais n'influence pas la note. Aucun seuil ou nombre d'années n'est inventé.

- score compétences = compétences obligatoires correspondantes / compétences obligatoires ;
- score formation = niveau détecté comparé au niveau demandé, lorsqu'ils sont disponibles ;
- score global = moyenne pondérée des seuls composants disponibles ;
- égalités du classement = date de candidature, puis identifiant.

Le résultat expose les compétences correspondantes, manquantes et supplémentaires, chaque composant, le poids normalisé, le label et une synthèse déterministe.

## Techniques utilisées

| Fonction | Technique réelle |
|---|---|
| Lecture PDF | Parsing PyMuPDF et reconstruction de l'ordre des blocs |
| Lecture DOCX | Parsing `python-docx` des paragraphes et tableaux |
| OCR | Tesseract via `pytesseract`, fallback facultatif uniquement |
| Nettoyage/sections | Règles déterministes et expressions régulières |
| Identité/contact | Regex, heuristiques et scores de confiance déterministes |
| Compétences | Dictionnaire/regex, aliases et déduplication |
| Expérience/formation | Règles bilingues, regex de dates et regroupement heuristique |
| Matching | Comparaison d'ensembles normalisés |
| Score | Formule pondérée déterministe, sans pourcentage aléatoire |
| Synthèse | Gabarit déterministe ; aucune dépendance Ollama |
| Classement | Tri déterministe et stable |
| Ollama | Utilisé par l'assistant général, pas requis par le matching recrutement |

## Correction humaine et cache

L'extraction est stockée dans `CVAnalysis` avec le hash source et une version d'extracteur. Une analyse existante est réutilisée ; l'OCR n'est pas relancé à l'ouverture d'un écran. Les données validées par un humain ne sont jamais remplacées sans réanalyse forcée et confirmation explicite. Le matching utilise ensuite ces données corrigées.

## Limites

- Tesseract et les packs de langue doivent être installés sur l'OS pour l'OCR.
- Les mises en page inhabituelles, tableaux complexes et scans de mauvaise qualité réduisent la précision.
- Les règles couvrent principalement le français et l'anglais, avec des formats marocains de téléphone privilégiés.
- L'expérience sans dates reste descriptive et n'est pas convertie en années.
- La formation incomplète n'est pas transformée en information certaine.
- Les aliases sont volontairement limités ; aucune compétence absente du CV n'est inventée.
- Les scores mesurent l'alignement aux critères structurés disponibles, pas la qualité globale d'une personne.
