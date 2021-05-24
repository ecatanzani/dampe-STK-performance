from datetime import date, timedelta
from tqdm import tqdm
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib import rcParams
from ROOT import TFile, TH1D, TH2D, TProfile, TDatime, TCanvas, gStyle, gROOT, gPad
import argparse
import os
from downloadCal import updateCalFiles, getDateFromDir



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
    all_sigma_values = []
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
            df = pd.read_csv(file_cal_dict[trb_value][ladder_value], header=None)
            df.columns=["ch", "va", "chva", "ped", "sigma_raw", "sigma", "status", "status_2", "status_3"]
            df = df.drop(list(range(383, 386)))
            all_sigma_values += list(df['sigma'])
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
    return (dict(zip(trbs, dict_sigma_mean)), dict(zip(trbs, dict_sigmaraw_mean)), dict(zip(trbs, dict_ped_mean)), dict(zip(trbs, dict_cn_mean)), dict(zip(trbs, dict_ch5)), dict(zip(trbs, dict_ch5_10)), dict(zip(trbs, dict_ch10))), all_sigma_values

def getMeanValue(valdict: dict) -> float:
    trb_meanvalues = []
    for trb_value in valdict:
        trb_meanvalues.append(np.array(list(valdict[trb_value].values())).mean())
    return np.array(trb_meanvalues).mean()

def getValues(valdict: dict) -> list:
    ladder_values = []
    for trb_value in valdict:
        ladder_values += list(valdict[trb_value].values())
    return ladder_values

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

def updateLocalDirs(local_cal_dir: str, local_folders: list, opts: argparse.Namespace, config: dict) -> bool:
    if opts.verbose:
        print("updating local directory calibration files...")
    config['start_date'] = getDateFromDir(local_folders[-1]) + timedelta(days=1)
    return updateCalFiles(config, opts)

def getCalDirList(local_cal_dir: str) -> list:
    local_folders = [f"{local_cal_dir}/{folder}" for folder in os.listdir(local_cal_dir) if folder.startswith('20')]
    local_folders.sort()
    return local_folders

def parseCalLocalDirs(local_cal_dir: str, opts: argparse.Namespace, config: dict) -> dict:
    caldate = []
    sigma = []
    sigma_values = []
    sigma_raw = []
    sigma_raw_values = []
    ped = []
    ped_values = []
    cn = []
    cn_values = []
    chfrac_s5 = []
    chfrac_s510 = []
    chfrac_s10 = []
    chsigmas = []

    local_folders = getCalDirList(local_cal_dir)
    if opts.local:
        if opts.update:
            if updateLocalDirs(local_cal_dir, local_folders, opts, config.copy()):
                local_folders = getCalDirList(local_cal_dir)
            else:
                print(f"Error opdating local calibration folder: [{local_cal_dir}]")
                return {}
        local_folders = purgeDirs(local_folders, config)
    
    if not len(local_folders):
        print('No calibration found matching the selected time window... select a different time interval')
        return {}
    if opts.verbose:
        print("Parsing calibration files...")

    for cal_folder in tqdm(local_folders):
        caldate.append(getDateFromDir(cal_folder))
        ladder_dicts, sigmas = readCalDict(buildCalDict(cal_folder))
        sigma.append(getMeanValue(ladder_dicts[0]))
        sigma_values.append(getValues(ladder_dicts[0]))
        sigma_raw.append(getMeanValue(ladder_dicts[1]))
        sigma_raw_values.append(getValues(ladder_dicts[1]))
        ped.append(getMeanValue(ladder_dicts[2]))
        ped_values.append(getValues(ladder_dicts[2]))
        cn.append(getMeanValue(ladder_dicts[3]))
        cn_values.append(getValues(ladder_dicts[3]))
        chfrac_s5.append(getChannelFraction(ladder_dicts[4]))
        chfrac_s510.append(getChannelFraction(ladder_dicts[5]))
        chfrac_s10.append(getChannelFraction(ladder_dicts[6]))
        chsigmas.append(sigmas)
    return {'date': caldate, 'sigma': sigma, 'sigma_values': sigma_values, 'sigma_raw': sigma_raw, 'sigma_raw_values': sigma_raw_values, 'pedestal': ped, 'pedestal_values': ped_values, 'cn': cn, 'cn_values': cn_values, 'chfrac_s5': chfrac_s5, 'chfrac_s510': chfrac_s510, 'chfrac_s10': chfrac_s10, 'chsigmas': chsigmas}

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

def buildROOThistos(time_evolution: dict, out_filename: str):
    outfile = TFile(out_filename, "RECREATE")
    if not outfile.IsOpen():
        print(f"Error writing output TFile: [{out_filename}]")

    start_time = TDatime(time_evolution['date'][0].year, time_evolution['date'][0].month, time_evolution['date'][0].day, 12, 0, 0).Convert()
    end_time = TDatime(time_evolution['date'][-1].year, time_evolution['date'][-1].month, time_evolution['date'][-1].day, 12, 0, 0).Convert()
    bins = int((end_time-start_time)/86400)
    
    sigma_evolution = TH2D("sigma_evolution", "#sigma time evolution", bins, start_time, end_time, 100, 2, 4)
    sigma_evolution_profile = TProfile("sigma_evolution_profile", "#sigma time evolution - profile", bins, start_time, end_time, 2, 4)

    sigma_raw_evolution = TH2D("sigma_raw_evolution", "#sigma_{raw} time evolution", bins, start_time, end_time, 100, 10, 13)
    sigma_raw_evolution_profile = TProfile("sigma_raw_evolution_profile", "#sigma_{raw} time evolution - profile", bins, start_time, end_time, 10, 13)

    pedestal_evolution = TH2D("pedestal_evolution", "pedestal time evolution", bins, start_time, end_time, 100, 100, 400)
    pedestal_evolution_profile = TProfile("spedestal_evolution_profile", "pedestal time evolution - profile", bins, start_time, end_time, 100, 400)

    cn_evolution = TH2D("cn_evolution", "Common Noise time evolution", bins, start_time, end_time, 100, 9, 13)
    cn_evolution_profile = TProfile("cn_evolution_profile", "Common Noise time evolution - profile", bins, start_time, end_time, 9, 13)

    for idx, ladder_values in enumerate(time_evolution['sigma_values']):
        for single_value in ladder_values:
            tmpdate = TDatime(time_evolution['date'][idx].year, time_evolution['date'][idx].month, time_evolution['date'][idx].day, 12, 0, 0).Convert()
            sigma_evolution.Fill(tmpdate, single_value)
            sigma_evolution_profile.Fill(tmpdate, single_value)
    
    for idx, ladder_values in enumerate(time_evolution['sigma_raw_values']):
        for single_value in ladder_values:
            tmpdate = TDatime(time_evolution['date'][idx].year, time_evolution['date'][idx].month, time_evolution['date'][idx].day, 12, 0, 0).Convert()
            sigma_raw_evolution.Fill(tmpdate, single_value)
            sigma_raw_evolution_profile.Fill(tmpdate, single_value)

    for idx, ladder_values in enumerate(time_evolution['pedestal_values']):
        for single_value in ladder_values:
            tmpdate = TDatime(time_evolution['date'][idx].year, time_evolution['date'][idx].month, time_evolution['date'][idx].day, 12, 0, 0).Convert()
            pedestal_evolution.Fill(tmpdate, single_value)
            pedestal_evolution_profile.Fill(tmpdate, single_value)

    for idx, ladder_values in enumerate(time_evolution['cn_values']):
        for single_value in ladder_values:
            tmpdate = TDatime(time_evolution['date'][idx].year, time_evolution['date'][idx].month, time_evolution['date'][idx].day, 12, 0, 0).Convert()
            cn_evolution.Fill(tmpdate, single_value)
            cn_evolution_profile.Fill(tmpdate, single_value)
    

    sigma_evolution.GetXaxis().SetTimeDisplay(1)
    sigma_evolution.GetXaxis().SetNdivisions(-503)
    sigma_evolution.GetXaxis().SetTimeFormat("%Y-%m-%d")
    sigma_evolution.GetXaxis().SetTimeOffset(0,"gmt")
    sigma_evolution.GetYaxis().SetTitle("#sigma")
    sigma_evolution.SetMarkerStyle(6)

    sigma_evolution_profile.GetXaxis().SetTimeDisplay(1)
    sigma_evolution_profile.GetXaxis().SetNdivisions(-503)
    sigma_evolution_profile.GetXaxis().SetTimeFormat("%Y-%m-%d")
    sigma_evolution_profile.GetXaxis().SetTimeOffset(0,"gmt")
    sigma_evolution_profile.GetYaxis().SetTitle("#sigma")
    sigma_evolution_profile.SetLineWidth(0)
    sigma_evolution_profile.SetMarkerStyle(20)

    sigma_raw_evolution.GetXaxis().SetTimeDisplay(1)
    sigma_raw_evolution.GetXaxis().SetNdivisions(-503)
    sigma_raw_evolution.GetXaxis().SetTimeFormat("%Y-%m-%d")
    sigma_raw_evolution.GetXaxis().SetTimeOffset(0,"gmt")
    sigma_raw_evolution.GetYaxis().SetTitle("#sigma_{raw}")
    sigma_raw_evolution.SetMarkerStyle(6)
    sigma_raw_evolution.GetYaxis().SetTitleOffset(1.3)
    
    sigma_raw_evolution_profile.GetXaxis().SetTimeDisplay(1)
    sigma_raw_evolution_profile.GetXaxis().SetNdivisions(-503)
    sigma_raw_evolution_profile.GetXaxis().SetTimeFormat("%Y-%m-%d")
    sigma_raw_evolution_profile.GetXaxis().SetTimeOffset(0,"gmt")
    sigma_raw_evolution_profile.GetYaxis().SetTitle("#sigma_{raw}")
    sigma_raw_evolution_profile.SetLineWidth(0)
    sigma_raw_evolution_profile.SetMarkerStyle(20)

    pedestal_evolution.GetXaxis().SetTimeDisplay(1)
    pedestal_evolution.GetXaxis().SetNdivisions(-503)
    pedestal_evolution.GetXaxis().SetTimeFormat("%Y-%m-%d")
    pedestal_evolution.GetXaxis().SetTimeOffset(0,"gmt")
    pedestal_evolution.GetYaxis().SetTitle("pedestal")
    pedestal_evolution.SetMarkerStyle(6)
    
    pedestal_evolution_profile.GetXaxis().SetTimeDisplay(1)
    pedestal_evolution_profile.GetXaxis().SetNdivisions(-503)
    pedestal_evolution_profile.GetXaxis().SetTimeFormat("%Y-%m-%d")
    pedestal_evolution_profile.GetXaxis().SetTimeOffset(0,"gmt")
    pedestal_evolution_profile.GetYaxis().SetTitle("pedestal")
    pedestal_evolution_profile.SetLineWidth(0)
    pedestal_evolution_profile.SetMarkerStyle(20)

    cn_evolution.GetXaxis().SetTimeDisplay(1)
    cn_evolution.GetXaxis().SetNdivisions(-503)
    cn_evolution.GetXaxis().SetTimeFormat("%Y-%m-%d")
    cn_evolution.GetXaxis().SetTimeOffset(0,"gmt")
    cn_evolution.GetYaxis().SetTitle("Common Noise")
    cn_evolution.SetMarkerStyle(6)

    cn_evolution_profile.GetXaxis().SetTimeDisplay(1)
    cn_evolution_profile.GetXaxis().SetNdivisions(-503)
    cn_evolution_profile.GetXaxis().SetTimeFormat("%Y-%m-%d")
    cn_evolution_profile.GetXaxis().SetTimeOffset(0,"gmt")
    cn_evolution_profile.GetYaxis().SetTitle("Common Noise")
    cn_evolution_profile.SetLineWidth(0)
    cn_evolution_profile.SetMarkerStyle(20)

    sigma_evolution.Write()
    sigma_evolution_profile.Write()
    sigma_raw_evolution.Write()
    sigma_raw_evolution_profile.Write()
    pedestal_evolution.Write()
    pedestal_evolution_profile.Write()
    cn_evolution.Write()
    cn_evolution_profile.Write()
    
    sigma_distribution_per_day = []
    for idx, chsigma in enumerate(time_evolution['chsigmas']):
        tmpdate = TDatime(time_evolution['date'][idx].year, time_evolution['date'][idx].month, time_evolution['date'][idx].day, 12, 0, 0).Convert()
        tmphisto = TH1D(f"hsigmach_{tmpdate}",f"hsigmach_{tmpdate}", 1000, 0, 100)
        for channel in chsigma:
            tmphisto.Fill(channel)
        tmphisto.GetXaxis().SetTitle('#sigma (ADC)')
        tmphisto.GetYaxis().SetTitle('counts')
        sigma_distribution_per_day.append(tmphisto)

    gStyle.SetLineWidth(3)
    
    canvas_sigma = TCanvas("canvas_sigma", "sigma Time Evolution", 700, 700)
    canvas_sigma.cd()
    sigma_evolution.Draw()
    sigma_evolution.SetStats(0)
    sigma_evolution_profile.Draw("same")
    gPad.Modified()
    gPad.Update()
    sigma_evolution.GetXaxis().SetLabelOffset(0.02)
    sigma_evolution.GetYaxis().SetLabelOffset(0.01)
    canvas_sigma.SetTicks()
    gPad.Modified()
    gPad.Update()

    canvas_sigma_raw = TCanvas("canvas_sigma_raw", "sigma raw Time Evolution", 700, 700)
    canvas_sigma_raw.cd()
    sigma_raw_evolution.Draw()
    sigma_raw_evolution.SetStats(0)
    sigma_raw_evolution_profile.Draw("same")
    gPad.Modified()
    gPad.Update()
    sigma_raw_evolution.GetXaxis().SetLabelOffset(0.02)
    sigma_raw_evolution.GetYaxis().SetLabelOffset(0.01)
    canvas_sigma_raw.SetTicks()
    gPad.Modified()
    gPad.Update()

    canvas_pedestal = TCanvas("canvas_pedestal", "pedestal Time Evolution", 700, 700)
    canvas_pedestal.cd()
    pedestal_evolution.Draw()
    pedestal_evolution.SetStats(0)
    pedestal_evolution_profile.Draw("same")
    gPad.Modified()
    gPad.Update()
    pedestal_evolution.GetXaxis().SetLabelOffset(0.02)
    pedestal_evolution.GetYaxis().SetLabelOffset(0.01)
    canvas_pedestal.SetTicks()
    gPad.Modified()
    gPad.Update()

    canvas_cn = TCanvas("canvas_cn", "Common Noise Time Evolution", 700, 700)
    canvas_cn.cd()
    cn_evolution.Draw()
    cn_evolution.SetStats(0)
    cn_evolution_profile.Draw("same")
    gPad.Modified()
    gPad.Update()
    cn_evolution.GetXaxis().SetLabelOffset(0.02)
    cn_evolution.GetYaxis().SetLabelOffset(0.01)
    canvas_cn.SetTicks()
    gPad.Modified()
    gPad.Update()

    canvas_sigma.Write()
    canvas_sigma_raw.Write()
    canvas_pedestal.Write()
    canvas_cn.Write()

    outfile.mkdir('sigmas')
    outfile.cd('sigmas')
    for histo in sigma_distribution_per_day:
        histo.Write()

    outfile.Close()

def buildStkPlots(opts: argparse.Namespace, config: dict):
    local_cal_dir = opts.local if opts.local else "cal"
    time_evolution = parseCalLocalDirs(local_cal_dir, opts, config)
    if opts.verbose:
        print(f"Getting time evolution information from local dir: {local_cal_dir}")

    xinterval = 6
    buildEvFigure(time_evolution, plt_variable="sigma", plt_variable_label="sigma", plt_color="firebrick", xaxis_interval=xinterval, yaxis_title="sigma", plt_path="sigma_evolution.pdf")
    buildEvFigure(time_evolution, plt_variable="sigma_raw", plt_variable_label="sigma raw", plt_color="darkorange", xaxis_interval=xinterval, yaxis_title="sigma raw", plt_path="sigmaraw_evolution.pdf")
    buildEvFigure(time_evolution, plt_variable="pedestal", plt_variable_label="pedestal", plt_color="forestgreen", xaxis_interval=xinterval, yaxis_title="pedestal" , plt_path="pedestal_evolution.pdf")
    buildEvFigure(time_evolution, plt_variable="cn", plt_variable_label="common noise", plt_color="mediumturquoise", xaxis_interval=xinterval, yaxis_title="common noise", plt_path="cn_evolution.pdf")
    buildEvFigure(time_evolution, plt_variable="chfrac_s5", plt_variable_label="ch frac sigma < 5", plt_color="cornflowerblue", xaxis_interval=xinterval, yaxis_title="channel fraction sigma < 5", plt_path="chfrac_sigma_5.pdf")
    buildEvFigure(time_evolution, plt_variable="chfrac_s510", plt_variable_label="ch frac 5 < sigma < 10", plt_color="sandybrown", xaxis_interval=xinterval, yaxis_title="channel fraction 5 < sigma < 10", plt_path="chfrac_sigma_5_10.pdf")
    buildEvFigure(time_evolution, plt_variable="chfrac_s10", plt_variable_label="ch frac sigma > 10", plt_color="firebrick", xaxis_interval=xinterval, yaxis_title="channel fraction sigma > 10", plt_path="chfrac_sigma_10.pdf")
    buildChSigmaEv(time_evolution, xaxis_interval=xinterval, plt_path="channel_noise_evolution.pdf") 
    buildROOThistos(time_evolution, out_filename="ladder_time_info.root")
