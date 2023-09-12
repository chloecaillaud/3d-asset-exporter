from PIL import Image
import customtkinter
import subprocess
import platform
import shlex
import os

# import type defs
from fileDataClasses import FileCategory, PresetFileCollectionData
from collections.abc import Iterable
from customtkinter import CTkImage
from customtkinter import CTkFrame
from typing import Callable, Any
from os import PathLike

# since app is intended to be run in a different working dir, CURRENT_FILE_DIR is needed for accessing certain data
CURRENT_FILE_DIR = os.path.dirname(os.path.abspath(__file__))

# custom components for customtkinter
#---------------------------------------------------------------------------------------------------
class ConfirmCancelComponent(CTkFrame):
	def __init__(self, master: Any, cancelCB: Callable, confirmCB: Callable, cancelButtonTheme: dict | None = None, confirmButtonTheme: dict | None = None) -> None:
		super().__init__(master=master, fg_color='transparent')
		
		# cancel button
		self.cancelButton = customtkinter.CTkButton(master=self, text='cancel', command=cancelCB)
		if cancelButtonTheme != None:
			self.cancelButton.configure(True, **cancelButtonTheme)
		self.cancelButton.grid(column=1, row=0, padx=(0,5), pady=10, sticky='ew')
		# confirm button
		self.confirmButton = customtkinter.CTkButton(master=self, text='confirm', command=confirmCB)
		if confirmButtonTheme != None:
			self.confirmButton.configure(True, **confirmButtonTheme)
		self.confirmButton.grid(column=2, row=0, padx=(5,0), pady=10, sticky='ew')
		# layout
		self.columnconfigure(0, weight=2)
		self.columnconfigure((1,2), weight=1, minsize=100)
		self.rowconfigure(0, weight=1, minsize=32)

#---------------------------------------------------------------------------------------------------
class OpenDirBottonComponent(customtkinter.CTkButton):
	def __init__(self, master: Any, dir: PathLike[str] | str, imageSize: int = 16, buttonTheme: dict = None) -> None:
		self.targetDir = dir
		self.imageSize = imageSize
		self.icon = CTkImage(light_image=Image.open(os.path.join(CURRENT_FILE_DIR, './images/icon_folder_light.png')), dark_image=Image.open(os.path.join(CURRENT_FILE_DIR, './images/icon_folder_dark.png')), size=(self.imageSize,self.imageSize))

		# create the button
		super().__init__(master=master, text= '', width=imageSize*2, image=self.icon, command=self.openDir)
		self.configure(True, **buttonTheme)

#---
	def openDir(self) -> None:
		# process differs based on platform
		if platform.system() == "Windows":
			subprocess.Popen(shlex.split(f'explorer "{self.targetDir}"'))
		elif platform.system() == "Darwin":
			subprocess.Popen(shlex.split(f'open "{self.targetDir}"'))
		elif platform.system() == "Linux":
			subprocess.Popen(shlex.split(f'xdg-open "{self.targetDir}"'))
		else:
			raise Exception('unsupported system/OS.')

#---------------------------------------------------------------------------------------------------
class CheckboxGroupComponent(CTkFrame):
	def __init__(self, master: Any, values: Iterable[str]) -> None:
		super().__init__(master=master)

		# wrap in another frame for additional padding
		# NOTE: feels redundent, however it was the only way to optain the look needed
		self.innerFrame = CTkFrame(master=self, fg_color='transparent')
		self.innerFrame.grid(column=0, row=0, padx=10, pady=10, sticky='nsew')
		self.columnconfigure(0, weight=1)
		self.rowconfigure(0, weight=1)

		#create a checkboxes for each value
		self.checkboxes = {}
		for i, valueName in enumerate(values):
			self.checkboxes[valueName] = customtkinter.CTkCheckBox(master=self.innerFrame, text=valueName)
			self.checkboxes[valueName].grid(column=0, row=i, padx=10, pady=10, sticky='nw')

		self.innerFrame.columnconfigure(0, weight=1)

#---
	def get(self, boxName: str | None  = None) -> list[customtkinter.CTkCheckBox] | bool | None:
		""" get status of a checkbox by its name or from all checkboxes if boxName is None. """
		if boxName == None:
			# get list of all checked
			checked = []
			for box in self.checkboxes:
				if self.checkboxes[box].get() == 1:
					checked.append(box)
			return checked

		else:
			# get specified box's value
			try:
				if self.checkboxes[boxName].get() == 1:
					return True
				else:
					return False
			except:
				# if doesnt exist
				return None

#---
	def set(self, boxName: str | Iterable[str]) -> None:
		""" sets the status of checkbox(es). """
		if isinstance(boxName, str):
			self.checkboxes[boxName].select()
		else:
			for box in boxName:
				self.checkboxes[box].select()

#---------------------------------------------------------------------------------------------------
class TextListComponent(CTkFrame):
	def __init__(self, master: Any, textList: list[str]) -> None:
		super().__init__(master=master)

		#create a label per value
		self.labels = {}
		for i, text in enumerate(textList):
			self.labels[text] = customtkinter.CTkLabel(master=self, text=text)
			self.labels[text].grid(column=0, row=i, padx=10, pady=10, sticky='new')
			
		self.columnconfigure(0, weight=1)

#---------------------------------------------------------------------------------------------------
class TabsComponent(customtkinter.CTkTabview):
	def __init__(self, master: Any, names: Iterable[str], minDim: int) -> None:
		super().__init__(master=master)
		
		self.tabNames = names

		# create a tab per name
		for tabName in self.tabNames:
			self.add(tabName)
			tab = self.tab(tabName)
			tab.columnconfigure(0, weight=1, minsize=minDim[1])
			tab.rowconfigure(0, weight=1, minsize=minDim[0])

#---
	def getTab(self, id: int | str) -> CTkFrame:
		""" get tab ref from either its index or name. """
		if isinstance(id, int):
			return self.tab(self.tabNames[id])
		elif isinstance(id, str):
			return self.tab(id)
		else:
			raise TypeError(f'{type(id)} is not a valid type for id')

#---------------------------------------------------------------------------------------------------
class SummaryComponent(CTkFrame):
	def __init__(self, master: Any, presets: FileCategory, imgSize: int = 32) -> None:
		super().__init__(master=master, fg_color='transparent')
		
		self.imageSize = imgSize
		self._frameNum = 0
		self._rowNum = 0

		# get the pass fail icons
		self.icon_check = CTkImage(Image.open(os.path.join(CURRENT_FILE_DIR, './images/icon_checkmark.png')), size=(self.imageSize/2,self.imageSize/2))
		self.icon_cross = CTkImage(Image.open(os.path.join(CURRENT_FILE_DIR, './images/icon_X.png')),         size=(self.imageSize/2,self.imageSize/2))

		self.rowconfigure(0, weight=1)

		for presetData in presets.children:
			# outer layout
			self.columnconfigure(self._frameNum, weight=1, minsize=self.imageSize)

			# frame
			frame = customtkinter.CTkScrollableFrame(master=self, label_text=presetData.name, fg_color= customtkinter.ThemeManager.theme["CTk"]["fg_color"])
			frame.grid(column=self._frameNum, row=0, padx=5, pady=10, sticky='nsew')
			frame.columnconfigure(0, weight=1, minsize=self.imageSize)
			self._frameNum += 1

			# create the formated list of passing and failing ext
			self._rowNum = 1
			self._summaryFromPresetData(presetData, frame, 1)

		# reset incremental values
		self._frameNum = 0
		self._rowNum = 0

#---
	def _summaryFromPresetData(self, presetData: FileCategory | PresetFileCollectionData, master: CTkFrame, depth) -> None:
		if isinstance(presetData, FileCategory):
			self._addHeading(master, presetData.name, depth)
			presetData.foreach(self._summaryFromPresetData, master, depth + 1)
		if isinstance(presetData, PresetFileCollectionData):
			if presetData.requiredSuffixes == None:
				self._addExts(master, presetData, None, depth)
			else:
				self._addHeading(master, presetData.name, depth)
				for suffix in presetData.requiredSuffixes:
					self._addHeading(master, suffix, depth + 1)
					self._addExts(master, presetData, suffix, depth + 2)

#---
	def _addExts(self, master: Any, presetData: PresetFileCollectionData, suffix: str | None = None, depth: int = 0) -> None:
		""" creates an indented row of all ext in a category. """
		# add items for passing ext
		for ext in presetData.getPassingExt():
			# get number of occurneces of ext in files
			fileCount = 0
			for file in presetData.getFilterdFiles(suffix):
				if file.endswith(ext):
					fileCount += 1

			self._addTextImgItem(master, f'{ext} ({str(fileCount)})', self.icon_check, depth)
		
		# add items for failing ext
		for ext in presetData.getFailingExt():
			self._addTextImgItem(master, f'{ext} (0)', self.icon_cross, depth)

#---
	def _addTextImgItem(self, master: Any, text: str, img: CTkImage, depth: int = 1)-> None:
		""" add indentable TextWithImageComponent. """
		item = TextWithImageComponent(master, text, img, self.imageSize)
		# layout
		item.grid(column=0, row=self._rowNum, padx=(depth*8,4), pady=2, sticky='nw')
		master.rowconfigure(self._rowNum, minsize=self.imageSize+4)

		self._rowNum += 1

#---
	def _addHeading(self, master: Any, text: str, depth: int = 1)-> None:
		""" add indentable heading. """
		frame = CTkFrame(master=master, fg_color='transparent')
		frame.grid(column=0, row=self._rowNum, padx=(depth*8,4), pady=2, sticky='nw')

		heading = customtkinter.CTkLabel(master=frame, text=text)
		heading.grid(column=0, row=0, padx=4, pady=2, sticky='nsw')

		frame.columnconfigure(0, minsize=self.imageSize+4)
		frame.rowconfigure(0, weight=1, minsize=self.imageSize+4)

		master.rowconfigure(self._rowNum, minsize=self.imageSize+4)
		self._rowNum += 1


#---------------------------------------------------------------------------------------------------
class TextWithImageComponent(CTkFrame):
	def __init__(self, master: Any, text: str, image: CTkImage, size: int)-> None:
		super().__init__(master=master, fg_color='transparent')

		self.frameSize = size
		self.image = image
		self.text = text

		# img
		self.imageComponent = customtkinter.CTkLabel(master=self, text='', image=self.image)
		self.imageComponent.grid(column=0, row=0, padx=(4,self.frameSize/2), pady=2, sticky='nsw')
		# text
		self.textComponent  = customtkinter.CTkLabel(master=self, text=self.text)
		self.textComponent.grid(column=1, row=0, padx=(0,4), pady=2, sticky='nsw')
		# layout
		self.columnconfigure((0,1), weight=1, minsize=int(self.frameSize*1.5+8))
		self.rowconfigure(0, weight=1, minsize=self.frameSize+4)

#---
	def setImage(self, newImg: CTkImage)-> None:
		self.image = newImg
		self.imageComponent.configure(image=self.image)

#---
	def setText(self, newText: str) -> None:
		self.text = newText
		self.textComponent.configure(text=self.text)

#---------------------------------------------------------------------------------------------------
class InfoModalWindow(customtkinter.CTkToplevel):
	def __init__(self, parent: Any, text: str) -> None:
		self.parent = parent

		# 'disable' main window
		self.parent.wm_attributes('-disable', True)
		
		super().__init__()
		self.geometry(self.__getGeomtryString(300, 120))
		self.resizable(False, False)
		self.title('info')

		# redirect focus to modal when attemting to return to main window
		self.transient(master=self.parent)

		# text and img frame
		self.msgFrame = CTkFrame(master=self, fg_color='transparent')
		self.msgFrame.grid(column=0, row=0, padx=20, pady=10, sticky='new')
		# img
		self.image = customtkinter.CTkImage(Image.open(os.path.join(CURRENT_FILE_DIR, './images/icon_info.png')), size=(32,32))
		self.imageComponent = customtkinter.CTkLabel(master=self.msgFrame, text='', image=self.image, )
		self.imageComponent.grid(column=0, row=0, padx=0, pady=0, sticky='ns')
		# text
		self.msgLabel = customtkinter.CTkLabel(master=self.msgFrame, text=text, height= 50)
		self.msgLabel.cget('font').configure(size=20, weight='bold')
		self.msgLabel.grid(column=1, row=0, padx=0, pady=0, sticky='nsew')
		# frame layout
		self.msgFrame.columnconfigure(0, minsize=64)
		self.msgFrame.columnconfigure(1, weight=1)
		self.msgFrame.rowconfigure(0, weight=1)

		# button
		self.okButton = customtkinter.CTkButton(master=self, text='ok', command=self.close)
		self.okButton.grid(column=0, row=1, padx=20, pady=10, sticky='s')

		# layout
		self.columnconfigure(0, weight=1)
		self.rowconfigure(0, weight=3)
		self.rowconfigure(1, weight=1)

		# bind windows deletion to the close func
		self.protocol('WM_DELETE_WINDOW', self.close)

#---
	def close(self) -> None:
		# re 'enable' main window
		self.parent.wm_attributes('-disable', False)
		self.destroy()

#---
	def __getGeomtryString(self, width: int, height: int) -> str:
		""" returns the position and dims for the window relative to the parent. """
		xPos = int(self.parent.winfo_x() + (self.parent.winfo_width()  / 2))
		yPos = int(self.parent.winfo_y() + (self.parent.winfo_height() / 2))

		return f'{width}x{height}+{xPos}+{yPos}'