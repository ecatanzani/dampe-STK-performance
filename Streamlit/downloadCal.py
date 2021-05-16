import streamlit as st
import shutil
import time
from datetime import date
from tqdm import tqdm
import subprocess
import sys
import os



def getdate(file: str) -> date:
    year = int(file[file.rfind('/')+1:file.rfind('/')+5])
    month = int(file[file.rfind('/')+5:file.rfind('/')+7])
    day = int(file[file.rfind('/')+7:])
    return date(year, month, day)

def getdate_str(file_date: date) -> str:
    year = str(file_date.year)
    month = str(f"0{file_date.month}") if file_date.month < 10 else str(file_date.month)
    day = str(f"0{file_date.day}") if file_date.day < 10 else str(file_date.day)
    return f"{year}{month}{day}"

def downloadSingleFile(file: str, file_date: date, local_dir: str, config: dict):
    downloadDataCommand = f"xrdcp {config['farmAddress']}/{file} {local_dir}/{getdate_str(file_date)}"
    print(f"Downloading file: {format(downloadDataCommand)}")
    subprocess.run(downloadDataCommand, shell=True, check=True, stdout=subprocess.PIPE)

def checkLocalDir(local_dir: str) -> bool:
    status = True
    if (os.path.exists(local_dir)):
        status = False
    else:
        os.mkdir(local_dir)
    return status

def parseXrootDfiles(config: dict, local_dir: str) -> dict:

    st.info("**Searching calibration siles on XROOTD...**")
    st.info("This process may require some minuts accordingly to the selected time window ...")

    # Crate output data file list
    years = []
    files = []
    dates = []
    counters = []
    nladders = 192

    # Get stage 0 dirs --> /FM/FlightData/CAL/STK/
    getDataDirsCommand = f"xrdfs {config['farmAddress']} ls {config['cal_XRDFS_path']}"
    
    dataDirsOut = subprocess.run(
        getDataDirsCommand, shell=True, check=True, stdout=subprocess.PIPE)
    dataDirs = str.split(dataDirsOut.stdout.decode('utf-8').rstrip(), '\n')

    # Get stage 1 dirs --> /FM/FlightData/CAL/STK/DayOfCalibration/
    for dir_st1 in dataDirs:
        if "20" in dir_st1:

            # Date filtering
            tmpdate = getdate(dir_st1)
            if tmpdate < config['start_date'] or tmpdate > config['end_date']:
                continue
            if tmpdate.year not in years:
                years.append(tmpdate.year)
                year_data_idx = len(years)-1
                counters.append(0)
            
            getDataDirsCommand = f"xrdfs {config['farmAddress']} ls {dir_st1}"
            dataDirsOut = subprocess.run(
                getDataDirsCommand, shell=True, check=True, stdout=subprocess.PIPE)
            dataDirs_st1 = str.split(
                dataDirsOut.stdout.decode('utf-8').rstrip(), '\n')

            # Get stage 2 dirs --> /FM/FlightData/CAL/STK/DayOfCalibration/STK_CALIB_RAW_***/CalibrationFiles
            foundcaldir = False
            for dir_st2 in [tmpdst2 for tmpdst2 in dataDirs_st1 if "RAW" in tmpdst2]:
                if not foundcaldir:
                    getDataDirsCommand = f"xrdfs {config['farmAddress']} ls {dir_st2}"
                    dataDirsOut = subprocess.run(
                        getDataDirsCommand, shell=True, check=True, stdout=subprocess.PIPE)
                    dataDirs_st2 = str.split(
                        dataDirsOut.stdout.decode('utf-8').rstrip(), '\n')

                    # Get calibration data file
                    cal_files = [file for file in dataDirs_st2 if file.endswith('.cal')]
                    if len(cal_files) == nladders:
                        dates.append(tmpdate)
                        files.append(cal_files)
                        foundcaldir = True
                        counters[year_data_idx] += len(cal_files)
    
    print(f"{sum(counters)} data files have been read...")
    for year_idx, year in enumerate(years):
        print(f"{counters[year_idx]} data files found in {year} folder")
    return dict(zip(dates, files))

def downloadFiles(file_dict: dict, local_dir: str, config: dict):
    st.info("**Downloading calibration files...**")
    
    nladders = 192
    perc_complete = 0.
    step = 1./(len(file_dict)*nladders)
    bar = st.progress(perc_complete)

    for tmpdate in file_dict:
        os.mkdir(f"{local_dir}/{getdate_str(tmpdate)}")
        for calfile in file_dict[tmpdate]:
            downloadSingleFile(calfile, tmpdate, local_dir, config)
            perc_complete += step 
            bar.progress(round(perc_complete, 1))

def checkDownloadedFiles(local_dir: str = "cal") -> bool:
    status = True
    nladders = 192
    
    st.info("Checking downloaded calibration files")
    for day_cal in tqdm([_dir for _dir in os.listdir(local_dir) if not _dir.startswith('.')]):
        cals = [cal for cal in os.listdir(f"{local_dir}/{day_cal}") if cal.endswith('.cal')]
        if len(cals) is not nladders:
            status = False
            st.error(f"Error: check calibration files in {day_cal}")
            break
    return status

def getCalFiles(config: dict, local_dir: str = "cal") -> bool:

    # Check local directory
    if not checkLocalDir(local_dir):
        shutil.rmtree(local_dir)
        os.mkdir(local_dir)
    file_dict = parseXrootDfiles(config, local_dir)
    downloadFiles(file_dict, local_dir, config)
    return checkDownloadedFiles(local_dir)
    