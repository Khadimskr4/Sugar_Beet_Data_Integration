from django.db import models
from django.db.models import Q, F
import uuid

# ============================
# Controlled Vocabularies (CV)
# ============================

class CV_ResultsType(models.Model):
    Term = models.CharField(max_length=255, unique=True)
    Name = models.CharField(max_length=255, primary_key=True)
    Definition = models.TextField(null=True, blank=True)
    Category = models.CharField(max_length=255, null=True, blank=True)
    SourceVocabularyURI = models.CharField(max_length=500, null=True, blank=True)

    class Meta:
        db_table = "CV_ResultsType"

    def __str__(self):
        return self.Name


class CV_VariableName(models.Model):
    Term = models.CharField(max_length=255, unique=True)
    Name = models.CharField(max_length=255, primary_key=True)
    Definition = models.TextField(null=True, blank=True)
    Category = models.CharField(max_length=255, null=True, blank=True)
    SourceVocabularyURI = models.CharField(max_length=500, null=True, blank=True)

    class Meta:
        db_table = "CV_VariableName"

    def __str__(self):
        return self.Name


class CV_Units(models.Model):
    Term = models.CharField(max_length=255, unique=True)
    Name = models.CharField(max_length=255, primary_key=True)
    Definition = models.TextField(null=True, blank=True)
    Category = models.CharField(max_length=255, null=True, blank=True)
    SourceVocabularyURI = models.CharField(max_length=500, null=True, blank=True)

    class Meta:
        db_table = "CV_Units"

    def __str__(self):
        return self.Name


class CV_SiteType(models.Model):
    Term = models.CharField(max_length=255, unique=True)
    Name = models.CharField(max_length=255, primary_key=True)
    Definition = models.TextField(null=True, blank=True)
    Category = models.CharField(max_length=255, null=True, blank=True)
    SourceVocabularyURI = models.CharField(max_length=500, null=True, blank=True)

    class Meta:
        db_table = "CV_SiteType"

    def __str__(self):
        return self.Name


class CV_RelationshipType(models.Model):
    Term = models.CharField(max_length=255, unique=True)
    Name = models.CharField(max_length=255, primary_key=True)
    Definition = models.TextField(null=True, blank=True)
    Category = models.CharField(max_length=255, null=True, blank=True)
    SourceVocabularyURI = models.CharField(max_length=500, null=True, blank=True)

    class Meta:
        db_table = "CV_RelationshipType"

    def __str__(self):
        return self.Name


class CV_SamplingFeatureType(models.Model):
    Term = models.CharField(max_length=255, unique=True)
    Name = models.CharField(max_length=255, primary_key=True)
    Definition = models.TextField(null=True, blank=True)
    Category = models.CharField(max_length=255, null=True, blank=True)
    SourceVocabularyURI = models.CharField(max_length=500, null=True, blank=True)

    class Meta:
        db_table = "CV_SamplingFeatureType"

    def __str__(self):
        return self.Name


class CV_ActionType(models.Model):
    Term = models.CharField(max_length=255, unique=True)
    Name = models.CharField(max_length=255, primary_key=True)
    Definition = models.TextField(null=True, blank=True)
    Category = models.CharField(max_length=255, null=True, blank=True)
    SourceVocabularyURI = models.CharField(max_length=500, null=True, blank=True)

    class Meta:
        db_table = "CV_ActionType"

    def __str__(self):
        return self.Name


class CV_CategoricalValue(models.Model):
    Term = models.CharField(max_length=255, unique=True)
    Name = models.CharField(max_length=255, primary_key=True)
    Definition = models.TextField(null=True, blank=True)
    Category = models.CharField(max_length=255, null=True, blank=True)
    SourceVocabularyURI = models.CharField(max_length=500, null=True, blank=True)

    class Meta:
        db_table = "CV_CategoricalValue"

    def __str__(self):
        return self.Name


class CV_AnnotationType(models.Model):
    Term = models.CharField(max_length=255, unique=True)
    Name = models.CharField(max_length=255, primary_key=True)
    Definition = models.TextField(null=True, blank=True)
    Category = models.CharField(max_length=255, null=True, blank=True)
    SourceVocabularyURI = models.CharField(max_length=500, null=True, blank=True)

    class Meta:
        db_table = "CV_AnnotationType"

    def __str__(self):
        return self.Name


# ==============
# Core Entities
# ==============

class Variables(models.Model):
    VariableID = models.AutoField(primary_key=True)
    VariableCode = models.CharField(max_length=100, unique=True)
    VariableNameCV = models.ForeignKey(
        CV_VariableName, to_field="Name", on_delete=models.CASCADE, db_column="VariableNameCV"
    )

    class Meta:
        db_table = "ODM2_Variables"

    def __str__(self):
        return self.VariableCode


class Units(models.Model):
    UnitsID = models.AutoField(primary_key=True)
    UnitsTypeCV = models.ForeignKey(
        CV_Units, to_field="Name", on_delete=models.CASCADE, db_column="UnitsTypeCV"
    )
    UnitsName = models.CharField(max_length=255)

    class Meta:
        db_table = "ODM2_Units"

    def __str__(self):
        return self.UnitsName


class SamplingFeatures(models.Model):
    SamplingFeatureID = models.AutoField(primary_key=True)
    SamplingFeatureUUID = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    SamplingFeatureTypeCV = models.ForeignKey(
        CV_SamplingFeatureType, to_field="Name", on_delete=models.CASCADE, db_column="SamplingFeatureTypeCV"
    )
    SamplingFeatureCode = models.CharField(max_length=255)
    SamplingFeatureName = models.CharField(max_length=255, null=True, blank=True)
    SamplingFeatureDescription = models.TextField(null=True, blank=True)
    FeatureGeometry = models.TextField(null=True, blank=True)  # WKT/GeoJSON
    Elevation_m = models.FloatField(null=True, blank=True)

    class Meta:
        db_table = "ODM2_SamplingFeatures"
        indexes = [
            models.Index(fields=["SamplingFeatureCode"]),
            models.Index(fields=["SamplingFeatureTypeCV"]),
        ]

    def __str__(self):
        return self.SamplingFeatureCode


class Sites(models.Model):
    SamplingFeatureID = models.OneToOneField(
        SamplingFeatures, on_delete=models.CASCADE, primary_key=True, db_column="SamplingFeatureID"
    )
    SiteTypeCV = models.ForeignKey(
        CV_SiteType, to_field="Name", on_delete=models.CASCADE, db_column="SiteTypeCV"
    )
    Latitude = models.FloatField(null=True, blank=True)
    Longitude = models.FloatField(null=True, blank=True)

    class Meta:
        db_table = "ODM2_Sites"

    def __str__(self):
        return f"Site({self.SamplingFeatureID_id})"


class Actions(models.Model):
    ActionID = models.AutoField(primary_key=True)
    ActionTypeCV = models.ForeignKey(
        CV_ActionType, to_field="Name", on_delete=models.CASCADE, db_column="ActionTypeCV"
    )
    BeginDateTime = models.DateTimeField(null=True, blank=True)
    EndDateTime = models.DateTimeField(null=True, blank=True)
    ActionDescription = models.TextField(null=True, blank=True)

    class Meta:
        db_table = "ODM2_Actions"
        indexes = [models.Index(fields=["ActionTypeCV", "BeginDateTime"])]

    def __str__(self):
        return f"{self.ActionTypeCV_id} @ {self.BeginDateTime}"


class FeatureActions(models.Model):
    FeatureActionID = models.AutoField(primary_key=True)
    SamplingFeatureID = models.ForeignKey(
        SamplingFeatures, on_delete=models.CASCADE, db_column="SamplingFeatureID"
    )
    ActionID = models.ForeignKey(
        Actions, on_delete=models.CASCADE, db_column="ActionID"
    )

    class Meta:
        db_table = "ODM2_FeatureActions"
        unique_together = ("SamplingFeatureID", "ActionID")
        indexes = [
            models.Index(fields=["SamplingFeatureID", "ActionID"]),
        ]

    def __str__(self):
        return f"FA({self.SamplingFeatureID_id}, {self.ActionID_id})"


class Results(models.Model):
    ResultID = models.AutoField(primary_key=True)
    FeatureActionID = models.ForeignKey(
        FeatureActions, on_delete=models.CASCADE, db_column="FeatureActionID"
    )
    ResultTypeCV = models.ForeignKey(
        CV_ResultsType, to_field="Name", on_delete=models.CASCADE, db_column="ResultTypeCV"
    )
    VariableID = models.ForeignKey(
        Variables, on_delete=models.CASCADE, db_column="VariableID"
    )
    UnitsID = models.ForeignKey(
        Units, on_delete=models.CASCADE, null=True, blank=True, db_column="UnitsID"
    )
    ResultDateTime = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "ODM2_Results"
        indexes = [
            models.Index(fields=["FeatureActionID", "VariableID"]),
            models.Index(fields=["ResultTypeCV"]),
        ]

    def __str__(self):
        return f"Result({self.ResultID})"


class RelatedFeatures(models.Model):
    """Relation sujet–type–objet sans SpatialOffsetID.
    Colonnes demandées : RelationID, SamplingFeatureID (sujet), RelationshipTypeCV, RelatedFeatureID (objet).
    """
    RelationID = models.AutoField(primary_key=True)

    # Sujet de la relation (ex.: la réplication "rep")
    SamplingFeatureID = models.ForeignKey(
        SamplingFeatures,
        on_delete=models.CASCADE,
        related_name="relatedfeatures_as_subject",
        db_column="SamplingFeatureID",
    )

    # Type de relation (ex.: isPartOf, derivedFrom, storedIn)
    RelationshipTypeCV = models.ForeignKey(
        CV_RelationshipType,
        to_field="Name",
        on_delete=models.CASCADE,
        db_column="RelationshipTypeCV",
    )

    # Objet/cible de la relation (ex.: le site parent)
    RelatedFeatureID = models.ForeignKey(
        SamplingFeatures,
        on_delete=models.CASCADE,
        related_name="relatedfeatures_as_object",
        db_column="RelatedFeatureID",
    )

    class Meta:
        db_table = "ODM2_RelatedFeatures"
        unique_together = ("SamplingFeatureID", "RelationshipTypeCV", "RelatedFeatureID")
        indexes = [
            models.Index(fields=["SamplingFeatureID", "RelationshipTypeCV"]),
            models.Index(fields=["RelatedFeatureID"]),
        ]
        constraints = [
            models.CheckConstraint(
                check=~Q(SamplingFeatureID=F("RelatedFeatureID")),
                name="ck_relatedfeatures_no_self_loop",
            )
        ]

    def __str__(self):
        return f"{self.SamplingFeatureID_id} -{self.RelationshipTypeCV_id}-> {self.RelatedFeatureID_id}"


class RelatedResults(models.Model):
    RelationID = models.AutoField(primary_key=True)
    ResultID = models.ForeignKey(
        Results, on_delete=models.CASCADE, related_name="as_result", db_column="ResultID"
    )
    RelationshipTypeCV = models.ForeignKey(
        CV_RelationshipType, to_field="Name", on_delete=models.CASCADE, db_column="RelationshipTypeCV"
    )
    RelatedResultID = models.ForeignKey(
        Results, on_delete=models.CASCADE, related_name="as_related", db_column="RelatedResultID"
    )
    VersionCode = models.CharField(max_length=100, null=True, blank=True)
    RelatedResultSequenceNumber = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "ODM2_RelatedResults"
        unique_together = ("ResultID", "RelationshipTypeCV", "RelatedResultID")
        indexes = [
            models.Index(fields=["ResultID", "RelationshipTypeCV"]),
            models.Index(fields=["RelatedResultID"]),
        ]

    def __str__(self):
        return f"{self.ResultID_id} -{self.RelationshipTypeCV_id}-> {self.RelatedResultID_id}"


# =================
# Results subtypes
# =================

class MeasurementResults(models.Model):
    ResultID = models.OneToOneField(
        Results, on_delete=models.CASCADE, primary_key=True, db_column="ResultID"
    )

    class Meta:
        db_table = "ODM2_MeasurementResults"

    def __str__(self):
        return f"Measurement({self.ResultID_id})"


class TimeSeriesResults(models.Model):
    ResultID = models.OneToOneField(
        Results, on_delete=models.CASCADE, primary_key=True, db_column="ResultID"
    )

    class Meta:
        db_table = "ODM2_TimeSeriesResults"

    def __str__(self):
        return f"TimeSeries({self.ResultID_id})"


class CategoricalResults(models.Model):
    ResultID = models.OneToOneField(
        Results, on_delete=models.CASCADE, primary_key=True, db_column="ResultID"
    )

    class Meta:
        db_table = "ODM2_CategoricalResults"

    def __str__(self):
        return f"Categorical({self.ResultID_id})"


# ===========================
# Result Values (yellow box)
# ===========================

class MeasurementResultValues(models.Model):
    ValueID = models.AutoField(primary_key=True)
    ResultID = models.ForeignKey(
        MeasurementResults, on_delete=models.CASCADE, db_column="ResultID", related_name="Values"
    )
    DataValue = models.FloatField()
    ValueDateTime = models.DateTimeField()
    hasCategorical = models.BooleanField(default=False)

    class Meta:
        db_table = "ODM2_MeasurementResultValues"
        indexes = [models.Index(fields=["ValueDateTime"])]

    def __str__(self):
        return f"{self.ValueDateTime} = {self.DataValue}"


class TimeSeriesResultValues(models.Model):
    ValueID = models.AutoField(primary_key=True)
    ResultID = models.ForeignKey(
        TimeSeriesResults, on_delete=models.CASCADE, db_column="ResultID", related_name="Values"
    )
    DataValue = models.FloatField()
    ValueDateTime = models.DateTimeField()

    class Meta:
        db_table = "ODM2_TimeSeriesResultValues"
        indexes = [models.Index(fields=["ValueDateTime"])]

    def __str__(self):
        return f"{self.ValueDateTime} = {self.DataValue}"


class CategoricalResultValues(models.Model):
    ValueID = models.AutoField(primary_key=True)
    ResultID = models.ForeignKey(
        CategoricalResults, on_delete=models.CASCADE, db_column="ResultID", related_name="Values"
    )
    # Deux représentations possibles : texte libre OU vocabulaire contrôlé
    DataValue = models.CharField(max_length=255, null=True, blank=True)
    DataValueCV = models.ForeignKey(
        CV_CategoricalValue,
        to_field="Name",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column="DataValueCV",
    )
    ValueDateTime = models.DateTimeField()
    hasMeasurement = models.BooleanField(default=False)

    class Meta:
        db_table = "ODM2_CategoricalResultValues"
        indexes = [models.Index(fields=["ValueDateTime"])]
        constraints = [
            models.CheckConstraint(
                check=(Q(DataValue__isnull=False) | Q(DataValueCV__isnull=False)),
                name="ck_catval_value_or_cv_not_null",
            )
        ]

    def __str__(self):
        label = self.DataValueCV_id or self.DataValue or "—"
        return f"{self.ValueDateTime} = {label}"


# ======================
# Equipment Extension
# ======================

class Equipments(models.Model):
    EquipmentID = models.AutoField(primary_key=True)
    EquipmentName = models.CharField(max_length=255)
    Description = models.TextField(null=True, blank=True)

    class Meta:
        db_table = "ODM2_Equipments"

    def __str__(self):
        return self.EquipmentName


class EquipmentUsed(models.Model):
    BridgeID = models.AutoField(primary_key=True)
    ActionID = models.ForeignKey(Actions, on_delete=models.CASCADE, db_column="ActionID")
    EquipmentID = models.ForeignKey(Equipments, on_delete=models.CASCADE, db_column="EquipmentID")

    class Meta:
        db_table = "ODM2_EquipmentUsed"
        unique_together = ("ActionID", "EquipmentID")
        indexes = [models.Index(fields=["ActionID", "EquipmentID"]) ]

    def __str__(self):
        return f"Used({self.EquipmentID_id}) in Action({self.ActionID_id})"


# ==============
# Annotation
# ==============

class SamplingFeatureAnnotations(models.Model):
    BridgeID = models.AutoField(primary_key=True)
    SamplingFeatureID = models.ForeignKey(
        SamplingFeatures, on_delete=models.CASCADE, db_column="SamplingFeatureID"
    )
    AnnotationTypeCV = models.ForeignKey(
        CV_AnnotationType, to_field="Name", on_delete=models.CASCADE, db_column="AnnotationTypeCV"
    )
    AnnotationDateTime = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "ODM2_SamplingFeatureAnnotations"
        indexes = [models.Index(fields=["SamplingFeatureID", "AnnotationTypeCV"])]

    def __str__(self):
        return f"Ann({self.SamplingFeatureID_id}, {self.AnnotationTypeCV_id})"
