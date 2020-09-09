from operator import itemgetter

from notifications_utils.serialised_model import SerialisedModelCollection
from notifications_utils.formatters import formatted_list
from werkzeug.utils import cached_property

from .polygons import Polygons
from .repo import BroadcastAreasRepository


class SortableMixin:

    def __repr__(self):
        return f'{self.__class__.__name__}(<{self.id}>)'

    def __lt__(self, other):
        # Implementing __lt__ means any classes inheriting from this
        # method are sortable
        return self.name < other.name


class GetItemByIdMixin:
    def get(self, id):
        for item in self:
            if item.id == id:
                return item
        raise KeyError(id)


class BroadcastArea(SortableMixin):

    def __init__(self, row):
        self.id, self.name = row

    def __eq__(self, other):
        return self.id == other.id

    @cached_property
    def polygons(self):
        return Polygons(
            BroadcastAreasRepository().get_polygons_for_area(self.id)
        )

    @cached_property
    def simple_polygons(self):
        return Polygons(
            BroadcastAreasRepository().get_simple_polygons_for_area(self.id)
        )

    @cached_property
    def sub_areas(self):
        return [
            BroadcastArea(row)
            for row in BroadcastAreasRepository().get_all_areas_for_group(self.id)
        ]


class BroadcastAreaLibrary(SerialisedModelCollection, SortableMixin, GetItemByIdMixin):

    model = BroadcastArea

    def __init__(self, row):
        id, name, name_singular, is_group = row
        self.id = id
        self.name = name
        self.name_singular = name_singular
        self.is_group = bool(is_group)
        self.items = BroadcastAreasRepository().get_all_areas_for_library(self.id)

    def get_examples(self):
        # we show up to four things. three areas, then either a fourth area if there are exactly four, or "and X more".
        areas_to_show = [area[1] for area in sorted(self.items, key=itemgetter(1))[:4]]

        count_of_areas_not_named = len(self.items) - 3
        # if there's exactly one area not named, there are exactly four - we should just show all four.
        if count_of_areas_not_named > 1:
            return f'{", ".join(areas_to_show[:3])} and {count_of_areas_not_named} more…'
        else:
            return formatted_list(areas_to_show, before_each='', after_each='')


class BroadcastAreaLibraries(SerialisedModelCollection, GetItemByIdMixin):

    model = BroadcastAreaLibrary

    def __init__(self):
        self.items = BroadcastAreasRepository().get_libraries()

    def get_areas(self, *area_ids):
        # allow people to call `get_areas('a', 'b') or get_areas(['a', 'b'])`
        if len(area_ids) == 1 and isinstance(area_ids[0], list):
            area_ids = area_ids[0]

        areas = BroadcastAreasRepository().get_areas(area_ids)
        return [BroadcastArea(area) for area in areas]


broadcast_area_libraries = BroadcastAreaLibraries()
