import threading

# import type defs
from os import PathLike

class ObjAnalyzer():
	def __init__(self, inputPath: PathLike | None = None, outputPath: PathLike | None = None) -> None:
		# constants def
		self.COMMENT_PATTERN = '# '.encode()
		self.OBJECT_PATTERN = 'o '.encode()
		self.VERTEX_PATTERN = 'v '.encode()
		self.FACE_PATTERN = 'f '.encode()

		# paths
		self.inputPath = inputPath
		self.outputPath = outputPath

		# threads
		self.readWriteThread = None

#---
	def run(self, inputPathOverride: PathLike | None = None, outputPathOverride: PathLike | None  = None) -> None:
		""" reads and writes data to and from files in an other thread.\n

		use awaitCompletion() to wait for the process to terminate
		"""
		
		# raise error if no valid path available
		if inputPathOverride == None and self.inputPath == None:
			raise ValueError('no valid input path provided')
		if outputPathOverride == None and self.outputPath == None:
			raise ValueError('no valid output path provided')
		# raise error if thread already running
		if self.readWriteThread != None:
			raise RuntimeError('thread already in use')

		# reset vars
		self.vertCount = 0
		self.faceCount = 0
		self.triCount  = 0
		self.quadCount = 0
		self.ngonCount = 0
		self.objectNames = []

		self.readWriteThread = threading.Thread(target=lambda: (self._readFile(inputPathOverride), self._writeFile(outputPathOverride)))
		self.readWriteThread.start()

#---
	def readData(self, inputPathOverride: PathLike | None  = None) -> None:
		""" writes the data to file in an other thread.\n
		NOTE: data may be incorrect if readData() or run() have not finished running. 

		use awaitCompletion() to wait for the process to terminate
		"""

		# raise error if no valid path available
		if inputPathOverride == None and self.inputPath == None:
			raise ValueError('no valid input path provided')
		# raise error if thread already running
		if self.readWriteThread != None:
			raise RuntimeError('thread already in use')

		# reset vars
		self.vertCount = 0
		self.faceCount = 0
		self.triCount  = 0
		self.quadCount = 0
		self.ngonCount = 0
		self.objectNames = []

		self.readWriteThread = threading.Thread(target=lambda: self._readFile(inputPathOverride))
		self.readWriteThread.start()

#-
	def writeData(self, outputPathOverride: PathLike | None = None)-> None:
		""" writes the data to file in an other thread.\n
		NOTE: data may be incorrect if readData() or run() have not finished running. 

		use awaitCompletion() to wait for the process to terminate
		"""

		# raise error if no valid path available
		if outputPathOverride == None and self.outputPath == None:
			raise ValueError('no valid output path provided')
		# raise error if thread already running
		if self.readWriteThread != None:
			raise RuntimeError('thread already in use')

		self.readWriteThread = threading.Thread(target=lambda: self._writeFile(outputPathOverride))
		self.readWriteThread.start()

#---
	def _readFile(self, inputPathOverride: PathLike | None  = None) -> None:
		with open(inputPathOverride or self.inputPath, 'rb') as fileData:
			for line in fileData:
				# double if since faster than and ¯\_(ツ)_/¯
				if line[0] == self.VERTEX_PATTERN[0]:
					if line[1] == self.VERTEX_PATTERN[1]:
						self.vertCount += 1
				elif line[0] == self.FACE_PATTERN[0]:
					if line[1] == self.FACE_PATTERN[1]:
						self.faceCount += 1
						# checked in order of likly occurrence
						# to avoid unecessary compares
						facePointCount = line.count(b' ')
						if facePointCount == 4:
							self.quadCount += 1
						elif facePointCount == 3:
							self.triCount += 1
						else:
							self.ngonCount += 1
				elif line[0] == self.OBJECT_PATTERN[0]:
					if line[1] == self.OBJECT_PATTERN[1]:
						self.objectNames.append(line[2:-1].decode())

#-
	def _writeFile(self, outputPathOverride: PathLike | None = None)-> None:
		with open(outputPathOverride or self.outputPath, 'w+') as fileData:
			# object names
			if len(self.objectNames) != 0:
				formatedobjectNames = "\n  ".join(self.objectNames)
				fileData.write('Objects:\n  ' + formatedobjectNames + '\n')
				fileData.write('\n')
			else:
				fileData.write('No objects found' + '\n')
				fileData.write('\n')
			# component counts
			fileData.write('Vertex count: ' + str(self.vertCount) + '\n')
			fileData.write('Face count: '   + str(self.faceCount) + '\n')
			fileData.write('\n')
			fileData.write('Tri count: '  + str(self.triCount)  + '\n')
			fileData.write('Quad count: ' + str(self.quadCount) + '\n')
			fileData.write('Ngon count: ' + str(self.ngonCount) + '\n')
			fileData.write('\n')
	
#---
	def awaitCompletion(self) -> None:
		""" awaits competion of any current operations. """

		self.readWriteThread.join()
		# reset ref
		self.readWriteThread = None
#---
	# if None no change
	def setPaths(self, inputPath: PathLike | None = None, outputPath: PathLike | None = None) -> None:
		"""" sets the default paths. None means no changes. """
		if inputPath != None:
			self.inputPath = inputPath
		if outputPath != None:
			self.outputPath = outputPath