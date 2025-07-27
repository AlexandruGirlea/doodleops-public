import re
from django.db import models
from django.core.exceptions import ValidationError


class Setting(models.Model):
	DATA_TYPES = (
		('int', 'Integer'),
		('str', 'String'),
		('bool', 'Boolean'),
		('float', 'Float'),
		('datetime', 'Datetime'),
		('json', 'JSON'),
	)

	key = models.CharField(max_length=100, unique=True)
	value_type = models.CharField(max_length=10, choices=DATA_TYPES)
	int_value = models.IntegerField(null=True, blank=True)
	str_value = models.TextField(null=True, blank=True)
	bool_value = models.BooleanField(null=True, blank=True)
	float_value = models.FloatField(null=True, blank=True)
	datetime_value = models.DateTimeField(null=True, blank=True)
	description = models.TextField(blank=True)
	json_value = models.JSONField(
		null=True, blank=True,
		help_text=(
			"Attention: JSON data must be valid, else Django Admin JS "
			"will not send it."
		)
	)

	def clean(self):
		super().clean()

		pattern = r'^[a-z_]{1,100}$'
		if not re.match(pattern, self.key):
			raise ValidationError({
				"key": (
					"Key must be snake_case and have a maximum of 100 characters."
				)
			})
		self.str_value = self.str_value if self.str_value else None

		value_fields = {
			'int': self.int_value,
			'str': self.str_value,
			'bool': self.bool_value,
			'float': self.float_value,
			'datetime': self.datetime_value,
			'json': self.json_value,
		}

		# Check that the correct field is populated
		for field_type, field_value in value_fields.items():
			if field_type == self.value_type:
				if field_value is None:
					raise ValidationError(
						f'Value for type {self.value_type} must not be empty.')
			else:
				if field_value is not None:
					raise ValidationError(
						f'Field {field_type}_value should be empty.')

	def get_value(self):
		"""Retrieve the value based on value_type."""
		value_fields = {
			'int': self.int_value,
			'str': self.str_value,
			'bool': self.bool_value,
			'float': self.float_value,
			'datetime': self.datetime_value,
			'json': self.json_value,
		}
		return value_fields.get(self.value_type)

	def __str__(self):
		return self.key
