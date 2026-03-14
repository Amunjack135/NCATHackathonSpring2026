from __future__ import annotations

import CustomMethodsVI.Stream as Stream


class NullStream(Stream.Stream):
	__SINGLETON: NullStream = ...

	def __new__(cls, *args, **kwargs) -> NullStream:
		if NullStream.__SINGLETON is ...:
			NullStream.__SINGLETON = super().__new__(*args, **kwargs)

		return NullStream.__SINGLETON

	def write(self, buffer) -> None:
		pass
