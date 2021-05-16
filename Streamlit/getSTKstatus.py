import streamlit as st
from downloadCal import getCalFiles
from buildSTKplots import buildStkPlots

def appSettings() -> tuple:
    st.write("""
    # DAMPE STK status monitor
    Monitoring DAMPE STK performances in a selected time window
    """)
    st.sidebar.write('**Settings**')
    start_date = st.sidebar.date_input("Start date", help="Select the calibration start date")
    end_date = st.sidebar.date_input("End date", help="Select the calibration end date")
    data_storage_opt = st.sidebar.selectbox('Choose how to get calibration files', ("Download through XROOTD", 'Use local dir'), index=1)
    status = False
    datecheck = False
    return (start_date, end_date, data_storage_opt, status, datecheck)

def plotSettings() -> tuple:
    st.sidebar.write('**Plot options**')
    live_plots = st.sidebar.checkbox('Use interactive plots', value=True)
    plot_sigmas = st.sidebar.checkbox('Plot sigma & sigma row', value=True)
    plot_pedestal = st.sidebar.checkbox('Plot pedestal', value=True)
    plot_cn = st.sidebar.checkbox('Plot Common Noise', value=True)
    xinterval = st.sidebar.slider('X axis interval', min_value = 0, max_value=6, value=1, help='Plots X axis interval in months')
    return (plot_sigmas, plot_pedestal, plot_cn, xinterval, live_plots)

def main():
    st.set_page_config(layout="wide")
    start_date, end_date, data_storage_opt, status, datecheck = appSettings()
    if data_storage_opt == "Download through XROOTD":
        xrootd_entrypoint = st.sidebar.text_input('XROOTD DAMPE entrypoint:', "root://xrootd-dampe.cloud.ba.infn.it//")
        calib_xrdfs_path = st.sidebar.text_input('XROOTD DAMPE calibration files:', "/FM/FlightData/CAL/STK/")
        plot_sigmas, plot_pedestal, plot_cn, xinterval, int_plots = plotSettings()
        config = {"farmAddress": xrootd_entrypoint,  "cal_XRDFS_path": calib_xrdfs_path, "start_date": start_date, "end_date": end_date}
        local_cal_dir = "cal"
        if st.sidebar.button("Start Analysis"):
            if (getCalFiles(config)):
                st.balloons()
                status = True
                datecheck = True
    else:
        local_cal_dir = st.sidebar.text_input("Please, select the calibration directory:", "cal", help="Select the local calibration directory")
        plot_sigmas, plot_pedestal, plot_cn, xinterval, int_plots = plotSettings()
        if st.sidebar.button("Start Analysis"):
            status = True

    if status:
        buildStkPlots(local_cal_dir, start_date, end_date, datecheck, plot_sigmas, plot_pedestal, plot_cn, xinterval, int_plots)

if __name__ == "__main__":
    main()