# odm2_data/management/commands/load_site_field_information.py

import csv, os
from datetime import datetime
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from odm2_data.models import (
    # Core + CV
    SamplingFeatures, Variables, Units, Results,
    MeasurementResults, MeasurementResultValues,
    CategoricalResults, CategoricalResultValues,
    FeatureActions, Actions,
    CV_VariableName, CV_Units, CV_ActionType, CV_AnnotationType,
    CV_ResultsType, CV_CategoricalValue,
    # Annotations (pink)
    SamplingFeatureAnnotations,
)

class Command(BaseCommand):
    help = "Charger 4_site_field_information.csv (mesures ponctuelles, irrigation catégorielle, annotations) en ODM2"

    NUMERIC_COLS = ["soil_mineral_N", "depth", "pH"]
    ANNOTATION_COLS = ["precrop", "intercrop", "remark"]

    def add_arguments(self, parser):
        parser.add_argument("--path", default=os.path.join("data", "4_site_field_information.csv"))
        parser.add_argument("--encoding", default="latin1")
        parser.add_argument("--delimiter", default=";")
        parser.add_argument("--default-date", dest="default_date", default="2000-01-01")

    @transaction.atomic
    def handle(self, *args, **opts):
        path = opts["path"]; enc = opts["encoding"]; delim = opts["delimiter"]
        default_date = opts["default_date"]

        if not os.path.exists(path):
            self.stderr.write(f"❌ Fichier introuvable: {path}")
            return

        # ===== CV requis =====
        rt_meas = self._require_cv(CV_ResultsType, "Measurement")
        rt_cat  = self._require_cv(CV_ResultsType, "Categorical")
        if not (rt_meas and rt_cat):
            self.stderr.write("❌ CV_ResultsType ('Measurement','Categorical') manquants. Lancez d'abord load_cv.")
            return

        trial_type = self._ensure_cv(CV_ActionType, "Trial")
        # Unités par défaut si Unit_<col> absent
        DEFAULT_UNITS = {
            "soil_mineral_N": ["mg/kg", "g/kg"],
            "depth": ["cm"],
            "pH": ["unitless"],
        }

        with open(path, encoding=enc, newline="") as f:
            reader = csv.DictReader(f, delimiter=delim)

            required = {"site_no", "site", "Trial"}
            missing = required - set(reader.fieldnames or [])
            if missing:
                self.stderr.write(f"❌ En-têtes manquantes: {missing}")
                return

            has_year = "year" in reader.fieldnames

            for row in reader:
                try:
                    site_no = (row.get("site_no") or "").strip()
                    site_name = (row.get("site") or "").strip()
                    trial_label = (row.get("Trial") or "").strip()
                    if not site_no:
                        self.stdout.write(self.style.WARNING("⚠️ Ligne ignorée (site_no manquant)"))
                        continue
                    if not trial_label:
                        self.stdout.write(self.style.WARNING(f"⚠️ Ligne ignorée (Trial manquant) pour SITE_{site_no}"))
                        continue

                    site_code = f"SITE_{site_no}"
                    site = SamplingFeatures.objects.filter(SamplingFeatureCode=site_code).first()
                    if not site:
                        self.stderr.write(f"❌ Site introuvable (chargez d’abord 2_site_information): {site_code}")
                        continue

                    # Datetime (année si fournie, sinon default_date)
                    dt = self._dt_from_year_or_default((row.get("year") or "").strip(), default_date)
                    if timezone.is_naive(dt):
                        dt = timezone.make_aware(dt)

                    # ---- Action ‘Trial’ + FeatureAction (1 par site × trial × année)
                    trial_desc = f"Trial {trial_label} at {site_name or site_code}"
                    action, _ = Actions.objects.get_or_create(
                        ActionTypeCV=trial_type,
                        BeginDateTime=dt,
                        EndDateTime=dt,
                        ActionDescription=trial_desc
                    )
                    fa, _ = FeatureActions.objects.get_or_create(
                        SamplingFeatureID=site, ActionID=action
                    )

                    # ======================
                    # 1) Mesures ponctuelles
                    # ======================
                    for var_key in self.NUMERIC_COLS:
                        raw = (row.get(var_key) or "").strip()
                        if raw in ("", "NA"):
                            continue

                        var_cv = CV_VariableName.objects.filter(Name__iexact=var_key).first()
                        if not var_cv:
                            self.stdout.write(self.style.WARNING(
                                f"⚠️ CV_VariableName manquant pour '{var_key}' → ignoré"
                            ))
                            continue

                        # Unité (colonne Unit_<var> prioritaire, sinon DEFAULT_UNITS)
                        unit = self._resolve_unit((row.get(f"Unit_{var_key}") or "").strip(),
                                                  DEFAULT_UNITS.get(var_key, []))
                        if not unit:
                            self.stdout.write(self.style.WARNING(
                                f"⚠️ Unité introuvable pour {var_key} → ignoré"
                            ))
                            continue

                        # Variable (globale)
                        variable, _ = Variables.objects.get_or_create(
                            VariableCode=var_key.lower(),
                            defaults={"VariableNameCV": var_cv}
                        )

                        # Result (type = Measurement)
                        result, _ = Results.objects.get_or_create(
                            FeatureActionID=fa,
                            ResultTypeCV=rt_meas,
                            VariableID=variable,
                            UnitsID=unit,
                            defaults={"ResultDateTime": dt}
                        )
                        mres, _ = MeasurementResults.objects.get_or_create(ResultID=result)

                        try:
                            val = float(raw.replace(",", "."))
                        except ValueError:
                            self.stdout.write(self.style.WARNING(
                                f"⚠️ Valeur non numérique '{raw}' pour {var_key} ({site_code}) → ignorée"
                            ))
                            continue

                        MeasurementResultValues.objects.get_or_create(
                            ResultID=mres,
                            ValueDateTime=dt,
                            defaults={"DataValue": val, "hasCategorical": False}
                        )

                    # ======================
                    # 2) Irrigation (catégoriel)
                    # ======================
                    irr = (row.get("irrigation") or "").strip()
                    if irr and irr.upper() != "NA":
                        var_cv = CV_VariableName.objects.filter(Name__iexact="irrigation").first()
                        if var_cv:
                            variable, _ = Variables.objects.get_or_create(
                                VariableCode="irrigation",
                                defaults={"VariableNameCV": var_cv}
                            )
                            result, _ = Results.objects.get_or_create(
                                FeatureActionID=fa,
                                ResultTypeCV=rt_cat,
                                VariableID=variable,
                                UnitsID=None,
                                defaults={"ResultDateTime": dt}
                            )
                            cres, _ = CategoricalResults.objects.get_or_create(ResultID=result)

                            # ✅ essayer d'abord valeur contrôlée (FK), sinon garder la valeur libre
                            cv_val = CV_CategoricalValue.objects.filter(Name__iexact=irr).first()
                            if cv_val:
                                CategoricalResultValues.objects.get_or_create(
                                    ResultID=cres,
                                    ValueDateTime=dt,
                                    defaults={"DataValueCV": cv_val, "hasMeasurement": False}
                                )
                            else:
                                CategoricalResultValues.objects.get_or_create(
                                    ResultID=cres,
                                    ValueDateTime=dt,
                                    defaults={"DataValue": irr, "hasMeasurement": False}
                                )
                        else:
                            self.stdout.write(self.style.WARNING("⚠️ CV_VariableName 'irrigation' manquant → ignoré"))

                    # ======================
                    # 3) Annotations (modèle sans texte)
                    # ======================
                    for field in self.ANNOTATION_COLS:
                        txt = (row.get(field) or "").strip()
                        if not txt or txt.upper() == "NA":
                            continue
                        atype = (CV_AnnotationType.objects.filter(Name__iexact=field).first()
                                 or CV_AnnotationType.objects.filter(Name__iexact="remark").first())
                        if atype:
                            # NB: ton modèle SamplingFeatureAnnotations ne stocke pas le texte,
                            # on enregistre donc seulement le type + la date.
                            SamplingFeatureAnnotations.objects.get_or_create(
                                SamplingFeatureID=site,
                                AnnotationTypeCV=atype,
                                AnnotationDateTime=dt
                            )

                    self.stdout.write(self.style.SUCCESS(
                        f"✅ {site_code} — Trial '{trial_label}' importé"
                    ))

                except Exception as e:
                    self.stderr.write(f"❌ Erreur ligne {reader.line_num} ({row.get('site_no','?')}): {e}")
                    raise  # rollback

    # --------- helpers ----------
    def _dt_from_year_or_default(self, year_str: str, default_date: str) -> datetime:
        if year_str and year_str.upper() != "NA":
            try:
                return datetime(int(year_str), 1, 1)
            except ValueError:
                pass
        return datetime.fromisoformat(default_date)

    def _resolve_unit(self, explicit_name: str, fallbacks):
        """Retourne une instance Units (miroir) à partir d'un nom de CV_Units."""
        names = [explicit_name] if explicit_name else []
        names += [n for n in fallbacks if n]
        for nm in names:
            cvu = CV_Units.objects.filter(Name__iexact=nm).first()
            if cvu:
                unit, _ = Units.objects.get_or_create(UnitsName=cvu.Name, UnitsTypeCV=cvu)
                return unit
        return None

    def _ensure_cv(self, Model, name):
        """Renvoie un enregistrement CV (créé si absent) avec Term=Name=…"""
        if not name:
            return None
        obj = Model.objects.filter(Name__iexact=name).first()
        if obj:
            return obj
        return Model.objects.create(Term=name, Name=name)

    def _require_cv(self, Model, name):
        """Comme _ensure_cv mais ne crée pas — retourne None si absent."""
        return Model.objects.filter(Name__iexact=name).first()
