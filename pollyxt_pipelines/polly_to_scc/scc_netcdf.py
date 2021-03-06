'''
Routines for converting PollyXT files to SCC files
'''

from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Tuple
from enum import Enum

from netCDF4 import Dataset
import numpy as np

from pollyxt_pipelines.polly_to_scc import pollyxt
from pollyxt_pipelines.locations import Location


class Wavelength(Enum):
    '''Laser wavelength'''
    NM_355 = 355
    NM_532 = 532


'''When calibration takes place each day, in HH:MM-HH:MM format'''
CALIBRATION_PERIODS = ['02:31-02:41', '17:31-17:41', '21:31-21:41']


def calibration_to_datetime(base: datetime, period: str) -> Tuple[datetime, datetime]:
    '''
    Given a calibrarion period in HH:MM-HH:MM format (start-end), it converts it to a pair of `datetime`, the same day
    as the given `base`.
    '''
    base = base.replace(hour=0, minute=0, second=0)

    start, end = period.split('-')
    start = [int(x) for x in start.split(':')]
    end = [int(x) for x in end.split(':')]

    start = base + timedelta(hours=start[0], minutes=start[1])
    end = base + timedelta(hours=end[0], minutes=end[1])

    return start, end


def create_scc_netcdf(
    pf: pollyxt.PollyXTFile,
    output_path: Path,
    location: Location
) -> Tuple[str, Path]:
    '''
    Convert a PollyXT netCDF file to a SCC file.

    Parameters:
        pf: An opened PollyXT file. When you create this, you can specify the time period of interest.
        output_path: Where to store the produced netCDF file
        location: Where did this measurement take place

    Returns:
        A tuple containing  the measurement ID and the output path
    '''

    # Calculate measurement ID
    measurement_id = pf.start_date.strftime(
        f'%Y%m%d{location.scc_code}%H{pf.end_date.strftime("%H")}')

    # Create SCC file
    # Output filename is always the measurement ID
    output_filename = output_path / f'{measurement_id}.nc'
    nc = Dataset(output_filename, 'w')

    # Create dimensions (mandatory!)
    nc.createDimension('points', np.size(pf.raw_signal, axis=1))
    nc.createDimension('channels', np.size(pf.raw_signal, axis=2))
    nc.createDimension('time', None)
    nc.createDimension('nb_of_time_scales', 1)
    nc.createDimension('scan_angles', 1)

    # Create Global Attributes (mandatory!)
    nc.Measurement_ID = measurement_id
    nc.RawData_Start_Date = pf.start_date.strftime('%Y%m%d')
    nc.RawData_Start_Time_UT = pf.start_date.strftime('%H%M%S')
    nc.RawData_Stop_Time_UT = pf.end_date.strftime('%H%M%S')

    # Create Global Attributes (optional)
    nc.RawBck_Start_Date = nc.RawData_Start_Date
    nc.RawBck_Start_Time_UT = nc.RawData_Start_Time_UT
    nc.RawBck_Stop_Time_UT = nc.RawData_Stop_Time_UT
    nc.Sounding_File_Name = f'rs_{measurement_id[:-2]}.nc'
    # nc.Overlap_File_Name = 'ov_' + selected_start.strftime('%Y%m%daky%H') + '.nc'

    # Custom attribute for configuration ID
    # From 04:00 until 16:00 we use daytime configuration
    if pf.start_date.replace(hour=4, minute=0) < pf.start_date and pf.start_date < pf.start_date.replace(hour=16, minute=0):
        nc.NOAReACT_Configuration_ID = location.system_id_day
    else:
        nc.NOAReACT_Configuration_ID = location.system_id_night

    # Create Variables. (mandatory)
    raw_data_start_time = nc.createVariable(
        'Raw_Data_Start_Time', 'i4', dimensions=('time', 'nb_of_time_scales'), zlib=True)
    raw_data_stop_time = nc.createVariable(
        'Raw_Data_Stop_Time', 'i4', dimensions=('time', 'nb_of_time_scales'), zlib=True)
    raw_lidar_data = nc.createVariable(
        'Raw_Lidar_Data', 'f8', dimensions=('time', 'channels', 'points'), zlib=True)
    channel_id = nc.createVariable('channel_ID', 'i4', dimensions=('channels'), zlib=True)
    id_timescale = nc.createVariable('id_timescale', 'i4', dimensions=('channels'), zlib=True)
    laser_pointing_angle = nc.createVariable(
        'Laser_Pointing_Angle', 'f8', dimensions=('scan_angles'), zlib=True)
    laser_pointing_angle_of_profiles = nc.createVariable(
        'Laser_Pointing_Angle_of_Profiles', 'i4', dimensions=('time', 'nb_of_time_scales'), zlib=True)
    laser_shots = nc.createVariable('Laser_Shots', 'i4', dimensions=('time', 'channels'), zlib=True)
    background_low = nc.createVariable('Background_Low', 'f8', dimensions=('channels'), zlib=True)
    background_high = nc.createVariable('Background_High', 'f8', dimensions=('channels'), zlib=True)
    molecular_calc = nc.createVariable('Molecular_Calc', 'i4', dimensions=(), zlib=True)
    nc.createVariable(
        'Pol_Calib_Range_Min', 'f8', dimensions=('channels'), zlib=True)
    nc.createVariable(
        'Pol_Calib_Range_Max', 'f8', dimensions=('channels'), zlib=True)
    pressure_at_lidar_station = nc.createVariable(
        'Pressure_at_Lidar_Station', 'f8', dimensions=(), zlib=True)
    temperature_at_lidar_station = nc.createVariable(
        'Temperature_at_Lidar_Station', 'f8', dimensions=(), zlib=True)
    lr_input = nc.createVariable('LR_Input', 'i4', dimensions=('channels'), zlib=True)

    # Fill Variables with Data. (mandatory)
    raw_data_start_time[:] = pf.measurement_time[:, 1] - pf.measurement_time[0, 1]
    raw_data_stop_time[:] = (pf.measurement_time[:, 1] - pf.measurement_time[0, 1]) + 30
    raw_lidar_data[:] = np.swapaxes(pf.raw_signal, 1, 2)
    channel_id[:] = np.array([493, 500, 497, 499, 494, 496, 498, 495, 501, 941, 940, 502])
    id_timescale[:] = np.zeros(np.size(pf.raw_signal, axis=2))
    laser_pointing_angle[:] = int(pf.zenith_angle.item(0))
    laser_pointing_angle_of_profiles[:] = np.zeros(np.size(pf.raw_signal, axis=0))
    laser_shots[:] = pf.measurement_shots[:]
    background_low[:] = np.array([0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0])
    background_high[:] = np.array([249, 249, 249, 249, 249, 249, 249, 249, 249, 249, 249, 249])
    molecular_calc[:] = 1
    pressure_at_lidar_station[:] = 1008
    temperature_at_lidar_station[:] = 20
    lr_input[:] = np.array([1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1])

    # Close the netCDF file.
    nc.close()

    return measurement_id, output_filename


def create_scc_calibration_netcdf(
    pf: pollyxt.PollyXTFile,
    output_path: Path,
    location: Location,
    wavelength: Wavelength,
    pol_calib_range_min: int = 1200,
    pol_calib_range_max: int = 2500
) -> Tuple[str, Path]:
    '''
    From a PollyXT netCDF file, create the corresponding calibration SCC file.
    Calibration times are:
    - 02:31 to 02:41
    - 17:31 to 17:41
    - 21:31 to 21:41
    Take care to create the `PollyXTFile` with these intervals.

    Parameters:
        pf: An opened PollyXT file
        output_path: Where to store the produced netCDF file
        location: Where did this measurement take place
        wavelength: Calibration for 355nm or 532nm
        pol_calib_range_min: Calibration contant calculation, minimum height
        pol_calib_range_max: Calibration contant calculation, maximum height

    Returns:
        A tuple containing the measurement ID and the output path
    '''

    # Calculate measurement ID
    measurement_id = pf.start_date.strftime(f'%Y%m%d{location.scc_code}%H')

    # Create SCC file
    # Output filename is always the measurement ID
    output_filename = output_path / f'calibration_{measurement_id}.nc'
    nc = Dataset(output_filename, 'w')

    # Create Dimensions. (mandatory)
    nc.createDimension("points", np.size(pf.raw_signal, axis=1))
    nc.createDimension("channels", 4)
    nc.createDimension("time", 3)
    nc.createDimension("nb_of_time_scales", 1)
    nc.createDimension("scan_angles", 1)

    # Create Global Attributes. (mandatory)
    nc.RawData_Start_Date = pf.start_date.strftime('%Y%m%d')
    nc.RawData_Start_Time_UT = pf.start_date.strftime('%H%M%S')
    nc.RawData_Stop_Time_UT = pf.end_date.strftime('%H%M%S')

    # Create Global Attributes (optional)
    nc.RawBck_Start_Date = nc.RawData_Start_Date
    nc.RawBck_Start_Time_UT = nc.RawData_Start_Time_UT
    nc.RawBck_Stop_Time_UT = nc.RawData_Stop_Time_UT

    # Create Variables. (mandatory)
    raw_data_start_time = nc.createVariable(
        "Raw_Data_Start_Time", "i4", dimensions=("time", "nb_of_time_scales"), zlib=True)
    raw_data_stop_time = nc.createVariable(
        "Raw_Data_Stop_Time", "i4", dimensions=("time", "nb_of_time_scales"), zlib=True)
    raw_lidar_data = nc.createVariable(
        "Raw_Lidar_Data", "f8", dimensions=("time", "channels", "points"), zlib=True)
    channel_id = nc.createVariable("channel_ID", "i4", dimensions=("channels"), zlib=True)
    id_timescale = nc.createVariable("id_timescale", "i4", dimensions=("channels"), zlib=True)
    laser_pointing_angle = nc.createVariable(
        "Laser_Pointing_Angle", "f8", dimensions=("scan_angles"), zlib=True)
    laser_pointing_angle_of_profiles = nc.createVariable(
        "Laser_Pointing_Angle_of_Profiles", "i4", dimensions=("time", "nb_of_time_scales"), zlib=True)
    laser_shots = nc.createVariable("Laser_Shots", "i4", dimensions=("time", "channels"), zlib=True)
    background_low = nc.createVariable("Background_Low", "f8", dimensions=("channels"), zlib=True)
    background_high = nc.createVariable("Background_High", "f8", dimensions=("channels"), zlib=True)
    molecular_calc = nc.createVariable("Molecular_Calc", "i4", dimensions=(), zlib=True)
    pol_calib_range_min_var = nc.createVariable(
        "Pol_Calib_Range_Min", "f8", dimensions=("channels"), zlib=True)
    pol_calib_range_max_var = nc.createVariable(
        "Pol_Calib_Range_Max", "f8", dimensions=("channels"), zlib=True)
    pressure_at_lidar_station = nc.createVariable(
        "Pressure_at_Lidar_Station", "f8", dimensions=(), zlib=True)
    temperature_at_lidar_station = nc.createVariable(
        "Temperature_at_Lidar_Station", "f8", dimensions=(), zlib=True)

    # define measurement_cycles
    start_first_measurement = 0
    stop_first_measurement = 12

    # Fill Variables with Data. (mandatory)
    id_timescale[:] = np.array([0, 0, 0, 0])
    laser_pointing_angle[:] = 5
    laser_pointing_angle_of_profiles[:, :] = 0.0
    laser_shots[0, :] = np.array([600, 600, 600, 600])
    laser_shots[1, :] = np.array([600, 600, 600, 600])
    laser_shots[2, :] = np.array([600, 600, 600, 600])
    background_low[:] = np.array([0, 0, 0, 0])
    background_high[:] = np.array([249, 249, 249, 249])
    molecular_calc[:] = 0
    pol_calib_range_min_var[:] = np.repeat(pol_calib_range_min, 4)
    pol_calib_range_max_var[:] = np.repeat(pol_calib_range_max, 4)
    pressure_at_lidar_station[:] = 1008  # TODO Maybe take these from radiosonde?
    temperature_at_lidar_station[:] = 20

    # Define total and cross channels IDs from Polly
    if wavelength == Wavelength.NM_355:
        total_channel = 0
        cross_channel = 1
        channel_id[:] = np.array([1236, 1266, 1267, 1268])
        nc.Measurement_ID = measurement_id + '35'  # TODO This is the filename!!
    elif wavelength == Wavelength.NM_532:
        total_channel = 4
        cross_channel = 5
        channel_id[:] = np.array([1269, 1270, 1271, 1272])
        nc.Measurement_ID = measurement_id + '53'  # TODO This is the filename!!
    else:
        raise ValueError(f'Unknown wavelength {wavelength}')

    # Copy calibration cycles
    raw_data_start_time[0, 0] = start_first_measurement
    raw_data_start_time[1, 0] = start_first_measurement + 1
    raw_data_start_time[2, 0] = start_first_measurement + 2
    raw_data_stop_time[0, 0] = stop_first_measurement
    raw_data_stop_time[1, 0] = stop_first_measurement + 1
    raw_data_stop_time[2, 0] = stop_first_measurement + 2

    raw_lidar_data[0, 0, :] = pf.raw_signal_swap[start_first_measurement, cross_channel, :]
    raw_lidar_data[0, 1, :] = pf.raw_signal_swap[start_first_measurement, total_channel, :]
    raw_lidar_data[0, 2, :] = pf.raw_signal_swap[stop_first_measurement, cross_channel, :]
    raw_lidar_data[0, 3, :] = pf.raw_signal_swap[stop_first_measurement, total_channel, :]

    raw_lidar_data[1, 0, :] = pf.raw_signal_swap[start_first_measurement + 1, cross_channel, :]
    raw_lidar_data[1, 1, :] = pf.raw_signal_swap[start_first_measurement + 1, total_channel, :]
    raw_lidar_data[1, 2, :] = pf.raw_signal_swap[stop_first_measurement + 1, cross_channel, :]
    raw_lidar_data[1, 3, :] = pf.raw_signal_swap[stop_first_measurement + 1, total_channel, :]

    raw_lidar_data[2, 0, :] = pf.raw_signal_swap[start_first_measurement + 2, cross_channel, :]
    raw_lidar_data[2, 1, :] = pf.raw_signal_swap[start_first_measurement + 2, total_channel, :]
    raw_lidar_data[2, 2, :] = pf.raw_signal_swap[stop_first_measurement + 2, cross_channel, :]
    raw_lidar_data[2, 3, :] = pf.raw_signal_swap[stop_first_measurement + 2, total_channel, :]

    # Close the netCDF file.
    nc.close()

    return measurement_id, output_filename


def convert_pollyxt_file(
        input_path: Path,
        output_path: Path,
        location: Location,
        interval: timedelta,
        should_round=False,
        calibration=True):
    '''
    Converts a PollyXT file into a bunch of SCC files. The input file will be split into intervals before being converted
    to the new format.

    This function is a generator, so you can use it in a for loop to monitor progress::

        for measurement_id, path in convert_pollyxt_file(...):
            # Do something with id/path, maybe print a message?


    Parameters:
        input_path: PollyXT file to convert
        output_path: Directory to write the SCC files
        location: Geographical information, where the measurement took place
        interval: What interval to use when splitting the PollyXT file (e.g. 1 hour)
        shoudld_round: If true, the interval starts will be rounded down. For example, from 01:02 to 01:00.
    '''

    # Open input netCDF
    measurement_start, measurement_end = pollyxt.get_measurement_period(input_path)

    # Create output files
    interval_start = measurement_start
    while interval_start < measurement_end:
        # If the option is set, round down hours
        if should_round:
            interval_start = interval_start.replace(microsecond=0, second=0, minute=0)

        # Interval end
        interval_end = interval_start + interval

        # Open netCDF file and convert to SCC
        pf = pollyxt.PollyXTFile(input_path, interval_start, interval_end)
        id, path = create_scc_netcdf(pf, output_path, location)
        yield id, path, interval_start

        # Set start of next interval to the end of this one
        interval_start = interval_end

    # Generate calibration files
    # - 02:31 to 02:41
    # - 17:31 to 17:41
    # - 21:31 to 21:41
    if calibration:
        # Check for any valid calibration intervals
        for period in CALIBRATION_PERIODS:
            start, end = calibration_to_datetime(measurement_start, period)

            if start > measurement_start and end < measurement_end:
                pf = pollyxt.PollyXTFile(input_path, start, end)
                id, path = create_scc_calibration_netcdf(
                    pf, output_path, location, wavelength=Wavelength.NM_532)

                yield id, path, start
