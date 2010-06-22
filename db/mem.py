"""Contains the MemoryDatabase implementation"""
from loose import LooseObjectDB
from base import (
						ObjectDBR, 
						ObjectDBW
					)

from gitdb.base import OStream
from gitdb.util import to_bin_sha
from gitdb.exc import (
						BadObject,
						UnsupportedOperation
						)
from gitdb.stream import (
							ZippedStoreShaWriter,
							DecompressMemMapReader,
						)

__all__ = ("MemoryDB", )

class MemoryDB(ObjectDBR, ObjectDBW):
	"""A memory database stores everything to memory, providing fast IO and object
	retrieval. It should be used to buffer results and obtain SHAs before writing
	it to the actual physical storage, as it allows to query whether object already
	exists in the target storage before introducing actual IO
	
	:note: memory is currently not threadsafe, hence the async methods cannot be used
		for storing"""
	
	def __init__(self):
		super(MemoryDB, self).__init__()
		self._db = LooseObjectDB("path/doesnt/matter")
		
		# maps 20 byte shas to their OStream objects
		self._cache = dict()
		
	def set_ostream(self, stream):
		raise UnsupportedOperation("MemoryDB's always stream into memory")
		
	def store(self, istream):
		zstream = ZippedStoreShaWriter()
		self._db.set_ostream(zstream)
		
		istream = self._db.store(istream)
		zstream.close()		# close to flush
		zstream.seek(0)
		
		# don't provide a size, the stream is written in object format, hence the 
		# header needs decompression
		decomp_stream = DecompressMemMapReader(zstream.getvalue(), close_on_deletion=False) 
		self._cache[istream.binsha] = OStream(istream.sha, istream.type, istream.size, decomp_stream)
		
		return istream
		
	def store_async(self, reader):
		raise UnsupportedOperation("MemoryDBs cannot currently be used for async write access")
	
	def has_object(self, sha):
		return to_bin_sha(sha) in self._cache

	def info(self, sha):
		# we always return streams, which are infos as well
		return self.stream(sha)
	
	def stream(self, sha):
		sha = to_bin_sha(sha)
		try:
			ostream = self._cache[sha]
			# rewind stream for the next one to read
			ostream.stream.seek(0)
			return ostream
		except KeyError:
			raise BadObject(sha)
		# END exception handling
	
	def size(self):
		return len(self._cache)
		
	def sha_iter(self):
		return self._cache.iterkeys()
