from django.db import models

# ----------------------------
# Controlled Vocabularies (CV_*)
# ----------------------------

class CV_SamplingFeatureType(models.Model):
    name = models.CharField(primary_key=True, max_length=255)
    definition = models.TextField()

    def __str__(self):
        return self.name

class CV_VariableName(models.Model):
    name = models.CharField(primary_key=True, max_length=255)
    category = models.CharField(max_length=255)
    definition = models.TextField()

    def __str__(self):
        return self.name

class CV_Unit(models.Model):
    name = models.CharField(primary_key=True, max_length=255)
    unit_type = models.CharField(max_length=255)
    definition = models.TextField()

    def __str__(self):
        return self.name

class CV_ActionType(models.Model):
    name = models.CharField(primary_key=True, max_length=255)
    definition = models.TextField()

    def __str__(self):
        return self.name

class CV_AnnotationType(models.Model):
    name = models.CharField(primary_key=True, max_length=255)
    definition = models.TextField()

    def __str__(self):
        return self.name

class CV_RelationshipType(models.Model):
    name = models.CharField(primary_key=True, max_length=255)
    definition = models.TextField()

    def __str__(self):
        return self.name

class CV_CategoricalValue(models.Model):
    term = models.CharField(primary_key=True, max_length=255)
    name = models.CharField(max_length=255)
    definition = models.TextField(null=True, blank=True)
    category = models.CharField(max_length=255, null=True, blank=True)
    provenance = models.CharField(max_length=255, null=True, blank=True)
    provenance_uri = models.URLField(max_length=500, null=True, blank=True)
    note = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.name

# ----------------------------
# Core Entities
# ----------------------------

class SamplingFeature(models.Model):
    sampling_feature_id = models.AutoField(primary_key=True)
    sampling_feature_code = models.CharField(max_length=255, unique=True)
    sampling_feature_name = models.CharField(max_length=255, null=True, blank=True)
    sampling_feature_type = models.ForeignKey(CV_SamplingFeatureType, on_delete=models.CASCADE)

    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    elevation_m = models.FloatField(null=True, blank=True)
    site_description = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.sampling_feature_code

class RelatedFeature(models.Model):
    related_feature_id = models.AutoField(primary_key=True)
    subject_feature = models.ForeignKey(SamplingFeature, on_delete=models.CASCADE, related_name='related_subjects')
    relationship_type = models.ForeignKey(CV_RelationshipType, on_delete=models.CASCADE)
    object_feature = models.ForeignKey(SamplingFeature, on_delete=models.CASCADE, related_name='related_objects')
    annotation = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"{self.subject_feature} {self.relationship_type.name} {self.object_feature}"

class Unit(models.Model):
    unit_id = models.AutoField(primary_key=True)
    unit_name = models.ForeignKey(CV_Unit, on_delete=models.CASCADE)

    def __str__(self):
        return str(self.unit_name)

class Variable(models.Model):
    variable_id = models.AutoField(primary_key=True)
    variable_code = models.CharField(max_length=50, unique=True)
    variable_type = models.CharField(max_length=255)
    variable_name = models.ForeignKey(CV_VariableName, on_delete=models.CASCADE)

    def __str__(self):
        return self.variable_code

class Action(models.Model):
    action_id = models.AutoField(primary_key=True)
    action_type = models.ForeignKey(CV_ActionType, on_delete=models.CASCADE)
    begin_datetime = models.DateTimeField(null=True, blank=True)
    end_datetime = models.DateTimeField(null=True, blank=True)
    action_description = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"{self.action_type.name} - {self.begin_datetime}"

class FeatureAction(models.Model):
    feature_action_id = models.AutoField(primary_key=True)
    sampling_feature = models.ForeignKey(SamplingFeature, on_delete=models.CASCADE)
    action = models.ForeignKey(Action, on_delete=models.CASCADE)
    feature_action_type = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.feature_action_type} - {self.sampling_feature} - {self.action}"

class Result(models.Model):
    result_id = models.AutoField(primary_key=True)
    result_type = models.CharField(max_length=255)
    variable = models.ForeignKey(Variable, on_delete=models.CASCADE)
    units = models.ForeignKey(Unit, on_delete=models.CASCADE, null=True, blank=True)
    feature_action = models.ForeignKey(FeatureAction, on_delete=models.CASCADE)
    time_aggregation_interval = models.FloatField(null=True, blank=True)

    def __str__(self):
        return f"{self.result_type} - {self.variable}"

# ----------------------------
# Results
# ----------------------------

class MeasurementResult(models.Model):
    result = models.OneToOneField(Result, on_delete=models.CASCADE, primary_key=True)

    result_datetime = models.DateTimeField(null=True, blank=True)
    value = models.FloatField(null=True, blank=True)
    x_location = models.FloatField(null=True, blank=True)
    x_location_units = models.ForeignKey(Unit, on_delete=models.SET_NULL, null=True, blank=True, related_name='mr_x_units')
    y_location = models.FloatField(null=True, blank=True)
    y_location_units = models.ForeignKey(Unit, on_delete=models.SET_NULL, null=True, blank=True, related_name='mr_y_units')
    z_location = models.FloatField(null=True, blank=True)
    z_location_units = models.ForeignKey(Unit, on_delete=models.SET_NULL, null=True, blank=True, related_name='mr_z_units')

    censor_code_cv = models.CharField(max_length=255, null=True, blank=True)
    quality_code_cv = models.CharField(max_length=255, null=True, blank=True)
    aggregation_statistic_cv = models.CharField(max_length=255, null=True, blank=True)

    time_aggregation_interval = models.FloatField(null=True, blank=True)
    time_aggregation_interval_units = models.ForeignKey(Unit, on_delete=models.SET_NULL, null=True, blank=True, related_name='mr_ta_units')

class MeasurementResultValue(models.Model):
    measurement_result = models.ForeignKey(MeasurementResult, on_delete=models.CASCADE, related_name='values')
    result_datetime = models.DateTimeField()
    value = models.FloatField()
    censor_code = models.CharField(max_length=255, null=True, blank=True)
    quality_code = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['result_datetime']),
        ]

    def __str__(self):
        return f"{self.result_datetime} - {self.value}"

class CategoricalResult(models.Model):
    result = models.OneToOneField(Result, on_delete=models.CASCADE, primary_key=True)

    x_location = models.FloatField(null=True, blank=True)
    x_location_units = models.ForeignKey(Unit, on_delete=models.SET_NULL, null=True, blank=True, related_name='cr_x_units')
    y_location = models.FloatField(null=True, blank=True)
    y_location_units = models.ForeignKey(Unit, on_delete=models.SET_NULL, null=True, blank=True, related_name='cr_y_units')
    z_location = models.FloatField(null=True, blank=True)
    z_location_units = models.ForeignKey(Unit, on_delete=models.SET_NULL, null=True, blank=True, related_name='cr_z_units')

    quality_code_cv = models.CharField(max_length=255, null=True, blank=True)
    aggregation_statistic_cv = models.CharField(max_length=255, null=True, blank=True)

    time_aggregation_interval = models.FloatField(null=True, blank=True)
    time_aggregation_interval_units = models.ForeignKey(Unit, on_delete=models.SET_NULL, null=True, blank=True, related_name='cr_ta_units')

class CategoricalResultValue(models.Model):
    categorical_result = models.ForeignKey(CategoricalResult, on_delete=models.CASCADE, related_name='values')
    value_datetime = models.DateTimeField()
    category = models.ForeignKey(CV_CategoricalValue, on_delete=models.SET_NULL, null=True, blank=True)
    value_text = models.TextField(null=True, blank=True)
    quality_code = models.CharField(max_length=255, null=True, blank=True)
    notes = models.TextField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['value_datetime']),
        ]

    def __str__(self):
        return f"{self.value_datetime} - {self.category or self.value_text}"

# ----------------------------
# Annotation
# ----------------------------

class Annotation(models.Model):
    annotation_id = models.AutoField(primary_key=True)
    annotation_type = models.ForeignKey(CV_AnnotationType, on_delete=models.CASCADE)
    related_feature = models.ForeignKey(SamplingFeature, on_delete=models.CASCADE)
    annotation_text = models.TextField()
    annotation_datetime = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.annotation_text

# ----------------------------
# Equipment Extension
# ----------------------------

class Equipment(models.Model):
    equipment_id = models.AutoField(primary_key=True)
    equipment_name = models.CharField(max_length=255)
    equipment_type = models.CharField(max_length=255, null=True, blank=True)
    description = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.equipment_name

class ActionEquipment(models.Model):
    action_equipment_id = models.AutoField(primary_key=True)
    action = models.ForeignKey(Action, on_delete=models.CASCADE)
    equipment = models.ForeignKey(Equipment, on_delete=models.CASCADE)
    role = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return f"{self.equipment} used in {self.action}"
