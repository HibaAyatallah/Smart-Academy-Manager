"""
Migration de données idempotente : enregistre le catalogue des formations internes
(CCNA, CCNP, Infoblox, Palo Alto, PMP) ainsi que leurs modules respectifs.
"""

from django.db import migrations


def seed_catalogue(apps, schema_editor):
    Training = apps.get_model("trainings", "Training")

    # 1. CCNA
    ccna_desc = "Formation complète CCNA (Cisco Certified Network Associate) pour maîtriser les bases du routage et de la commutation."
    ccna, _ = Training.objects.get_or_create(
        title="CCNA",
        defaults={
            "description": ccna_desc,
            "training_type": "INTERNAL",
            "category": "Réseaux",
            "objectives": "Maîtriser les concepts de routage, commutation,adressage IPv4/IPv6 et automatisation réseau.",
            "prerequisites": "Aucun prérequis technique.",
            "duration": 40,
            "delivery_mode": "ON_SITE",
            "level": "Débutant",
            "status": "PUBLISHED",
        }
    )

    ccna_modules = [
        "CCNA - Volume 1 - Part 1 Introduction to Networking",
        "CCNA - Volume 1 - Part 2 Implementing Ethernet LANs",
        "CCNA - Volume 1 - Part 3 Implementing VLANs and STP",
        "CCNA - Volume 1 - Part 4 IPv4 Addressing",
        "CCNA - Volume 1 - Part 5 IPv4 Routing",
        "CCNA - Volume 1 - Part 6 OSPF",
        "CCNA - Volume 2 - Part 1 IP Access Control Lists",
        "CCNA - Volume 2 - Part 2 Security Services",
        "CCNA - Volume 2 - Part 3 IP Services",
        "CCNA - Volume 2 - Part 4 Network Architecture",
        "CCNA - Volume 2 - Part 5 Network Automation",
        "CCNA - Évaluation - Test final CCNA"
    ]
    for title in ccna_modules:
        Training.objects.get_or_create(
            title=title,
            defaults={
                "description": f"Module de la formation CCNA : {title}.",
                "training_type": "INTERNAL",
                "category": "CCNA",
                "objectives": f"Assimiler et valider les compétences du module {title}.",
                "prerequisites": "Suivi des parties précédentes.",
                "duration": 4,
                "delivery_mode": "ON_SITE",
                "level": "Débutant",
                "status": "PUBLISHED",
            }
        )

    # 2. CCNP Formations (DCCOR, ENCOR, SCOR) sous la catégorie CCNP
    ccnp_trainings = [
        {
            "title": "DCCOR",
            "description": "Cisco Data Center Core Technologies (350-601 DCCOR).",
            "objectives": "Maîtriser l'implémentation et la gestion des technologies de Data Center Cisco.",
            "level": "Avancé",
            "modules": [
                "DCCOR Part I: Networking",
                "DCCOR Part II: Storage",
                "DCCOR Part III: Compute",
                "DCCOR Part IV: Automation",
                "DCCOR Part V: Security",
                "DCCOR Test final"
            ]
        },
        {
            "title": "ENCOR",
            "description": "Cisco Enterprise Network Core Technologies (350-401 ENCOR).",
            "objectives": "Mettre en œuvre les technologies de réseau d'entreprise Cisco Core.",
            "level": "Avancé",
            "modules": [
                "ENCOR 0: Introduction",
                "ENCOR 1: Forwarding",
                "ENCOR 2: Layer 2",
                "ENCOR 3: Routing",
                "ENCOR 4: Services",
                "ENCOR 5: Overlay",
                "ENCOR 6: Wireless",
                "ENCOR 7: Architecture",
                "ENCOR 8: Security",
                "ENCOR 9: SDN",
                "ENCOR Exam 350-401"
            ]
        },
        {
            "title": "SCOR",
            "description": "Cisco Security Core Technologies (350-701 SCOR).",
            "objectives": "Mettre en œuvre et exploiter les technologies de sécurité Cisco Core.",
            "level": "Avancé",
            "modules": [
                "SCOR Part 1",
                "SCOR Part 2",
                "SCOR Part 3",
                "SCOR Part 4",
                "SCOR Test final"
            ]
        }
    ]

    for data in ccnp_trainings:
        parent_tr, _ = Training.objects.get_or_create(
            title=data["title"],
            defaults={
                "description": data["description"],
                "training_type": "INTERNAL",
                "category": "CCNP",
                "objectives": data["objectives"],
                "prerequisites": "Certification CCNA ou niveau équivalent.",
                "duration": 40,
                "delivery_mode": "ON_SITE",
                "level": data["level"],
                "status": "PUBLISHED",
            }
        )
        for m_title in data["modules"]:
            Training.objects.get_or_create(
                title=m_title,
                defaults={
                    "description": f"Module de la formation {data['title']} : {m_title}.",
                    "training_type": "INTERNAL",
                    "category": data["title"],
                    "objectives": f"Assimiler et valider les compétences du module {m_title}.",
                    "prerequisites": f"Suivi des prérequis de la formation {data['title']}.",
                    "duration": 6,
                    "delivery_mode": "ON_SITE",
                    "level": data["level"],
                    "status": "PUBLISHED",
                }
            )

    # 3. Infoblox
    infoblox, _ = Training.objects.get_or_create(
        title="Infoblox",
        defaults={
            "description": "Administration et configuration de la solution DDI Infoblox (DNS/DHCP/IPAM).",
            "training_type": "INTERNAL",
            "category": "Réseaux",
            "objectives": "Configurer les services DNS et DHCP sur Infoblox Grid Manager.",
            "prerequisites": "Bonnes connaissances DNS/DHCP.",
            "duration": 24,
            "delivery_mode": "ON_SITE",
            "level": "Intermédiaire",
            "status": "PUBLISHED",
        }
    )
    infoblox_modules = [
        "Infoblox DHCP",
        "Infoblox DNS",
        "Infoblox Test final"
    ]
    for title in infoblox_modules:
        Training.objects.get_or_create(
            title=title,
            defaults={
                "description": f"Module de la formation Infoblox : {title}.",
                "training_type": "INTERNAL",
                "category": "Infoblox",
                "objectives": f"Assimiler et valider les compétences du module {title}.",
                "prerequisites": "Suivi des prérequis Infoblox.",
                "duration": 8,
                "delivery_mode": "ON_SITE",
                "level": "Intermédiaire",
                "status": "PUBLISHED",
            }
        )

    # 4. Palo Alto
    palo_alto, _ = Training.objects.get_or_create(
        title="Palo Alto",
        defaults={
            "description": "Pare-feu de nouvelle génération Palo Alto Networks (PAN-OS).",
            "training_type": "INTERNAL",
            "category": "Sécurité",
            "objectives": "Configurer, administrer et dépanner les pares-feux Palo Alto.",
            "prerequisites": "Bases en sécurité des réseaux.",
            "duration": 30,
            "delivery_mode": "ON_SITE",
            "level": "Intermédiaire",
            "status": "PUBLISHED",
        }
    )
    palo_alto_modules = [
        "Palo Alto - Domaine 1",
        "Palo Alto - Domaine 2",
        "Palo Alto - Domaine 3",
        "Palo Alto - Domaine 4"
    ]
    for title in palo_alto_modules:
        Training.objects.get_or_create(
            title=title,
            defaults={
                "description": f"Module de la formation Palo Alto : {title}.",
                "training_type": "INTERNAL",
                "category": "Palo Alto",
                "objectives": f"Assimiler et valider les compétences du module {title}.",
                "prerequisites": "Suivi des prérequis Palo Alto.",
                "duration": 7,
                "delivery_mode": "ON_SITE",
                "level": "Intermédiaire",
                "status": "PUBLISHED",
            }
        )

    # 5. PMP
    pmp, _ = Training.objects.get_or_create(
        title="PMP",
        defaults={
            "description": "Préparation à la certification Project Management Professional (PMP) du PMI.",
            "training_type": "INTERNAL",
            "category": "Gestion de projet",
            "objectives": "Maîtriser les standards du PMBOK pour la gestion de projet.",
            "prerequisites": "Expérience en gestion de projet.",
            "duration": 35,
            "delivery_mode": "ON_SITE",
            "level": "Avancé",
            "status": "PUBLISHED",
        }
    )
    pmp_modules = [
        "PMP Partie 1",
        "PMP Partie 2",
        "PMP Partie 3",
        "PMP Partie 4"
    ]
    for title in pmp_modules:
        Training.objects.get_or_create(
            title=title,
            defaults={
                "description": f"Module de la formation PMP : {title}.",
                "training_type": "INTERNAL",
                "category": "PMP",
                "objectives": f"Assimiler et valider les compétences du module {title}.",
                "prerequisites": "Suivi des prérequis PMP.",
                "duration": 8,
                "delivery_mode": "ON_SITE",
                "level": "Avancé",
                "status": "PUBLISHED",
            }
        )


def remove_catalogue(apps, schema_editor):
    Training = apps.get_model("trainings", "Training")
    titles_to_remove = [
        "CCNA", "DCCOR", "ENCOR", "SCOR", "Infoblox", "Palo Alto", "PMP"
    ]
    # CCNA modules
    titles_to_remove.extend([
        "CCNA - Volume 1 - Part 1 Introduction to Networking",
        "CCNA - Volume 1 - Part 2 Implementing Ethernet LANs",
        "CCNA - Volume 1 - Part 3 Implementing VLANs and STP",
        "CCNA - Volume 1 - Part 4 IPv4 Addressing",
        "CCNA - Volume 1 - Part 5 IPv4 Routing",
        "CCNA - Volume 1 - Part 6 OSPF",
        "CCNA - Volume 2 - Part 1 IP Access Control Lists",
        "CCNA - Volume 2 - Part 2 Security Services",
        "CCNA - Volume 2 - Part 3 IP Services",
        "CCNA - Volume 2 - Part 4 Network Architecture",
        "CCNA - Volume 2 - Part 5 Network Automation",
        "CCNA - Évaluation - Test final CCNA"
    ])
    # DCCOR, ENCOR, SCOR modules
    titles_to_remove.extend([
        "DCCOR Part I: Networking",
        "DCCOR Part II: Storage",
        "DCCOR Part III: Compute",
        "DCCOR Part IV: Automation",
        "DCCOR Part V: Security",
        "DCCOR Test final",
        "ENCOR 0: Introduction",
        "ENCOR 1: Forwarding",
        "ENCOR 2: Layer 2",
        "ENCOR 3: Routing",
        "ENCOR 4: Services",
        "ENCOR 5: Overlay",
        "ENCOR 6: Wireless",
        "ENCOR 7: Architecture",
        "ENCOR 8: Security",
        "ENCOR 9: SDN",
        "ENCOR Exam 350-401",
        "SCOR Part 1",
        "SCOR Part 2",
        "SCOR Part 3",
        "SCOR Part 4",
        "SCOR Test final"
    ])
    # Infoblox, Palo Alto, PMP modules
    titles_to_remove.extend([
        "Infoblox DHCP",
        "Infoblox DNS",
        "Infoblox Test final",
        "Palo Alto - Domaine 1",
        "Palo Alto - Domaine 2",
        "Palo Alto - Domaine 3",
        "Palo Alto - Domaine 4",
        "PMP Partie 1",
        "PMP Partie 2",
        "PMP Partie 3",
        "PMP Partie 4"
    ])
    Training.objects.filter(title__in=titles_to_remove).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("trainings", "0006_daily_session_attendance"),
    ]

    operations = [
        migrations.RunPython(
            seed_catalogue,
            reverse_code=remove_catalogue,
        ),
    ]
