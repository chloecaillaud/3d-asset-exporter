from app import App
import sys

# commandline syntax:
# ./assetExporter.py [-path <path>] [--print-paths]

# default values
basepath = None
printPaths = False

# remove first arg (ie path to program), pre-process the rest
arguments = list(map(lambda arg: arg.strip(), sys.argv[1:]))
# set values
try:
	if '-path' in arguments:
		basepath = arguments[arguments.index('-path') + 1]
	if '--print-paths' in arguments:
		printPaths = True
except IndexError:
	pass

app = App(basepath, printPaths)
app.mainloop()