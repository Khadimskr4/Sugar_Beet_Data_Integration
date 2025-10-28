# odm2_data/management/commands/load_weather_data.py

import csv
import os
from datetime import datetime
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from odm2_data.models import (
    # CV
    CV_SamplingFeatureType, CV_ActionType, CV_VariableName, CV_Units,
    CV_ResultsType,
    # Core
    SamplingFeatures, Actions, FeatureActions, Variables, Units, Results,
    # Subtypes + Values
    MeasurementResults, MeasurementResultValues,
    TimeSeriesResults, TimeSeriesResultValues,
)

class Command(BaseCommand):
    help = "Charger 9_weather_data.csv : dps -> Measurement ; météo -> TimeSeries (réutilise les SamplingFeatures existants)"

    DPS_COL = "dps"
    TS_COLS = ["min_temp", "max_temp", "av_temp", "precipitation", "glob_radiation", "ET_grass"]

    DEFAULT_UNITS = {
        "dps": "unitless",
        "min_temp": "°C",
        "max_temp": "°C",
        "av_temp": "°C",
        "precipitation": "mm",
        "glob_radiation": "MJ/m²",
        "ET_grass": "mm",
    }

    def add_arguments(self, parser):
        parser.add_argument("--path", default=os.path.join("data", "9_weather_data.csv"))
        parser.add_argument("--encoding", default="latin1")
        parser.add_argument("--delimiter", default=";")

    @transaction.atomic
    def handle(self, *args, **opts):
        path = opts["path"]; enc = opts["encoding"]; delim = opts["delimiter"]

        if not os.path.exists(path):
            self.stderr.write(f"❌ Fichier introuvable : {path}")
            return

        # --- CV requis
        obs_type = self._ensure_cv(CV_ActionType, "Observation")
        rt_meas  = self._require_cv(CV_ResultsType, "Measurement")
        rt_ts    = self._require_cv(CV_ResultsType, "TimeSeries")
        if not (rt_meas and rt_ts):
            self.stderr.write("❌ CV_ResultsType ('Measurement', 'TimeSeries') manquants — lance `load_cv`.")
            return

        # Précharger les unités par défaut
        unit_cache = {}
        for key, uname in self.DEFAULT_UNITS.items():
            cvu = CV_Units.objects.filter(Name__iexact=uname).first()
            if not cvu:
                self.stderr.write(f"❌ Unité '{uname}' absente de CV_Units (pour {key}). Ajoute-la via `load_cv`.")
                return
            unit_cache[uname] = Units.objects.get_or_create(UnitsName=cvu.Name, UnitsTypeCV=cvu)[0]

        with open(path, encoding=enc, newline="") as f:
            reader = csv.DictReader(f, delimiter=delim)

            required = {"site_no", "site", "date", self.DPS_COL}
            missing = required - set(reader.fieldnames or [])
            if missing:
                self.stderr.write(f"❌ En-têtes manquantes : {missing}")
                return

            # colonnes Unit_* optionnelles (prioritaires si présentes)
            unit_cols = {c: f"Unit_{c}" for c in [self.DPS_COL] + self.TS_COLS}

            for row in reader:
                try:
                    site_no = (row.get("site_no") or "").strip()
                    site_nm = (row.get("site") or "").strip()
                    if not site_no:
                        self.stdout.write(self.style.WARNING("⚠️ Ligne ignorée (site_no manquant)"))
                        continue

                    site_code = f"SITE_{site_no}"

                    # --- Réutilisation du SamplingFeature (pas de création)
                    site = SamplingFeatures.objects.filter(SamplingFeatureCode=site_code).first()
                    if not site:
                        self.stdout.write(self.style.WARNING(
                            f"⚠️ SamplingFeature {site_code} introuvable (charge d’abord 2_site_information) — ligne ignorée"
                        ))
                        continue

                    # --- Datetime (date du jour météo)
                    dt = self._parse_date((row.get("date") or "").strip())
                    if not dt:
                        self.stdout.write(self.style.WARNING("⚠️ Date invalide — ligne ignorée"))
                        continue
                    if timezone.is_naive(dt):
                        dt = timezone.make_aware(dt)

                    # --- Action Observation + FeatureAction (idempotent)
                    desc = f"Weather observation {site_code} {dt.date().isoformat()}"
                    action, _ = Actions.objects.get_or_create(
                        ActionTypeCV=obs_type,
                        BeginDateTime=dt,
                        EndDateTime=dt,
                        ActionDescription=desc,
                    )
                    fa, _ = FeatureActions.objects.get_or_create(
                        SamplingFeatureID=site, ActionID=action
                    )

                    # ============= dps : Measurement =================
                    dps_raw = (row.get(self.DPS_COL) or "").strip()
                    if dps_raw and dps_raw.upper() != "NA":
                        dps_val = self._to_float(dps_raw)
                        if dps_val is None:
                            self.stdout.write(self.style.WARNING(f"⚠️ dps non numérique '{dps_raw}' @ {site_code}"))
                        else:
                            dps_cv = self._ensure_cv(CV_VariableName, self.DPS_COL)
                            dps_var, _ = Variables.objects.get_or_create(
                                VariableCode=self.DPS_COL.lower(),
                                defaults={"VariableNameCV": dps_cv}
                            )
                            # unité (colonne Unit_dps prioritaire)
                            unit = self._resolve_unit_override(row.get(unit_cols[self.DPS_COL]), self.DEFAULT_UNITS[self.DPS_COL], unit_cache)

                            res, _ = Results.objects.get_or_create(
                                FeatureActionID=fa, ResultTypeCV=rt_meas,
                                VariableID=dps_var, UnitsID=unit,
                                defaults={"ResultDateTime": dt}
                            )
                            mres, _ = MeasurementResults.objects.get_or_create(ResultID=res)
                            MeasurementResultValues.objects.get_or_create(
                                ResultID=mres, ValueDateTime=dt,
                                defaults={"DataValue": dps_val, "hasCategorical": False}
                            )

                    # ============= Météo : TimeSeries =================
                    for col in self.TS_COLS:
                        raw = (row.get(col) or "").strip()
                        if not raw or raw.upper() == "NA":
                            continue
                        val = self._to_float(raw)
                        if val is None:
                            self.stdout.write(self.style.WARNING(f"⚠️ Valeur non numérique '{raw}' pour {col} @ {site_code}"))
                            continue

                        vcv = self._ensure_cv(CV_VariableName, col)
                        var, _ = Variables.objects.get_or_create(
                            VariableCode=col.lower(),
                            defaults={"VariableNameCV": vcv}
                        )
                        # unité (Unit_<col> prioritaire)
                        unit = self._resolve_unit_override(row.get(unit_cols[col]), self.DEFAULT_UNITS[col], unit_cache)

                        res, _ = Results.objects.get_or_create(
                            FeatureActionID=fa, ResultTypeCV=rt_ts,
                            VariableID=var, UnitsID=unit,
                            defaults={"ResultDateTime": dt}
                        )
                        ts, _ = TimeSeriesResults.objects.get_or_create(ResultID=res)
                        TimeSeriesResultValues.objects.get_or_create(
                            ResultID=ts, ValueDateTime=dt,
                            defaults={"DataValue": val}
                        )

                    self.stdout.write(self.style.SUCCESS(f"✅ {site_code} — {dt.date().isoformat()}"))

                except Exception as e:
                    self.stderr.write(f"❌ Erreur ligne {reader.line_num} ({row.get('site_no') or '?'}) : {e}")
                    raise  # rollback

    # ---------------- helpers ----------------
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

    def _to_float(self, s: str):
        try:
            return float(str(s).replace(",", "."))
        except Exception:
            return None

    def _ensure_cv(self, Model, name):
        obj = Model.objects.filter(Name__iexact=name).first()
        if obj:
            return obj
        return Model.objects.create(Term=name, Name=name)

    def _require_cv(self, Model, name):
        return Model.objects.filter(Name__iexact=name).first()

    def _resolve_unit_override(self, unit_cell, default_unit_name, cache):
        """
        Si une colonne Unit_<var> existe et matche un CV_Units, on l'utilise.
        Sinon on prend l'unité par défaut (déjà mise en cache).
        """
        unit_cell = (unit_cell or "").strip()
        if unit_cell:
            cvu = CV_Units.objects.filter(Name__iexact=unit_cell).first()
            if cvu:
                return Units.objects.get_or_create(UnitsName=cvu.Name, UnitsTypeCV=cvu)[0]
        # fallback par défaut préchargé
        return cache[default_unit_name]
