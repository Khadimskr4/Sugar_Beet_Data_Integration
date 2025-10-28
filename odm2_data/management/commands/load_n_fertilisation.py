# odm2_data/management/commands/load_n_fertilisation.py

import os, csv
from datetime import datetime
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from odm2_data.models import (
    # Core + CV (version PascalCase, comme ton modèle)
    SamplingFeatures, Variables, Units, Results,
    MeasurementResults, MeasurementResultValues,
    Actions, FeatureActions,
    CV_ActionType, CV_AnnotationType, CV_VariableName, CV_Units, CV_ResultsType,
    # Annotations (pink) – sans texte dans ton modèle
    SamplingFeatureAnnotations,
)

class Command(BaseCommand):
    help = "Charger 6_N_fertilisation.csv (Action=Fertilization, amount_N mesuré, annotation N-fertiliser)"

    def add_arguments(self, parser):
        parser.add_argument("--path", default=os.path.join("data", "6_N_fertilisation.csv"))
        parser.add_argument("--encoding", default="latin1")
        parser.add_argument("--delimiter", default=";")

    @transaction.atomic
    def handle(self, *args, **opts):
        path = opts["path"]; enc = opts["encoding"]; delim = opts["delimiter"]

        if not os.path.exists(path):
            self.stderr.write(f"❌ Fichier introuvable: {path}")
            return

        # ===== CV requis (ne créent que si nécessaire quand c’est logique) =====
        rt_meas = self._require_cv(CV_ResultsType, "Measurement")
        if not rt_meas:
            self.stderr.write("❌ CV_ResultsType 'Measurement' manquant. Lance d'abord `load_cv`.")
            return

        fert_type = self._ensure_cv(CV_ActionType, "Fertilization")
        annot_type = self._ensure_cv(CV_AnnotationType, "N-fertiliser")

        # Variable amount_N (déjà dans tes CV normalement)
        amount_cv = self._ensure_cv(CV_VariableName, "amount_N")

        # Unités: priorité "kg N/ha", fallback "kg/ha"
        default_unit = self._resolve_unit(["kg N/ha", "kg/ha"])
        if not default_unit:
            self.stderr.write("❌ Aucune unité disponible parmi ['kg N/ha','kg/ha'] dans CV_Units. Lance d'abord `load_cv`.")
            return

        with open(path, encoding=enc, newline="") as f:
            reader = csv.DictReader(f, delimiter=delim)

            required = {"site_no", "site", "date"}
            missing = required - set(reader.fieldnames or [])
            if missing:
                self.stderr.write(f"❌ En-têtes manquantes: {missing}")
                return

            has_unit_col = "Unit_amount_N" in reader.fieldnames

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

                    # ---- date → timezone-aware
                    dt = self._parse_date((row.get("date") or "").strip())
                    if not dt:
                        self.stdout.write(self.style.WARNING(f"⚠️ Date invalide pour {site_code} → ligne ignorée"))
                        continue
                    if timezone.is_naive(dt):
                        dt = timezone.make_aware(dt)

                    # ---- Action Fertilization (clé: type + begin + end + desc)
                    desc = f"Fertilization at {site_name or site_code} on {dt.date().isoformat()}"
                    action, _ = Actions.objects.get_or_create(
                        ActionTypeCV=fert_type,
                        BeginDateTime=dt,
                        EndDateTime=dt,
                        ActionDescription=desc
                    )

                    # ---- FeatureAction (idempotent)
                    fa, _ = FeatureActions.objects.get_or_create(
                        SamplingFeatureID=site,
                        ActionID=action
                    )

                    # ---- amount_N (measurement)
                    raw = (row.get("amount_N") or "").strip()
                    if raw and raw.upper() != "NA":
                        try:
                            val = float(str(raw).replace(",", "."))
                        except ValueError:
                            self.stdout.write(self.style.WARNING(
                                f"⚠️ Valeur non numérique '{raw}' pour amount_N ({site_code}) → ignorée"
                            ))
                        else:
                            unit_obj = default_unit
                            if has_unit_col:
                                explicit = (row.get("Unit_amount_N") or "").strip()
                                if explicit:
                                    maybe = self._resolve_unit([explicit])
                                    if maybe:
                                        unit_obj = maybe
                                    else:
                                        self.stdout.write(self.style.WARNING(
                                            f"⚠️ Unité '{explicit}' inconnue → fallback '{default_unit.UnitsName}'"
                                        ))

                            # Variable (globale par code)
                            variable, _ = Variables.objects.get_or_create(
                                VariableCode="amount_N",
                                defaults={"VariableNameCV": amount_cv}
                            )

                            # Result → Measurement
                            result, _ = Results.objects.get_or_create(
                                FeatureActionID=fa,
                                ResultTypeCV=rt_meas,
                                VariableID=variable,
                                UnitsID=unit_obj,
                                defaults={"ResultDateTime": dt}
                            )
                            mres, _ = MeasurementResults.objects.get_or_create(ResultID=result)

                            # Valeur (booléen hasCategorical=FALSE)
                            MeasurementResultValues.objects.get_or_create(
                                ResultID=mres,
                                ValueDateTime=dt,
                                defaults={"DataValue": val, "hasCategorical": False}
                            )

                    # ---- Annotation ‘N-fertiliser’ (sans texte dans ton modèle)
                    fert_name = (row.get("N-fertiliser") or "").strip()
                    if fert_name and fert_name.upper() != "NA":
                        # On enregistre seulement le type + la date, conformément à SamplingFeatureAnnotations
                        SamplingFeatureAnnotations.objects.get_or_create(
                            SamplingFeatureID=site,
                            AnnotationTypeCV=annot_type,
                            AnnotationDateTime=dt
                        )

                    self.stdout.write(self.style.SUCCESS(
                        f"✅ {site_code} — fertilisation du {dt.date().isoformat()} importée"
                    ))

                except Exception as e:
                    self.stderr.write(f"❌ Erreur ligne {reader.line_num} ({row.get('site_no','?')}): {e}")
                    raise  # rollback

    # =============== helpers ===============

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
        """Renvoie (ou crée) l’entrée CV avec Term=Name=name si absente."""
        if not name:
            return None
        obj = Model.objects.filter(Name__iexact=name).first()
        if obj:
            return obj
        return Model.objects.create(Term=name, Name=name)

    def _require_cv(self, Model, name: str):
        """Renvoie l’entrée CV si elle existe, sinon None (pas de création silencieuse)."""
        return Model.objects.filter(Name__iexact=name).first()

    def _resolve_unit(self, candidates: list):
        """
        À partir d'une liste de noms candidats (ordre de préférence),
        retourne une instance Units (miroir) basée sur CV_Units.
        """
        for nm in candidates:
            if not nm:
                continue
            cvu = CV_Units.objects.filter(Name__iexact=nm).first()
            if cvu:
                unit, _ = Units.objects.get_or_create(UnitsName=cvu.Name, UnitsTypeCV=cvu)
                return unit
        return None
