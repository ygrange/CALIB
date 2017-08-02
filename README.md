# CALIB image pipeline demonstrator 
CALIB has been used as a toy pipeline in several projects. This is a working repo to have a central place where I keep it

# Practical things

When you have configured the paths for the files in the config file and you essentially want to list all the files in a directory to process, you can use the following command to get the file list in the expected format (NB: for calibrator, replace 'target' by 'calibrator').

`ls | awk '{print "\"%(target_path)s/" $1 "\"" }' | paste -sd,`
