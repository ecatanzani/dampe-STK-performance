from argparse import ArgumentParser
import sys


def main(args=None):
    parser = ArgumentParser(
        usage="Usage: %(prog)s [options]", description="Plot facility for Skimmed Flight Data")

    parser.add_argument("-l", "--local", type=str, dest='local',
                        help='use local calibration directory')
    parser.add_argument("-v", "--verbose", dest='verbose', default=False,
                        action='store_true', help='run in high verbosity mode')
    opts = parser.parse_args(args)

    # Load analysis functions
    sys.path.append("moduls")
    from configParser import parseConfigFile
    from downloadCal import getCalFiles
    from buildSTKplots import buildStkPlots

    # Get dictionary from config file parsing
    pars = parseConfigFile()
    status = True
    if not opts.local:
        # Download cal files
        status = getCalFiles(pars, opts)
    if status:
        buildStkPlots(opts, pars)

if __name__ == '__main__':
    main()
