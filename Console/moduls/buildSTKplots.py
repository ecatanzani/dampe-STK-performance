from datetime import date
from tqdm import tqdm
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib import rcParams
import argparse
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

def readCalDict(file_cal_dict: dict) -> tuple:
    trbs_sigma_mean = []
    trbs_rawsigma_mean = []
    trbs_ped_mean = []
    trbs_cn_mean = []
    ch5_tot = []
    ch5_10_tot = []
    ch10_tot = []
    for trb_value in file_cal_dict:
        tmp_sigma_mean = []
        tmp_sigmaraw_mean = []
        tmp_ped_mean = []
        tmp_cn_mean = []
        ch5 = []
        ch5_10 = []
        ch10 = []
        for ladder_value in file_cal_dict[trb_value]:
            df = pd.read_csv(file_cal_dict[trb_value][ladder_value])
            df.columns=["ch", "va", "chva", "ped", "sigma_raw", "sigma", "status", "status_2", "status_3"]
            df = df.drop(list(range(383, 386)))
            tmp_sigma_mean.append(df['sigma'].mean())
            tmp_sigmaraw_mean.append(df['sigma_raw'].mean())
            tmp_ped_mean.append(df['ped'].mean())
            tmp_cn_mean.append(np.sqrt(pow(tmp_sigmaraw_mean[-1], 2) - pow(tmp_sigma_mean[-1], 2)))
            ch5.append(len(df.query('sigma<5')))
            ch5_10.append(len(df.query('sigma>=5 & sigma<=10')))
            ch10.append(len(df.query('sigma>10')))
        trbs_sigma_mean.append(tmp_sigma_mean)
        trbs_rawsigma_mean.append(tmp_sigmaraw_mean)
        trbs_ped_mean.append(tmp_ped_mean)
        trbs_cn_mean.append(tmp_cn_mean)
        ch5_tot.append(ch5)
        ch5_10_tot.append(ch5_10)
        ch10_tot.append(ch10)
    trbs = [f"TRB0{trb_idx}" for trb_idx in range(8)]
    dict_sigma_mean = [dict(zip(range(len(trbs_sigma_mean[0])), sigmas)) for sigmas in trbs_sigma_mean]
    dict_sigmaraw_mean = [dict(zip(range(len(trbs_rawsigma_mean[0])), sigmas)) for sigmas in trbs_rawsigma_mean]
    dict_ped_mean = [dict(zip(range(len(trbs_ped_mean[0])), sigmas)) for sigmas in trbs_ped_mean]
    dict_cn_mean = [dict(zip(range(len(trbs_cn_mean[0])), sigmas)) for sigmas in trbs_cn_mean]
    dict_ch5 = [dict(zip(range(len(trbs_cn_mean[0])), ch)) for ch in ch5_tot]
    dict_ch5_10 = [dict(zip(range(len(trbs_cn_mean[0])), ch)) for ch in ch5_10_tot]
    dict_ch10 = [dict(zip(range(len(trbs_cn_mean[0])), ch)) for ch in ch10_tot]
    return (dict(zip(trbs, dict_sigma_mean)), dict(zip(trbs, dict_sigmaraw_mean)), dict(zip(trbs, dict_ped_mean)), dict(zip(trbs, dict_cn_mean)), dict(zip(trbs, dict_ch5)), dict(zip(trbs, dict_ch5_10)), dict(zip(trbs, dict_ch10)))

def getMeanValue(valdict: dict) -> float:
    trb_meanvalues = []
    for trb_value in valdict:
        trb_meanvalues.append(np.array(list(valdict[trb_value].values())).mean())
    return np.array(trb_meanvalues).mean()

def getChannelFraction(valdict: dict) -> float:
    ch_ladder = 384
    ch_selected = 0
    for trb_value in valdict:
        for ch_tmp_ladder in valdict[trb_value]:
            ch_selected += valdict[trb_value][ch_tmp_ladder]
    return ch_selected/(ch_ladder*len(valdict)*len(valdict['TRB00']))

def purgeDirs(filelist: list, config:list) -> list:
    purged_filelist = []
    for cal_dir in filelist:
        tmpdate = getDateFromDir(cal_dir)
        if tmpdate >= config['start_date'] and tmpdate <= config['end_date']:
            purged_filelist.append(cal_dir)
    return purged_filelist

def parseCalLocalDirs(local_cal_dir: str, opts: argparse.Namespace, config: dict) -> dict:
    caldate = []
    sigma = []
    sigma_row = []
    ped = []
    cn = []
    chfrac_s5 = []
    chfrac_s510 = []
    chfrac_s10 = []

    local_folders = [f"{local_cal_dir}/{folder}" for folder in os.listdir(local_cal_dir) if folder.startswith('20')]
    local_folders.sort()
    if opts.local:
        local_folders = purgeDirs(local_folders, config)
    if not len(local_folders):
        print('No calibration found matching the selected time window... select a different time interval')
        return {}

    for cal_folder in tqdm(local_folders):
        caldate.append(getDateFromDir(cal_folder))
        ladder_dicts = readCalDict(buildCalDict(cal_folder))
        sigma.append(getMeanValue(ladder_dicts[0]))
        sigma_row.append(getMeanValue(ladder_dicts[1]))
        ped.append(getMeanValue(ladder_dicts[2]))
        cn.append(getMeanValue(ladder_dicts[3]))
        chfrac_s5.append(getChannelFraction(ladder_dicts[4]))
        chfrac_s510.append(getChannelFraction(ladder_dicts[5]))
        chfrac_s10.append(getChannelFraction(ladder_dicts[6]))
    return {'date': caldate, 'sigma': sigma, 'sigma_row': sigma_row, 'pedestal': ped, 'cn': cn, 'chfrac_s5': chfrac_s5, 'chfrac_s510': chfrac_s510, 'chfrac_s10': chfrac_s10}

def buildEvFigure(time_evolution: dict, plt_variable: str, plt_variable_label: str, plt_color: str, xaxis_interval: int, yaxis_title: str, plt_path: str) -> plt.figure:
    fig, ax = plt.subplots(clear=True)
    ax.plot(time_evolution['date'], time_evolution[plt_variable], label=plt_variable_label, color=plt_color)
    if xaxis_interval:
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=xaxis_interval))
        if xaxis_interval<=3:
            ax.xaxis.set_minor_locator(mdates.DayLocator())
        else:
            ax.xaxis.set_minor_locator(mdates.MonthLocator())
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    fig.autofmt_xdate()
    ax.set_ylabel(yaxis_title, fontsize=10)
    plt.savefig(plt_path)
    return fig

def buildChSigmaEv(time_evolution: dict, xaxis_interval: int, plt_path: str) -> plt.figure:
    rcParams.update({'figure.autolayout': True})
    fig, ax = plt.subplots(clear=True)
    #ax.plot(time_evolution['date'], time_evolution['chfrac_s5'], label='ch frac sigma < 5', color='cornflowerblue')
    ax.plot(time_evolution['date'], time_evolution['chfrac_s510'], label='ch frac 5 < sigma < 10', color='sandybrown')
    ax.plot(time_evolution['date'], time_evolution['chfrac_s10'], label='ch frac sigma > 10', color='firebrick')
    if xaxis_interval:
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=xaxis_interval))
        if xaxis_interval<=3:
            ax.xaxis.set_minor_locator(mdates.DayLocator())
        else:
            ax.xaxis.set_minor_locator(mdates.MonthLocator())
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    fig.autofmt_xdate()
    plt.legend(bbox_to_anchor=(1.05, 0.5), loc='center left')
    plt.savefig(plt_path)
    return fig

def buildVariableDistribution(time_evolution: dict, plt_variable: str, bins: int, xrange: tuple) -> plt.figure:
    fig, ax = plt.subplots(clear=True)
    ax.hist(time_evolution[plt_variable], bins, density=True, range=xrange)
    return fig

def buildStkPlots(opts: argparse.Namespace, config: dict):
    local_cal_dir = opts.local if opts.local else "cal"
    if opts.verbose:
        print(f"\nGetting time evolution information from local dir: {local_cal_dir}\n")
    
    xinterval = 6
    time_evolution = parseCalLocalDirs(local_cal_dir, opts, config)
    buildEvFigure(time_evolution, plt_variable="sigma", plt_variable_label="sigma", plt_color="firebrick", xaxis_interval=xinterval, yaxis_title="sigma", plt_path="sigma_evolution.pdf")
    buildEvFigure(time_evolution, plt_variable="sigma_row", plt_variable_label="sigma raw", plt_color="darkorange", xaxis_interval=xinterval, yaxis_title="sigma row", plt_path="sigmaraw_evolution.pdf")
    buildEvFigure(time_evolution, plt_variable="pedestal", plt_variable_label="pedestal", plt_color="forestgreen", xaxis_interval=xinterval, yaxis_title="pedestal" , plt_path="pedestal_evolution.pdf")
    buildEvFigure(time_evolution, plt_variable="cn", plt_variable_label="common noise", plt_color="mediumturquoise", xaxis_interval=xinterval, yaxis_title="common noise", plt_path="cn_evolution.pdf")
    buildEvFigure(time_evolution, plt_variable="chfrac_s5", plt_variable_label="ch frac sigma < 5", plt_color="cornflowerblue", xaxis_interval=xinterval, yaxis_title="channel fraction sigma < 5", plt_path="chfrac_sigma_5.pdf")
    buildEvFigure(time_evolution, plt_variable="chfrac_s510", plt_variable_label="ch frac 5 < sigma < 10", plt_color="sandybrown", xaxis_interval=xinterval, yaxis_title="channel fraction 5 < sigma < 10", plt_path="chfrac_sigma_5_10.pdf")
    buildEvFigure(time_evolution, plt_variable="chfrac_s10", plt_variable_label="ch frac sigma > 10", plt_color="firebrick", xaxis_interval=xinterval, yaxis_title="channel fraction sigma > 10", plt_path="chfrac_sigma_10.pdf")
    buildChSigmaEv(time_evolution, xaxis_interval=xinterval, plt_path="channel_noise_evolution.pdf") 

