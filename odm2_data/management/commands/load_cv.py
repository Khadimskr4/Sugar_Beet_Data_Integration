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
            ("mm", "mm", "Millimetre (length).", "Length", "http://qudt.org/vocab/unit#Millimeter; http://his.cuahsi.org/mastercvreg/edit_cv11.aspx?tbl=Units&id=1125579048; http://qwwebservices.usgs.gov/service-domains.html"),
            ("kg/ha", "kg/ha", "Kilogram per hectare.", "MassPerArea", "https://qudt.org/vocab/unit/KiloGM-PER-HA"),
            ("seeds/ha", "seeds/ha", "Seeds per hectare.", "CountPerArea", ""),
            ("t/ha", "t/ha", "Tonne per hectare.", "MassPerArea", "http://environment.data.gov.au/def/unit/TonnesPerHectare"),
            ("g/m²", "g/m²", "Gram per square metre.", "MassPerArea", "http://his.cuahsi.org/mastercvreg/edit_cv11.aspx?tbl=Units&id=1125579048; http://qwwebservices.usgs.gov/service-domains.html"),
            ("%", "%", "Percent.", "Dimensionless", "http://qudt.org/vocab/unit#Percent; http://unitsofmeasure.org/ucum.html#para-29; http://his.cuahsi.org/mastercvreg/edit_cv11.aspx?tbl=Units&id=1125579048; http://www.unidata.ucar.edu/software/udunits/; http://qwwebservices.usgs.gov/service-domains.html"),
            ("W/m²", "W/m²", "Watt per square metre.", "PowerPerArea", "http://qudt.org/vocab/unit#WattPerSquareMeter; http://his.cuahsi.org/mastercvreg/edit_cv11.aspx?tbl=Units&id=1125579048; http://qwwebservices.usgs.gov/service-domains.html"),
            ("g/kg", "g/kg", "Gram per kilogram.", "MassFraction", "http://his.cuahsi.org/mastercvreg/edit_cv11.aspx?tbl=Units&id=1125579048; http://qwwebservices.usgs.gov/service-domains.html"),
            ("unitless", "unitless", "Dimensionless unit.", "Dimensionless", ""),
            ("kg/m²", "kg/m²", "Kilogram per square metre.", "MassPerArea", "http://qudt.org/vocab/unit#KilogramPerSquareMeter; http://his.cuahsi.org/mastercvreg/edit_cv11.aspx?tbl=Units&id=1125579048"),
            ("cm", "cm", "Centimetre.", "Length", "http://qudt.org/vocab/unit#Centimeter"),
            ("kg/ha", "kg/ha", "Kilogram of nitrogen per hectare.", "MassPerArea", "http://his.cuahsi.org/mastercvreg/edit_cv11.aspx?tbl=Units&id=1125579048; http://environment.data.gov.au/def/unit/KilogramsPerHectare"),
            ("mmol/kg", "mmol/kg", "Millimole per kilogram.", "ConcentrationCountPerPmass", "http://his.cuahsi.org/mastercvreg/edit_cv11.aspx?tbl=Units&id=1125579048"),
            ("MJ/m²", "MJ/m²", "Megajoule per square metre.", "EnergyPerArea", "http://his.cuahsi.org/mastercvreg/edit_cv11.aspx?tbl=Units&id=1125579048"),
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
            ("Ackerzahl", "Ackerzahl", "Catalogue of methods for assessing natural soil functions, the archival function of soil, the utilisation function ‘raw material deposit’ in accordance with the Federal Soil Protection Act (BBodSchG), and the sensitivity of soil to erosion and compaction, 2nd revised and expanded edition, March 2007", "SoilScience", "https://www.bgr.bund.de/SiteGlobals/Forms/Suche/Expertensuche/Expertensuche_Formular.html#searchResults"),
            ("field_capacity", "field_capacity", "Soil water retained after drainage.", "SoilScience", "https://agrovoc.fao.org/browse/agrovoc/en/page/c_32445"),
            ("available_water_capacity", "available_water_capacity", "Capacity of soil to retain water available for plants.", "SoilScience", ""),
            ("availabe_water_root_zone", "availabe_water_root_zone", "", "", ""),
            ("soil_type", "soil_type", "Classification of soils based on characteristics.", "SoilScience", "https://agrovoc.fao.org/browse/agrovoc/en/page/c_7204"),
            ("soil_texture", "soil_texture", "The relative proportions of the various sized groups of individual soil grains in a mass of soil. Specifically, it refers to the proportions of clay, silt, and sand below 2 mm in size (fine earth fraction).", "SoilScience", "https://agrovoc.fao.org/browse/agrovoc/en/page/c_7199"),
            ("soil_texture_class", "soil_texture_class", "", "", ""),
            ("soil_mineral_N", "soil_mineral_N", "Inorganic nitrogen compounds in soil.", "SoilScience", ""),
            ("depth", "depth", "Vertical distance from a reference point.", "General", "https://agrovoc.fao.org/browse/agrovoc/en/page/c_2190"),
            ("pH", "pH", "Measure of acidity or alkalinity.", "Chemistry", ""),
            ("irrigation", "irrigation", "Application of water to soil for plant growth.", "Agronomy", ""),
            ("measure_implemented", "measure_implemented", "", "", ""),
            ("sowing_density", "sowing_density", "Number of seeds per unit area.", "Agronomy", "https://agrovoc.fao.org/browse/agrovoc/en/page/c_7272"),
            ("rate_emergence", "rate_emergence", "Speed at which plants emerge.", "Agronomy", ""),
            ("beet_rows", "beet_rows", "", "", ""),
            ("variety", "variety", "variety choice", "Biology", "https://agrovoc.fao.org/browse/agrovoc/en/page/c_36085"),
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
            ("sugar", "sugar", "polarimetric sugar content of root fresh matter", "Chemistry", "https://agrovoc.fao.org/browse/agrovoc/en/page/c_1298"),
            ("K", "K", "Potassium element.", "Chemistry", "https://agrovoc.fao.org/browse/agrovoc/en/page/c_6139"),
            ("Na", "Na", "Sodium element.", "Chemistry", "https://agrovoc.fao.org/browse/agrovoc/en/page/c_7145"),
            ("amino_N", "amino_N", "Amino nitrogen compounds.", "Chemistry", "https://agrovoc.fao.org/browse/agrovoc/en/page/c_8768"),
            ("soluble_Nt", "soluble_Nt", " clear to opalescent liquid to be applied as a solution of the active constituent after dilution in water. The liquid may contain water-insoluble formulants.", "Chemistry", "https://agrovoc.fao.org/browse/agrovoc/en/page/c_8476dd49"),
            ("NO3", "NO3", "Amount of nitrogen as component of nitrate", "Chemistry", "https://agrovoc.fao.org/browse/agrovoc/en/page/c_0e5d9815"),
            ("betaine", "betaine", "Amino acid derivative.", "Chemistry", "https://agrovoc.fao.org/browse/agrovoc/en/page/c_26760"),
            ("invert_sugar", "invert_sugar", "Mixture of glucose and fructose.", "Chemistry", ""),
            ("marc", "marc", "Residue after extraction/pressing.", "Agriculture", ""),
            ("min_temp", "min_temp", "Minimum temperature.", "Climatology", ""),
            ("max_temp", "max_temp", "Maximum temperature.", "Climatology", ""),
            ("av_temp", "av_temp", "Average temperature.", "Climatology", ""),
            ("precipitation", "precipitation", "Any or all of the forms of water, whether liquid (i.e., rain or drizzle) or solid (e.g., snow or hail), that fall from the atmosphere and reach the ground.", "Climatology", "https://agrovoc.fao.org/browse/agrovoc/en/page/c_6161"),
            ("glob_radiation", "glob_radiation", "Global solar radiation.", "Climatology", "https://agrovoc.fao.org/browse/agrovoc/en/page/c_6422"),
            ("ET_grass", "ET_grass", "Process by which water is transferred from the land to the atmosphere by evaporation from the soil and other surfaces and by transpiration from plants.", "Climatology", "https://agrovoc.fao.org/browse/agrovoc/en/page/c_2741"),
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
            ("fluvisol", "fluvisol", "Fluvisols accommodate genetically young soils in fluvial, lacustrine or marine deposits. Despite their name, Fluvisols are not restricted to river sediments (Latin fluvius, river); they also occur in lacustrine and marine deposits. Many Fluvisols correlate with Alluvial soils (Russia), Stratic Rudosols (Australia), Fluvents (United States of America), Auenböden (Germany), Neossolos (Brazil), and Sols minéraux bruts d’apport alluvial ou colluvial or Sols peu évolués non climatiques d’apport alluvial ou colluvial 158 World reference base for soil resources 2014 (France). The position of Fluvisols in the key was changed several times during history of FAO and WRB classification systems. The current 3rd edition of WRB puts them further down and shifts some former Fluvisols to other RSGs, especially to Solonchaks and Gleysols.", "SoilType", "https://agrovoc.fao.org/browse/agrovoc/en/page/c_3000"),
            ("cambisol", "cambisol", "Cambisols combine soils with at least an incipient subsurface soil formation. Transformation of parent material is evident from structure formation and mostly brownish discoloration, increasing clay percentage, and/or carbonate removal. Other soil classification systems refer to many Cambisols as Braunerden and Terrae fuscae (Germany), Sols bruns (France), burozems (Russia) and Tenosols (Australia). The name Cambisols was coined for the Soil Map of the World (FAO–UNESCO, 1971–1981) and later adopted by Brazil (Cambissolos). In the United States of America they were formerly called Brown soils/Brown forest soils and are now named Inceptisols.", "SoilType", "https://agrovoc.fao.org/browse/agrovoc/en/page/c_1224"),
            ("chernozem", "chernozem", "Chernozems accommodate soils with a thick blackish mineral surface layer that is rich in organic matter. The Russian soil scientist V.V. Dokuchaev coined the name Chernozem in 1883 to denote the typical soils of the tall-grass steppes in continental Russia. Many Chernozems correspond to Kalktschernoseme (Germany), Chernosols (France), Eluviated black soils (Canada) and Chernossolos (Brazil). In the United States of America they were formerly called Calcareous black soils and belong now to several Suborders (especially Udolls) of the Mollisols.", "SoilType", "https://agrovoc.fao.org/browse/agrovoc/en/page/c_1533"),
            ("luvisol", "luvisol", "Luvisols have a higher clay content in the subsoil than in the topsoil, as a result of pedogenetic processes (especially clay migration) leading to an argic subsoil horizon. Luvisols have high-activity clays throughout the argic horizon and a high base saturation in the 50–100 cm depth. Many Luvisols are known as Texturally-differentiated soils and part of Metamorphic soils (Russia), Sols lessivés (France), Parabraunerden (Germany), Chromosols (Australia) and Luvissolos (Brazil). In the United States of America, they were formerly named Grey-brown podzolic soils and belong now to the Alfisols with high-activity clays.", "SoilType", "https://agrovoc.fao.org/browse/agrovoc/en/page/c_4470"),
            ("clayey_loam", "clayey loam", "Texture with high clay content.", "SoilTexture", ""),
            ("sandy_loam", "sandy loam", "Texture with high sand content.", "SoilTexture", "https://agrovoc.fao.org/browse/agrovoc/en/page/c_6781"),
            ("loamy_fine_sand", "loamy fine sand", "", "SoilTexture", ""),
            ("silty_loam", "silty loam", "Texture with high silt content.", "SoilTexture", "https://agrovoc.fao.org/browse/agrovoc/en/page/c_7066"),
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
