from fileManager import FileManager
from objAnalizer import ObjAnalyzer
from customComponents import *
from PIL import Image
import customtkinter
import os
import gc

# since app is intended to be run in a different working dir, CURRENT_FILE_DIR is needed for accessing certain data
CURRENT_FILE_DIR = os.path.dirname(os.path.abspath(__file__))

# app
class App(customtkinter.CTk):
	def __init__(self, basepath: PathLike[str] | str | None = None, printPaths: bool = False) -> None:
		super().__init__()
		
		# init external file related systems
		self.fileManager = FileManager(basepath or './', os.path.join(CURRENT_FILE_DIR, './settings/dirLayout.json'), os.path.join(CURRENT_FILE_DIR, './settings/presetSettings.json'))

		objFilePath = self.fileManager.getFilePath(endsWith='.obj')
		if objFilePath != None:
			self.objAnalyzer = ObjAnalyzer(objFilePath, os.path.join(self.fileManager.outputDir, 'obj_stats.txt'))

		# define theme
		customtkinter.set_appearance_mode('system')
		customtkinter.set_default_color_theme('blue')
		self.customColors = self.fileManager.getCustomColors(os.path.join(CURRENT_FILE_DIR, './settings/customColors.json'))

		# define default dim
		self.defaultDim = '400x500'
		self.geometry(self.defaultDim)
		self.resizable(True, True)
		
		# set info
		self.title('asset exporter')

		# initalize all other vars
		self.currentMainFrame = None
		self.selectedPresets = []
		self.prevSteps = []

		self.interuptTransferBarUpdate = False
		self.maxExportJobCount = 0
		self.exportJobCount = 0

		# print debug info if specified
		if printPaths:
			print(f'base path: {os.path.abspath(self.fileManager.basePath)}')
			print(f'output path: {os.path.abspath(self.fileManager.outputDir)}')

		# display first window content
		self.displayPresetSelect()

#---
# main window contents

	def displayPresetSelect(self) -> None:
		self.resetMainFrame()
		self.geometry('400x500')

		# top label
		self.components['titleLabel'] = customtkinter.CTkLabel(master=self.currentMainFrame, text='select desired presets.')
		self.components['titleLabel'].grid(column=0, row=0, padx=10, pady=10, sticky='new')
		self.currentMainFrame.columnconfigure(0, weight=1)

		# checkboxes
		self.components['checkboxes'] = CheckboxGroupComponent(self.currentMainFrame, self.fileManager.presets)
		self.components['checkboxes'].grid(column=0, row=1, padx=10, pady=0, sticky='nsew')
		self.currentMainFrame.rowconfigure(1, weight=1)

		# set the checkboxes previously selected
		if len(self.selectedPresets) != 0:
			self.components['checkboxes'].set(self.selectedPresets)
			self.selectedPresets.clear()

		# bottom buttons
		self.components['actionButtons'] = ConfirmCancelComponent(self.currentMainFrame, self.cancelButtonCB, self.presetSelConfirmCB, self.customColors['grayButton'], self.customColors['blueButton'])
		self.components['actionButtons'].grid(column=0, row=2, padx=10, pady=(0,10), sticky='se')

#-
	def displayOverview(self) -> None:
		self.resetMainFrame()
		self.geometry('800x500')
		
		# top label
		self.components['titleLabel'] = customtkinter.CTkLabel(master=self.currentMainFrame, text='overview')
		self.components['titleLabel'].grid(column=0, row=0, padx=10, pady=10, sticky='new')
		self.currentMainFrame.columnconfigure(0, weight=1)

		# top buttons
		self.components['titleFrame'] = customtkinter.CTkFrame(master=self.currentMainFrame, fg_color='transparent')
		self.components['titleFrame'].grid(column=0, row=0, padx=10, pady=10, sticky='ne')
		# open dir button
		self.components['openDirButton'] = OpenDirBottonComponent(self.components['titleFrame'], os.path.abspath(self.fileManager.basePath), buttonTheme=self.customColors['grayButton'])
		self.components['openDirButton'].grid(column=1, row=0, padx=10, pady=10, sticky='ne')
		# reload button
		icon_reload = customtkinter.CTkImage(light_image=Image.open(os.path.join(CURRENT_FILE_DIR, './images/icon_reload_light.png')), dark_image=Image.open(os.path.join(CURRENT_FILE_DIR, './images/icon_reload_dark.png')), size=(16,16))
		self.components['reloadButton'] = customtkinter.CTkButton(master=self.components['titleFrame'], width=32, text= '', image=icon_reload, command=self.reloadDisplayOverviewCB)
		self.components['reloadButton'].configure(True, **self.customColors['grayButton'])
		self.components['reloadButton'].grid(column=2, row=0, padx=10, pady=10, sticky='ne')

		# per preset tabs
		self.components['tabs'] = TabsComponent(self.currentMainFrame, self.selectedPresets, (len(self.selectedPresets)*32*2, 32*2))
		self.components['tabs'].grid(column=0, row=1, padx=10, pady=0, sticky='nsew')
		self.currentMainFrame.rowconfigure(1, weight=1)

		# tab content
		for preset in self.selectedPresets:
			data = self.fileManager.getPresetFileData(preset)
			tab  = self.components['tabs'].getTab(preset)

			summary = SummaryComponent(tab, data, 32)
			summary.grid(column=0, row=0, padx=0, pady=0, sticky='nsew')

		# bottom buttons
		self.components['actionButtons'] = ConfirmCancelComponent(self.currentMainFrame, self.cancelButtonCB, self.overviewConfirmCB, self.customColors['grayButton'], self.customColors['blueButton'])
		self.components['actionButtons'].grid(column=0, row=2, padx=10, pady=(0,10), sticky='se')

#-
	def displayTransferProgress(self) -> None:
		self.resetMainFrame()
		self.geometry('400x200')
		
		# top label
		self.components['titleLabel'] = customtkinter.CTkLabel(master=self.currentMainFrame, text='copying')
		self.components['titleLabel'].grid(column=0, row=0, padx=10, pady=10, sticky='new')
		self.currentMainFrame.columnconfigure(0, weight=1)

		# progress bar
		self.components['progressBar'] = customtkinter.CTkProgressBar(self.currentMainFrame)
		self.components['progressBar'].grid(column=0, row=1, padx=50, pady=0, sticky='ew')
		self.currentMainFrame.rowconfigure(1, weight=1)
		
		# start transfering files
		for preset in self.selectedPresets:
			self.fileManager.exportFiles(preset)
		self.maxExportJobCount = self.fileManager.getActiveJobCount()
		
		# go straight to complete if no files to transfer
		# TODO: change to a warning window instead
		# TODO: make objAnalyzer async and await on progress bar completion
		if self.maxExportJobCount != 0:
			self.updateTransferBarLoop()
			if hasattr(self, 'objAnalyzer'):
				self.objAnalyzer.run()
		else:
			if hasattr(self, 'objAnalyzer'):
				self.objAnalyzer.run()
			self.transferCompleteCB()

#-
	def displayPostTransferReport(self) -> None:
		# prep data
		failedCategories = set()
		for job in self.fileManager.failedJobs:
			# get the lowest level output dir name, ie: output categories
			failedCategories.add(job.args[2].split('/')[-2])

		hasNoFailures = bool(len(failedCategories) == 0)

		# create window
		self.resetMainFrame()

		if hasNoFailures:
			self.geometry('300x150')
		else:
			self.geometry('300x300')
		
		# top label
		self.components['titleLabel'] = customtkinter.CTkLabel(master=self.currentMainFrame, text='transfer complete.')
		self.components['titleLabel'].grid(column=0, row=0, padx=10, pady=10, sticky='new')
		self.currentMainFrame.columnconfigure(0, weight=1)

		if hasNoFailures:
			# checkmark icon
			icon_check = customtkinter.CTkImage(Image.open(os.path.join(CURRENT_FILE_DIR, './images/icon_checkmark.png')), size=(32,32))
			self.components['statusIcon'] = customtkinter.CTkLabel(master=self.currentMainFrame, text='', image=icon_check)
			self.components['statusIcon'].grid(column=0, row=1, padx=10, pady=0, sticky='ns')
			self.currentMainFrame.rowconfigure(1, weight=1)
		else:
			# get transfer failure report
			# report title label
			icon_warn = customtkinter.CTkImage(Image.open(os.path.join(CURRENT_FILE_DIR, './images/icon_warn.png')), size=(16,16))
			self.components['reportTitle'] = TextWithImageComponent(self.currentMainFrame, 'One or more items failed to copy \nin the following categories: \n See console for details.', icon_warn, 32)
			self.components['reportTitle'].grid(column=0, row=1, padx=10, pady=0, sticky='s')
			# list of failed categories
			self.components['reportBody'] = TextListComponent(self.currentMainFrame, failedCategories)
			self.components['reportBody'].grid(column=0, row=2, padx=20, pady=0, sticky='new')
			self.currentMainFrame.rowconfigure(2, weight=1)

		self.components['actionButtons'] = customtkinter.CTkButton(master=self, text='ok', command=self.destroy)
		self.components['actionButtons'].grid(column=0, row=3, padx=100, pady=10, sticky='sew')

#---
# button callbacks

	def cancelButtonCB(self) -> None:
		""" display previous window content.
		exits program if no previous step.
		"""
		try:
			step = self.prevSteps.pop()
			step()
		except:
			# if empty close app
			self.destroy()

#-
	def presetSelConfirmCB(self) -> None:
		# gather user selections
		self.selectedPresets = self.components['checkboxes'].get()

		if(len(self.selectedPresets) == 0):
			# warn when no selection
			InfoModalWindow(self, 'no item selected')
		else:
			# display next window content
			self.prevSteps.append(self.displayPresetSelect)
			self.displayOverview()

#-
	def overviewConfirmCB(self) -> None:
		# display next window content
		self.prevSteps.append(self.displayOverview)
		self.displayTransferProgress()
		# TODO: add condition if no files to transfer

#---
# non button callbacks

	def transferCompleteCB(self) -> None:
		# wait for obj file to be analized
		if hasattr(self, 'objAnalyzer'):
			self.components['progressBar'].set(1)
			self.objAnalyzer.awaitCompletion()

		self.prevSteps.append(self.displayTransferProgress)
		self.displayPostTransferReport()

#-
	def reloadDisplayOverviewCB(self)-> None:
		""" reloads all files and recalculates preset reqs,
		then updates ui.
		"""

		self.fileManager.reloadInputFiles()
		self.displayOverview()

#---
# other non display functions

	def resetMainFrame(self) -> None:
		""" resets the main window content. """

		if(self.currentMainFrame != None):
			self.currentMainFrame.destroy()
		# de-ref sub components and clear them from mem
		self.components = {}
		gc.collect()

		# initialize new frame
		self.currentMainFrame = customtkinter.CTkFrame(master=self, fg_color='transparent')
		# outer layout
		self.currentMainFrame.grid(column=0, row=0, padx=0, pady=0, sticky='nsew')
		self.columnconfigure(0, weight=1)
		self.rowconfigure(0, weight=1)

#-
	def updateTransferBarLoop(self) -> None:
		""" loop for progress bar. """

		if self.interuptTransferBarUpdate is True:
			# reset value and exit loop
			self.interuptTransferBarUpdate = False
			return
		
		self.exportJobCount = self.fileManager.pollFinishedJobs()

		self.components['progressBar'].set((self.maxExportJobCount - self.exportJobCount) / self.maxExportJobCount)

		if self.exportJobCount == 0:
			self.transferCompleteCB()
		else:
			self.after(500, self.updateTransferBarLoop)