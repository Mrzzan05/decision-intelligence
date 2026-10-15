from decimal import Decimal
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from accounts.models import UserPreference
from catalog.models import Category, Criteria, Product, SavedProduct
from journal.models import DecisionEntry
from reviews.models import Review, ReviewScore

User = get_user_model()


class Command(BaseCommand):
    help = "Populate PostgreSQL with complete demo data for all 8 platform features."

    @transaction.atomic
    def handle(self, *args, **options) -> None:
        admin_user, created = User.objects.get_or_create(
            email="admin@example.com",
            defaults={"username": "admin", "is_staff": True, "is_superuser": True},
        )
        if created:
            admin_user.set_password("admin1234")
            admin_user.save()

        reviewer_user, _ = User.objects.get_or_create(
            email="reviewer@example.com",
            defaults={"username": "tech_reviewer"},
        )

        # 1. Category: Laptops
        laptops, _ = Category.objects.get_or_create(
            slug="laptops", defaults={"name": "Laptops & Ultrabooks"}
        )
        UserPreference.objects.update_or_create(
            user=admin_user,
            defaults={"preferred_category": laptops, "default_budget": Decimal("1400.00"), "dark_mode": False},
        )

        c_gpu, _ = Criteria.objects.get_or_create(category=laptops, name="GPU & AI Performance")
        c_bat, _ = Criteria.objects.get_or_create(category=laptops, name="Battery Life")
        c_therm, _ = Criteria.objects.get_or_create(category=laptops, name="Cooling & Thermals")
        c_port, _ = Criteria.objects.get_or_create(category=laptops, name="Portability")

        loq, _ = Product.objects.update_or_create(
            slug="lenovo-loq-15irh8",
            defaults={
                "category": laptops,
                "brand": "Lenovo",
                "name": "LOQ 15IRH8",
                "price": Decimal("950.00"),
                "description": "High-value engineering and gaming laptop featuring dedicated RTX 4050 graphics and dual-fan thermal dissipation.",
                "specs": {
                    "cpu": "Intel Core i7-13620H",
                    "gpu": "NVIDIA RTX 4050 6GB",
                    "ram": "16GB DDR5",
                    "storage": "512GB NVMe SSD",
                },
            },
        )
        thinkpad, _ = Product.objects.update_or_create(
            slug="thinkpad-x1-carbon",
            defaults={
                "category": laptops,
                "brand": "Lenovo",
                "name": "ThinkPad X1 Carbon Gen 11",
                "price": Decimal("1650.00"),
                "description": "Ultra-lightweight carbon-fiber executive notebook built for all-day battery endurance and typing comfort.",
                "specs": {
                    "cpu": "Intel Core i7-1355U",
                    "gpu": "Intel Iris Xe",
                    "ram": "32GB LPDDR5",
                    "weight": "1.12 kg",
                },
            },
        )
        macbook, _ = Product.objects.update_or_create(
            slug="macbook-air-m3",
            defaults={
                "category": laptops,
                "brand": "Apple",
                "name": "MacBook Air 15 (M3)",
                "price": Decimal("1299.00"),
                "description": "Fanless Apple Silicon laptop combining silent operation, 18-hour battery life, and high unified memory bandwidth.",
                "specs": {
                    "cpu": "Apple M3 (8-Core)",
                    "gpu": "10-Core Integrated",
                    "ram": "16GB Unified",
                    "battery": "18 Hours",
                },
            },
        )

        laptop_reviews = [
            (
                loq,
                9,
                "Dedicated RTX 4050 handles CUDA and local LLMs smoothly; sturdy thermal design.",
                "Heavy power brick and modest 5-hour unplugged battery life.",
                {c_gpu: 9, c_bat: 5, c_therm: 9, c_port: 6},
            ),
            (
                thinkpad,
                8,
                "Best-in-class keyboard, featherlight 1.12kg chassis, Linux compatibility.",
                "Integrated GPU is not suited for heavy 3D or deep learning workloads.",
                {c_gpu: 4, c_bat: 9, c_therm: 7, c_port: 10},
            ),
            (
                macbook,
                9,
                "Unmatched battery life, zero fan noise, bright Liquid Retina display.",
                "No upgradeable RAM slots and passive cooling throttles under sustained load.",
                {c_gpu: 7, c_bat: 10, c_therm: 8, c_port: 9},
            ),
        ]
        for prod, overall, pros, cons, score_map in laptop_reviews:
            rev, _ = Review.objects.update_or_create(
                user=reviewer_user,
                product=prod,
                defaults={
                    "overall_rating": overall,
                    "pros": pros,
                    "cons": cons,
                    "comment": f"Comprehensive benchmark evaluation for {prod}.",
                },
            )
            for crit, val in score_map.items():
                ReviewScore.objects.update_or_create(
                    review=rev, criteria=crit, defaults={"score": val}
                )

        # 2. Category: Smartphones (including hierarchical Sub-Criteria)
        phones, _ = Category.objects.get_or_create(
            slug="smartphones", defaults={"name": "Flagship Smartphones"}
        )
        p_cam, _ = Criteria.objects.get_or_create(category=phones, name="Camera System")
        p_lowlight, _ = Criteria.objects.update_or_create(
            category=phones, name="Low-Light Photography", defaults={"parent": p_cam}
        )
        p_bat, _ = Criteria.objects.get_or_create(category=phones, name="Battery Endurance")
        p_disp, _ = Criteria.objects.get_or_create(category=phones, name="Display Quality")

        s24, _ = Product.objects.update_or_create(
            slug="galaxy-s24-ultra",
            defaults={
                "category": phones,
                "brand": "Samsung",
                "name": "Galaxy S24 Ultra",
                "price": Decimal("1199.00"),
                "description": "Titanium flagship with anti-reflective 120Hz AMOLED display and 5x optical periscope zoom.",
                "specs": {"display": "6.8 AMOLED 120Hz", "camera": "200MP Quad", "battery": "5000mAh"},
            },
        )
        pixel, _ = Product.objects.update_or_create(
            slug="pixel-9-pro",
            defaults={
                "category": phones,
                "brand": "Google",
                "name": "Pixel 9 Pro",
                "price": Decimal("999.00"),
                "description": "Computational photography leader with Tensor G4 and class-leading night sight.",
                "specs": {"display": "6.3 LTPO OLED", "chip": "Tensor G4", "camera": "50MP Triple"},
            },
        )

        for prod, overall, pros, cons, score_map in [
            (
                s24,
                9,
                "Anti-reflective screen and S-Pen productivity.",
                "Bulky in small pockets.",
                {p_cam: 9, p_lowlight: 8, p_bat: 9, p_disp: 10},
            ),
            (
                pixel,
                9,
                "Best night-mode skin tones and clean Android updates.",
                "Charging speed is slower than competitors.",
                {p_cam: 10, p_lowlight: 10, p_bat: 7, p_disp: 9},
            ),
        ]:
            rev, _ = Review.objects.update_or_create(
                user=reviewer_user,
                product=prod,
                defaults={"overall_rating": overall, "pros": pros, "cons": cons},
            )
            for crit, val in score_map.items():
                ReviewScore.objects.update_or_create(
                    review=rev, criteria=crit, defaults={"score": val}
                )

        # 3. Saved Products & Decision Journal with Expectation vs Reality
        SavedProduct.objects.get_or_create(user=admin_user, product=loq)
        SavedProduct.objects.get_or_create(user=admin_user, product=macbook)

        DecisionEntry.objects.update_or_create(
            user=admin_user,
            category=laptops,
            chosen_product=loq,
            defaults={
                "weights_snapshot": {
                    "GPU & AI Performance": 10.0,
                    "Cooling & Thermals": 9.0,
                    "Battery Life": 4.0,
                    "Portability": 5.0,
                },
                "rationale": "Selected Lenovo LOQ 15IRH8 because local LLM inference and CUDA coursework require dedicated RTX 4050 graphics and strong cooling.",
                "expected_outcome": "Expected smooth 7B LLM execution in Ollama and stable temperatures under compilation loads.",
                "expected_rating": 8,
                "actual_experience": "After 6 months of university projects, RTX 4050 exceeded expectations in PyTorch and Ollama, though battery requires carrying the charger.",
                "satisfaction_rating": 9,
            },
        )

        self.stdout.write(self.style.SUCCESS("✅ Complete demo data seeded! Login: admin@example.com / admin1234"))
