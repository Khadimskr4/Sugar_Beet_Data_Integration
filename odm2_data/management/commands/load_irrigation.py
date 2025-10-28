# odm2_data/management/commands/load_irrigation.py

import csv
import os
from datetime import datetime
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from odm2_data.models import (
    # Core & CV (version PascalCase du modèle récent)
    SamplingFeatures,
    Variables, Units, Results,
    TimeSeriesResults, TimeSeriesResultValues,
    FeatureActions, Actions,
    CV_ActionType, CV_VariableName, CV_Units, CV_ResultsType,
)

class Command(BaseCommand):
    help = "Charger 7_irrigation.csv (Action Irrigation + quantité) en TimeSeriesResults/TimeSeriesResultValues"

    def add_arguments(self, parser):
        parser.add_argument("--path", default=os.path.join("data", "7_irrigation.csv"))
        parser.add_argument("--encoding", default="latin1")
        parser.add_argument("--delimiter", default=";")

    @transaction.atomic
    def handle(self, *args, **opts):
        path = opts["path"]; enc = opts["encoding"]; delim = opts["delimiter"]

        if not os.path.exists(path):
            self.stderr.write(f"❌ Fichier introuvable: {path}")
            return

        # ===== CV requis =====
        irrig_act = self._ensure_cv(CV_ActionType, "Irrigation")
        trial_act = self._ensure_cv(CV_ActionType, "Trial")
        rt_ts     = self._require_cv(CV_ResultsType, "TimeSeries")
        if not rt_ts:
            self.stderr.write("❌ CV_ResultsType 'TimeSeries' manquant. Lance d’abord load_cv.")
            return

        var_cv = self._require_cv(CV_VariableName, "irrigation_amount")
        if not var_cv:
            self.stderr.write("❌ CV_VariableName 'irrigation_amount' manquant. Lance d’abord load_cv.")
            return

        # Unité par défaut: mm
        default_unit = self._get_or_create_units("mm")
        if not default_unit:
            self.stderr.write("❌ Unité 'mm' manquante dans CV_Units. Lance d’abord load_cv.")
            return

        with open(path, encoding=enc, newline="") as f:
            reader = csv.DictReader(f, delimiter=delim)

            required = {"site_no", "site", "date"}
            missing = required - set(reader.fieldnames or [])
            if missing:
                self.stderr.write(f"❌ En-têtes manquantes: {missing}")
                return

            has_trial_col = "trial" in {h.lower() for h in reader.fieldnames}
            has_unit_col  = "Unit_irrigation_amount" in reader.fieldnames

            # certaines versions de fichier ont une faute de frappe
            headers_lower = {h.lower(): h for h in reader.fieldnames}
            value_col = headers_lower.get("irrigation_amount") or headers_lower.get("irrigation_amoun")
            if not value_col:
                self.stderr.write("❌ Colonne 'irrigation_amount' (ou 'irrigation_amoun') introuvable.")
                return

            for row in reader:
                try:
                    site_no   = (row.get("site_no") or "").strip()
                    site_name = (row.get("site") or "").strip()
                    if not site_no:
                        self.stdout.write(self.style.WARNING("⚠️ Ligne ignorée (site_no manquant)"))
                        continue
                    site_code = f"SITE_{site_no}"

                    site = SamplingFeatures.objects.filter(SamplingFeatureCode=site_code).first()
                    if not site:
                        self.stderr.write(f"❌ Site introuvable (charge d’abord 2_site_information): {site_code}")
                        continue

                    # Date → timezone-aware
                    dt = self._parse_date((row.get("date") or "").strip())
                    if not dt:
                        self.stdout.write(self.style.WARNING(f"⚠️ Date invalide pour {site_code} → ligne ignorée"))
                        continue
                    if timezone.is_naive(dt):
                        dt = timezone.make_aware(dt)

                    # Trial optionnel (ancré au 1er janvier de l'année)
                    if has_trial_col:
                        trial_label = (row.get(headers_lower.get("trial")) or "").strip()
                        if trial_label and trial_label.upper() != "NA":
                            t_ref = dt.replace(month=1, day=1)
                            t_desc = f"Trial {trial_label} at {site_name or site_code}"
                            t_action, _ = Actions.objects.get_or_create(
                                ActionTypeCV=trial_act,
                                BeginDateTime=t_ref, EndDateTime=t_ref,
                                ActionDescription=t_desc
                            )
                            FeatureActions.objects.get_or_create(
                                SamplingFeatureID=site, ActionID=t_action
                            )

                    # Action Irrigation (idempotente: (type, begin, end, desc))
                    irrig_desc = f"Irrigation at {site_name or site_code} on {dt.date().isoformat()}"
                    action, _ = Actions.objects.get_or_create(
                        ActionTypeCV=irrig_act,
                        BeginDateTime=dt, EndDateTime=dt,
                        ActionDescription=irrig_desc
                    )
                    fa, _ = FeatureActions.objects.get_or_create(
                        SamplingFeatureID=site, ActionID=action
                    )

                    # Valeur de quantité
                    raw = (row.get(value_col) or "").strip()
                    if raw == "" or raw.upper() == "NA":
                        self.stdout.write(self.style.WARNING(
                            f"⚠️ Quantité d'irrigation manquante pour {site_code} au {dt.date().isoformat()}"
                        ))
                        continue
                    try:
                        val = float(str(raw).replace(",", "."))
                    except ValueError:
                        self.stdout.write(self.style.WARNING(
                            f"⚠️ Valeur non numérique '{raw}' pour {site_code} au {dt.date().isoformat()} → ignorée"
                        ))
                        continue

                    # Variable (globale, code stable)
                    variable, _ = Variables.objects.get_or_create(
                        VariableCode="irrigation_amount",
                        defaults={"VariableNameCV": var_cv}
                    )

                    # Unité explicite si fournie
                    unit_obj = default_unit
                    if has_unit_col:
                        explicit = (row.get("Unit_irrigation_amount") or "").strip()
                        if explicit:
                            resolved = self._get_or_create_units(explicit)
                            if resolved:
                                unit_obj = resolved
                            else:
                                self.stdout.write(self.style.WARNING(
                                    f"⚠️ Unité '{explicit}' inconnue → fallback 'mm'"
                                ))

                    # Result (TimeSeries) + Value
                    res, _ = Results.objects.get_or_create(
                        FeatureActionID=fa,
                        ResultTypeCV=rt_ts,
                        VariableID=variable,
                        UnitsID=unit_obj,
                        defaults={"ResultDateTime": dt}
                    )
                    ts, _ = TimeSeriesResults.objects.get_or_create(ResultID=res)
                    TimeSeriesResultValues.objects.get_or_create(
                        ResultID=ts, ValueDateTime=dt,
                        defaults={"DataValue": val}
                    )

                    self.stdout.write(self.style.SUCCESS(
                        f"✅ {site_code} — {dt.date().isoformat()} — {val} {unit_obj.UnitsName}"
                    ))

                except Exception as e:
                    self.stderr.write(f"❌ Erreur ligne {reader.line_num} ({row.get('site_no','?')}): {e}")
                    raise  # rollback

    # ---------- helpers ----------
    def _parse_date(self, s: str):
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

    def _ensure_cv(self, Model, name):
        obj = Model.objects.filter(Name__iexact=name).first()
        if obj:
            return obj
        return Model.objects.create(Term=name, Name=name)

    def _require_cv(self, Model, name):
        return Model.objects.filter(Name__iexact=name).first()

    def _get_or_create_units(self, units_name: str):
        """Assure l’existence du couple CV_Units + Units (miroir) et retourne l’instance Units."""
        if not units_name:
            return None
        cvu = CV_Units.objects.filter(Name__iexact=units_name).first()
        if not cvu:
            # crée un CV_Units minimal si absent (cohérent avec tes autres loaders)
            cvu = CV_Units.objects.create(
                Term=units_name, Name=units_name, Definition="", Category="", SourceVocabularyURI=""
            )
        unit, _ = Units.objects.get_or_create(UnitsName=cvu.Name, UnitsTypeCV=cvu)
        return unit
