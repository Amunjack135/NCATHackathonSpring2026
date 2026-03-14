from __future__ import annotations

import CustomMethodsVI.Stream as Stream


class NullStream(Stream.Stream):
	def write(self, buffer) -> None:
		pass
