from abc import ABC, abstractmethod
from collections.abc import Sequence
from notifications_utils.timezones import utc_string_to_aware_gmt_datetime

from flask import abort


class JSONModel():

    ALLOWED_PROPERTIES = set()
    DATETIME_PROPERTIES = set()

    def __init__(self, _dict):
        # in the case of a bad request _dict may be `None`
        self._dict = _dict or {}

    def __bool__(self):
        return self._dict != {}

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        return self.id == other.id

    def __getattribute__(self, attr):

        try:
            return super().__getattribute__(attr)
        except AttributeError as e:
            # Re-raise any `AttributeError`s that are not directly on
            # this object because they indicate an underlying exception
            # that we don’t want to swallow
            if str(e) != "'{}' object has no attribute '{}'".format(
                self.__class__.__name__, attr
            ):
                raise e

        if attr in super().__getattribute__('DATETIME_PROPERTIES'):
            return self._datetime_from_date_string(
                super().__getattribute__('_dict').get(attr)
            )

        if attr in super().__getattribute__('ALLOWED_PROPERTIES'):
            return super().__getattribute__('_dict')[attr]

        raise AttributeError((
            "'{}' object has no attribute '{}' and '{}' is not a field "
            "in the underlying JSON"
        ).format(
            self.__class__.__name__, attr, attr
        ))

    def _get_by_id(self, things, id):
        try:
            return next(thing for thing in things if thing['id'] == str(id))
        except StopIteration:
            abort(404)

    @staticmethod
    def _datetime_from_date_string(datetime_string):
        if not datetime_string:
            return None
        return utc_string_to_aware_gmt_datetime(datetime_string)


class ModelList(ABC, Sequence):

    @property
    @abstractmethod
    def client_method(self):
        pass

    @property
    @abstractmethod
    def model(self):
        pass

    def __init__(self, *args):
        self.items = self.client_method(*args)

    def __getitem__(self, index):
        return self.model(self.items[index])

    def __len__(self):
        return len(self.items)

    def __add__(self, other):
        return list(self) + list(other)


class InviteTokenError(Exception):
    pass
