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
    help = "Seed 20 real-world laptops and smartphones across 11 global brands with benchmarks and 100 buyer reviews."

    @transaction.atomic
    def handle(self, *args, **options) -> None:
        admin_user, created = User.objects.get_or_create(
            email="admin@example.com",
            defaults={"username": "admin", "first_name": "Mehrsan", "is_staff": True, "is_superuser": True},
        )
        if created:
            admin_user.set_password("admin1234")
            admin_user.save()

        buyer_profiles = [
            ("buyer1@example.com", "arash_dev", "Arash K. (Verified Buyer)"),
            ("buyer2@example.com", "sara_design", "Sara M. (Verified Buyer)"),
            ("buyer3@example.com", "kian_ai", "Kian R. (ML Engineer)"),
            ("buyer4@example.com", "nima_photo", "Nima T. (Tech Reviewer)"),
            ("buyer5@example.com", "elena_daily", "Elena V. (Power User)"),
        ]
        reviewers = []
        for email, uname, fname in buyer_profiles:
            u, _ = User.objects.update_or_create(
                email=email,
                defaults={"username": uname, "first_name": fname},
            )
            reviewers.append(u)

        # =========================================================================
        # CATEGORY 1: LAPTOPS & ULTRABOOKS (10 Real Models across Lenovo, Apple, ASUS, Dell, HP)
        # =========================================================================
        laptop_schema = [
            {"key": "cpu", "label": "Processor (CPU)", "unit": "", "higher_is_better": None, "group": "Compute & AI"},
            {"key": "gpu", "label": "Graphics (GPU)", "unit": "", "higher_is_better": None, "group": "Compute & AI"},
            {"key": "geekbench_multi", "label": "Geekbench 6 Multi-Core", "unit": "pts", "higher_is_better": True, "group": "Benchmarks"},
            {"key": "gpu_tflops", "label": "GPU Compute Power", "unit": "TFLOPS", "higher_is_better": True, "group": "Benchmarks"},
            {"key": "ram_gb", "label": "Memory (RAM)", "unit": "GB", "higher_is_better": True, "group": "Memory & Storage"},
            {"key": "storage_gb", "label": "NVMe SSD", "unit": "GB", "higher_is_better": True, "group": "Memory & Storage"},
            {"key": "display_hz", "label": "Display Refresh Rate", "unit": "Hz", "higher_is_better": True, "group": "Display & Chassis"},
            {"key": "battery_wh", "label": "Battery Capacity", "unit": "Wh", "higher_is_better": True, "group": "Mobility"},
            {"key": "weight_kg", "label": "Weight", "unit": "kg", "higher_is_better": False, "group": "Mobility"},
        ]

        laptops, _ = Category.objects.update_or_create(
            slug="laptops",
            defaults={
                "name": "Laptops & Ultrabooks",
                "spec_schema": laptop_schema,
                "presets": {
                    "gamer": {
                        "label": "AI & Gaming Power",
                        "weights": {"GPU & AI Performance": 10, "Cooling & Thermals": 9, "Display & Build Quality": 8, "Battery Life": 3, "Portability": 3},
                    },
                    "traveler": {
                        "label": "Ultrabook & Study",
                        "weights": {"Battery Life": 10, "Portability": 10, "Display & Build Quality": 8, "Cooling & Thermals": 6, "GPU & AI Performance": 3},
                    },
                    "creator": {
                        "label": "Content Creator",
                        "weights": {"Display & Build Quality": 10, "GPU & AI Performance": 9, "Battery Life": 7, "Portability": 7, "Cooling & Thermals": 8},
                    },
                    "daily": {
                        "label": "Balanced Daily",
                        "weights": {"Battery Life": 7, "Portability": 7, "Cooling & Thermals": 7, "GPU & AI Performance": 7, "Display & Build Quality": 7},
                    },
                },
            },
        )

        UserPreference.objects.update_or_create(
            user=admin_user,
            defaults={"preferred_category": laptops, "default_budget": Decimal("1450.00")},
        )

        c_gpu, _ = Criteria.objects.get_or_create(category=laptops, name="GPU & AI Performance")
        c_bat, _ = Criteria.objects.get_or_create(category=laptops, name="Battery Life")
        c_therm, _ = Criteria.objects.get_or_create(category=laptops, name="Cooling & Thermals")
        c_port, _ = Criteria.objects.get_or_create(category=laptops, name="Portability")
        c_disp, _ = Criteria.objects.get_or_create(category=laptops, name="Display & Build Quality")
        c_fan_noise, _ = Criteria.objects.update_or_create(
            category=laptops, name="Fan Acoustics Under Load", defaults={"parent": c_therm}
        )

        laptop_catalog = [
            {
                "slug": "lenovo-loq-15irh8",
                "brand": "Lenovo",
                "name": "LOQ 15IRH8",
                "price": "950.00",
                "description": "Best-value engineering & gaming laptop with dedicated RTX 4050 CUDA cores and high-airflow cooling.",
                "specs": {"cpu": "Intel Core i7-13620H", "gpu": "NVIDIA RTX 4050 6GB", "geekbench_multi": 12450, "gpu_tflops": 11.5, "ram_gb": 16, "storage_gb": 512, "display_hz": 144, "battery_wh": 60, "weight_kg": 2.4},
                "pros": "Full-powered RTX 4050 for local LLMs and gaming; sturdy military-grade chassis.",
                "cons": "Heavy 2.4kg body and 5-hour unplugged battery life.",
                "scores": [
                    {c_gpu: 9, c_bat: 5, c_therm: 9, c_port: 5, c_disp: 7, c_fan_noise: 9},
                    {c_gpu: 9, c_bat: 4, c_therm: 8, c_port: 6, c_disp: 7, c_fan_noise: 4},
                    {c_gpu: 9, c_bat: 5, c_therm: 9, c_port: 5, c_disp: 8, c_fan_noise: 8},
                    {c_gpu: 8, c_bat: 5, c_therm: 9, c_port: 5, c_disp: 7, c_fan_noise: 4},
                    {c_gpu: 9, c_bat: 6, c_therm: 8, c_port: 6, c_disp: 7, c_fan_noise: 9},
                ],
            },
            {
                "slug": "lenovo-legion-slim-5-16",
                "brand": "Lenovo",
                "name": "Legion Slim 5 16 (Gen 9)",
                "price": "1399.00",
                "description": "Enthusiast RTX 4060 workstation/gaming hybrid with ColdFront hyper-chamber thermal engineering.",
                "specs": {"cpu": "AMD Ryzen 7 8845HS", "gpu": "NVIDIA RTX 4060 8GB", "geekbench_multi": 13100, "gpu_tflops": 15.1, "ram_gb": 16, "storage_gb": 1024, "display_hz": 165, "battery_wh": 80, "weight_kg": 2.3},
                "pros": "8GB VRAM RTX 4060 crushes 3D rendering and AI training; 165Hz 1600p screen.",
                "cons": "Bulky 230W power adapter required for peak turbo mode.",
                "scores": [
                    {c_gpu: 10, c_bat: 6, c_therm: 9, c_port: 6, c_disp: 9, c_fan_noise: 7},
                    {c_gpu: 9, c_bat: 6, c_therm: 9, c_port: 6, c_disp: 9, c_fan_noise: 8},
                    {c_gpu: 10, c_bat: 7, c_therm: 9, c_port: 5, c_disp: 8, c_fan_noise: 7},
                    {c_gpu: 10, c_bat: 6, c_therm: 9, c_port: 6, c_disp: 9, c_fan_noise: 7},
                    {c_gpu: 9, c_bat: 6, c_therm: 10, c_port: 6, c_disp: 9, c_fan_noise: 8},
                ],
            },
            {
                "slug": "thinkpad-x1-carbon",
                "brand": "Lenovo",
                "name": "ThinkPad X1 Carbon Gen 11",
                "price": "1650.00",
                "description": "Featherlight 1.12kg carbon-fiber executive ultrabook with legendary tactile keyboard and Linux support.",
                "specs": {"cpu": "Intel Core i7-1355U", "gpu": "Intel Iris Xe", "geekbench_multi": 9850, "gpu_tflops": 2.1, "ram_gb": 32, "storage_gb": 512, "display_hz": 60, "battery_wh": 57, "weight_kg": 1.12},
                "pros": "Unrivaled typing comfort, 1.12kg weight, and out-of-the-box Debian/Arch Linux compatibility.",
                "cons": "Integrated Iris Xe GPU is unsuitable for heavy gaming or local LLM training.",
                "scores": [
                    {c_gpu: 4, c_bat: 9, c_therm: 7, c_port: 10, c_disp: 8, c_fan_noise: 8},
                    {c_gpu: 5, c_bat: 9, c_therm: 7, c_port: 10, c_disp: 8, c_fan_noise: 8},
                    {c_gpu: 4, c_bat: 8, c_therm: 8, c_port: 10, c_disp: 9, c_fan_noise: 7},
                    {c_gpu: 4, c_bat: 9, c_therm: 7, c_port: 10, c_disp: 8, c_fan_noise: 8},
                    {c_gpu: 5, c_bat: 9, c_therm: 7, c_port: 10, c_disp: 8, c_fan_noise: 8},
                ],
            },
            {
                "slug": "macbook-air-m3",
                "brand": "Apple",
                "name": "MacBook Air 15 (M3)",
                "price": "1299.00",
                "description": "Fanless Apple Silicon ultrabook delivering 18-hour real-world battery endurance and zero acoustic noise.",
                "specs": {"cpu": "Apple M3 (8-Core)", "gpu": "10-Core Apple GPU", "geekbench_multi": 12150, "gpu_tflops": 4.1, "ram_gb": 16, "storage_gb": 512, "display_hz": 60, "battery_wh": 66, "weight_kg": 1.51},
                "pros": "Completely silent fanless design, 18-hour battery life, and high unified memory bandwidth.",
                "cons": "60Hz display refresh rate and thermal throttling under 30-minute sustained rendering.",
                "scores": [
                    {c_gpu: 7, c_bat: 10, c_therm: 8, c_port: 9, c_disp: 9, c_fan_noise: 10},
                    {c_gpu: 7, c_bat: 10, c_therm: 7, c_port: 9, c_disp: 9, c_fan_noise: 10},
                    {c_gpu: 8, c_bat: 9, c_therm: 8, c_port: 9, c_disp: 8, c_fan_noise: 10},
                    {c_gpu: 7, c_bat: 10, c_therm: 8, c_port: 9, c_disp: 9, c_fan_noise: 10},
                    {c_gpu: 7, c_bat: 10, c_therm: 8, c_port: 9, c_disp: 9, c_fan_noise: 10},
                ],
            },
            {
                "slug": "macbook-pro-14-m3-pro",
                "brand": "Apple",
                "name": "MacBook Pro 14 (M3 Pro)",
                "price": "1999.00",
                "description": "Pro-grade Mini-LED 120Hz workstation with active cooling and class-leading efficiency per watt.",
                "specs": {"cpu": "Apple M3 Pro (12-Core)", "gpu": "18-Core Apple GPU", "geekbench_multi": 15250, "gpu_tflops": 7.4, "ram_gb": 18, "storage_gb": 512, "display_hz": 120, "battery_wh": 72, "weight_kg": 1.61},
                "pros": "1600-nit Liquid Retina XDR 120Hz screen, whisper-quiet fans, and 16-hour battery.",
                "cons": "High entry price and soldered storage/RAM.",
                "scores": [
                    {c_gpu: 9, c_bat: 10, c_therm: 9, c_port: 8, c_disp: 10, c_fan_noise: 9},
                    {c_gpu: 9, c_bat: 9, c_therm: 9, c_port: 8, c_disp: 10, c_fan_noise: 10},
                    {c_gpu: 8, c_bat: 10, c_therm: 9, c_port: 8, c_disp: 10, c_fan_noise: 9},
                    {c_gpu: 9, c_bat: 9, c_therm: 9, c_port: 8, c_disp: 10, c_fan_noise: 9},
                    {c_gpu: 9, c_bat: 10, c_therm: 9, c_port: 8, c_disp: 10, c_fan_noise: 9},
                ],
            },
            {
                "slug": "asus-rog-zephyrus-g14-2024",
                "brand": "ASUS",
                "name": "ROG Zephyrus G14 OLED (2024)",
                "price": "1599.00",
                "description": "CNC-milled aluminum 14-inch gaming & creator powerhouse with 3K 120Hz Nebula OLED display.",
                "specs": {"cpu": "AMD Ryzen 9 8945HS", "gpu": "NVIDIA RTX 4060 8GB", "geekbench_multi": 12900, "gpu_tflops": 14.2, "ram_gb": 16, "storage_gb": 1024, "display_hz": 120, "battery_wh": 73, "weight_kg": 1.50},
                "pros": "Stunning 120Hz OLED panel and RTX 4060 packed into an ultra-portable 1.5kg CNC aluminum shell.",
                "cons": "Soldered RAM on 2024 model and keyboard deck gets warm during gaming.",
                "scores": [
                    {c_gpu: 9, c_bat: 8, c_therm: 7, c_port: 9, c_disp: 10, c_fan_noise: 8},
                    {c_gpu: 9, c_bat: 8, c_therm: 7, c_port: 9, c_disp: 10, c_fan_noise: 4},
                    {c_gpu: 9, c_bat: 7, c_therm: 8, c_port: 9, c_disp: 10, c_fan_noise: 8},
                    {c_gpu: 9, c_bat: 8, c_therm: 7, c_port: 9, c_disp: 10, c_fan_noise: 4},
                    {c_gpu: 9, c_bat: 8, c_therm: 7, c_port: 9, c_disp: 10, c_fan_noise: 9},
                ],
            },
            {
                "slug": "asus-zenbook-14-oled",
                "brand": "ASUS",
                "name": "Zenbook 14 OLED (UX3405)",
                "price": "1099.00",
                "description": "Sleek Intel Core Ultra 7 ultrabook offering 3K OLED visuals and 75Wh battery at an accessible price.",
                "specs": {"cpu": "Intel Core Ultra 7 155H", "gpu": "Intel Arc Graphics", "geekbench_multi": 11800, "gpu_tflops": 4.2, "ram_gb": 16, "storage_gb": 1024, "display_hz": 120, "battery_wh": 75, "weight_kg": 1.28},
                "pros": "Vibrant 120Hz OLED screen, large 75Wh battery in a 1.28kg body, great value.",
                "cons": "Glossy screen reflects overhead lights.",
                "scores": [
                    {c_gpu: 6, c_bat: 9, c_therm: 7, c_port: 9, c_disp: 9, c_fan_noise: 8},
                    {c_gpu: 6, c_bat: 9, c_therm: 8, c_port: 9, c_disp: 9, c_fan_noise: 8},
                    {c_gpu: 7, c_bat: 8, c_therm: 7, c_port: 9, c_disp: 9, c_fan_noise: 7},
                    {c_gpu: 6, c_bat: 9, c_therm: 7, c_port: 9, c_disp: 9, c_fan_noise: 8},
                    {c_gpu: 6, c_bat: 9, c_therm: 8, c_port: 9, c_disp: 9, c_fan_noise: 8},
                ],
            },
            {
                "slug": "dell-xps-14-9440",
                "brand": "Dell",
                "name": "XPS 14 (9440)",
                "price": "1699.00",
                "description": "Futuristic machined-aluminum laptop with edge-to-edge InfinityEdge display and seamless glass touchpad.",
                "specs": {"cpu": "Intel Core Ultra 7 155H", "gpu": "NVIDIA RTX 4050 6GB", "geekbench_multi": 12100, "gpu_tflops": 9.8, "ram_gb": 16, "storage_gb": 512, "display_hz": 120, "battery_wh": 69, "weight_kg": 1.68},
                "pros": "Iconic industrial design, crisp display, and optional low-wattage RTX 4050.",
                "cons": "Capacitive touch function row is divisive among developers; expensive.",
                "scores": [
                    {c_gpu: 7, c_bat: 8, c_therm: 7, c_port: 8, c_disp: 9, c_fan_noise: 7},
                    {c_gpu: 8, c_bat: 7, c_therm: 6, c_port: 8, c_disp: 10, c_fan_noise: 8},
                    {c_gpu: 7, c_bat: 8, c_therm: 7, c_port: 8, c_disp: 9, c_fan_noise: 7},
                    {c_gpu: 7, c_bat: 8, c_therm: 7, c_port: 8, c_disp: 9, c_fan_noise: 7},
                    {c_gpu: 8, c_bat: 7, c_therm: 7, c_port: 8, c_disp: 9, c_fan_noise: 8},
                ],
            },
            {
                "slug": "hp-spectre-x360-14",
                "brand": "HP",
                "name": "Spectre x360 14 (2024)",
                "price": "1449.00",
                "description": "Versatile 2-in-1 convertible with 2.8K IMAX OLED touch screen, stylus support, and 9MP webcam.",
                "specs": {"cpu": "Intel Core Ultra 7 155H", "gpu": "Intel Arc Graphics", "geekbench_multi": 11650, "gpu_tflops": 4.0, "ram_gb": 16, "storage_gb": 1024, "display_hz": 120, "battery_wh": 68, "weight_kg": 1.44},
                "pros": "360-degree hinge with included pen, best webcam and speakers in Windows class.",
                "cons": "Limited port selection on the chassis sides.",
                "scores": [
                    {c_gpu: 6, c_bat: 8, c_therm: 8, c_port: 9, c_disp: 9, c_fan_noise: 8},
                    {c_gpu: 6, c_bat: 8, c_therm: 8, c_port: 8, c_disp: 9, c_fan_noise: 9},
                    {c_gpu: 6, c_bat: 9, c_therm: 7, c_port: 9, c_disp: 9, c_fan_noise: 8},
                    {c_gpu: 7, c_bat: 8, c_therm: 8, c_port: 9, c_disp: 9, c_fan_noise: 8},
                    {c_gpu: 6, c_bat: 8, c_therm: 8, c_port: 9, c_disp: 10, c_fan_noise: 8},
                ],
            },
            {
                "slug": "hp-victus-16-rtx4060",
                "brand": "HP",
                "name": "Victus 16 (2024)",
                "price": "899.00",
                "description": "Budget-friendly 16-inch gaming laptop delivering desktop-class CPU and RTX 4060 graphics.",
                "specs": {"cpu": "Intel Core i5-13500HX", "gpu": "NVIDIA RTX 4060 8GB", "geekbench_multi": 11900, "gpu_tflops": 14.5, "ram_gb": 16, "storage_gb": 512, "display_hz": 144, "battery_wh": 70, "weight_kg": 2.35},
                "pros": "Unbeatable RTX 4060 price-to-performance ratio under USD 900.",
                "cons": "Plastic build with noticeable screen wobble and dim 250-nit panel.",
                "scores": [
                    {c_gpu: 9, c_bat: 5, c_therm: 8, c_port: 5, c_disp: 5, c_fan_noise: 6},
                    {c_gpu: 9, c_bat: 6, c_therm: 8, c_port: 5, c_disp: 6, c_fan_noise: 6},
                    {c_gpu: 9, c_bat: 5, c_therm: 7, c_port: 5, c_disp: 5, c_fan_noise: 5},
                    {c_gpu: 9, c_bat: 5, c_therm: 8, c_port: 5, c_disp: 6, c_fan_noise: 6},
                    {c_gpu: 8, c_bat: 5, c_therm: 8, c_port: 5, c_disp: 5, c_fan_noise: 6},
                ],
            },
        ]

        # =========================================================================
        # CATEGORY 2: SMARTPHONES (10 Real Models: Samsung, Apple, Xiaomi, Google, Oppo, Nothing, Huawei)
        # =========================================================================
        phone_schema = [
            {"key": "chip", "label": "SoC Processor", "unit": "", "higher_is_better": None, "group": "Performance & Benchmarks"},
            {"key": "antutu_v10", "label": "AnTuTu v10 Score", "unit": "pts", "higher_is_better": True, "group": "Performance & Benchmarks"},
            {"key": "ram_gb", "label": "RAM", "unit": "GB", "higher_is_better": True, "group": "Memory & Storage"},
            {"key": "storage_gb", "label": "Internal Storage", "unit": "GB", "higher_is_better": True, "group": "Memory & Storage"},
            {"key": "main_camera_mp", "label": "Main Camera Sensor", "unit": "MP", "higher_is_better": True, "group": "Camera Hardware"},
            {"key": "peak_nits", "label": "Peak Display Brightness", "unit": "nits", "higher_is_better": True, "group": "Display & Design"},
            {"key": "battery_mah", "label": "Battery Capacity", "unit": "mAh", "higher_is_better": True, "group": "Battery & Charging"},
            {"key": "charging_w", "label": "Fast Wired Charging", "unit": "W", "higher_is_better": True, "group": "Battery & Charging"},
            {"key": "weight_g", "label": "Weight", "unit": "g", "higher_is_better": False, "group": "Display & Design"},
        ]

        phones, _ = Category.objects.update_or_create(
            slug="smartphones",
            defaults={
                "name": "Flagship & Value Smartphones",
                "spec_schema": phone_schema,
                "presets": {
                    "photographer": {
                        "label": "Pro Photographer",
                        "weights": {"Camera System": 10, "Display Quality": 9, "Performance & Gaming": 6, "Battery & Charging": 6, "Software & Value": 6},
                    },
                    "gamer": {
                        "label": "Mobile Gamer & Power",
                        "weights": {"Performance & Gaming": 10, "Battery & Charging": 9, "Display Quality": 9, "Camera System": 5, "Software & Value": 7},
                    },
                    "value": {
                        "label": "Smart Value Buyer",
                        "weights": {"Software & Value": 10, "Battery & Charging": 9, "Display Quality": 8, "Performance & Gaming": 7, "Camera System": 7},
                    },
                },
            },
        )

        p_cam, _ = Criteria.objects.get_or_create(category=phones, name="Camera System")
        p_lowlight, _ = Criteria.objects.update_or_create(
            category=phones, name="Low-Light & Zoom", defaults={"parent": p_cam}
        )
        p_bat, _ = Criteria.objects.get_or_create(category=phones, name="Battery & Charging")
        p_disp, _ = Criteria.objects.get_or_create(category=phones, name="Display Quality")
        p_perf, _ = Criteria.objects.get_or_create(category=phones, name="Performance & Gaming")
        p_val, _ = Criteria.objects.get_or_create(category=phones, name="Software & Value")

        phone_catalog = [
            {
                "slug": "galaxy-s24-ultra",
                "brand": "Samsung",
                "name": "Galaxy S24 Ultra",
                "price": "1199.00",
                "description": "Titanium Android powerhouse with Gorilla Armor anti-reflective display, S-Pen, and 7 years of OS updates.",
                "specs": {"chip": "Snapdragon 8 Gen 3", "antutu_v10": 1820000, "ram_gb": 12, "storage_gb": 256, "main_camera_mp": 200, "peak_nits": 2600, "battery_mah": 5000, "charging_w": 45, "weight_g": 232},
                "pros": "Anti-reflective screen is game-changing outdoors; versatile 5x optical zoom and S-Pen.",
                "cons": "Boxy corners feel heavy in pocket; shutter lag on indoor moving pets.",
                "scores": [
                    {p_cam: 9, p_lowlight: 9, p_bat: 9, p_disp: 10, p_perf: 10, p_val: 8},
                    {p_cam: 9, p_lowlight: 4, p_bat: 9, p_disp: 10, p_perf: 9, p_val: 8},
                    {p_cam: 9, p_lowlight: 8, p_bat: 9, p_disp: 10, p_perf: 10, p_val: 7},
                    {p_cam: 9, p_lowlight: 4, p_bat: 9, p_disp: 10, p_perf: 10, p_val: 8},
                    {p_cam: 9, p_lowlight: 9, p_bat: 9, p_disp: 10, p_perf: 10, p_val: 8},
                ],
            },
            {
                "slug": "iphone-16-pro-max",
                "brand": "Apple",
                "name": "iPhone 16 Pro Max",
                "price": "1199.00",
                "description": "Apple flagship featuring A18 Pro silicon, 4K120 ProRes video recording, and industry-leading battery life.",
                "specs": {"chip": "Apple A18 Pro", "antutu_v10": 1780000, "ram_gb": 8, "storage_gb": 256, "main_camera_mp": 48, "peak_nits": 2000, "battery_mah": 4685, "charging_w": 30, "weight_g": 227},
                "pros": "Unrivaled video stabilization, A18 Pro single-core speed, and multi-day battery life.",
                "cons": "Slow 30W wired charging compared to Chinese flagships.",
                "scores": [
                    {p_cam: 10, p_lowlight: 9, p_bat: 9, p_disp: 10, p_perf: 10, p_val: 7},
                    {p_cam: 9, p_lowlight: 9, p_bat: 9, p_disp: 9, p_perf: 10, p_val: 8},
                    {p_cam: 10, p_lowlight: 9, p_bat: 10, p_disp: 10, p_perf: 10, p_val: 7},
                    {p_cam: 9, p_lowlight: 9, p_bat: 9, p_disp: 10, p_perf: 10, p_val: 7},
                    {p_cam: 10, p_lowlight: 9, p_bat: 9, p_disp: 10, p_perf: 10, p_val: 7},
                ],
            },
            {
                "slug": "xiaomi-14-ultra",
                "brand": "Xiaomi",
                "name": "14 Ultra (Leica Edition)",
                "price": "1099.00",
                "description": "Co-engineered with Leica featuring a 1-inch Sony LYT-900 main sensor, stepless variable aperture, and 90W charging.",
                "specs": {"chip": "Snapdragon 8 Gen 3", "antutu_v10": 1950000, "ram_gb": 16, "storage_gb": 512, "main_camera_mp": 50, "peak_nits": 3000, "battery_mah": 5000, "charging_w": 90, "weight_g": 220},
                "pros": "1-inch sensor delivers DSLR-like natural bokeh; blazing 90W HyperCharge.",
                "cons": "HyperOS includes pre-installed apps; massive camera bump makes phone top-heavy.",
                "scores": [
                    {p_cam: 10, p_lowlight: 10, p_bat: 8, p_disp: 9, p_perf: 10, p_val: 7},
                    {p_cam: 10, p_lowlight: 10, p_bat: 8, p_disp: 9, p_perf: 9, p_val: 7},
                    {p_cam: 10, p_lowlight: 9, p_bat: 8, p_disp: 9, p_perf: 10, p_val: 8},
                    {p_cam: 10, p_lowlight: 10, p_bat: 8, p_disp: 9, p_perf: 10, p_val: 7},
                    {p_cam: 9, p_lowlight: 10, p_bat: 8, p_disp: 9, p_perf: 10, p_val: 7},
                ],
            },
            {
                "slug": "pixel-9-pro",
                "brand": "Google",
                "name": "Pixel 9 Pro",
                "price": "999.00",
                "description": "Google AI & computational photography leader with Super Actua 3000-nit OLED and clean day-one Android updates.",
                "specs": {"chip": "Google Tensor G4", "antutu_v10": 1140000, "ram_gb": 16, "storage_gb": 256, "main_camera_mp": 50, "peak_nits": 3000, "battery_mah": 4700, "charging_w": 27, "weight_g": 199},
                "pros": "Best point-and-shoot skin tones, clean Android UI, ultra-bright 3000-nit screen.",
                "cons": "Tensor G4 raw gaming benchmark trails Snapdragon 8 Gen 3.",
                "scores": [
                    {p_cam: 10, p_lowlight: 10, p_bat: 7, p_disp: 10, p_perf: 7, p_val: 9},
                    {p_cam: 10, p_lowlight: 9, p_bat: 7, p_disp: 9, p_perf: 7, p_val: 8},
                    {p_cam: 9, p_lowlight: 10, p_bat: 8, p_disp: 10, p_perf: 7, p_val: 9},
                    {p_cam: 10, p_lowlight: 10, p_bat: 7, p_disp: 10, p_perf: 6, p_val: 9},
                    {p_cam: 10, p_lowlight: 9, p_bat: 7, p_disp: 9, p_perf: 7, p_val: 9},
                ],
            },
            {
                "slug": "oppo-find-x7-ultra",
                "brand": "Oppo",
                "name": "Find X7 Ultra",
                "price": "980.00",
                "description": "World's first dual-periscope telephoto smartphone tuned with Hasselblad Master Mode and 100W SUPERVOOC.",
                "specs": {"chip": "Snapdragon 8 Gen 3", "antutu_v10": 2010000, "ram_gb": 16, "storage_gb": 512, "main_camera_mp": 50, "peak_nits": 4500, "battery_mah": 5000, "charging_w": 100, "weight_g": 221},
                "pros": "Dual 3x and 6x periscope zoom lenses are unmatched for portraits; 100W full charge in 26 mins.",
                "cons": "Limited global carrier band availability outside Asia/Europe.",
                "scores": [
                    {p_cam: 10, p_lowlight: 10, p_bat: 9, p_disp: 9, p_perf: 10, p_val: 8},
                    {p_cam: 10, p_lowlight: 9, p_bat: 9, p_disp: 9, p_perf: 10, p_val: 8},
                    {p_cam: 10, p_lowlight: 10, p_bat: 9, p_disp: 9, p_perf: 9, p_val: 8},
                    {p_cam: 10, p_lowlight: 10, p_bat: 9, p_disp: 9, p_perf: 10, p_val: 7},
                    {p_cam: 9, p_lowlight: 10, p_bat: 9, p_disp: 9, p_perf: 10, p_val: 8},
                ],
            },
            {
                "slug": "nothing-phone-2",
                "brand": "Nothing",
                "name": "Phone (2)",
                "price": "599.00",
                "description": "Distinctive transparent Glyph LED interface paired with ultra-fast, bloat-free Nothing OS and high value.",
                "specs": {"chip": "Snapdragon 8+ Gen 1", "antutu_v10": 1360000, "ram_gb": 12, "storage_gb": 256, "main_camera_mp": 50, "peak_nits": 1600, "battery_mah": 4700, "charging_w": 45, "weight_g": 201},
                "pros": "Iconic Glyph LED notifications, zero bloatware, smooth 120Hz LTPO OLED at USD 599.",
                "cons": "No dedicated optical telephoto zoom lens; average low-light camera.",
                "scores": [
                    {p_cam: 7, p_lowlight: 6, p_bat: 9, p_disp: 8, p_perf: 8, p_val: 10},
                    {p_cam: 7, p_lowlight: 5, p_bat: 8, p_disp: 8, p_perf: 8, p_val: 10},
                    {p_cam: 6, p_lowlight: 6, p_bat: 9, p_disp: 9, p_perf: 8, p_val: 9},
                    {p_cam: 7, p_lowlight: 6, p_bat: 9, p_disp: 8, p_perf: 9, p_val: 10},
                    {p_cam: 7, p_lowlight: 5, p_bat: 9, p_disp: 8, p_perf: 8, p_val: 10},
                ],
            },
            {
                "slug": "huawei-pura-70-ultra",
                "brand": "Huawei",
                "name": "Pura 70 Ultra",
                "price": "1150.00",
                "description": "Retractable 1-inch XMAGE mechanical camera lens with ultra-speed snapshot and Kunlun Glass.",
                "specs": {"chip": "Kirin 9010", "antutu_v10": 980000, "ram_gb": 16, "storage_gb": 512, "main_camera_mp": 50, "peak_nits": 2500, "battery_mah": 5200, "charging_w": 100, "weight_g": 226},
                "pros": "DXOMark chart-topping retractable 1-inch lens and macro photography; 100W charging.",
                "cons": "Kirin 9010 3D gaming speed and lack of native Google Play services polarize users.",
                "scores": [
                    {p_cam: 10, p_lowlight: 10, p_bat: 9, p_disp: 9, p_perf: 7, p_val: 5},
                    {p_cam: 10, p_lowlight: 10, p_bat: 9, p_disp: 9, p_perf: 6, p_val: 8},
                    {p_cam: 10, p_lowlight: 10, p_bat: 9, p_disp: 9, p_perf: 7, p_val: 4},
                    {p_cam: 10, p_lowlight: 10, p_bat: 8, p_disp: 9, p_perf: 7, p_val: 9},
                    {p_cam: 10, p_lowlight: 10, p_bat: 9, p_disp: 9, p_perf: 6, p_val: 5},
                ],
            },
            {
                "slug": "samsung-galaxy-s24-fe",
                "brand": "Samsung",
                "name": "Galaxy S24 FE",
                "price": "649.00",
                "description": "Fan Edition flagship killer bringing Galaxy AI, 3x optical telephoto, and IP68 durability to mid-range budgets.",
                "specs": {"chip": "Exynos 2400e", "antutu_v10": 1610000, "ram_gb": 8, "storage_gb": 256, "main_camera_mp": 50, "peak_nits": 1900, "battery_mah": 4700, "charging_w": 25, "weight_g": 213},
                "pros": "Full Galaxy AI suite and 7-year update promise at almost half the Ultra price.",
                "cons": "25W charging is slow and screen bezels are thicker than S24+.",
                "scores": [
                    {p_cam: 8, p_lowlight: 8, p_bat: 8, p_disp: 8, p_perf: 8, p_val: 9},
                    {p_cam: 8, p_lowlight: 7, p_bat: 8, p_disp: 9, p_perf: 8, p_val: 9},
                    {p_cam: 8, p_lowlight: 8, p_bat: 7, p_disp: 8, p_perf: 9, p_val: 9},
                    {p_cam: 8, p_lowlight: 8, p_bat: 8, p_disp: 8, p_perf: 8, p_val: 10},
                    {p_cam: 8, p_lowlight: 7, p_bat: 8, p_disp: 8, p_perf: 8, p_val: 9},
                ],
            },
            {
                "slug": "iphone-16",
                "brand": "Apple",
                "name": "iPhone 16",
                "price": "799.00",
                "description": "Compact 170g iOS flagship with A18 chip, Action Button, and Camera Control.",
                "specs": {"chip": "Apple A18", "antutu_v10": 1590000, "ram_gb": 8, "storage_gb": 128, "main_camera_mp": 48, "peak_nits": 2000, "battery_mah": 3561, "charging_w": 25, "weight_g": 170},
                "pros": "Featherlight 170g comfort, flagship A18 speed, high resale value.",
                "cons": "60Hz display refresh rate in 2026 feels dated at USD 799.",
                "scores": [
                    {p_cam: 8, p_lowlight: 8, p_bat: 8, p_disp: 6, p_perf: 9, p_val: 8},
                    {p_cam: 8, p_lowlight: 8, p_bat: 8, p_disp: 6, p_perf: 10, p_val: 8},
                    {p_cam: 9, p_lowlight: 8, p_bat: 8, p_disp: 5, p_perf: 9, p_val: 7},
                    {p_cam: 8, p_lowlight: 8, p_bat: 8, p_disp: 6, p_perf: 9, p_val: 8},
                    {p_cam: 8, p_lowlight: 8, p_bat: 9, p_disp: 6, p_perf: 9, p_val: 8},
                ],
            },
            {
                "slug": "xiaomi-14t-pro",
                "brand": "Xiaomi",
                "name": "14T Pro",
                "price": "749.00",
                "description": "High-refresh 144Hz AMOLED flagship killer with Dimensity 9300+ and 120W HyperCharge.",
                "specs": {"chip": "Dimensity 9300+", "antutu_v10": 2020000, "ram_gb": 12, "storage_gb": 512, "main_camera_mp": 50, "peak_nits": 4000, "battery_mah": 5000, "charging_w": 120, "weight_g": 209},
                "pros": "120W full battery charge in 19 minutes; 2M+ AnTuTu performance for USD 749.",
                "cons": "Ultrawide camera is softer than main Leica sensor.",
                "scores": [
                    {p_cam: 8, p_lowlight: 8, p_bat: 10, p_disp: 9, p_perf: 10, p_val: 10},
                    {p_cam: 8, p_lowlight: 8, p_bat: 10, p_disp: 9, p_perf: 10, p_val: 9},
                    {p_cam: 8, p_lowlight: 7, p_bat: 10, p_disp: 9, p_perf: 10, p_val: 10},
                    {p_cam: 9, p_lowlight: 8, p_bat: 9, p_disp: 9, p_perf: 10, p_val: 10},
                    {p_cam: 8, p_lowlight: 8, p_bat: 10, p_disp: 9, p_perf: 10, p_val: 10},
                ],
            },
        ]

        # Seed all 20 products and 100 buyer reviews
        def seed_product_list(cat_obj: Category, items: list[dict]) -> dict[str, Product]:
            created_map: dict[str, Product] = {}
            for item in items:
                prod, _ = Product.objects.update_or_create(
                    slug=item["slug"],
                    defaults={
                        "category": cat_obj,
                        "brand": item["brand"],
                        "name": item["name"],
                        "price": Decimal(item["price"]),
                        "description": item["description"],
                        "specs": item["specs"],
                    },
                )
                created_map[item["slug"]] = prod
                for idx, score_map in enumerate(item["scores"]):
                    rev, _ = Review.objects.update_or_create(
                        user=reviewers[idx],
                        product=prod,
                        defaults={
                            "overall_rating": 9 if idx % 2 == 0 else 8,
                            "pros": item["pros"],
                            "cons": item["cons"],
                            "comment": f"Verified long-term buyer evaluation of {prod.brand} {prod.name}.",
                        },
                    )
                    for crit, val in score_map.items():
                        ReviewScore.objects.update_or_create(
                            review=rev, criteria=crit, defaults={"score": val}
                        )
            return created_map

        laptop_map = seed_product_list(laptops, laptop_catalog)
        phone_map = seed_product_list(phones, phone_catalog)

        SavedProduct.objects.get_or_create(user=admin_user, product=laptop_map["lenovo-loq-15irh8"])
        SavedProduct.objects.get_or_create(user=admin_user, product=laptop_map["asus-rog-zephyrus-g14-2024"])
        SavedProduct.objects.get_or_create(user=admin_user, product=phone_map["galaxy-s24-ultra"])

        DecisionEntry.objects.update_or_create(
            user=admin_user,
            category=laptops,
            chosen_product=laptop_map["lenovo-loq-15irh8"],
            defaults={
                "weights_snapshot": {"GPU & AI Performance": 10.0, "Cooling & Thermals": 9.0, "Battery Life": 4.0, "Portability": 5.0},
                "rationale": "Selected Lenovo LOQ 15IRH8 for CUDA and local LLM workloads.",
                "expected_outcome": "Smooth local model execution and stable thermals.",
                "expected_rating": 8,
                "actual_experience": "Exceeded expectations in PyTorch and Ollama over 6 months.",
                "satisfaction_rating": 9,
            },
        )

        self.stdout.write(
            self.style.SUCCESS(
                "✅ Seeded 20 real-world laptops & smartphones (11 brands), benchmarks, and 100 verified buyer reviews!"
            )
        )
