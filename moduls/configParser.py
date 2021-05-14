from datetime import date

def parseConfigFile():
	dConfig = {'farmAddress': "", 'cal_XRDFS_path': "", 'start_date': date(1,1,1), 'end_date': date(1,1,1)}
	
	config_params = []
	with open("skim_xrootd.conf", "r") as _config:
		for line in _config:
			for word in line.split():
				config_params.append(word)

	for idx, word in enumerate(config_params):
		if word == "farmAddress":
			dConfig['farmAddress'] = config_params[idx+1]
		if word == "cal_XRDFS_path":
			dConfig['cal_XRDFS_path'] = config_params[idx+1]
		if word == "start_year":
			year = int(config_params[idx+1])
		if word == "start_month":
			month = int(config_params[idx+1])
		if word == "start_day":
			day = int(config_params[idx+1])
			dConfig['start_date'] = date(year, month, day)
		if word == "end_year":
			year = int(config_params[idx+1])
		if word == "end_month":
			month = int(config_params[idx+1])
		if word == "end_day":
			day = int(config_params[idx+1])
			dConfig['end_date'] = date(year, month, day)

	return dConfig