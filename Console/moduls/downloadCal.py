from datetime import date
from tqdm import tqdm
import subprocess
import argparse
import shutil
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
    
def checkLocalDir(local_dir: str) -> bool:
    status = True
    if (os.path.exists(local_dir)):
        status = False
    else:
        os.mkdir(local_dir)
    return status

def parseXrootDfiles(config: dict, opts: argparse.Namespace, local_dir: str) -> dict:

    # Crate output data file list
    years = []
    filedirs = []
    dates = []
    counters = []
    nladders = 192

    # Get stage 0 dirs --> /FM/FlightData/CAL/STK/
    getDataDirsCommand = f"xrdfs {config['farmAddress']} ls {config['cal_XRDFS_path']}"
    if opts.verbose:
        print(f"Executing XRDFS command: {format(getDataDirsCommand)}")
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
            if opts.verbose:
                print(f"Executing XRDFS command: {getDataDirsCommand}")
            dataDirsOut = subprocess.run(
                getDataDirsCommand, shell=True, check=True, stdout=subprocess.PIPE)
            dataDirs_st1 = str.split(
                dataDirsOut.stdout.decode('utf-8').rstrip(), '\n')

            # Get stage 2 dirs --> /FM/FlightData/CAL/STK/DayOfCalibration/STK_CALIB_RAW_***/CalibrationFiles
            foundcaldir = False
            for dir_st2 in [tmpdst2 for tmpdst2 in dataDirs_st1 if "RAW" in tmpdst2]:
                if not foundcaldir:
                    getDataDirsCommand = f"xrdfs {config['farmAddress']} ls {dir_st2}"
                    if opts.verbose:
                        print(f"Executing XRDFS command: {getDataDirsCommand}")
                    dataDirsOut = subprocess.run(
                        getDataDirsCommand, shell=True, check=True, stdout=subprocess.PIPE)
                    dataDirs_st2 = str.split(
                        dataDirsOut.stdout.decode('utf-8').rstrip(), '\n')

                    # Get calibration data file
                    cal_files = [file for file in dataDirs_st2 if file.endswith('.cal')]
                    if len(cal_files) == nladders:
                        dates.append(tmpdate)
                        filedirs.append(dir_st2)
                        counters[year_data_idx] += len(cal_files)
                        foundcaldir = True

    if opts.verbose:
        print(f"{sum(counters)} data files have been read...")
        for year_idx, year in enumerate(years):
            print(f"{counters[year_idx]} data files found in {year} folder")
    return dict(zip(dates, filedirs))
    
def downloadSingleFile(file: str, file_date: date, local_dir: str, config: dict, opts: argparse.Namespace):
    downloadDataCommand = f"xrdcp {config['farmAddress']}/{file} {local_dir}/{getdate_str(file_date)}"
    if opts.verbose:
        print(f"Downloading file: {format(downloadDataCommand)}")
    subprocess.run(downloadDataCommand, shell=True, check=True, stdout=subprocess.PIPE)

def downloadSingleFolder(remote_folder: str, folder_date: date, local_dir: str, config: dict):
    downloadDataCommand = f"xrdcp -r {config['farmAddress']}/{remote_folder} {local_dir}/{getdate_str(folder_date)}"
    print(f"Downloading folder: {format(downloadDataCommand)}")
    subprocess.run(downloadDataCommand, shell=True, check=True, stdout=subprocess.PIPE)

def downloadFiles(file_dict: dict, local_dir: str, config: dict, opts: argparse.Namespace):
    if opts.verbose:
        print("Downloading calibration files...")
    for tmpdate in file_dict:
        os.mkdir(f"{local_dir}/{getdate_str(tmpdate)}")
        downloadSingleFolder(file_dict[tmpdate], tmpdate, local_dir, config)

def pruneSignleDownloadedDir(raw_cal_dir: str, cal_files: list, local_dir: str, day_cal: str):
    for calfile in cal_files:
        shutil.move(f"{local_dir}/{day_cal}/{raw_cal_dir}/{calfile}", f"{local_dir}/{day_cal}/{calfile[calfile.rfind('/')+1:]}")
    shutil.rmtree(f"{local_dir}/{day_cal}/{raw_cal_dir}")

def pruneDownloadedFiles(local_dir: str) -> bool:
    for day_cal in tqdm([_dir for _dir in os.listdir(local_dir) if not _dir.startswith('.')]):
        raw_dir = [raw for raw in os.listdir(f"{local_dir}/{day_cal}") if not raw.startswith('.')][0]
        cals = [cal for cal in os.listdir(f"{local_dir}/{day_cal}/{raw_dir}") if cal.endswith('.cal')]
        for calfile in cals:
            shutil.move(calfile, f"{local_dir}/{day_cal}/{calfile[calfile.rfind('/')+1:]}")

def checkDownloadedFiles(opts: argparse.Namespace, local_dir: str = "cal") -> bool:
    status = True
    nladders = 192
    if opts.verbose:
        print("Checking downloaded calibration files")
    for day_cal in tqdm([_dir for _dir in os.listdir(local_dir) if not _dir.startswith('.')]):
        raw_dir = [raw for raw in os.listdir(f"{local_dir}/{day_cal}") if not raw.startswith('.')][0]
        cals = [cal for cal in os.listdir(f"{local_dir}/{day_cal}/{raw_dir}") if cal.endswith('.cal')]
        if len(cals) is not nladders:
            status = False
            print(f"Error: check calibration files in {day_cal}/{raw_dir}")
            break
        else:
            pruneSignleDownloadedDir(raw_dir, cals, local_dir, day_cal)
    return status

def getCalFiles(config: dict, opts: argparse.Namespace, local_dir: str = "cal") -> bool:

    if not checkLocalDir(local_dir):
        print(f"WARNING: calibration local dir already existing ({local_dir}) ... exiting")
        return False
    else:
        file_dict = parseXrootDfiles(config, opts, local_dir)
        if len(file_dict):
            downloadFiles(file_dict, local_dir, config, opts)
            return checkDownloadedFiles(opts, local_dir)
        else:
            print('No calibration found matching the selected time window... select a different time interval')
            return False
    