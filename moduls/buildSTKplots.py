import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import date
from tqdm import tqdm
import pandas as pd
import numpy as np
import argparse
import sys
import os

def getDateFromDir(local_cal_dir: str) -> date:
    year = int(local_cal_dir[local_cal_dir.rfind('/')+1:local_cal_dir.rfind('/')+5])
    month = int(local_cal_dir[local_cal_dir.rfind('/')+5:local_cal_dir.rfind('/')+7])
    day = int(local_cal_dir[local_cal_dir.rfind('/')+7:])
    return date(year, month, day)

def buildTRBfileList(local_cal_dir: str) -> list:
    trbfiles = []
    files = [file for file in os.listdir(local_cal_dir) if file.endswith('.cal')]
    for trb in [f"TRB0{trb_idx}" for trb_idx in range(8)]:
        trbfiles.append([f"{local_cal_dir}/{ladder_cal}" for ladder_cal in files if ladder_cal.startswith(trb)])
        trbfiles[-1].sort()
    return trbfiles

def buildCalDict(local_cal_dir: str) -> dict:
    trbfiles = buildTRBfileList(local_cal_dir)
    trbs = [f"TRB0{trb_idx}" for trb_idx in range(8)]
    trb_dicts = [dict(zip(range(len(trbfiles[0])), tmptrbfiles)) for tmptrbfiles in trbfiles]
    return dict(zip(trbs, trb_dicts))

def buildMeanCalDict(file_cal_dict: dict) -> tuple:
    trbs_sigma_mean = []
    trbs_rawsigma_mean = []
    trbs_ped_mean = []
    trbs_cn_mean = []
    for trb_value in file_cal_dict:
        tmp_sigma_mean = []
        tmp_sigmaraw_mean = []
        tmp_ped_mean = []
        tmp_cn_mean = []
        for ladder_value in file_cal_dict[trb_value]:
            df = pd.read_csv(file_cal_dict[trb_value][ladder_value])
            df.columns=["ch", "va", "chva", "ped", "sigma_raw", "sigma", "status", "status_2", "status_3"]
            df = df.drop(list(range(383, 386)))
            tmp_sigma_mean.append(df['sigma'].mean())
            tmp_sigmaraw_mean.append(df['sigma_raw'].mean())
            tmp_ped_mean.append(df['ped'].mean())
            tmp_cn_mean.append(np.sqrt(pow(tmp_sigmaraw_mean[-1], 2) - pow(tmp_sigma_mean[-1], 2)))
        trbs_sigma_mean.append(tmp_sigma_mean)
        trbs_rawsigma_mean.append(tmp_sigmaraw_mean)
        trbs_ped_mean.append(tmp_ped_mean)
        trbs_cn_mean.append(tmp_cn_mean)
    trbs = [f"TRB0{trb_idx}" for trb_idx in range(8)]
    dict_sigma_mean = [dict(zip(range(len(trbs_sigma_mean[0])), sigmas)) for sigmas in trbs_sigma_mean]
    dict_sigmaraw_mean = [dict(zip(range(len(trbs_rawsigma_mean[0])), sigmas)) for sigmas in trbs_rawsigma_mean]
    dict_ped_mean = [dict(zip(range(len(trbs_ped_mean[0])), sigmas)) for sigmas in trbs_ped_mean]
    dict_cn_mean = [dict(zip(range(len(trbs_cn_mean[0])), sigmas)) for sigmas in trbs_cn_mean]
    return (dict(zip(trbs, dict_sigma_mean)), dict(zip(trbs, dict_sigmaraw_mean)), dict(zip(trbs, dict_ped_mean)), dict(zip(trbs, dict_cn_mean)))

def getMeanValue(valdict: dict) -> float:
    trb_meanvalues = []
    for trb_value in valdict:
        trb_meanvalues.append(np.array(list(valdict[trb_value].values())).mean())
    return np.array(trb_meanvalues).mean()

def parseCalLocalDirs(local_cal_dir: str) -> dict:
    caldate = []
    sigma = []
    sigma_row = []
    ped = []
    cn = []
    for cal_folder in tqdm([f"{local_cal_dir}/{folder}" for folder in os.listdir(local_cal_dir) if folder.startswith('20')]):
        caldate.append(getDateFromDir(cal_folder))
        cal_dict = buildCalDict(cal_folder)
        mean_dicts = buildMeanCalDict(cal_dict)
        sigma.append(getMeanValue(mean_dicts[0]))
        sigma_row.append(getMeanValue(mean_dicts[1]))
        ped.append(getMeanValue(mean_dicts[2]))
        cn.append(getMeanValue(mean_dicts[3]))
    return {'date': caldate, 'sigma': sigma, 'sigma_row': sigma_row, 'pedestal': ped, 'cn': cn}


def buildEvFigure(time_evolution: dict, plt_variable:str, plt_variable_label: str, plt_color: str, plt_path: str):
    plt.clf()
    fig, ax = plt.subplots()
    ax.plot(time_evolution['date'], time_evolution[plt_variable], label=plt_variable_label, color=plt_color)
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=6))
    ax.xaxis.set_minor_locator(mdates.MonthLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    fig.autofmt_xdate()
    plt.savefig(plt_path)

def buildStkPlots(opts: argparse.Namespace):
    local_cal_dir = opts.local if opts.local else "cal"
    if opts.verbose:
        print(f"\nGetting time evolution information from local dir: {local_cal_dir}\n")
    time_evolution = parseCalLocalDirs(local_cal_dir)
    buildEvFigure(time_evolution, plt_variable="sigma", plt_variable_label="sigma", plt_color="firebrick", plt_path="sigma_evolution.pdf")
    buildEvFigure(time_evolution, plt_variable="sigma_row", plt_variable_label="sigma raw", plt_color="darkorange", plt_path="sigmaraw_evolution.pdf")
    buildEvFigure(time_evolution, plt_variable="pedestal", plt_variable_label="pedestal", plt_color="forestgreen", plt_path="pedestal_evolution.pdf")
    buildEvFigure(time_evolution, plt_variable="cn", plt_variable_label="common noise", plt_color="mediumturquoise", plt_path="cn_evolution.pdf")


     

