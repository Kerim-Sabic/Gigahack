"""Small, bounded reader for the app's PCM16 RIFF/RF64 files.

This deliberately does not decode arbitrary upload formats; FFmpeg normalizes those first.
Only uncompressed little-endian PCM is accepted. RF64 uses the EBU ds64 size fields.
"""
import os
import struct


def header(frames, rate=16000, channels=1, force_rf64=False):
    if not isinstance(frames, int) or not 0 <= frames < 2**62 or not 8000 <= rate <= 96000 or channels != 1:
        raise ValueError("invalid_pcm_header")
    size = frames * channels * 2
    fmt = b"fmt " + struct.pack("<IHHIIHH", 16, 1, channels, rate, rate * channels * 2, channels * 2, 16)
    if force_rf64 or size + 36 > 0xffffffff:
        return (b"RF64" + struct.pack("<I", 0xffffffff) + b"WAVEds64"
                + struct.pack("<IQQQI", 28, size + 72, size, frames, 0) + fmt
                + b"data" + struct.pack("<I", 0xffffffff))
    return b"RIFF" + struct.pack("<I", size + 36) + b"WAVE" + fmt + b"data" + struct.pack("<I", size)


class Reader:
    def __init__(self, path):
        self.stream = open(path, "rb")
        try:
            self._parse()
        except BaseException:
            self.stream.close()
            raise

    def _parse(self):
        stream = self.stream
        size = os.fstat(stream.fileno()).st_size
        prefix = stream.read(12)
        if len(prefix) != 12 or prefix[:4] not in (b"RIFF", b"RF64") or prefix[8:] != b"WAVE":
            raise ValueError("invalid_canonical_audio_header")
        rf64 = prefix[:4] == b"RF64"
        container_size = struct.unpack("<I", prefix[4:8])[0]
        extended = None
        fmt = None
        # Canonical files have only a few small metadata chunks; bound hostile header scans.
        for _ in range(256):
            chunk = stream.read(8)
            if len(chunk) != 8:
                raise ValueError("truncated_canonical_audio")
            tag, length = struct.unpack("<4sI", chunk)
            if tag == b"ds64":
                if not rf64 or extended is not None or length < 28 or length > 65536:
                    raise ValueError("invalid_rf64_sizes")
                body = stream.read(28)
                if len(body) != 28:
                    raise ValueError("truncated_canonical_audio")
                container_size, data_size, sample_count, table_count = struct.unpack("<QQQI", body)
                if table_count != 0:
                    raise ValueError("unsupported_rf64_size_table")
                extended = data_size, sample_count
                stream.seek(length - 28 + length % 2, 1)
            elif tag == b"fmt ":
                if fmt is not None or not 16 <= length <= 65536:
                    raise ValueError("invalid_pcm_format")
                body = stream.read(16)
                if len(body) != 16:
                    raise ValueError("truncated_canonical_audio")
                fmt = struct.unpack("<HHIIHH", body)
                stream.seek(length - 16 + length % 2, 1)
            elif tag == b"data":
                if fmt is None or (rf64 and (extended is None or length != 0xffffffff)):
                    raise ValueError("missing_pcm_format_or_sizes")
                code, channels, rate, byte_rate, block, bits = fmt
                if code != 1 or channels != 1 or bits != 16 or block != 2 or byte_rate != rate * 2 or not 8000 <= rate <= 96000:
                    raise ValueError("unsupported_canonical_pcm")
                length = extended[0] if rf64 else length
                self.offset, self.rate, self.frames = stream.tell(), rate, length // 2
                if length % 2 or self.offset + length > size or container_size + 8 > size or self.offset + length > container_size + 8:
                    raise ValueError("truncated_canonical_audio")
                if extended and extended[1] not in (0, self.frames):
                    raise ValueError("invalid_rf64_sample_count")
                self.position = 0
                return
            else:
                if length == 0xffffffff or stream.tell() + length > size:
                    raise ValueError("truncated_canonical_audio")
                stream.seek(length + length % 2, 1)
            if stream.tell() > size:
                raise ValueError("truncated_canonical_audio")
        raise ValueError("excessive_audio_header_chunks")

    def getnframes(self):
        return self.frames

    def getframerate(self):
        return self.rate

    def getnchannels(self):
        return 1

    def getsampwidth(self):
        return 2

    def setpos(self, position):
        if not isinstance(position, int) or not 0 <= position <= self.frames:
            raise ValueError("invalid_audio_position")
        self.stream.seek(self.offset + position * 2)
        self.position = position

    def readframes(self, count):
        if not isinstance(count, int) or count < 0:
            raise ValueError("invalid_audio_read_size")
        count = min(count, self.frames - self.position)
        data = self.stream.read(count * 2)
        if len(data) != count * 2:
            raise ValueError("truncated_canonical_audio")
        self.position += count
        return data

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.stream.close()
