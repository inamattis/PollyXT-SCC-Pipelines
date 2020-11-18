'''
Various container classes and utility functions for handling SCC responses
'''

from datetime import datetime
from dataclasses import dataclass, field
from pollyxt_pipelines.locations import Location, get_location_by_scc_code

from bs4.element import Tag


# ## Utility function for HTML parsing


def scc_date(tag: Tag) -> datetime:
    '''Convert a table cell to a date'''
    return datetime.strptime(tag.text, '%Y-%m-%d %H:%M')


def scc_bool(node: Tag) -> bool:
    '''Convert a table cell to a bool'''
    return node.img['alt'] == 'True'


# ## Container classes


@dataclass(frozen=True)
class Measurement():
    id: str
    station_code: str
    location: Location = field(init=False)

    date_start: datetime
    date_end: datetime
    date_creation: datetime
    date_updated: datetime

    is_uploaded: bool
    has_hirelpp: bool
    has_cloudmask: bool
    has_elpp: bool
    has_elda: bool
    has_eldec: bool
    has_elic: bool
    has_elquick: bool

    is_processing: bool

    def __post_init__(self):
        super().__setattr__('location', get_location_by_scc_code(self.station_code))

    def to_csv(self):
        return f"{self.id},{self.location.name},{self.station_code},{self.date_start.isoformat()},{self.date_end.isoformat()},{self.date_creation.isoformat()},{self.date_updated.isoformat()},{self.is_uploaded},{self.has_hirelpp},{self.has_cloudmask},{self.has_elpp},{self.has_elda},{self.has_eldec},{self.has_elic},{self.has_elquick}"

    @staticmethod
    def from_table_row(tr: Tag):
        '''
        Create a measurement object from a table row.
        Table rows are formatted like in https://scc.imaa.cnr.it/admin/database/measurements/
        '''

        # print(tr.prettify())

        return Measurement(
            id=tr.find('td', class_='field-id').text,
            station_code=tr.find('th', class_='field-station_id').a.text,
            date_start=scc_date(tr.find('td', class_='field-start')),
            date_end=scc_date(tr.find('td', class_='field-stop')),
            date_creation=scc_date(tr.find('td', class_='field-creation_date')),
            date_updated=scc_date(tr.find('td', class_='field-updated_date')),
            is_uploaded=scc_bool(tr.find('td', class_='field-upload_ok')),
            has_hirelpp=scc_bool(tr.find('td', class_='field-hirelpp_ok')),
            has_cloudmask=scc_bool(tr.find('td', class_='field-cloudmask_ok')),
            has_elpp=scc_bool(tr.find('td', class_='field-elpp_ok')),
            has_elda=scc_bool(tr.find('td', class_='field-eldec_ok')),
            has_eldec=scc_bool(tr.find('td', class_='field-eldec_ok')),
            has_elic=scc_bool(tr.find('td', class_='field-elic_ok')),
            has_elquick=scc_bool(tr.find('td', class_='field-elquick_ok')),
            is_processing=scc_bool(tr.find('td', class_='field-is_being_processed'))
        )