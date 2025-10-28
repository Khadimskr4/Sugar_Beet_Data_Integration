import csv
import os
from django.core.management.base import BaseCommand
from odm2_data.models import CV_VariableName, CV_Unit

class Command(BaseCommand):
    help = "Valider la présence des variables et unités référencées dans le fichier 4_site_field_information.csv"

    def handle(self, *args, **kwargs):
        file_path = os.path.join('data', '4_site_field_information.csv')

        with open(file_path, encoding='latin1') as csvfile:
            reader = csv.DictReader(csvfile, delimiter=';')
            headers = reader.fieldnames

            variables_detected = set()
            units_detected = {}

            for col in headers:
                if col.startswith("Unit_"):
                    var = col.replace("Unit_", "").strip()
                    units_detected[var] = col
                elif col not in ["site_no", "site", "trial", "precrop", "intercrop", "remark", "irrigation"]:
                    variables_detected.add(col.strip())

            # Vérification des variables
            self.stdout.write("🔎 Vérification des variables présentes dans CV_VariableName...")
            for var in variables_detected.union(units_detected.keys()):
                if not CV_VariableName.objects.filter(name=var).exists():
                    self.stdout.write(self.style.ERROR(f"❌ Variable absente : {var}"))
                else:
                    self.stdout.write(self.style.SUCCESS(f"✅ Variable OK : {var}"))

            # Vérification des unités
            self.stdout.write("\n🔎 Vérification des unités présentes dans CV_Unit...")
            sample_row = next(reader)  # Une seule ligne suffit pour récupérer les unités
            for var, unit_col in units_detected.items():
                unit = sample_row.get(unit_col, "").strip()
                if not unit:
                    self.stdout.write(self.style.WARNING(f"⚠️ Unité vide pour la variable : {var}"))
                elif not CV_Unit.objects.filter(name=unit).exists():
                    self.stdout.write(self.style.ERROR(f"❌ Unité absente : {unit} (pour variable {var})"))
                else:
                    self.stdout.write(self.style.SUCCESS(f"✅ Unité OK : {unit} pour {var}"))
