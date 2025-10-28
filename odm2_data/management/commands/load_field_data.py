# odm2_data/management/commands/load_field_data.py

import csv
import os
from datetime import datetime
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from odm2_data.models import (
    # Core + CV (exactement comme dans ton modèle)
    SamplingFeatures, Sites,
    CV_SamplingFeatureType, CV_SiteType,
    CV_RelationshipType, RelatedFeatures,
    CV_ActionType, Actions, FeatureActions,
    CV_VariableName, Variables,
    CV_Units, Units,
    CV_ResultsType, Results,
    MeasurementResults, MeasurementResultValues,
    CategoricalResults, CategoricalResultValues,
    CV_CategoricalValue,
)

NUMERIC_VARS = [
    "dps", "soil_moisture_30", "soil_moisture_60", "soil_moisture_90",
    "PAW_30", "PAW_60", "PAW_90",
    "root_yield", "root_dry_matter",
    "leaf_yield", "leaf_dry_matter",
    "LAI", "n", "sugar", "K", "Na",
    "amino_N", "soluble_Nt", "NO3", "betaine", "invert_sugar", "marc",
]

UNIT_MAP = {
    "dps": "unitless",
    "soil_moisture_30": "%", "soil_moisture_60": "%", "soil_moisture_90": "%",
    "PAW_30": "mm", "PAW_60": "mm", "PAW_90": "mm",
    "root_yield": "t/ha", "root_dry_matter": "%",
    "leaf_yield": "t/ha", "leaf_dry_matter": "%",
    "LAI": "unitless",
    "n": "%", "sugar": "%",
    "K": "g/kg", "Na": "g/kg", "amino_N": "g/kg", "soluble_Nt": "g/kg",
    "NO3": "g/kg", "betaine": "g/kg",
    "invert_sugar": "%", "marc": "%",
}

class Command(BaseCommand):
    help = "Charger 8_field_data.csv : réplications (Sites type 'rep'), Trial/Observation, mesures & irrigation (cat)"

    def add_arguments(self, parser):
        parser.add_argument("--path", default=os.path.join("data", "8_field_data.csv"))
        parser.add_argument("--encoding", default="latin1")
        parser.add_argument("--delimiter", default=";")

    @transaction.atomic
    def handle(self, *args, **opts):
        path = opts["path"]; enc = opts["encoding"]; delim = opts["delimiter"]

        if not os.path.exists(path):
            self.stderr.write(f"❌ Fichier introuvable: {path}")
            return

        # --------- CV requis ---------
        sf_type = CV_SamplingFeatureType.objects.filter(Name__iexact="site").first()
        site_type_site = CV_SiteType.objects.filter(Name__iexact="site").first()
        site_type_rep = CV_SiteType.objects.filter(Name__iexact="rep").first()
        if not (sf_type and site_type_site and site_type_rep):
            self.stderr.write("❌ CV manquants (SamplingFeatureType 'site', SiteType 'site'/'rep'). Lance `load_cv`.")
            return

        # Relations hiérarchiques (rep -> site ; site -> rep)
        rel_is_part_of = self._ensure_cv(CV_RelationshipType, "isPartOf")
        rel_is_parent_of = self._ensure_cv(CV_RelationshipType, "isParentOf")

        trial_type = self._ensure_cv(CV_ActionType, "Trial")
        obs_type   = self._ensure_cv(CV_ActionType, "Observation")

        rt_meas = CV_ResultsType.objects.filter(Name__iexact="Measurement").first()
        rt_cat  = CV_ResultsType.objects.filter(Name__iexact="Categorical").first()
        if not (rt_meas and rt_cat):
            self.stderr.write("❌ CV_ResultsType ('Measurement','Categorical') manquants. Lance `load_cv`.")
            return

        irrigation_cv = CV_VariableName.objects.filter(Name__iexact="irrigation").first()

        # --------- Précharger les Units ----------
        unit_cache = {}
        for u in sorted(set(UNIT_MAP.values())):
            cvu = CV_Units.objects.filter(Name__iexact=u).first()
            if not cvu:
                self.stderr.write(f"❌ Unité '{u}' absente de CV_Units. Lance `load_cv`.")
                return
            unit_cache[u] = Units.objects.get_or_create(UnitsName=cvu.Name, UnitsTypeCV=cvu)[0]

        with open(path, encoding=enc, newline="") as f:
            reader = csv.DictReader(f, delimiter=delim)
            required = {"site_no", "site", "rep", "date", "Trial"}
            missing = required - set(reader.fieldnames or [])
            if missing:
                self.stderr.write(f"❌ En-têtes manquantes: {missing}")
                return

            for row in reader:
                try:
                    site_no = (row.get("site_no") or "").strip()
                    site_nm = (row.get("site") or "").strip()
                    rep_lbl = (row.get("rep") or "").strip()
                    trial   = (row.get("Trial") or "").strip()

                    if not site_no or not rep_lbl:
                        self.stdout.write(self.style.WARNING("⚠️ Ligne ignorée (site_no/rep manquant)"))
                        continue

                    site_code = f"SITE_{site_no}"
                    rep_code  = f"{site_code}_REP{rep_lbl}"

                    # ----- SamplingFeature parent (site) + Sites(type=site)
                    site_sf, _ = SamplingFeatures.objects.get_or_create(
                        SamplingFeatureCode=site_code,
                        defaults={
                            "SamplingFeatureTypeCV": sf_type,
                            "SamplingFeatureName": site_nm or site_code,
                            "SamplingFeatureDescription": site_nm or site_code,
                        },
                    )
                    Sites.objects.get_or_create(
                        SamplingFeatureID=site_sf,
                        defaults={"SiteTypeCV": site_type_site}
                    )

                    # ----- SamplingFeature réplication (type=site) + Sites(type=rep)
                    rep_sf, created_rep = SamplingFeatures.objects.get_or_create(
                        SamplingFeatureCode=rep_code,
                        defaults={
                            "SamplingFeatureTypeCV": sf_type,
                            "SamplingFeatureName": f"{site_nm}_REP{rep_lbl}" if site_nm else rep_code,
                            "SamplingFeatureDescription": f"Replication {rep_lbl} of {site_code}",
                        },
                    )
                    Sites.objects.get_or_create(
                        SamplingFeatureID=rep_sf,
                        defaults={"SiteTypeCV": site_type_rep}
                    )

                    # ----- Liens RelatedFeatures (idempotents)
                    # rep --isPartOf--> site
                    RelatedFeatures.objects.get_or_create(
                        SamplingFeatureID=rep_sf,
                        RelatedFeatureID=site_sf,
                        RelationshipTypeCV=rel_is_part_of,
                    )
                    # site --isParentOf--> rep
                    RelatedFeatures.objects.get_or_create(
                        SamplingFeatureID=site_sf,
                        RelatedFeatureID=rep_sf,
                        RelationshipTypeCV=rel_is_parent_of,
                    )

                    # ----- Date (aware)
                    dt = self._parse_date((row.get("date") or "").strip())
                    if not dt:
                        self.stdout.write(self.style.WARNING(f"⚠️ Date invalide (ligne {reader.line_num})"))
                        continue
                    if timezone.is_naive(dt):
                        dt = timezone.make_aware(dt)

                    # ----- Actions du jour (Trial + Observation) sur la réplication
                    trial_action, _ = Actions.objects.get_or_create(
                        ActionTypeCV=trial_type,
                        BeginDateTime=dt, EndDateTime=dt,
                        ActionDescription=f"Trial {trial or ''} at {rep_code}".strip(),
                    )
                    trial_fa, _ = FeatureActions.objects.get_or_create(
                        SamplingFeatureID=rep_sf, ActionID=trial_action
                    )

                    obs_action, _ = Actions.objects.get_or_create(
                        ActionTypeCV=obs_type,
                        BeginDateTime=dt, EndDateTime=dt,
                        ActionDescription=f"Observation at {rep_code} on {dt.date()}",
                    )
                    obs_fa, _ = FeatureActions.objects.get_or_create(
                        SamplingFeatureID=rep_sf, ActionID=obs_action
                    )

                    # ----- Mesures numériques
                    for var in NUMERIC_VARS:
                        raw = (row.get(var) or "").strip()
                        if raw == "" or raw.upper() == "NA":
                            continue
                        try:
                            val = float(raw.replace(",", "."))
                        except ValueError:
                            self.stdout.write(self.style.WARNING(
                                f"⚠️ Valeur non numérique '{raw}' pour {var} (ligne {reader.line_num})"
                            ))
                            continue

                        var_cv = CV_VariableName.objects.filter(Name__iexact=var).first()
                        if not var_cv:
                            self.stdout.write(self.style.WARNING(f"⚠️ CV_VariableName manquant pour '{var}' → ignoré"))
                            continue

                        unit = unit_cache[UNIT_MAP.get(var, "unitless")]

                        variable, _ = Variables.objects.get_or_create(
                            VariableCode=f"{var.lower()}_{rep_code.lower()}",
                            defaults={"VariableNameCV": var_cv}
                        )

                        result, _ = Results.objects.get_or_create(
                            FeatureActionID=obs_fa,
                            ResultTypeCV=rt_meas,
                            VariableID=variable,
                            UnitsID=unit,
                            defaults={"ResultDateTime": dt}
                        )
                        mres, _ = MeasurementResults.objects.get_or_create(ResultID=result)
                        MeasurementResultValues.objects.get_or_create(
                            ResultID=mres, ValueDateTime=dt,
                            defaults={"DataValue": val, "hasCategorical": False}
                        )

                    # ----- Irrigation (catégoriel) si présent
                    if "irrigation" in reader.fieldnames:
                        irr = (row.get("irrigation") or "").strip()
                        if irr and irr.upper() != "NA" and irrigation_cv:
                            irrigation_var, _ = Variables.objects.get_or_create(
                                VariableCode=f"irrigation_{rep_code.lower()}",
                                defaults={"VariableNameCV": irrigation_cv},
                            )
                            irr_res, _ = Results.objects.get_or_create(
                                FeatureActionID=obs_fa,
                                ResultTypeCV=rt_cat,
                                VariableID=irrigation_var,
                                UnitsID=None,
                                defaults={"ResultDateTime": dt}
                            )
                            cat, _ = CategoricalResults.objects.get_or_create(ResultID=irr_res)

                            cv_val = CV_CategoricalValue.objects.filter(Name__iexact=irr).first()
                            if cv_val:
                                CategoricalResultValues.objects.get_or_create(
                                    ResultID=cat, ValueDateTime=dt,
                                    defaults={"DataValueCV": cv_val, "hasMeasurement": False}
                                )
                            else:
                                CategoricalResultValues.objects.get_or_create(
                                    ResultID=cat, ValueDateTime=dt,
                                    defaults={"DataValue": irr, "hasMeasurement": False}
                                )

                    self.stdout.write(self.style.SUCCESS(f"✅ {rep_code} — {dt.date()}"))

                except Exception as e:
                    self.stderr.write(f"❌ Erreur ligne {reader.line_num}: {e}")
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

    def _ensure_cv(self, Model, name: str):
        obj = Model.objects.filter(Name__iexact=name).first()
        if obj:
            return obj
        return Model.objects.create(Term=name, Name=name)
