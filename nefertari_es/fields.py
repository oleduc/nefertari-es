import datetime
from dateutil import parser

import six
from elasticsearch_dsl import (
    field,
    DocType,
    )
from elasticsearch_dsl.exceptions import ValidationException
from elasticsearch_dsl.utils import AttrList, AttrDict


class CustomMappingMixin(object):
    """ Mixin that allows to define custom ES field mapping.

    Set mapping to "_custom_mapping" attribute. Defaults to None, in
    which case default field mapping is used. Custom mapping extends
    default mapping.
    """
    _custom_mapping = None

    def to_dict(self, *args, **kwargs):
        data = super(CustomMappingMixin, self).to_dict(*args, **kwargs)
        if self._custom_mapping is not None:
            data.update(self._custom_mapping)
        return data


class BaseFieldMixin(object):
    def __init__(self, *args, **kwargs):
        self._primary_key = kwargs.pop('primary_key', False)
        if self._primary_key:
            kwargs['required'] = True
        super(BaseFieldMixin, self).__init__(*args, **kwargs)


class IdField(CustomMappingMixin, BaseFieldMixin, field.String):
    """ Field that stores ID generated by ES. """
    name = 'idfield'
    _custom_mapping = {'type': 'string'}

    def __init__(self, *args, **kwargs):
        kwargs['primary_key'] = True
        super(IdField, self).__init__(*args, **kwargs)
        self._required = False

    def _empty(self):
        return None


class IntervalField(BaseFieldMixin, field.Integer):
    """ Custom field that stores `datetime.timedelta` instances.

    Values are stored as seconds in ES and loaded by
    `datetime.timedelta(seconds=<value>) when restoring from ES.
    """
    _coerce = True

    def _to_python(self, data):
        if isinstance(data, int):
            return datetime.timedelta(seconds=data)
        return super(IntervalField, self)._to_python(data)


class DictField(CustomMappingMixin, BaseFieldMixin, field.Object):
    name = 'dict'
    _custom_mapping = {'type': 'object', 'enabled': False}


class DateTimeField(CustomMappingMixin, BaseFieldMixin, field.Field):
    name = 'datetime'
    _coerce = True
    _custom_mapping = {'type': 'date', 'format': 'dateOptionalTime'}

    def _to_python(self, data):
        if not data:
            return None
        if isinstance(data, datetime.datetime):
            return data
        try:
            return parser.parse(data)
        except Exception as e:
            raise ValidationException(
                'Could not parse datetime from the value (%r)' % data, e)


class DateField(CustomMappingMixin, BaseFieldMixin, field.Date):
    _custom_mapping = {'type': 'date', 'format': 'dateOptionalTime'}


class TimeField(CustomMappingMixin, BaseFieldMixin, field.Field):
    name = 'time'
    _coerce = True
    _custom_mapping = {'type': 'date', 'format': 'HH:mm:ss'}

    def _to_python(self, data):
        if not data:
            return None
        if isinstance(data, datetime.time):
            return data
        if isinstance(data, datetime.datetime):
            return data.time()
        try:
            return parser.parse(data).time()
        except Exception as e:
            raise ValidationException(
                'Could not parse time from the value (%r)' % data, e)


class IntegerField(BaseFieldMixin, field.Integer):
    pass


class SmallIntegerField(BaseFieldMixin, field.Integer):
    pass


class StringField(BaseFieldMixin, field.String):
    pass


class TextField(BaseFieldMixin, field.String):
    pass


class UnicodeField(BaseFieldMixin, field.String):
    pass


class UnicodeTextField(BaseFieldMixin, field.String):
    pass


class BigIntegerField(BaseFieldMixin, field.Long):
    pass


class BooleanField(BaseFieldMixin, field.Boolean):
    pass


class FloatField(BaseFieldMixin, field.Float):
    pass


class BinaryField(BaseFieldMixin, field.Byte):
    pass


class DecimalField(BaseFieldMixin, field.Double):
    pass


class ReferenceField(CustomMappingMixin, field.String):
    _backref_prefix = 'backref_'
    _coerce = False

    def __init__(self, doc_class, is_backref=False, *args, **kwargs):
        prefix_len = len(self._backref_prefix)
        self._backref_kwargs = {
            key[prefix_len:]: val for key, val in kwargs.items()
            if key.startswith(self._backref_prefix)}
        for key in self._backref_kwargs:
            del kwargs[self._backref_prefix + key]
        self._is_backref = is_backref
        self._doc_class = doc_class
        super(ReferenceField, self).__init__(*args, **kwargs)

    @property
    def _doc_class(self):
        from .meta import get_document_cls
        return get_document_cls(self._doc_class_name)

    @_doc_class.setter
    def _doc_class(self, name):
        self._doc_class_name = name

    def empty(self):
        if not self._required:
            return AttrList([]) if self._multi else None
        return super(ReferenceField, self).empty()

    def clean(self, data):
        types = (self._doc_class, list, AttrDict, AttrList)
        if not isinstance(data, types):
            return data
        return super(ReferenceField, self).clean(data)

    def _backref_field_name(self):
        return self._backref_kwargs.get('name')


def Relationship(document_type, uselist=True, nested=True, **kw):
    # XXX deal with updating, deleting rules

    return ReferenceField(
        multi=uselist,
        doc_class=document_type,
        **kw)
