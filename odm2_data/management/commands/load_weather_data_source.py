# odm2_data/management/commands/load_weather_sources.py

import csv
import os
from datetime import datetime
from django.core.management.base import BaseCommand
from django.utils import timezone

from odm2_data.models import (
    SamplingFeatures,
    SamplingFeatureAnnotations,
    CV_AnnotationType,
)

class Command(BaseCommand):
    help = "Charger 10_weather_data_source.csv en annotations (SamplingFeatureAnnotations) — pas de création de sites"

    # Colonnes attendues dans le CSV (on accepte aussi des variantes *_source)
    FIELD_ALIASES = {
        "temperature": ["temperature", "temperature_source"],
        "precipitation": ["precipitation", "precipitation_source"],
        "global_radiation": ["global_radiation", "global_radiation_source"],
        "14h_air_temperature_humidity": [
            "14h_air_temperature_humidity",
            "14h_air_temperature_humidity_source",
            "air_temperature_humidity_14h",
        ],
    }

    # Définitions facultatives pour peupler CV_AnnotationType si manquant
    ANNOT_DEFS = {
        "temperature": "Source/méthode pour la température quotidienne",
        "precipitation": "Source/méthode pour la précipitation quotidienne",
        "global_radiation": "Source/méthode pour le rayonnement global",
        "14h_air_temperature_humidity": "Source pour le snapshot T/H à 14h",
    }

    def add_arguments(self, parser):
        parser.add_argument("--path", default=os.path.join("data", "10_weather_data_source.csv"))
        parser.add_argument("--encoding", default="latin1")
        parser.add_argument("--delimiter", default=";")

    def handle(self, *args, **opts):
        path = opts["path"]; enc = opts["encoding"]; delim = opts["delimiter"]

        if not os.path.exists(path):
            self.stderr.write(f"❌ Fichier introuvable : {path}")
            return

        with open(path, encoding=enc, newline="") as f:
            reader = csv.DictReader(f, delimiter=delim)

            required = {"site_no", "site", "year"}
            missing = required - set(reader.fieldnames or [])
            if missing:
                self.stderr.write(f"❌ En-têtes manquantes : {missing}")
                return

            # Résoudre dynamiquement les noms de colonnes présents
            resolved_cols = {}
            for key, candidates in self.FIELD_ALIASES.items():
                for c in candidates:
                    if c in reader.fieldnames:
                        resolved_cols[key] = c
                        break
            # (il est normal que certaines colonnes ne soient pas présentes)

            for row in reader:
                try:
                    site_no = (row.get("site_no") or "").strip()
                    site_name = (row.get("site") or "").strip()
                    year_str = (row.get("year") or "").strip()

                    if not site_no:
                        self.stdout.write(self.style.WARNING("⚠️ Ligne ignorée (site_no manquant)"))
                        continue
                    if not year_str.isdigit():
                        self.stdout.write(self.style.WARNING(
                            f"⚠️ Année invalide pour SITE_{site_no} → '{year_str}'"
                        ))
                        continue

                    site_code = f"SITE_{site_no}"
                    site = SamplingFeatures.objects.filter(SamplingFeatureCode=site_code).first()
                    if not site:
                        self.stdout.write(self.style.WARNING(
                            f"⚠️ SamplingFeature {site_code} introuvable (charge d’abord 2_site_information) — ligne ignorée"
                        ))
                        continue

                    # Datetime utilisé pour l’annotation (1er janvier de l’année)
                    dt = datetime(int(year_str), 1, 1)
                    if timezone.is_naive(dt):
                        dt = timezone.make_aware(dt)

                    # Créer une annotation par champ renseigné
                    for annot_key, col in resolved_cols.items():
                        raw = (row.get(col) or "").strip()
                        if not raw or raw.upper() == "NA":
                            continue

                        # CV_AnnotationType (créé si manquant)
                        atype, _ = CV_AnnotationType.objects.get_or_create(
                            Name=annot_key,
                            defaults={"Term": annot_key, "Definition": self.ANNOT_DEFS.get(annot_key, annot_key)}
                        )

                        # Ton modèle ne stocke pas de texte d’annotation -> on enregistre seulement type + date
                        SamplingFeatureAnnotations.objects.get_or_create(
                            SamplingFeatureID=site,
                            AnnotationTypeCV=atype,
                            AnnotationDateTime=dt,
                        )

                    self.stdout.write(self.style.SUCCESS(
                        f"✅ {site_name or site_code} ({year_str}) — annotations météo enregistrées"
                    ))

                except Exception as e:
                    self.stderr.write(f"❌ Erreur ligne {reader.line_num} : {e}")
                    raise
