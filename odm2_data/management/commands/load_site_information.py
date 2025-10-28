# odm2_data/management/commands/load_sites_from_2_site_information.py

import csv
import os
from django.core.management.base import BaseCommand
from django.utils.dateparse import parse_datetime
from django.db import transaction

from odm2_data.models import (
    # Core & CV (version PascalCase)
    SamplingFeatures, CV_SamplingFeatureType, CV_SiteType, Sites,
    CV_VariableName, CV_Units, CV_CategoricalValue,
    Variables, Units, Results,
    MeasurementResults, MeasurementResultValues,
    CategoricalResults, CategoricalResultValues,
    Actions, CV_ActionType, FeatureActions,
    CV_ResultsType,
)

class Command(BaseCommand):
    help = "Charger SamplingFeatures/Sites + variables mesurées & catégorielles depuis 2_site_information.csv"

    # --- Mapping selon le tableau fourni ---
    MEASUREMENT_COLS = {
        "Ackerzahl",
        "field_capacity",
        "available_water_capacity",
        "availabe_water_root_zone",
        "annual_mean_temperature",
        "annual_rainfall",
    }
    CATEGORICAL_COLS = {"soil_type", "soil_texture", "soil_texture_class"}

    ID_COLS = {"site_no", "site", "latitude", "longitude", "altitude"}  # colonnes identitaires

    # unités par défaut pour les variables de mesure
    DEFAULT_UNITS = {
        "Ackerzahl": "unitless",
        "field_capacity": "%",                      # capacité au champ en %
        "available_water_capacity": "mm",           # AWC souvent en mm
        "availabe_water_root_zone": "mm",
        "annual_mean_temperature": "°C",
        "annual_rainfall": "mm",
    }

    def add_arguments(self, parser):
        parser.add_argument("--path", default=os.path.join("data", "2_site_information.csv"))
        parser.add_argument("--encoding", default="latin1")
        parser.add_argument("--delimiter", default=";")
        parser.add_argument("--default-date", default="2000-01-01T00:00:00")

    @transaction.atomic
    def handle(self, *args, **opts):
        file_path = opts["path"]
        encoding = opts["encoding"]
        delimiter = opts["delimiter"]
        default_dt = parse_datetime(opts["default_date"])

        if not os.path.exists(file_path):
            self.stdout.write(self.style.ERROR(f"❌ Fichier introuvable: {file_path}"))
            return

        # ---- CV requis (FK par Name, insensible à la casse)
        sft_site = self._get_cv(CV_SamplingFeatureType, "site")
        if not sft_site:
            raise RuntimeError("CV_SamplingFeatureType.Name='site' introuvable. Charge d'abord les CV.")
        sitetype_site = self._get_cv(CV_SiteType, "site")
        if not sitetype_site:
            raise RuntimeError("CV_SiteType.Name='site' introuvable. Charge d'abord les CV.")
        act_obs = self._ensure_cv(CV_ActionType, "Observation", Term="Observation")
        rt_meas = self._ensure_cv(CV_ResultsType, "Measurement", Term="Measurement")
        rt_cat = self._ensure_cv(CV_ResultsType, "Categorical", Term="Categorical")

        with open(file_path, encoding=encoding, newline="") as f:
            reader = csv.DictReader(f, delimiter=delimiter)

            required = {"site_no", "site", "latitude", "longitude", "altitude"}
            missing = required - set(reader.fieldnames or [])
            if missing:
                self.stdout.write(self.style.ERROR(f"❌ En-têtes manquants: {missing}"))
                return

            for row in reader:
                site_no = (row.get("site_no") or "").strip()
                site_label = (row.get("site") or "").strip()
                if not site_no:
                    self.stdout.write(self.style.WARNING("⚠️ Ligne ignorée: site_no manquant"))
                    continue

                lat = self._to_float(row.get("latitude"))
                lon = self._to_float(row.get("longitude"))
                alt = self._to_float(row.get("altitude"))

                site_code = f"SITE_{site_no}"
                geom = f"POINT({lon} {lat})" if lat is not None and lon is not None else None

                # --- SamplingFeatures
                sf, _ = SamplingFeatures.objects.get_or_create(
                    SamplingFeatureCode=site_code,
                    defaults={
                        "SamplingFeatureTypeCV": sft_site,
                        "SamplingFeatureName": site_label or site_code,
                        "SamplingFeatureDescription": f"Site n°{site_no} - {site_label}" if site_label else f"Site n°{site_no}",
                        "FeatureGeometry": geom,
                        "Elevation_m": alt,
                    }
                )
                # compléter si des champs étaient vides
                changed = False
                if sf.FeatureGeometry in (None, "") and geom:
                    sf.FeatureGeometry = geom; changed = True
                if sf.Elevation_m is None and alt is not None:
                    sf.Elevation_m = alt; changed = True
                if changed:
                    sf.save()

                # --- Sites (PK=FK)
                site_obj, _ = Sites.objects.get_or_create(
                    SamplingFeatureID=sf,
                    defaults={"SiteTypeCV": sitetype_site, "Latitude": lat, "Longitude": lon}
                )
                upd = False
                if site_obj.Latitude is None and lat is not None:
                    site_obj.Latitude = lat; upd = True
                if site_obj.Longitude is None and lon is not None:
                    site_obj.Longitude = lon; upd = True
                if upd:
                    site_obj.save()

                # --- Action Observation unique par site
                obs_action, _ = Actions.objects.get_or_create(
                    ActionTypeCV=act_obs,
                    BeginDateTime=default_dt, EndDateTime=default_dt,
                    ActionDescription=f"Observation site info @ {site_label or site_code}"
                )
                fa, _ = FeatureActions.objects.get_or_create(
                    SamplingFeatureID=sf, ActionID=obs_action
                )

                # --- Variables (mesures & catégorielles)
                for col, raw in row.items():
                    if col in self.ID_COLS or col.startswith("Unit_"):
                        continue
                    if raw is None or str(raw).strip() in {"", "NA"}:
                        continue

                    value_str = str(raw).strip()
                    is_measure = col in self.MEASUREMENT_COLS
                    is_categ = col in self.CATEGORICAL_COLS
                    if not (is_measure or is_categ):
                        # colonne non mappée : ignorer proprement
                        continue

                    # CV_VariableName
                    var_cv = self._get_cv(CV_VariableName, col)
                    if not var_cv:
                        self.stdout.write(self.style.WARNING(f"⚠️ CV_VariableName '{col}' introuvable — variable ignorée"))
                        continue

                    # Variables (code = nom de colonne, unique)
                    var, _ = Variables.objects.get_or_create(
                        VariableCode=col,
                        defaults={"VariableNameCV": var_cv}
                    )

                    if is_measure:
                        # Units (via mapping par défaut; si 'Unit_<col>' existe, il prend la priorité)
                        unit_name = (row.get(f"Unit_{col}") or "").strip() or self.DEFAULT_UNITS.get(col, "unitless")
                        unit = self._get_or_create_units(unit_name)

                        # Results -> Measurement
                        res, _ = Results.objects.get_or_create(
                            FeatureActionID=fa,
                            ResultTypeCV=rt_meas,
                            VariableID=var,
                            UnitsID=unit,
                            defaults={"ResultDateTime": default_dt}
                        )
                        mres, _ = MeasurementResults.objects.get_or_create(ResultID=res)

                        # Valeur numérique
                        val = self._to_float(value_str)
                        if val is None:
                            self.stdout.write(self.style.WARNING(
                                f"⚠️ Valeur non numérique pour '{col}' au {site_code}: '{value_str}' — ignorée"
                            ))
                        else:
                            MeasurementResultValues.objects.get_or_create(
                                ResultID=mres, ValueDateTime=default_dt,
                                defaults={"DataValue": val, "hasCategorical": False}
                            )
                            self.stdout.write(self.style.SUCCESS(f"✅ {col} (meas) → {site_code} = {val} {unit.UnitsName}"))

                    else:
                        # Results -> Categorical (sans unité)
                        res, _ = Results.objects.get_or_create(
                            FeatureActionID=fa,
                            ResultTypeCV=rt_cat,
                            VariableID=var,
                            UnitsID=None,
                            defaults={"ResultDateTime": default_dt}
                        )
                        cres, _ = CategoricalResults.objects.get_or_create(ResultID=res)

                        # ✅ si valeur contrôlée → DataValueCV ; sinon → DataValue (texte)
                        cv_val = self._get_cv(CV_CategoricalValue, value_str)
                        if cv_val:
                            CategoricalResultValues.objects.get_or_create(
                                ResultID=cres, ValueDateTime=default_dt,
                                defaults={"DataValueCV": cv_val, "hasMeasurement": False}
                            )
                            self.stdout.write(self.style.SUCCESS(
                                f"✅ {col} (cat) → {site_code} = CV:{cv_val.Name}"
                            ))
                        else:
                            CategoricalResultValues.objects.get_or_create(
                                ResultID=cres, ValueDateTime=default_dt,
                                defaults={"DataValue": value_str, "hasMeasurement": False}
                            )
                            self.stdout.write(self.style.SUCCESS(
                                f"✅ {col} (cat) → {site_code} = '{value_str}' (non contrôlée)"
                            ))

    # ---------------- helpers ----------------

    def _get_cv(self, Model, name):
        """Retourne Model où Name = name (case-insensitive)."""
        name = (name or "").strip()
        if not name:
            return None
        return Model.objects.filter(Name__iexact=name).first()

    def _ensure_cv(self, Model, name, **defaults):
        obj = self._get_cv(Model, name)
        if obj:
            return obj
        # Création minimale si manquant
        obj, _ = Model.objects.get_or_create(Name=name, defaults={"Term": name, **defaults})
        return obj

    def _get_or_create_units(self, units_name):
        """Assure l'existence du couple CV_Units + Units miroir."""
        cv = self._get_cv(CV_Units, units_name)
        if not cv:
            # crée un CV_Units minimal si absent
            cv, _ = CV_Units.objects.get_or_create(
                Name=units_name, defaults={"Term": units_name, "Definition": "", "Category": "", "SourceVocabularyURI": ""}
            )
        unit, _ = Units.objects.get_or_create(
            UnitsName=units_name,
            UnitsTypeCV=cv
        )
        return unit

    def _to_float(self, s):
        try:
            if s is None:
                return None
            s = str(s).strip().replace(",", ".")
            return float(s) if s != "" else None
        except ValueError:
            return None
