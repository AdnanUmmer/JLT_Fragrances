import csv
from django.core.management.base import BaseCommand
from store.models import Product, Variant


class Command(BaseCommand):
    help = "Import perfumes from CSV and reset database"

    def handle(self, *args, **kwargs):

        # 🔥 RESET DATA
        Variant.objects.all().delete()
        Product.objects.all().delete()

        file_path = "store/data/perfumes.csv"

        count = 0

        with open(file_path, newline='', encoding='latin-1') as file:
            reader = csv.DictReader(file)

            for row in reader:

                product = Product.objects.create(
                    inspired_by=row["PRODUCTS"].strip(),
                    brand=row["BRANDS"].strip(),
                    category="like",
                    top_note=row.get("TOP NOTE", "").strip(),
                    middle_note=row.get("MIDDLE NOTE", "").strip(),
                    base_note=row.get("BASE NOTE", "").strip(),
                    description=row.get("DESCRIPTION", "").strip(),
                    occasion=row.get("OCCASION", "").strip(),
                )

                count += 1

        self.stdout.write(
            self.style.SUCCESS(f"{count} perfumes imported successfully")
        )