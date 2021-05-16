import matplotlib
from datetime import date
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import date
import streamlit as st
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

def purgeDirs(filelist: list, start_date: date, end_date: date) -> list:
    purged_filelist = []
    for cal_dir in filelist:
        tmpdate = getDateFromDir(cal_dir)
        if tmpdate >= start_date and tmpdate <= end_date:
            purged_filelist.append(cal_dir)
    return purged_filelist


def parseCalLocalDirs(local_cal_dir: str, start_date: date, end_date: date, datecheck: bool) -> dict:
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
    if not datecheck:
        local_folders = purgeDirs(local_folders, start_date, end_date)
    if not len(local_folders):
        st.error('No calibration found matching the selected time window... select a different time interval')
        return {}

    perc_complete = 0.
    step = 1./len(local_folders)
    bar = st.progress(perc_complete)

    for cal_folder in local_folders:
        caldate.append(getDateFromDir(cal_folder))
        ladder_dicts = readCalDict(buildCalDict(cal_folder))
        sigma.append(getMeanValue(ladder_dicts[0]))
        sigma_row.append(getMeanValue(ladder_dicts[1]))
        ped.append(getMeanValue(ladder_dicts[2]))
        cn.append(getMeanValue(ladder_dicts[3]))
        chfrac_s5.append(getChannelFraction(ladder_dicts[4]))
        chfrac_s510.append(getChannelFraction(ladder_dicts[5]))
        chfrac_s10.append(getChannelFraction(ladder_dicts[6]))
        perc_complete += step
        bar.progress(round(perc_complete, 1))
    return {'date': caldate, 'sigma': sigma, 'sigma_row': sigma_row, 'pedestal': ped, 'cn': cn, 'chfrac_s5': chfrac_s5, 'chfrac_s510': chfrac_s510, 'chfrac_s10': chfrac_s10}


def buildEvFigure(time_evolution: dict, plt_variable: str, plt_variable_label: str, plt_color: str, xaxis_interval: int, plt_path: str) -> matplotlib.figure:
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
    plt.savefig(plt_path)
    return fig

def buildChSigmaEv(time_evolution: dict, xaxis_interval: int, plt_path: str) -> matplotlib.figure:
    
    fig, ax = plt.subplots(clear=True)
    ax.plot(time_evolution['date'], time_evolution['chfrac_s5'], label='ch frac sigma < 5', color='cornflowerblue')
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
    plt.savefig(plt_path)
    return fig

def buildVariableDistribution(time_evolution: dict, plt_variable: str, bins: int, xrange: tuple) -> matplotlib.figure:
    fig, ax = plt.subplots(clear=True)
    ax.hist(time_evolution[plt_variable], bins, density=True, range=xrange)
    return fig

def buildStkPlots(local_cal_dir: str, start_date: date , end_date: date, datecheck: bool, plot_sigma: bool, plot_ped: bool, plot_cn: bool, xinterval: int, int_plots: bool):
    
    st.info(f"Processing time evolution information from selected local directory: **{local_cal_dir}**")
    time_evolution = parseCalLocalDirs(local_cal_dir, start_date, end_date, datecheck)
    if len(time_evolution):
        sigma_tev_fig = buildEvFigure(time_evolution, plt_variable="sigma", plt_variable_label="sigma", plt_color="firebrick", xaxis_interval=xinterval, plt_path="sigma_evolution.pdf")
        sigmarow_tev_fig = buildEvFigure(time_evolution, plt_variable="sigma_row", plt_variable_label="sigma raw", plt_color="darkorange", xaxis_interval=xinterval, plt_path="sigmaraw_evolution.pdf")
        ped_tev_fig = buildEvFigure(time_evolution, plt_variable="pedestal", plt_variable_label="pedestal", plt_color="forestgreen", xaxis_interval=xinterval, plt_path="pedestal_evolution.pdf")
        cn_tev_fig = buildEvFigure(time_evolution, plt_variable="cn", plt_variable_label="common noise", plt_color="mediumturquoise", xaxis_interval=xinterval, plt_path="cn_evolution.pdf")
        chfrac_tev_fig = buildChSigmaEv(time_evolution, xaxis_interval=xinterval, plt_path="channel_noise_evolution.pdf")
        chfrac_s5_tev_fig = buildEvFigure(time_evolution, plt_variable="chfrac_s5", plt_variable_label="ch frac sigma < 5", plt_color="cornflowerblue", xaxis_interval=xinterval, plt_path="chfrac_sigma_5.pdf")
        chfrac_s510_tev_fig = buildEvFigure(time_evolution, plt_variable="chfrac_s510", plt_variable_label="ch frac 5 < sigma < 10", plt_color="sandybrown", xaxis_interval=xinterval, plt_path="chfrac_sigma_5_10.pdf")
        chfrac_s10_tev_fig = buildEvFigure(time_evolution, plt_variable="chfrac_s10", plt_variable_label="ch frac sigma > 10", plt_color="firebrick", xaxis_interval=xinterval, plt_path="chfrac_sigma_10.pdf")

        sigma_dist_fig = buildVariableDistribution(time_evolution, plt_variable="sigma", bins = 100, xrange=(2.5,3.5))
        sigmarow_dist_fig = buildVariableDistribution(time_evolution, plt_variable="sigma_row", bins = 100, xrange=(11,12))
        ped_dist_fig = buildVariableDistribution(time_evolution, plt_variable="pedestal", bins = 100, xrange=(221, 222))
        cn_dist_fig = buildVariableDistribution(time_evolution, plt_variable="cn", bins = 100, xrange=(10, 12))

        if plot_sigma:
            st.write("""
        # Sigma evolution""")
            if int_plots:
                st.plotly_chart(sigma_tev_fig, use_container_width=True)
            else:
                st.pyplot(sigma_tev_fig)
            st.write("""
        # Sigma row evolution""")
            if int_plots:
                st.plotly_chart(sigmarow_tev_fig, use_container_width=True)
            else:
                st.pyplot(sigmarow_tev_fig)
            sigma_dist, sigmarow_dist = st.beta_columns(2)
            with sigma_dist:
                st.subheader('sigma distribution')
                if int_plots:
                    st.plotly_chart(sigma_dist_fig, use_container_width=True)
                else:
                    st.pyplot(sigma_dist_fig)
            with sigmarow_dist:
                st.subheader('sigma row distribution')
                if int_plots:
                    st.plotly_chart(sigmarow_dist_fig, use_container_width=True)
                else:
                    st.pyplot(sigmarow_dist_fig)

            st.write("""
        # Channel noise evolution""")
            st.write('Fraction of channels with *sigma > 5 ADC*')
            if int_plots:
                st.plotly_chart(chfrac_s5_tev_fig, use_container_width=True)
            else:
                st.pyplot(chfrac_s5_tev_fig)
            st.write('Fraction of channels with *5 ADC < sigma < 10 ADC*')
            if int_plots:
                st.plotly_chart(chfrac_s510_tev_fig, use_container_width=True)
            else:
                st.pyplot(chfrac_s510_tev_fig)
            st.write('Fraction of channels with *sigma > 10 ADC*')
            if int_plots:
                st.plotly_chart(chfrac_s10_tev_fig, use_container_width=True)
            else:
                st.pyplot(chfrac_s10_tev_fig)
            st.write('Fraction of channels - complete view')
            if int_plots:
                st.plotly_chart(chfrac_tev_fig, use_container_width=True)
            else:
                st.pyplot(chfrac_tev_fig)

        if plot_ped:
            st.write("""
        # Pedestal evolution""")
            if int_plots:
                st.plotly_chart(ped_tev_fig, use_container_width=True)
                st.plotly_chart(ped_dist_fig, use_container_width=True)
            else:
                st.pyplot(ped_tev_fig)
                st.pyplot(ped_dist_fig)
            

        if plot_cn:
            st.write("""
        # Common Noise evolution""")
            st.latex('CN = \sqrt{\sigma_{row}^2 - \sigma^2}')
            if int_plots:
                st.plotly_chart(cn_tev_fig, use_container_width=True)
                st.plotly_chart(cn_dist_fig, use_container_width=True)
            else:
                st.pyplot(cn_tev_fig)
                st.pyplot(cn_dist_fig)
