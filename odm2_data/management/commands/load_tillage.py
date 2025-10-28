# odm2_data/management/commands/load_tillage.py

import csv, os
from datetime import datetime
from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils.dateparse import parse_datetime
from django.utils import timezone
from django.db import transaction

from odm2_data.models import (
    SamplingFeatures, CV_ActionType,
    Actions, FeatureActions, Equipments, EquipmentUsed
)

class Command(BaseCommand):
    help = "Charger les événements de travail du sol (tillage) depuis 3_tillage.csv"

    def add_arguments(self, parser):
        parser.add_argument("--path", default=os.path.join("data", "3_tillage.csv"))
        parser.add_argument("--encoding", default="latin1")
        parser.add_argument("--delimiter", default=";")

    @transaction.atomic
    def handle(self, *args, **opts):
        path = opts["path"]; enc = opts["encoding"]; delim = opts["delimiter"]

        if not os.path.exists(path):
            self.stdout.write(self.style.ERROR(f"❌ Fichier introuvable : {path}"))
            return

        # CV_ActionType: Name='Tillage'
        tillage_type = CV_ActionType.objects.filter(Name__iexact="Tillage").first()
        if not tillage_type:
            self.stdout.write(self.style.ERROR("❌ CV_ActionType(Name='Tillage') manquant. Lance d’abord `load_cv`."))
            return

        with open(path, encoding=enc, newline="") as f:
            reader = csv.DictReader(f, delimiter=delim)

            required = {"site_no", "date"}
            missing = required - set(reader.fieldnames or [])
            if missing:
                self.stdout.write(self.style.ERROR(f"❌ En-têtes manquantes : {missing}"))
                return

            # La colonne équipement peut s'appeler 'Equipment' ou 'Tillage'
            equip_col = "Equipment" if "Equipment" in reader.fieldnames else ("Tillage" if "Tillage" in reader.fieldnames else None)

            for row in reader:
                try:
                    site_no = (row.get("site_no") or "").strip()
                    if not site_no:
                        self.stdout.write(self.style.WARNING("⚠️ Ligne ignorée (site_no manquant)"))
                        continue

                    site_code = f"SITE_{site_no}"
                    site = SamplingFeatures.objects.filter(SamplingFeatureCode=site_code).first()
                    if not site:
                        self.stdout.write(self.style.ERROR(f"❌ SamplingFeatures introuvable : {site_code}"))
                        continue

                    # ---- date
                    date_str = (row.get("date") or "").strip()
                    dt = self._parse_date(date_str)
                    if not dt:
                        self.stdout.write(self.style.WARNING(f"⚠️ Date invalide '{date_str}' pour {site_code} → ligne ignorée"))
                        continue
                    if settings.USE_TZ and timezone.is_naive(dt):
                        dt = timezone.make_aware(dt)

                    # ---- Action (1 par site & date)
                    desc = f"Tillage at {site_code} on {dt.date().isoformat()}"
                    action, _ = Actions.objects.get_or_create(
                        ActionTypeCV=tillage_type,
                        BeginDateTime=dt,
                        EndDateTime=dt,
                        ActionDescription=desc
                    )

                    # ---- Equipements
                    equipments = self._split_equipment((row.get(equip_col) or "").strip()) if equip_col else []
                    for eq_name in equipments:
                        equipment, _ = Equipments.objects.get_or_create(
                            EquipmentName=eq_name,
                            defaults={"Description": f"{eq_name} equipment"}
                        )
                        EquipmentUsed.objects.get_or_create(
                            ActionID=action, EquipmentID=equipment
                        )

                    # ---- FeatureAction (idempotent)
                    FeatureActions.objects.get_or_create(
                        SamplingFeatureID=site, ActionID=action
                    )

                    self.stdout.write(self.style.SUCCESS(
                        f"✅ {site_code} — {dt.date().isoformat()} — équipements: {', '.join(equipments) or 'aucun'}"
                    ))

                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"[❌] Ligne en erreur : {row} | {e}"))
                    raise  # rollback transaction

    # ---------- helpers ----------
    def _parse_date(self, s: str):
        s = (s or "").strip()
        if not s:
            return None
        dt = parse_datetime(s)
        if dt:
            return dt
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d", "%d-%m-%Y", "%m/%d/%Y"):
            try:
                return datetime.strptime(s, fmt)
            except ValueError:
                continue
        return None

    def _split_equipment(self, s: str):
        """Découpe 'plow, harrow' / 'plow+harrow' / 'plow/harrow' / 'plow ; harrow'."""
        if not s:
            return []
        for sep in [";", "/", "+", "|"]:
            s = s.replace(sep, ",")
        return [p.strip() for p in s.split(",") if p.strip()]
