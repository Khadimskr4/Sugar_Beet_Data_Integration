from django.core.management.base import BaseCommand
from django.db import transaction
from odm2_data.models import (
    CV_ActionType, CV_SamplingFeatureType, CV_SiteType, CV_Units,
    CV_VariableName, CV_AnnotationType, CV_RelationshipType, Units,
    CV_CategoricalValue, CV_ResultsType
)

class Command(BaseCommand):
    help = "Charger tous les vocabulaires contrôlés (CV_*) harmonisés (Term, Name, Definition, Category, SourceVocabularyURI) + miroir Units."

    # -------- Helpers --------
    def _get_or_create_cv(self, Model, name, defaults):
        # normalise les chaînes
        clean = {k: (v.strip() if isinstance(v, str) else v) for k, v in (defaults or {}).items()}
        obj, created = Model.objects.get_or_create(Name=name.strip(), defaults=clean)
        return obj, created

    @transaction.atomic
    def handle(self, *args, **kwargs):
        created = {"act":0, "sft":0, "st":0, "cvu":0, "u":0, "vn":0, "ann":0, "rel":0, "cat":0, "rt":0}

        # ----------------------------
        # CV_ResultsType
        # ----------------------------
        # (ajoute au besoin d'autres types : SectionResult, TransectResult, etc.)
        results_types = [
            ("Measurement", "Measurement", "Scalar measured values.", "ResultType", ""),
            ("TimeSeries", "TimeSeries", "Time-indexed sequence of numeric values.", "ResultType", ""),
            ("Categorical", "Categorical", "Values drawn from a controlled list.", "ResultType", ""),
        ]
        for term, name, definition, category, uri in results_types:
            _, was_created = self._get_or_create_cv(CV_ResultsType, name, {
                "Term": term, "Definition": definition, "Category": category, "SourceVocabularyURI": uri
            })
            created["rt"] += int(was_created)

        # ----------------------------
        # CV_ActionType
        # ----------------------------
        action_types = [
            ("Tillage", "Tillage",
             "Physical manipulation of soil to improve conditions for seedling establishment and crop growth.",
             "Agronomy", "https://agrovoc.fao.org/browse/agrovoc/en/page/c_7771"),
            ("Sowing", "Sowing",
             "The process of planting.", "Agronomy",
             "https://agrovoc.fao.org/browse/agrovoc/en/page/c_7268"),
            ("Fertilization", "Fertilization",
             "The application of fertilizers to soil or plants.",
             "Agronomy", "https://agrovoc.fao.org/browse/agrovoc/en/page/c_2863"),
            ("Irrigation", "Irrigation",
             "Controlled application of water to meet crop water requirements.",
             "Agronomy", "https://agrovoc.fao.org/browse/agrovoc/en/page/c_3954"),
            ("Observation", "Observation",
             "Recognizing and noting a fact or occurrence.",
             "Research", "https://agrovoc.fao.org/browse/agrovoc/en/page/c_fc54b25b"),
            ("Weather_recording", "Weather recording",
             "Recording of weather observations.", "Climatology", ""),
            ("Trial", "Trial",
             "Experiment or test conducted to evaluate something.", "Research", ""),
            ("Measure", "Measure",
             "Directly observed numeric value.", "Research",
             "https://agrovoc.fao.org/browse/agrovoc/en/page/c_330493"),
        ]
        for term, name, definition, category, uri in action_types:
            _, was_created = self._get_or_create_cv(CV_ActionType, name, {
                "Term": term, "Definition": definition, "Category": category, "SourceVocabularyURI": uri
            })
            created["act"] += int(was_created)

        # ----------------------------
        # CV_SamplingFeatureType
        # ----------------------------
        sft_values = [
            ("site", "site",
             "A place where something is located or has been located.",
             "Geography", "https://agrovoc.fao.org/browse/agrovoc/en/page/c_331000"),
        ]
        for term, name, definition, category, uri in sft_values:
            _, was_created = self._get_or_create_cv(CV_SamplingFeatureType, name, {
                "Term": term, "Definition": definition, "Category": category, "SourceVocabularyURI": uri
            })
            created["sft"] += int(was_created)

        # ----------------------------
        # CV_SiteType
        # ----------------------------
        site_types = [
            ("site", "site",
             "A location where experiments or tests are conducted.",
             "Research", "https://agrovoc.fao.org/browse/agrovoc/en/page/c_33990"),
            ("rep", "rep", "Experimental replicate.", "Research", ""),
        ]
        for term, name, definition, category, uri in site_types:
            _, was_created = self._get_or_create_cv(CV_SiteType, name, {
                "Term": term, "Definition": definition, "Category": category, "SourceVocabularyURI": uri
            })
            created["st"] += int(was_created)

        # ----------------------------
        # CV_Units (+ miroir Units)
        # ----------------------------
        units = [
            ("°C", "°C", "Degree Celsius (temperature).", "Temperature", "https://qudt.org/vocab/unit/DEG_C"),
            ("mm", "mm", "Millimetre (length).", "Length", "https://qudt.org/vocab/unit/MilliM"),
            ("kg/ha", "kg/ha", "Kilogram per hectare.", "MassPerArea", "https://qudt.org/vocab/unit/KiloGM-PER-HA"),
            ("seeds/ha", "seeds/ha", "Seeds per hectare.", "CountPerArea", ""),
            ("t/ha", "t/ha", "Tonne per hectare.", "MassPerArea", ""),
            ("g/m²", "g/m²", "Gram per square metre.", "MassPerArea", ""),
            ("%", "%", "Percent.", "Dimensionless", ""),
            ("W/m²", "W/m²", "Watt per square metre.", "PowerPerArea", ""),
            ("g/kg", "g/kg", "Gram per kilogram.", "MassFraction", ""),
            ("unitless", "unitless", "Dimensionless unit.", "Dimensionless", ""),
            ("kg/m²", "kg/m²", "Kilogram per square metre.", "MassPerArea", ""),
            ("cm", "cm", "Centimetre.", "Length", ""),
            ("kg N/ha", "kg N/ha", "Kilogram of nitrogen per hectare.", "MassPerArea", ""),
            ("mmol/kg", "mmol/kg", "Millimole per kilogram.", "AmountPerMass", ""),
            ("MJ/m²", "MJ/m²", "Megajoule per square metre.", "EnergyPerArea", ""),
        ]
        for term, name, definition, category, uri in units:
            cvu, was_created = self._get_or_create_cv(CV_Units, name, {
                "Term": term, "Definition": definition, "Category": category, "SourceVocabularyURI": uri
            })
            created["cvu"] += int(was_created)

            # miroir Units : UnitsName = Name, UnitsTypeCV -> FK vers ce CV_Units
            _, u_created = Units.objects.get_or_create(
                UnitsName=name,
                UnitsTypeCV=cvu
            )
            created["u"] += int(u_created)

        # ----------------------------
        # CV_VariableName
        # ----------------------------
        variables = [
            ("annual_mean_temperature", "annual_mean_temperature", "Average temperature over a year.", "Climatology", ""),
            ("annual_rainfall", "annual_rainfall", "Total precipitation over a year.", "Climatology", ""),
            ("Ackerzahl", "Ackerzahl", "", "", ""),
            ("field_capacity", "field_capacity", "Soil water retained after drainage.", "SoilScience", "https://agrovoc.fao.org/browse/agrovoc/en/page/c_32445"),
            ("available_water_capacity", "available_water_capacity", "Capacity of soil to retain water available for plants.", "SoilScience", ""),
            ("availabe_water_root_zone", "availabe_water_root_zone", "", "", ""),
            ("soil_type", "soil_type", "Classification of soils based on characteristics.", "SoilScience", "https://agrovoc.fao.org/browse/agrovoc/en/page/c_7204"),
            ("soil_texture", "soil_texture", "Relative proportions of sand, silt, and clay.", "SoilScience", ""),
            ("soil_texture_class", "soil_texture_class", "", "", ""),
            ("soil_mineral_N", "soil_mineral_N", "Inorganic nitrogen compounds in soil.", "SoilScience", ""),
            ("depth", "depth", "Vertical distance from a reference point.", "General", "https://agrovoc.fao.org/browse/agrovoc/en/page/c_2190"),
            ("pH", "pH", "Measure of acidity or alkalinity.", "Chemistry", ""),
            ("irrigation", "irrigation", "Application of water to soil for plant growth.", "Agronomy", ""),
            ("measure_implemented", "measure_implemented", "", "", ""),
            ("sowing_density", "sowing_density", "Number of seeds per unit area.", "Agronomy", "https://agrovoc.fao.org/browse/agrovoc/en/page/c_7272"),
            ("rate_emergence", "rate_emergence", "Speed at which plants emerge.", "Agronomy", ""),
            ("beet_rows", "beet_rows", "", "", ""),
            ("variety", "variety", "Cultivar/variety identifier.", "Biology", ""),
            ("amount_N", "amount_N", "Quantity of nitrogen applied.", "Agriculture", ""),
            ("irrigation_amount", "irrigation_amount", "Quantity of water applied through irrigation.", "Agronomy", ""),
            ("dps", "dps", "Days past sowing.", "Agronomy", ""),
            ("soil_moisture_30", "soil_moisture_30", "Soil water content at 30 cm.", "SoilScience", ""),
            ("soil_moisture_60", "soil_moisture_60", "Soil water content at 60 cm.", "SoilScience", ""),
            ("soil_moisture_90", "soil_moisture_90", "Soil water content at 90 cm.", "SoilScience", ""),
            ("PAW_30", "PAW_30", "Plant available water at 30 cm.", "SoilScience", ""),
            ("PAW_60", "PAW_60", "Plant available water at 60 cm.", "SoilScience", ""),
            ("PAW_90", "PAW_90", "Plant available water at 90 cm.", "SoilScience", ""),
            ("root_yield", "root_yield", "Mass of roots per area.", "Agriculture", ""),
            ("root_dry_matter", "root_dry_matter", "Dry weight of root material.", "Agriculture", ""),
            ("leaf_yield", "leaf_yield", "Mass of leaves per area.", "Agriculture", ""),
            ("leaf_dry_matter", "leaf_dry_matter", "Dry weight of leaf material.", "Agriculture", ""),
            ("LAI", "LAI", "Leaf Area Index.", "Agriculture", "https://agrovoc.fao.org/browse/agrovoc/en/page/c_35196"),
            ("n", "n", "Nitrogen element.", "Chemistry", ""),
            ("sugar", "sugar", "Soluble carbohydrates.", "Chemistry", ""),
            ("K", "K", "Potassium element.", "Chemistry", ""),
            ("Na", "Na", "Sodium element.", "Chemistry", ""),
            ("amino_N", "amino_N", "Amino nitrogen compounds.", "Chemistry", ""),
            ("soluble_Nt", "soluble_Nt", "", "Chemistry", ""),
            ("NO3", "NO3", "Nitrate ion.", "Chemistry", ""),
            ("betaine", "betaine", "Amino acid derivative.", "Chemistry", ""),
            ("invert_sugar", "invert_sugar", "Mixture of glucose and fructose.", "Chemistry", ""),
            ("marc", "marc", "Residue after extraction/pressing.", "Agriculture", ""),
            ("min_temp", "min_temp", "Minimum temperature.", "Climatology", ""),
            ("max_temp", "max_temp", "Maximum temperature.", "Climatology", ""),
            ("av_temp", "av_temp", "Average temperature.", "Climatology", ""),
            ("precipitation", "precipitation", "Precipitation.", "Climatology", ""),
            ("glob_radiation", "glob_radiation", "Global solar radiation.", "Climatology", ""),
            ("ET_grass", "ET_grass", "Reference grass evapotranspiration.", "Climatology", ""),
        ]
        for term, name, definition, category, uri in variables:
            _, was_created = self._get_or_create_cv(CV_VariableName, name, {
                "Term": term, "Definition": definition, "Category": category, "SourceVocabularyURI": uri
            })
            created["vn"] += int(was_created)

        # ----------------------------
        # CV_AnnotationType
        # ----------------------------
        annotation_types = [
            ("data_source", "data_source", "Data source reference.", "Metadata", ""),
            ("remark", "remark", "Free-text remark.", "Metadata", ""),
            ("intercrop", "intercrop", "Growing two or more crops simultaneously.", "Agronomy", ""),
            ("precrop", "precrop", "Preceding crop.", "Agronomy", ""),
            ("N_fertiliser", "N-fertiliser", "Nitrogen-containing fertilizers.", "Agronomy", ""),
            ("temperature_source", "temperature_source", "", "Climatology", ""),
            ("precipitation_source", "precipitation_source", "", "Climatology", ""),
            ("global_radiation_source", "global_radiation_source", "", "Climatology", ""),
            ("14h_air_temperature_humidity_source", "14h_air_temperature_humidity_source", "", "Climatology", ""),
        ]
        for term, name, definition, category, uri in annotation_types:
            _, was_created = self._get_or_create_cv(CV_AnnotationType, name, {
                "Term": term, "Definition": definition, "Category": category, "SourceVocabularyURI": uri
            })
            created["ann"] += int(was_created)

        # ----------------------------
        # CV_RelationshipType
        # ----------------------------
        for term, name, definition, category, uri in [
            ("isParent", "isParent", "Parent relation.", "Graph", ""),
            ("isPartOf", "isPartOf", "Part-of relation.", "Graph", ""),
        ]:
            _, was_created = self._get_or_create_cv(CV_RelationshipType, name, {
                "Term": term, "Definition": definition, "Category": category, "SourceVocabularyURI": uri
            })
            created["rel"] += int(was_created)

        # ----------------------------
        # CV_CategoricalValue
        # ----------------------------
        categorical_values = [
            ("fluvisol", "fluvisol", "A soil type formed from river deposits.", "SoilType", ""),
            ("cambisol", "cambisol", "Beginning soil formation.", "SoilType", ""),
            ("chernozem", "chernozem", "Black soil rich in humus.", "SoilType", ""),
            ("luvisol", "luvisol", "Clay accumulation.", "SoilType", ""),
            ("clayey_loam", "clayey loam", "Texture with high clay content.", "SoilTexture", ""),
            ("sandy_loam", "sandy loam", "Texture with high sand content.", "SoilTexture", ""),
            ("loamy_fine_sand", "loamy fine sand", "", "SoilTexture", ""),
            ("silty_loam", "silty loam", "Texture with high silt content.", "SoilTexture", ""),
            ("Lts", "Lts", "", "SoilTextureClass", ""),
            ("Sl3", "Sl3", "", "SoilTextureClass", ""),
            ("mSfS", "mSfS", "", "SoilTextureClass", ""),
            ("Ut2-3", "Ut2-3", "", "SoilTextureClass", ""),
            ("Ut3", "Ut3", "", "SoilTextureClass", ""),
            ("Ut2", "Ut2", "", "SoilTextureClass", ""),
        ]
        for term, name, definition, category, uri in categorical_values:
            _, was_created = self._get_or_create_cv(CV_CategoricalValue, name, {
                "Term": term, "Definition": definition, "Category": category, "SourceVocabularyURI": uri
            })
            created["cat"] += int(was_created)

        self.stdout.write(self.style.SUCCESS(
            "✅ Chargement CV_* harmonisé terminé.\n"
            f"    ResultsType +{created['rt']}, ActionType +{created['act']}, SamplingFeatureType +{created['sft']}, "
            f"SiteType +{created['st']}, CV_Units +{created['cvu']}, Units +{created['u']}, "
            f"VariableName +{created['vn']}, AnnotationType +{created['ann']}, "
            f"RelationshipType +{created['rel']}, CategoricalValue +{created['cat']}"
        ))
