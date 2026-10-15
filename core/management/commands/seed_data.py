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
    help = "Seed normalized spec_schema, priority presets, multi-reviewer consensus data, and journal entries."

    @transaction.atomic
    def handle(self, *args, **options) -> None:
        admin_user, created = User.objects.get_or_create(
            email="admin@example.com",
            defaults={"username": "admin", "first_name": "Mehrsan", "is_staff": True, "is_superuser": True},
        )
        if created:
            admin_user.set_password("admin1234")
            admin_user.save()

        reviewers = []
        for idx in range(1, 6):
            u, _ = User.objects.get_or_create(
                email=f"reviewer{idx}@example.com",
                defaults={"username": f"analyst_{idx}", "first_name": f"Reviewer {idx}"},
            )
            reviewers.append(u)

        # 1. Category: Laptops & Ultrabooks
        laptop_schema = [
            {"key": "cpu", "label": "Processor", "unit": "", "higher_is_better": None, "group": "Performance"},
            {"key": "gpu", "label": "Graphics Card", "unit": "", "higher_is_better": None, "group": "Performance"},
            {"key": "ram_gb", "label": "Memory (RAM)", "unit": "GB", "higher_is_better": True, "group": "Performance"},
            {"key": "storage_gb", "label": "SSD Storage", "unit": "GB", "higher_is_better": True, "group": "Storage"},
            {"key": "battery_wh", "label": "Battery Capacity", "unit": "Wh", "higher_is_better": True, "group": "Mobility"},
            {"key": "weight_kg", "label": "Weight", "unit": "kg", "higher_is_better": False, "group": "Mobility"},
        ]

        laptops, _ = Category.objects.update_or_create(
            slug="laptops",
            defaults={
                "name": "Laptops & Ultrabooks",
                "spec_schema": laptop_schema,
                "presets": {
                    "gamer": {"label": "AI & Gaming", "weights": {"GPU & AI Performance": 10, "Cooling & Thermals": 9, "Battery Life": 3, "Portability": 4}},
                    "traveler": {"label": "Mobile & Study", "weights": {"Battery Life": 10, "Portability": 10, "Cooling & Thermals": 6, "GPU & AI Performance": 3}},
                    "daily": {"label": "Balanced Daily", "weights": {"Battery Life": 7, "Portability": 7, "Cooling & Thermals": 7, "GPU & AI Performance": 7}},
                },
            },
        )

        UserPreference.objects.update_or_create(
            user=admin_user,
            defaults={"preferred_category": laptops, "default_budget": Decimal("1400.00"), "theme_mode": "system"},
        )

        c_gpu, _ = Criteria.objects.get_or_create(category=laptops, name="GPU & AI Performance")
        c_bat, _ = Criteria.objects.get_or_create(category=laptops, name="Battery Life")
        c_therm, _ = Criteria.objects.get_or_create(category=laptops, name="Cooling & Thermals")
        c_port, _ = Criteria.objects.get_or_create(category=laptops, name="Portability")
        c_fan_noise, _ = Criteria.objects.update_or_create(
            category=laptops, name="Fan Acoustics Under Load", defaults={"parent": c_therm}
        )

        loq, _ = Product.objects.update_or_create(
            slug="lenovo-loq-15irh8",
            defaults={
                "category": laptops,
                "brand": "Lenovo",
                "name": "LOQ 15IRH8",
                "price": Decimal("950.00"),
                "description": "Engineering and gaming laptop with dedicated RTX 4050 GPU and dual-fan cooling.",
                "specs": {"cpu": "Intel Core i7-13620H", "gpu": "NVIDIA RTX 4050 6GB", "ram_gb": 16, "storage_gb": 512, "battery_wh": 60, "weight_kg": 2.4},
            },
        )
        thinkpad, _ = Product.objects.update_or_create(
            slug="thinkpad-x1-carbon",
            defaults={
                "category": laptops,
                "brand": "Lenovo",
                "name": "ThinkPad X1 Carbon Gen 11",
                "price": Decimal("1650.00"),
                "description": "Ultra-light carbon-fiber executive notebook built for mobility and typing comfort.",
                "specs": {"cpu": "Intel Core i7-1355U", "gpu": "Intel Iris Xe", "ram_gb": 16, "storage_gb": 512, "battery_wh": 57, "weight_kg": 1.12},
            },
        )
        macbook, _ = Product.objects.update_or_create(
            slug="macbook-air-m3",
            defaults={
                "category": laptops,
                "brand": "Apple",
                "name": "MacBook Air 15 (M3)",
                "price": Decimal("1299.00"),
                "description": "Fanless Apple Silicon notebook with 18-hour battery endurance and silent operation.",
                "specs": {"cpu": "Apple M3 (8-Core)", "gpu": "10-Core Apple GPU", "ram_gb": 16, "storage_gb": 512, "battery_wh": 66, "weight_kg": 1.51},
            },
        )

        loq_distributions = [
            {c_gpu: 9, c_bat: 5, c_therm: 9, c_port: 5, c_fan_noise: 9},
            {c_gpu: 9, c_bat: 4, c_therm: 8, c_port: 6, c_fan_noise: 4},
            {c_gpu: 10, c_bat: 5, c_therm: 9, c_port: 5, c_fan_noise: 8},
            {c_gpu: 9, c_bat: 5, c_therm: 9, c_port: 5, c_fan_noise: 4},
            {c_gpu: 9, c_bat: 6, c_therm: 8, c_port: 6, c_fan_noise: 9},
        ]
        for idx, score_map in enumerate(loq_distributions):
            rev, _ = Review.objects.update_or_create(
                user=reviewers[idx], product=loq,
                defaults={"overall_rating": 9, "pros": "Strong RTX 4050 CUDA performance", "cons": "Modest unplugged battery life"},
            )
            for crit, val in score_map.items():
                ReviewScore.objects.update_or_create(review=rev, criteria=crit, defaults={"score": val})

        thinkpad_distributions = [
            {c_gpu: 4, c_bat: 9, c_therm: 7, c_port: 10, c_fan_noise: 8},
            {c_gpu: 5, c_bat: 9, c_therm: 7, c_port: 10, c_fan_noise: 8},
            {c_gpu: 4, c_bat: 8, c_therm: 8, c_port: 9, c_fan_noise: 7},
            {c_gpu: 4, c_bat: 9, c_therm: 7, c_port: 10, c_fan_noise: 8},
            {c_gpu: 5, c_bat: 9, c_therm: 7, c_port: 10, c_fan_noise: 8},
        ]
        for idx, score_map in enumerate(thinkpad_distributions):
            rev, _ = Review.objects.update_or_create(
                user=reviewers[idx], product=thinkpad,
                defaults={"overall_rating": 8, "pros": "Featherlight 1.12kg chassis and best keyboard", "cons": "Integrated GPU only"},
            )
            for crit, val in score_map.items():
                ReviewScore.objects.update_or_create(review=rev, criteria=crit, defaults={"score": val})

        macbook_distributions = [
            {c_gpu: 7, c_bat: 10, c_therm: 8, c_port: 9, c_fan_noise: 10},
            {c_gpu: 7, c_bat: 10, c_therm: 7, c_port: 9, c_fan_noise: 10},
            {c_gpu: 8, c_bat: 9, c_therm: 8, c_port: 9, c_fan_noise: 10},
            {c_gpu: 7, c_bat: 10, c_therm: 8, c_port: 9, c_fan_noise: 10},
            {c_gpu: 7, c_bat: 10, c_therm: 8, c_port: 8, c_fan_noise: 10},
        ]
        for idx, score_map in enumerate(macbook_distributions):
            rev, _ = Review.objects.update_or_create(
                user=reviewers[idx], product=macbook,
                defaults={"overall_rating": 9, "pros": "Silent fanless M3 and 18h battery", "cons": "Non-upgradeable memory"},
            )
            for crit, val in score_map.items():
                ReviewScore.objects.update_or_create(review=rev, criteria=crit, defaults={"score": val})

        # 2. Category: Flagship Smartphones
        phone_schema = [
            {"key": "chip", "label": "SoC Processor", "unit": "", "higher_is_better": None, "group": "Hardware"},
            {"key": "ram_gb", "label": "RAM", "unit": "GB", "higher_is_better": True, "group": "Hardware"},
            {"key": "storage_gb", "label": "Storage", "unit": "GB", "higher_is_better": True, "group": "Hardware"},
            {"key": "battery_mah", "label": "Battery Capacity", "unit": "mAh", "higher_is_better": True, "group": "Endurance"},
            {"key": "weight_g", "label": "Weight", "unit": "g", "higher_is_better": False, "group": "Design"},
        ]

        phones, _ = Category.objects.update_or_create(
            slug="smartphones",
            defaults={
                "name": "Flagship Smartphones",
                "spec_schema": phone_schema,
                "presets": {
                    "photographer": {"label": "Photographer", "weights": {"Camera System": 10, "Display Quality": 8, "Battery Endurance": 5}},
                    "power": {"label": "Heavy User", "weights": {"Battery Endurance": 10, "Display Quality": 9, "Camera System": 5}},
                    "daily": {"label": "Daily Driver", "weights": {"Camera System": 7, "Battery Endurance": 8, "Display Quality": 8}},
                },
            },
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
                "description": "Titanium flagship with anti-reflective 120Hz AMOLED display and S-Pen.",
                "specs": {"chip": "Snapdragon 8 Gen 3", "ram_gb": 12, "storage_gb": 256, "battery_mah": 5000, "weight_g": 232},
            },
        )
        pixel, _ = Product.objects.update_or_create(
            slug="pixel-9-pro",
            defaults={
                "category": phones,
                "brand": "Google",
                "name": "Pixel 9 Pro",
                "price": Decimal("999.00"),
                "description": "Compact flagship with class-leading computational photography and Tensor G4.",
                "specs": {"chip": "Google Tensor G4", "ram_gb": 16, "storage_gb": 256, "battery_mah": 4700, "weight_g": 199},
            },
        )

        s24_distributions = [
            {p_cam: 9, p_lowlight: 9, p_bat: 9, p_disp: 10},
            {p_cam: 9, p_lowlight: 4, p_bat: 9, p_disp: 10},
            {p_cam: 8, p_lowlight: 8, p_bat: 10, p_disp: 10},
            {p_cam: 9, p_lowlight: 4, p_bat: 9, p_disp: 9},
            {p_cam: 9, p_lowlight: 9, p_bat: 9, p_disp: 10},
        ]
        for idx, score_map in enumerate(s24_distributions):
            rev, _ = Review.objects.update_or_create(
                user=reviewers[idx], product=s24,
                defaults={"overall_rating": 9, "pros": "Best anti-reflective display and battery", "cons": "Mixed low-light shutter speed on moving subjects"},
            )
            for crit, val in score_map.items():
                ReviewScore.objects.update_or_create(review=rev, criteria=crit, defaults={"score": val})

        pixel_distributions = [
            {p_cam: 10, p_lowlight: 10, p_bat: 6, p_disp: 9},
            {p_cam: 10, p_lowlight: 9, p_bat: 6, p_disp: 9},
            {p_cam: 9, p_lowlight: 10, p_bat: 5, p_disp: 9},
            {p_cam: 10, p_lowlight: 10, p_bat: 6, p_disp: 9},
            {p_cam: 10, p_lowlight: 9, p_bat: 6, p_disp: 10},
        ]
        for idx, score_map in enumerate(pixel_distributions):
            rev, _ = Review.objects.update_or_create(
                user=reviewers[idx], product=pixel,
                defaults={"overall_rating": 9, "pros": "Unmatched night sight and skin tones", "cons": "Modest battery endurance under heavy 5G use"},
            )
            for crit, val in score_map.items():
                ReviewScore.objects.update_or_create(review=rev, criteria=crit, defaults={"score": val})

        SavedProduct.objects.get_or_create(user=admin_user, product=loq)
        SavedProduct.objects.get_or_create(user=admin_user, product=macbook)

        DecisionEntry.objects.update_or_create(
            user=admin_user,
            category=laptops,
            chosen_product=loq,
            defaults={
                "weights_snapshot": {"GPU & AI Performance": 10.0, "Cooling & Thermals": 9.0, "Battery Life": 4.0, "Portability": 5.0},
                "rationale": "Selected Lenovo LOQ 15IRH8 for CUDA and local LLM workloads.",
                "expected_outcome": "Smooth local model execution and stable thermals.",
                "expected_rating": 8,
                "actual_experience": "Exceeded expectations in PyTorch and Ollama over 6 months.",
                "satisfaction_rating": 9,
            },
        )

        self.stdout.write(self.style.SUCCESS("✅ Seeded all categories with normalized schema, presets, and 5-reviewer consensus!"))
