# odm2_data/management/commands/load_sowing_field_emergence.py

import csv
import os
from datetime import datetime
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from odm2_data.models import (
    # Core + subtypes
    SamplingFeatures, Variables, Units, Results,
    MeasurementResults, MeasurementResultValues,
    CategoricalResults, CategoricalResultValues,
    Actions, FeatureActions,
    # CV tables
    CV_VariableName, CV_Units, CV_ActionType, CV_AnnotationType,
    CV_ResultsType, CV_CategoricalValue,
    # Annotations (pink)
    SamplingFeatureAnnotations,
)

class Command(BaseCommand):
    help = "Charger 5_sowing_field_emergence.csv (actions Sowing/Measure, mesures, variété, remarques)"

    NUMERIC_VARS = ["sowing_density", "rate_emergence", "beet_rows"]
    DEFAULT_UNITS = {
        "sowing_density": "seeds/ha",
        "rate_emergence": "%",
        "beet_rows": "unitless",
    }

    def add_arguments(self, parser):
        parser.add_argument("--path", default=os.path.join("data", "5_sowing_field_emergence.csv"))
        parser.add_argument("--encoding", default="latin1")
        parser.add_argument("--delimiter", default=";")

    @transaction.atomic
    def handle(self, *args, **opts):
        path = opts["path"]; enc = opts["encoding"]; delim = opts["delimiter"]

        if not os.path.exists(path):
            self.stderr.write(f"❌ Fichier introuvable: {path}")
            return

        # === CV requis (Result types) ===
        rt_meas = self._require_cv(CV_ResultsType, "Measurement")
        rt_cat  = self._require_cv(CV_ResultsType, "Categorical")
        if not (rt_meas and rt_cat):
            self.stderr.write("❌ CV_ResultsType ('Measurement','Categorical') manquants. Lance d'abord load_cv.")
            return

        # Action types (créés au besoin)
        sow_type = self._ensure_cv(CV_ActionType, "Sowing")
        meas_type = self._ensure_cv(CV_ActionType, "Measure")
        obs_type  = self._ensure_cv(CV_ActionType, "Observation")

        with open(path, encoding=enc, newline="") as f:
            reader = csv.DictReader(f, delimiter=delim)

            required = {"site_no", "site", "date"}
            missing = required - set(reader.fieldnames or [])
            if missing:
                self.stderr.write(f"❌ En-têtes manquantes: {missing}")
                return

            for row in reader:
                try:
                    site_no = (row.get("site_no") or "").strip()
                    site_name = (row.get("site") or "").strip()
                    if not site_no:
                        self.stdout.write(self.style.WARNING("⚠️ Ligne ignorée (site_no manquant)"))
                        continue

                    site_code = f"SITE_{site_no}"
                    site = SamplingFeatures.objects.filter(SamplingFeatureCode=site_code).first()
                    if not site:
                        self.stderr.write(f"❌ Site introuvable (charge d’abord 2_site_information): {site_code}")
                        continue

                    # --- date
                    dt = self._parse_date((row.get("date") or "").strip())
                    if not dt:
                        self.stdout.write(self.style.WARNING(f"⚠️ Date invalide pour {site_code} → ligne ignorée"))
                        continue
                    if timezone.is_naive(dt):
                        dt = timezone.make_aware(dt)

                    # --- Choix du type d'action à partir des colonnes sowing/measure
                    sow_flag = (row.get("sowing") or "").strip()
                    meas_flag = (row.get("measure") or "").strip()

                    if sow_flag and sow_flag.upper() not in ("NA", "0", "NO", "NON", "FALSE"):
                        atype = sow_type; aname = "Sowing"
                    elif meas_flag and meas_flag.upper() not in ("NA", "0", "NO", "NON", "FALSE"):
                        atype = meas_type; aname = "Measure"
                    else:
                        atype = obs_type;  aname = "Observation"

                    # --- Action (1 par site × date × type) + FeatureAction
                    desc = f"{aname} at {site_name or site_code} on {dt.date().isoformat()}"
                    action, _ = Actions.objects.get_or_create(
                        ActionTypeCV=atype,
                        BeginDateTime=dt,
                        EndDateTime=dt,
                        ActionDescription=desc
                    )
                    fa, _ = FeatureActions.objects.get_or_create(
                        SamplingFeatureID=site,
                        ActionID=action
                    )

                    # ======================
                    # 1) Mesures numériques
                    # ======================
                    for var in self.NUMERIC_VARS:
                        raw = (row.get(var) or "").strip()
                        if raw in ("", "NA"):
                            continue

                        var_cv = CV_VariableName.objects.filter(Name__iexact=var).first()
                        if not var_cv:
                            self.stdout.write(self.style.WARNING(f"⚠️ CV_VariableName manquant pour '{var}' → ignoré"))
                            continue

                        unit_name = (row.get(f"Unit_{var}") or "").strip() or self.DEFAULT_UNITS[var]
                        unit = self._get_or_create_units(unit_name)
                        if not unit:
                            self.stdout.write(self.style.WARNING(f"⚠️ Unité introuvable pour {var} → ignoré"))
                            continue

                        variable, _ = Variables.objects.get_or_create(
                            VariableCode=var.lower(),
                            defaults={"VariableNameCV": var_cv}
                        )

                        res, _ = Results.objects.get_or_create(
                            FeatureActionID=fa,
                            ResultTypeCV=rt_meas,
                            VariableID=variable,
                            UnitsID=unit,
                            defaults={"ResultDateTime": dt}
                        )
                        mres, _ = MeasurementResults.objects.get_or_create(ResultID=res)

                        try:
                            val = float(str(raw).replace(",", "."))
                        except ValueError:
                            self.stdout.write(self.style.WARNING(
                                f"⚠️ Valeur non numérique '{raw}' pour {var} ({site_code}) → ignorée"
                            ))
                            continue

                        MeasurementResultValues.objects.get_or_create(
                            ResultID=mres,
                            ValueDateTime=dt,
                            defaults={"DataValue": val, "hasCategorical": False}
                        )

                    # ======================
                    # 2) Variété (catégoriel)
                    # ======================
                    variety = (row.get("variety") or "").strip()
                    if variety and variety.upper() != "NA":
                        vcv = CV_VariableName.objects.filter(Name__iexact="variety").first()
                        if vcv:
                            variable, _ = Variables.objects.get_or_create(
                                VariableCode="variety",
                                defaults={"VariableNameCV": vcv}
                            )
                            res, _ = Results.objects.get_or_create(
                                FeatureActionID=fa,
                                ResultTypeCV=rt_cat,
                                VariableID=variable,
                                UnitsID=None,
                                defaults={"ResultDateTime": dt}
                            )
                            cres, _ = CategoricalResults.objects.get_or_create(ResultID=res)

                            # D'abord valeur contrôlée (CV_CategoricalValue), sinon DataValue libre
                            cv_val = CV_CategoricalValue.objects.filter(Name__iexact=variety).first()
                            if cv_val:
                                CategoricalResultValues.objects.get_or_create(
                                    ResultID=cres, ValueDateTime=dt,
                                    defaults={"DataValueCV": cv_val, "DataValue": None, "hasMeasurement": False}
                                )
                            else:
                                CategoricalResultValues.objects.get_or_create(
                                    ResultID=cres, ValueDateTime=dt,
                                    defaults={"DataValue": variety, "DataValueCV": None, "hasMeasurement": False}
                                )
                        else:
                            self.stdout.write(self.style.WARNING("⚠️ CV_VariableName 'variety' manquant → ignoré"))

                    # ======================
                    # 3) Remarque → Annotation (sans texte dans ton modèle)
                    # ======================
                    remark = (row.get("remark") or "").strip()
                    if remark and remark.upper() != "NA":
                        at = CV_AnnotationType.objects.filter(Name__iexact="remark").first()
                        if at:
                            SamplingFeatureAnnotations.objects.get_or_create(
                                SamplingFeatureID=site,
                                AnnotationTypeCV=at,
                                AnnotationDateTime=dt
                            )

                    self.stdout.write(self.style.SUCCESS(
                        f"✅ {site_code} — {aname} au {dt.date().isoformat()} importé"
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

    def _require_cv(self, Model, name):
        return Model.objects.filter(Name__iexact=name).first()

    def _ensure_cv(self, Model, name):
        obj = self._require_cv(Model, name)
        if obj:
            return obj
        return Model.objects.create(Term=name, Name=name)

    def _get_or_create_units(self, units_name: str):
        """Assure l’existence du CV_Units(Name) et crée/retourne Units miroir."""
        if not units_name:
            return None
        cvu = CV_Units.objects.filter(Name__iexact=units_name).first()
        if not cvu:
            cvu = CV_Units.objects.create(Term=units_name, Name=units_name, Definition="", Category="", SourceVocabularyURI="")
        unit, _ = Units.objects.get_or_create(UnitsName=cvu.Name, UnitsTypeCV=cvu)
        return unit
