from django.core.management.base import BaseCommand
from app.models import QuickReply


class Command(BaseCommand):
    help = 'Créer les quick replies pour le bot messenger'

    def handle(self, *args, **options):
        # Données des quick replies
        quick_replies_data = [ 
            {
                'title': 'À propos',
                'payload': 'ABOUT',
                'response_text': 'HOSODOKO-KO est une maison de production d\'œuvre d\'art à partir de recyclage des déchets.\n\n🎯 VISION: Être une référence de la gestion des déchets et dans l\'éducation et sensibilisation environnementales avec une approche participative et inclusive.\n\n🎨 MISSIONS:\n• Valoriser les déchets en œuvre d\'arts originaux et inspirants\n• Promouvoir l\'écoresponsabilité grâce à des approches ludiques\n• Fédérer un réseau d\'acteurs locaux\n• Diffuser les connaissances en gestion des déchets\n\n💎 VALEURS: Création et innovation, Durabilité, Intégrité et transparence, Éducation et partage\n\n📧 Contact: hosodokoko@gmail.com | ☎️ +261 34 20 801 09'
            },
            {
                'title': 'Savoir-faire',
                'payload': 'SKILLS',
                'response_text': '🛠️ TUTO : FABRIQUE UN POT DE FLEURS AVEC UNE BOUTEILLE PLASTIQUE\n\n📋 MATÉRIAUX NÉCESSAIRES :\n• 1 bouteille plastique (1,5L ou 2L)\n• Cutter ou ciseaux\n• Peinture ou marqueurs\n• Terre et graines/plante\n\n👷 ÉTAPES :\n1️⃣ Coupe la bouteille au 2/3 de sa hauteur\n2️⃣ Fais 3-4 petits trous au fond pour drainage\n3️⃣ Décore avec peinture ou dessins\n4️⃣ Remplis de terre et plante tes graines\n5️⃣ Arrose légèrement\n\n💡 ASTUCE : Utilise le haut comme entonnoir d\'arrosage !\n\n✨ En 30 min, tu transformes un déchet en objet utile ! 🌱'
            },
            {
                'title': 'Événements',
                'payload': 'EVENTS',
                'response_text': '🌱 NOS ÉVÉNEMENTS:\n• Ateliers de création d\'œuvres d\'art à partir de déchets recyclés\n• Sessions d\'éducation environnementale\n• Campagnes de sensibilisation à la protection de l\'environnement\n• Projets de reboisement communautaire\n• Formations en gestion des déchets\n• Expositions d\'art écologique\n\nContactez-nous pour participer à nos prochaines activités ! 📧 hosodokoko@gmail.com'
            },
            {
                'title': 'Challenges',
                'payload': 'CHALLENGES',
                'response_text': 'DÉFI ÉCOLOGIQUE DE LA SEMAINE :\n\n🎨 "TRANSFORME TES DÉCHETS EN ART !"\n\nTon mission :\n1️⃣ Collecte 5 bouteilles plastiques, boîtes de conserve ou cartons\n2️⃣ Crée une œuvre d\'art originale (sculpture, pot de fleurs, organisateur, etc.)\n3️⃣ Prends une photo de ta création\n4️⃣ Partage ton histoire : qu\'as-tu appris ?\n\n🏆 RÉCOMPENSE : Les meilleures créations seront exposées lors de nos événements !\n\n✅ Défi terminé ? Contacte-nous :\n📧 hosodokoko@gmail.com\n☎️ +261 34 20 801 09\n\nEnsemble, transformons les déchets en trésors ! 🌍♻️'
            },
            # {
            #     'title': 'Quizz',
            #     'payload': 'QUIZ',
            #     'response_text': 'Quel est le plat japonais traditionnel souvent servi lors des célébrations ?\n1. Sushi\n2. Ramen\n3. Mochi\n4. Tempura\nRépondez avec le numéro de votre choix !'
            # }
        ]

        # Créer ou mettre à jour les quick replies
        for qr_data in quick_replies_data:
            quick_reply, created = QuickReply.objects.get_or_create(
                payload=qr_data['payload'],
                defaults={
                    'title': qr_data['title'],
                    'response_text': qr_data['response_text']
                }
            )
            
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'Quick reply "{quick_reply.title}" créé avec succès')
                )
            else:
                # Mettre à jour les champs si nécessaire
                updated = False
                if quick_reply.title != qr_data['title']:
                    quick_reply.title = qr_data['title']
                    updated = True
                if quick_reply.response_text != qr_data['response_text']:
                    quick_reply.response_text = qr_data['response_text']
                    updated = True
                
                if updated:
                    quick_reply.save()
                    self.stdout.write(
                        self.style.WARNING(f'Quick reply "{quick_reply.title}" mis à jour')
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(f'Quick reply "{quick_reply.title}" existe déjà')
                    )

        self.stdout.write(
            self.style.SUCCESS('Toutes les quick replies ont été traitées avec succès!')
        )
