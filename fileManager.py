import subprocess
import platform
import json
import os

from fileDataClasses import *

# import type defs
from collections.abc import Iterable
from subprocess import Popen
from os import PathLike

#---------------------------------------------------------------------------------------------------
class FileManager():
	def __init__(self, basePath: PathLike, dirSettingsPath: PathLike, presetsSettingsPath: PathLike) -> None:
		
		# paths
		self.basePath = basePath
		self.dirSettingsPath = dirSettingsPath
		self.presetsSettingsPath = presetsSettingsPath

		# input/output dirs
		dirSettings = self.__fetchJsonData(self.dirSettingsPath)
		self.outputDir = dirSettings.pop('output', './tmp/')
		self.inputDirs = dirSettings
		# presets
		self.presets = self.__fetchJsonData(self.presetsSettingsPath)

		# init other vars
		self.exportJobs = []
		self.successfullJobs = []
		self.failedJobs = []

		# generates self.files struct
		self.createinputFiles()

#---
# input data management

	def createinputFiles(self) -> None:
		""" generate the self.files structure, and popuate it. \n
		structure format: FileCategory[FileCollection | FileCategory[FileCollection]] \n
		"""

		self.files = FileCategory('inputFiles')
		for directory in self.inputDirs:
			if(type(self.inputDirs[directory]) is str):
			# no sub-categories
				self.files.add(FileCollection(directory, os.path.normpath(self.inputDirs[directory]), []))
			else:
			# with sub-categories
				childCategory = FileCategory(directory)
				self.files.add(childCategory)
				for subDir in self.inputDirs[directory]:
				# same as above, just one level down
					childCategory.add(FileCollection(subDir, os.path.normpath(self.inputDirs[directory][subDir]), []))

		self.reloadInputFiles()

#-
	def reloadInputFiles(self) -> None:
		""" (re)loads all data relating to the input files. \n
		NOTE: changes to dir layout will not be accounted for
		"""

		# sub function
		@staticmethod
		def _populateCollections(collection, basePath) -> None:
			if isinstance(collection, FileCollection):
				# get entries from dir
				allEntries = os.listdir(os.path.join(basePath, collection.dirPath))
				# filter out non file entries (ie: subdir)
				collection.replaceFiles([entry for entry in allEntries if os.path.isfile(os.path.join(basePath, collection.dirPath, entry))])
		
		# main function
		self.files.foreachRecursive(_populateCollections, self.basePath)

#---
# file searching
	def getFilePath(self, startsWith: str | None = None, endsWith: str | None = None, contains: str | None = None) -> PathLike[str] | str | None:
		""" searches gathered input files for specific match. \n
		returns the first match.
		"""

		# sub function
		@staticmethod
		def _matchFile(fileData: FileDataType, startsWith: str | None = None, endsWith: str | None = None, contains: str | None = None) -> PathLike[str] | str | None:
			# get files
			if isinstance(fileData, FileCollection):
				files = fileData.files
				basePath = fileData.dirPath
			elif isinstance(fileData, PresetFileCollectionData):
				files = fileData.fileCollection.files
				basePath = fileData.fileCollection.dirPath
			else:
				return None

			# find matching file
			for fileName in files:
				if startsWith != None and fileName.startswith(startsWith) != True:
					continue
				if endsWith != None and fileName.endswith(endsWith) != True:
					continue
				if contains != None and fileName.find(contains) == -1:
					continue
				# if passes all req return
				return os.path.join(basePath, fileName)

			return None

		# main function
		if startsWith == None and endsWith == None and contains == None:
			raise ValueError('at least one of the following arguments must be specified: startsWith, EndsWith, Contains')

		return self.files.foreachRecursive(_matchFile, startsWith, endsWith, contains, breakOnReturn = True)

#---
# preset data management
	def getPresetFileData(self, preset: str) -> FileCategory:
		""" get a structure containing information relating to the requirments in a preset. \n
		structure format: FileCategory[PresetFileCollectionData[FileCollection] | FileCategory[PresetFileCollectionData[FileCollection]]]
		"""

		# generates the data if not yet created
		data = getattr(self, f'{preset}_presetData', None)
		if data == None:
			data = self.generatePresetFileData(preset)
		return data

#-
	def generatePresetFileData(self, preset: str) -> FileCategory:
		""" generates a structure containing information relating to the requirments in a preset. \n
		NOTE: this function forcably regenerates this structure, to access the structure instead: use 'getPassingFiles'. \n
		structure format: FileCategory[PresetFileCollectionData[FileCollection] | FileCategory[PresetFileCollectionData[FileCollection]]]
		"""

		# sub function
		@staticmethod
		def _PresetFromInputData(parent: FileCategory, inputCollection: FileCollection | FileCategory, outputPath: PathLike[str] | str, suffixes: list | None, exts: set | None) -> None:
			if isinstance(inputCollection, FileCollection):
				if suffixes == None:
					parent.add(PresetFileCollectionData(inputCollection.name, inputCollection, outputPath, exts, None))
				else:
					#for suffix in suffixes:
					parent.add(PresetFileCollectionData(inputCollection.name, inputCollection, outputPath, exts, tuple(suffixes)))

			if isinstance(inputCollection, FileCategory):
				child = FileCategory(inputCollection.name)
				parent.add(child)

				for subCollection in inputCollection.children:
					_PresetFromInputData(child, subCollection, outputPath, suffixes, exts)

		# main function
		presetReqs = self.presets[preset]['req']
		presetStruct = FileCategory(preset)

		for category in self.files.children:

			# get preset data for this category
			outputPath = self.presets[preset]['output'].get(f'{category.name}', './default/')
			reqSuffixes = presetReqs.get(f'{category.name}_suffix', None)
			reqExts = presetReqs.get(f'{category.name}_format', None)
			if reqExts != None:
				reqExts = set(reqExts)

			# populate structure
			_PresetFromInputData(presetStruct, category, outputPath, reqSuffixes, reqExts)
		
		# asign and return result
		setattr(self, f'{preset}_presetData', presetStruct)
		return presetStruct

#---
# file copying

	def exportFiles(self, preset: str)-> None:
		""" copies all files in a preset to their respective output dirs. """

		# sub function
		@staticmethod
		def _copyPresetCollection(collection, copyFunc: Callable[[PathLike[str] | str, PathLike[str] | str, tuple[PathLike[str] | str, ...], str], None], presetName: str) -> None:
			if isinstance(collection, PresetFileCollectionData):
				copyFunc(collection.fileCollection.dirPath, collection.exportDirPath, collection.getFilterdFiles(), presetName)

		# main function
		presetFileData = self.getPresetFileData(preset)
		presetFileData.foreachRecursive(_copyPresetCollection, self.copyFiles, preset)

#-
	def copyFiles(self, inputPath: PathLike[str] | str, relOutputPath: PathLike[str] | str, files: Iterable[PathLike[str] | str], presetName: str = '.') -> None:
		""" copy some files. \n
		full output path is as follows: \n
		outputDir(as defined by dirSettings) -> presetName -> relOutputPath\n
		NOTE: created to work on window/linux/darwin. However has only been tested on windows.\n
		"""

		# sub functions
		@staticmethod
		def _copyFiles_Windows(basePath: PathLike, inputPath: PathLike, outputPath: PathLike, files: Iterable[PathLike]) -> Popen:
			# for syntax info see: https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/robocopy
			# define program and paths
			cmdArgs = ['robocopy', inputPath, outputPath]
			# define files to copy
			cmdArgs.extend(files)
			# define copy options
			cmdArgs.extend(['/copy:DA'])
			# define retry options
			cmdArgs.extend(['/w:5'])

			return subprocess.Popen(cmdArgs, cwd=os.path.abspath(basePath), stderr=subprocess.STDOUT, stdout=subprocess.PIPE)

		@staticmethod
		def _copyFiles_Linux(inputPath: PathLike, outputPath: PathLike, files: Iterable[PathLike]) -> Popen:
			# define program
			cmdArgs = ['cp']
			# define files to copy
			cmdArgs.extend(files)
			# define output path
			cmdArgs.append(outputPath)

			return subprocess.Popen(cmdArgs, cwd=os.path.abspath(inputPath), stderr=subprocess.STDOUT, stdout=subprocess.PIPE)
		
		# main function
		if len(files) == 0:
			return
		# copy methods difer per platform
		if platform.system() == "Windows":
			copyJob = _copyFiles_Windows(self.basePath, inputPath, os.path.join(self.outputDir, f'{presetName}/', relOutputPath), files)
		elif platform.system() == "Darwin" or platform.system() == "Linux":
			# darwin uses the same system as linux
			copyJob = _copyFiles_Linux(inputPath, os.path.join(self.outputDir, f'{presetName}/', relOutputPath), files)
		else:
			raise Exception('unsupported system/OS.')
		
		self.exportJobs.append(copyJob)

#-
	def pollFinishedJobs(self, noStdOut: bool = False) -> int:
		""" processes all finished jobs since last poll.
		optinally spits out stdout of finshed jobs to console

		returns the number of unfinished jobs.
		"""

		# sub function
		@staticmethod
		def _isSuccessExitCode(exitcode: int) -> bool:
			if platform.system() == "Windows":
				return bool(exitcode <= 7)
			elif platform.system() == "Darwin" or platform.system() == "Linux":
				# darwin uses the same system as linux
				return bool(exitcode == 0)
			else:
				raise True

		# main function
		for i, job in enumerate(self.exportJobs):
			exitCode = job.poll()
			if exitCode is None:
				continue
			else:
				self.exportJobs[i] = None
				if _isSuccessExitCode(exitCode):
					self.successfullJobs.append(job)
				else:
					self.failedJobs.append(job)

				# pipe subprocess stdout to python console
				# NOTE: this assumes stderr to be merges with stdout
				if not noStdOut:
					print(job.communicate()[0].decode("utf-8"))

		# removes finshed jobs from exportJobs
		self.exportJobs = [job for job in self.exportJobs if job is not None]
		return self.getActiveJobCount()

#-
	def getActiveJobCount(self) -> int:
		return len(self.exportJobs)

#-
	def clearJobResults(self) -> None:
		self.successfullJobs.clear()
		self.failedJobs.clear()

#---
# other

	# intended to be stored externaly since data is irrelevant to files
	# but still included in this class for its use of __fetchJsonData
	def getCustomColors(self, path: PathLike[str] | str) -> dict:
		return self.__fetchJsonData(path)
	
#-
	def __fetchJsonData(self, filePath: PathLike[str] | str) -> dict:
		file = open(filePath)
		data = json.load(file)
		file.close()

		return data