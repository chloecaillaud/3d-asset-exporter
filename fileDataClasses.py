#from __future__ import annotations
import os
from dataclasses import *

# import type defs
from types import GenericAlias, UnionType
from collections.abc import Iterable
from typing import Callable, Any
from os import PathLike


@dataclass
class FileDataBaseClass():
	name: str

#-
	def __post_init__(self) -> None:
		self._TypeVerificaton()

#-
	def _TypeVerificaton(self) -> None:
		# sub function
		@staticmethod
		def _checkType(name, itemTypes: tuple, value) -> None:
			""" typecheck for value and its components. """
			"""
			given: list[tuple[str | int] | str]] | set[str]
			and acounting for all possible value type:

			list ->
				baseTypes = (list, set)
				subTypes  = (tuple[str | int], str)

				list[tuple] ->
					baseTypes = (tuple, str)
					subTypes  = (str, int)
					
					list[tuple[str]] ->
						baseTypes = (str, int)
						subTypes  = None

					list[tuple[int]] ->
						baseTypes = (str, int)
						subTypes  = None

				list[str] -> baseTypes = (tuple, str)
						subTypes  = None
			
			set ->
				baseTypes = (list, set)
				subTypes  = (str)

				set[str] ->
					baseTypes = (str)
					subTypes  = None
			"""

			baseTypes = list()
			subTypes = None

			# extract types from Unions
			flatenedItemTypes = list()
			for itemType in itemTypes:
				if isinstance(itemType, UnionType):
					flatenedItemTypes.extend(itemType.__args__)
				else:
					flatenedItemTypes.append(itemType)

			for itemType in flatenedItemTypes:
				# account for parameterized generic typedefs
				if isinstance(itemType, GenericAlias):
					baseTypes.append(itemType.__origin__)
					# get subtypes only if value matches current basetype, to account for multiple subtype groups
					if isinstance(value, itemType.__origin__):
						subTypes = itemType.__args__
				else:
					baseTypes.append(itemType)

			if not isinstance(value, tuple(baseTypes)):
				raise TypeError(f'Expected {name} to be {baseTypes}, got {type(value)}.')

			if subTypes != None:
				for item in value:
					_checkType(f'item in {name}', tuple(subTypes), item)

		# main function
		for field in fields(self):
			_checkType(field.name, (field.type,), getattr(self, field.name))

# type def
FileDataType = FileDataBaseClass


@dataclass
class FileCollection(FileDataBaseClass):
	""" collection of files in a directory. \n

	name - name of the file collection, ex: 'images' \n
	dirPath - path to the directory the files are stores in, ex: '../a/b/' \n
	files - list of file names, ex: ['textFile.txt', 'imageFile.png'] \n
	fileExts - set of extentions present in files, ex: {'.png', '.txt'} \n
	"""

	dirPath: PathLike | str
	files: list[PathLike[str] | str] = field(default_factory = list)
	# not set by user
	fileExts: set[str] = field(default_factory = set, init = False)

#-
	def __post_init__(self) -> None:
		super().__post_init__()
	
		# verify dir path
		self.dirPath = os.path.normpath(self.dirPath)
		if not os.path.isdir(self.dirPath):
			raise ValueError(f'dirPath must be a valid directory.')
		
		# clean up file names
		for i in range(len(self.files)):
			self.files[i] = os.path.basename(self.files[i])

		self.recalculateImplicitData()

#-
	def recalculateImplicitData(self) -> None:
		self.fileExts = {os.path.splitext(file)[1] for file in self.files}

#-
	def add(self, fileName: PathLike[str] | str | Iterable[PathLike[str] | str]) -> None:
		""" add a file to the files list"""
		if isinstance(fileName, (PathLike, str)):
			self.files.append(os.path.basename(fileName))
		elif isinstance(fileName, Iterable):
			self.files.extend([os.path.basename(file) for file in fileName])
		else:
			raise TypeError(f'Expected fileName to be PathLike[str] | str | Iterable[PathLike[str] | str], got {type(fileName)}.')
		self.recalculateImplicitData()

#-
	def remove(self, fileName: PathLike[str] | str) -> None:
		""" remove the first file matching the provided name from the files list. """
		try:
			self.files.remove(os.path.basename(fileName))
			isFilesUpdated = True
		except:
			isFilesUpdated = False

		if isFilesUpdated:
			self.recalculateImplicitData()

	def replaceFiles(self, files: Iterable[PathLike[str] | str]) -> None:
		""" replaces all files in the collection. """
		if not isinstance(files, Iterable):
			raise TypeError(f'Expected files to be Iterable[PathLike[str] | str], got {type(files)}.')
		
		self.files.clear()
		self.files.extend(files)
		self.recalculateImplicitData()


# TODO: find a better name for this class
@dataclass()
class PresetFileCollectionData(FileDataBaseClass):
	""" preset data for a given file collection. \n
	
	name - name of the file collection, ex: 'images'\n
	exportDirPath - the preset output path \n
	requiredExts - set of required extentions, ex: {'.png', '.txt'} \n
	requiredSuffix - list of required prefix placed prior to ext (case sensitive), ex: '_Color'
	"""

	fileCollection: FileCollection
	exportDirPath: PathLike[str] | str
	requiredExts: set[str] | None = None
	requiredSuffixes: tuple[str, ...] | None = None

#-
	def __post_init__(self) -> None:
		super().__post_init__()

		self.exportDirPath = os.path.normpath(self.exportDirPath)

	def _fileFilter(self, fileName: str, suffix: str | None) -> bool:
		(baseName, extName) =  os.path.splitext(fileName)

		# suffixes
		if self.requiredSuffixes != None:
			if suffix != None :
				# secified Suffix
				if not baseName.endswith(suffix):
					return False
			else:
				# any Suffixes
				if not baseName.endswith(self.requiredSuffixes):
					return False

		# ext
		if self.requiredExts != None:
			if extName in self.requiredExts:
				return True
				
		return False

#-
	def setReqs(self, exts: set[str] | None, suffixes: tuple[str, ...] | None) -> None:
		if not isinstance(exts, set):
			TypeError(f'Expected exts to be a set[str], got {type(exts)}.')
		if not isinstance(suffixes, list):
			TypeError(f'Expected exts to be a tuple[str, ...], got {type(suffixes)}.')
		
		self.requiredExts = exts
		self.requiredSuffixes = suffixes

#-
	def getFilterdFiles(self, suffix: str | None = None) -> tuple[PathLike[str] | str, ...]:
		return tuple(filter(lambda file: self._fileFilter(file, suffix=suffix), self.fileCollection.files))

#-
	def getPassingExt(self) -> set[str]:
		if self.requiredExts == None:
			return self.fileCollection.fileExts
		else:
			return self.requiredExts.intersection(self.fileCollection.fileExts)

#-
	def getFailingExt(self) -> set[str]:
		if self.requiredExts == None:
			return set()
		else:
			return self.requiredExts.difference(self.fileCollection.fileExts)

@dataclass
class FileCategory(FileDataBaseClass):
	""" categorical collection of any fileDataTypes. \n

	name - the name of the category, ex: 'images' \n
	children - list containing references to either any fileDataType objects. \n
	"""
	children: list[FileDataType] = field(default_factory = list)

	def get(self, name: str) -> FileDataType:
		""" get child from name. """
		for child in self.children:
			if child.name == name:
				return child
#-
	def add(self, item: FileDataType) -> None:
		""" append a child to the chidren list."""
		if not isinstance(item, FileDataType):
			raise TypeError(f'Expected item to be a FileDataType, got {type(item)}')

		self.children.append(item)

#-
	def remove(self, childName: str) -> None:
		""" remove the first occurence of a child who's name matches the privided one."""
		for i in range(len(self.children)):
			if self.children[i].name == childName:
				self.children.pop(i)
				break

#-
	def foreach(self, func: Callable[[FileDataType, Any], Any | None], *args, breakOnReturn: bool = False) -> Any | None:
		""" iterate over children. \n
		passes the child as  the first argument of the function. \n
		*args - aditional arguments to pass to the function. \n
		breakOnReturn - if func's return value is not None, breaks loop and returns value
		"""
		for child in self.children:
			result = func(child, *args)

			if breakOnReturn and result != None:
				return result
	
	def foreachRecursive(self, func: Callable[[FileDataType, Any], Any | None], *args, breakOnReturn: bool = False) -> Any | None:
		""" iterate recursively  over children. \n
		passes the child as  the first argument of the function. \n
		*args - aditional arguments to pass to the function. \n
		breakOnReturn - if func's return value is not None, breaks loop and returns value
		"""
		for child in self.children:
			# contains data
			if isinstance(child, (FileCollection, PresetFileCollectionData)):
				result = func(child, *args)
			# contains children
			elif isinstance(child, FileCategory):
				result = func(child, *args)
				if not breakOnReturn or result == None:
					result = child.foreachRecursive(func, *args, breakOnReturn = breakOnReturn)
			else:
				result = None

			if breakOnReturn and result != None:
					return result