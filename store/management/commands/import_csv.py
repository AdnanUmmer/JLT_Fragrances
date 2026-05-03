import csv
from pathlib import Path

from django.db import transaction
from django.core.management.base import BaseCommand
from django.conf import settings
from store.models import Product, Variant


class Command(BaseCommand):
    help = "Import perfumes from CSV into the product catalog"

    def add_arguments(self, parser):
        parser.add_argument(
            "--path",
            default=str(settings.BASE_DIR / "store" / "data" / "JLT_Perfumes_Updated.csv"),
            help="CSV file path. Defaults to store/data/JLT_Perfumes_Updated.csv.",
        )
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete existing products and variants before importing.",
        )
        parser.add_argument(
            "--skip-if-products-exist",
            action="store_true",
            help="Do nothing when at least one product already exists.",
        )

    def handle(self, *args, **options):
        if options["skip_if_products_exist"] and Product.objects.exists():
            self.stdout.write(self.style.WARNING("Products already exist. Skipping CSV import."))
            return

        file_path = Path(options["path"])
        if not file_path.is_absolute():
            file_path = settings.BASE_DIR / file_path

        if not file_path.exists():
            raise FileNotFoundError(f"CSV file not found: {file_path}")

        if options["reset"]:
            Variant.objects.all().delete()
            Product.objects.all().delete()

        imported = 0
        updated = 0

        with file_path.open(newline="", encoding="utf-8-sig") as file:
            reader = csv.DictReader(file)

            with transaction.atomic():
                for row in reader:
                    name = (row.get("PRODUCTS") or "").strip()
                    brand = (row.get("BRANDS") or "").strip()
                    if not name or not brand:
                        continue

                    defaults = {
                        "category": (row.get("CATEGORY") or "like").strip().lower(),
                        "top_note": (row.get("TOP NOTE") or "").strip(),
                        "middle_note": (row.get("MIDDLE NOTE") or "").strip(),
                        "base_note": (row.get("BASE NOTE") or "").strip(),
                        "description": (row.get("DESCRIPTION") or "").strip(),
                        "occasion": (row.get("OCCASION") or "").strip(),
                        "stock": int((row.get("STOCK") or "100").strip() or 100),
                    }
                    product = Product.objects.filter(inspired_by=name, brand=brand).first()
                    if product:
                        for field, value in defaults.items():
                            setattr(product, field, value)
                        product.save()
                        created = False
                    else:
                        product = Product.objects.create(
                            inspired_by=name,
                            brand=brand,
                            **defaults,
                        )
                        created = True

                    if not product.variants.exists():
                        for size, price in Product.DEFAULT_VARIANTS:
                            Variant.objects.create(product=product, size=size, price=price)

                    imported += int(created)
                    updated += int(not created)

        self.stdout.write(
            self.style.SUCCESS(
                f"CSV import complete from {file_path}: {imported} created, {updated} updated."
            )
        )
